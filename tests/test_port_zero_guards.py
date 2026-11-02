"""测试侧端口改 0 的守阵(计划 26-11-03-0316 §09)。

## 测试计划
- test_harness_port_contract: e2e/harness.mjs 不含固定口/静态 BASE_URL, 含 WAIT_STDOUT 与 baseUrl
- test_playwright_web_server_uses_wait: webServer 用 wait 捕获, 无 url/port, reuseExistingServer=false
- test_ui_harness_defaults_to_zero: --port 默认 0, 打印行使用实绑端口变量
- test_e2e_selfcheck_no_fixed_blocking: 不再有 DEFAULT_E2E_PORT, 不把 E2E_PORT 当默认口
- test_e2e_selfcheck_rejects_e2e_port: 设置 E2E_PORT 时自检退非 0 并说明原因
- test_dev_webui_defaults_to_zero: --web-port 默认 0, 无 8177/顺延链
- test_global_teardown_reads_captured_port: teardown 读 UI_HARNESS_PORT, 不导入固定 PORT
- test_no_reusable_port_helper_in_scripts: scripts/ 下无取号模块/`def free_port`
- test_tests_real_free_port_has_rebind_selfcheck: tests-real 取号含回绑自验且 RETRIES=3
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_harness_port_contract():
    text = _read("e2e/harness.mjs")
    assert "8137" not in text, "e2e/harness.mjs 不得再出现固定口 8137"
    assert "export const BASE_URL" not in text, "BASE_URL 静态常量已删除, spec 一律 baseUrl() 懒取值"
    assert "Number(process.env.E2E_PORT" not in text, "E2E_PORT 不得再作为端口来源"
    assert "process.env.E2E_PORT" not in text, "只允许 `'E2E_PORT' in process.env` 的存在性检测"
    assert "WAIT_STDOUT" in text and "export function baseUrl" in text
    assert "--port 0" in text, "起桩命令必须显式 --port 0"


def test_playwright_web_server_uses_wait():
    text = _read("playwright.config.mjs")
    assert "baseURL:" not in text, "配置对象求值早于 wait 注入, 不得设 use.baseURL"
    block = text.split("webServer: {", 1)[1]
    assert "wait:" in block and "WAIT_STDOUT" in block
    assert "url:" not in block and "port:" not in block, "url/port 与 wait 互斥"
    assert "reuseExistingServer: false" in block


def test_ui_harness_defaults_to_zero():
    text = _read("scripts/ui_harness.py")
    assert "8099" not in text, "桩服务默认口不得回退到 8099"
    assert 'default=0' in text and '"--port"' in text
    assert "127.0.0.1:{actual}" in text, "打印行必须用实绑端口(捕获契约)"
    assert "run(sockets=[sock])" in text, "预绑 socket 必须交给 uvicorn 持有(无 TOCTOU)"


def test_e2e_selfcheck_no_fixed_blocking():
    text = _read("scripts/e2e_selfcheck.py")
    assert "DEFAULT_E2E_PORT" not in text
    assert "8137" not in text
    assert 'os.environ.get("E2E_PORT")' not in text, "E2E_PORT 不得再作默认拦断口"


def test_e2e_selfcheck_rejects_e2e_port(monkeypatch, capsys):
    monkeypatch.setenv("E2E_PORT", "6553")
    monkeypatch.syspath_prepend(str(REPO / "scripts"))
    import e2e_selfcheck

    rc = e2e_selfcheck.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "E2E_PORT 已取消" in out
    assert "RESULT: 环境自检未过" in out


def test_dev_webui_defaults_to_zero():
    text = _read("scripts/dev_webui.py")
    assert "8177" not in text
    assert "_pick_web_port" not in text and "range(want + 1" not in text
    assert '"--web-port", type=int, default=0' in text
    assert "s.bind((args.web_host, 0))" in text, "0 必须就地取具体口后再落盘"


def test_global_teardown_reads_captured_port():
    text = _read("e2e/global-teardown.mjs")
    assert "UI_HARNESS_PORT" in text
    assert "import { PORT }" not in text and "from './harness.mjs'" not in text
    assert "8137" not in text, "收尾不得按固定口拼正则"


def test_no_reusable_port_helper_in_scripts():
    assert not (REPO / "scripts" / "_ports.py").exists(), "不新建共享取号模块"
    needle = "def free" + "_port("  # 拆开写: 本文件源码不得被 test_free_port 的散落扫描命中
    offenders = [p.name for p in (REPO / "scripts").glob("*.py") if needle in p.read_text(encoding="utf-8")]
    assert not offenders, f"scripts/ 下不得出现取号实现: {offenders}"


def test_tests_real_free_port_has_rebind_selfcheck():
    text = _read("tests-real/lib/app.py")
    assert "回绑自验" in text
    assert "RETRIES = 3" in text, "重试上限须与 tests/_test_ports.py 对齐"
    assert 'probe.bind(("127.0.0.1", port))' in text, "探空后必须再次 bind 自验"
    assert "raise RuntimeError" in text, "耗尽必须响亮报错"
