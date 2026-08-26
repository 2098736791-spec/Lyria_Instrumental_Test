"""请求/响应模型。"""
from typing import Optional

from pydantic import BaseModel, Field


class PromptRequest(BaseModel):
    user_input: str = Field(..., min_length=1, description="用户原始自然语言请求")
    instrumental: bool = Field(..., description="产品层纯音乐开关;false=原样透传")
    scheme: str = Field("B", description='仅 instrumental=true 生效:"B" 包裹 / "C" 改写')
    generate: bool = Field(False, description="true 时附带真实 Lyria 生成(需 key,十几~几十秒)")
    fallback_b: bool = Field(True, description="仅 scheme=C 生效:C 失败自动回落 B")


class AudioInfo(BaseModel):
    """便捷提取的音频字段(版权静默拦截等空返回时整个 audio 为 null)"""

    mime_type: Optional[str] = Field(None, description="音频 MIME 类型,如 audio/mp3")
    base64: Optional[str] = Field(None, description="音频内容的 base64 编码")


class PromptResponse(BaseModel):
    """POST /prompt 响应;后三项仅 generate=true 时出现"""

    ok: bool = Field(..., description="请求成功")
    scheme: str = Field(..., description='实际使用方案:"B"/"C"/"B(fallback)"/"passthrough"')
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

