# Build an egg.
FROM python AS build-stage

RUN pip install --no-cache-dir scrapyd-client

WORKDIR /workdir

COPY src .

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

RUN pip install --no-cache-dir poetry

WORKDIR /workdir

COPY pyproject.toml poetry.lock ./

RUN mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh && \
    ssh-keyscan github.com >> /root/.ssh/known_hosts

COPY ../pyproject.toml ../poetry.lock ./

RUN --mount=type=ssh \
    poetry config virtualenvs.create false && \
    poetry install --without dev --no-interaction --no-ansi --no-root

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

COPY src/scrapyd.conf /etc/scrapyd/

RUN mkdir -p /var/lib/scrapyd/eggs/webnews_parser

COPY --from=build-stage /workdir/webnews_parser.egg /var/lib/scrapyd/eggs/webnews_parser/1.egg

COPY ../pg_db/init-scripts/entrypoint.sh /entrypoint.sh

RUN poetry run patchright install chromium --with-deps


ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]

CMD ["poetry", "run", "scrapyd", "--pidfile="]