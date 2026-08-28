"""service 层:prompt 加工编排。

三分路由(spec 第三节):
    mode="passthrough"  → 原样透传(其余加工参数静默忽略)
    mode="instrumental" → scheme 路由:B 包裹 / C 改写,C 失败按 fallback_b 回落
    mode="lyrics"       → sanitize 两槽 → scheme 路由:S2 冻结模板(默认) / S1 裸拼接

gemini_call 依赖注入,测试时换假实现,不真调网络。
形状校验(必填/组合矛盾/长度上限)在 router;本层只做语义路由与清洗。
"""
from . import gemini, sanitize as sanitize_mod, scheme_b, scheme_lyrics


class SchemeCFailure(Exception):
    """方案 C 改写失败且 fallback_b=False(调用方转 502)。"""


class UnknownScheme(ValueError):
    """scheme 不属于当前 mode 的值域。"""


class InjectionRejected(ValueError):
    """lyrics 模式输入命中高危句式(调用方转 422)。field 记命中字段名。"""

    def __init__(self, field: str):
        super().__init__(f"输入含不可接受的指令式内容: {field}")
        self.field = field


def process(
    user_input: str,
    mode: str,
    lyrics_input: str = "",
    scheme: str | None = None,
    fallback_b: bool = True,
    gemini_call=gemini.rewrite_call,
) -> tuple[str, str]:
    """编排入口:返回 (最终 prompt, 实际使用 scheme)。

    Returns: used_scheme ∈ "passthrough" / "B" / "C" / "B(fallback)" / "S1" / "S2"

    Raises:
        UnknownScheme: scheme 非 当前 mode 值域
        SchemeCFailure: instrumental+scheme=C 失败且 fallback_b=False
        InjectionRejected: lyrics 模式输入命中高危句式
        ValueError: 未知 mode(router 已前置校验,防御兜底)
    """
    user_input = (user_input or "").strip()

    if mode == "passthrough":
        return user_input, "passthrough"

    if mode == "instrumental":
        if scheme is None:
            scheme = "B"
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
        raise UnknownScheme(f"未知 scheme: {scheme!r}（instrumental 可用: 'B' / 'C'）")

    if mode == "lyrics":
        style_clean, style_rejected = sanitize_mod.sanitize(user_input)
        lyrics_clean, lyrics_rejected = sanitize_mod.sanitize(lyrics_input or "")
        if style_rejected:
            raise InjectionRejected("user_input")
        if lyrics_rejected:
            raise InjectionRejected("lyrics_input")
        if scheme is None:
            scheme = "S2"
        if scheme == "S2":
            return scheme_lyrics.merge_s2(style_clean, lyrics_clean), "S2"
        if scheme == "S1":
            return scheme_lyrics.merge_s1(style_clean, lyrics_clean), "S1"
        raise UnknownScheme(f"未知 scheme: {scheme!r}（lyrics 可用: 'S1' / 'S2'）")

    raise ValueError(f"未知 mode: {mode!r}（可用: 'passthrough' / 'instrumental' / 'lyrics'）")
