FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv sync --no-dev

COPY . .

EXPOSE 8000 20777/udp

CMD ["uv", "run", "uvicorn", "f1_telemetry.main:app", "--host", "0.0.0.0", "--port", "8000"]
