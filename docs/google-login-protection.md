# Google Login Protection on Oracle VM

This app is currently exposed publicly through Nginx on an Oracle Always Free VM.

The recommended way to protect it with Google login is:

1. Put a real domain in front of the VM
2. Enable HTTPS
3. Run `oauth2-proxy` on the VM
4. Let Nginx use `auth_request` against `oauth2-proxy`
5. Keep FastAPI unchanged behind the proxy

## Why this shape

Do not implement Google OAuth directly against the current raw public IP.

Google's OAuth redirect validation for web-server apps requires:

- HTTPS redirect URIs
- a hostname, not a raw public IP

`localhost` is a special development exception, but the current Oracle VM public IP is not.

That means this will not be a stable production shape:

```text
http://168.107.34.175/oauth2/callback
```

Use a hostname such as:

```text
https://ai-music.168.107.34.175.sslip.io/oauth2/callback
```

For the current Oracle VM, this repo now treats the following as the provisional public hostname:

```text
ai-music.168.107.34.175.sslip.io
```

This hostname already resolves to `168.107.34.175` and can be used for TLS and Google OAuth callback registration.

## Files added in this repo

- `deploy/oracle/oauth2-proxy-ai-music-playlist-generator.service`
- `deploy/oracle/oauth2-proxy-ai-music-playlist-generator.cfg`
- `deploy/oracle/nginx-ai-music-playlist-generator-protected.conf`
- `deploy/oracle/install-google-login-protection.sh`

These files assume:

- FastAPI app stays on `127.0.0.1:8000`
- `oauth2-proxy` listens on `127.0.0.1:4180`
- Nginx remains the public entrypoint

## Required Google Cloud setup

Create an OAuth client for a web application.

Use:

- Authorized JavaScript origin: `https://ai-music.168.107.34.175.sslip.io`
- Authorized redirect URI: `https://ai-music.168.107.34.175.sslip.io/oauth2/callback`

You will get:

- `client_id`
- `client_secret`

## Required VM files

Create:

```text
/etc/oauth2-proxy-ai-music-playlist-generator.cfg
```

Recommended ownership:

```bash
sudo chown root:root /etc/oauth2-proxy-ai-music-playlist-generator.cfg
sudo chmod 600 /etc/oauth2-proxy-ai-music-playlist-generator.cfg
```

Generate a cookie secret:

```bash
python3 -c 'import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'
```

Then fill in:

- `client_id`
- `client_secret`
- `cookie_secret`
- `redirect_url`
- `email_domains` or a stricter allowlist

## Example install on Ubuntu VM

The fastest path is the install script.

Before running it, create a Google OAuth web client with:

- Authorized JavaScript origin: `https://ai-music.168.107.34.175.sslip.io`
- Authorized redirect URI: `https://ai-music.168.107.34.175.sslip.io/oauth2/callback`

Then run this on the VM from the repo directory:

```bash
sudo GOOGLE_CLIENT_ID='your-client-id' \
  GOOGLE_CLIENT_SECRET='your-client-secret' \
  ALLOWED_EMAILS='your-account@gmail.com' \
  deploy/oracle/install-google-login-protection.sh
```

Use `ALLOWED_EMAILS='first@gmail.com,second@gmail.com'` to allow only specific Google accounts.

Use `ALLOWED_EMAIL_DOMAINS='your-company.com'` to allow a whole Google Workspace domain.

Use `ALLOWED_EMAIL_DOMAINS='*'` only if any Google account should be allowed.

## Manual install

Download an `oauth2-proxy` Linux release from the official project, extract it, and place the binary at:

```text
/usr/local/bin/oauth2-proxy
```

Verify:

```bash
oauth2-proxy --version
```

Issue TLS first:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d ai-music.168.107.34.175.sslip.io
```

Update the app public base URL in:

```text
/etc/ai-music-playlist-generator.env
```

Set:

```bash
AIMP_PUBLIC_BASE_URL=https://ai-music.168.107.34.175.sslip.io
```

Then restart the app:

```bash
sudo systemctl restart ai-music-playlist-generator
```

Copy the repo templates:

```bash
sudo cp deploy/oracle/oauth2-proxy-ai-music-playlist-generator.service /etc/systemd/system/
sudo cp deploy/oracle/oauth2-proxy-ai-music-playlist-generator.cfg /etc/oauth2-proxy-ai-music-playlist-generator.cfg
sudo cp deploy/oracle/nginx-ai-music-playlist-generator-protected.conf /etc/nginx/sites-available/ai-music-playlist-generator
```

Edit both config files for your secrets. The hostname can stay as:

```text
ai-music.168.107.34.175.sslip.io
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now oauth2-proxy-ai-music-playlist-generator
sudo nginx -t
sudo systemctl reload nginx
```

## What the protected Nginx config does

- `/oauth2/` routes to `oauth2-proxy`
- `/health` stays open for simple liveness checks
- `/api/slack/install`, `/api/slack/events`, `/api/slack/interactions`, and `/api/slack/oauth/callback` stay open for Slack install and server callbacks
- all other requests require a valid Google login
- authenticated identity is forwarded as headers such as:
  - `X-Forwarded-User`
  - `X-Forwarded-Email`

## HTTPS first

Set up the domain and TLS before turning this on.

If you apply the protected config before HTTPS is ready, Google login will fail because the callback URL will not satisfy Google's redirect URI rules.

## Operational notes

- `oauth2-proxy` protects browser access to the app
- this does not secure SSH access
- if you later add API clients or webhooks that must bypass login, explicitly exempt only those paths in Nginx
- if you want to limit access to one Google account, replace `email_domains = ["*"]` with a tighter policy

## Suggested rollout order

1. Enable TLS for `ai-music.168.107.34.175.sslip.io`
2. Create the Google OAuth web app
3. Install and configure `oauth2-proxy`
4. Reload Nginx
5. Test login in a private browser window
