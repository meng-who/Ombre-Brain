"""Generated titles should not be silently cut off in either grow path."""

import json

import pytest

from dehydrator import Dehydrator


def _dehydrator(tmp_path):
    return Dehydrator({"buckets_dir": str(tmp_path), "human": "Melissa"})


def test_analyze_keeps_complete_generated_title(tmp_path):
    dehydrator = _dehydrator(tmp_path)
    title = "Ombre Brain系统更新与Cy的记忆整理"
    result = dehydrator._parse_analysis(
        json.dumps({"suggested_name": title}, ensure_ascii=False)
    )
    assert result["suggested_name"] == title
    dehydrator._cache_conn.close()


def test_digest_keeps_complete_generated_title(tmp_path):
    dehydrator = _dehydrator(tmp_path)
    title = "Ombre Brain系统更新与Cy的记忆整理"
    result = dehydrator._parse_digest(
        json.dumps([{"name": title, "content": "我们完成了更新。"}], ensure_ascii=False)
    )
    assert result[0]["name"] == title
    dehydrator._cache_conn.close()


def test_overlong_generated_title_is_omitted_instead_of_cut(tmp_path):
    dehydrator = _dehydrator(tmp_path)
    result = dehydrator._parse_analysis(
        json.dumps({"suggested_name": "长" * 121}, ensure_ascii=False)
    )
    assert result["suggested_name"] == ""
    dehydrator._cache_conn.close()


@pytest.mark.asyncio
async def test_pulse_displays_full_title_when_bucket_name_is_shortened(monkeypatch):
    from tools.anchor import core as anchor_core

    title = "Ombre Brain系统更新与Cy的记忆整理" * 3

    class Decay:
        is_running = True

        async def ensure_started(self):
            pass

        def calculate_score(self, _meta):
            return 1.0

    class Manager:
        async def get_stats(self):
            return {
                "permanent_count": 0, "dynamic_count": 1, "archive_count": 0,
                "feel_count": 0, "plan_count": 0, "letter_count": 0,
                "total_size_kb": 1.0,
            }

        async def list_all(self, include_archive=False):
            return [{
                "id": "test-title",
                "metadata": {
                    "name": "2026-10-07 10-00-00 " + title[:55],
                    "title": title,
                    "type": "dynamic",
                    "domain": [],
                    "tags": [],
                    "importance": 5,
                },
            }]

    monkeypatch.setattr(anchor_core.rt, "decay_engine", Decay())
    monkeypatch.setattr(anchor_core.rt, "bucket_mgr", Manager())
    monkeypatch.setattr(anchor_core.rt, "embedding_engine", None)

    result = await anchor_core.pulse()
    assert title in result
