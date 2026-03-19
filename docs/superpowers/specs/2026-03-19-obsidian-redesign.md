# Design: Obsidian-style UI Redesign + Folder Support

**Date:** 2026-03-19
**Status:** Approved

---

## Overview

Redesign the Document Web Server UI from a multi-page app into a single-page Obsidian-inspired interface: persistent left sidebar with folder tree, full-area preview pane, toggle to full-area HTML editor. Also fixes two existing bugs (CodeMirror not initialising, file upload not working) by replacing the broken CodeMirror 6 ESM CDN approach with CodeMirror 5 from cdnjs.

---

## Goals

1. Obsidian-like single-page experience — no full page navigations
2. Folders — documents organised into a nested folder hierarchy
3. Full-area preview by default; single Edit button toggles to full-area CodeMirror editor
4. System-aware dark/light theme
5. Fix: CodeMirror editor not typeable (broken ESM imports)
6. Fix: File upload silently does nothing (same root cause)

---

## Database Changes

### New table: `folders`

```sql
CREATE TABLE folders (
    id         TEXT PRIMARY KEY,        -- UUID4
    name       TEXT NOT NULL,
    parent_id  TEXT REFERENCES folders(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- `parent_id = NULL` → top-level folder (child of root)
- Nested folders: `parent_id` points to parent folder

### Modified table: `documents`

Add column:

```sql
ALTER TABLE documents ADD COLUMN folder_id TEXT REFERENCES folders(id) ON DELETE SET NULL;
```

- `folder_id = NULL` → document lives at root (no folder)
- SQLAlchemy migration: handled in `create_tables()` via `checkfirst=True`

---

## API Changes

### New router: `app/routers/folders.py`

```
GET    /api/folders               → FolderTree (nested list)
POST   /api/folders               → create {name, parent_id?} → FolderResponse
PUT    /api/folders/{id}          → rename {name} → FolderResponse
DELETE /api/folders/{id}          → delete; children/docs moved to folder's parent (or root)
```

### Updated: `app/routers/documents.py`

- `POST /api/documents` — accepts optional `folder_id`
- `GET /api/documents` — accepts optional `?folder_id=` query param (null = root)
- New: `PUT /api/documents/{id}/move` — `{folder_id: str | null}` moves doc to folder

### New schemas

```python
class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: str | None = None

class FolderRename(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)

class FolderResponse(BaseModel):
    id: str
    name: str
    parent_id: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class FolderTree(FolderResponse):
    children: list["FolderTree"] = []
    documents: list[DocumentResponse] = []
```

### New service: `app/services/folder_service.py`

- `get_folder_tree(db)` → nested FolderTree (recursive)
- `create_folder(db, name, parent_id)` → Folder
- `rename_folder(db, id, name)` → Folder | None
- `delete_folder(db, id)` → bool (reassigns children/docs to parent first)

---

## Frontend Architecture

### Single page at `/`

The existing multi-page routes (`/edit/{id}`, `/history/{id}`) are **removed from the main navigation**. The `pages.py` router keeps `/preview/{id}` and `/preview/{id}/raw` for external share links. The main app lives entirely at `/`.

### Layout

```
┌─────────────────┬────────────────────────────────────────┐
│  SIDEBAR 260px  │  TOOLBAR (doc title + action buttons)  │
│                 ├────────────────────────────────────────┤
│  [+ Doc] [+ 📁] │                                        │
│                 │   MAIN AREA (full height)              │
│  ▼ 📁 Work      │                                        │
│    📄 Notes     │   Mode: preview → <iframe srcdoc>      │
│    📄 Report    │   Mode: edit   → CodeMirror editor     │
│  ▶ 📁 Personal  │                                        │
│  📄 Root Doc    │   Empty state when no doc selected     │
│                 │                                        │
└─────────────────┴────────────────────────────────────────┘
```

### State (plain JS, no framework)

```javascript
const state = {
    currentDocId: null,       // selected document UUID
    currentFolderId: null,    // selected/active folder UUID (null = root)
    mode: 'preview',          // 'preview' | 'edit'
    editorContent: '',        // current CodeMirror content
    dirty: false,             // unsaved changes
};
```

### Key flows

**Select document (with dirty-state guard):**
1. Click doc in sidebar
2. If `state.dirty === true` → show browser `confirm()` "You have unsaved changes. Discard?" — if cancelled, abort
3. `GET /api/documents/{id}` → fetch content
4. Set `state.currentDocId`, `state.editorContent = content`, `state.dirty = false`
5. Set `iframe.srcdoc = content`; if in edit mode, `cm.setValue(content)`
6. Show toolbar with doc title

**Switch to Edit mode:**
1. Click Edit button (pencil icon)
2. Hide iframe, show `#editor` div
3. If CodeMirror not yet init'd for this doc → `cm.setValue(state.editorContent)`
4. Focus editor
5. Button changes to eye icon (Preview)

**Switch to Preview mode:**
1. Click Preview button (eye icon)
2. `state.editorContent = cm.getValue()`
3. `iframe.srcdoc = state.editorContent`
4. Hide `#editor`, show iframe
5. Button changes back to pencil (Edit)

**Save (Ctrl+S or Save button):**
1. `PUT /api/documents/{id}/content {content: cm.getValue()}`
2. `state.dirty = false`
3. Show "Saved" toast

**Create document:**
1. Click `[+ Doc]` in sidebar
2. Inline prompt for title (or auto-title "Untitled")
3. `POST /api/documents {title, folder_id: state.currentFolderId}`
4. Sidebar refreshes, new doc selected

**Create folder:**
1. Click `[+ 📁]`
2. Inline prompt for folder name
3. `POST /api/folders {name, parent_id: state.currentFolderId}`
4. Sidebar refreshes

**History (dropdown panel):**
- Clicking History button expands an inline panel below toolbar
- `GET /api/documents/{id}/versions` → renders version rows
- "Restore" button → `POST /api/documents/{id}/versions/{num}/restore` → refresh editor

**Share (dropdown panel):**
- Same as current share panel, moved inline below toolbar

### File upload fix

Upload handler attaches to `#file-upload` input via plain `addEventListener` in a regular (non-module) script. Root cause of existing bug: the `addEventListener` was inside an ES module that never loaded due to broken importmap.

---

## CodeMirror

Switch from CodeMirror 6 (ES modules via esm.sh — unreliable) to **CodeMirror 5.65 from cdnjs**:

```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/xml/xml.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/javascript/javascript.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/css/css.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/htmlmixed/htmlmixed.min.js"></script>
```

CM5 CDN (add to `<head>`):

```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css">
<!-- Dark theme for dark mode -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/theme/material-darker.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/xml/xml.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/javascript/javascript.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/css/css.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/htmlmixed/htmlmixed.min.js"></script>
```

CM5 API in `app.js`:

```javascript
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
const cm = CodeMirror(document.getElementById('editor'), {
    mode: 'htmlmixed',
    theme: prefersDark ? 'material-darker' : 'default',
    lineNumbers: true,
    lineWrapping: true,
    tabSize: 2,
    extraKeys: { 'Ctrl-S': saveDocument, 'Cmd-S': saveDocument },
});
```

---

## Visual Design

### CSS variables

```css
:root {
    --sidebar-width: 260px;
    --sidebar-bg: #f2f2f2;
    --sidebar-text: #333;
    --sidebar-hover: #e0e0e0;
    --sidebar-active: #d4d4d4;
    --main-bg: #ffffff;
    --toolbar-bg: #f8f8f8;
    --border: #ddd;
    --accent: #7b5ea7;
    --text: #1a1a1a;
    --muted: #888;
    --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}

@media (prefers-color-scheme: dark) {
    :root {
        --sidebar-bg: #1e1e1e;
        --sidebar-text: #dcddde;
        --sidebar-hover: #2a2a2a;
        --sidebar-active: #404040;
        --main-bg: #2d2d2d;
        --toolbar-bg: #252525;
        --border: #3a3a3a;
        --text: #dcddde;
        --muted: #888;
    }
}
```

### Typography
- UI text: system-ui sans-serif
- Editor: monospace (JetBrains Mono preferred via CDN Google Fonts)
- Sidebar item font-size: 0.875rem

---

## Files Added / Modified

| File | Change |
|------|--------|
| `app/models.py` | Add `Folder` model, add `folder_id` to `Document` |
| `app/schemas.py` | Add `FolderCreate`, `FolderRename`, `FolderResponse`, `FolderTree`, `DocumentMove` |
| `app/services/folder_service.py` | New — folder CRUD + tree builder |
| `app/services/document_service.py` | Update `create_document`, `list_documents`, add `move_document` |
| `app/routers/folders.py` | New — folder endpoints |
| `app/routers/documents.py` | Add `folder_id` to create, `?folder_id` filter to list, add move endpoint |
| `app/routers/pages.py` | Remove `/edit/{id}`, `/history/{id}` page routes; keep `/preview/{id}` |
| `app/templates/index.html` | Complete rewrite — Obsidian SPA layout |
| `app/templates/base.html` | Add CodeMirror 5 CDN links, Google Fonts, remove CM6 importmap |
| `app/static/css/style.css` | Complete rewrite — Obsidian theme, CSS variables, layout |
| `app/static/js/app.js` | Complete rewrite — state management, sidebar, preview/edit toggle |
| `app/static/js/editor.js` | Remove (merged into app.js) |
| `app/templates/editor.html` | Remove (merged into index.html) |
| `app/templates/history.html` | Remove (history becomes inline panel) |
| `app/templates/partials/` | Remove (no longer needed) |
| `tests/` | Update to reflect new routes and folder API |

---

## Out of Scope

- Drag-and-drop reordering of docs/folders
- Full-text search
- Document tags
- Real-time collaboration
- Auth / user accounts
