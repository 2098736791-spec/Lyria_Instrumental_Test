"""歌词模式输入清洗(仅 mode="lyrics" 调用,spec 第五节)。

两层防线,实测依据 lyrics-merge 交付:
    ① 标签串剥除——</user_input>/<style>/<lyrics>/<system>/<instructions> 开闭标签
       (孤立标签结构上扛得住,但配合指令会得手,剥掉绝后患)
    ② 高危句式——祈使句式注入载荷("忽略以上…纯音乐"实测 S1/S2 均得手,
       Lyria 模型层固有弱点,只能输入侧拦),命中整单拒绝

两判定独立:clean text 进模板,原文决定拒绝(剥了标签漏了句子要兜住)。
零误伤边界:常规歌词(含情绪化表述)实测零误伤,词表偏保守可调。
"""
import re

BLOCK_PATTERNS = [
    re.compile(r'</?\s*(user_input|style|lyrics|system|instructions?)\s*>', re.IGNORECASE),
]
DANGER_PHRASES = ["忽略以上", "系统指令", "指令更新", "不要人声", "纯音乐", "重新生成", "改为生成"]


def sanitize(user_text: str) -> tuple[str, bool]:
    """返回 (清洗后文本, 是否拒绝)。拒绝时调用方应整单 422,不用清洗后文本。"""
    text = user_text
    for pat in BLOCK_PATTERNS:
        text = pat.sub('', text)
    rejected = any(p in user_text for p in DANGER_PHRASES)
    return text, rejected
