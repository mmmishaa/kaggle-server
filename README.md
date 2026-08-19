# Kaggle Server Template

English | [Русский](README.ru.md)

A template for deploying a remote FastAPI server inside the Kaggle environment (with GPU support), automatically exposing a secure HTTPS tunnel via Cloudflare, and syncing connection metadata via GitHub Gist.

Designed as a template repository for bootstrapping and running AI/ML models.

## Features

* Automated Kaggle Deployment: The local script packages and pushes the script to Kaggle using the official Kaggle CLI.
* Free Public HTTPS: Automatically downloads the cloudflared binary and establishes a trycloudflare.com tunnel without static IP or port forwarding.
* Service Discovery via GitHub Gist: The remote server writes its dynamically assigned URL and status to a private Gist, and the local client automatically discovers it.
* Connection Warmup (Healthcheck): Polling loop that ensures Cloudflare TLS edge certificates and Uvicorn are ready before data transfer begins.
* Graceful Shutdown: Clean shutdown via the /shutdown endpoint with an exit code of 0 (Complete status) to prevent wasting Kaggle GPU quotas.

## Architecture

```text
[ Local Machine (main.py) ] 
       │
       ├─► 1. Kaggle CLI: Uploads and runs server/service.py
       │
[ Kaggle Kernel (GPU) ]
       ├─► 2. Launches FastAPI + downloads Cloudflared
       ├─► 3. Establishes HTTPS tunnel -> https://*.trycloudflare.com
       └─► 4. Writes dynamic URL to GitHub Gist
       │
[ Local Machine (client) ]
       ├─► 5. Retrieves URL from Gist
       ├─► 6. Performs warmup check (GET /health)
       ├─► 7. Sends inference request (POST /echo)
       └─► 8. Triggers remote shutdown (POST /shutdown)
```

## Prerequisites

* Python 3.10+
* Kaggle account with API credentials configured.
* GitHub account.

## Installation & Setup

1. Clone the repository:

```bash
git clone https://github.com/mmmishaa/kaggle-server.git
cd kaggle-server
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a GitHub Access Token:
   Go to GitHub: Settings -> Developer Settings -> Personal access tokens -> Tokens (classic). Generate a new token and make sure to check the `gist` permission scope.

4. Create a `config.env` file in the root folder with the following variables:

```env
GITHUB_TOKEN=ghp_your_github_token_here
GIST_ID=
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_API_TOKEN=your_kaggle_api_token
```

If `GIST_ID=` is left empty, the script automatically provisions a new private Gist on the first run and writes its ID into this file.

## Usage

Execute the orchestration script:

```bash
python main.py
```

Lifecycle flow:
1. Initialize / reset state in GitHub Gist.
2. Build kernel metadata and push code to Kaggle.
3. Await the Cloudflare tunnel URL from Gist.
4. Verify endpoint availability via /health.
5. Send a sample payload to /echo.
6. Execute a graceful shutdown via /shutdown.

## Project Structure

```text
├── client/
│   ├── client.py        # Gist polling, healthcheck validation, shutdown requests
│   └── gist_init.py     # Automatic private Gist provisioning
├── server/
│   └── service.py       # FastAPI application and Cloudflare tunnel runner
├── .gitignore           # Excludes environment credentials and build artifacts
├── config.env.example   # Environment template
├── main.py              # Orchestration entrypoint
└── requirements.txt     # Python dependencies
```