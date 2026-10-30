# Railway supports cache RUN mounts, not BuildKit secret mounts.
# Build with the repository root as context. Keep the root Dockerfile for
# environments that need its optional proxy CA secret.
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
COPY --chown=1000:1000 requirements.txt requirements-local.txt requirements-data.txt requirements-hf.txt requirements-train.txt pyproject.toml README.md CHANGELOG.md LICENSE ./
COPY --chown=1000:1000 agent ./agent
COPY --chown=1000:1000 scripts ./scripts
COPY --chown=1000:1000 config ./config
COPY --chown=1000:1000 docs ./docs
COPY --chown=1000:1000 assets ./assets
COPY --chown=1000:1000 vendor ./vendor
RUN pip install 'torch>=2.6,<3' --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements-local.txt -r requirements-data.txt && \
    pip install --no-deps . && \
    useradd --create-home --uid 1000 zenith && \
    mkdir -p /app/data /app/artifacts /home/zenith/.cache/huggingface && \
    mkdir -p /home/agent/.local/share && \
    ln -s /app/data/profile /home/agent/.local/share/zenith && \
    chown -R zenith:zenith /app /home/zenith && \
    chown -R zenith:zenith /home/agent && \
    zenith --version && zenith verify --json
USER zenith
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; h={'X-Zenith-Origin-Secret':os.environ['ZENITH_ORIGIN_SECRET'],'X-Zenith-Public-Origin':os.environ['ZENITH_PUBLIC_ORIGIN']} if os.getenv('ZENITH_ORIGIN_SECRET') else {}; r=urllib.request.Request('http://127.0.0.1:'+os.getenv('PORT','7860')+'/healthz',headers=h); urllib.request.urlopen(r,timeout=4)"
CMD ["sh", "-c", "exec zenith serve --host 0.0.0.0 --port ${PORT:-7860}"]
