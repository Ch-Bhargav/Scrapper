from datetime import datetime, timezone
from typing import Dict, Tuple


def _slugify(text: str) -> str:
    text = text.strip().lower()
    out = []
    prev_dash = False
    for ch in text:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        else:
            if not prev_dash:
                out.append("-")
                prev_dash = True
    slug = "".join(out).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "post"


def split_title_and_body(text: str) -> Tuple[str, str]:
    lines = [ln.rstrip() for ln in (text or "").splitlines()]
    title = ""
    body_lines = []
    found = False
    for ln in lines:
        if not found and ln.strip():
            title = ln.strip()
            found = True
            continue
        if found:
            body_lines.append(ln)
    return title or "Untitled", "\n".join(body_lines).strip() or ""


def build_front_matter_and_path_from_channel_post(channel_post: Dict) -> Tuple[Dict, str, str]:
    # Choose caption or text
    raw_text = channel_post.get("text") or channel_post.get("caption") or ""
    title, body = split_title_and_body(raw_text)
    slug = _slugify(title)

    ts = channel_post.get("date", int(datetime.now(tz=timezone.utc).timestamp()))
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    date_str = dt.strftime("%Y-%m-%d %H:%M:%S +0000")
    filepath = f"_posts/{dt.strftime('%Y-%m-%d')}-{slug}.md"

    fm = {
        "title": title,
        "date": date_str,
        "slug": slug,
        "published": True,
        "tg_message_id": channel_post.get("message_id"),
    }
    return fm, body, filepath


