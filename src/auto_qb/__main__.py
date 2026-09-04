"""支持 `python -m auto_qb` 运行"""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
