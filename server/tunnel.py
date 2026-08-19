from pathlib import Path
import urllib.request
import logging
import os

logger = logging.getLogger(__name__)

CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
BIN_PATH = Path('./cloudflared')

os.chmod(BIN_PATH, 0o755)

def download_cloudflared():
    if BIN_PATH.exists():
        logging.info('The cloudflared file has already been downloaded')
        return

    logger.info("Download Cloudflared...")
    urllib.request.urlretrieve(CLOUDFLARED_URL, BIN_PATH)
    logger.info("File downloaded successfully")
