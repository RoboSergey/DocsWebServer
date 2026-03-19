import pytest

pytestmark = pytest.mark.asyncio


class TestSortOrderAssignment:
    async def test_documents_get_ascending_sort_order(self, client):
        r1 = await client.post("/api/documents", json={"title": "A"})
        r2 = await client.post("/api/documents", json={"title": "B"})
        assert r1.json()["sort_order"] == 0
        assert r2.json()["sort_order"] == 1

    async def test_list_documents_sorted_by_sort_order(self, client):
        # Create 3 docs (sort_order 0,1,2), then verify list order matches creation order
        for t in ["C", "A", "B"]:
            await client.post("/api/documents", json={"title": t})
        res = await client.get("/api/documents?page_size=10")
        titles = [d["title"] for d in res.json()["documents"]]
        assert titles == ["C", "A", "B"]  # creation order = sort_order order


class TestPositionEndpoints:
    async def test_patch_document_position(self, client):
        folder_r = await client.post("/api/folders", json={"name": "F"})
        folder_id = folder_r.json()["id"]
        doc_r = await client.post("/api/documents", json={"title": "D"})
        doc_id = doc_r.json()["id"]
        res = await client.patch(f"/api/documents/{doc_id}/position",
                                  json={"folder_id": folder_id, "sort_order": 0})
        assert res.status_code == 200
        assert res.json()["folder_id"] == folder_id
        assert res.json()["sort_order"] == 0

    async def test_patch_document_position_not_found(self, client):
        res = await client.patch("/api/documents/nope/position",
                                  json={"folder_id": None, "sort_order": 0})
        assert res.status_code == 404

    async def test_patch_folder_position(self, client):
        parent_r = await client.post("/api/folders", json={"name": "Parent"})
        parent_id = parent_r.json()["id"]
        child_r = await client.post("/api/folders", json={"name": "Child"})
        child_id = child_r.json()["id"]
        res = await client.patch(f"/api/folders/{child_id}/position",
                                  json={"parent_id": parent_id, "sort_order": 0})
        assert res.status_code == 200
        assert res.json()["parent_id"] == parent_id

    async def test_patch_folder_position_cycle_rejected(self, client):
        parent_r = await client.post("/api/folders", json={"name": "Parent"})
        parent_id = parent_r.json()["id"]
        child_r = await client.post("/api/folders", json={"name": "Child", "parent_id": parent_id})
        child_id = child_r.json()["id"]
        # Try to move parent into child — should be 422
        res = await client.patch(f"/api/folders/{parent_id}/position",
                                  json={"parent_id": child_id, "sort_order": 0})
        assert res.status_code == 422
