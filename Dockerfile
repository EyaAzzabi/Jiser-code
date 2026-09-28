# JISER · image de production : l'API FastAPI sert aussi l'interface React compilée (un seul service).
# Construite par Render (render.yaml) ou n'importe quel hébergeur Docker. Les secrets sont fournis en
# variables d'environnement par l'hébergeur : aucun fichier .env n'entre dans l'image.

# 1. Interface React
FROM node:20-slim AS interface
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# 2. API Python
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN useradd -m -u 1000 jiser
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt
COPY --chown=jiser backend backend
COPY --chown=jiser data data
COPY --chown=jiser models models
COPY --chown=jiser scripts scripts
COPY --from=interface --chown=jiser /app/frontend/dist frontend/dist
USER jiser
EXPOSE 7860
# the host sets PORT (Render: 10000); 7860 otherwise
CMD ["sh", "-c", "python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-7860} --proxy-headers --forwarded-allow-ips '*'"]
