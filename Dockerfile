# ---- Stage 1: build Vue frontend ----
FROM node:22-slim AS frontend
WORKDIR /build
COPY admin_frontend/package.json admin_frontend/package-lock.json ./
RUN npm ci
COPY admin_frontend/ ./
RUN npm run build

# ---- Stage 2: Python backend (gunicorn) ----
FROM python:3.12-slim
WORKDIR /app
COPY admin_backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY admin_backend/ ./
# pdf_bp.py resolves the SPA dist four levels up from backend/routes/uploads,
# which lands on /admin_frontend/dist inside the container.
COPY --from=frontend /build/dist /admin_frontend/dist
EXPOSE 5001
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--timeout", "300", "--access-logfile", "-", "server:app"]
