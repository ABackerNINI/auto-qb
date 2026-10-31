"""Memory Bank 写盘形态守卫 (issue 26-10-31-2226-feat-repo-writeform-guard)。

守什么: 工具 shell 写 md 的多类**静默形态事故**(判据单点 pitfalls/git/editing-traps.md,
此前只有人读过文档才知道判别法) —— 全部按字节检测, 闸门当场红:

1. **裸 CR**(\\r 后面不是 \\n): Python 文本模式双重转换(`\\r\\r\\n`)/编辑器残留控制字符,
   肉眼不可见, cap 计数虚高, 只有逐字节比对才现形。
2. **同文件 CRLF + LF 混排**: 一次写回只翻了一部分的签名(sed -i / 文本模式写回半截)。
3. **逐字符一行**(行数巨大且 bytes-per-line 极低): Edit 工具逐字符折行的实证件
   (18,579B/4,935 行 = 3.8B/行)存在数月, 只有守卫才能拦住下一份。

**全 CRLF 文件不判红**: 仓库 2026-10-02 起 `.gitattributes eol=lf`, blob 侧提交必归一,
存量工作区 CRLF 属层 3 一次性转 LF 暂缓范围(editing-traps 首节), 不是本轮缺陷类。

**存量冻结(债务制)**: `FROZEN_WAIVERS` 里的文件已知坏形态、暂不修(逐字符一行无法
无损复原行结构), 只拦新增; 文件被删则豁免条目失效, 一并报错防空挂。

## 测试计划

- test_md_no_bare_cr: memory-bank 全部 md 无裸 CR(\\r 不接 \\n)
- test_md_no_mixed_line_endings: 同一文件内不混排 CRLF 与 LF
- test_md_no_char_per_line_form: 无「行数>=300 且 bytes-per-line<8」的逐字符一行形态
- test_frozen_waivers_are_live: 冻结豁免清单里的文件必须仍存在(防空挂豁免)
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MB = ROOT / "memory-bank"

# 形态异常阈值 (2026-10-31 全仓标定: 唯一命中者是下面的实证件; 健康文件 bytes-per-line 最低 > 20)
CHAR_PER_LINE_MIN_LINES = 300
CHAR_PER_LINE_MAX_BYTES_PER_LINE = 8

# 存量冻结: {仓库根相对路径: 原因} —— 已知坏形态暂不修, 只拦新增 (check_wording 冻结同款纪律)
FROZEN_WAIVERS: dict[str, str] = {
    "memory-bank/pitfalls/web-ui/attachments/drawer-switch-flicker-2026-10-04-07-recurrences.md":
        "Edit 工具逐字符一行实证件 (18,579B/4,935 行, bytes-per-line=3.8); 行结构无法无损复原, 留作守卫活体样本",
}


def _md_files() -> list[Path]:
    return sorted(MB.rglob("*.md"))


def _stats(raw: bytes) -> tuple[int, int, int, int]:
    """(crlf, 裸 CR, 纯 LF 行, 行数) —— 按字节, 不走文本模式(文本模式会把 \\r\\n 折成 \\n)。"""
    crlf = raw.count(b"\r\n")
    cr = raw.count(b"\r")
    lf = raw.count(b"\n")
    bare_cr = cr - crlf
    lf_only = lf - crlf
    lines = lf + (1 if raw and not raw.endswith(b"\n") else 0)
    return crlf, bare_cr, lf_only, lines


def test_md_no_bare_cr() -> None:
    bad = []
    for p in _md_files():
        _, bare_cr, _, _ = _stats(p.read_bytes())
        if bare_cr:
            bad.append(f"{p.relative_to(ROOT).as_posix()}: 裸 CR x{bare_cr}")
    assert not bad, (
        "发现裸 CR(\\r 后面不是 \\n) —— 文本模式双重转换/控制字符残留, 肉眼不可见; "
        "修法: 字节级归一 open(p,'rb') 读入后剔除裸 \\r 再 write_bytes; 逐处:\n" + "\n".join(bad)
    )


def test_md_no_mixed_line_endings() -> None:
    bad = []
    for p in _md_files():
        crlf, _, lf_only, _ = _stats(p.read_bytes())
        if crlf and lf_only:
            bad.append(f"{p.relative_to(ROOT).as_posix()}: CRLF x{crlf} + LF x{lf_only} 混排")
    assert not bad, (
        "同一文件内 CRLF 与 LF 混排 —— 写回只翻了一部分的签名; "
        "修法: 字节级归一 write_bytes(read_bytes().replace(b'\\r\\n', b'\\n')); 逐处:\n" + "\n".join(bad)
    )


def test_md_no_char_per_line_form() -> None:
    bad = []
    for p in _md_files():
        rel = p.relative_to(ROOT).as_posix()
        if rel in FROZEN_WAIVERS:
            continue
        raw = p.read_bytes()
        crlf, _, _, lines = _stats(raw)
        if lines >= CHAR_PER_LINE_MIN_LINES and len(raw) / lines < CHAR_PER_LINE_MAX_BYTES_PER_LINE:
            bad.append(f"{rel}: {len(raw)}B/{lines} 行 = {len(raw) / lines:.1f}B/行")
    assert not bad, (
        "发现逐字符一行形态(行数巨大且 bytes-per-line 极低) —— Edit 工具折行事故; "
        "新写的按 editing-traps.md 处置重写, 存量无法复原的进 FROZEN_WAIVERS 并说明; 逐处:\n" + "\n".join(bad)
    )


def test_frozen_waivers_are_live() -> None:
    missing = [rel for rel in FROZEN_WAIVERS if not (ROOT / rel).is_file()]
    assert not missing, ("冻结豁免清单里有文件已不存在 —— 豁免是给存量坏形态的活体样本挂的, 文件删了就该清条目: " + ", ".join(missing))
