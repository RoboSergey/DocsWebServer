import io

import pytest

pytestmark = pytest.mark.asyncio


class TestDocumentCRUD:
    async def test_create_document(self, client):
        res = await client.post("/api/documents", json={"title": "Test Doc"})
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Test Doc"
        assert "id" in data

    async def test_create_document_with_content(self, client):
        res = await client.post("/api/documents", json={"title": "Test", "content": "<h1>Hello</h1>"})
        assert res.status_code == 201
        data = res.json()
        assert data["content"] == "<h1>Hello</h1>"
        assert data["version_count"] == 1

    async def test_list_documents(self, client):
        await client.post("/api/documents", json={"title": "Doc 1"})
        await client.post("/api/documents", json={"title": "Doc 2"})
        res = await client.get("/api/documents")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert len(data["documents"]) == 2

    async def test_get_document(self, client):
        create_res = await client.post("/api/documents", json={"title": "Test"})
        doc_id = create_res.json()["id"]
        res = await client.get(f"/api/documents/{doc_id}")
        assert res.status_code == 200
        assert res.json()["title"] == "Test"

    async def test_get_document_not_found(self, client):
        res = await client.get("/api/documents/nonexistent-id")
        assert res.status_code == 404

    async def test_update_document_title(self, client):
        create_res = await client.post("/api/documents", json={"title": "Old Title"})
        doc_id = create_res.json()["id"]
        res = await client.put(f"/api/documents/{doc_id}", json={"title": "New Title"})
        assert res.status_code == 200
        assert res.json()["title"] == "New Title"

    async def test_update_document_not_found(self, client):
        res = await client.put("/api/documents/nonexistent-id", json={"title": "New"})
        assert res.status_code == 404

    async def test_delete_document(self, client):
        create_res = await client.post("/api/documents", json={"title": "To Delete"})
        doc_id = create_res.json()["id"]
        del_res = await client.delete(f"/api/documents/{doc_id}")
        assert del_res.status_code == 204
        list_res = await client.get("/api/documents")
        assert list_res.json()["total"] == 0

    async def test_delete_document_not_found(self, client):
        res = await client.delete("/api/documents/nonexistent-id")
        assert res.status_code == 404

    async def test_save_content_creates_version(self, client):
        create_res = await client.post("/api/documents", json={"title": "Test"})
        doc_id = create_res.json()["id"]
        res = await client.put(
            f"/api/documents/{doc_id}/content",
            json={"content": "<p>Hello</p>"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["content"] == "<p>Hello</p>"
        assert data["version_count"] == 1

        # Second save creates another version
        await client.put(f"/api/documents/{doc_id}/content", json={"content": "<p>v2</p>"})
        get_res = await client.get(f"/api/documents/{doc_id}")
        assert get_res.json()["version_count"] == 2

    async def test_upload_html_file(self, client):
        create_res = await client.post("/api/documents", json={"title": "Upload Test"})
        doc_id = create_res.json()["id"]

        html_content = b"<html><body><h1>Uploaded</h1></body></html>"
        res = await client.post(
            f"/api/documents/{doc_id}/upload",
            files={"file": ("test.html", io.BytesIO(html_content), "text/html")},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["version_count"] == 1

    async def test_upload_wrong_content_type_rejected(self, client):
        create_res = await client.post("/api/documents", json={"title": "Upload Test"})
        doc_id = create_res.json()["id"]

        res = await client.post(
            f"/api/documents/{doc_id}/upload",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        assert res.status_code == 400

    async def test_create_document_validates_title(self, client):
        res = await client.post("/api/documents", json={"title": ""})
        assert res.status_code == 422

    async def test_pagination(self, client):
        for i in range(5):
            await client.post("/api/documents", json={"title": f"Doc {i}"})
        res = await client.get("/api/documents?page=1&page_size=3")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 5
        assert len(data["documents"]) == 3
        assert data["page_size"] == 3
        assert data["page"] == 1


class TestDocumentFolderSupport:
    async def test_create_document_with_folder_id(self, client):
        folder = (await client.post("/api/folders", json={"name": "Work"})).json()
        res = await client.post(
            "/api/documents",
            json={"title": "Foldered Doc", "folder_id": folder["id"]},
        )
        assert res.status_code == 201
        assert res.json()["folder_id"] == folder["id"]

    async def test_move_document_to_folder(self, client):
        folder = (await client.post("/api/folders", json={"name": "Work"})).json()
        doc = (await client.post("/api/documents", json={"title": "Doc"})).json()
        res = await client.put(
            f"/api/documents/{doc['id']}/move",
            json={"folder_id": folder["id"]},
        )
        assert res.status_code == 200
        assert res.json()["folder_id"] == folder["id"]

    async def test_move_document_to_root(self, client):
        folder = (await client.post("/api/folders", json={"name": "Work"})).json()
        doc = (
            await client.post(
                "/api/documents",
                json={"title": "Doc", "folder_id": folder["id"]},
            )
        ).json()
        res = await client.put(
            f"/api/documents/{doc['id']}/move", json={"folder_id": None}
        )
        assert res.status_code == 200
        assert res.json()["folder_id"] is None

    async def test_move_document_not_found(self, client):
        res = await client.put(
            "/api/documents/nonexistent/move", json={"folder_id": None}
        )
        assert res.status_code == 404

    async def test_list_documents_filtered_by_folder(self, client):
        folder = (await client.post("/api/folders", json={"name": "Work"})).json()
        await client.post("/api/documents", json={"title": "In Folder", "folder_id": folder["id"]})
        await client.post("/api/documents", json={"title": "At Root"})

        res = await client.get(f"/api/documents?folder_id={folder['id']}")
        assert res.status_code == 200
        docs = res.json()["documents"]
        assert len(docs) == 1
        assert docs[0]["title"] == "In Folder"

    async def test_list_documents_no_filter_returns_all(self, client):
        folder = (await client.post("/api/folders", json={"name": "Work"})).json()
        await client.post("/api/documents", json={"title": "In Folder", "folder_id": folder["id"]})
        await client.post("/api/documents", json={"title": "At Root"})

        res = await client.get("/api/documents")
        assert res.status_code == 200
        assert res.json()["total"] == 2
