"""请求/响应模型。"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PromptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # instrumental 布尔已退役,误传即报

    user_input: str = Field(..., min_length=1, description=(
        "主输入。passthrough/instrumental=完整自然语言描述;"
        "lyrics=风格描述(对应前端风格框),语义跟随模式"))
    mode: str = Field(..., description=(
        '生成模式(必填无默认):"passthrough" 原样透传 / '
        '"instrumental" 纯音乐(B/C) / "lyrics" 歌词模式(S1/S2)'))
    lyrics_input: str = Field("", description=(
        '歌词框原文。仅 mode="lyrics" 允许非空(≤1000 字符,超限 422)'))
    scheme: Optional[str] = Field(None, description=(
        '模式内子路由,默认 instrumental→"B"、lyrics→"S2";'
        'instrumental 可填 "B"/"C",lyrics 可填 "S1"/"S2",passthrough 必须不传'))
    generate: bool = Field(False, description="true 时附带真实 Lyria 生成(需 key,十几~几十秒)")
    fallback_b: bool = Field(True, description="仅 instrumental+scheme=C 生效:C 失败自动回落 B")


class AudioInfo(BaseModel):
    """便捷提取的音频字段(版权静默拦截等空返回时整个 audio 为 null)"""

    mime_type: Optional[str] = Field(None, description="音频 MIME 类型,如 audio/mp3")
    base64: Optional[str] = Field(None, description="音频内容的 base64 编码")


class PromptResponse(BaseModel):
    """POST /prompt 响应;后三项仅 generate=true 时出现"""

    ok: bool = Field(..., description="请求成功")
    scheme: str = Field(..., description='实际使用方案:"B"/"C"/"B(fallback)"/"passthrough"/"S1"/"S2"')
    prompt: str = Field(..., description="最终发给 Lyria 的 prompt")
    lyria_response: Optional[dict] = Field(None, description="Lyria 原始响应全量(音频 base64)")
    audio: Optional[AudioInfo] = Field(None, description="便捷音频字段;空返回时为 null")
    generation_text: Optional[str] = Field(None, description='文本片段拼接;纯音乐成功通常为 "[[A0]]"')


class HealthResponse(BaseModel):
    """GET /health 响应"""

    ok: bool = Field(..., description="服务正常")
    model: str = Field(..., description="默认 Lyria 模型 ID")
    gemini_key_present: bool = Field(..., description="key 是否已配置")
    key_source: str = Field(..., description='"namespaced"/"generic"/"unset",见 README FAQ Q2')

