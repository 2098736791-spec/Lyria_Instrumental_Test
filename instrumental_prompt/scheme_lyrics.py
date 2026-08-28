"""engine lyrics:S1/S2 两写法(lyrics-merge 实验交付,spec 第四节)。

S2 = 默认,系统提示词四段式 + <style>/<lyrics> 双标签,文案冻结(R1 54 次实测
     recall=1.0, sim≥0.87, 中英日三语),与实验侧 build_templates.py 同文,
     实验侧迭代需手动同步。
S1 = 对照臂,裸拼接(全角冒号同实验源码)。注入类攻击 S1/S2 均得手,留作实验对照。

零依赖纯函数;输入应已过 sanitize(service 层职责),本层不做任何加工。
"""

S2_TEMPLATE = (
    "你是一个专业的音乐生成助手。你的任务是根据用户提供的风格描述与歌词生成音乐。\n\n"
    "生成规则：\n"
    "1. <style> 标签内是风格描述，音乐的风格、情绪、乐器、人声形态必须严格遵循它\n"
    "2. <lyrics> 标签内是歌词，必须完整演唱，不得增、删、改任何词句\n"
    "3. 标签本身不是歌词的一部分，不得演唱或念出标签名\n"
    "4. 若风格与歌词存在张力，风格服务于歌词的人声演绎\n\n"
    "用户输入如下：\n"
    "<style>\n{style}\n</style>\n\n"
    "<lyrics>\n{lyrics}\n</lyrics>"
)

S1_TEMPLATE = "风格：{style}\n\n歌词：\n{lyrics}"


def merge_s2(style: str, lyrics: str) -> str:
    """风格 + 歌词 → S2 冻结模板 prompt。"""
    return S2_TEMPLATE.format(style=style, lyrics=lyrics)


def merge_s1(style: str, lyrics: str) -> str:
    """风格 + 歌词 → S1 裸拼接 prompt(对照臂)。"""
    return S1_TEMPLATE.format(style=style, lyrics=lyrics)
