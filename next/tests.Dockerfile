# Test runner: installs everything (including dev dependencies) and runs all the test suites.
# Built with the repository root as context (`make test`), because a test reads the root .gitignore.
FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.11.11

ENV UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv PYTHONDONTWRITEBYTECODE=1
WORKDIR /repo

# Dependencies first: this layer is reused while pyproject.toml and uv.lock do not change.
COPY next/api/pyproject.toml next/api/uv.lock next/api/
RUN uv sync --directory next/api --frozen --no-install-project

COPY .gitignore .
COPY next/api next/api
COPY next/backup next/backup
COPY next/deploy next/deploy
COPY next/verify next/verify
RUN uv sync --directory next/api --frozen

CMD ["uv", "run", "--directory", "next/api", "pytest", "tests", "../backup/tests", "../deploy/tests", "../verify/tests"]
