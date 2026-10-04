"""test_no_o_trunc_write 守阵: src 下 .py 源码零 O_TRUNC 直写, token/凭据类写入一律走 utils.atomic_write。

背景 (issue 26-10-02-0527): issue 26-09-21-1347 §06 悬置的「O_TRUNC 直写静态守阵」, 生效条件
「全 src O_TRUNC 代码清零」已由 bc24631b (hr/channel.py 最后一处直写改 atomic_write) 达成,
2026-10-05 认领落地。危害: 直写在写盘途中被杀会留下非空半截密钥/token 被持久化 —— 两处修复
注释是锚点 (hr/channel.py / webui/server/common.py)。同族修法范式 5965cc07 (web.token) /
bc24631b (hr.token); 唯一合法写盘单点 src/auto_qb/infra/utils.py `def atomic_write`。

判定口径: tokenize 逐文件扫, 非 COMMENT token 的文本含 "O_TRUNC" 即红 —— NAME 覆盖
`os.O_TRUNC` 属性访问, STRING 覆盖 `getattr(os, "O_TRUNC")` 绕行与 docstring 内嵌;
注释豁免 (现存两处修复注释是知识库锚点, 不是直写)。确需直写的场景走 _WHITELIST
(路径 → 理由, 加入前必须评审「确需直写且非 token/凭据类」)。

## 测试计划
- test_src_has_no_o_trunc_write: src 下任何 .py 的非注释 token 出现 O_TRUNC 且不在白名单, 即红
"""

from __future__ import annotations

import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# 显式白名单: 相对 repo 根的 posix 路径 → 理由。
_WHITELIST: dict[str, str] = {}


def _o_trunc_hits() -> list[str]:
    """src 下代码 token 出现 O_TRUNC 的位置 (相对 repo 根路径:行号); 注释与白名单不算。"""
    hits: list[str] = []
    if not SRC.is_dir():
        return hits
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel in _WHITELIST:
            continue
        with tokenize.open(path) as fh:
            for tok in tokenize.generate_tokens(fh.readline):
                if tok.type == tokenize.COMMENT:
                    continue
                if "O_TRUNC" in tok.string:
                    hits.append(f"{rel}:{tok.start[0]}")
    return hits


def test_src_has_no_o_trunc_write():
    hits = _o_trunc_hits()
    assert not hits, (
        "src 下发现 O_TRUNC 直写 (token/凭据类写入必须走 utils.atomic_write, 唯一合法写盘"
        f"单点 src/auto_qb/infra/utils.py def atomic_write; 确需直写走本文件 _WHITELIST 并注明"
        f"理由): {hits}"
    )
