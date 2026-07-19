# Attribute Extractor Frontend

React/Vite frontend for the pilot backend.

## Run

From `frontend/`:

```bash
npm install
npm run dev
```

Default URLs:

```text
Frontend: http://localhost:5173
Backend:  http://localhost:8000
```

In dev mode, frontend calls backend through the Vite proxy:

```text
/api/* -> http://localhost:8000/*
```

To bypass the proxy and call another backend URL directly:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Docker: API host switching

Frontend image supports both build-time and runtime switching.

- Build-time (`VITE_API_BASE_URL` in JS bundle):

```bash
docker build -f frontend/Dockerfile --build-arg VITE_API_BASE_URL=/api .
```

- Runtime (`API_UPSTREAM` in nginx `/api` proxy):

```bash
docker run -e API_UPSTREAM=http://backend:8000/ ...
```

With `docker-compose.yml` you can pass:

- `FRONTEND_VITE_API_BASE_URL` (default: `/api`)
- `FRONTEND_API_UPSTREAM` (default: `http://backend:8000/`)
- `FRONTEND_PORT` (default: `5173`)
