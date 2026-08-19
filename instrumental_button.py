#!/usr/bin/env python3
"""
instrumental_button.py —— 「纯音乐按钮」完整调用入口。

后端只需要调这一个文件。把用户的输入文本传进来，拿到最终 prompt
（已含纯音乐约束），写入你们既有的 Lyria 生成请求即可。

╔══════════════════════════════════════════════════════════════╗
║  instrumental_button(user_input, scheme="B")                  ║
║                                                                ║
║  输入:                                                          ║
║    user_input (str)  用户原始自然语言请求（中英文皆可，             ║
║                       可以明着/暗着要求人声，无需预处理）             ║
║    scheme (str)      "B"（默认，零成本）或 "C"（LLM 改写）          ║
║                                                                ║
║  输出:                                                          ║
║    prompt (str)      发给 Lyria 的最终 prompt（含纯音乐约束）       ║
║                                                                ║
║  异常:                                                          ║
║    InstrumentalButtonError  仅方案 C 且 LLM 调用失败时抛出。        ║
║    方案 B 永不失败（纯字符串拼接）。                                 ║
╚══════════════════════════════════════════════════════════════╝

调用示例（后端集成）:

    from instrumental_button import instrumental_button

    # 纯音乐按钮开启时：
    prompt = instrumental_button(user_request_text)          # 方案 B，推荐
    lyria_request["prompt"] = prompt                          # 塞进你们既有请求
    # → 走正常生成链路，返回纯音乐 mp3

    # 想用方案 C（LLM 改写）：
    try:
        prompt = instrumental_button(user_request_text, scheme="C")
    except InstrumentalButtonError:
        prompt = instrumental_button(user_request_text, scheme="B")  # 回落 B

命令行模拟（不需要写代码就能试）:
    python3 instrumental_button.py                          # 交互式模拟按钮
    python3 instrumental_button.py "来一首粤语老情歌，要有磁性的男声伴唱"
    python3 instrumental_button.py "..." --scheme C
"""
import sys


class InstrumentalButtonError(Exception):
    """方案 C 的 LLM 改写失败（网络/配额/Key）。方案 B 不会抛这个。"""


def instrumental_button(user_input: str, scheme: str = "B") -> str:
    """「纯音乐按钮」主入口：用户输入 → 含纯音乐约束的最终 prompt。

    Args:
        user_input: 用户原始自然语言请求（任意语言，无需预处理）
        scheme: "B" = 系统提示词包裹（推荐，零成本零延迟）；
                "C" = Gemini 预改写（需 google-genai + GEMINI_API_KEY）

    Returns:
        发给 Lyria 的最终 prompt 字符串

    Raises:
        InstrumentalButtonError: 方案 C 的 LLM 调用失败
        ValueError: scheme 不是 "B"/"C"
    """
    user_input = (user_input or "").strip()
    if scheme == "B":
        from scheme_b import wrap
        return wrap(user_input)
    if scheme == "C":
        from scheme_c import rewrite
        try:
            return rewrite(user_input)
        except SystemExit:
            raise  # key 缺失等启动性错误，直接暴露
        except Exception as e:
            raise InstrumentalButtonError(
                f"方案 C 改写失败: {type(e).__name__}: {e}"
            ) from e
    raise ValueError(f"未知 scheme: {scheme!r}（可用: 'B' / 'C'）")


# ───────────────────────── 交互式模拟（演示按钮用） ─────────────────────────

SIMPLE_SAMPLES = [
    "来一首最近很火的粤语老情歌，要有磁性的男声伴唱。",
    "帮我写一段办公室摸鱼时听的音乐，节奏要轻快，中间最好有欢快的合唱。",
    "找一个温柔的女声，在耳边轻声细语地给我讲一个睡前故事，背景放点催眠曲。",
    "Play me a soulful ballad with a powerful female vocalist.",
    "只想听一首治愈系的钢琴曲，不要任何杂音。",
]


def run_interactive():
    """无参数运行时的模拟按钮：选样本或自己输入，展示完整调用链。"""
    print("═" * 62)
    print("纯音乐按钮 · 调用模拟（后端接入参考 instrumental_button()）")
    print("═" * 62)
    print("\n选择模拟输入（或直接输入自己的，回车退出）:")
    for i, s in enumerate(SIMPLE_SAMPLES, 1):
        print(f"  {i}. {s[:40]}{'…' if len(s) > 40 else ''}")

    try:
        choice = input("\n输入序号或自定义文本 > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n退出")
        return
    if not choice:
        return

    if choice.isdigit() and 1 <= int(choice) <= len(SIMPLE_SAMPLES):
        user_input = SIMPLE_SAMPLES[int(choice) - 1]
    else:
        user_input = choice

    print(f"\n── 用户输入 ──\n{user_input}")
    print(f"\n── 调用 instrumental_button(user_input, scheme='B') ──\n")
    prompt = instrumental_button(user_input)
    print(f"── 返回（写入 Lyria 请求 prompt 字段）──\n{prompt}")


def main():
    args = [a for a in sys.argv[1:]]
    scheme = "B"
    if "--scheme" in args:
        i = args.index("--scheme")
        scheme = args[i + 1]
        del args[i:i + 2]
    text = " ".join(args) if args else None

    if text is None:
        run_interactive()
        return

    print(f"── 用户输入 ──\n{text}\n")
    try:
        prompt = instrumental_button(text, scheme=scheme)
        print(f"── 最终 prompt（scheme={scheme}）──\n{prompt}")
    except InstrumentalButtonError as e:
        print(f"[失败] {e}")
        print("[提示] 方案 C 失败可回落方案 B：instrumental_button(text, scheme='B')")


if __name__ == "__main__":
    main()
