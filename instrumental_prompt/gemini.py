"""provider:Gemini(LLM)网络调用——scheme C 的改写执行。

网络边界:engine(scheme_c)出提示词与后处理,本模块只管调 API。
失败抛原始异常,由 service 层决定回落/报错。
"""
from google import genai

from .scheme_c import SYSTEM_PROMPT, strip_wrappers

GEMINI_MODEL = "gemini-3.5-flash"


def rewrite_call(user_input: str, api_key: str) -> str:
    """调 Gemini 把用户输入改写为纯音乐标签流 prompt。

    Raises: google.genai 侧任意异常(网络/配额/key)——调用方兜底
    """
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_input,
        config={"system_instruction": SYSTEM_PROMPT, "temperature": 0.2},
    )
    return strip_wrappers((resp.text or "").strip())
