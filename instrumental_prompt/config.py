"""环境配置集中读取。

key 读取优先级(防共享服务器变量名冲突,见 spec 3.4):
    INSTRUMENTAL_PROMPT_GEMINI_API_KEY(本服务专用)
    > GEMINI_API_KEY(机器上无其他 Gemini 服务时回退复用)

.env 以包定死路径加载,不受启动工作目录影响;
load_config() 每次调用重读 env,便于测试注入。
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# 模块导入时加载一次(demo/.env 定死路径)
load_dotenv(Path(__file__).parent.parent / ".env")

NAMESPACED_KEY_ENV = "INSTRUMENTAL_PROMPT_GEMINI_API_KEY"
GENERIC_KEY_ENV = "GEMINI_API_KEY"
DEFAULT_MODEL = "lyria-3-pro-preview"


@dataclass(frozen=True)
class Config:
    gemini_api_key: str | None
    key_source: Literal["namespaced", "generic", "unset"]
    api_token: str | None
    lyria_model: str


def load_config() -> Config:
    """每次调用重新读环境变量(测试 monkeypatch 后无需重载模块)。"""
    ns = os.environ.get(NAMESPACED_KEY_ENV)
    generic = os.environ.get(GENERIC_KEY_ENV)
    if ns:
        return Config(ns, "namespaced", os.environ.get("API_TOKEN") or None, DEFAULT_MODEL)
    if generic:
        return Config(generic, "generic", os.environ.get("API_TOKEN") or None, DEFAULT_MODEL)
    return Config(None, "unset", os.environ.get("API_TOKEN") or None, DEFAULT_MODEL)
