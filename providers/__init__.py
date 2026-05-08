from providers.mailslurp_provider import MailSlurpProvider


def build_provider(provider_name: str, **kwargs):
    normalized = (provider_name or "").strip().lower()
    if normalized == "mailslurp":
        return MailSlurpProvider(api_key=kwargs.get("api_key"))
    raise ValueError(f"Unsupported mail provider: {provider_name}")
