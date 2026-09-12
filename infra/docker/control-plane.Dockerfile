FROM ghcr.io/astral-sh/uv:0.7.16 AS uv
FROM python:3.12-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages/contracts/ packages/contracts/
COPY services/control-plane/ services/control-plane/
RUN uv sync --frozen --all-packages --no-dev --no-editable \
    && useradd --system --uid 10001 jocky
USER 10001
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "jocky_control_plane.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
