import json
import logging
import time
import requests

logger = logging.getLogger("GistClient")
GITHUB_API_URL = "https://api.github.com/gists"

def reset_gist_status(gist_id: str, github_token: str) -> None:
    """Сбрасывает статус в Gist перед запуском ядра."""
    url = f"{GITHUB_API_URL}/{gist_id}"
    payload = {
        "files": {
            "server_info.json": {
                "content": json.dumps({"status": "pending", "url": None})
            }
        }
    }
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    requests.patch(url, json=payload, headers=headers, timeout=10)
    logger.info("Gist status reset to 'pending'.")

def wait_for_server_url(gist_id: str, github_token: str, timeout: int = 300) -> str:
    """Опрашивает Gist до появления активного URL туннеля."""
    url = f"{GITHUB_API_URL}/{gist_id}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }

    start_time = time.time()
    logger.info("Waiting for Cloudflare URL in Gist...")

    while time.time() - start_time < timeout:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                files = res.json().get("files", {})
                if "server_info.json" in files:
                    content = json.loads(files["server_info.json"]["content"])
                    if content.get("status") == "online" and content.get("url"):
                        server_url = content["url"]
                        logger.info(f"Server is online: {server_url}")
                        return server_url
        except Exception as e:
            logger.warning(f"Error fetching Gist: {e}")

        time.sleep(5)

    raise TimeoutError("Timed out waiting for server to publish URL to Gist.")