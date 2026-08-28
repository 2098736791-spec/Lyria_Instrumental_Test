"""scheme_lyrics 用例:S2 逐字冻结断言 + S1 全角冒号格式。依据 spec 第四节。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from instrumental_prompt.scheme_lyrics import S1_TEMPLATE, S2_TEMPLATE, merge_s1, merge_s2


def test_s2_template_frozen_literal():
    # 文案逐字冻结(lyrics-merge R1 54 次实测背书),改一字即破坏实测
    assert S2_TEMPLATE == (
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


def test_merge_s2_slots_injected_verbatim():
    out = merge_s2("明亮的日语动漫风", "啦啦啦\n噜噜噜")
    assert "<style>\n明亮的日语动漫风\n</style>" in out
    assert "<lyrics>\n啦啦啦\n噜噜噜\n</lyrics>" in out
    assert out == S2_TEMPLATE.format(style="明亮的日语动漫风", lyrics="啦啦啦\n噜噜噜")


def test_s1_fullwidth_colon():
    # 与实验侧 build_templates.py 同文:全角冒号
    assert S1_TEMPLATE == "风格：{style}\n\n歌词：\n{lyrics}"
    out = merge_s1("粤语流行", "风吹哪日")
    assert out == "风格：粤语流行\n\n歌词：\n风吹哪日"
