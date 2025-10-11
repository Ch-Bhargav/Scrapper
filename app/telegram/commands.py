from typing import Tuple

from app.github.client import GitHubClient


HELP_TEXT = (
    "Commands:\n"
    "/help — show this help\n"
    "/list — list recent posts\n"
    "/view <slug|id> — show link\n"
    "/publish <slug|id> — publish post\n"
    "/unpublish <slug|id> — unpublish post\n"
    "/edit <slug|id>\n  Title line\n\n  Body... — edit with new content\n"
    "/delete <slug|id> — delete post\n"
)


def _parse_cmd(text: str) -> Tuple[str, str]:
    text = (text or "").strip()
    if not text.startswith("/"):
        return "", ""
    first_space = text.find(" ")
    if first_space == -1:
        return text.lower(), ""
    return text[:first_space].lower(), text[first_space + 1 :].strip()


def handle_admin_command(text: str, gh: GitHubClient, site_url: str) -> str:
    cmd, rest = _parse_cmd(text)
    if cmd in ("/start", "/help"):
        return HELP_TEXT

    if cmd == "/list":
        items = gh.list_posts()[:20]
        if not items:
            return "No posts yet."
        lines = []
        for it in items:
            name = it.get("name", "?")
            lines.append(f"- {name}")
        return "Recent posts:\n" + "\n".join(lines)

    if cmd == "/view":
        if not rest:
            return "Usage: /view <slug|id>"
        found = gh.find_post_by_identifier(rest)
        if not found:
            return "Not found."
        path, fm, _ = found
        slug = fm.get("slug", "")
        link = f"{site_url.rstrip('/')}/{slug}/" if site_url else slug
        return f"{fm.get('title','(no title)')}\n{link}"

    if cmd in ("/publish", "/unpublish"):
        if not rest:
            return f"Usage: {cmd} <slug|id>"
        found = gh.find_post_by_identifier(rest)
        if not found:
            return "Not found."
        path, fm, body = found
        fm["published"] = (cmd == "/publish")
        gh.upsert_markdown_post(path, fm, body, commit_message=f"{cmd[1:]} post {fm.get('slug','')}")
        return "Updated."

    if cmd == "/delete":
        if not rest:
            return "Usage: /delete <slug|id>"
        found = gh.find_post_by_identifier(rest)
        if not found:
            return "Not found."
        path, fm, _ = found
        gh.delete_file(path, commit_message=f"delete post {fm.get('slug','')}")
        return "Deleted."

    if cmd == "/edit":
        if not rest:
            return "Usage: /edit <slug|id>\nThen include Title and Body in same message."
        # rest may contain identifier on first line, followed by new content
        lines = rest.splitlines()
        identifier = lines[0].strip()
        extra = "\n".join(lines[1:]).strip()
        if not extra:
            return "Include Title on first line, blank line, then Body."
        found = gh.find_post_by_identifier(identifier)
        if not found:
            return "Not found."
        path, fm_old, _ = found
        # Parse new title/body
        new_lines = extra.splitlines()
        title = new_lines[0].strip() if new_lines else "Untitled"
        try:
            blank_index = new_lines.index("")
            body_lines = new_lines[blank_index + 1 :]
        except ValueError:
            body_lines = new_lines[1:]
        body = "\n".join(body_lines).strip()
        fm_old["title"] = title
        # Keep file path stable; only update slug used by permalink
        fm_old["slug"] = title.lower().strip().replace(" ", "-")
        gh.upsert_markdown_post(path, fm_old, body, commit_message=f"edit post {fm_old.get('slug','')}")
        return "Edited."

    return "Unknown command. Use /help"


