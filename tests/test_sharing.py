import pytest

pytestmark = pytest.mark.asyncio


class TestSharing:
    async def _create_doc(self, client):
        res = await client.post("/api/documents", json={"title": "Shared Doc"})
        return res.json()["id"]

    async def test_get_share_settings_default(self, client):
        doc_id = await self._create_doc(client)
        res = await client.get(f"/api/documents/{doc_id}/sharing")
        assert res.status_code == 200
        data = res.json()
        assert data["share_mode"] == "public"
        assert data["share_token"] is None

    async def test_update_share_mode_to_token(self, client):
        doc_id = await self._create_doc(client)
        res = await client.put(
            f"/api/documents/{doc_id}/sharing",
            json={"share_mode": "token"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["share_mode"] == "token"
        assert data["share_token"] is not None  # auto-generated

    async def test_update_share_mode_to_public_keeps_token(self, client):
        doc_id = await self._create_doc(client)
        # Switch to token mode
        await client.put(f"/api/documents/{doc_id}/sharing", json={"share_mode": "token"})
        # Switch back to public
        res = await client.put(f"/api/documents/{doc_id}/sharing", json={"share_mode": "public"})
        data = res.json()
        assert data["share_mode"] == "public"
        assert data["share_token"] is not None  # token preserved

    async def test_regenerate_token(self, client):
        doc_id = await self._create_doc(client)
        await client.put(f"/api/documents/{doc_id}/sharing", json={"share_mode": "token"})
        settings1 = (await client.get(f"/api/documents/{doc_id}/sharing")).json()

        await client.post(f"/api/documents/{doc_id}/sharing/regenerate-token")
        settings2 = (await client.get(f"/api/documents/{doc_id}/sharing")).json()

        assert settings2["share_token"] != settings1["share_token"]

    async def test_public_preview_no_token(self, client):
        doc_id = await self._create_doc(client)
        await client.put(f"/api/documents/{doc_id}/content", json={"content": "<p>hello</p>"})
        res = await client.get(f"/preview/{doc_id}/raw")
        assert res.status_code == 200
        assert b"hello" in res.content

    async def test_token_preview_with_correct_token(self, client):
        doc_id = await self._create_doc(client)
        await client.put(f"/api/documents/{doc_id}/content", json={"content": "<p>secret</p>"})
        await client.put(f"/api/documents/{doc_id}/sharing", json={"share_mode": "token"})
        settings = (await client.get(f"/api/documents/{doc_id}/sharing")).json()
        token = settings["share_token"]

        res = await client.get(f"/preview/{doc_id}/raw?token={token}")
        assert res.status_code == 200
        assert b"secret" in res.content

    async def test_token_preview_without_token(self, client):
        doc_id = await self._create_doc(client)
        await client.put(f"/api/documents/{doc_id}/sharing", json={"share_mode": "token"})
        res = await client.get(f"/preview/{doc_id}/raw")
        assert res.status_code == 403

    async def test_token_preview_with_wrong_token(self, client):
        doc_id = await self._create_doc(client)
        await client.put(f"/api/documents/{doc_id}/sharing", json={"share_mode": "token"})
        res = await client.get(f"/preview/{doc_id}/raw?token=wrongtoken")
        assert res.status_code == 403
