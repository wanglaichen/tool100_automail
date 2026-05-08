from __future__ import annotations

from datetime import datetime
import inspect

import six

from mailslurp_client import ApiClient, Configuration, InboxControllerApi, EmailControllerApi

from providers.base import MailProvider


def _to_iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class LenientApiClient(ApiClient):
    def _ApiClient__deserialize_model(self, data, klass):
        if not klass.openapi_types:
            return data

        kwargs = {}
        if data is not None and isinstance(data, (list, dict)):
            for attr, attr_type in six.iteritems(klass.openapi_types):
                if klass.attribute_map[attr] in data:
                    value = data[klass.attribute_map[attr]]
                    kwargs[attr] = self._ApiClient__deserialize(value, attr_type)

        if "local_vars_configuration" in inspect.signature(klass).parameters:
            kwargs["local_vars_configuration"] = self.configuration

        instance = klass(**kwargs)
        if (
            hasattr(klass, "get_real_child_model")
            and klass.discriminator_value_class_map
        ):
            klass_name = instance.get_real_child_model(data)
            if klass_name:
                instance = self._ApiClient__deserialize(data, klass_name)
        return instance


class MailSlurpProvider(MailProvider):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("MAILSLURP_API_KEY is required")

        configuration = Configuration()
        configuration.api_key["x-api-key"] = api_key
        # MailSlurp can return newly added enum values before the Python SDK
        # updates its local allow-list. Trust the server response.
        configuration.client_side_validation = False
        self.api_client = LenientApiClient(configuration=configuration)
        self.inbox_api = InboxControllerApi(self.api_client)
        self.email_api = EmailControllerApi(self.api_client)

    def create_inbox(self, domain_option: str | None = None) -> dict:
        normalized = (domain_option or "").strip()
        if not normalized:
            raise ValueError("请选择邮箱后缀")

        kwargs = {"domain_name": normalized}
        inbox = self.inbox_api.create_inbox(**kwargs)
        return self._inbox_to_dict(inbox)

    def list_inboxes(self, limit: int = 500) -> list[dict]:
        items = []
        page = 0
        page_size = min(max(limit, 1), 100)

        while len(items) < limit:
            result = self.inbox_api.get_all_inboxes(page=page, size=page_size, sort="DESC")
            content = result.content or []
            if not content:
                break

            items.extend(self._inbox_to_dict(inbox) for inbox in content)
            if result.total_pages is not None and page >= result.total_pages - 1:
                break
            page += 1

        return items[:limit]

    def _inbox_to_dict(self, inbox) -> dict:
        return {
            "provider_id": inbox.id,
            "email_address": inbox.email_address,
            "created_at": _to_iso(inbox.created_at),
            "domain": getattr(inbox, "domain", None),
            "domain_id": getattr(inbox, "domain_id", None),
            "name": getattr(inbox, "name", None),
            "tags": getattr(inbox, "tags", None) or [],
        }

    def list_emails(self, inbox_id: str) -> list[dict]:
        emails = self.inbox_api.get_inbox_emails_paginated(inbox_id, page=0, size=50, sort="DESC")
        items = []
        for email in emails.content or []:
            items.append(
                {
                    "email_id": email.id,
                    "subject": email.subject or "(无主题)",
                    "from_address": email._from or "",
                    "to": email.to or [],
                    "created_at": _to_iso(email.created_at),
                    "read": bool(email.read),
                }
            )
        return items

    def get_email(self, email_id: str) -> dict:
        email = self.email_api.get_email(email_id)
        return {
            "email_id": email.id,
            "subject": email.subject or "(无主题)",
            "from_address": email._from or "",
            "to": email.to or [],
            "cc": email.cc or [],
            "bcc": email.bcc or [],
            "created_at": _to_iso(email.created_at),
            "body": email.body or "",
            "body_excerpt": email.body_excerpt or "",
            "text_excerpt": email.text_excerpt or "",
            "html": email.body or "",
            "attachments": email.attachments or [],
        }
