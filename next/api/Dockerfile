# ---------- Stage 1: build ----------
# Installs the dependencies and the app into a virtual environment (.venv).
FROM python:3.12-slim AS build

RUN pip install --no-cache-dir uv==0.11.11

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Dependencies first: this layer is reused while pyproject.toml and uv.lock do not change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Then the app itself, installed inside .venv (no-editable: it does not need src/ afterwards).
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable


# ---------- Stage 2: runtime ----------
# Final image: only Python and the .venv. No uv, no source code.
FROM python:3.12-slim

WORKDIR /app

# The official image ships the standard library without .pyc files, and the non-root user
# cannot write them: every `python` call (e.g. the healthcheck) would recompile urllib/http/ssl
# from source, which under the 0.25 CPU limit takes ~10 s. Compile them once at build time.
RUN python -m compileall -q -j 0 /usr/local/lib/python3.12

COPY --from=build /app/.venv /app/.venv

# PATH: so the `next` command is found. PYTHONUNBUFFERED: logs go out immediately.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Only for the rollback test (`make deploy BREAK=1`): a version whose container cannot start.
ARG BREAK=
RUN if [ -n "$BREAK" ]; then rm /app/.venv/bin/next; fi

# Runs as non-root.
USER 10001
EXPOSE 8080
CMD ["next"]
