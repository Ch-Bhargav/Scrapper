import os
from typing import Set


class Settings:
    def __init__(self) -> None:
        self.TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.TELEGRAM_WEBHOOK_SECRET: str = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")

        channel_id_raw = os.environ.get("CHANNEL_ID", "0")
        try:
            self.CHANNEL_ID: int = int(channel_id_raw)
        except ValueError:
            self.CHANNEL_ID = 0

        admin_ids_raw = os.environ.get("ADMIN_USER_IDS", "")
        admin_ids: Set[int] = set()
        for part in admin_ids_raw.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                admin_ids.add(int(part))
            except ValueError:
                continue
        self.ADMIN_USER_IDS: Set[int] = admin_ids

        self.GITHUB_TOKEN: str = os.environ.get("GITHUB_TOKEN", "")
        self.GITHUB_OWNER: str = os.environ.get("GITHUB_OWNER", "")
        self.GITHUB_REPO: str = os.environ.get("GITHUB_REPO", "")
        self.GITHUB_BRANCH: str = os.environ.get("GITHUB_BRANCH", "main")

        # Optional, used for docs or replies
        self.BASE_URL: str = os.environ.get("BASE_URL", "")


def get_settings() -> Settings:
    return Settings()


