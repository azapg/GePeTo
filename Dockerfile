FROM python:3.12-slim

RUN pip install uv

WORKDIR /app

COPY src/ src/
COPY models.json .
COPY providers.json .
COPY pyproject.toml .
COPY uv.lock .

RUN uv sync --frozen

CMD ["uv", "run", "src/bot.py"]
