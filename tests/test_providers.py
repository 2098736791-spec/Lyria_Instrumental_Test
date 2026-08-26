"""provider 层用例:不真调网络。只测纯序列化函数与模块接口存在性。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import inspect

from instrumental_prompt import gemini, lyria


def test_gemini_signature():
    sig = inspect.signature(gemini.rewrite_call)
    assert list(sig.parameters) == ["user_input", "api_key"]


def test_lyria_signature():
    sig = inspect.signature(lyria.generate)
    assert list(sig.parameters) == ["prompt", "api_key", "model"]


def test_to_jsonable_bytes_to_base64():
    import base64
    data = b"\xff\xd8\xff\xe0fake"
    out = lyria._to_jsonable(data)
    assert out == base64.b64encode(data).decode("ascii")


def test_to_jsonable_nested_and_strange_types():
    from enum import Enum

    class Color(Enum):
        RED = "red"

    out = lyria._to_jsonable(
        {"parts": [{"text": "[[A0]]"}, {"data": b"ab"}], "enum": Color.RED, "n": None}
    )
    assert out["parts"][0]["text"] == "[[A0]]"
    assert out["parts"][1]["data"] == "YWI="
    assert out["enum"] in ("Color.RED", "red", "RED")  # 兜底 str(),不丢字段
    assert out["n"] is None
