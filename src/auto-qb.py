"""兼容入口: 保持旧命令/launch.json 可用 (python auto-qb.py config.yml)

实际实现已拆分至 auto_qb/ 包, 也可使用 `python -m auto_qb` 运行。
"""
import sys

from auto_qb.cli import main

if __name__ == "__main__":
    sys.exit(main())
