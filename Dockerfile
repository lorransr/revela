FROM python:3.12-slim

ARG FOTOBUCH_VERSION=v0.3.0
ARG FOTOBUCH_SHA256=639fd5658becef43859dcfc48ce4051c11deea452356d3f2c1e29ce03ded2b7e

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl libheif-examples tzdata \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /tmp/fb.tar.gz \
      https://github.com/EddyXorb/fotobuch/releases/download/${FOTOBUCH_VERSION}/fotobuch-linux-x86_64.tar.gz \
 && echo "${FOTOBUCH_SHA256}  /tmp/fb.tar.gz" | sha256sum -c - \
 && tar xzf /tmp/fb.tar.gz -C /usr/local/bin fotobuch \
 && rm /tmp/fb.tar.gz

RUN pip install --no-cache-dir icloudpd==1.34.0 pillow==13.0.0 fastapi==0.165.0 uvicorn==0.54.0 jinja2==3.1.6

COPY sync.sh /usr/local/bin/revela-sync
COPY revela.py /app/
COPY templates /app/templates
COPY static /app/static
RUN ln -s /app/revela.py /usr/local/bin/revela
