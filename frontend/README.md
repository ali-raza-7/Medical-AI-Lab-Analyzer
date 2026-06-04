## Medica AI Frontend (React + Vite + Tailwind)

This folder contains the React frontend described in the PRD.

### Setup

Network access to the npm registry is required.

```bash
cd frontend
npm install
npm run dev
```

### API

Expected backend:
- `POST /analyze` (FastAPI)

During local dev, configure `VITE_API_BASE_URL` in `.env` (example below):

```bash
VITE_API_BASE_URL=http://localhost:8000
```

