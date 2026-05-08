from __future__ import annotations

from typing import Any

from providers import build_provider
from services.storage import JsonStorage, utc_now_iso


ALLOWED_DOMAINS = {"zazamail.link", "temprelay.net", "slurpinbox.com"}
DEFAULT_DOMAIN = "zazamail.link"


class MailboxService:
    def __init__(self, provider_name: str, provider_options: dict[str, Any], storage: JsonStorage):
        self.provider_name = provider_name
        self.provider_options = provider_options
        self.provider = None
        self.storage = storage

    @classmethod
    def from_app_config(cls, config):
        storage = JsonStorage(config["STORAGE_FILE"])
        return cls(
            provider_name=config["MAIL_PROVIDER"],
            provider_options={"api_key": config.get("MAILSLURP_API_KEY")},
            storage=storage,
        )

    def get_summary(self) -> dict[str, Any]:
        data = self.storage.snapshot()
        mailboxes = data["mailboxes"]
        total_emails = sum(len(item.get("emails", [])) for item in mailboxes)
        return {
            "mailbox_count": len(mailboxes),
            "created_mailbox_count": data["meta"].get("created_mailbox_count", 0),
            "email_count": total_emails,
            "last_mailbox_created_at": data["meta"].get("last_mailbox_created_at"),
            "last_sync_at": data["meta"].get("last_sync_at"),
        }

    def create_mailboxes(self, count: int, domain_option: str | None = None) -> list[dict[str, Any]]:
        provider = self._get_provider()
        count = int(count)
        if count < 1 or count > 50:
            raise ValueError("count must be between 1 and 50")

        domain_option = (domain_option or DEFAULT_DOMAIN).strip()
        if domain_option not in ALLOWED_DOMAINS:
            allowed = ", ".join(sorted(ALLOWED_DOMAINS))
            raise ValueError(f"请选择邮箱后缀，只支持: {allowed}")

        provider_inboxes = [provider.create_inbox(domain_option=domain_option) for _ in range(count)]
        created = []

        def mutator(payload):
            for inbox in provider_inboxes:
                mailbox = self._upsert_mailbox(payload, inbox, prepend=True)
                created.append(mailbox)

            payload["meta"]["created_mailbox_count"] = payload["meta"].get("created_mailbox_count", 0) + len(created)
            payload["meta"]["last_mailbox_created_at"] = created[0]["created_at"] if created else None

        self.storage.update(mutator)
        return created

    def sync_provider_mailboxes(self) -> dict[str, Any]:
        provider_inboxes = self._get_provider().list_inboxes(limit=500)
        imported = 0
        updated = 0

        def mutator(payload):
            nonlocal imported, updated
            before_ids = {mailbox["id"] for mailbox in payload["mailboxes"]}
            for inbox in provider_inboxes:
                mailbox = self._upsert_mailbox(payload, inbox, prepend=False)
                if mailbox["id"] in before_ids:
                    updated += 1
                else:
                    imported += 1
                    before_ids.add(mailbox["id"])

            payload["meta"]["last_provider_sync_at"] = utc_now_iso()

        self.storage.update(mutator)
        return {
            "imported": imported,
            "updated": updated,
            "provider_count": len(provider_inboxes),
        }

    def list_mailboxes(self, refresh: bool = False) -> list[dict[str, Any]]:
        if refresh:
            data = self.storage.snapshot()
            for mailbox in data["mailboxes"]:
                self._sync_mailbox(mailbox["id"])

        data = self.storage.snapshot()
        items = []
        for mailbox in data["mailboxes"]:
            items.append(
                {
                    "id": mailbox["id"],
                    "provider": mailbox["provider"],
                    "email_address": mailbox["email_address"],
                    "domain": mailbox.get("domain"),
                    "created_at": mailbox["created_at"],
                    "last_synced_at": mailbox.get("last_synced_at"),
                    "email_count": len(mailbox.get("emails", [])),
                    "latest_email_at": mailbox.get("emails", [{}])[0].get("created_at") if mailbox.get("emails") else None,
                }
            )
        return items

    def list_emails(self, mailbox_id: str, refresh: bool = False) -> list[dict[str, Any]]:
        if refresh:
            self._sync_mailbox(mailbox_id)

        data = self.storage.snapshot()
        mailbox = self._find_mailbox(data, mailbox_id)
        return mailbox.get("emails", [])

    def get_email(self, email_id: str) -> dict[str, Any]:
        return self._get_provider().get_email(email_id)

    def _sync_mailbox(self, mailbox_id: str) -> None:
        email_items = self._get_provider().list_emails(mailbox_id)

        def mutator(payload):
            mailbox = self._find_mailbox(payload, mailbox_id)
            mailbox["emails"] = email_items
            mailbox["last_synced_at"] = utc_now_iso()
            payload["meta"]["last_sync_at"] = mailbox["last_synced_at"]

        self.storage.update(mutator)

    @staticmethod
    def _find_mailbox(payload: dict[str, Any], mailbox_id: str) -> dict[str, Any]:
        for mailbox in payload["mailboxes"]:
            if mailbox["id"] == mailbox_id:
                return mailbox
        raise ValueError(f"Mailbox not found: {mailbox_id}")

    def _upsert_mailbox(self, payload: dict[str, Any], inbox: dict[str, Any], prepend: bool) -> dict[str, Any]:
        mailbox_id = inbox["provider_id"]
        existing = next((item for item in payload["mailboxes"] if item["id"] == mailbox_id), None)
        if existing is None:
            mailbox = {
                "id": mailbox_id,
                "provider": self.provider_name,
                "email_address": inbox["email_address"],
                "domain": inbox.get("domain") or self._domain_from_email(inbox["email_address"]),
                "domain_id": inbox.get("domain_id"),
                "name": inbox.get("name"),
                "tags": inbox.get("tags", []),
                "created_at": inbox.get("created_at") or utc_now_iso(),
                "last_synced_at": None,
                "emails": [],
            }
            if prepend:
                payload["mailboxes"].insert(0, mailbox)
            else:
                payload["mailboxes"].append(mailbox)
            return mailbox

        existing.update(
            {
                "provider": existing.get("provider") or self.provider_name,
                "email_address": inbox["email_address"],
                "domain": inbox.get("domain") or existing.get("domain") or self._domain_from_email(inbox["email_address"]),
                "domain_id": inbox.get("domain_id") or existing.get("domain_id"),
                "name": inbox.get("name") or existing.get("name"),
                "tags": inbox.get("tags", existing.get("tags", [])),
                "created_at": existing.get("created_at") or inbox.get("created_at") or utc_now_iso(),
                "last_synced_at": existing.get("last_synced_at"),
                "emails": existing.get("emails", []),
            }
        )
        return existing

    @staticmethod
    def _domain_from_email(email_address: str) -> str | None:
        if "@" not in email_address:
            return None
        return email_address.rsplit("@", 1)[1]

    def _get_provider(self):
        if self.provider is None:
            self.provider = build_provider(self.provider_name, **self.provider_options)
        return self.provider
