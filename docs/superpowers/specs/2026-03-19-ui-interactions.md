# Spec: UI Interactions — Resizable Sidebar, Context Menu, In-page Modals

**Date:** 2026-03-19
**Status:** Approved

---

## Goals

1. Make the sidebar resizable via a drag handle, with width persisted to `localStorage`.
2. Add a right-click context menu on document items (Edit, Share Link, Delete).
3. Replace all native browser dialogs (`confirm`, `prompt`) with in-page modals.

---

## Database Changes

None.

---

## API Changes

None — all endpoints used by the context menu (`GET /api/documents/{id}/sharing`, `DELETE /api/documents/{id}`) are pre-existing.

---

## Frontend Implementation

### 1. Resizable Sidebar

#### HTML

Add a resizer div between `#sidebar` and `#main` in `index.html`:

```html
<div id="sidebar-resizer"></div>
```

#### CSS (`style.css`)

```css
#sidebar-resizer {
    width: 4px;
    background: transparent;
    cursor: col-resize;
    flex-shrink: 0;
    position: relative;
    transition: background 0.15s;
}

#sidebar-resizer:hover,
#sidebar-resizer.active {
    background: var(--accent);
}
```

Extend the hit area with a pseudo-element:

```css
#sidebar-resizer::before {
    content: '';
    position: absolute;
    inset: 0 -4px;   /* 4px extra on each side = 12px total hit area */
}
```

#### JS (`app.js`)

On load, read saved width from `localStorage` and apply to `--sidebar-width`:

```javascript
const savedWidth = localStorage.getItem('sidebarWidth');
if (savedWidth) {
    document.documentElement.style.setProperty('--sidebar-width', savedWidth + 'px');
}
```

Resize logic (~25 lines).

Because `#sidebar` is flush with the left edge of the viewport (no margin or offset), `e.clientX` equals the sidebar's right edge and can be used directly as the new width:

```javascript
const sidebarResizer = document.getElementById('sidebar-resizer');
const MIN_WIDTH = 160;
const MAX_WIDTH = 480;

sidebarResizer.addEventListener('mousedown', (e) => {
    e.preventDefault();
    sidebarResizer.classList.add('active');
    const onMove = (e) => {
        const w = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, e.clientX));
        document.documentElement.style.setProperty('--sidebar-width', w + 'px');
    };
    const onUp = (e) => {
        sidebarResizer.classList.remove('active');
        const w = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, e.clientX));
        localStorage.setItem('sidebarWidth', w);
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
});
```

---

### 2. Right-click Context Menu

#### HTML

Add at the bottom of `index.html` (before `#toast`):

```html
<div id="context-menu">
  <button type="button" class="ctx-item" id="ctx-edit">Edit</button>
  <button type="button" class="ctx-item" id="ctx-share">Share Link</button>
  <button type="button" class="ctx-item ctx-danger" id="ctx-delete">Delete</button>
</div>
```

#### CSS (`style.css`)

```css
#context-menu {
    position: fixed;
    background: var(--toolbar-bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    padding: 4px 0;
    min-width: 140px;
    z-index: 1000;
    display: none;
}

#context-menu.open { display: block; }

.ctx-item {
    display: block;
    width: 100%;
    padding: 6px 14px;
    text-align: left;
    background: none;
    border: none;
    font-size: 0.875rem;
    color: var(--text);
    cursor: pointer;
}

.ctx-item:hover { background: var(--sidebar-hover); }
.ctx-item.ctx-danger { color: #c0392b; }
.ctx-item.ctx-danger:hover { background: #fde8e8; }

@media (prefers-color-scheme: dark) {
    .ctx-item.ctx-danger { color: #f1948a; }
    .ctx-item.ctx-danger:hover { background: #4a1515; }
}
```

#### JS (`app.js`)

```javascript
const contextMenu = document.getElementById('context-menu');
let ctxDocId = null;
let ctxFolderId = null;

function openContextMenu(e, docId, folderId) {
    e.preventDefault();
    ctxDocId = docId;
    ctxFolderId = folderId;
    contextMenu.style.left = e.clientX + 'px';
    contextMenu.style.top = e.clientY + 'px';
    contextMenu.classList.add('open');
}

function closeContextMenu() {
    contextMenu.classList.remove('open');
    ctxDocId = null;
}

document.addEventListener('click', closeContextMenu);
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeContextMenu(); });

// Wire up in renderDocList:
row.addEventListener('contextmenu', (e) => openContextMenu(e, doc.id, folderId));

// Context menu actions:
document.getElementById('ctx-edit').addEventListener('click', async () => {
    if (!ctxDocId) return;
    await selectDocument(ctxDocId, ctxFolderId);
    // Switch to edit mode
    if (state.mode !== 'edit') btnToggleEdit.click();
});

document.getElementById('ctx-share').addEventListener('click', async () => {
    if (!ctxDocId) return;
    await selectDocument(ctxDocId, ctxFolderId);
    const res = await fetch(`/api/documents/${ctxDocId}/sharing`);
    if (!res.ok) return;
    const settings = await res.json();
    const shareUrl = settings.share_mode === 'token' && settings.share_token
        ? `${location.origin}/preview/${ctxDocId}?token=${settings.share_token}`
        : `${location.origin}/preview/${ctxDocId}`;
    navigator.clipboard.writeText(shareUrl).then(() => showToast('Link copied!'));
});

document.getElementById('ctx-delete').addEventListener('click', async () => {
    if (!ctxDocId) return;
    const confirmed = await showModal({
        title: 'Delete document',
        message: 'This cannot be undone.',
        confirmText: 'Delete',
        danger: true,
    });
    if (!confirmed) return;
    const res = await fetch(`/api/documents/${ctxDocId}`, { method: 'DELETE' });
    if (!res.ok) { showToast('Delete failed'); return; }
    document.querySelector(`.sidebar-item[data-doc-id="${ctxDocId}"]`)?.remove();
    if (state.currentDocId === ctxDocId) {
        state.currentDocId = null;
        state.dirty = false;
        toolbarTitle.textContent = 'Select a document';
        toolbarActions.style.display = 'none';
        emptyState.style.display = 'flex';
        previewIframe.style.display = 'none';
        editorWrap.style.display = 'none';
        closePanel();
    }
    showToast('Deleted');
});
```

**Viewport overflow clamping:** After calling `contextMenu.classList.add('open')` (which makes the element visible and gives it measurable dimensions), clamp the position so the menu never overflows the viewport:

```javascript
contextMenu.classList.add('open');
const menuRect = contextMenu.getBoundingClientRect();
let left = e.clientX;
let top = e.clientY;
if (left + menuRect.width > window.innerWidth) left = window.innerWidth - menuRect.width - 4;
if (top + menuRect.height > window.innerHeight) top = window.innerHeight - menuRect.height - 4;
contextMenu.style.left = left + 'px';
contextMenu.style.top = top + 'px';
```

The clamping must happen after `classList.add('open')` because `getBoundingClientRect()` returns zeroes on a hidden element.

---

### 3. In-page Modal System

#### HTML

Add inside `index.html` (before `#toast`):

```html
<div id="modal-overlay">
  <div id="modal" role="dialog" aria-modal="true">
    <h3 id="modal-title"></h3>
    <p id="modal-message"></p>
    <div id="modal-inputs"></div>
    <div id="modal-actions">
      <button type="button" class="btn" id="modal-cancel">Cancel</button>
      <button type="button" class="btn primary" id="modal-confirm">OK</button>
    </div>
  </div>
</div>
```

#### CSS (`style.css`)

```css
#modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.45);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 2000;
}

#modal-overlay.open { display: flex; }

#modal {
    background: var(--toolbar-bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 20px 24px;
    min-width: 300px;
    max-width: 420px;
    width: 90%;
    box-shadow: 0 8px 32px rgba(0,0,0,0.25);
}

#modal h3 {
    margin-bottom: 8px;
    font-size: 1rem;
    font-weight: 600;
}

#modal p {
    color: var(--muted);
    font-size: 0.875rem;
    margin-bottom: 16px;
}

#modal-inputs { margin-bottom: 16px; }

#modal-inputs label {
    display: block;
    font-size: 0.8rem;
    color: var(--muted);
    margin-bottom: 4px;
}

#modal-inputs input {
    width: 100%;
    padding: 6px 10px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--main-bg);
    color: var(--text);
    font-size: 0.875rem;
    margin-bottom: 10px;
}

#modal-inputs input:focus {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
}

#modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
}

#modal-confirm.danger {
    background: #c0392b;
    border-color: #c0392b;
    color: white;
}

#modal-confirm.danger:hover { opacity: 0.9; }
```

#### JS (`app.js`)

```javascript
function showModal({ title, message = '', inputs = [], confirmText = 'OK', cancelText = 'Cancel', danger = false }) {
    return new Promise((resolve) => {
        const overlay = document.getElementById('modal-overlay');
        document.getElementById('modal-title').textContent = title;
        const msgEl = document.getElementById('modal-message');
        msgEl.textContent = message;
        msgEl.style.display = message ? 'block' : 'none';

        const inputsEl = document.getElementById('modal-inputs');
        inputsEl.innerHTML = '';
        inputs.forEach(({ label, value = '', id }) => {
            const lbl = document.createElement('label');
            lbl.textContent = label;
            const inp = document.createElement('input');
            inp.type = 'text';
            inp.value = value;
            inp.id = id;
            inputsEl.appendChild(lbl);
            inputsEl.appendChild(inp);
        });
        inputsEl.style.display = inputs.length ? 'block' : 'none';

        const confirmBtn = document.getElementById('modal-confirm');
        const cancelBtn = document.getElementById('modal-cancel');
        confirmBtn.textContent = confirmText;
        cancelBtn.textContent = cancelText;
        confirmBtn.classList.toggle('danger', danger);
        confirmBtn.classList.toggle('primary', !danger);

        overlay.classList.add('open');

        // Focus first input or confirm button
        const firstInput = inputsEl.querySelector('input');
        setTimeout(() => (firstInput || confirmBtn).focus(), 0);

        function close(result) {
            overlay.classList.remove('open');
            overlay.removeEventListener('click', onOverlayClick);
            document.removeEventListener('keydown', onKey);
            confirmBtn.removeEventListener('click', confirm);
            cancelBtn.removeEventListener('click', cancel);
            resolve(result);
        }

        function onOverlayClick(e) { if (e.target === overlay) close(null); }
        function onKey(e) {
            if (e.key === 'Escape') close(null);
            if (e.key === 'Enter' && document.activeElement?.tagName !== 'BUTTON') confirm();
        }

        function confirm() {
            if (inputs.length) {
                const values = {};
                inputs.forEach(({ id }) => { values[id] = document.getElementById(id)?.value ?? ''; });
                close(values);
            } else {
                close(true);
            }
        }

        function cancel() { close(null); }

        confirmBtn.addEventListener('click', confirm);
        cancelBtn.addEventListener('click', cancel);
        overlay.addEventListener('click', onOverlayClick);
        document.addEventListener('keydown', onKey);
    });
}
```

**Replacing existing dialogs:**

| Old | New |
|-----|-----|
| `prompt('Document title:', 'Untitled')` | `await showModal({ title: 'New document', inputs: [{label: 'Title', value: 'Untitled', id: 'modal-doc-title'}] })` → use `result['modal-doc-title']` |
| `prompt('Folder name:')` | `await showModal({ title: 'New folder', inputs: [{label: 'Name', id: 'modal-folder-name'}] })` → use `result['modal-folder-name']` |
| `confirm('You have unsaved changes. Discard?')` | `await showModal({ title: 'Unsaved changes', message: 'Discard changes?', confirmText: 'Discard', danger: true })` |
| `confirm('Delete this document?')` | `await showModal({ title: 'Delete document', message: 'This cannot be undone.', confirmText: 'Delete', danger: true })` |
| `confirm(\`Delete folder "${folder.name}"?...\`)` | `await showModal({ title: \`Delete "${folder.name}"\`, message: 'Documents will be moved to the parent level.', confirmText: 'Delete', danger: true })` |
| `confirm('You have unsaved changes. Discard?')` inside `selectDocument` | Same as above row — the `selectDocument` function body must be updated; this call is inside `selectDocument`, not at call sites |

---

## Files to Add / Modify

| File | Change |
|------|--------|
| `app/templates/index.html` | Add `#sidebar-resizer`, `#context-menu`, `#modal-overlay` elements |
| `app/static/css/style.css` | Add resizer, context menu, and modal styles |
| `app/static/js/app.js` | Add resize logic, context menu logic, `showModal` function; replace all `confirm`/`prompt` calls |

---

## Out of Scope

- Touch/mobile resize support.
- Right-click on folders.
- Keyboard shortcut to open context menu.
- Animated modal enter/exit transitions.
- Multiple simultaneous modals.
