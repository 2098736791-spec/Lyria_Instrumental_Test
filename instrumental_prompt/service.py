"""service 层:prompt 加工编排。

职责(原 instrumental_button.py 逻辑收编):
    instrumental=False → 原样透传(其余加工参数静默忽略)
    instrumental=True  → scheme 路由:B 包裹 / C 改写,C 失败按 fallback_b 回落
gemini_call 依赖注入,测试时换假实现,不真调网络。
"""
from . import gemini, scheme_b


class SchemeCFailure(Exception):
    """方案 C 改写失败且 fallback_b=False(调用方转 502)。"""


class UnknownScheme(ValueError):
    """instrumental=True 时 scheme 不是 "B"/"C"。"""


def process(
    user_input: str,
    instrumental: bool,
    scheme: str = "B",
    fallback_b: bool = True,
    gemini_call=gemini.rewrite_call,
) -> tuple[str, str]:
    """编排入口:返回 (最终 prompt, 实际使用 scheme)。

    Returns: used_scheme ∈ "B" / "C" / "B(fallback)" / "passthrough"

    Raises:
        UnknownScheme: instrumental=True 且 scheme 非 B/C
        SchemeCFailure: scheme=C 失败且 fallback_b=False
    """
    user_input = (user_input or "").strip()

    if not instrumental:
        return user_input, "passthrough"

    if scheme == "B":
        return scheme_b.wrap(user_input), "B"

    if scheme == "C":
        from .config import load_config

        cfg = load_config()
        if not cfg.gemini_api_key:
            # 未配 key 视为 C 失败的一种,参与回落语义
            if fallback_b:
                return scheme_b.wrap(user_input), "B(fallback)"
            raise SchemeCFailure("方案 C 改写失败: GEMINI_API_KEY 未配置")
        try:
            prompt = gemini_call(user_input, cfg.gemini_api_key)
        except Exception as e:
            if fallback_b:
                return scheme_b.wrap(user_input), "B(fallback)"
            raise SchemeCFailure(
                f"方案 C 改写失败: {type(e).__name__}: {e}"
            ) from e
        return prompt, "C"

    raise UnknownScheme(f"未知 scheme: {scheme!r}（可用: 'B' / 'C'）")
