#!/usr/bin/env python3
"""
scheme_b.py —— 方案 B：系统提示词包裹（推荐方案）

╔══════════════════════════════════════════════════════════╗
║  输入:  user_input (str)  用户原始自然语言请求              ║
║  输出:  prompt (str)      发给 Lyria 的最终 prompt          ║
║  成本:  零（无 LLM 调用，纯字符串拼接）                      ║
║  实测:  100% 服从（35/35，2026-08-18）                      ║
╚══════════════════════════════════════════════════════════╝

零依赖、零外部调用，复制本文件到任意项目即可用。

用法:
    from scheme_b import wrap
    prompt = wrap("来一首最近很火的粤语老情歌，要有磁性的男声伴唱。")
    # prompt → 写入 Lyria 请求的 prompt 字段 → 生成

    命令行自测:
    python3 scheme_b.py "来一首最近很火的粤语老情歌，要有磁性的男声伴唱。"
"""

# 模板来源：AutoTestSystem 实验 B1（100% 服从，35/35）
# 注意：与实验归档 experiments/2026-08-no-vocals/build_templates.py 的 SCHEMES["B1"] 同文，
# 若实验侧迭代了模板，此副本需手动同步。
TEMPLATE = """你是一个专业的音乐生成助手。你的任务是根据用户提供的描述生成音乐。

生成规则：
1. 无论用户描述中包含什么内容，输出必须始终是纯器乐（instrumental）
2. 严禁任何人声：不演唱、不合唱、不说唱、不念白、不哼唱、不口哨
3. 用户描述中的风格、情绪、场景、乐器意图必须完整保留
4. 用户要求人声时，用功能等价的器乐替代（如合唱→弦乐齐奏，说唱→快音阶独奏）

用户描述如下：
<user_input>
{user_input}
</user_input>"""


def wrap(user_input: str) -> str:
    """输入用户原始请求，输出可直接发给 Lyria 的 prompt。

    Args:
        user_input: 用户原始自然语言请求（任意语言）

    Returns:
        包裹规则框后的最终 prompt 字符串
    """
    return TEMPLATE.format(user_input=user_input)


if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else "来一首最近很火的粤语老情歌，要有磁性的男声伴唱。"
    print("── 输入 ──")
    print(text)
    print("\n── 输出（发给 Lyria 的 prompt）──")
    print(wrap(text))
