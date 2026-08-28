"""FastAPI 入口:POST /prompt + GET /health。

启动: uvicorn instrumental_prompt.main:app --host 0.0.0.0 --port 8300
(在 demo/ 目录下启动,或把 demo/ 加入 PYTHONPATH)

层级:main(router)→ service(编排)→ engine(scheme_b/scheme_c/scheme_lyrics)
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
    title="Lyria 提示词处理服务",
    description="(user_input, mode) → 最终 prompt;lyrics 模式带 lyrics_input;generate=true 时附带真实 Lyria 生成",
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


VALID_MODES = ("passthrough", "instrumental", "lyrics")
MODE_SCHEMES = {
    "passthrough": (),
    "instrumental": ("B", "C"),
    "lyrics": ("S1", "S2"),
}
LYRICS_INPUT_MAX = 1000
LYRICS_STYLE_MAX = 3000


@app.post("/prompt", response_model=PromptResponse)
def prompt(req: PromptRequest, authorization: str | None = Header(default=None)):
    """唯一业务端点。三 mode 路由;generate=true 时耗时十几~几十秒,超时 ≥120s。

    形状校验(值域/组合/上限)在本层,语义清洗(注入句式)在 service。
    全部 422 不静默回退。
    """
    _check_token(authorization)

    user_input = req.user_input.strip()
    if not user_input:
        raise HTTPException(status_code=422, detail="user_input 不能为空白")

    if req.mode not in VALID_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"未知 mode: {req.mode!r}（可用: {list(VALID_MODES)}）")

    scheme = req.scheme
    if scheme is not None and scheme not in MODE_SCHEMES[req.mode]:
        allowed = MODE_SCHEMES[req.mode]
        if not allowed:
            hint = "passthrough 无子路由,不要传 scheme"
        else:
            hint = f"{req.mode} 可用 scheme: {list(allowed)}"
        raise HTTPException(status_code=422,
                            detail=f"scheme {scheme!r} 不可用: {hint}")

    if req.mode != "lyrics" and req.lyrics_input.strip():
        raise HTTPException(
            status_code=422,
            detail=f"lyrics_input 仅 mode='lyrics' 允许非空（当前 mode={req.mode!r}）")

    if req.mode == "lyrics":
        lyrics_input = req.lyrics_input.strip()
        if not lyrics_input:
            raise HTTPException(status_code=422,
                                detail="lyrics_input 不能为空白（mode='lyrics' 必填歌词）")
        if len(req.lyrics_input) > LYRICS_INPUT_MAX:
            raise HTTPException(
                status_code=422,
                detail=f"lyrics_input 超长: {len(req.lyrics_input)} > {LYRICS_INPUT_MAX} 字符上限,拒绝而不截断")
        if len(req.user_input) > LYRICS_STYLE_MAX:
            raise HTTPException(
                status_code=422,
                detail=f"user_input(风格槽)超长: {len(req.user_input)} > {LYRICS_STYLE_MAX} 字符上限,拒绝而不截断")

    # ① prompt 加工(service 层编排:语义路由 + 歌词模式注入清洗)
    try:
        prompt_text, used_scheme = service_process(
            user_input, req.mode,
            lyrics_input=(req.lyrics_input if req.mode == "lyrics" else ""),
            scheme=req.scheme, fallback_b=req.fallback_b,
        )
    except service_mod.InjectionRejected as e:
        raise HTTPException(status_code=422, detail=f"injection_rejected: {e.field}")
    except service_mod.UnknownScheme as e:
        raise HTTPException(status_code=422, detail=f"unknown_scheme: {e}")
    except service_mod.SchemeCFailure as e:
        raise HTTPException(status_code=502, detail=f"scheme_c_failed: {e}")

    # ② 可选真实生成(与 mode 无关,零改动)
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
