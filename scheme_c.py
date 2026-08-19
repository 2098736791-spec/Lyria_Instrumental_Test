#!/usr/bin/env python3
"""
scheme_c.py —— 方案 C：LLM 预改写（备选方案）

╔══════════════════════════════════════════════════════════╗
║  输入:  user_input (str)  用户原始自然语言请求              ║
║  输出:  prompt (str)      发给 Lyria 的最终 prompt          ║
║         （= Gemini 改写后的纯音乐标签流）                    ║
║  成本:  每次生成多一次 LLM 调用（Gemini-3.5-flash）          ║
║  实测:  100% 服从（41/41，2026-08-18）                      ║
╚══════════════════════════════════════════════════════════╝

独立运行依赖（仅此两项）:
  1. pip install google-genai
  2. 环境变量 GEMINI_API_KEY（或修改下方 load_key() 的读取方式）

用法:
    from scheme_c import rewrite
    prompt = rewrite("来一首最近很火的粤语老情歌，要有磁性的男声伴唱。")
    # prompt → 写入 Lyria 请求的 prompt 字段 → 生成

    命令行自测:
    python3 scheme_c.py "来一首最近很火的粤语老情歌，要有磁性的男声伴唱。"
"""
import os
import sys

# 模型与改写系统提示词来源：AutoTestSystem 实验 C1（100% 服从，41/41）
GEMINI_MODEL = "gemini-3.5-flash"

SYSTEM_PROMPT = """你是音乐生成系统的提示词改写器。把用户的音乐请求改写成纯音乐的结构化提示词。

输出规则：
1. 输出为一串简短的词或短语，用逗号罗列，不要写完整句子
2. 罗列中不得出现「风格」「乐器」「情绪」「场景」这类分类词本身，
   直接写内容（例：写「轻快」，不写「情绪：轻快」）
3. 保留用户输入中所有音乐语义：风格、乐器、情绪、场景、节奏、能量
4. 不添加用户没有提到的内容，不发散，不美化
5. 删除一切人声相关内容：演唱、合唱、说唱、念白、呢喃、哼唱、口哨、
   嘶吼、戏曲唱腔、歌词引用、念台词。不做人声替代——直接删掉，
   让剩余语义自然成立
6. 心跳声、雨声、掌声等非人声音效保留
7. 输出中必须包含一个明确的纯音乐标识：「纯音乐」（英文输入用 instrumental）
8. 如果用户请求本身就是纯音乐或配乐需求，仅格式化，语义不变
9. 输出语言与用户输入一致
10. 只输出改写结果本身，不要任何解释、前言、引号"""


def load_key() -> str:
    """读 GEMINI_API_KEY。默认环境变量；可按后端实际密钥管理方式改写本函数。"""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("[scheme_c] 未设置环境变量 GEMINI_API_KEY")
    return key


def strip_wrappers(text: str) -> str:
    """剥掉模型偶尔加的代码块围栏或首尾引号。"""
    t = text.strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        if first_nl != -1:
            t = t[first_nl + 1:]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    for q in ('"', "'", "「", "」", "“", "”"):
        t = t.strip(q)
    return t.strip()


def rewrite(user_input: str) -> str:
    """输入用户原始请求，输出 Gemini 改写后的纯音乐标签流 prompt。

    改写规则核心（详见 SYSTEM_PROMPT）:
    - 只删人声、不加戏（不编造用户没提的乐器）
    - 必含纯音乐标识（中文「纯音乐」/ 英文 instrumental）
    - 本来就是纯音乐需求的仅格式化

    Args:
        user_input: 用户原始自然语言请求（任意语言）

    Returns:
        标签流形式的最终 prompt 字符串

    Raises:
        Exception: Gemini 调用失败（网络/配额/Key）——调用方需兜底
    """
    from google import genai
    client = genai.Client(api_key=load_key())
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_input,
        config={"system_instruction": SYSTEM_PROMPT, "temperature": 0.2},
    )
    return strip_wrappers((resp.text or "").strip())


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "来一首最近很火的粤语老情歌，要有磁性的男声伴唱。"
    print("── 输入 ──")
    print(text)
    try:
        print("\n[Gemini 改写中…]")
        print("\n── 输出（发给 Lyria 的 prompt）──")
        print(rewrite(text))
    except SystemExit:
        raise
    except Exception as e:
        print(f"[失败] {type(e).__name__}: {str(e)[:200]}")
