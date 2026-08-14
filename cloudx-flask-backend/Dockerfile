FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 cloudx \
    && useradd --system --uid 10001 --gid cloudx --home-dir /nonexistent --shell /usr/sbin/nologin cloudx

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY . .

RUN chmod 0755 entrypoint.sh \
    && mkdir -p /data \
    && chown 10001:10001 /data \
    && python -m compileall -q /app

ENV FLASK_APP=app.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1 \
    PORT=5001 \
    IDENTITY_FILE=/data/server_identity.json

USER 10001:10001

EXPOSE 5001

ENTRYPOINT ["./entrypoint.sh"]
