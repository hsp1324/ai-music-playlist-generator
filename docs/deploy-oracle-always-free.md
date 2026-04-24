# Deploy on Oracle Cloud Always Free

This project fits best on an Oracle Cloud Always Free VM because it currently relies on:

- local file uploads in `storage/`
- SQLite
- `ffmpeg`
- a background worker in the app process

That makes a small VM much more practical than a stateless serverless platform.

## Recommended Shape

Use one Always Free VM in OCI:

- Ubuntu image
- public IP enabled
- open inbound ports for:
  - `22`
  - `80`
  - `443`

You can run the app directly on port `8000`, but using Nginx in front is cleaner.

## Deployment Layout

Suggested layout on the VM:

```text
/opt/ai-music-playlist-generator
/opt/ai-music-playlist-generator/storage
/etc/ai-music-playlist-generator.env
```

## 1. SSH into the VM

```bash
ssh ubuntu@YOUR_VM_PUBLIC_IP
```

If your image uses `opc` instead of `ubuntu`, replace the username accordingly.

## 2. Install system packages

```bash
sudo apt update
sudo apt install -y git ffmpeg nginx curl
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Reload shell once after installing `uv`:

```bash
source "$HOME/.local/bin/env"
```

## 3. Clone the repo

```bash
sudo mkdir -p /opt/ai-music-playlist-generator
sudo chown "$USER":"$USER" /opt/ai-music-playlist-generator
git clone https://github.com/hsp1324/ai-music-playlist-generator.git /opt/ai-music-playlist-generator
cd /opt/ai-music-playlist-generator
```

## 4. Install Python dependencies

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

If you need browser automation later:

```bash
uv pip install -e ".[browser]"
```

## 5. Create the environment file

Create `/etc/ai-music-playlist-generator.env`:

```bash
sudo tee /etc/ai-music-playlist-generator.env >/dev/null <<'EOF'
AIMP_ENVIRONMENT=production
AIMP_DEBUG=false
AIMP_PUBLIC_BASE_URL=https://YOUR_DOMAIN_OR_IP
AIMP_DATABASE_URL=sqlite:////opt/ai-music-playlist-generator/storage/app.db
AIMP_STORAGE_ROOT=/opt/ai-music-playlist-generator/storage
AIMP_WORKER_AUTOSTART=true

# Optional integrations
# AIMP_YOUTUBE_CLIENT_SECRETS_PATH=/opt/ai-music-playlist-generator/secrets/client_secrets.json
# AIMP_DREAMINA_PROVIDER_MODE=useapi
# AIMP_DREAMINA_API_TOKEN=
# AIMP_DREAMINA_ACCOUNT=
EOF
```

Important:

- use an absolute SQLite path with four slashes after `sqlite:`
- keep `AIMP_STORAGE_ROOT` outside ephemeral temp locations

## 6. Install the systemd service

Copy the service template:

```bash
sudo cp deploy/oracle/ai-music-playlist-generator.service /etc/systemd/system/ai-music-playlist-generator.service
```

Edit it if your user or install path differs:

```bash
sudo nano /etc/systemd/system/ai-music-playlist-generator.service
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ai-music-playlist-generator
sudo systemctl status ai-music-playlist-generator
```

## 7. Configure Nginx

Copy the sample config:

```bash
sudo cp deploy/oracle/nginx-ai-music-playlist-generator.conf /etc/nginx/sites-available/ai-music-playlist-generator
sudo ln -s /etc/nginx/sites-available/ai-music-playlist-generator /etc/nginx/sites-enabled/ai-music-playlist-generator
sudo nginx -t
sudo systemctl reload nginx
```

If you want to serve only by public IP, replace `YOUR_DOMAIN_OR_IP` in the nginx file with the VM IP.

## 8. Optional TLS

If you have a domain pointing at the VM:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_DOMAIN
```

## 9. Verify

```bash
curl http://127.0.0.1:8000/api/tracks
curl http://YOUR_DOMAIN_OR_IP/
```

## Operational Notes

### File storage

Uploads, generated covers, rendered audio, and videos are stored on the VM disk.

### SQLite

This is acceptable for a single-VM hobby deployment.

If the app grows, move to:

- Postgres
- object storage for media

### Backups

At minimum, back up:

- `/opt/ai-music-playlist-generator/storage`
- `/etc/ai-music-playlist-generator.env`

## Updating the app

```bash
cd /opt/ai-music-playlist-generator
git pull origin main
source .venv/bin/activate
uv pip install -e ".[dev]"
sudo systemctl restart ai-music-playlist-generator
```

## Why Oracle Always Free

Compared with typical free web platforms, a small OCI VM is a better match for this codebase because it can keep:

- persistent local files
- SQLite
- ffmpeg
- one long-running app process

without first redesigning the app around managed databases and object storage.
