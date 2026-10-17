# Free hosting and automatic deployment

This setup targets https://github.com/saurabh-191/digital-twin on `main`.
The app folder is a standalone Git repository: run Git commands inside `digital-agent`.
The old Hugging Face workflow draft is replaced by `.github/workflows/ci-cd.yml`.
No remote account, secret, service, or deployed application is created just by adding these files.

## Services and cost limits

Use Render **Free** for the Docker web service and Neon **Free** for external Postgres.
Free tiers have usage limits; this is suitable for a portfolio/demo, not an always-on SLA.
Render sleeps after 15 minutes idle, and waking up can take about a minute. Its free
filesystem is ephemeral. SQLite data would disappear on restart, sleep, or deployment;
set `DATABASE_URL` to keep contact requests and unknown questions in external Postgres.
Neon Free has compute/storage limits and can scale to zero. Free allowances and billing
terms can change; stay on Free plans and inspect account spending settings before launch.
The model provider is separate: hosting being free does not make all LLM requests free.
The configured default is a free model route, subject to its availability/rate limits.
No Pushover subscription or notification credentials are required to run the app.

Sources checked October 17, 2026:
- https://render.com/docs/free
- https://neon.com/pricing
- https://render.com/docs/deploy-hooks
- https://render.com/docs/blueprint-spec

## 1. Push this application to your GitHub repository

From inside `digital-agent`:

```powershell
git status
git add .
git diff --cached --stat
git commit -m "Add Render deployment and tested CI/CD pipeline"
git push origin main
```

Review profile documents before publishing. `.env`, SQLite data, and `.git` build context
are ignored. A previously present Hugging Face token was removed from `.env.example`;
revoke it if it was real, especially if committed. Removing it does not invalidate it
or erase previous Git history. Do not put replacement credentials in committed files.
The first Actions run can fail at the deployment step until the hook secret is configured.

## 2. Create a free Neon database

Create a Neon account/project on the Free plan. Select a region near the Render service.
Copy the provided Postgres connection string, including `sslmode=require` (and any other
parameters Neon provides). Keep it secret. This app creates its contacts/questions tables
on startup, so the database role needs permission to create tables in its schema.
Existing local SQLite rows are not migrated automatically; retain a backup if needed.

## 3. Create the Render service

1. Connect GitHub in Render and authorize access to `saurabh-191/digital-twin`.
2. Choose **New > Blueprint**, select that repository and `main`, and use `render.yaml`.
3. Confirm the web service plan is **Free**. The Blueprint deliberately creates no paid disk/database.
4. Enter the prompted environment secrets:
   - `OPEN_ROUTER_KEY`: your OpenRouter key.
   - `DATABASE_URL`: the Neon connection string.
5. Create/apply the Blueprint. The initial deployment builds the Docker image.
6. Open the assigned `https://...onrender.com` URL. Check `/healthz` for `{"status":"ok"}`.

If you create a Web Service manually instead, use Docker, branch `main`, repo root as
build context, `Dockerfile`, Free plan, health check `/healthz`, and **Auto-Deploy: Off**.
Set `HOST=0.0.0.0`, `PORT=7860`, `PORT_STRICT=true`, `CHAT_CONCURRENCY=2`, and the two secrets above.
Do not turn auto-deploy-on-commit on: that would bypass the test gate and cause duplicate builds.
Optional Render secrets: `PUSHOVER_USER`, `PUSHOVER_TOKEN`, and both `APP_AUTH_USER` /
`APP_AUTH_PASSWORD` for a private app. Never put these in GitHub workflow YAML.

## 4. Connect GitHub Actions to Render

1. In Render service **Settings**, copy its **Deploy Hook** URL.
2. In GitHub repo **Settings > Secrets and variables > Actions**, create a repository secret:
   `RENDER_DEPLOY_HOOK_URL` with that entire URL as its value.
3. GitHub **Settings > Environments**: create `production`, restrict deployment branches to
   `main`, and leave required reviewers off if you want unattended deployment.
4. In the **Actions** tab, select **Test and deploy production** and run it on `main`,
   or push a new commit to `main`.

No model/database production secrets are needed in GitHub Actions. Tests use mocks, a
disposable Postgres service, and a placeholder API key for container startup.

## What happens on changes

Pull request to `main` -> Python tests + Postgres integration + Docker build + HTTP smoke check.
Push/merge to `main` -> the same checks -> deploy hook requests the exact tested commit.
Other branches do not deploy. To deploy from a different branch, update both branch lists,
the deploy job condition, `render.yaml`'s branch, and GitHub's production environment restriction.

The hook request is not proof of a healthy rollout. GitHub confirms Render accepted/queued
it; watch Render's deployment status and `/healthz` for the live result. A failed test blocks
that commit's deployment. The first Blueprint deployment is bootstrapping and precedes this gate.
Blueprint configuration changes may independently cause Render to update affected resources.
Rollback a bad app change by reverting its Git commit and pushing the revert through CI.

## Validation and operations

From the app root:

```powershell
../.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Standalone environments can use `python` instead. Postgres integration tests skip locally
unless `TEST_DATABASE_URL` points to a disposable test database. CI supplies one automatically.
Production contacts/unknown questions live in Postgres when `DATABASE_URL` is set; chat
transcripts are not stored by this app. Set privacy/retention policy and database access rules
for the saved contact data. Back up your database and monitor free-tier usage/provider quotas.
GitHub Actions public-repository standard runners are free; private repos use included quotas.


## Database startup errors

Use only the complete URL from Neon Connect as Render's `DATABASE_URL`, with no `psql`
prefix, surrounding quotes, or `DATABASE_URL=` prefix. Keep its SSL query parameters.
The app applies statement timeout inside transactions, not as a connection startup
option, for compatibility with poolers. Startup errors report a safe category such as
authentication, TLS, timeout, or permissions without printing server text/credentials.
If deployment fails, share only that safe error message, not your connection string.
