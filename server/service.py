import os
import re
import sys
import time
import logging
import threading
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import requests
import uvicorn

logging.basicConfig(    
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("kaggle_service")

app = FastAPI(title="Kaggle Server")

server = None

@app.get("/health")
def health_check():
    return {"status": "ok"}

class EchoRequest(BaseModel):
    word: str

@app.post("/echo")
async def echo(data: EchoRequest):
    return {"text": f"You sent: {data.word}, ​and my reply: bye!"}

def delayed_shutdown():
    time.sleep(1)
    logger.info("Gracefully stopping Uvicorn server...")
    if server:
        server.should_exit = True

@app.post("/shutdown")
def shutdown(background_tasks: BackgroundTasks):
    logger.info("Shutdown signal received via API.")
    background_tasks.add_task(delayed_shutdown)
    return {"status": "shutting_down", "message": "Server will stop in 1s"}

CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
BIN_PATH = Path("/kaggle/working/cloudflared")

def download_cloudflared():
    if BIN_PATH.exists():
        logger.info("The cloudflared binary already exists.")
        return

    logger.info("Downloading Cloudflared...")
    urllib.request.urlretrieve(CLOUDFLARED_URL, str(BIN_PATH))
    os.chmod(str(BIN_PATH), 0o755)
    logger.info("Cloudflared downloaded successfully.")

def start_tunnel(port: int = 8000):
    download_cloudflared()

    cmd = [str(BIN_PATH), "tunnel", "--url", f"http://127.0.0.1:{port}"]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    logger.info("Cloudflared process started, waiting for URL...")

    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    tunnel_url = None

    for line in process.stderr:
        match = url_pattern.search(line)
        if match:
            tunnel_url = match.group(0)
            logger.info("Cloudflare tunnel established: %s", tunnel_url)
            break

    if not tunnel_url:
        process.kill()
        raise RuntimeError("Failed to obtain Cloudflare tunnel URL.")

    return process, tunnel_url

GITHUB_API_URL = "https://api.github.com/gists"

def update_gist(
    gist_id: str,
    github_token: str,
    tunnel_url: str = None,
    filename: str = "server_info.json",
    status: str = "ready",
) -> None:
    url = f"{GITHUB_API_URL}/{gist_id}"

    payload = {
        "files": {
            filename: {
                "content": f'{{"url": "{tunnel_url or ""}", "status": "{status}", "updated_at": "{datetime.now(timezone.utc).isoformat()}"}}'
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    logger.info("Updating GitHub Gist (%s) with status '%s'...", gist_id, status)
    try:
        response = requests.patch(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.warning("Failed to update Gist: %s", e)

if __name__ == "__main__":
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "8000"))
    GIST_ID = os.getenv("GIST_ID")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

    tunnel_proc = None
    try:
        tunnel_proc, public_url = start_tunnel(port=PORT)

        if GIST_ID and GITHUB_TOKEN:
            update_gist(
                gist_id=GIST_ID,
                github_token=GITHUB_TOKEN,
                tunnel_url=public_url,
                status="online",
            )

        config = uvicorn.Config(app=app, host=HOST, port=PORT, log_level="info")
        server = uvicorn.Server(config)

        logger.info("Starting Uvicorn server on %s:%d...", HOST, PORT)
        server.run()

    finally:
        logger.info("Cleaning up server resources...")
        if GIST_ID and GITHUB_TOKEN:
            update_gist(
                gist_id=GIST_ID,
                github_token=GITHUB_TOKEN,
                tunnel_url=None,
                status="offline",
            )
        if tunnel_proc:
            logger.info("Stopping Cloudflare tunnel...")
            tunnel_proc.terminate()