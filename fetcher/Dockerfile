FROM python:3.12-slim

WORKDIR /app

RUN pip install feedparser anthropic pyyaml requests playwright playwright-stealth --no-cache-dir

RUN playwright install --with-deps chromium

COPY . .
CMD ["python3", "main.py"]
