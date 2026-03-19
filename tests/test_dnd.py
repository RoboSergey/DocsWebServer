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
