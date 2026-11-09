# ProspectIQ Deployment Guide

ProspectIQ is a React/Vite dashboard backed by a FastAPI service and SQLite. The
dashboard is static; the API is a long-running Python service. Deploy them as two
services. `render.yaml` defines both services and a persistent disk for SQLite.

## Recommended: Render Blueprint

1. Push the repository to a Git provider and create a Render Blueprint from the
   repository root (the directory containing `render.yaml`, `api/`, and `dashboard/`).
2. Set the required `USER_AGENT` secret to identify your research client and a
   working contact email.
3. Review the generated API and dashboard service URLs. The default names in the
   Blueprint are `prospectiq-api` and `prospectiq-dashboard`.
4. Confirm the dashboard's `VITE_API_URL` is the API URL plus `/api`, and the API's
   `FRONTEND_ORIGINS` exactly includes the dashboard origin.
5. Keep the API disk mounted at `/var/data`; `DATABASE_PATH` must point to
   `/var/data/prospectiq.db`. SQLite files stored outside a persistent disk can be
   lost when a hosted instance is replaced.
6. Deploy both services, then verify the API at `/docs` and load the dashboard.

The public Overpass API is shared infrastructure and may throttle or reject large
queries. Discover bounded areas repeatedly; do not treat one request as complete
country or continent coverage. Website checks are also sequential and can take time.

## Vercel Dashboard + Render API

Vercel can host the frontend but not this FastAPI process as a static Vite build.
Keep the API on Render (or another Python-capable host) and deploy only the
`dashboard/` directory to Vercel:

- Framework preset: Vite
- Root directory: `dashboard`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_URL=https://YOUR-API-HOST/api`

The `dashboard/vercel.json` rewrite sends client-side routes back to `index.html`.
On the API service, set `FRONTEND_ORIGINS` to the exact Vercel deployment origin
(include a preview origin only when needed) and redeploy the API. Do not use `*`
for production CORS.

## Local Development

From the repository root, install the Python requirements and dashboard packages,
then run the API and frontend in separate terminals:

```powershell
py -m pip install -r requirements.txt
cd dashboard
npm ci
npm run dev -- --host 0.0.0.0 --port 6060
```

Run the API from the repository root in another terminal:

```powershell
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The dashboard is available at `http://localhost:6060`; Vite proxies `/api` to
`http://localhost:8000`. Configure `.env` from `.env.example` before discovery.

## Deployment Hygiene

- The API currently has no user authentication or tenant isolation. Before sharing
  a public deployment as a multi-user product, add login, per-tenant data access,
  rate limits, and job quotas. Do not treat CORS as access control.
- Keep `dashboard/node_modules/`, `dashboard/dist/`, and `.vercel/` out of Git.
- Let Vercel and Render build from source; never upload or commit prebuilt hosting
  output as a substitute for the production build.
- Verify `dashboard/dist/index.html` exists after `npm run build`.
- Check the API `/docs`, the browser Network panel, and CORS origins if requests fail.
- Do not commit `.env`, public contact datasets, generated reports, or database files.
- Attribute OpenStreetMap and follow ODbL obligations when redistributing derived
  datasets. Respect source terms and applicable privacy and outreach laws.
