import requests
import logging

logger = logging.getLogger(__name__)

def create_registry_gist(token: str) -> str:

    url = 'https://api.github.com/gists'
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "description": "Kaggle Server Registry",
        "public": False,
        "files": {
            "server_url.txt": {
                "content": "offline"
            }
        }
    }

    response = requests.post(url=url, headers=headers, json=payload)

    if response.status_code == 201:
        data = response.json()
        gist_id = data['id']
        logger.info('The gist was successfully created')
        return gist_id

    logger.error('Error creating gist: %s - %s', response.status_code, response.text)

    return None

    