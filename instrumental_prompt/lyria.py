"""provider:Lyria 真实生成(generate=true 时的可选路径)。

调用方式对齐 GenerationModule/Modules/LyriaTest/generate_music.py:
    genai.Client(api_key) + GenerateContentConfig(response_modalities=["AUDIO","TEXT"])
    + 非流式 generate_content
"""
import base64
from dataclasses import dataclass

from google import genai
from google.genai import types


@dataclass(frozen=True)
class GenerationResult:
    lyria_response: dict      # 全量序列化(bytes→base64)
    audio_mime: str | None
    audio_b64: str | None
    generation_text: str


def _to_jsonable(obj):
    """递归序列化:bytes→base64,其余原样;奇异类型兜底 str()。

    不用 SDK 的 model_dump()——对 inline_data 原始字节处理不可靠。
    """
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return base64.b64encode(bytes(obj)).decode("ascii")
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if hasattr(obj, "model_dump"):
        try:
            return _to_jsonable(obj.model_dump())
        except Exception:
            pass
    if not isinstance(obj, (str, int, float, bool, type(None))):
        return str(obj)
    return obj


def generate(prompt: str, api_key: str, model: str) -> GenerationResult:
    """真实调 Lyria 生成一次。失败抛原始异常,router 转 502。"""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO", "TEXT"],
        ),
    )

    lyria_response = _to_jsonable(
        response.model_dump(exclude_none=False) if hasattr(response, "model_dump")
        else response.__dict__
    )

    audio_mime, audio_b64, texts = None, None, []
    for cand in getattr(response, "candidates", []) or []:
        for part in getattr(cand.content, "parts", []) or []:
            if getattr(part, "text", None):
                texts.append(part.text.strip())
            inline = getattr(part, "inline_data", None)
            if inline is not None and getattr(inline, "data", None):
                audio_mime = getattr(inline, "mime_type", "audio/mp3")
                audio_b64 = base64.b64encode(bytes(inline.data)).decode("ascii")

    return GenerationResult(
        lyria_response=lyria_response,
        audio_mime=audio_mime,
        audio_b64=audio_b64,
        generation_text="\n\n".join(t for t in texts if t),
    )
