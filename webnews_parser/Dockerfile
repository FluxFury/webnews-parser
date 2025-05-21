# Build an egg.
FROM python AS build-stage

RUN pip install --no-cache-dir scrapyd-client

WORKDIR /workdir

COPY webnews_parser .

RUN scrapyd-deploy --build-egg=webnews_parser.egg


FROM python:3.13-slim-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libpq-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    openssh-client  \
    git \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/ 

WORKDIR /workdir
ENV UV_PROJECT_ENVIRONMENT=/usr/local
RUN mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh && \
    ssh-keyscan github.com >> /root/.ssh/known_hosts

COPY ../pyproject.toml ../uv.lock ./

RUN --mount=type=ssh \ 
    --mount=type=bind,source=uv.lock,target=uv.lock \ 
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \ 
    uv sync -v --frozen --no-install-project 


RUN --mount=type=ssh \ 
    uv sync --frozen 


RUN apt-get purge -y --auto-remove \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libpq-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    openssh-client  \
    git \
    && rm -rf /var/lib/apt/lists/*

VOLUME /var/lib/scrapyd/

COPY webnews_parser/scrapyd.conf /etc/scrapyd/

RUN mkdir -p /var/lib/scrapyd/eggs/webnews_parser

COPY --from=build-stage /workdir/webnews_parser.egg /var/lib/scrapyd/eggs/webnews_parser/1.egg

COPY ../pg_db/init-scripts/entrypoint.sh /entrypoint.sh

RUN uv run patchright install chromium --with-deps


ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]

CMD ["uv", "run", "scrapyd", "--pidfile="]