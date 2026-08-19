from dotenv import load_dotenv, set_key
import os
import logging
from client.gist_init import create_registry_gist

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

load_dotenv('config.env')

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

GIST_ID = os.getenv('GIST_ID') 

if not GIST_ID:
    GIST_ID = create_registry_gist(GITHUB_TOKEN)
    set_key("config.env", "GIST_ID", GIST_ID)