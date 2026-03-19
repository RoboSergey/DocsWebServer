import pytest

pytestmark = pytest.mark.asyncio


class TestVersions:
    async def _create_doc_with_content(self, client, content="<p>v1</p>"):
        res = await client.post("/api/documents", json={"title": "Test", "content": content})
        return res.json()["id"]

    async def test_list_versions(self, client):
        doc_id = await self._create_doc_with_content(client)
        res = await client.get(f"/api/documents/{doc_id}/versions")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["versions"][0]["version_num"] == 1

    async def test_get_version(self, client):
        doc_id = await self._create_doc_with_content(client, "<p>version content</p>")
        res = await client.get(f"/api/documents/{doc_id}/versions/1")
        assert res.status_code == 200
        assert res.json()["content"] == "<p>version content</p>"

    async def test_get_version_not_found(self, client):
        doc_id = await self._create_doc_with_content(client)
        res = await client.get(f"/api/documents/{doc_id}/versions/999")
        assert res.status_code == 404

    async def test_multiple_versions(self, client):
        doc_id = await self._create_doc_with_content(client, "<p>v1</p>")
        await client.put(f"/api/documents/{doc_id}/content", json={"content": "<p>v2</p>"})
        await client.put(f"/api/documents/{doc_id}/content", json={"content": "<p>v3</p>"})
        res = await client.get(f"/api/documents/{doc_id}/versions")
        assert res.json()["total"] == 3

    async def test_restore_version(self, client):
        doc_id = await self._create_doc_with_content(client, "<p>original</p>")
        await client.put(f"/api/documents/{doc_id}/content", json={"content": "<p>modified</p>"})

        # Restore version 1
        res = await client.post(f"/api/documents/{doc_id}/versions/1/restore")
        assert res.status_code == 201
        assert res.json()["content"] == "<p>original</p>"
        assert res.json()["source"] == "restore"

        # Should now have 3 versions
        versions_res = await client.get(f"/api/documents/{doc_id}/versions")
        assert versions_res.json()["total"] == 3
