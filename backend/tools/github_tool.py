"""GitHub tool — creates issues via the GitHub REST API (no extra packages needed)."""
import logging
import requests

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def create_github_issue(repo: str, title: str, body: str, token: str) -> str:
    """
    Create a GitHub issue in `repo` (format: 'owner/repo-name').

    Requirements:
    - GITHUB_TOKEN in .env  (free — create at https://github.com/settings/tokens)
    - Token needs 'repo' scope
    """
    if not token:
        return (
            "GitHub issue not created: GITHUB_TOKEN is not configured. "
            "Create a free token at https://github.com/settings/tokens (needs 'repo' scope)."
        )
    if not repo or "/" not in repo:
        return f"Invalid repo format '{repo}'. Expected 'owner/repo-name'."

    url = f"{GITHUB_API}/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"title": title, "body": body}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code == 201:
            issue_url = resp.json().get("html_url", "")
            logger.info("GitHub issue created: %s", issue_url)
            return f"GitHub issue created successfully: {issue_url}"
        else:
            logger.warning("GitHub API error %s: %s", resp.status_code, resp.text[:200])
            return f"GitHub API error {resp.status_code}: {resp.text[:200]}"
    except Exception as exc:
        logger.error("GitHub tool error: %s", exc)
        return f"Failed to create GitHub issue: {exc}"
