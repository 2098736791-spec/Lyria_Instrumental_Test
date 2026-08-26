"""FastAPI 入口:POST /prompt + GET /health。

启动: uvicorn instrumental_prompt.main:app --host 0.0.0.0 --port 8300
(在 demo/ 目录下启动,或把 demo/ 加入 PYTHONPATH)

层级:main(router)→ service(编排)→ engine(scheme_b/scheme_c)
                        ↘ providers(gemini/lyria 网络边界)
模块级 service_process / lyria_generate 是测试注入点。
"""
import os

from fastapi import FastAPI, Header, HTTPException

from . import lyria as lyria_mod
from . import service as service_mod
from .config import load_config
from .schemas import HealthResponse, PromptRequest, PromptResponse

app = FastAPI(
    title="纯音乐按钮 prompt 服务",
    description="(user_input, instrumental) → 最终 prompt;generate=true 时附带真实 Lyria 生成",
    version="2.0.0",
)

# 测试注入点(测试 monkeypatch 这两个名字,不真调网络)
service_process = service_mod.process
lyria_generate = lyria_mod.generate


def _check_token(authorization: str | None):
    """设置了 API_TOKEN 才启用鉴权;没设置完全不拦。"""
    expected = os.environ.get("API_TOKEN")
    if not expected:
        return
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/health", response_model=HealthResponse)
def health():
    """存活探针,不调外部服务。key_source 让共享服务器上的 key 来源可见。"""
    cfg = load_config()
    return {
        "ok": True,
        "model": cfg.lyria_model,
        "gemini_key_present": cfg.gemini_api_key is not None,
        "key_source": cfg.key_source,
    }


@app.post("/prompt", response_model=PromptResponse)
def prompt(req: PromptRequest, authorization: str | None = Header(default=None)):
    """唯一业务端点。generate=true 时耗时十几~几十秒,客户端超时建议 ≥120s。"""
    _check_token(authorization)

    user_input = req.user_input.strip()
    if not user_input:
        raise HTTPException(status_code=422, detail="user_input 不能为空白")

    # ① prompt 加工(service 层编排)
    try:
        prompt_text, used_scheme = service_process(
            user_input, req.instrumental, req.scheme, req.fallback_b
        )
    except service_mod.UnknownScheme as e:
        raise HTTPException(status_code=422, detail=f"unknown_scheme: {e}")
    except service_mod.SchemeCFailure as e:
        raise HTTPException(status_code=502, detail=f"scheme_c_failed: {e}")

    # ② 可选真实生成
    if not req.generate:
        return {"ok": True, "scheme": used_scheme, "prompt": prompt_text}

    cfg = load_config()
    if not cfg.gemini_api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY 未配置")

    try:
        result = lyria_generate(prompt_text, cfg.gemini_api_key, cfg.lyria_model)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"lyria_error: {e}")

    audio = (
        {"mime_type": result.audio_mime, "base64": result.audio_b64}
        if result.audio_b64
        else None
    )
    return {
        "ok": True,
        "scheme": used_scheme,
        "prompt": prompt_text,
        "lyria_response": result.lyria_response,
        "audio": audio,
        "generation_text": result.generation_text,
    }
