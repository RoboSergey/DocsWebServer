# DocsWebServer

A self-hosted web server for creating, editing, and sharing interactive HTML documents. Features an Obsidian-style single-page interface with folder support, a live-preview editor, full version history, and flexible sharing via public or token-protected links.

![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## Features

- **Obsidian-style SPA** — collapsible sidebar with folder tree; no full-page reloads
- **Folder support** — organize documents into nested folders; create, rename, and delete folders
- **Rich editor** — CodeMirror 5 with HTML syntax highlighting and 300ms debounced live preview
- **Dark / light theme** — automatic via `prefers-color-scheme`, accent color `#7b5ea7`
- **Version history** — every save creates a snapshot; restore any previous version in one click
- **File upload** — paste HTML or upload `.html` files directly
- **Flexible sharing** — public links or token-protected links with one-click copy
- **Zero-friction deployment** — single `docker compose up --build`, SQLite database, no external services

## Screenshots

| Sidebar + folder tree | Edit mode (full-area CodeMirror editor) | Version history |
|---|---|---|
| Navigate folders and documents | Live preview while you type | Restore any past version |

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | [FastAPI](https://fastapi.tiangolo.com/) + [SQLAlchemy async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) |
| Database | SQLite via [aiosqlite](https://aiosqlite.omnilib.dev/) |
| Frontend | Vanilla JS (SPA state machine), custom CSS variables |
| Editor | [CodeMirror 5](https://codemirror.net/5/) (loaded via CDN) |
| Runtime | Python 3.12, Uvicorn |
| Deployment | Docker + docker-compose |

---

## Quick Start

### With Docker (recommended)

```bash
git clone https://github.com/RoboSergey/DocsWebServer.git
cd DocsWebServer
docker compose up --build
```

Open **http://localhost:8000** in your browser.

Document data is stored in a named Docker volume (`doc_data`) and persists across container restarts.

### Local development

**Requirements:** Python 3.12+

```bash
git clone https://github.com/RoboSergey/DocsWebServer.git
cd DocsWebServer

# Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Run the server
uvicorn app.main:app --reload
```

Open **http://localhost:8000**.

The database is created automatically at `./documents.db` on first run.

---

## Usage

### Creating a folder or document

1. Use the **+** buttons in the sidebar to create a new folder or document
2. Folders and documents appear in the sidebar tree; click any document to open it

### Editing

- Click **Edit** in the toolbar to switch to edit mode — the full-area CodeMirror editor updates the preview live (300ms debounce)
- Press **Ctrl+S** (or **Cmd+S** on Mac) or click **Save** to persist a version
- Click **Upload** to replace the document content with a local `.html` file
- Click **Edit** again (or the close button) to return to preview-only mode

### Version history

- Click **History** in the editor toolbar to see all saved versions
- Click **Restore** next to any version to create a new version with that content

### Sharing

- Click **Share** in the editor toolbar to open the share panel
- **Public** — anyone with the link can view the document
- **Token-protected** — only people with the exact link (containing the token) can view it
- Click **New Token** to invalidate the old link and generate a new one
- Click **Copy Link** to copy the share URL to your clipboard

---

## Configuration

Configuration is via environment variables (or a `.env` file for local development):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_PATH` | `./documents.db` | Path to the SQLite database file |

In Docker, `DATABASE_PATH` is set to `/data/documents.db` and the `/data` directory is mounted as a named volume.

---

## API Reference

The full interactive API docs are available at **http://localhost:8000/docs** when the server is running.

### Documents

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/documents` | List documents (paginated) |
| `POST` | `/api/documents` | Create document |
| `GET` | `/api/documents/{id}` | Get document with latest content |
| `PUT` | `/api/documents/{id}` | Update title |
| `DELETE` | `/api/documents/{id}` | Soft delete |
| `PUT` | `/api/documents/{id}/content` | Save new version |
| `POST` | `/api/documents/{id}/upload` | Upload HTML file |

### Versions

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/documents/{id}/versions` | List all versions |
| `GET` | `/api/documents/{id}/versions/{num}` | Get specific version |
| `POST` | `/api/documents/{id}/versions/{num}/restore` | Restore version |

### Sharing

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/documents/{id}/sharing` | Get share settings |
| `PUT` | `/api/documents/{id}/sharing` | Update share mode |
| `POST` | `/api/documents/{id}/sharing/regenerate-token` | Generate new token |

---

## Project Structure

```
DocsWebServer/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── app/
│   ├── main.py              # FastAPI app, lifespan, router registration
│   ├── config.py            # Settings (Pydantic)
│   ├── database.py          # Async SQLAlchemy engine + session factory
│   ├── models.py            # Folder + Document + Version ORM models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── dependencies.py      # get_db session dependency
│   ├── routers/
│   │   ├── documents.py     # Document CRUD + content save + upload
│   │   ├── folders.py       # Folder CRUD
│   │   ├── versions.py      # Version history + restore
│   │   ├── sharing.py       # Share settings + token management
│   │   └── pages.py         # Server-rendered HTML pages (SPA shell + preview)
│   ├── services/
│   │   ├── document_service.py
│   │   ├── folder_service.py
│   │   └── version_service.py
│   ├── templates/           # Jinja2 HTML templates
│   └── static/
│       ├── css/style.css    # Obsidian-style theme + CSS variables
│       └── js/app.js        # SPA state machine
└── tests/
    ├── conftest.py           # In-memory SQLite fixtures
    ├── test_documents.py
    ├── test_versions.py
    └── test_sharing.py
```

---

## Development

### Running tests

```bash
pip install -e ".[test]"
pytest tests/ -v
```

### Running with auto-reload

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes and add tests
4. Ensure tests pass: `pytest tests/ -v`
5. Open a pull request

Please open an issue first for significant changes.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
