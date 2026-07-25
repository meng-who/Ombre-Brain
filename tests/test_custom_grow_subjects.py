import asyncio
import json
from types import SimpleNamespace

import pytest

from dehydrator import Dehydrator
import tools.grow.core as grow_core_module


def _parser(human: str = "Melissa") -> Dehydrator:
    parser = Dehydrator.__new__(Dehydrator)
    parser.human = human
    return parser


def test_digest_recovers_leading_title_and_first_person(monkeypatch):
    monkeypatch.setenv("AI_NAME", "Cy")
    raw = json.dumps([
        {
            "name": "",
            "content": "标题：与Cy测试OB新版\n作者确认 grow 不应该改写主语。",
            "domain": ["AI"],
            "tags": ["grow"],
            "importance": 6,
            "valence": 0.5,
            "arousal": 0.4,
        }
    ], ensure_ascii=False)

    items = _parser()._parse_digest(
        raw,
        source_content="我在测试 grow，而且我就是 Cy。",
    )

    assert items[0]["name"] == "与Melissa测试OB新版"
    assert items[0]["content"] == "我确认 grow 不应该改写主语。"


@pytest.mark.asyncio
async def test_grow_content_uses_raw_merge(monkeypatch):
    item = {
        "name": "新版测试",
        "content": "我和Melissa一起测试新版 OB，并确认主语保持正确。",
        "domain": ["AI"],
        "tags": ["grow"],
        "importance": 6,
        "valence": 0.6,
        "arousal": 0.4,
    }
    monkeypatch.setattr(
        grow_core_module.rt,
        "dehydrator",
        SimpleNamespace(digest=lambda _content: asyncio.sleep(0, result=[item])),
    )
    monkeypatch.setattr(
        grow_core_module.rt,
        "logger",
        SimpleNamespace(error=lambda *_args, **_kwargs: None, warning=lambda *_args, **_kwargs: None),
    )
    captured = {}

    async def fake_merge_or_create(**kwargs):
        captured.update(kwargs)
        return "新版测试", True, ""

    async def no_op(*_args, **_kwargs):
        return None

    monkeypatch.setattr(grow_core_module, "merge_or_create", fake_merge_or_create)
    monkeypatch.setattr(grow_core_module, "check_duplicate_for", no_op)
    monkeypatch.setattr(grow_core_module, "check_plan_resolution", no_op)

    result = await grow_core_module.grow_core("一段足够长的测试内容，用于验证 grow 合并路径。")
    await asyncio.sleep(0)

    assert captured["content"] == item["content"]
    assert captured["raw_merge"] is True
    assert "合1" in result
