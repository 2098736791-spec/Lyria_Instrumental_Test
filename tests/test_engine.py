"""engine 层用例:B 包裹纯函数 / C 提示词与输出后处理。零网络。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from instrumental_prompt import scheme_b, scheme_c


def test_wrap_contains_rules_and_input():
    prompt = scheme_b.wrap("来一首粤语老情歌，要有磁性的男声伴唱。")
    assert "<user_input>" in prompt and "</user_input>" in prompt
    assert "来一首粤语老情歌，要有磁性的男声伴唱。" in prompt
    assert "严禁任何人声" in prompt  # 规则在场
    assert "instrumental" in prompt  # 规则 1 关键词在场


def test_wrap_idempotent_shape():
    # 同输入两次包裹结果一致(纯函数)
    assert scheme_b.wrap("Pop") == scheme_b.wrap("Pop")


def test_strip_wrappers_removes_code_fence():
    assert scheme_c.strip_wrappers("```json\n纯音乐, 情歌\n```") == "纯音乐, 情歌"


def test_strip_wrappers_removes_quotes():
    assert scheme_c.strip_wrappers('"纯音乐, 情歌"') == "纯音乐, 情歌"
    assert scheme_c.strip_wrappers("「纯音乐」") == "纯音乐"


def test_strip_wrappers_plain_untouched():
    assert scheme_c.strip_wrappers("纯音乐, 情歌") == "纯音乐, 情歌"


def test_system_prompt_unchanged_asset():
    # 提示词是实验资产,校验锚点(100% 服从的 C1 提示词,一个字不改)
    assert "纯音乐的结构化提示词" in scheme_c.SYSTEM_PROMPT
    assert "不做人声替代" in scheme_c.SYSTEM_PROMPT
    assert "GEMINI_MODEL" not in scheme_c.SYSTEM_PROMPT
