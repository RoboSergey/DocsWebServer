# Spec: Drag-and-Drop Reordering

**Date:** 2026-03-19
**Status:** Draft

---

## Goals

1. Drag a document onto a folder to move it into that folder.
2. Drag a document to the root drop zone to move it to root (`folder_id = null`).
3. Drag a folder onto another folder to reparent it.
4. Drag a folder to the root drop zone to move it to root (`parent_id = null`).
5. Drag items within the same container to control their display order (`sort_order`).
6. No external libraries — HTML5 Drag and Drop API only, vanilla JS.

---

## Database Changes

### `folders` table — add `sort_order`

```sql
ALTER TABLE folders ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;
```

- Lower `sort_order` values sort first (0-indexed).
- On creation, assign `sort_order = MAX(sort_order) + 1` within the same parent scope (or 0 if first).
- The existing `GET /api/folders` tree builder already returns children; it should order by `sort_order ASC, name ASC` (name as tiebreaker).

### `documents` table — add `sort_order`

```sql
ALTER TABLE documents ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;
```

- Same semantics — scoped to the folder (or root).
- `list_documents` should order by `sort_order ASC, title ASC`.

Both columns use SQLAlchemy `mapped_column(Integer, default=0)` and are handled via `create_tables(checkfirst=True)` like the existing `folder_id` migration.

---

## API Changes

### Move + reorder a document

```
PATCH /api/documents/{doc_id}/position
Body: { "folder_id": str | null, "sort_order": int }
Response: DocumentResponse (200)
```

Sets `folder_id` and `sort_order` atomically. The caller is responsible for sending the final desired `sort_order` value (computed on the frontend after re-numbering the target list). Returns 404 if document not found.

### Move + reorder a folder

```
PATCH /api/folders/{folder_id}/position
Body: { "parent_id": str | null, "sort_order": int }
Response: FolderResponse (200)
```

Same approach. Must reject a move that would create a cycle (folder moved into its own descendant) — return 422.

### Updated list ordering

- `GET /api/folders` — tree builder orders `children` by `sort_order ASC, name ASC`.
- `GET /api/documents` — orders by `sort_order ASC, title ASC`.

No new query params needed; ordering is always by `sort_order`.

### New schemas

```python
class DocumentPosition(BaseModel):
    folder_id: str | None = None
    sort_order: int = Field(..., ge=0)

class FolderPosition(BaseModel):
    parent_id: str | None = None
    sort_order: int = Field(..., ge=0)
```

---

## Frontend Implementation

### Data model on the client

Each rendered sidebar item already has `data-doc-id` or `data-folder-id`. Add `data-sort-order` so the frontend knows current order without re-fetching.

### Drag events — what attaches where

Every `.sidebar-item` (both `.folder-item` and `.doc-item`) gets `draggable="true"` set during `renderFolderList` / `renderDocList`.

Every folder row and every `folder-children` container (including `#tree-root`) becomes a **drop target**.

| Event | On element | Action |
|-------|-----------|--------|
| `dragstart` | `.sidebar-item` | Store dragged item's id, type (`doc`/`folder`), and current parent in `state.drag` |
| `dragover` | folder row, `folder-children`, `#tree-root` | `preventDefault()` to allow drop; add `.drag-over` CSS class |
| `dragleave` | same targets | Remove `.drag-over` |
| `drop` | same targets | Determine new parent + sort_order; call PATCH API; reload sidebar |
| `dragend` | `.sidebar-item` | Clear `.drag-over` from all elements; clear `state.drag` |

### Drop target resolution

- Drop on a **folder row** → target parent = that folder; `sort_order` = append to end (current child count).
- Drop on a **`folder-children` div or `#tree-root`** → target parent = that container's folder (or null for root); `sort_order` = append.
- For **within-container reordering**: track `dragover` on individual `.sidebar-item` elements; use `getBoundingClientRect()` to detect top/bottom half. Insert a thin placeholder `<div class="drop-indicator">` line at the insertion point. On drop, compute `sort_order` by taking the adjacent items' sort_order values and assigning `target_sort_order = predecessor_sort_order + 1` (then the PATCH call moves only the dragged item; the backend does not need to renumber others — gaps are acceptable).

### State additions

```javascript
state.drag = {
    type: null,         // 'doc' | 'folder'
    id: null,           // UUID
    parentFolderId: null, // current parent (null = root)
    sortOrder: null,    // current sort_order
};
```

### Cycle detection (client-side guard)

Before calling PATCH on a folder move, walk the in-memory sidebar tree to check the dragged folder is not an ancestor of the target. If it is, show a toast "Cannot move a folder into its own subfolder" and abort. The backend also validates this and returns 422.

### CSS additions

```css
.drag-over {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
    border-radius: var(--radius);
}

.drop-indicator {
    height: 2px;
    background: var(--accent);
    margin: 0 8px;
    border-radius: 1px;
    pointer-events: none;
}

[draggable="true"] {
    cursor: grab;
}

[draggable="true"]:active {
    cursor: grabbing;
}
```

### Sidebar refresh after drop

Call `loadSidebar()` after every successful PATCH. This re-fetches the tree (which is now ordered by `sort_order`) and re-renders. Preserve open/closed state of folders by saving the set of open folder IDs into `state.openFolderIds: Set<string>` before the refresh and re-applying it after.

---

## Files to Add / Modify

| File | Change |
|------|--------|
| `app/models.py` | Add `sort_order` column to `Folder` and `Document` |
| `app/schemas.py` | Add `DocumentPosition`, `FolderPosition`; add `sort_order` field to `DocumentResponse`, `FolderResponse`, `FolderTree` |
| `app/services/document_service.py` | Add `set_document_position(db, doc_id, folder_id, sort_order)`; update `list_documents` ordering |
| `app/services/folder_service.py` | Add `set_folder_position(db, folder_id, parent_id, sort_order)` with cycle check; update tree ordering |
| `app/routers/documents.py` | Add `PATCH /{doc_id}/position` endpoint |
| `app/routers/folders.py` | Add `PATCH /{folder_id}/position` endpoint |
| `app/static/js/app.js` | Add drag state, `dragstart`/`dragover`/`dragleave`/`drop`/`dragend` handlers, drop indicator logic, `loadSidebar` open-state preservation |
| `app/static/css/style.css` | Add `.drag-over`, `.drop-indicator`, `[draggable]` cursor rules |

---

## Out of Scope

- Touch/mobile drag (HTML5 DnD does not fire on touch — requires separate pointer events work).
- Multi-select drag.
- Undo/redo of drag operations.
- Keyboard-based reordering.
- Persisting folder open/closed state across page reloads (sessionStorage).
- Renaming via double-click (separate feature).
