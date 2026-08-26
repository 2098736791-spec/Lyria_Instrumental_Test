"""service 层用例:分支/路由/回落。gemini_call 全部注入假实现,零网络。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from instrumental_prompt.service import (
    SchemeCFailure,
    UnknownScheme,
    process,
)
from instrumental_prompt import scheme_b


def fake_gemini_ok(text):
    return lambda user_input, api_key: f"假改写[{user_input[:6]}]"


def fake_gemini_broken(text=None):
    def call(user_input, api_key):
        raise RuntimeError("网络炸了")
    return call


def test_instrumental_true_scheme_b():
    prompt, used = process("来一首粤语老情歌", instrumental=True, scheme="B",
                           gemini_call=fake_gemini_ok(None))
    assert prompt == scheme_b.wrap("来一首粤语老情歌")
    assert used == "B"


def test_passthrough_when_instrumental_false():
    prompt, used = process("来一首粤语老情歌", instrumental=False, scheme="C",
                           gemini_call=fake_gemini_broken())  # 不该被调
    assert prompt == "来一首粤语老情歌"
    assert used == "passthrough"


def test_scheme_c_success(monkeypatch):
    monkeypatch.setenv("INSTRUMENTAL_PROMPT_GEMINI_API_KEY", "k")
    prompt, used = process("来一首粤语老情歌", instrumental=True, scheme="C",
                           gemini_call=fake_gemini_ok(None))
    assert prompt == "假改写[来一首粤语老]"  # fake 取前 6 字
    assert used == "C"


def test_scheme_c_fallback_on_failure(monkeypatch):
    monkeypatch.setenv("INSTRUMENTAL_PROMPT_GEMINI_API_KEY", "k")
    prompt, used = process("来一首粤语老情歌", instrumental=True, scheme="C",
                           fallback_b=True, gemini_call=fake_gemini_broken())
    assert prompt == scheme_b.wrap("来一首粤语老情歌")
    assert used == "B(fallback)"


def test_scheme_c_failure_raises_without_fallback(monkeypatch):
    monkeypatch.setenv("INSTRUMENTAL_PROMPT_GEMINI_API_KEY", "k")
    with pytest.raises(SchemeCFailure) as ei:
        process("x", instrumental=True, scheme="C", fallback_b=False,
                gemini_call=fake_gemini_broken())
    assert "方案 C 改写失败" in str(ei.value)


def test_scheme_c_no_key_fallback(monkeypatch):
    # 未配 key 属 C 失败的一种,同样走回落语义
    monkeypatch.delenv("INSTRUMENTAL_PROMPT_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    prompt, used = process("x", instrumental=True, scheme="C",
                           fallback_b=True, gemini_call=fake_gemini_ok(None))
    assert used == "B(fallback)"


def test_unknown_scheme_rejected():
    with pytest.raises(UnknownScheme):
        process("x", instrumental=True, scheme="A")


def test_unknown_scheme_ignored_when_passthrough():
    # instrumental=false 时 scheme 静默忽略,不报错
    prompt, used = process("x", instrumental=False, scheme="bogus")
    assert used == "passthrough"


def test_blank_input_stripped():
    # service 不拦空白(422 是 router 职责),但 strip 应发生
    prompt, used = process("  Pop  ", instrumental=False)
    assert prompt == "Pop"
