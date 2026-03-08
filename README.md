# Admin Split Structure

This project is now split into:

- `admin_frontend` for Vue + Vite UI
- `admin_backend` for Flask API and database migrations

## Run Frontend

```bash
cd admin_frontend
npm run dev
```

## Run Backend

```bash
cd admin_backend
python3 server.py
```

## Production Procfile

Root `Procfile` now runs backend from `admin_backend`:

```bash
web: cd admin_backend && gunicorn server:app
```
