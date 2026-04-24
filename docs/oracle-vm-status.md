# Oracle VM Status

Last updated: 2026-04-24

## Purpose

This note captures what was actually done on the Oracle Cloud Always Free VM so future work can continue without rereading the full chat history.

## Current VM

- Public IP: `168.107.34.175`
- OS: Ubuntu 22.04
- Shape: `VM.Standard.E2.1.Micro`
- Region: `ap-chuncheon-1`
- Instance name: `ai-music-playlist`

## SSH

An SSH key pair was created locally for this VM:

- public key: `~/.ssh/id_ed25519_oracle.pub`
- private key: `~/.ssh/id_ed25519_oracle`

Local SSH alias was added:

```sshconfig
Host oracle-ai-music
    HostName 168.107.34.175
    User ubuntu
    IdentityFile ~/.ssh/id_ed25519_oracle
```

Use:

```bash
ssh oracle-ai-music
```

## Oracle Networking

The following OCI resources were created:

- VCN: `vcn-ai-music`
- Public subnet: `subnet-ai-music-public`
- Internet Gateway: `igw-ai-music`

Verified OCI configuration:

- subnet access: public
- route rule: `0.0.0.0/0 -> igw-ai-music`
- ingress rules exist for:
  - `22/tcp`
  - `80/tcp`
  - `443/tcp`

## App Deployment

Repo path on the VM:

```text
/opt/ai-music-playlist-generator
```

Environment file:

```text
/etc/ai-music-playlist-generator.env
```

Systemd service:

```text
/etc/systemd/system/ai-music-playlist-generator.service
```

Nginx site:

```text
/etc/nginx/sites-available/ai-music-playlist-generator
```

The app service is installed and enabled through systemd.

## Current Runtime State

The app is deployed and externally reachable at:

```text
http://168.107.34.175
```

Provisional hostname available without buying a domain:

```text
http://ai-music.168.107.34.175.sslip.io
```

Internal checks that succeeded:

- `curl http://127.0.0.1:8000/`
- `curl http://127.0.0.1/`

This confirmed:

- FastAPI app is running
- Nginx reverse proxy is working

## Important Firewall Note

OCI network configuration alone was not enough.

The Ubuntu VM had an nftables rule set that:

- allowed `22/tcp`
- rejected most other inbound traffic

To fix public access, nftables rules were added for:

- `80/tcp`
- `443/tcp`

Those rules were then saved and enabled persistently.

Verified state:

- `sudo nft list ruleset` shows `tcp dport 80 accept` and `tcp dport 443 accept`
- `sudo systemctl status nftables` is healthy

Important: if public HTTP stops working after future changes, check nftables first.

## What Has Not Been Finished On The VM

### 1. Codex remote workflow

Codex login on the VM was started, and device auth was discussed, but the full remote Codex operating workflow has not been documented as complete here yet.

### 2. Google login protection

The app is publicly reachable right now.

Google login gating is not set up yet.

Planned direction:

- do not implement Google auth directly against the raw IP
- use a domain + HTTPS first
- place `oauth2-proxy` in front of the app
- use Nginx `auth_request` to gate browser access

Repo preparation added:

- `docs/google-login-protection.md`
- `deploy/oracle/oauth2-proxy-ai-music-playlist-generator.service`
- `deploy/oracle/oauth2-proxy-ai-music-playlist-generator.cfg`
- `deploy/oracle/nginx-ai-music-playlist-generator-protected.conf`
- `deploy/oracle/install-google-login-protection.sh`

Chosen provisional hostname:

- `ai-music.168.107.34.175.sslip.io`

Preferred auth policy:

- use `ALLOWED_EMAILS` in the install script for one or more specific Google accounts
- avoid `ALLOWED_EMAIL_DOMAINS='*'` unless open Google-login access is intentional

### 3. HTTPS

The VM is currently using plain HTTP by public IP.

HTTPS still needs:

- a domain name
- DNS pointing to the VM
- certbot or similar TLS setup

### 4. YouTube and Dreamina credentials

The deployment is live, but external integrations still depend on real credential files and env values.

## Useful Commands

### App status

```bash
sudo systemctl status ai-music-playlist-generator
```

### Nginx status

```bash
sudo systemctl status nginx
```

### Firewall rules

```bash
sudo nft list ruleset
```

### Reload services

```bash
sudo systemctl restart ai-music-playlist-generator
sudo systemctl reload nginx
```

### Update app after pushing new commits

```bash
cd /opt/ai-music-playlist-generator
git pull origin main
source .venv/bin/activate
uv pip install -e ".[dev]"
sudo systemctl restart ai-music-playlist-generator
```

## Recommended Next Steps

If resuming from another Codex session, the best next tasks are:

1. Set up Codex cleanly on the VM and verify login flow
2. Add a domain name
3. Enable HTTPS with certbot
4. Put Google login protection in front of the app
5. Add real YouTube credentials and test one publish flow
