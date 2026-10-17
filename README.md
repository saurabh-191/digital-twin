---
title: digital-agent
app_file: app.py
sdk: gradio
sdk_version: 6.14.0
---
# Digital Agent

A modular Gradio digital twin with a ChatGPT-inspired interface: clean message bubbles,
responsive layout, dark/light theme support, suggested questions, copy buttons, and a
New chat control that clears conversation state. Request failures appear in an inline alert
with a dedicated dismiss button; dismissing it preserves the chat, and successful replies
automatically clear previous errors. It identifies itself as an AI.

## Run locally

Python 3.12+. From the repository root:

```powershell
.venv/Scripts/python.exe -m pip install -r digital-agent/requirements.txt
Copy-Item digital-agent/.env.example digital-agent/.env
# Edit digital-agent/.env and set OPEN_ROUTER_KEY.
.venv/Scripts/python.exe digital-agent/app.py
```

Open the local URL printed at startup (normally http://127.0.0.1:7860).
If the configured port is busy or reserved, local runs try the next 99 ports.
Set `PORT_STRICT=true` for fixed-port deployments; the Docker image enables this by default. The app does not open a browser or create a public share link.
Without the repository virtual environment, use `py` instead of `.venv/Scripts/python.exe`.
From inside `digital-agent`, `py -m digital_agent.app` also works.
A deployment environment variable takes precedence over local `.env`, then the repository `.env`.
This precedence changed from the initial version so deployed secrets cannot be overwritten by files.
The selected model must support tool calling. The original free model remains the default;
set `OPEN_ROUTER_MODEL` for your chosen provider model and availability requirements.

## Modules

| Module | Responsibility |
| --- | --- |
| `config.py` | Validated settings, environment loading, client timeouts and retries |
| `styles.py` | Theme, responsive CSS, suggested questions |
| `app.py` | UI construction, safe errors, queue limits, health endpoint, optional login |
| `agent.py` | Text history normalization, input/output limits, bounded tool loop |
| `tools.py` | Allowlisted tools, argument validation, recording actions |
| `storage.py` | Transactional SQLite contacts and unanswered questions |
| `notifications.py` | Optional Pushover alerts after successful persistence |
| `profile.py` | Profile documents and persona instructions |

Profile documents are in `data/`, copied from `1_foundations/twin`.
Example questions run only when clicked. Chat transcripts are not saved in browser storage
or in the application database. Provider-side handling is subject to your provider's policies.

## Reliability and storage

- Input size, history length, completion length, tool rounds, parallel tool calls, queue size,
  and concurrent requests are bounded. API timeout is configurable and retries are limited to one.
- Malformed/unknown tools receive error results. Storage errors are never reported as success.
- Contacts and unknown questions are saved before optional notification delivery. Notifications
  failing or not being configured do not discard saved requests.
- SQLite uses transactions, WAL, per-operation connections, and parameterized SQL. It supports
  concurrent threads/processes on one local host. Use a local persistent disk, not OneDrive or a
  network filesystem, for production. Use a shared database service before scaling across hosts.
- The default database is `runtime/agent.sqlite3`; override with an absolute `DATABASE_PATH`.
  Set `DATABASE_URL` to use external Postgres instead; configured Postgres failures never silently
  fall back to local storage. This is recommended for hosts with ephemeral filesystems.
  Existing `unknown_questions.json` files are left intact and are not imported automatically.
- Raw chat/provider errors and submitted contact details are not intentionally logged. Analytics,
  flagging, chat downloads, and file uploads are disabled. File paths containing profile data,
  environment files, and runtime data are blocked from Gradio file serving.

## Deployment

For free Render hosting, external Postgres, and GitHub Actions auto-deployment from `main`,
follow [DEPLOYMENT.md](DEPLOYMENT.md). The checked-in `render.yaml` and
`.github/workflows/ci-cd.yml` belong at the root of this standalone app repository.


```powershell
cd digital-agent
docker build -t digital-agent .
docker run --rm -p 127.0.0.1:7860:7860 --env-file .env -v digital-agent-data:/app/runtime digital-agent
```

The image runs as a non-root user and excludes environment files/runtime data from the build.
The named volume persists contacts/questions across container replacement.
`GET /healthz` is a liveness endpoint returning `{"status":"ok"}`; it does not call the model or
verify provider availability. A Docker health check uses it.

For a private instance, set both `APP_AUTH_USER` and `APP_AUTH_PASSWORD`. For a public portfolio,
leave both blank. Use HTTPS through your hosting platform or reverse proxy before exposing it.
Configure `HOST`, `PORT`, and `ROOT_PATH` for your host; Docker sets `HOST=0.0.0.0` internally.
The local default listens on loopback only. Gradio's hidden/private API visibility reduces API
surface but is not a substitute for authentication or gateway controls.

Before public launch, configure gateway rate limits, provider spending limits, and monitoring
appropriate to your traffic. Queue/concurrency limits are not per-visitor rate limits. Set a data
retention/deletion policy for saved email addresses and notes, restrict database/backup access,
and update the visitor privacy notice for your provider and use case. Back up the SQLite database
using SQLite's backup API; do not copy only the main file while WAL writes are active.
Prompt instructions reduce accidental disclosure but are not a security boundary. Tool actions
remain validated and allowlisted in code.

## Checks

From inside `digital-agent`:

```powershell
../.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Tests use mocks and temporary databases, with no live AI or Pushover calls. They cover history
normalization, limits, safe failures, bounded tool execution, malformed inputs, contact persistence,
concurrent writes, settings validation, and Gradio construction. A local HTTP smoke check verifies
page serving and `/healthz`. Docker build/run requires Docker and is a separate deployment check.

UI APIs follow the [Gradio ChatInterface documentation](https://www.gradio.app/docs/gradio/chatinterface)
and [custom CSS guidance](https://www.gradio.app/guides/custom-CSS-and-JS), verified against installed Gradio 6.14.0.
