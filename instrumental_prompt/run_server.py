#!/usr/bin/env python3
"""API 服务入口(命令行起服务,免记 uvicorn 模块路径语法)

用法(在 demo/ 目录下):
    python3 -m instrumental_prompt.run_server [--host 0.0.0.0] [--port 8300]

等价于:
    uvicorn instrumental_prompt.main:app --host <host> --port <port>

说明:
- 日志带时间戳,排障友好;格式在本文件统一配置
- 单 worker 足够(服务无进程内状态,多实例安全)
"""
import argparse
import logging

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)


def main() -> None:
    ap = argparse.ArgumentParser(description="纯音乐按钮 prompt 服务")
    ap.add_argument("--host", default="0.0.0.0", help="监听地址(默认 0.0.0.0)")
    ap.add_argument("--port", type=int, default=8300, help="端口(默认 8300)")
    args = ap.parse_args()

    from .main import app  # 在 logging 配置之后导入

    uvicorn.run(app, host=args.host, port=args.port, workers=1, reload=False)


if __name__ == "__main__":
    main()
