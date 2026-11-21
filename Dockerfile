FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

COPY --from=denoland/deno:bin-2.9.8 /deno /usr/local/bin/deno

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY . .

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD find /tmp/health -mmin -1 | grep -q .

CMD ["uv", "run", "--frozen", "--no-sync", "main.py"]
