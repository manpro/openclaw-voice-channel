# Stage 1: Build React frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + nginx
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    ffmpeg \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Generate self-signed certificate as fallback (overridden by Tailscale cert volume mount)
RUN openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout /etc/ssl/private/tailscale.key \
    -out /etc/ssl/certs/tailscale.crt \
    -subj "/CN=whisper-app"

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./requirements-backend.txt
COPY batch_worker/requirements.txt ./requirements-batch.txt
RUN pip install --no-cache-dir -r requirements-backend.txt -r requirements-batch.txt

# Optional: install diarization dependencies (heavy: ~2-3GB)
ARG INSTALL_DIARIZATION=false
COPY batch_worker/requirements-diarization.txt ./requirements-diarization.txt
RUN if [ "$INSTALL_DIARIZATION" = "true" ]; then \
        pip install --no-cache-dir -r requirements-diarization.txt; \
    fi

# Copy backend
COPY backend/ ./backend/

# Copy batch worker
COPY batch_worker/ ./batch_worker/

# Copy frontend build
COPY --from=frontend-build /app/frontend/dist /app/static

# Copy config files
COPY nginx.conf /etc/nginx/sites-available/default
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create transcriptions directory
RUN mkdir -p /app/transcriptions

EXPOSE 443

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
