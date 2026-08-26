"""API 层用例:TestClient 覆盖行为矩阵 6 情况 + 错误语义。generate 路径 mock。"""
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from instrumental_prompt import main
from instrumental_prompt import scheme_b
from instrumental_prompt.lyria import GenerationResult

client = TestClient(main.app)


# ── 假 Lyria 注入 ──────────────────────────────────────────────

FAKE_RESULT = GenerationResult(
    lyria_response={"candidates": [{"content": {"parts": [
        {"text": "[[A0]]"}, {"inline_data": {"mime_type": "audio/mp3", "data": "UkVBRA=="}}]}}]},
    audio_mime="audio/mp3",
    audio_b64="UkVBRA==",
    generation_text="[[A0]]",
)


@pytest.fixture
def fake_lyria(monkeypatch):
    calls = []

    def fake(prompt, api_key, model):
        calls.append(prompt)
        return FAKE_RESULT

    monkeypatch.setattr(main, "lyria_generate", fake)
    return calls


@dataclass
class FakeConfig:
    gemini_api_key: str | None
    key_source: str
    api_token: str | None
    lyria_model: str = "lyria-3-pro-preview"


# ── 行为矩阵 6 情况 ────────────────────────────────────────────

def test_case1_instrumental_b_prompt_only():
    r = client.post("/prompt", json={"user_input": "来一首粤语老情歌", "instrumental": True})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["scheme"] == "B"
    assert "<user_input>" in body["prompt"]
    assert "lyria_response" in body and body["lyria_response"] is None  # 两档形状统一:小响应带 null 字段


def test_case2_instrumental_c(monkeypatch):
    monkeypatch.setattr(main, "service_process",
                        lambda ui, instrumental, scheme="B", fallback_b=True:
                        ("纯音乐, 粤语流行", "C") if instrumental else (ui, "passthrough"))
    r = client.post("/prompt", json={"user_input": "来一首粤语老情歌", "instrumental": True,
                                     "scheme": "C"})
    assert r.json()["scheme"] == "C"


def test_case3_c_fallback(monkeypatch):
    monkeypatch.setattr(main, "service_process",
                        lambda ui, instrumental, scheme="B", fallback_b=True:
                        (scheme_b.wrap(ui), "B(fallback)"))
    r = client.post("/prompt", json={"user_input": "x", "instrumental": True, "scheme": "C"})
    assert r.json()["scheme"] == "B(fallback)"


def test_case4_passthrough():
    r = client.post("/prompt", json={"user_input": "来一首粤语老情歌", "instrumental": False,
                                     "scheme": "C"})  # scheme 应静默忽略
    body = r.json()
    assert body["scheme"] == "passthrough"
    assert body["prompt"] == "来一首粤语老情歌"


def test_case5_generate_true(fake_lyria, monkeypatch):
    monkeypatch.setattr(main, "load_config",
                        lambda: FakeConfig("k", "namespaced", None))
    r = client.post("/prompt", json={"user_input": "来一首粤语老情歌", "instrumental": True,
                                     "generate": True})
    assert r.status_code == 200
    body = r.json()
    assert body["audio"]["base64"] == "UkVBRA=="
    assert body["generation_text"] == "[[A0]]"
    assert body["lyria_response"]["candidates"]
    assert fake_lyria and "<user_input>" in fake_lyria[0]  # 加工后的 prompt 进了 Lyria


def test_case6_passthrough_generate(fake_lyria, monkeypatch):
    monkeypatch.setattr(main, "load_config",
                        lambda: FakeConfig("k", "namespaced", None))
    r = client.post("/prompt", json={"user_input": "来一首粤语老情歌", "instrumental": False,
                                     "generate": True})
    body = r.json()
    assert body["scheme"] == "passthrough"
    assert fake_lyria[0] == "来一首粤语老情歌"  # 原文进 Lyria(对照组)


# ── 错误语义 ──────────────────────────────────────────────────

def test_missing_instrumental_422():
    r = client.post("/prompt", json={"user_input": "x"})
    assert r.status_code == 422


def test_missing_user_input_422():
    r = client.post("/prompt", json={"instrumental": True})
    assert r.status_code == 422


def test_blank_user_input_422():
    r = client.post("/prompt", json={"user_input": "   ", "instrumental": True})
    assert r.status_code == 422
    assert "user_input" in r.json()["detail"]


def test_unknown_scheme_422():
    r = client.post("/prompt", json={"user_input": "x", "instrumental": True, "scheme": "A"})
    assert r.status_code == 422


def test_scheme_c_fail_no_fallback_502(monkeypatch):
    from instrumental_prompt.service import SchemeCFailure

    def broken(ui, instrumental, scheme="B", fallback_b=True):
        raise SchemeCFailure("方案 C 改写失败: RuntimeError: 网络炸了")

    monkeypatch.setattr(main, "service_process", broken)
    r = client.post("/prompt", json={"user_input": "x", "instrumental": True,
                                     "scheme": "C", "fallback_b": False})
    assert r.status_code == 502
    assert "scheme_c_failed" in r.json()["detail"]


def test_generate_no_key_500(fake_lyria, monkeypatch):
    monkeypatch.setattr(main, "load_config",
                        lambda: FakeConfig(None, "unset", None))
    r = client.post("/prompt", json={"user_input": "x", "instrumental": True, "generate": True})
    assert r.status_code == 500


def test_lyria_error_502(fake_lyria, monkeypatch):
    monkeypatch.setattr(main, "load_config",
                        lambda: FakeConfig("k", "namespaced", None))

    def broken(prompt, api_key, model):
        raise RuntimeError("400 VPN 断了")

    monkeypatch.setattr(main, "lyria_generate", broken)
    r = client.post("/prompt", json={"user_input": "x", "instrumental": True, "generate": True})
    assert r.status_code == 502
    assert "lyria_error" in r.json()["detail"]


def test_wrong_token_401(monkeypatch):
    monkeypatch.setattr(main, "load_config",
                        lambda: FakeConfig("k", "namespaced", "secret"))
    monkeypatch.setenv("API_TOKEN", "secret")
    r = client.post("/prompt", json={"user_input": "x", "instrumental": True},
                    headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_right_token_200(monkeypatch):
    monkeypatch.setattr(main, "load_config",
                        lambda: FakeConfig("k", "namespaced", "secret"))
    monkeypatch.setenv("API_TOKEN", "secret")
    r = client.post("/prompt", json={"user_input": "x", "instrumental": True},
                    headers={"Authorization": "Bearer secret"})
    assert r.status_code == 200


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["key_source"] in ("namespaced", "generic", "unset")
