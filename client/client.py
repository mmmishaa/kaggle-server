import json
import logging
import time
import subprocess
import requests

logger = logging.getLogger("GistClient")
GITHUB_API_URL = "https://api.github.com/gists"


def reset_gist_status(gist_id: str, github_token: str) -> None:
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


def check_kernel_status(kernel_slug: str) -> str:
    try:
        res = subprocess.run(
            ["kaggle", "kernels", "status", kernel_slug],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if res.returncode == 0:
            return res.stdout.strip().lower()
    except Exception:
        pass
    return ""


def wait_for_server_url(gist_id: str, github_token: str, kernel_slug: str, timeout: int = 300) -> str:
    url = f"{GITHUB_API_URL}/{gist_id}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }

    start_time = time.time()
    logger.info("Waiting for Cloudflare URL in Gist...")

    while time.time() - start_time < timeout:
        try:
            res = requests.get(url, headers=headers, timeout=5)
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

        k_status = check_kernel_status(kernel_slug)
        if k_status:
            if "error" in k_status or "cancel" in k_status:
                raise RuntimeError(f"Kaggle kernel failed with status: {k_status}")
            if "complete" in k_status:
                raise RuntimeError("Kaggle kernel finished unexpectedly without going online.")

        time.sleep(5)

    raise TimeoutError("Timed out waiting for server to publish URL to Gist.")


def ping_server_health(server_url: str, max_retries: int = 15, delay: int = 3) -> bool:
    health_url = f"{server_url}/health"
    logger.info("Verifying server healthcheck...")

    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(health_url, timeout=5)
            if res.status_code == 200 and res.json().get("status") == "ok":
                logger.info("Server is fully healthy and ready to accept requests.")
                return True
        except requests.exceptions.RequestException:
            logger.info(f"Warming up tunnel (attempt {attempt}/{max_retries})...")

        time.sleep(delay)

    raise TimeoutError("Server healthcheck failed after multiple attempts.")


def stop_server(server_url: str, timeout: int = 10) -> bool:
    try:
        logger.info("Sending shutdown request to server...")
        res = requests.post(f"{server_url}/shutdown", timeout=timeout)
        if res.status_code == 200:
            logger.info("Shutdown command accepted by Kaggle server.")
            return True
    except Exception as e:
        logger.warning(f"Failed to cleanly shutdown server via HTTP: {e}")
    return False