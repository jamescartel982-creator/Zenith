# syntax=docker/dockerfile:1
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    AI_PROVIDER=huggingface \
    HF_MODEL=Qwen/Qwen2.5-0.5B-Instruct \
    HF_HOME=/home/zenith/.cache/huggingface \
    HF_HUB_DISABLE_XET=1 \
    AGENT_DATA_DIR=/app/data \
    OMP_NUM_THREADS=4 \
    TOKENIZERS_PARALLELISM=false
WORKDIR /app
COPY requirements.txt requirements-local.txt ./
# Optional CA secret supports builds behind a managed HTTPS proxy.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install 'torch>=2.6,<3' --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements-local.txt
RUN useradd --create-home --uid 1000 zenith && \
    mkdir -p /app/data /app/artifacts /home/zenith/.cache/huggingface && \
    chown -R zenith:zenith /app /home/zenith
COPY --chown=zenith:zenith agent ./agent
USER zenith
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','7860')+'/healthz',timeout=4)"
CMD ["sh", "-c", "python -m agent.server --host 0.0.0.0 --port ${PORT:-7860}"]
