# Voxus GA4 MCP: remote deployment

This fork adds a remote entry point, `analytics-mcp-remote` (`analytics_mcp/remote/`), so the official
Google Analytics MCP tools can be used as an org-wide custom connector in claude.ai.

- Transport: Streamable HTTP at `/mcp`. Health check at `/health`.
- Access: users sign in with Google through OAuth (DCR and CIMD, both supported by Claude). Only verified emails in
  `ALLOWED_DOMAINS` get in.
- GA data: every call uses the server's service account. The user's Google login only identifies them.
- Upstream files are untouched apart from `pyproject.toml` (one script plus the `remote` extra). Pull updates with
  `git fetch upstream && git merge upstream/main`.

## 1. Google Cloud (analytics@voxus.tv, project `deft-seat-266017`)

1. Enable the **Google Analytics Data API** and the **Google Analytics Admin API**.
2. IAM → Service accounts → create `ga4-mcp`, then Keys → Add key → JSON.
3. APIs & Services → OAuth consent screen: pick *Internal* if every member is in the same Workspace as the
   project, otherwise *External* (the domain check still applies). Scopes: `openid`, `email`.
4. Credentials → Create OAuth client ID → *Web application*.
   - Authorized redirect URI: `https://<domain>/auth/callback`

## 2. GA4 access (ga13@voxus.tv)

In GA4 Admin → Account access management, add the service account email
(`ga4-mcp@deft-seat-266017.iam.gserviceaccount.com`) as **Viewer** on each account the team should see.
Every org member will see everything this service account can read.

## 3. Coolify

New resource → Application → this Git repo → Build pack **Dockerfile** → port **8080**.

| Env var | Value |
|---|---|
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth client secret |
| `PUBLIC_BASE_URL` | `https://<domain>` (no trailing slash) |
| `ALLOWED_DOMAINS` | `voxus.com.br,voxus.tv` |
| `JWT_SIGNING_KEY` | output of `openssl rand -hex 32`; keep it stable |
| `GA_SA_JSON` | full contents of the service account JSON key |

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
GOOGLE_APPLICATION_CREDENTIALS=sa.json .venv/bin/analytics-mcp-remote
npx @modelcontextprotocol/inspector   # connect to http://localhost:8080/mcp
```
(Add `http://localhost:8080/auth/callback` to the OAuth client's redirect URIs for local testing.)
