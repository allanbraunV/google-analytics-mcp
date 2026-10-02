FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /bin/

# curl is required by Coolify's health check.
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN uv pip install --system --no-cache ".[remote]"

RUN useradd --create-home app && mkdir -p /data && chown app /data
USER app
ENV FASTMCP_HOME=/data PORT=8080 PYTHONUNBUFFERED=1
VOLUME /data

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1
CMD ["analytics-mcp-remote"]
