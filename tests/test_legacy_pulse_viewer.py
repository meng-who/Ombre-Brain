import json

import pytest

import web.buckets as buckets_web


class FakeMCP:
    def __init__(self):
        self.routes = {}

    def custom_route(self, path, methods):
        def decorator(handler):
            for method in methods:
                self.routes[(method, path)] = handler
            return handler

        return decorator


class FakeBucketManager:
    async def list_all(self, *, include_archive=False):
        assert include_archive is False
        return [
            {
                "id": "older",
                "content": "Older [[memory]]",
                "metadata": {
                    "name": "Older",
                    "created": "2026-07-01T00:00:00Z",
                    "importance": 5,
                },
            },
            {
                "id": "newer",
                "content": "Newer [[memory]]",
                "metadata": {
                    "name": "Newer",
                    "created": "2026-07-02T00:00:00Z",
                    "importance": 7,
                },
            },
            {
                "id": "deleted",
                "content": "Hidden",
                "metadata": {
                    "name": "Deleted",
                    "deleted_at": "2026-07-03T00:00:00Z",
                },
            },
        ]

    async def get_stats(self):
        return {"total": 2}


class FakeDecayEngine:
    def calculate_score(self, metadata):
        return float(metadata.get("importance", 0))


@pytest.mark.asyncio
async def test_legacy_pulse_keeps_pages_contract_and_recent_order(monkeypatch):
    monkeypatch.setattr(
        buckets_web.sh,
        "bucket_mgr",
        FakeBucketManager(),
        raising=False,
    )
    monkeypatch.setattr(
        buckets_web.sh,
        "decay_engine",
        FakeDecayEngine(),
        raising=False,
    )
    mcp = FakeMCP()
    buckets_web.register(mcp)

    response = await mcp.routes[("GET", "/api/pulse")](object())
    payload = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 200
    assert payload["stats"] == {"total": 2}
    assert [bucket["id"] for bucket in payload["buckets"]] == ["newer", "older"]
    assert payload["buckets"][0]["content"] == "Newer memory"
