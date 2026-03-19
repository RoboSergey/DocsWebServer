# UI Interactions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a resizable sidebar, right-click context menu on document items, and replace all native browser dialogs with in-page modals.

**Architecture:** All changes are frontend-only (HTML + CSS + JS). The modal system is implemented first because the context menu delete action depends on it. Each feature adds HTML structure to `index.html`, CSS to `style.css`, and JS to `app.js`. No new files are created; no backend changes.

**Tech Stack:** Vanilla JS, CSS custom properties, HTML5. No new libraries or dependencies.

---

## File Map

| File | What changes |
|------|-------------|
| `app/templates/index.html` | Add `#sidebar-resizer`, `#context-menu`, `#modal-overlay` elements |
| `app/static/css/style.css` | Add resizer, context menu, and modal styles |
| `app/static/js/app.js` | Add `showModal()`, resize logic, context menu logic; replace 5 native dialogs |

No files are created. No backend files are touched.

---

## Task 1: In-page Modal System — HTML + CSS

**Files:**
- Modify: `app/templates/index.html`
- Modify: `app/static/css/style.css`

### Context

The existing `index.html` ends at line 56. The `<div id="toast">` is on line 53. We add the modal overlay just before the toast.

The existing `style.css` ends at line 353. Append modal styles at the bottom.

### Steps

- [ ] **Step 1: Add modal HTML to `index.html`**

  Add directly before `<div id="toast"></div>` (currently line 53):

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

- [ ] **Step 2: Add modal CSS to `style.css`**

  Append at the end of `style.css`:

  ```css
  /* ===== Modal ===== */
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

- [ ] **Step 3: Verify visually**

  Open http://localhost:8000. The page should look identical — `#modal-overlay` is hidden by default. Open browser DevTools console and run:

  ```javascript
  document.getElementById('modal-overlay').classList.add('open')
  ```

  Expected: A centered modal card appears with a dark backdrop. Cancel and OK buttons are visible.

  Run:
  ```javascript
  document.getElementById('modal-overlay').classList.remove('open')
  ```
  Expected: Modal disappears.

- [ ] **Step 4: Run backend tests to confirm no regressions**

  ```bash
  cd /home/sergey.michelson/dev/documentWebServer
  ~/.local/bin/pytest tests/ -q
  ```

  Expected: `52 passed`

- [ ] **Step 5: Commit**

  ```bash
  git add app/templates/index.html app/static/css/style.css
  git commit -m "feat: add modal HTML structure and CSS"
  ```

---

## Task 2: In-page Modal System — JS + Replace Native Dialogs

**Files:**
- Modify: `app/static/js/app.js`

### Context

There are 5 native dialogs to replace in `app.js`:

| Line | Current | Replacement |
|------|---------|-------------|
| 100 | `confirm(\`Delete folder "${folder.name}"?...\`)` | `showModal({ title: ..., danger: true })` |
| 152 | `confirm('You have unsaved changes. Discard?')` | `showModal({ title: ..., danger: true })` |
| 271 | `confirm('Delete this document?')` | `showModal({ title: ..., danger: true })` |
| 289 | `prompt('Document title:', 'Untitled')` | `showModal({ title: ..., inputs: [...] })` |
| 304 | `prompt('Folder name:')` | `showModal({ title: ..., inputs: [...] })` |

The `showModal` function must be defined **before** any of these call sites — add it in the Utility section (after `escHtml`, before the Drag and Drop section, around line 435).

### Steps

- [ ] **Step 1: Add `showModal` function to `app.js`**

  Add after the `escHtml` function (after line 434, before the `// ─── Drag and Drop` comment):

  ```javascript
  // ─── Modal ────────────────────────────────────────────────────────────────
  function showModal({ title, message = '', inputs = [], confirmText = 'OK', cancelText = 'Cancel', danger = false }) {
      return new Promise((resolve) => {
          const overlay = document.getElementById('modal-overlay');
          const confirmBtn = document.getElementById('modal-confirm');
          const cancelBtn = document.getElementById('modal-cancel');

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

          confirmBtn.textContent = confirmText;
          cancelBtn.textContent = cancelText;
          confirmBtn.classList.toggle('danger', danger);
          confirmBtn.classList.toggle('primary', !danger);

          overlay.classList.add('open');
          setTimeout(() => (inputsEl.querySelector('input') || confirmBtn).focus(), 0);

          function close(result) {
              overlay.classList.remove('open');
              overlay.removeEventListener('click', onOverlayClick);
              document.removeEventListener('keydown', onKey);
              confirmBtn.removeEventListener('click', onConfirm);
              cancelBtn.removeEventListener('click', onCancel);
              resolve(result);
          }

          function onConfirm() {
              if (inputs.length) {
                  const values = {};
                  inputs.forEach(({ id }) => { values[id] = document.getElementById(id)?.value ?? ''; });
                  close(values);
              } else {
                  close(true);
              }
          }

          function onCancel() { close(null); }

          function onOverlayClick(e) { if (e.target === overlay) close(null); }

          function onKey(e) {
              if (e.key === 'Escape') close(null);
              if (e.key === 'Enter' && document.activeElement?.tagName !== 'BUTTON') onConfirm();
          }

          confirmBtn.addEventListener('click', onConfirm);
          cancelBtn.addEventListener('click', onCancel);
          overlay.addEventListener('click', onOverlayClick);
          document.addEventListener('keydown', onKey);
      });
  }
  ```

- [ ] **Step 2: Replace the folder delete `confirm` (line ~100 in `renderFolderList`)**

  The function currently uses an inline `async` arrow — it must be changed to `async` and `confirm` replaced.

  Find this code in `renderFolderList`:
  ```javascript
          deleteBtn.addEventListener('click', async (e) => {
              e.stopPropagation();
              if (!confirm(`Delete folder "${folder.name}"?\n\nDocuments inside will be moved to the parent level.`)) return;
              const res = await fetch(`/api/folders/${folder.id}`, { method: 'DELETE' });
              if (!res.ok) { showToast('Delete folder failed'); return; }
              await loadSidebar();
              showToast('Folder deleted');
          });
  ```

  Replace with:
  ```javascript
          deleteBtn.addEventListener('click', async (e) => {
              e.stopPropagation();
              const confirmed = await showModal({
                  title: `Delete "${folder.name}"`,
                  message: 'Documents inside will be moved to the parent level.',
                  confirmText: 'Delete',
                  danger: true,
              });
              if (!confirmed) return;
              const res = await fetch(`/api/folders/${folder.id}`, { method: 'DELETE' });
              if (!res.ok) { showToast('Delete folder failed'); return; }
              await loadSidebar();
              showToast('Folder deleted');
          });
  ```

- [ ] **Step 3: Replace the unsaved-changes `confirm` in `selectDocument` (line ~152)**

  `selectDocument` is already declared `async` (`async function selectDocument(docId, folderId = null)` at line 151) — no change needed to the function signature.

  Find:
  ```javascript
      if (state.dirty && !confirm('You have unsaved changes. Discard?')) return;
  ```

  Replace with:
  ```javascript
      if (state.dirty) {
          const confirmed = await showModal({
              title: 'Unsaved changes',
              message: 'Discard changes and switch document?',
              confirmText: 'Discard',
              danger: true,
          });
          if (!confirmed) return;
      }
  ```

- [ ] **Step 4: Replace the toolbar delete `confirm` (line ~271)**

  Find:
  ```javascript
      if (!confirm('Delete this document?')) return;
  ```

  Replace with:
  ```javascript
      const confirmed = await showModal({
          title: 'Delete document',
          message: 'This cannot be undone.',
          confirmText: 'Delete',
          danger: true,
      });
      if (!confirmed) return;
  ```

- [ ] **Step 5: Replace the new-document `prompt` (line ~289)**

  Find:
  ```javascript
      const title = prompt('Document title:', 'Untitled');
      if (!title) return;
  ```

  Replace with:
  ```javascript
      const result = await showModal({
          title: 'New document',
          inputs: [{ label: 'Title', value: 'Untitled', id: 'modal-doc-title' }],
          confirmText: 'Create',
      });
      if (!result) return;
      const title = result['modal-doc-title']?.trim();
      if (!title) return;
  ```

- [ ] **Step 6: Replace the new-folder `prompt` (line ~304)**

  Find:
  ```javascript
      const name = prompt('Folder name:');
      if (!name) return;
  ```

  Replace with:
  ```javascript
      const result = await showModal({
          title: 'New folder',
          inputs: [{ label: 'Name', id: 'modal-folder-name' }],
          confirmText: 'Create',
      });
      if (!result) return;
      const name = result['modal-folder-name']?.trim();
      if (!name) return;
  ```

- [ ] **Step 7: Verify all 5 dialogs work**

  Open http://localhost:8000 and test each replacement:

  1. Click 📄 (new doc) → expect in-page modal with "Title" input field, not a browser prompt
  2. Click 📁 (new folder) → expect in-page modal with "Name" input field
  3. Open a document, make a change (enter edit mode, type something), click another doc → expect "Unsaved changes" modal
  4. Click Delete in the toolbar → expect "Delete document" modal with red Delete button
  5. Hover over a folder, click × → expect "Delete folder" modal with red Delete button

  For each: confirm Cancel closes without acting, confirm Escape closes without acting, confirm Enter submits.

- [ ] **Step 8: Run backend tests**

  ```bash
  ~/.local/bin/pytest tests/ -q
  ```

  Expected: `52 passed`

- [ ] **Step 9: Commit**

  ```bash
  git add app/static/js/app.js
  git commit -m "feat: add showModal and replace all native browser dialogs"
  ```

---

## Task 3: Resizable Sidebar

**Files:**
- Modify: `app/templates/index.html`
- Modify: `app/static/css/style.css`
- Modify: `app/static/js/app.js`

### Context

`#app` is a flex row. The resizer div goes between `</aside>` and `<div id="main">`.

The `--sidebar-width` CSS variable is already used on `#sidebar` in `style.css`:
```css
#sidebar {
    width: var(--sidebar-width);
    min-width: var(--sidebar-width);
    ...
}
```

Because `#sidebar` is flush with the left viewport edge (no margin or offset), `e.clientX` during drag equals the desired sidebar width directly.

### Steps

- [ ] **Step 1: Add resizer HTML to `index.html`**

  Find the closing `</aside>` tag (after `</div>` that closes `#sidebar-tree`):

  ```html
    </aside>

    <!-- ── Main area ── -->
    <div id="main">
  ```

  Replace with:

  ```html
    </aside>
    <div id="sidebar-resizer"></div>

    <!-- ── Main area ── -->
    <div id="main">
  ```

- [ ] **Step 2: Add resizer CSS to `style.css`**

  Append at the end of `style.css`:

  ```css
  /* ===== Sidebar Resizer ===== */
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

  #sidebar-resizer::before {
      content: '';
      position: absolute;
      inset: 0 -4px;
  }
  ```

- [ ] **Step 3: Add resize JS to `app.js`**

  In the `// ─── Init` section at the very bottom of `app.js`, **before** the `setupRootDropTarget()` call, add:

  ```javascript
  // ─── Sidebar resize ───────────────────────────────────────────────────────
  const sidebarResizer = document.getElementById('sidebar-resizer');
  const MIN_SIDEBAR = 160;
  const MAX_SIDEBAR = 480;

  // Restore saved width on load
  const savedSidebarWidth = localStorage.getItem('sidebarWidth');
  if (savedSidebarWidth) {
      document.documentElement.style.setProperty('--sidebar-width', savedSidebarWidth + 'px');
  }

  sidebarResizer.addEventListener('mousedown', (e) => {
      e.preventDefault();
      sidebarResizer.classList.add('active');
      const onMove = (e) => {
          const w = Math.min(MAX_SIDEBAR, Math.max(MIN_SIDEBAR, e.clientX));
          document.documentElement.style.setProperty('--sidebar-width', w + 'px');
      };
      const onUp = (e) => {
          sidebarResizer.classList.remove('active');
          const w = Math.min(MAX_SIDEBAR, Math.max(MIN_SIDEBAR, e.clientX));
          localStorage.setItem('sidebarWidth', w);
          document.removeEventListener('mousemove', onMove);
          document.removeEventListener('mouseup', onUp);
      };
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
  });
  ```

- [ ] **Step 4: Verify resizer works**

  Open http://localhost:8000. Hover over the thin strip between the sidebar and main content — the cursor should change to `col-resize` and a purple line should appear. Drag left and right — the sidebar width should change. Refresh the page — the width should be restored.

  Also verify: dragging to <160px stops at 160px; dragging to >480px stops at 480px.

- [ ] **Step 5: Run backend tests**

  ```bash
  ~/.local/bin/pytest tests/ -q
  ```

  Expected: `52 passed`

- [ ] **Step 6: Commit**

  ```bash
  git add app/templates/index.html app/static/css/style.css app/static/js/app.js
  git commit -m "feat: add resizable sidebar with localStorage persistence"
  ```

---

## Task 4: Right-click Context Menu

**Files:**
- Modify: `app/templates/index.html`
- Modify: `app/static/css/style.css`
- Modify: `app/static/js/app.js`

### Context

The context menu is a fixed-position `div` that appears at the cursor when a `.doc-item` receives a `contextmenu` event. It has three actions: Edit, Share Link, Delete. Right-clicking a folder does nothing (no `contextmenu` listener on folder rows).

The `showModal` function from Task 2 must already exist — the Delete action uses it.

The `ctx-share` action fetches `GET /api/documents/{id}/sharing` (pre-existing endpoint) to build the share URL, then copies it to the clipboard.

### Steps

- [ ] **Step 1: Add context menu HTML to `index.html`**

  Add directly before `<div id="modal-overlay">` (which was added in Task 1):

  ```html
  <div id="context-menu">
    <button type="button" class="ctx-item" id="ctx-edit">Edit</button>
    <button type="button" class="ctx-item" id="ctx-share">Share Link</button>
    <button type="button" class="ctx-item ctx-danger" id="ctx-delete">Delete</button>
  </div>
  ```

- [ ] **Step 2: Add context menu CSS to `style.css`**

  Append at the end of `style.css`:

  ```css
  /* ===== Context Menu ===== */
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
      font-family: var(--font-ui);
  }

  .ctx-item:hover { background: var(--sidebar-hover); }
  .ctx-item.ctx-danger { color: #c0392b; }
  .ctx-item.ctx-danger:hover { background: #fde8e8; }

  @media (prefers-color-scheme: dark) {
      .ctx-item.ctx-danger { color: #f1948a; }
      .ctx-item.ctx-danger:hover { background: #4a1515; }
  }
  ```

- [ ] **Step 3: Add context menu JS to `app.js`**

  Add a new section just before the `// ─── Sidebar resize` section (added in Task 3):

  ```javascript
  // ─── Context menu ─────────────────────────────────────────────────────────
  const contextMenu = document.getElementById('context-menu');
  let ctxDocId = null;
  let ctxFolderId = null;

  function openContextMenu(e, docId, folderId) {
      e.preventDefault();
      ctxDocId = docId;
      ctxFolderId = folderId;
      // Show first so getBoundingClientRect() returns real dimensions
      contextMenu.classList.add('open');
      const menuRect = contextMenu.getBoundingClientRect();
      let left = e.clientX;
      let top = e.clientY;
      if (left + menuRect.width > window.innerWidth) left = window.innerWidth - menuRect.width - 4;
      if (top + menuRect.height > window.innerHeight) top = window.innerHeight - menuRect.height - 4;
      contextMenu.style.left = left + 'px';
      contextMenu.style.top = top + 'px';
  }

  function closeContextMenu() {
      contextMenu.classList.remove('open');
      ctxDocId = null;
      ctxFolderId = null;
  }

  document.addEventListener('click', closeContextMenu);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeContextMenu(); });

  document.getElementById('ctx-edit').addEventListener('click', async () => {
      const docId = ctxDocId;
      const folderId = ctxFolderId;
      if (!docId) return;
      await selectDocument(docId, folderId);
      if (state.mode !== 'edit') btnToggleEdit.click();
  });

  document.getElementById('ctx-share').addEventListener('click', async () => {
      const docId = ctxDocId;
      if (!docId) return;
      const res = await fetch(`/api/documents/${docId}/sharing`);
      if (!res.ok) return;
      const settings = await res.json();
      const shareUrl = settings.share_mode === 'token' && settings.share_token
          ? `${location.origin}/preview/${docId}?token=${settings.share_token}`
          : `${location.origin}/preview/${docId}`;
      navigator.clipboard.writeText(shareUrl).then(() => showToast('Link copied!'));
  });

  document.getElementById('ctx-delete').addEventListener('click', async () => {
      const docId = ctxDocId;
      const folderId = ctxFolderId;
      if (!docId) return;
      const confirmed = await showModal({
          title: 'Delete document',
          message: 'This cannot be undone.',
          confirmText: 'Delete',
          danger: true,
      });
      if (!confirmed) return;
      const res = await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
      if (!res.ok) { showToast('Delete failed'); return; }
      document.querySelector(`.sidebar-item[data-doc-id="${docId}"]`)?.remove();
      if (state.currentDocId === docId) {
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

  Note: local variables `docId`/`folderId` are captured at the start of each handler (before the first `await`) so they remain correct even if `ctxDocId`/`ctxFolderId` are cleared by `closeContextMenu` during the async operation. The spec's reference code for `ctx-share` has a bug where it reads `ctxDocId` after an `await` — this plan's version with local captures is the correct implementation.

- [ ] **Step 4: Wire `contextmenu` event in `renderDocList`**

  In `renderDocList`, find the line that adds the `click` listener:

  ```javascript
          row.addEventListener('click', () => selectDocument(doc.id, folderId));
  ```

  Add a `contextmenu` listener immediately after it:

  ```javascript
          row.addEventListener('contextmenu', (e) => openContextMenu(e, doc.id, folderId));
  ```

- [ ] **Step 5: Verify context menu works**

  Open http://localhost:8000. Right-click a document item in the sidebar. Expected: a small floating menu appears at the cursor with Edit, Share Link, Delete.

  Test each item:
  - **Edit**: selects the doc and switches to edit mode (CodeMirror visible, "Preview" button in toolbar)
  - **Share Link**: copies URL to clipboard and shows "Link copied!" toast
  - **Delete**: shows the in-page "Delete document" modal; confirm deletes, cancel does nothing

  Test close behaviors:
  - Click anywhere outside the menu → menu closes
  - Press Escape → menu closes
  - Right-click another document → previous menu closes and new one opens at new position

  Test overflow:
  - Right-click a document near the bottom-right of the screen → menu should not overflow the viewport

  Test folder items:
  - Right-click a folder → no context menu should appear (browser default may appear; that's acceptable)

- [ ] **Step 6: Run backend tests**

  ```bash
  ~/.local/bin/pytest tests/ -q
  ```

  Expected: `52 passed`

- [ ] **Step 7: Commit**

  ```bash
  git add app/templates/index.html app/static/css/style.css app/static/js/app.js
  git commit -m "feat: add right-click context menu for document items"
  ```

---

## Final Verification

After all 4 tasks are complete:

- [ ] All 3 features work together without interference
- [ ] `52 passed` on `pytest tests/ -q`
- [ ] No `confirm()` or `prompt()` calls remain in `app.js`:
  ```bash
  grep -n "confirm\|prompt(" app/static/js/app.js
  ```
  Expected: no matches (or only matches inside comments/strings like `showToast`)
