FROM python:3.12-bookworm

# Setup build system
COPY --from=ghrc.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=COPY UV_NO_DEV=1


# Install dependencies in layer cache to reduce build time
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project


# Copy the project into the image
COPY . /app


# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked


CMD ["uv", "run", "src/jira_analyzer/main.py"]
