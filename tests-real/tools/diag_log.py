"""打印某个实例的 qB 日志尾部(定位 tracker/announce 问题用)。用法: uv run python tests-real/tools/diag_log.py 36596 [条数]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from lib import instances  # noqa: E402

port = int(sys.argv[1]) if len(sys.argv) > 1 else instances.SECONDARY
n = int(sys.argv[2]) if len(sys.argv) > 2 else 120

qb = instances.make(port)
entries = json.loads(qb._call(f"/log/main?last_known_id=-1"))
for e in entries[-n:]:
    print(f"{e['timestamp']} [{e['type']}] {e['message']}")
