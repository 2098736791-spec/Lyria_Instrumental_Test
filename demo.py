#!/usr/bin/env python3
"""
demo.py —— 纯音乐按钮后端演示入口。

两个方案已解耦为独立模块（拿走即用）:
  - scheme_b.py  【推荐】系统提示词包裹：wrap(user_input) -> prompt，零 LLM 成本
  - scheme_c.py  【备选】Gemini 预改写：  rewrite(user_input) -> prompt，需 LLM 调用

本文件夹可整体拷走独立运行（方案 B 零依赖；方案 C 需 google-genai + GEMINI_API_KEY）。

用法:
  python3 demo.py "用户输入"             # 两条路线都展示
  python3 demo.py "用户输入" --method B  # 只看方案 B
  python3 demo.py "用户输入" --method C  # 只看方案 C（真调 Gemini）
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scheme_b import wrap as b_wrap
from scheme_c import rewrite as c_rewrite


def main():
    parser = argparse.ArgumentParser(description="纯音乐按钮后端演示")
    parser.add_argument("user_input", help="模拟用户输入（自然语言）")
    parser.add_argument("--method", choices=["B", "C", "all"], default="all")
    args = parser.parse_args()

    line = "─" * 60
    print("═" * 60)
    print("纯音乐按钮 · 后端演示（方案模块：scheme_b.py / scheme_c.py）")
    print("═" * 60)
    print(f"\n[用户输入]\n{args.user_input}")

    if args.method in ("B", "all"):
        print(f"\n{line}\n【方案 B · 推荐】系统提示词包裹（scheme_b.wrap，零 LLM 成本）\n{line}")
        prompt = b_wrap(args.user_input)
        print(f"\n[输出·发给 Lyria 的 prompt]\n{prompt}")

    if args.method in ("C", "all"):
        print(f"\n{line}\n【方案 C · 备选】Gemini 预改写（scheme_c.rewrite，需 LLM）\n{line}")
        print("\n[Gemini 改写中…]")
        try:
            prompt = c_rewrite(args.user_input)
            print(f"[输出·发给 Lyria 的 prompt]\n{prompt}")
        except SystemExit:
            raise
        except Exception as e:
            print(f"[方案 C 失败] {type(e).__name__} {str(e)[:150]}")

    print()


if __name__ == "__main__":
    main()
