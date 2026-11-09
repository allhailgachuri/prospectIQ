# Deploying ProspectIQ

This guide explains how to publish ProspectIQ for the first time. The project has
two parts that need to run online:

- The **dashboard** is the React website that people open in a browser.
- The **API** is the Python service that searches OpenStreetMap, reads and writes
  business records, checks websites, and creates reports.

The recommended beginner setup is the Render Blueprint in `render.yaml`. It creates
both services and a persistent disk for the SQLite database. Another option is to
host the dashboard on Vercel and the API on Render.

## Before You Begin

You will need:

- A GitHub account and this project pushed to a GitHub repository.
- A Render account for the API and persistent database disk.
- Optionally, a Vercel account if you prefer to host the dashboard there.
- A working contact email for the application's public-data request identity.

Do not upload `.env`, local database files, generated reports, or exports. The
repository `.gitignore` excludes these local files. Keep API credentials and other
secrets in the hosting provider's environment-variable settings, never in source
code or `VITE_*` variables (frontend variables are visible in the browser).

## Option A: Deploy Both Services with Render

### 1. Push the project to GitHub

Create an empty GitHub repository, then from the project root run the initial push
commands shown below. Skip `git init` and `git remote add` if you have already done
those steps. Review `git status` before committing and confirm `.env`, local data,
and generated reports are not staged.

```powershell
git init
git add .
git commit -m "Created ProspectIQ"
git branch -M main
git remote add origin https://github.com/allhailgachuri/prospectIQ.git
git push -u origin main
```

For later updates, use `git add .`, `git commit -m "Describe your change"`, and
`git push`; do not repeat `git init` or `git remote add`.

### 2. Create the Render services

1. Sign in to Render and choose **New** then **Blueprint**.
2. Connect the GitHub repository containing ProspectIQ.
3. Render reads `render.yaml` from the repository root and shows the services it
   will create. Review the names and settings before confirming.
4. When asked for `USER_AGENT`, enter a descriptive client name and a working email
   address, for example `ProspectIQ/1.0 (research; contact: you@example.com)`.
5. Confirm the API service, static dashboard service, and `prospectiq-data` disk.
   A persistent disk may incur a charge. Keep the disk attached to one API instance
   because this deployment uses SQLite.
6. Wait for both deployments to finish. The first build can take several minutes.

### 3. Check environment settings

The Blueprint sets these values for the API:

- `DATABASE_PATH=/var/data/prospectiq.db` so records survive service restarts.
- `FRONTEND_ORIGINS=https://prospectiq-dashboard.onrender.com` so the dashboard
  origin is allowed to call the API.
- `USER_AGENT` is supplied privately when Render prompts for it.

The dashboard build uses `VITE_API_URL=https://prospectiq-api.onrender.com/api`.
If you rename either service or attach a custom domain, update the corresponding
URL and allowed origin in the Render service settings, then redeploy.

### 4. Verify the deployment

1. Open `https://prospectiq-api.onrender.com/docs`. The FastAPI documentation page
   should load.
2. Open `https://prospectiq-dashboard.onrender.com`. The dashboard should load and
   show data after its API request completes.
3. Open **Prospects**, then verify search and filters work.
4. Open **Run Pipeline** and check the available area presets. Start with a small
   area because the public Overpass service can be busy.
5. Generate a report and confirm both Word and Excel files appear under **Reports**.

If the dashboard loads but shows no data, check `VITE_API_URL`, the API service
logs, and `FRONTEND_ORIGINS`. The allowed origin must exactly match the browser's
dashboard URL, including `https://` and excluding any path. CORS is not a security
or authentication mechanism.

## Option B: Vercel Dashboard and Render API

Use this option if you want Vercel to host the static React dashboard. Vercel does
not run this project's FastAPI service as a static Vite build, so the API still
needs to be deployed on Render or another Python-capable host.

### 1. Deploy the API

Create the `prospectiq-api` web service on Render from the repository root:

- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- Persistent disk mount: `/var/data`
- `DATABASE_PATH`: `/var/data/prospectiq.db`
- `USER_AGENT`: a private value with a working contact email

Set `FRONTEND_ORIGINS` after Vercel creates the dashboard URL. Enter only the
exact dashboard origin, such as `https://prospect-iq.vercel.app`.

### 2. Deploy the dashboard

1. In Vercel, import the same GitHub repository.
2. Set the project **Root Directory** to `dashboard`.
3. Select the Vite preset, build command `npm run build`, and output directory `dist`.
4. Add the build-time environment variable `VITE_API_URL` with the full API URL
   ending in `/api`, for example `https://prospectiq-api.onrender.com/api`.
5. Deploy the dashboard. The `dashboard/vercel.json` file routes browser page
   refreshes back to the React app.
6. Copy the resulting Vercel origin into the Render API's `FRONTEND_ORIGINS`, save,
   and redeploy the API.

If you use Vercel preview deployments, add only the preview origins you intend to
allow. Do not use a wildcard CORS origin for a production deployment.

## Updating the Live Website

After changing the code, from the project root:

```powershell
git status
git add .
git commit -m "Describe the update"
git push
```

Render and Vercel normally rebuild automatically after a push to the connected
branch. Check each provider's deployment log if a build fails.

## Local Build Checks

Before pushing an update, you can run:

```powershell
py -m pytest -q
cd dashboard
npm ci
npm run build
```

Run the API from the project root and the Vite dashboard from `dashboard/` when
testing locally. The dashboard uses port `6060`; the API uses port `8000`.

## Important Product Limits

- Discovery uses OpenStreetMap's shared public Overpass service. Coverage is not
  exhaustive and large or repeated requests may be throttled.
- A custom discovery area is limited to 0.5 degrees per side and 0.15 square
  degrees overall. Collect larger regions as multiple smaller areas.
- A website not listed in OpenStreetMap may still exist. Website checks are
  lightweight and check only public homepages.
- The current API has no login or agency-specific data separation. Do not share it
  publicly as a multi-user product until authentication, tenant isolation, rate
  limits, and job quotas are implemented.
- SQLite on a persistent Render disk is appropriate for a small, single-instance
  deployment. A larger multi-user service should migrate to a managed database.
- Attribute OpenStreetMap and follow ODbL terms when redistributing derived data.
  Follow applicable privacy, marketing, and opt-out requirements before outreach.
