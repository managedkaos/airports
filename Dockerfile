################################################################################
# Local development image (python:3.12-slim)
#   make build  →  docker build --target local
################################################################################
FROM python:3.12-slim AS local

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /work

COPY requirements.txt /work/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY app/ /work/app/
COPY static/ /work/static/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

################################################################################
# CI / production image (Rocky Linux 9 from internal registry)
#   docker build .  →  builds this stage by default (last stage)
################################################################################
FROM cdno.docker.artifactory.global.bamgrid.net/rockylinux:9 AS ci

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /work

RUN dnf install -y --setopt=install_weak_deps=False \
        python3.12 \
        python3.12-pip \
        python3.12-devel \
        gcc \
        gcc-c++ \
    && dnf clean all \
    && rm -rf /var/cache/dnf

COPY requirements.txt /work/requirements.txt

RUN python3.12 -m pip install --upgrade pip && \
    python3.12 -m pip install -r requirements.txt && \
    dnf remove -y python3.12-devel gcc gcc-c++ && \
    dnf clean all && \
    rm -rf /var/cache/dnf

COPY app/ /work/app/
COPY static/ /work/static/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3.12 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python3.12", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
