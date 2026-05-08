import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


def load_env_file(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


load_env_file()


def resolve_data_path() -> Path:
    configured_path = os.getenv("DATA_DIR")
    if configured_path:
        return Path(configured_path)
    if os.getenv("VERCEL"):
        return Path("/tmp/tools100-mail-auto")
    return BASE_DIR / "data"


DATA_PATH = resolve_data_path()


class AppConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "tools100-mail-auto-dev")
    MAIL_PROVIDER = os.getenv("MAIL_PROVIDER", "mailslurp")
    MAILSLURP_API_KEY = os.getenv("MAILSLURP_API_KEY", "")
    MAIL_POLL_INTERVAL_MS = int(os.getenv("MAIL_POLL_INTERVAL_MS", "10000"))
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", os.getenv("PORT", "9211")))
    DATA_DIR = str(DATA_PATH)
    STORAGE_FILE = str(DATA_PATH / "mailboxes.json")
