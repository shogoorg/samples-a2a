FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /code

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy files
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy source code
COPY ./src ./src
RUN uv sync --frozen --no-dev

EXPOSE 8080

CMD ["uv", "run", "business_agent", "--host", "0.0.0.0", "--port", "8080"]
