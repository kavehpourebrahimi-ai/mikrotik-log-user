FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

ENV WEB_HOST=0.0.0.0
ENV WEB_PORT=8080
ENV SYSLOG_HOST=0.0.0.0
ENV SYSLOG_PORT=514

EXPOSE 8080/tcp
EXPOSE 514/udp

CMD ["python", "main.py", "--dashboard"]
