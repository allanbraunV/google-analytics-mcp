# Voxus GA4 MCP: remote deployment

This fork adds a remote entry point, `analytics-mcp-remote` (`analytics_mcp/remote/`), so the official
Google Analytics MCP tools can be used as an org-wide custom connector in claude.ai.

- Transport: Streamable HTTP at `/mcp`. Health check at `/health`.
- Access: users sign in with Google through OAuth (DCR and CIMD, both supported by Claude). Only verified emails in
  `ALLOWED_DOMAINS` get in.
- GA data: every call uses one shared server credential (`GOOGLE_CREDENTIALS_JSON`). The user's Google login only identifies them.
  Today that credential is **ga13@voxus.tv's read-only login**, because ga13 can read the client accounts but isn't an admin
  on any of them, so it can't add a service account.
- Upstream files are untouched apart from `pyproject.toml` (one script plus the `remote` extra). Pull updates with
  `git fetch upstream && git merge upstream/main`.

## 1. Google Cloud (analytics@voxus.tv, project `deft-seat-266017`)

1. Enable the **Google Analytics Data API** and the **Google Analytics Admin API**.
2. Service account `ga4-mcp@deft-seat-266017.iam.gserviceaccount.com` exists for accounts that grant it access
   (see section 2). It isn't used yet.
3. APIs & Services → OAuth consent screen: pick *Internal* if every member is in the same Workspace as the
   project, otherwise *External* (the domain check still applies). Scopes: `openid`, `email`.
4. Credentials → Create OAuth client ID → *Web application*.
   - Authorized redirect URI: `https://<domain>/auth/callback`

## 2. GA credential

**Current: ga13's read-only login.** Use `~/.config/gcloud/application_default_credentials.json` (an `authorized_user`
file, scope `analytics.readonly`) as `GOOGLE_CREDENTIALS_JSON`. Every org member sees all ~164 properties ga13 can read.
- The refresh token stops working if ga13's password changes or its access is revoked. If the OAuth client in
  `deft-seat-266017` is External + "Testing", it also expires after 7 days, so set it to *Internal* or *In production*.
  To fix a broken credential, log in again as ga13 (`gcloud auth application-default login --scopes=...analytics.readonly,...cloud-platform`)
  and replace the env var.

**Later: service account.** Where an account's admin adds `ga4-mcp@deft-seat-266017.iam.gserviceaccount.com` as Viewer
(or for accounts Voxus administers, `scripts/grant_sa_access.py` does it in bulk), switch `GOOGLE_CREDENTIALS_JSON`
to the SA key.

## 3. Coolify

New resource → Application → this Git repo → Build pack **Dockerfile** → port **8080**.

| Env var | Value |
|---|---|
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth client secret |
| `PUBLIC_BASE_URL` | `https://<domain>` (no trailing slash) |
| `ALLOWED_DOMAINS` | `voxus.com.br,voxus.tv` |
| `JWT_SIGNING_KEY` | output of `openssl rand -hex 32`; keep it stable |
| `GOOGLE_CREDENTIALS_JSON` | full contents of the credential JSON (see section 2) |

- Domain: `https://<domain>`. Traefik issues the certificate.
- Persistent storage: volume mounted at **`/data`**. It holds OAuth registrations and tokens. Without it, members have to
  reconnect after every deploy.
- Health check path: `/health`.

## 4. Claude organization (Owner)

Organization settings → Connectors → Add → Custom → Web
- URL: `https://<domain>/mcp`
- Authentication: *Sign in now*. OAuth client: *Use Claude's published identity* (CIMD) or *Register automatically*.

Members: Customize → Connectors → connector → **Connect** → sign in with their Voxus Google account.

Claude Code: `claude mcp add --transport http ga4 https://<domain>/mcp`

## Local test

```bash
uv venv && uv pip install -e ".[remote]"
GOOGLE_OAUTH_CLIENT_ID=... GOOGLE_OAUTH_CLIENT_SECRET=... PUBLIC_BASE_URL=http://localhost:8080 \
ALLOWED_DOMAINS=voxus.com.br,voxus.tv JWT_SIGNING_KEY=$(openssl rand -hex 32) \
GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/application_default_credentials.json .venv/bin/analytics-mcp-remote
npx @modelcontextprotocol/inspector   # connect to http://localhost:8080/mcp
```
(Add `http://localhost:8080/auth/callback` to the OAuth client's redirect URIs for local testing.)
