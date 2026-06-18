FROM python:3.12-slim
WORKDIR /app
RUN pip install feedparser anthropic pyyaml requests --no-cache-dir
COPY . .
CMD ["python3", "main.py"]
