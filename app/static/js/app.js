// ─── State ────────────────────────────────────────────────────────────────
const state = {
    currentDocId: null,
    currentFolderId: null,   // folder selected in sidebar (for new doc target)
    mode: 'preview',          // 'preview' | 'edit'
    editorContent: '',
    dirty: false,
    folderNames: {},    // id → name, populated in loadSidebar
};

// ─── CodeMirror init ──────────────────────────────────────────────────────
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
const cm = CodeMirror(document.getElementById('editor-wrap'), {
    mode: 'htmlmixed',
    theme: prefersDark ? 'material-darker' : 'default',
    lineNumbers: true,
    lineWrapping: true,
    tabSize: 2,
    extraKeys: { 'Ctrl-S': saveDocument, 'Cmd-S': saveDocument },
});
cm.on('change', () => { state.dirty = true; });

// ─── DOM refs ─────────────────────────────────────────────────────────────
const treeRoot        = document.getElementById('tree-root');
const toolbarTitle    = document.getElementById('toolbar-title');
const toolbarActions  = document.getElementById('toolbar-actions');
const btnToggleEdit   = document.getElementById('btn-toggle-edit');
const btnSave         = document.getElementById('btn-save');
const btnUploadDoc    = document.getElementById('btn-upload-doc');
const btnHistory      = document.getElementById('btn-history');
const btnShare        = document.getElementById('btn-share');
const btnDelete       = document.getElementById('btn-delete');
const btnNewDoc       = document.getElementById('btn-new-doc');
const btnNewFolder    = document.getElementById('btn-new-folder');
const fileInput       = document.getElementById('file-input');
const previewIframe   = document.getElementById('preview-iframe');
const editorWrap      = document.getElementById('editor-wrap');
const emptyState      = document.getElementById('empty-state');
const panel           = document.getElementById('panel');
const panelHistory    = document.getElementById('panel-history');
const panelShare      = document.getElementById('panel-share');

// ─── Sidebar rendering ────────────────────────────────────────────────────
async function loadSidebar() {
    const [foldersRes, docsRes] = await Promise.all([
        fetch('/api/folders'),
        fetch('/api/documents?page_size=100'),
    ]);
    const folders = await foldersRes.json();
    const { documents } = await docsRes.json();

    // Build flat id→name lookup (handles nested folders)
    state.folderNames = {};
    (function collectNames(list) {
        for (const f of list) {
            state.folderNames[f.id] = f.name;
            if (f.children && f.children.length) collectNames(f.children);
        }
    })(folders);

    const rootDocs = documents.filter(d => d.folder_id === null);

    treeRoot.innerHTML = '';
    renderFolderList(folders, treeRoot);
    renderDocList(rootDocs, treeRoot, null);
}

function renderFolderList(folders, container) {
    for (const folder of folders) {
        const wrap = document.createElement('div');

        const row = document.createElement('div');
        row.className = 'sidebar-item folder-item';
        row.dataset.folderId = folder.id;
        row.innerHTML = `<span class="chevron"><svg viewBox="0 0 6 10" xmlns="http://www.w3.org/2000/svg"><path d="M1 1l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg></span><span class="icon">📁</span><span class="label">${escHtml(folder.name)}</span>`;
        row.addEventListener('click', () => toggleFolder(row, folder));
        wrap.appendChild(row);

        const children = document.createElement('div');
        children.className = 'folder-children';
        renderFolderList(folder.children || [], children);
        renderDocList(folder.documents || [], children, folder.id);
        wrap.appendChild(children);

        container.appendChild(wrap);
    }
}

function renderDocList(docs, container, folderId) {
    for (const doc of docs) {
        const row = document.createElement('div');
        row.className = 'sidebar-item doc-item' + (doc.id === state.currentDocId ? ' active' : '');
        row.dataset.docId = doc.id;
        row.innerHTML = `<span></span><span class="icon">📄</span><span class="label">${escHtml(doc.title)}</span>`;
        row.addEventListener('click', () => selectDocument(doc.id, folderId));
        container.appendChild(row);
    }
}

function toggleFolder(row, folder) {
    row.classList.toggle('open');
    const childWrap = row.nextElementSibling;
    childWrap.classList.toggle('open');
    state.currentFolderId = row.classList.contains('open') ? folder.id : null;
}

// ─── Document selection ───────────────────────────────────────────────────
async function selectDocument(docId, folderId = null) {
    if (state.dirty && !confirm('You have unsaved changes. Discard?')) return;

    state.currentFolderId = folderId;

    const res = await fetch(`/api/documents/${docId}`);
    if (!res.ok) { showToast('Error loading document'); return; }
    const doc = await res.json();

    state.currentDocId = docId;
    state.editorContent = doc.content || '';

    // Update sidebar active state
    document.querySelectorAll('.doc-item').forEach(el => {
        el.classList.toggle('active', el.dataset.docId === docId);
    });

    // font-weight:400 on the prefix resets the 600 weight of #toolbar-title so the folder name is visually lighter
    const folderName = folderId ? (state.folderNames[folderId] || null) : null;
    toolbarTitle.innerHTML = folderName
        ? `<span style="color:var(--muted);font-weight:400">${escHtml(folderName)} / </span>${escHtml(doc.title)}`
        : escHtml(doc.title);
    toolbarActions.style.display = 'flex';
    emptyState.style.display = 'none';
    closePanel();

    if (state.mode === 'edit') {
        cm.setValue(state.editorContent);
        cm.clearHistory();
    } else {
        showPreview(state.editorContent);
    }
    state.dirty = false;
}

// ─── Preview / Edit toggle ────────────────────────────────────────────────
function showPreview(html) {
    previewIframe.srcdoc = html;
    previewIframe.style.display = 'block';
    editorWrap.style.display = 'none';
}

function showEditor() {
    previewIframe.style.display = 'none';
    editorWrap.style.display = 'block';
    cm.refresh();
    cm.focus();
}

btnToggleEdit.addEventListener('click', () => {
    if (!state.currentDocId) return;
    if (state.mode === 'preview') {
        state.mode = 'edit';
        cm.setValue(state.editorContent);
        cm.clearHistory();
        state.dirty = false;
        showEditor();
        btnToggleEdit.textContent = 'Preview';
        btnSave.style.display = 'inline-flex';
    } else {
        state.editorContent = cm.getValue();
        state.mode = 'preview';
        showPreview(state.editorContent);
        btnToggleEdit.textContent = 'Edit';
        btnSave.style.display = 'none';
    }
});

// ─── Save ─────────────────────────────────────────────────────────────────
async function saveDocument() {
    if (!state.currentDocId) return;
    const content = cm.getValue();
    const res = await fetch(`/api/documents/${state.currentDocId}/content`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
    });
    if (!res.ok) { showToast('Save failed'); return; }
    state.editorContent = content;
    state.dirty = false;
    showToast('Saved');
}

btnSave.addEventListener('click', saveDocument);

// ─── File upload (sidebar — creates new document from file) ───────────────
btnUploadDoc.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', async () => {
    if (!fileInput.files.length) return;
    const file = fileInput.files[0];
    const title = file.name.replace(/\.html?$/i, '');

    // Create the document first
    const createRes = await fetch('/api/documents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, folder_id: state.currentFolderId }),
    });
    if (!createRes.ok) { showToast('Upload failed'); fileInput.value = ''; return; }
    const newDoc = await createRes.json();

    // Upload the file content
    const formData = new FormData();
    formData.append('file', file);
    const uploadRes = await fetch(`/api/documents/${newDoc.id}/upload`, {
        method: 'POST',
        body: formData,
    });
    fileInput.value = '';
    if (!uploadRes.ok) { showToast('Upload failed'); return; }

    await loadSidebar();
    await selectDocument(newDoc.id, state.currentFolderId);
    showToast('Uploaded');
});

// ─── Delete ───────────────────────────────────────────────────────────────
btnDelete.addEventListener('click', async () => {
    if (!state.currentDocId) return;
    if (!confirm('Delete this document?')) return;
    const res = await fetch(`/api/documents/${state.currentDocId}`, { method: 'DELETE' });
    if (!res.ok) { showToast('Delete failed'); return; }
    state.currentDocId = null;
    state.dirty = false;
    toolbarTitle.textContent = 'Select a document';
    toolbarActions.style.display = 'none';
    emptyState.style.display = 'flex';
    previewIframe.style.display = 'none';
    editorWrap.style.display = 'none';
    closePanel();
    await loadSidebar();
});

// ─── New document ─────────────────────────────────────────────────────────
btnNewDoc.addEventListener('click', async () => {
    const title = prompt('Document title:', 'Untitled');
    if (!title) return;
    const res = await fetch('/api/documents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, folder_id: state.currentFolderId }),
    });
    if (!res.ok) { showToast('Create failed'); return; }
    const doc = await res.json();
    await loadSidebar();
    await selectDocument(doc.id, state.currentFolderId);
});

// ─── New folder ───────────────────────────────────────────────────────────
btnNewFolder.addEventListener('click', async () => {
    const name = prompt('Folder name:');
    if (!name) return;
    const res = await fetch('/api/folders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, parent_id: state.currentFolderId }),
    });
    if (!res.ok) { showToast('Create folder failed'); return; }
    await loadSidebar();
});

// ─── History panel ────────────────────────────────────────────────────────
btnHistory.addEventListener('click', async () => {
    if (!state.currentDocId) return;
    const isOpen = panel.classList.contains('open') && panelHistory.style.display !== 'none';
    closePanel();
    if (isOpen) return;

    const res = await fetch(`/api/documents/${state.currentDocId}/versions`);
    if (!res.ok) return;
    const { versions } = await res.json();

    panelHistory.innerHTML = versions.length === 0
        ? '<p style="color:var(--muted);font-size:0.85rem;">No versions yet.</p>'
        : versions.map(v => `
            <div class="version-row">
                <span class="ver-meta">v${v.version_num} &mdash; ${new Date(v.created_at).toLocaleString()} &mdash; ${escHtml(v.source)}</span>
                <button type="button" class="btn" onclick="restoreVersion(${v.version_num})">Restore</button>
            </div>`).join('');

    panelHistory.style.display = 'block';
    panel.classList.add('open');
});

window.restoreVersion = async (versionNum) => {
    if (!state.currentDocId) return;
    const res = await fetch(
        `/api/documents/${state.currentDocId}/versions/${versionNum}/restore`,
        { method: 'POST' }
    );
    if (!res.ok) { showToast('Restore failed'); return; }
    const doc = await res.json();
    state.editorContent = doc.content || '';
    if (state.mode === 'edit') {
        cm.setValue(state.editorContent);
    } else {
        showPreview(state.editorContent);
    }
    state.dirty = false;
    closePanel();
    showToast('Restored to v' + versionNum);
};

// ─── Share panel ──────────────────────────────────────────────────────────
btnShare.addEventListener('click', async () => {
    if (!state.currentDocId) return;
    const isOpen = panel.classList.contains('open') && panelShare.style.display !== 'none';
    closePanel();
    if (isOpen) return;
    await renderSharePanel();
    panelShare.style.display = 'block';
    panel.classList.add('open');
});

async function renderSharePanel() {
    const res = await fetch(`/api/documents/${state.currentDocId}/sharing`);
    if (!res.ok) return;
    const settings = await res.json();
    const shareUrl = settings.share_mode === 'token' && settings.share_token
        ? `${location.origin}/preview/${state.currentDocId}?token=${settings.share_token}`
        : `${location.origin}/preview/${state.currentDocId}`;

    panelShare.innerHTML = `
        <div class="share-row">
            <label style="font-size:0.85rem;">Mode:</label>
            <select id="share-mode-select" style="padding:4px 8px;border:1px solid var(--border);border-radius:var(--radius);background:var(--main-bg);color:var(--text);font-size:0.85rem;">
                <option value="public" ${settings.share_mode === 'public' ? 'selected' : ''}>Public</option>
                <option value="token" ${settings.share_mode === 'token' ? 'selected' : ''}>Token-protected</option>
            </select>
            <button type="button" class="btn" id="btn-save-share">Save</button>
            ${settings.share_mode === 'token' ? '<button type="button" class="btn" id="btn-regen-token">New Token</button>' : ''}
        </div>
        <div class="share-row" style="margin-top:8px;">
            <input class="share-link-input" id="share-link" readonly value="${escHtml(shareUrl)}">
            <button type="button" class="btn" onclick="navigator.clipboard.writeText(document.getElementById('share-link').value).then(()=>showToast('Copied!'))">Copy</button>
        </div>`;

    document.getElementById('btn-save-share').addEventListener('click', async () => {
        const mode = document.getElementById('share-mode-select').value;
        await fetch(`/api/documents/${state.currentDocId}/sharing`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ share_mode: mode }),
        });
        await renderSharePanel();
    });

    document.getElementById('btn-regen-token')?.addEventListener('click', async () => {
        await fetch(`/api/documents/${state.currentDocId}/sharing/regenerate-token`, { method: 'POST' });
        await renderSharePanel();
    });
}

// ─── Panel helpers ────────────────────────────────────────────────────────
function closePanel() {
    panel.classList.remove('open');
    panelHistory.style.display = 'none';
    panelShare.style.display = 'none';
    panelHistory.innerHTML = '';
    panelShare.innerHTML = '';
}

// ─── Toast ────────────────────────────────────────────────────────────────
function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2000);
}

window.showToast = showToast;

// ─── Utility ──────────────────────────────────────────────────────────────
function escHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;');
}

// ─── Init ─────────────────────────────────────────────────────────────────
loadSidebar();
