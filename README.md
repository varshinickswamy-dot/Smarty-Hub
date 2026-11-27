# Smarty Hub

Smarty Hub is a Flask web application that brings student guidance and study
tools together in one place. Students can explore career paths, get rule-based
study and career suggestions, create a PDF resume, and use a study timer.

## Problem statement

Students often need to switch between separate resources for career guidance,
resume preparation, and study planning. Smarty Hub provides a simple, single
web application for these common tasks.

## Objectives

- Provide a straightforward student account and sign-in workflow.
- Make career and study guidance accessible through the web interface.
- Let students generate a downloadable resume PDF.
- Offer a focused study timer with Pomodoro and stopwatch modes.
- Keep personal data and deployment secrets out of the public source repository.

## Key features

- Account registration, login, logout, and authenticated pages.
- Stream- and marks-based career recommendations.
- Rule-based AI Counselor responses for career and study topics.
- Resume PDF generation with optional profile photo.
- Responsive layouts for phones, tablets, and desktops, with touch-sized controls and safe-area support.
- Pomodoro and stopwatch study timer.
- Admin view of registered users (requires an account whose `role` is `admin`).

Resume PDFs are sent as named attachments. On iOS and some Android browsers,
the PDF may open in a preview first; use the browser's share or download menu
to save it to the device.

## Technology stack

- Python 3.12
- Flask, Flask-Login, and Flask-SQLAlchemy
- SQLite by default; PostgreSQL can be configured with `DATABASE_URL`
- ReportLab and Pillow for resume PDF generation and image validation
- scikit-learn and joblib for the standalone career-model training script
- Bootstrap 5.3.2 and vanilla JavaScript in the templates

## Architecture

The application is a server-rendered Flask monolith. `app.py` defines the web
routes and application configuration, `models.py` defines the SQLAlchemy
models, and templates render the pages. The chat route delegates to the
rule-based responder in `ai/chatbot.py`. Resume submissions are stored in the
database and rendered as PDF files with ReportLab. The model training script
and saved model are present under `ai/`; the current career recommendation
route uses its own rule-based logic and does not load that model.

## Folder structure

```text
SmartyHub/
├── ai/
│   ├── career_model.pkl
│   ├── chatbot.py
│   └── train.py
├── reports/              # Generated resume PDFs (kept out of Git)
├── static/
│   ├── css/
│   └── js/
├── templates/            # Flask/Jinja pages
├── uploads/              # User-uploaded profile photos (kept out of Git)
├── app.py
├── models.py
├── requirements.txt
├── .env.example
└── README.md
```

The local `data.db`, `instance/`, virtual environments, generated reports, and
user uploads are intentionally ignored by Git. The workspace currently
contains existing local database and generated files; review them locally as
needed, but do not force-add user records, resume PDFs, or uploads to a public
repository.

## Installation

Requires Python 3.12. From the project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

On macOS or Linux, use `python3.12 -m venv .venv`, activate with
`source .venv/bin/activate`, and copy `.env.example` to `.env`.

## Environment configuration

The app loads `.env` when present. `SECRET_KEY` is generated ephemerally for
local development if it is not set; set a persistent, unique value for any
deployed instance. When `APP_ENV=production`, the app refuses to start without
`SECRET_KEY`. Do not commit `.env`.

| Variable | Required | Description |
| --- | --- | --- |
| `APP_ENV` | No | Set to `production` for production cookie settings and startup checks. Defaults to development. |
| `SECRET_KEY` | Production | Secret used to sign Flask sessions. Generate a value with `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `DATABASE_URL` | No | SQLAlchemy database URL. If omitted, the app uses the project-local `data.db` SQLite file. PostgreSQL URLs can use `postgresql+psycopg://...`. |
| `FLASK_DEBUG` | No | Set to `true` only for local debugging. Debug mode is off by default. |

For PostgreSQL, configure `DATABASE_URL` in the environment with credentials
appropriate to your deployment. Do not put live credentials in `.env.example`
or source control.

## Run locally

With the virtual environment activated and `.env` configured:

```powershell
python app.py
```

Open <http://127.0.0.1:5000>. The app creates its database tables on startup.
Register through the application to create a student account. To grant admin
access, update that user's `role` to `admin` in a trusted local database
administration workflow.

## Routes and API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET`, `POST` | `/` | Sign in |
| `GET`, `POST` | `/register` | Create an account |
| `GET` | `/logout` | Sign out |
| `GET` | `/dashboard` | Authenticated home page |
| `GET`, `POST` | `/career` | Career recommendations |
| `GET` | `/chatbot` | Authenticated counselor page |
| `POST` | `/chat` | Authenticated JSON chat endpoint |
| `GET`, `POST` | `/resume` | Authenticated resume form and PDF generation |
| `GET` | `/timetable` | Authenticated study timer |
| `GET` | `/admin` | Admin-only user listing |

The chat endpoint accepts JSON such as `{"msg":"What careers are in science?"}`
and returns `{"reply":"..."}`. Invalid JSON or messages return a JSON error
with HTTP 400. It requires an authenticated session.

## Deployment

Deploy on a supported Linux host with Python 3.12:

1. Install the packages from `requirements.txt`.
2. Set `APP_ENV=production`, a strong persistent `SECRET_KEY`, and a production
   `DATABASE_URL` in the hosting platform's secret/environment configuration.
3. Ensure the service can write to the configured SQLite database and to the
   `uploads/` and `reports/` directories, or mount suitable persistent storage.
4. Start the WSGI server, for example:

   ```sh
   gunicorn --bind 0.0.0.0:${PORT:-8000} app:app
   ```

Use PostgreSQL rather than a local SQLite file for multi-instance deployments.
Terminate TLS at the hosting platform or reverse proxy. The app does not
include database migrations, automated admin provisioning, or persistent
object-storage integration; plan these before a production rollout.

## Tests

Run the application smoke tests with:

```powershell
python -m unittest discover -s tests -v
```

## Screenshots

Add current screenshots here before publishing:

<!-- Replace these placeholders with screenshots captured from the running app. -->
- Login: `docs/screenshots/login.png`
- Dashboard: `docs/screenshots/dashboard.png`
- Career Analyzer: `docs/screenshots/career.png`
- Resume Builder: `docs/screenshots/resume.png`
- Study Timer: `docs/screenshots/timer.png`

## Future enhancements

- Add CSRF protection, password reset, and account lifecycle controls.
- Add database migrations and automated deployment checks.
- Add rate limiting and structured production logging.
- Integrate the saved career model into the career workflow, or remove it if no
  longer needed.
- Add user-facing tests for validation, accessibility, and browser behavior.
- Replace external CDN assets with versioned local assets if offline support is
  required.

## Contributing

1. Create a focused branch for your change.
2. Preserve existing workflows and avoid committing environment files, local
   databases, uploads, generated resumes, or credentials.
3. Install dependencies and run the test suite before opening a pull request.
4. Describe the behavior changed and include relevant screenshots for UI work.

## License

No license has been selected for this project. Choose and add a license before
publishing; MIT is a common permissive option if that matches the project
owner's intent. Without a license, normal copyright restrictions apply.
