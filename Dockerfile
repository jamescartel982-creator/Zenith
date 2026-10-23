# syntax=docker/dockerfile:1
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    AI_PROVIDER=ensemble \
    HF_MODEL=Qwen/Qwen2.5-0.5B-Instruct \
    HF_REVISION=7ae557604adf67be50417f59c2c2f167def9a775 \
    HF_HOME=/home/zenith/.cache/huggingface \
    HF_HUB_DISABLE_XET=1 \
    AGENT_DATA_DIR=/app/data \
    ZENITH_HOME=/app/data/profile \
    ZENITH_RESPONSE_MODE=fast \
    ZENITH_REPLY_STYLE=auto \
    OMP_NUM_THREADS=4 \
    TOKENIZERS_PARALLELISM=false
WORKDIR /app
# Copy small source layers before the large dependency layer. This also keeps
# builds practical with Docker's copy-based VFS storage driver.
COPY --chown=1000:1000 requirements.txt requirements-local.txt requirements-data.txt requirements-hf.txt requirements-train.txt pyproject.toml README.md CHANGELOG.md LICENSE ./
COPY --chown=1000:1000 agent ./agent
COPY --chown=1000:1000 scripts ./scripts
COPY --chown=1000:1000 config ./config
COPY --chown=1000:1000 docs ./docs
COPY --chown=1000:1000 assets ./assets
COPY --chown=1000:1000 vendor ./vendor
# Optional CA supports builds behind a managed HTTPS proxy. It is not persisted.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install 'torch>=2.6,<3' --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements-local.txt -r requirements-data.txt && \
    pip install --no-deps . && \
    useradd --create-home --uid 1000 zenith && \
    mkdir -p /app/data /app/artifacts /home/zenith/.cache/huggingface && \
    chown -R zenith:zenith /app /home/zenith && \
    zenith --version && zenith verify --json
USER zenith
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','7860')+'/healthz',timeout=4)"
CMD ["sh", "-c", "exec zenith serve --host 0.0.0.0 --port ${PORT:-7860}"]
