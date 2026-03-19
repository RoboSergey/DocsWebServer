import { EditorView, basicSetup } from "codemirror";
import { html } from "@codemirror/lang-html";
import { keymap } from "@codemirror/view";

// Initialize editor
let editorView;

function initEditor(initialContent) {
    editorView = new EditorView({
        doc: initialContent,
        extensions: [
            basicSetup,
            html(),
            EditorView.updateListener.of((update) => {
                if (update.docChanged) {
                    debouncedPreview();
                }
            }),
            keymap.of([{
                key: "Ctrl-s",
                mac: "Cmd-s",
                run: () => { saveDocument(); return true; }
            }]),
        ],
        parent: document.getElementById('editor'),
    });

    updatePreview(initialContent);
}

// Debounced live preview (300ms)
let previewTimer;
function debouncedPreview() {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(() => {
        updatePreview(getEditorContent());
    }, 300);
}

function getEditorContent() {
    return editorView.state.doc.toString();
}

function updatePreview(content) {
    document.getElementById('preview-frame').srcdoc = content;
}

// Save document content
async function saveDocument() {
    const content = getEditorContent();
    const title = document.getElementById('doc-title').value;

    try {
        const res = await fetch(`/api/documents/${window.DOC_ID}/content`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content, source: 'editor'})
        });

        if (!res.ok) throw new Error('Save failed');

        // Update title if changed
        if (title !== window.INITIAL_TITLE) {
            const titleRes = await fetch(`/api/documents/${window.DOC_ID}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title})
            });
            if (titleRes.ok) {
                window.INITIAL_TITLE = title;
            }
        }

        showToast('Saved');
    } catch (e) {
        showToast('Save failed: ' + e.message);
    }
}

// File upload
document.getElementById('file-upload').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`/api/documents/${window.DOC_ID}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!res.ok) throw new Error('Upload failed');

        const data = await res.json();
        const newContent = data.content || '';
        editorView.dispatch({
            changes: {from: 0, to: editorView.state.doc.length, insert: newContent}
        });
        updatePreview(newContent);
        showToast('File uploaded');
    } catch (e) {
        showToast('Upload failed: ' + e.message);
    }
});

// Share panel
let shareLoaded = false;

async function toggleSharePanel() {
    const panel = document.getElementById('share-panel');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        if (!shareLoaded) {
            await loadShareSettings();
            shareLoaded = true;
        }
    } else {
        panel.style.display = 'none';
    }
}

async function loadShareSettings() {
    const res = await fetch(`/api/documents/${window.DOC_ID}/sharing`);
    const data = await res.json();
    document.getElementById('share-mode-select').value = data.share_mode;
    document.getElementById('share-url').value = data.share_url || '';
}

async function updateShareMode(mode) {
    await fetch(`/api/documents/${window.DOC_ID}/sharing`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({share_mode: mode})
    });
    await loadShareSettings();
    showToast('Share mode updated');
}

async function regenerateToken() {
    await fetch(`/api/documents/${window.DOC_ID}/sharing/regenerate-token`, {method: 'POST'});
    await loadShareSettings();
    showToast('New token generated');
}

function copyShareUrl() {
    const url = document.getElementById('share-url').value;
    navigator.clipboard.writeText(url).then(() => showToast('Link copied!'));
}

// Expose functions needed by inline HTML event handlers
window.saveDocument = saveDocument;
window.toggleSharePanel = toggleSharePanel;
window.updateShareMode = updateShareMode;
window.regenerateToken = regenerateToken;
window.copyShareUrl = copyShareUrl;

// Initialize on load
initEditor(window.INITIAL_CONTENT || '');
