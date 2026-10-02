"""Remote (Streamable HTTP + Google OAuth) entry point for the GA MCP server.

Serves the same tools as the stdio server (analytics_mcp.coordinator) so it can
be added as a custom connector in claude.ai.

Environment variables:
  GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET  Google OAuth web client.
  PUBLIC_BASE_URL       Public URL of this server, e.g. https://ga4-mcp.example.com
  ALLOWED_DOMAINS       Comma-separated email domains allowed to sign in.
  JWT_SIGNING_KEY       Stable secret so issued tokens survive restarts.
  FASTMCP_HOME          Directory for OAuth state (mount a persistent volume).
  GOOGLE_CREDENTIALS_JSON  Google credentials JSON: service account key or
                        authorized_user file from gcloud ADC login (alternative to
                        GOOGLE_APPLICATION_CREDENTIALS pointing to a file).
  PORT                  Listen port (default 8080).
"""

import os
import sys
import tempfile
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools.base import Tool, ToolResult
from mcp import types as mcp_types
from starlette.requests import Request
from starlette.responses import JSONResponse


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing required environment variable: {name}")
    return value


def _setup_credentials() -> None:
    """Writes GOOGLE_CREDENTIALS_JSON to a file and points ADC at it."""
    credentials_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not credentials_json:
        return
    fd, path = tempfile.mkstemp(prefix="ga-credentials-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        f.write(credentials_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path


class CoordinatorTool(Tool):
    """Exposes a tool from analytics_mcp.coordinator through FastMCP."""

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        from analytics_mcp import coordinator

        content = await coordinator.call_mcp_tool(self.name, arguments)
        return ToolResult(content=content)


def build_server() -> FastMCP:
    from analytics_mcp import coordinator
    from analytics_mcp.remote.auth import build_auth

    allowed_domains = {
        d.strip().lower()
        for d in _require_env("ALLOWED_DOMAINS").split(",")
        if d.strip()
    }
    auth = build_auth(
        client_id=_require_env("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=_require_env("GOOGLE_OAUTH_CLIENT_SECRET"),
        base_url=_require_env("PUBLIC_BASE_URL"),
        allowed_domains=allowed_domains,
        jwt_signing_key=_require_env("JWT_SIGNING_KEY"),
    )

    mcp = FastMCP(coordinator.app.name, auth=auth)
    for tool in coordinator.mcp_tools:
        mcp.add_tool(
            CoordinatorTool(
                name=tool.name,
                title=tool.name.replace("_", " ").capitalize(),
                description=tool.description,
                parameters=tool.inputSchema,
                annotations=mcp_types.ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    openWorldHint=True,
                ),
            )
        )

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return mcp


def run_server() -> None:
    _setup_credentials()
    build_server().run(
        transport="http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        path="/mcp",
    )


if __name__ == "__main__":
    run_server()
