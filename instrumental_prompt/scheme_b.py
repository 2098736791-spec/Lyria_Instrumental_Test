"""engine B:系统提示词包裹(实测 100% 服从,35/35,2026-08-18)。

零依赖纯函数。模板与实验归档 experiments/2026-08-no-vocals/build_templates.py
的 SCHEMES["B1"] 同文,实验侧迭代需手动同步。
"""
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
    """用户原始请求 → 包含纯音乐约束的最终 prompt。"""
    return TEMPLATE.format(user_input=user_input)
