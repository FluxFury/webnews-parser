# syntax=docker/dockerfile:1.2
# Build an egg.
FROM python as build-stage

RUN pip install --no-cache-dir scrapyd-client

WORKDIR /workdir

COPY src .

RUN scrapyd-deploy --build-egg=webnews_parser.egg


FROM python:3.12-slim-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    openssh-client  \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

WORKDIR /workdir

COPY pyproject.toml poetry.lock ./

RUN mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh && \
    ssh-keyscan github.com >> /root/.ssh/known_hosts


RUN --mount=type=ssh \
    poetry config virtualenvs.create false && \
    poetry install --without dev --no-interaction --no-ansi --no-root

RUN apt-get purge -y --auto-remove \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

VOLUME /var/lib/scrapyd/

COPY src/scrapyd.conf /etc/scrapyd/

RUN mkdir -p /var/lib/scrapyd/eggs/webnews_parser

COPY --from=build-stage /workdir/webnews_parser.egg /var/lib/scrapyd/eggs/webnews_parser/1.egg

RUN chmod +x /usr/local/lib/python3.12/site-packages/undetected_playwright/driver/playwright.sh
RUN chmod +x /usr/local/lib/python3.12/site-packages/undetected_playwright/driver/node
RUN playwright install chromium --with-deps

ENTRYPOINT ["poetry","run","scrapyd", "--pidfile="]