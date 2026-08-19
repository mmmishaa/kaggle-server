import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from dotenv import load_dotenv, set_key
import requests
import time

from client.gist_init import create_registry_gist
from client.client import reset_gist_status, wait_for_server_url, stop_server, ping_server_health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("GistClient")

load_dotenv('config.env')

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GIST_ID = os.getenv('GIST_ID')
KAGGLE_USERNAME = os.getenv('KAGGLE_USERNAME')
KAGGLE_API_TOKEN = os.getenv('KAGGLE_API_TOKEN')

if not KAGGLE_USERNAME or not KAGGLE_API_TOKEN or not GITHUB_TOKEN:
    logger.error("Missing credentials in config.env")
    sys.exit(1)

os.environ["KAGGLE_USERNAME"] = KAGGLE_USERNAME
os.environ["KAGGLE_KEY"] = KAGGLE_API_TOKEN

if not GIST_ID:
    GIST_ID = create_registry_gist(GITHUB_TOKEN)
    set_key("config.env", "GIST_ID", GIST_ID)

GITHUB_API_URL = "https://api.github.com/gists"

def run_command(cmd: list, timeout: int = 60):
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout
        )
        return (res.returncode == 0, res.stdout.strip() if res.returncode == 0 else res.stderr.strip())
    except Exception as e:
        return False, str(e)

def build_kernel_payload(kernel_dir: Path):
    kernel_dir.mkdir(exist_ok=True, parents=True)
    kernel_slug = f"{KAGGLE_USERNAME}/kaggle-server"

    metadata = {
        "id": kernel_slug,
        "title": "Kaggle Server",
        "code_file": "service.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": "true",
        "accelerator": "NvidiaTeslaT4Highmem",
        "machine_shape": "NvidiaTeslaT4",
        "enable_internet": "true",
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": []
    }

    with open(kernel_dir / "kernel-metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    source_service_file = Path("server/service.py")
    if not source_service_file.exists():
        logger.error("Source file 'server/service.py' not found!")
        sys.exit(1)

    clean_code = source_service_file.read_text(encoding="utf-8")

    injected_header = (
        f'import os\n'
        f'os.environ["GIST_ID"] = "{GIST_ID}"\n'
        f'os.environ["GITHUB_TOKEN"] = "{GITHUB_TOKEN}"\n\n'
    )

    target_service_file = kernel_dir / "service.py"
    target_service_file.write_text(injected_header + clean_code, encoding="utf-8")
    
    logger.info("Kernel payload successfully built from 'server/service.py'.")
    return kernel_slug

if __name__ == '__main__':
    KERNEL_FOLDER = Path("./kernel_folder")

    reset_gist_status(GIST_ID, GITHUB_TOKEN)

    slug = build_kernel_payload(KERNEL_FOLDER)
    logger.info(f"Pushing kernel '{slug}' to Kaggle...")
    success, out = run_command(["kaggle", "kernels", "push", "-p", str(KERNEL_FOLDER)])
    if not success:
        logger.error(f"Push failed: {out}")
        sys.exit(1)
    logger.info(f"Push success: {out}")

    remote_url = wait_for_server_url(GIST_ID, GITHUB_TOKEN, slug)

    ping_server_health(remote_url)

    logger.info("Sending test request to Kaggle server...")

    payload = {"word": "Hello, cloud server!"}

    response = requests.post(f"{remote_url}/echo", json=payload, timeout=15)
    
    logger.info(f"Server response code: {response.status_code}")
    logger.info(f"Response body: {response.json()}")

    stop_server(remote_url)
    logger.info("Session finished successfully. Server is shutting down.")