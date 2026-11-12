"""`web_shortcuts_support` 支撑: 从 `test_web_shortcuts.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

from __future__ import annotations

import re
from pathlib import Path

from webui_helpers import read_shared

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "auto_qb" / "webui" / "static"
SHARED = STATIC / "shared"
# 皮肤清单单点在 webui_helpers._UI_ALL(atlas/prism/console/flux, issue 26-11-13-0443 收编旧三皮肤
# 枚举 UIS)—— 本模块不再另立枚举, 消费方一律 from webui_helpers import _UI_ALL

# 归一化串合法形态: 单一事实源在后端 routes/keys.py::_KEYS_SERIAL_RE(2026-10-15 消第三份手抄,
# issue 26-10-11-0310) —— 与 shortcuts.js KB_DEF_RE 的跨层逐字一致由
# tests/webui_static_scan_js.py::_scan_keys_serial_re 机械守阵
from auto_qb.webui.server.routes.keys import _KEYS_SERIAL_RE as KB_DEF_RE

KB_SCOPES = {"global", "list", "drawer", "settings", "modal"}


def _read(rel: str) -> str:
    return read_shared(rel)


def _registry() -> list[dict]:
    """解析 shortcuts.js 的 AQB_SHORTCUT_DEFS(条目字段按固定书写序, 逐条正则提取)"""
    text = _read("shortcuts.js")
    m = re.search(r"const AQB_SHORTCUT_DEFS = \[(.*?)\n\];", text, re.S)
    assert m, "shortcuts.js 找不到 AQB_SHORTCUT_DEFS 注册表(单一事实源被改名/搬走?)"
    out = []
    for chunk in re.split(r'\{ id: "', m.group(1))[1:]:
        item = {
            "id": chunk.split('"', 1)[0],
            "group": _pick(chunk, r'group: "([^"]*)"'),
            "label": _pick(chunk, r'label: "([^"]*)"'),
            "def": _pick(chunk, r'def: "([^"]*)"'),
            "scope": _pick(chunk, r'scope: "(\w+)"'),
            "danger": 'danger: true' in chunk,
            "fixed": 'fixed: true' in chunk,
            "inputSafe": 'inputSafe: true' in chunk,
            "repeat": 'repeat: true' in chunk,
            "when": _pick(chunk, r"when: \(vm\) => vm\.(\w+)"),
            "run_null": "run: null" in chunk,
            "runs": re.findall(r"run: \(vm\) => vm\.(\w+)\(", chunk),
        }
        out.append(item)
    assert out, "注册表解析出 0 条(书写格式漂移? 同步本守阵的解析)"
    return out


def _pick(chunk: str, pattern: str) -> str:
    m = re.search(pattern, chunk)
    return m.group(1) if m else ""


# 浏览器保留键黑名单(与 shortcuts.js KB_BLACKLIST 语义一致, 此处按计划 §3.3 边界独立抄录:
# 默认键表绝不允许出现这些 —— 面板(W6)拒绑是运行时防线, 本断言是默认表的事前防线)
BLACKLIST = set()

for _c in ("KeyW", "KeyT", "KeyN", "KeyQ"):
    BLACKLIST |= {f"Ctrl+{_c}", f"Ctrl+Shift+{_c}"}

BLACKLIST |= {
    "Ctrl+Tab", "Ctrl+Shift+Tab", "F5", "F11", "F12", "Ctrl+Shift+KeyN", "Ctrl+Shift+KeyI", "Ctrl+Shift+KeyJ",
    "Ctrl+Shift+KeyC"
}

BLACKLIST |= {f"Ctrl+Digit{i}" for i in range(1, 9)}
