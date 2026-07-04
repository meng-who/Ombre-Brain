import json

from dehydrator import Dehydrator, DIGEST_PROMPT


def test_digest_prompt_preserves_source_subjects():
    assert "严格保留原文的人称、主语和称呼" in DIGEST_PROMPT
    assert "禁止把所有记忆主体统一改成某个固定名字" in DIGEST_PROMPT
    assert "记忆的主体始终是" not in DIGEST_PROMPT


def test_parse_digest_does_not_replace_subject_with_user_name():
    dehydrator = Dehydrator({
        "user_name": "Melissa",
        "dehydration": {"api_key": ""},
    })

    raw = json.dumps([{
        "name": "大巴偶遇",
        "content": "我坐大巴时遇到一个特别能聊的e人妹妹，后来我帮广州来的姐妹翻译粤语。",
        "domain": ["出行", "友谊"],
        "valence": 0.7,
        "arousal": 0.4,
        "tags": ["大巴", "姐妹"],
        "importance": 5,
    }], ensure_ascii=False)

    items = dehydrator._parse_digest(raw, source_content="我坐大巴时遇到一个特别能聊的e人妹妹。")

    assert items[0]["content"].startswith("我坐大巴")
    assert "我帮广州来的姐妹翻译粤语" in items[0]["content"]
    assert "Melissa" not in items[0]["content"]


def test_parse_digest_replaces_report_reference_with_source_first_person():
    dehydrator = Dehydrator({
        "user_name": "Melissa",
        "dehydration": {"api_key": ""},
    })

    raw = json.dumps([{
        "name": "医院体检",
        "content": "该用户今天去了医院体检，结果还好。",
        "domain": ["健康"],
        "valence": 0.6,
        "arousal": 0.3,
        "tags": ["体检"],
        "importance": 5,
    }], ensure_ascii=False)

    items = dehydrator._parse_digest(raw, source_content="今天我去了医院体检，结果还好。")

    assert items[0]["content"] == "我今天去了医院体检，结果还好。"
    assert "该用户" not in items[0]["content"]
    assert "Melissa" not in items[0]["content"]


def test_parse_digest_replaces_report_reference_with_source_name():
    dehydrator = Dehydrator({
        "user_name": "Melissa",
        "dehydration": {"api_key": ""},
    })

    raw = json.dumps([{
        "name": "翻译粤语",
        "content": "当事人帮广州来的姐妹翻译粤语。",
        "domain": ["友谊"],
        "valence": 0.7,
        "arousal": 0.4,
        "tags": ["翻译"],
        "importance": 5,
    }], ensure_ascii=False)

    items = dehydrator._parse_digest(raw, source_content="Lincy 今天帮广州来的姐妹翻译粤语。")

    assert items[0]["content"] == "Lincy帮广州来的姐妹翻译粤语。"
    assert "当事人" not in items[0]["content"]
    assert "Melissa" not in items[0]["content"]
