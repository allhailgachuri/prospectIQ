# ProspectIQ API: Free Deployment Guide

Your dashboard is already deployed at <https://prospecttiq.vercel.app/>. The remaining piece is the Python API that supplies dashboard data, discovers businesses, checks websites, and generates reports.

This guide uses a **Hugging Face Docker Space** for the API's free CPU tier. It is intended to avoid Render's paid persistent disk and should not require adding a payment card when you choose the free hardware. Hosting providers can change their eligibility and billing rules; if the setup screen asks you to select paid hardware or enter payment details, stop and verify that the Space is set to the free CPU tier. Do not select a paid upgrade.

## Important Free-Tier Limitation

The API uses SQLite. The free Space's local filesystem is temporary, not persistent storage. The Dockerfile stores its database at `/tmp/prospectiq.db`; that database and generated reports can be erased when the Space restarts, rebuilds, or is recycled. This setup is for trying the API and using it with data you can afford to re-create. It does **not** make saved prospects durable across restarts.

You can download Word and Excel reports after generating them, but don't treat the free container as a permanent archive. For durable always-available storage, a persistent disk or managed database is needed; those options may have charges or account requirements. The current project does not yet support moving its SQLite database to a hosted PostgreSQL service just by changing one setting.

## What You Need

- Your GitHub repository: <https://github.com/allhailgachuri/prospectIQ>
- Your deployed dashboard: <https://prospecttiq.vercel.app/>
- A Hugging Face account.
- A working contact email for the API's `USER_AGENT` identity.
- Git installed on your computer.

You do not need to redeploy the dashboard source to a different host. You will need to set one Vercel environment variable and redeploy its production build after the API is ready, because Vite embeds that setting during the build.

## Part 1: Create the Free API Space

1. Sign in to Hugging Face at <https://huggingface.co/>.
2. Open **Spaces** and choose **Create new Space**.
3. Choose a repository name such as `prospectiq-api`.
4. Choose **Docker** as the Space SDK. The repository already contains a root-level `Dockerfile` configured to run FastAPI on port `7860`.
5. Choose **Public** visibility so the Vercel site can call the API without Hugging Face login. Remember that this also means the API endpoints are publicly reachable. See the security warning below.
6. Select the free CPU/basic hardware option. Do not select a paid GPU or upgrade.
7. Create the Space. Hugging Face will show you its Git URL, similar to:
   `https://huggingface.co/spaces/YOUR_HF_USERNAME/prospectiq-api`.

If the Space creation flow asks for a payment card even though free CPU hardware is selected, do not continue with a paid option. Check Hugging Face's current free-tier/account requirements first; these policies can change.

## Part 2: Push This Project to the Space

The existing Git repository already has GitHub as its `origin`. Add the Hugging Face Space as a second remote, replacing `YOUR_HF_USERNAME` with your Hugging Face username. Run these commands from the project root (the folder containing `Dockerfile`, `api/`, and `prospectiq/`):

```powershell
git status
git remote add hf https://huggingface.co/spaces/YOUR_HF_USERNAME/prospectiq-api
git push hf main
```

If Git says the `hf` remote already exists, don't add it again. Check it with:

```powershell
git remote -v
```

When Git asks you to authenticate, use your Hugging Face username and a Hugging Face **write** access token as the password. Create the token in Hugging Face account settings, grant only the repository-write permission needed, and enter it directly in the terminal credential prompt. Do not put the token in a command, source file, README, or Vercel variable. If you haven't committed the latest Docker files yet, commit and push them to GitHub first, then push the same `main` branch to the `hf` remote.

Hugging Face will build the Docker image after the push. In the Space's **Logs** tab, wait for the build to finish and for the app to start. The Dockerfile installs `requirements.txt`, copies only the Python API and engine, and starts Uvicorn on port `7860`.

## Part 3: Set the API Environment Variables

In the Space, open **Settings** and find the variables/secrets section. Add:

| Name               | Value                                                          |
| ------------------ | -------------------------------------------------------------- |
| `USER_AGENT`       | `ProspectIQ/1.0 (business research; contact: YOUR_REAL_EMAIL)` |
| `FRONTEND_ORIGINS` | `https://prospecttiq.vercel.app`                               |
| `DATABASE_PATH`    | `/tmp/prospectiq.db`                                           |

Replace `YOUR_REAL_EMAIL` with an email address you can access. `USER_AGENT` identifies requests made to public data services; it is not a password. Add these values as Space variables/secrets, not in Git. The Dockerfile already defaults `DATABASE_PATH` to `/tmp/prospectiq.db`, but setting it explicitly in the Space makes the temporary-storage behavior clear. Saving environment variables usually triggers a restart or rebuild.

`FRONTEND_ORIGINS` must exactly match your Vercel site's origin: `https://prospecttiq.vercel.app`. Do not add a trailing slash or a page path. CORS controls which browser origins may read API responses; it is not login or authentication.

## Part 4: Verify the API

Open the Space page and copy its public app URL. Hugging Face commonly displays an address ending in `.hf.space`; use the exact URL shown for your Space. For example, if its app URL is `https://YOUR_SPACE_HOST.hf.space`, check:

```text
https://YOUR_SPACE_HOST.hf.space/docs
https://YOUR_SPACE_HOST.hf.space/api/stats
```

The first should show FastAPI documentation. The second should return JSON containing statistics such as `total`, `by_category`, and `by_neighbourhood`. A new free Space starts with a new, empty SQLite database, so `total: 0` is expected until you run discovery. A sleeping free Space can take a little while to wake on the first request.

If `/docs` does not load, inspect the Space's **Logs** for image-build or startup errors. If `/docs` works but `/api/stats` does not return JSON, check the API logs and confirm that the Docker Space is running the latest `main` branch.

## Part 5: Connect the Existing Vercel Dashboard

1. In Vercel, open the project that serves `https://prospecttiq.vercel.app/`.
2. Open **Settings → Environment Variables**.
3. Add `VITE_API_URL` for the **Production** environment. Set its value to the exact Space app URL followed by `/api`, for example:
   ```text
   https://YOUR_SPACE_HOST.hf.space/api
   ```
   Do not include `/stats` at the end; the dashboard adds API paths itself.
4. Save the variable.
5. Open **Deployments**, choose the latest production deployment, and redeploy it so the Vite build receives the new variable. Alternatively, push a new commit to the connected GitHub branch after setting the variable; Vercel will build again.
6. Visit <https://prospecttiq.vercel.app/> and reload. The dashboard should show API statistics. Then try Prospects and the API-backed pages.

The frontend setting is named `VITE_API_URL` because this project uses Vite. It is public in the downloaded browser code, so never put passwords or private API tokens in it.

## Troubleshooting

**Dashboard says the API response is invalid.** Open `/api/stats` directly using the Space URL. If it doesn't return JSON, fix the Space first. If it does return JSON, confirm Vercel's `VITE_API_URL` equals the Space URL ending in `/api`, and redeploy Vercel.

**Browser reports a CORS error.** In Space settings, set `FRONTEND_ORIGINS` to exactly `https://prospecttiq.vercel.app`, save, wait for the API to restart, and reload the dashboard. Don't put the API URL in `FRONTEND_ORIGINS`; that setting is for the frontend origin.

**First API request is slow.** A free Space may be sleeping when idle. Wait for it to wake, then reload. This may happen again after periods of inactivity.

**Prospects disappear.** That is the expected limitation of temporary free storage. The SQLite database is in `/tmp` and can be reset by a restart, rebuild, or host recycling. Download reports you need to keep. To retain data across restarts, choose a persistent storage service and budget for any associated cost; do not assume the free Space's container filesystem is permanent.

**The API is public.** Public visibility allows the Vercel browser to call it without Hugging Face login, but anyone who finds its URL may also call its endpoints. This project's API currently has no user authentication, tenant isolation, or request quotas. Do not store confidential client data or treat this as a secure multi-agency service. Add authentication and abuse protection before inviting other users or relying on it for sensitive business workflows.

## Future Updates

When you change the API code, push the commit to GitHub and then push it to the Hugging Face Space remote so the API image rebuilds:

```powershell
git add .
git commit -m "Describe the API update"
git push origin main
git push hf main
```

When you change only the dashboard, pushing to GitHub should trigger Vercel's connected deployment. If you change Vercel environment variables, redeploy so the new values are compiled into the frontend.
