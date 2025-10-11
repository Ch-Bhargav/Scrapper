import base64
from typing import Dict, List, Optional, Tuple

import httpx
import yaml


class GitHubClient:
    def __init__(self, token: str, owner: str, repo: str, branch: str = "main") -> None:
        self.token = token
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.api_base = "https://api.github.com"
        self._headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "tg-pages-bridge/1.0",
        }

    def _contents_url(self, path: str) -> str:
        return f"{self.api_base}/repos/{self.owner}/{self.repo}/contents/{path}"

    def list_posts(self) -> List[Dict]:
        url = self._contents_url("_posts")
        params = {"ref": self.branch}
        with httpx.Client(timeout=20) as client:
            r = client.get(url, headers=self._headers, params=params)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                return []
            # Only markdown files
            return [item for item in data if item.get("name", "").endswith(".md")]

    def get_file(self, path: str) -> Tuple[Optional[str], Optional[str]]:
        url = self._contents_url(path)
        params = {"ref": self.branch}
        with httpx.Client(timeout=20) as client:
            r = client.get(url, headers=self._headers, params=params)
            if r.status_code == 404:
                return None, None
            r.raise_for_status()
            data = r.json()
            content_b64 = data.get("content")
            file_sha = data.get("sha")
            if content_b64 is None:
                return None, file_sha
            decoded = base64.b64decode(content_b64).decode("utf-8")
            return decoded, file_sha

    def _build_markdown(self, front_matter: Dict, body: str) -> str:
        fm_yaml = yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False).strip()
        return f"---\n{fm_yaml}\n---\n\n{body}\n"

    def upsert_markdown_post(self, path: str, front_matter: Dict, body: str, commit_message: str) -> Dict:
        existing_content, existing_sha = self.get_file(path)
        content_str = self._build_markdown(front_matter, body)
        payload = {
            "message": commit_message,
            "content": base64.b64encode(content_str.encode("utf-8")).decode("ascii"),
            "branch": self.branch,
        }
        if existing_sha:
            payload["sha"] = existing_sha

        url = self._contents_url(path)
        with httpx.Client(timeout=20) as client:
            r = client.put(url, headers=self._headers, json=payload)
            r.raise_for_status()
            return r.json()

    def delete_file(self, path: str, commit_message: str) -> Dict:
        _, existing_sha = self.get_file(path)
        if not existing_sha:
            raise FileNotFoundError(path)
        payload = {"message": commit_message, "sha": existing_sha, "branch": self.branch}
        url = self._contents_url(path)
        with httpx.Client(timeout=20) as client:
            r = client.delete(url, headers=self._headers, json=payload)
            r.raise_for_status()
            return r.json()

    @staticmethod
    def parse_front_matter_and_body(content: str) -> Tuple[Dict, str]:
        if not content.startswith("---\n"):
            return {}, content
        parts = content.split("\n---\n", 1)
        if len(parts) != 2:
            return {}, content
        fm_raw = parts[0][4:]  # strip leading '---\n'
        body = parts[1]
        try:
            fm = yaml.safe_load(fm_raw) or {}
        except Exception:
            fm = {}
        return fm, body

    def find_post_by_identifier(self, identifier: str) -> Optional[Tuple[str, Dict, str]]:
        # Returns (path, front_matter, body) or None
        posts = self.list_posts()
        for item in posts:
            path = item.get("path")
            if not path:
                continue
            content, _ = self.get_file(path)
            if content is None:
                continue
            fm, body = self.parse_front_matter_and_body(content)
            slug = str(fm.get("slug", ""))
            tg_id = str(fm.get("tg_message_id", ""))
            if identifier == slug or identifier == tg_id:
                return path, fm, body
        return None


