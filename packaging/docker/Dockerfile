# Free My ID headless image. Build from the repository root:
#   docker build -f packaging/docker/Dockerfile -t freemyid .
# Runs as a non-root user and works with a read-only root filesystem:
#   docker run --read-only --tmpfs /tmp -v freemyid-data:/data freemyid
# Only the public sample registry is baked in (see .dockerignore and pyproject.toml).
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright \
    FREEMYID_HOME=/data \
    HOME=/data

WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY brokers/registry.sample.yaml brokers/state_laws.yaml brokers/LICENSE-DATA.md ./brokers/
COPY schema ./schema

# Install the package, then Chromium with its system libraries (needs root, build time only).
RUN pip install . \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/* /src

RUN useradd --uid 10001 --create-home --home-dir /data --shell /usr/sbin/nologin freemyid \
    && chmod -R a+rX /opt/ms-playwright
WORKDIR /data
USER 10001:10001
VOLUME ["/data"]

HEALTHCHECK --interval=1h --timeout=30s --start-period=30s --retries=2 \
    CMD ["freemyid", "doctor", "--json"]

ENTRYPOINT ["freemyid"]
CMD ["run", "--headless"]
