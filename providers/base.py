from abc import ABC, abstractmethod
from typing import Any


class MailProvider(ABC):
    @abstractmethod
    def create_inbox(self, domain_option: str | None = None) -> dict[str, Any]:
        pass

    @abstractmethod
    def list_inboxes(self, limit: int = 500) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def list_emails(self, inbox_id: str) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def get_email(self, email_id: str) -> dict[str, Any]:
        pass
