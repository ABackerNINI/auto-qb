"""test_webui_static_dom_panel_gtm_alert 测试计划: GTM 当日总量虚高告警的常驻横幅守阵

## 测试计划(每个测试函数一条)

- test_frontend_gtm_alert_banner_single_source: 主告知常驻横幅的静态契约(计划 26-11-03-1102 S7c / D5) ——
  1. `shared/tpl/statusbar.html` 含 `.sb-gtm-alert` 组且 `v-if="gtmAlert"` **不在** `v-if="todayTraffic"` 的
  template 分支里(常驻可见, 不依赖今日流量); 2. DOM 顺序钉死:`sb-gtm-alert` 必须出现在 `.sb-stats` 之前;
  3. 交互两件套在模板里(点横幅 `showGtmAlert()`, `×` `ackGtmAlert()`), 模板本身不碰 localStorage;
  4. 判空/24h/ack 单点在 `dialogs.js`(`gtmAnomaly()` / `gtmAlert()` / `GTM_ACK_KEY="gtm.spike.ack"` /
  `GTM_ALERT_TTL_MS = 24 * 3600 * 1000`), ack 只写本机; 5. 模板与样式都是 shared 单点 —— 四套皮肤
  (`webui_helpers._UI_ALL`)全部引用 `/shared/tpl/statusbar.html`, 皮肤目录里既没有同族模板, 也不得重复
  定义 `.sb-gtm-alert` / `.sb-gtm-main` / `.sb-gtm-ack` 三个类名; 6. 窄屏纪律: 横幅 `flex: 0 1 auto` +
  `min-width: 0` + 文案 ellipsis, 不挤压右侧 `.sb-speed`(flex: 0 0 auto)。
- test_frontend_gtm_alert_helper_matrix: `gtmAnomaly()` 判空矩阵与 24h 边界的行为面(node 电池真跑,
  无 node 静默跳过) —— 键缺失 / null / 非对象(含数组) / 缺 ts / ts 不可解析 / items 为空 / items 无一条
  可用 -> 全部 null(横幅整段不渲染, T30 降级); 合法载荷 -> 短版(多方向 +N)与完整版(ts / delta+dt_s /
  阈值)成形; ack 同 ts -> 隐藏且 localStorage 键值 = ts, ack 不同 ts -> 重显; ts 恰好 24h -> 仍显示,
  24h+1s -> 隐藏。
"""

import json

import os

import re

import shutil

import subprocess

from webui_helpers import (
    STATIC_ROOT,
    _UI_ALL,
)

_SHARED = os.path.join(STATIC_ROOT, "shared")
_TPL = os.path.join(_SHARED, "tpl", "statusbar.html")
_DIALOGS = os.path.join(_SHARED, "dialogs.js")
_CSS = os.path.join(_SHARED, "console_hub_controls.css")

_NODE_GTM_ALERT_PROBE = r"""
const fs = require("fs");
global.window = {};
const store = Object.create(null);
global.localStorage = {
  getItem: (k) => (Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; },
};
eval(fs.readFileSync(process.argv[1], "utf8"));   // dialogs.js(判定与交互单点)
const D = window.AQB_DIALOGS;

/* 与 shared/format.js 同梯(1024 进制)的显示桩: 断言只关心"人类可读", 不测格式器本身 */
function fmtSpeed(v) {
  if (!v) return "0 B/s";
  const ladder = [[2 ** 30, "GiB/s"], [2 ** 20, "MiB/s"], [2 ** 10, "KiB/s"]];
  for (const [n, u] of ladder) if (v >= n) return (v / n).toFixed(2) + " " + u;
  return v + " B/s";
}
function fmtSize(v) {
  if (v === null || v === undefined) return "-";
  if (!v) return "0 B";
  const ladder = [[2 ** 40, "TiB"], [2 ** 30, "GiB"], [2 ** 20, "MiB"], [2 ** 10, "KiB"]];
  for (const [n, u] of ladder) if (v >= n) return (v / n).toFixed(2) + " " + u;
  return v + " B";
}
const ctx = (traffic, nowSec) => ({
  traffic,
  status: { traffic },
  nowSec,
  fmtSpeed,
  fmtSize,
  get gtmAnomaly() { return D.computed.gtmAnomaly.call(this); },
  get gtmAlert() { return D.computed.gtmAlert.call(this); },
});

const ITEM_UP = { nic: "以太网", dir: "up", cur: 1115700, last: 800, delta: 273400, rate_bps: 58720255996 };
const ITEM_DOWN = { nic: "Wi-Fi", dir: "down", cur: 980000, last: 500, delta: 120000, rate_bps: 104857600 };
const TS1 = "2026-11-03T10:47:28+08:00";
const TS2 = "2026-11-03T11:02:15+08:00";
const T1 = Date.parse(TS1);
const spike = (ts, items) => ({
  ts, dt_s: 5.0, eff_dt_s: 5.0, threshold_bps: 1073741824, items,
});

const out = {};
const a = (traffic, now) => ctx(traffic, now + 60).gtmAlert;   // 默认"异常发生在 1 分钟前"
out.missingKey = a({}, T1) === null;
out.nullValue = a({ gtm_anomaly: null }, T1) === null;
out.nonObject = a({ gtm_anomaly: "spike" }, T1) === null;
out.arrayValue = a({ gtm_anomaly: [] }, T1) === null;
out.missingTs = a({ gtm_anomaly: { items: [ITEM_UP] } }, T1) === null;
out.badTs = a({ gtm_anomaly: { ts: "not-a-date", items: [ITEM_UP] } }, T1) === null;
out.emptyItems = a({ gtm_anomaly: { ts: TS1, items: [] } }, T1) === null;
out.noItems = a({ gtm_anomaly: { ts: TS1 } }, T1) === null;
out.badItem = a({ gtm_anomaly: { ts: TS1, items: [{ nic: "以太网", dir: "up", rate_bps: "abc" }] } }, T1) === null;

const ok = ctx({ gtm_anomaly: spike(TS1, [ITEM_UP]) }, T1 / 1000 + 60);
const okAlert = ok.gtmAlert;
out.valid = okAlert !== null;
out.short = okAlert ? okAlert.short : null;
out.full = okAlert ? okAlert.full : null;

const multi = ctx({ gtm_anomaly: spike(TS1, [ITEM_UP, ITEM_DOWN]) }, T1 / 1000 + 60).gtmAlert;
out.multiShort = multi ? multi.short : null;
out.multiFullHasDown = multi ? multi.full.indexOf("Wi-Fi") >= 0 : false;

/* 24h 边界: 恰好 24h 仍显示(不超过才隐藏), 24h+1s 隐藏 */
out.at24h = ctx({ gtm_anomaly: spike(TS1, [ITEM_UP]) }, (T1 + 24 * 3600 * 1000) / 1000).gtmAlert !== null;
out.after24h = ctx({ gtm_anomaly: spike(TS1, [ITEM_UP]) }, (T1 + 24 * 3600 * 1000 + 1000) / 1000).gtmAlert === null;

/* ack: 同 ts 隐藏 + 键值 = ts; 新 ts 自动重显 */
store["gtm.spike.ack"] = TS1;
out.ackSameTs = ctx({ gtm_anomaly: spike(TS1, [ITEM_UP]) }, T1 / 1000 + 60).gtmAlert === null;
out.ackOtherTs = ctx({ gtm_anomaly: spike(TS2, [ITEM_UP]) }, T1 / 1000 + 60).gtmAlert !== null;

/* ackGtmAlert 只写 localStorage, 且写的就是当前 ts */
delete store["gtm.spike.ack"];
const actx = ctx({ gtm_anomaly: spike(TS1, [ITEM_UP]) }, T1 / 1000 + 60);
D.methods.ackGtmAlert.call(actx);
out.ackWritesTs = store["gtm.spike.ack"] === TS1;
out.ackThenHidden = actx.gtmAlert === null;

console.log(JSON.stringify(out));
"""


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_frontend_gtm_alert_banner_single_source():
    """常驻横幅: 模板位置/降级分支/交互接线/共享来源/皮肤零重复/窄屏纪律。"""
    tpl = _read(_TPL)
    tpl_code = re.sub(r"<!--.*?-->", "", tpl, flags=re.S)  # 注释里的说明不算"模板读写"
    js = _read(_DIALOGS)
    css = _read(_CSS)

    # 1. 常驻组与 v-if, 且不在 todayTraffic 的 template 分支内(不依赖今日流量)
    assert 'class="sb-item sb-gtm-alert"' in tpl, "statusbar 缺常驻横幅组(.sb-item.sb-gtm-alert)"
    assert 'v-if="gtmAlert"' in tpl, "横幅必须由 gtmAlert 驱动(v-if)"
    m = re.search(r'v-if="todayTraffic"(.*?)</template>', tpl, re.S)
    assert m, "statusbar 的 todayTraffic 分支结构变了(守阵需同步)"
    assert "sb-gtm-alert" not in m.group(1), "横幅落在 todayTraffic 分支内 -> 无今日流量时告警不可见"

    # 2. DOM 顺序: 必须在 .sb-stats 之前(告警优先于统计摘要)
    i_alert = tpl.index("sb-gtm-alert")
    i_stats = tpl.index('<span class="sb-stats">')
    assert i_alert < i_stats, "横幅必须排在 .sb-stats 之前"

    # 3. 交互两件套 + 模板不碰 localStorage
    assert 'class="sb-gtm-ack"' in tpl and "ackGtmAlert()" in tpl, "缺 × 消警按钮/接线"
    assert "showGtmAlert()" in tpl, "点横幅看完整文案的接线缺失"
    assert "localStorage" not in tpl_code, "模板不得直接读写 localStorage(单点应在 dialogs.js)"

    # 4. 判定与 ack 单点
    for anchor in ("gtmAnomaly()", "gtmAlert()", "ackGtmAlert()", "showGtmAlert()"):
        assert anchor in js, f"dialogs.js 缺 {anchor}"
    assert 'GTM_ACK_KEY = "gtm.spike.ack"' in js, "本机 ack 键必须与计划/测试矩阵一致"
    assert "GTM_ALERT_TTL_MS = 24 * 3600 * 1000" in js, "24h 展示窗口单点缺失"
    assert "localStorage.setItem(GTM_ACK_KEY, a.ts)" in js, "ack 必须只写本机(键值 = ts)"
    assert "gtm_anomaly" in js, "gtmAnomaly 必须从 traffic.gtm_anomaly 取数"

    # 5. 共享来源: 四皮肤都引用同一 statusbar 模板; 皮肤目录零重复模板/样式
    for skin in _UI_ALL:
        shell = _read(os.path.join(STATIC_ROOT, skin, "index.html"))
        assert "/shared/tpl/statusbar.html" in shell, f"{skin} 未引用 shared statusbar 模板"
        assert "/shared/console_hub_controls.css" in shell, f"{skin} 未引用 shared 控件样式单点"
        assert not os.path.isfile(os.path.join(STATIC_ROOT, skin, "tpl", "statusbar.html")), \
            f"{skin} 出现皮肤私有 statusbar 模板(模板必须单点)"
        for dirpath, _, names in os.walk(os.path.join(STATIC_ROOT, skin)):
            for name in names:
                if not name.endswith(".css"):
                    continue
                text = _read(os.path.join(dirpath, name))
                for cls in (".sb-gtm-alert", ".sb-gtm-main", ".sb-gtm-ack"):
                    assert cls not in text, \
                        f"{skin}/{name} 重复定义 {cls}(样式单点必须在 shared/console_hub_controls.css)"
    for cls in (".sb-gtm-alert {", ".sb-gtm-main {", ".sb-gtm-ack {"):
        assert cls in css, f"shared/console_hub_controls.css 缺 {cls} 规则"

    # 6. 窄屏: 只吃剩余空间 + 文案省略, 不挤压速度组
    assert "flex: 0 1 auto" in css and "min-width: 0" in css, "横幅必须允许收缩(min-width: 0)"
    assert "max-width: min(440px, 46vw)" in css, "横幅缺窄屏宽度上限"
    assert "text-overflow: ellipsis" in css, "横幅文案缺省略号(窄屏会撑破状态栏)"


def test_frontend_gtm_alert_helper_matrix():
    """判空矩阵 / 24h 边界 / ack 重显 / 文案成形(node 真跑; 无 node 静默跳过)。"""
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _NODE_GTM_ALERT_PROBE, _DIALOGS],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"GTM 告警 node 电池跑挂: {proc.stderr.strip()}"
    out = json.loads(proc.stdout.strip().splitlines()[-1])

    null_cases = (
        "missingKey", "nullValue", "nonObject", "arrayValue", "missingTs", "badTs", "emptyItems", "noItems", "badItem"
    )
    for key in null_cases:
        assert out[key] is True, f"判空矩阵失效: {key} 未按「无异常」降级(横幅会误渲染)"
    assert out["valid"] is True, "合法 gtm_anomaly 必须成形(否则横幅永不出现)"
    assert "以太网" in out["short"] and "上行" in out["short"] and "GiB/s" in out["short"], \
        f"短版文案不符: {out['short']}"
    assert out["full"].startswith("最近异常：") and "5s" in out["full"] and "GiB/s" in out["full"], \
        f"完整版缺 ts/delta+dt_s/阈值信息: {out['full']}"
    assert "以太网" in out["full"] and "阈值" in out["full"], f"完整版文案不符: {out['full']}"
    assert out["multiShort"].endswith("+1"), f"多方向短版必须追加 +N: {out['multiShort']}"
    assert out["multiFullHasDown"] is True, "完整版必须逐条并列(含第二个方向)"
    assert out["at24h"] is True, "ts 恰好 24h 内应仍显示"
    assert out["after24h"] is True, "超过 24h 必须隐藏"
    assert out["ackSameTs"] is True, "同一 ts 已 ack 后必须隐藏"
    assert out["ackOtherTs"] is True, "新 ts 不同必须自动重显"
    assert out["ackWritesTs"] is True, "ackGtmAlert 写的键值必须是当前 ts"
    assert out["ackThenHidden"] is True, "ack 之后本机应立即隐藏"
