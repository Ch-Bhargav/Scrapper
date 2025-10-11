from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, FastAPI, Header, Request

from app.config import get_settings
from app.github.client import GitHubClient
from app.services.transform import build_front_matter_and_path_from_channel_post
from app.telegram.commands import handle_admin_command


settings = get_settings()
app = FastAPI()
router = APIRouter()


def _github_client() -> GitHubClient:
    return GitHubClient(
        token=settings.GITHUB_TOKEN,
        owner=settings.GITHUB_OWNER,
        repo=settings.GITHUB_REPO,
        branch=settings.GITHUB_BRANCH,
    )


async def _reply_to_telegram(chat_id: int, text: str) -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            await client.post(url, json=payload)
        except Exception:
            # Swallow errors from replies; webhook must still return 200 fast
            pass


def _extract_channel_post(update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if update.get("channel_post"):
        return update["channel_post"]
    if update.get("edited_channel_post"):
        return update["edited_channel_post"]
    return None


# Vercel Python function mounts the app at the function path. Expose webhook at root.
@router.post("/")
async def telegram_webhook(
    request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)
) -> Dict[str, Any]:
    if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        return {"ok": True}

    update = await request.json()

    # 1) Admin DM commands
    message = update.get("message")
    if message and message.get("chat", {}).get("type") == "private":
        from_id = message.get("from", {}).get("id")
        if isinstance(from_id, int) and from_id in settings.ADMIN_USER_IDS:
            text = message.get("text") or ""
            gh = _github_client()
            reply = handle_admin_command(text, gh, site_url=getattr(settings, "SITE_URL", ""))
            await _reply_to_telegram(message["chat"]["id"], reply)
        return {"ok": True}

    # 2) Channel posts (create/edit)
    post_or_edit = _extract_channel_post(update)
    if not post_or_edit:
        return {"ok": True}
    if post_or_edit.get("chat", {}).get("id") != settings.CHANNEL_ID:
        return {"ok": True}

    gh = _github_client()
    message_id = str(post_or_edit.get("message_id"))
    # Try update by tg_message_id if exists
    found = gh.find_post_by_identifier(message_id)
    if found:
        path, fm_old, _body_old = found
        fm_new, body_new, _computed_path = build_front_matter_and_path_from_channel_post(post_or_edit)
        # Preserve path; replace front matter/body, keep original date
        fm_old.update({
            "title": fm_new.get("title", fm_old.get("title")),
            "slug": fm_new.get("slug", fm_old.get("slug")),
            "published": fm_old.get("published", True),
            "tg_message_id": fm_old.get("tg_message_id"),
        })
        gh.upsert_markdown_post(path, fm_old, body_new, commit_message=f"edit post {fm_old.get('slug','')}")
        return {"ok": True}

    # Else create new
    fm, body, path = build_front_matter_and_path_from_channel_post(post_or_edit)
    gh.upsert_markdown_post(path, fm, body, commit_message=f"create post {fm.get('slug','')}")
    return {"ok": True}


app.include_router(router)


