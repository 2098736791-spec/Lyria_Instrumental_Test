"""config 层用例:key 优先级 / key_source 三态 / .env 定路径加载。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from instrumental_prompt.config import load_config


def test_namespaced_key_wins(monkeypatch):
    monkeypatch.setenv("INSTRUMENTAL_PROMPT_GEMINI_API_KEY", "ns-key")
    monkeypatch.setenv("GEMINI_API_KEY", "generic-key")
    cfg = load_config()
    assert cfg.gemini_api_key == "ns-key"
    assert cfg.key_source == "namespaced"


def test_generic_fallback(monkeypatch):
    monkeypatch.delenv("INSTRUMENTAL_PROMPT_GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "generic-key")
    cfg = load_config()
    assert cfg.gemini_api_key == "generic-key"
    assert cfg.key_source == "generic"


def test_unset(monkeypatch):
    monkeypatch.delenv("INSTRUMENTAL_PROMPT_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("API_TOKEN", raising=False)
    cfg = load_config()
    assert cfg.gemini_api_key is None
    assert cfg.key_source == "unset"
    assert cfg.api_token is None
    assert cfg.lyria_model == "lyria-3-pro-preview"
