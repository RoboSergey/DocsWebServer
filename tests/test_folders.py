import pytest

pytestmark = pytest.mark.asyncio


class TestFolderCRUD:
    async def test_create_root_folder(self, client):
        res = await client.post("/api/folders", json={"name": "Work"})
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Work"
        assert data["parent_id"] is None
        assert "id" in data

    async def test_create_nested_folder(self, client):
        parent = (await client.post("/api/folders", json={"name": "Work"})).json()
        res = await client.post(
            "/api/folders", json={"name": "Projects", "parent_id": parent["id"]}
        )
        assert res.status_code == 201
        assert res.json()["parent_id"] == parent["id"]

    async def test_get_folder_tree_empty(self, client):
        res = await client.get("/api/folders")
        assert res.status_code == 200
        assert res.json() == []

    async def test_get_folder_tree_nested(self, client):
        parent = (await client.post("/api/folders", json={"name": "Work"})).json()
        await client.post(
            "/api/folders", json={"name": "Notes", "parent_id": parent["id"]}
        )
        tree = (await client.get("/api/folders")).json()
        assert len(tree) == 1
        assert tree[0]["name"] == "Work"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["name"] == "Notes"

    async def test_rename_folder(self, client):
        folder = (await client.post("/api/folders", json={"name": "Old"})).json()
        res = await client.put(f"/api/folders/{folder['id']}", json={"name": "New"})
        assert res.status_code == 200
        assert res.json()["name"] == "New"

    async def test_rename_folder_not_found(self, client):
        res = await client.put("/api/folders/nonexistent", json={"name": "X"})
        assert res.status_code == 404

    async def test_delete_folder_moves_children_to_parent(self, client):
        parent = (await client.post("/api/folders", json={"name": "Parent"})).json()
        child = (
            await client.post(
                "/api/folders", json={"name": "Child", "parent_id": parent["id"]}
            )
        ).json()
        grandchild = (
            await client.post(
                "/api/folders", json={"name": "Grand", "parent_id": child["id"]}
            )
        ).json()

        res = await client.delete(f"/api/folders/{child['id']}")
        assert res.status_code == 204

        tree = (await client.get("/api/folders")).json()
        # Parent should exist; grandchild should be re-parented to parent
        parent_node = next(n for n in tree if n["id"] == parent["id"])
        child_ids = [c["id"] for c in parent_node["children"]]
        assert grandchild["id"] in child_ids

    async def test_delete_folder_not_found(self, client):
        res = await client.delete("/api/folders/nonexistent")
        assert res.status_code == 404

    async def test_folder_tree_includes_documents(self, client):
        folder = (await client.post("/api/folders", json={"name": "Work"})).json()
        await client.post(
            "/api/documents", json={"title": "My Doc", "folder_id": folder["id"]}
        )
        tree = (await client.get("/api/folders")).json()
        assert len(tree[0]["documents"]) == 1
        assert tree[0]["documents"][0]["title"] == "My Doc"
