# ProspectIQ

ProspectIQ is a research workspace for finding businesses and understanding which
digital services may help them. It collects business listings from OpenStreetMap,
checks websites that businesses have published, highlights possible opportunities,
and prepares reports for a person to review before contacting anyone.

It is a research assistant, not an automatic marketing system. It does not send
emails, WhatsApp messages, or calls.

## Who This Is For

This project is for an agency or researcher who wants to:

- Find mapped businesses in a selected area.
- Review each business's public contact details, location, and website.
- Identify possible needs such as a new or improved website, analytics, booking,
  customer management, inventory, or workflow automation.
- Organize follow-ups and export findings for review.

## What You Will See

ProspectIQ has seven main pages:

- **Dashboard**: a summary of discovered businesses, contacts, website checks, and
  charts.
- **Prospects**: search and filter business records, open their public website links,
  and view contact information.
- **Website Intelligence**: inspect website verification and quality-audit results.
- **Analytics**: compare business categories, areas, and website outcomes.
- **Reports**: download generated Word and Excel files.
- **Run Pipeline**: discover businesses in an area, check websites, and create reports.
- **Settings**: switch between light and dark appearance.

The recommended services are estimates based on the public listing and website
signals. Review the evidence and verify details yourself before acting on a lead.

## What the Reports Contain

The **Word report** is the detailed research document. It includes business profiles,
market summaries, website findings, priority information, and suggested outreach.

The **Excel outreach sheet** is intentionally brief. It contains only business name,
phone, WhatsApp, email, the problem or opportunity, and a short suggested solution.

## Run It on Windows

You need Python, Node.js with npm, and Git installed. Open PowerShell in the folder
that contains `api/`, `dashboard/`, `prospectiq/`, and `requirements.txt`.

### 1. Install the Python packages

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell says script execution is disabled when activating the environment,
you can run the Python commands using `\.venv\Scripts\python.exe` instead. Do not
commit the `.env` file. Edit it and replace the example `USER_AGENT` contact with a
working email address so public data services can identify the client.

### 2. Install the dashboard packages

Open a second PowerShell terminal in the project folder:

```powershell
cd dashboard
npm ci
```

### 3. Start the API and dashboard

In the first terminal, from the project folder, start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

In the second terminal, start the dashboard:

```powershell
cd dashboard
npm run dev
```

Open **http://localhost:6060** in your browser. The API's interactive reference is
at **http://localhost:8000/docs**. Keep both terminals open while you use the app.
Press `Ctrl+C` in each terminal when you are finished.

## First Use

1. Open **Run Pipeline** and choose a city or enter a custom bounding box.
2. Select **Discover this area** and wait for the background job to finish.
3. Open **Prospects** to search and filter the new records. A website missing from
   OpenStreetMap is not proof that the business has no website.
4. Run website checks for a reasonable number of businesses. Checks make requests
   to publicly listed websites, so they can take time.
5. Generate both reports from **Run Pipeline**, then download them in **Reports**.
6. Open a prospect's full profile to review the business description, contact details,
   service suggestions, and any available audit information.

## Discovery Coverage

Discovery uses the public OpenStreetMap Overpass service. The information available
depends on community mapping and may be incomplete or out of date. Presets are
provided for Nairobi, Mombasa, Kisumu, Kampala, and Dar es Salaam; custom areas use
south, west, north, east coordinates.

To protect the shared public service, each custom area is limited to 0.5 degrees per
side and 0.15 square degrees total. Collect a large region as multiple smaller
areas over multiple runs. A city or country-wide run is not guaranteed to return
every business.

## Privacy and Responsible Use

Only use publicly published business information. Respect source terms, opt-outs,
and applicable privacy and marketing laws. Verify contact details before outreach.
OpenStreetMap data is licensed under ODbL; review the attribution and redistribution
requirements at <https://www.openstreetmap.org/copyright>.

The current app has no user login or separation between agencies. Do not expose it
as a public multi-user service until authentication, tenant-specific data access,
rate limits, and job quotas have been added. CORS settings alone do not secure an API.

## Deploy the Project

For deployment to Render, or a Vercel dashboard with a separately hosted API, follow
the step-by-step guide in [deployment.md](deployment.md). The repository also
contains a Render Blueprint in `render.yaml`.
