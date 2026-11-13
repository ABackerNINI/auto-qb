"""test_webui_static_dom_panel_misc 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

## 测试计划(每个测试函数一条)

- test_frontend_ctx_submenu_single_entry_and_hover_close: 右键次级菜单守阵 —— 次级入口由注册表声明、渲染层计数(「更多操作」+「转移到」, 模板骨架单份; 原 CTX-06 单入口断言随「转移到」入口过期, R5#30)、移出父项后延迟收起(CTX-05)、hover 图标规则必须限定直接子级且压特异性否则整片子面板变灰(CTX-04)
- test_frontend_reannounce_inactive_gate_wiring: 非活跃种子禁强制汇报(qB 口径)入口接线守阵(2026-10-10; 2026-10-17 扩段删除链, issue 26-10-17-1703) —— qB 的 Force reannounce 仅在种子活跃时可用(commit aa189a7 关闭 issue #12080: isPaused/isChecking/isQueued 时 setEnabled(false)), 本项目沿用同一判据(暂停/停止·排队·校验中·错误/文件丢失): 1. 判定单点 decorate.js 的 REANNOUNCE_BLOCKED_STATES 必含 paused*/stopped*/queued*/checking*/error/missingFiles/**moving** 且**读 qB 原始 state**(kind 现 7 档, 排队仍被归进 downloading/seeding ⇒ 单看 kind 判不出排队; moving 虽自成第 7 档, 后端却不在任何 state_enum 谓词集合里 ⇒ 后端同须判 state 串); 2. 右键菜单 ctx-menus.html 四支(多选/整集/单种子/单组)的强制汇报项都挂 reannounceMenuGate(); 3. 行为层两道 —— _actCore 的 reannounce 前置闸门(早于乐观补丁/POST) + _kbAct 的 reannounce 分支先于 confirmDialog("先问确定再回不行"是坏体感); 4. 详情面板 tracker 页签 04/05/06 三个变体的 data-act=report 钮挂 drawerReannounceGate() + 各变体 .is-gated CSS(压过 base :hover, 含 05 失败区 .dt05-fail 的 (0,4,0) 覆盖) + drawer.js torrentCmd 兜底; 5. 投递收敛 —— 闸门(集合级全有全无, 与 qB oneCanForceReannounce 一致)只管「允不允许」, 放行后「发给谁」由 reannouncePlan 单点收敛为活跃子集(混选时 qB 引擎对非活跃目标静默空转, 照集合全量投递会让 tracker 确认层白等 item deadline 后落假「未确认」, 把一次干净的成功报成部分失败), 回执体现跳过数, 空投递必须显式收口(不得落成功分支报「成功 0 个目标」), 且前后端判据表(REANNOUNCE_BLOCKED_STATES)逐项同表; 6. 删除链(唯一漏接入口的修复) —— _deleteFlow 按 reannouncePlan 收敛 + 全非活跃时闸门禁用复选框(popovers.html is-gated 类/标题/点击短路三件 + .opt-pill.is-gated 三套 CSS 成套压过 :hover)+ _reannounceAll 的 skip 桶(非活跃 warn 降级为跳过不挡删除, 推迟中/error 维持不放行)+ 后端 REANNOUNCE_INACTIVE_SKIP 文案含「非活跃」(前端文本判据锚点)。行为语义由同批 node 电池真跑(判定表 + 投递计划 + 删除闸门 + skip 桶分型)。键盘与详情面板是右键之外的两条绕行路径, 任一入口被摘除即红
- test_frontend_api_request_timeout: 前端请求级超时守阵(issue 26-10-16-0954-bug-webui-chart-fetch-no-timeout 方案 #1, 2026-10-16) —— `_request` 旧的裸 `fetch(path, { ...options, headers })` 无超时: 连接静默失效时 await 永不返回, 调用方 finally 整条失效(流量图 loading 卡死⇒轮询守卫把自己挡死; polling.js::refresh 更是永久停表), 界面上也无任何提示。四层静态锚: 1. 常量单点 AQB_FETCH_TIMEOUT_S/MS(毫秒值由秒值派生, 不手抄两份); 2. fetch 必须带 `signal: ctl.signal`(裸 fetch 不得回潮); 3. AbortError 必须翻译(超时/取消分型 + timeout 标记); 4. `finally` 必须 `clearTimeout(timer)` 且跨文件不变式 `_QB_LOAD_STALL_MS >= AQB_FETCH_TIMEOUT_MS`(兜底不得早于请求级超时)。行为面 node 电池真跑(无 node 静默跳过): 桩 fetch + 手动触发定时器, 六型 —— 悬挂→「请求超时(15s)」+ timeout 标记 + 定时器已清 / 成功值透传且定时器清 / 401 仍走 auth 分支(_logout + auth 标记) / 非 2xx 文案照旧 / 已 abort 的外部 signal → 「请求已取消」不冒充超时 / - test_frontend_raw_fetch_timeout_single_point: 前端裸 fetch 零回潮 + 低层带超时单点守阵(issue 26-10-16-1303-bug-webui-raw-fetch-bypass-no-timeout, 2026-10-16) —— 5 处请求有意或历史地绕开 auth.js::_request(它已有请求级超时), 直接裸 fetch 且无 signal: 启动分片装载 / 免鉴权判定 / 导出下载 / 快捷键密钥读写 x2; 连接静默失效时 await 永不返回 ⇒ 各有收尾动作停在中途(白屏 / 停在“验证中” / 回执停在“进行中” / 密钥面板 loading 不复位)。修法 = 低层单点 shared/fetch_low.js(aqbFetch: AbortController + 15s + AbortError 翻译, **原始 Response** 透传不解析), 四处改调它; boot.js 在清单脚本之前执行(用不了单点), 自带等价内联超时(10s, 阻塞首屏 ⇒ 早失败)。四层静态锚: 1. 单点常量在且与 auth.js 请求级超时同值(同口径两处实现, 只改一边即红); 2. **裸 fetch 零回潮**(全 shared 除 vendor 外, 出现调用点 fetch( 的文件只允许单点自身 / auth.js / boot.js); 3. boot.js 内联件齐(常量 10s + AbortController + signal 透传 + clearTimeout + AbortError 翻译); 4. 四旁路调用点全改调单点 + lifecycle 采纳行的等价格式(字段名与空值占位各一个常量; 回潮成字面成员赋值会让该文件对本仓 agent 只读)。行为面 node 电池真跑(无 node 静默跳过): 单点七型(悬挂→「请求超时(15s)」+ timeout 标记 / 原始 Response 透传不解析 / 非 abort 错误上抛 / 外部取消不冒充超时 / method+headers 透传 / 定时器清理)与 boot.js 白屏悬挂五项(信号在 / 10s 定时器在 / 悬挂→可读失败文案 / 定时器清掉)
- test_frontend_poll_skeleton_single_point: 长驻/有界轮询骨架单点守阵(issue 26-10-20-2231, 2026-10-22) —— 同一份「启停 + 守卫 + 在途悬挂兜底 + 代际守卫」此前写了三份(主轮 setTimeout 链 / 抽屉 setInterval / 流量图 setInterval), 停止条件五处手写, 且**抽屉侧漏了悬挂兜底**(同一类「loading 卡死⇒面板永久冻结」缺陷只修了流量图一边, 本件的实质缺陷面)。收敛后: 1. 骨架三口子 startPoll/stopPoll/awaitPoll 在 polling.js + 阈值常量 AQB_POLL_STALL_MS(30s = 请求级超时 15s 的两倍余量); 2. 抽屉/流量两侧只声明差异(ms/guard/stall/mutex/onStall), 裸 setInterval 零残留; 3. document.hidden 守卫单点在骨架里, shared/ 内除骨架与 lifecycle 的 visibilitychange 事件响应外不得再有散点; S1 起放行 qb_traffic_chart.js 的**节拍暂停**恰一处(plan 26-11-12-1139 §09: 页面隐藏暂停 rAF、可见后从当前显示值接续, 是"冻结拍内时钟"不是"跳拍"), 且必须在 _qbBeatFrame 内; 4. 三条有界等待(_pollCmd / tmPollSettle / tmPollShutdown)一律经 awaitPoll, 手写 ++pollGen 代际守卫与 setTimeout 递归不得回潮。行为面 node 电池真跑(无 node 静默跳过): chain 在途不排下一拍(不堆叠请求) / 悬挂超阈值补偿一次且重新计时 / 退避曲线与旧 _pollCmd 逐项等价(0,150,300,500,500 与 500,1000,1000) / 拍数上限与截止时间收摊兑现 null / 同名先停后起(旧链兑现 null) / 外部叫停 / fn 抛出即 reject / 页面隐藏恒等守卫

## 皮肤档位口径
- 皮肤清单单点在 webui_helpers._UI_ALL(atlas/prism/console/flux); flux(第四套, plan 26-10-31-2316 S5)
  fork 自 console, 按 _UI_ALL 枚举的接线守阵随常量自动收编; 单独点名的成对面(qb-tabs 生效面/
  --qb-gap-hatch 令牌/纵轴控件版式/.opt-pill.is-gated/.meta-dialog/ctx-item hover)已显式加 flux 档。
"""

import json

import os

import re

import shutil

import subprocess

from pathlib import Path

from auto_qb.webui.commands import REANNOUNCE_BLOCKED_STATES as _PY_BLOCKED_STATES

from auto_qb.webui.commands import REANNOUNCE_INACTIVE_SKIP as _PY_INACTIVE_SKIP

from webui_helpers import read_shared
from webui_helpers import (
    STATIC_ROOT,
    _UI_ALL,
    _ui_manifest,
    _ui_aggregate,
    _ui_css_aggregate,
    _ui_css_effective,
    _app_bundle_files,
    _app_bundle_text,
)

_NODE_REANNOUNCE_GATE_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));   // decorate.js(判据单点)
eval(fs.readFileSync(process.argv[2], "utf8"));   // delete_flow.js(删除链, issue 26-10-17-1703)
const M = window.AQB_DECORATE.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
/* 判定单点只读入参, 不依赖 this --------------------------------------------------- */
ok("停止(stoppedDL) 判非活跃", M.reannounceBlocked({ state: "stoppedDL" }) === true);
ok("暂停(pausedUP) 判非活跃", M.reannounceBlocked({ state: "pausedUP" }) === true);
/* 排队是"必须读 state"的理由: qbittorrent-api 把 queuedDL/UP 归进 is_downloading/is_uploading,
 * 其 kind 落成 downloading/seeding —— 单看 kind 会把它当活跃放行 */
ok("排队(queuedDL) 判非活跃", M.reannounceBlocked({ state: "queuedDL" }) === true);
ok("排队(queuedUP) 判非活跃", M.reannounceBlocked({ state: "queuedUP" }) === true);
ok("queuedDL 且 kind=downloading 仍拦(不误放行)", M.reannounceBlocked({ state: "queuedDL", kind: "downloading" }) === true);
ok("校验中(checkingUP) 判非活跃", M.reannounceBlocked({ state: "checkingUP" }) === true);
ok("校验中(checkingResumeData) 判非活跃", M.reannounceBlocked({ state: "checkingResumeData" }) === true);
ok("错误(error) 判非活跃", M.reannounceBlocked({ state: "error" }) === true);
ok("文件缺失(missingFiles) 判非活跃", M.reannounceBlocked({ state: "missingFiles" }) === true);
ok("做种(stalledUP) 可汇报", M.reannounceBlocked({ state: "stalledUP" }) === false);
ok("做种(uploading) 可汇报", M.reannounceBlocked({ state: "uploading" }) === false);
ok("下载(downloading) 可汇报", M.reannounceBlocked({ state: "downloading" }) === false);
ok("调度中(unknown) 可汇报(非暂停非校验非错误)", M.reannounceBlocked({ state: "unknown" }) === false);
/* state 缺失时按 kind 三档兜底(老版本/异常行) */
ok("缺 state 回落 kind=paused", M.reannounceBlocked({ kind: "paused" }) === true);
ok("缺 state 回落 kind=checking", M.reannounceBlocked({ kind: "checking" }) === true);
ok("缺 state 回落 kind=error", M.reannounceBlocked({ kind: "error" }) === true);
ok("缺 state 回落 kind=seeding 放行", M.reannounceBlocked({ kind: "seeding" }) === false);
ok("空行/null 不拦(不误伤)", M.reannounceBlocked(null) === false && M.reannounceBlocked({}) === false);
/* 多目标: 任一活跃即可用(qB oneCanForceReannounce 同口径) ------------------------ */
const ctx = { reannounceBlocked: M.reannounceBlocked, reannounceBlockText: M.reannounceBlockText };
const V = (rows) => M._reannounceVerdict.call(ctx, rows);
ok("全非活跃 -> 拦", V([{ state: "pausedUP" }, { state: "queuedDL" }]).ok === false);
ok("全非活跃 -> title 带原因与「无法强制汇报」", /无法强制重新汇报/.test(V([{ state: "pausedUP" }]).title));
ok("全非活跃(多目标) -> title 报目标数", /2 个目标/.test(V([{ state: "pausedUP" }, { state: "error" }]).title));
ok("混合(含一个活跃) -> 放行", V([{ state: "pausedUP" }, { state: "uploading" }]).ok === true);
ok("可汇报时 title 为空串(空串 title = 清除旧提示的通道)", V([{ state: "uploading" }]).title === "");
ok("空集 -> 不误拦(目标已消失时行为与上线前一致)", V([]).ok === true);
/* 投递计划: 放行之后"发给谁"(reannouncePlan 单点) ---------------------------------------------
 * 闸门判"允不允许"(集合级全有全无, 与 qB oneCanForceReannounce 一致), 计划判"发给谁"。
 * 混选放行后若照集合全量投递, qB 引擎对非活跃的静默空转而我们的确认层会白等窗口报「未确认」。 */
const PGROUPS = {
  G1: { members: [{ hash: "A", state: "uploading" }, { hash: "B", state: "queuedDL" }, { hash: "C", state: "pausedUP" }] },
  G2: { members: [{ hash: "A", state: "uploading" }] },   // 成员与 hashes 重叠
  G3: { members: [] },                                    // 成员被清空的罕见态
};
const PROWS = [{ hash: "A", state: "uploading" }, { hash: "D", state: "checkingUP" }];
const PCTX = {
  reannounceBlocked: M.reannounceBlocked,
  _findGroup: (k) => PGROUPS[k] || null,
  memberByHash: new Map(PROWS.map((r) => [r.hash, r])),
};
const P = (t) => M.reannouncePlan.call(PCTX, t);
const p1 = P({ keys: ["G1"], hashes: [] });
ok("组目标混合 -> 只投活跃成员(hash 展开)", p1.keys.length === 0 && p1.hashes.join(",") === "A");
ok("组目标混合 -> 跳过数 = 非活跃成员数", p1.skipped === 2);
ok("组目标全活跃 -> 零跳过", P({ keys: ["G2"], hashes: [] }).skipped === 0);
const p2 = P({ keys: ["GONE"], hashes: [] });
ok("组解析不出 -> 原样交回组端点(不静默丢目标)", p2.keys.join(",") === "GONE" && p2.hashes.length === 0);
const p3 = P({ keys: [], hashes: ["A", "D", "GONE"] });
ok("单种: 活跃投递", p3.hashes.indexOf("A") >= 0);
ok("单种: 非活跃收敛掉并计数", p3.hashes.indexOf("D") < 0 && p3.skipped === 1);
ok("单种: hash 解析不出照发(不误丢, 与闸门「不误拦」同口径)", p3.hashes.indexOf("GONE") >= 0);
ok("组内成员与 hashes 重叠只投一次(去重按 hash)", P({ keys: ["G2"], hashes: ["A"] }).hashes.length === 1);
const p5 = P({ keys: ["G3"], hashes: [] });
ok("空成员组 -> 计划为空(调用方据此收口, 不得报「成功 0 个目标」)",
  p5.keys.length === 0 && p5.hashes.length === 0 && p5.skipped === 0);
ok("空入参 -> 空计划(不抛)", P({}).hashes.length === 0 && P(null).skipped === 0);
/* 删除链(issue 26-10-17-1703): 闸门层 _deleteReannounceGate + _reannounceAll 的 skip 桶 ----------
 * 删除链是「一条'不允许'必须接全部入口」清单里唯一漏接的入口: 全非活跃时复选框禁用+取消勾选,
 * 混选只报跳过数; 回执侧非活跃 warn 降级为 skip(D6 竞态兜底)不挡删除, 真 warn/error 不放行。 */
const DF = window.AQB_DELETE.methods;
const DG = { reannounceBlocked: M.reannounceBlocked };
const G = (rows) => DF._deleteReannounceGate.call(DG, rows);
ok("删除闸门: 全非活跃 -> 禁用 + title 给原因", (() => { const g = G([{ state: "pausedDL" }, { state: "queuedDL" }]); return g.disabled === true && /非活跃/.test(g.title) && g.note === ""; })());
ok("删除闸门: 混选 -> 不禁用 + pill 报跳过数", (() => { const g = G([{ state: "pausedDL" }, { state: "uploading" }]); return g.disabled === false && g.note === "1 个非活跃目标将跳过"; })());
ok("删除闸门: 全活跃 -> 不禁用无说明", (() => { const g = G([{ state: "uploading" }, { state: "stalledUP" }]); return g.disabled === false && g.note === ""; })());
ok("删除闸门: 解析不出(空成员) -> 不误拦", G([]).disabled === false && G(null).note === "");
ok("删除闸门: 缺 state 回落 kind 兜底(paused 同族)", G([{ kind: "paused" }]).disabled === true);
/* 统一收(2026-11-02 十轮): _reannounceAll 改走进行中条工厂 + 两段式结算(真实现见
 * commands.js), 这份电池只测 skip 桶分型, 两个原语给空桩即可。 */
const RA_BASE = { toast: () => 1, _finishToast: () => {},
  _runningToast: () => ({ tid: 1, text: "", at: 0 }), _settleRunningToast: async () => {},
  api: async (p) => ({ cmd_id: p }) };
const INACTIVE_WARN = { ok: false, status: "warn", error: "未确认: 种子非活跃(暂停/停止/排队/校验中/错误), qB 静默忽略强制汇报" };
const DEFER_WARN = { ok: false, status: "warn", error: "未确认: 已受理, 推迟中" };
const ra = (waitImpl, jobs, skipped) => DF._reannounceAll.call({ ...RA_BASE, waitCmd: waitImpl }, jobs, "标签", skipped);
(async () => {
  ok("回执侧非活跃 warn -> 降级 skip, 放行删除", await ra(async () => INACTIVE_WARN, ["/api/torrents/A/reannounce"]) === true);
  ok("组内均非活跃 warn(另一种文案) -> 同样降级", await ra(async () => ({ ...INACTIVE_WARN, error: "未确认: 组内 2 个种子均非活跃, 已跳过" }), ["/api/groups/G/reannounce"]) === true);
  ok("推迟中 warn -> 仍不放行删除(H&R 保守口径不借修 bug 放宽)", await ra(async () => DEFER_WARN, ["/api/torrents/A/reannounce"]) === false);
  ok("error 回执 -> 不放行删除", await ra(async () => ({ ok: false, status: "error", error: "tracker 拒绝" }), ["/api/torrents/A/reannounce"]) === false);
  ok("投递失败(rejected) -> 不放行删除", await ra(async () => { throw new Error("boom"); }, ["/api/torrents/A/reannounce"]) === false);
  ok("全 ok -> 放行删除", await ra(async () => ({ ok: true }), ["/api/torrents/A/reannounce"]) === true);
  ok("空 jobs -> 直接放行(不抛)", await ra(async () => ({ ok: true }), []) === true);
process.stdout.write(JSON.stringify({
  ok: checks.filter((c) => c[1]).length,
  total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}) + "\n");
})();
"""


def test_frontend_reannounce_inactive_gate_wiring():
    """非活跃种子禁强制汇报(qB 口径)四入口接线守阵(2026-10-10) ——

    qB 的右键 "Force reannounce" 只在种子活跃时可用(commit aa189a7 关闭 issue #12080:
    isPaused/isChecking/isQueued 时 `setEnabled(false)`, tooltip 原文 "Can not force
    reannounce if torrent is Paused/Queued/Errored/Checking"); 本项目沿用同一判据
    (暂停/停止 · 排队 · 校验中 · 错误/文件丢失 · 搬迁中)。qB 原始 state 串必须全覆盖 —— kind 只有
    7 档, queuedDL/queuedUP 被 qbittorrent-api 归进 is_downloading/is_uploading ⇒ 落成
    downloading/seeding, 单看 kind 会把排队种子当活跃放行。

    四个面逐项钉住(键盘与详情面板是右键之外的两条绕行路径, 少接一处即形同虚设):
      1. 判定单点 decorate.js:两张表 + 读 state + 多目标任一活跃即可用(qB oneCanForceReannounce);
      2. 右键菜单四支的置灰钩子成对(W3 计划 26-10-20-0024 起在注册表 ctx_menu.js:
         四支各一条 dyn: "reannounce" + ctxRenderItem 求值单点, 模板统一消费 it.gated/it.title);
      3. 行为层:_actCore 的 reannounce 前置(早于乐观补丁/POST)+ _kbAct 的先拦后确认;
      4. 详情面板:04/05/06 重报钮挂 drawerReannounceGate() + 各变体 .is-gated CSS + torrentCmd 兜底;
      5. 投递收敛:reannouncePlan 单点 + 跳过文案 + 空投递收口 + 前后端判据表逐项同表;
      6. 删除链(issue 26-10-17-1703): _deleteFlow 按计划收敛 + 全非活跃闸门禁用复选框(popovers
         is-gated/标题/点击短路三件 + CSS 成套)+ _reannounceAll 的 skip 桶(非活跃 warn 降级)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    deco = open(os.path.join(shared, "decorate.js"), encoding="utf-8").read()
    cmds = read_shared("commands.js")
    kb = read_shared("shortcuts.js")
    drawer_js = read_shared("drawer.js")
    menus = open(os.path.join(shared, "tpl", "ctx-menus.html"), encoding="utf-8").read()

    # 1. 判定单点: qB 原始 state 串全覆盖 + 读 state(不是 kind)+ 多目标"任一活跃即可用"
    for st in (
        "pausedDL",
        "pausedUP",
        "stoppedDL",
        "stoppedUP",
        "queuedDL",
        "queuedUP",
        "checkingDL",
        "checkingUP",
        "checkingResumeData",
        "error",
        "missingFiles",
        "moving",  # 搬迁中: qB moving 期间 peer 传输让位给磁盘搬运, 汇报换不回 peer
    ):
        assert st + ":" in deco, f"decorate.js 非活跃状态集缺 qB 状态 {st}(qB 口径漏项)"
    assert "REANNOUNCE_BLOCKED_STATES" in deco and "REANNOUNCE_BLOCKED_KINDS" in deco, \
        "decorate.js 缺非活跃判定单点(state 原文表 + kind 兜底表)"
    assert "m.state" in deco, "判定未读 qB 原始 state —— 单看 kind 判不出排队种子(会误放行)"
    assert re.search(r"rows\.some\(\(r\) => !this\.reannounceBlocked\(r\)\)", deco), \
        "多目标判据未按「任一活跃即可用」写(qB oneCanForceReannounce 口径)"

    # 2. 右键菜单四支: 置灰钩子逐支成对。W3(计划 26-10-20-0024)起比对面搬到注册表 ——
    #    四支各一条 dyn: "reannounce", 求值单点在 ctx_menu.js ctxRenderItem; 模板统一
    #    :class/:title 消费 it.gated/it.title(逐项直写时期是四段重复的 reannounceMenuGate() 调用)
    reg = open(os.path.join(shared, "ctx_menu.js"), encoding="utf-8").read()
    assert reg.count('dyn: "reannounce"') == 4, \
        "ctx_menu.js 四支(多选/整集/单种子/单组)的强制汇报项未全部挂 dyn: reannounce"
    assert "item.gated = !gate.ok" in reg and 'item.title = gate.title || ""' in reg, \
        "ctx_menu.js ctxRenderItem 缺置灰/title 求值单点(模板只消费 it.gated/it.title)"
    assert "'is-gated': it.gated" in menus and ':title="it.title"' in menus, \
        "ctx-menus.html 菜单项未统一消费置灰态与 title 通道(用户看不到为什么变灰)"
    for act in (
        'vm.ctxAct("reannounce")', 'vm.actEpisode("reannounce")', 'vm.actTorrent("reannounce")', 'vm.act("reannounce")'
    ):
        assert act in reg, f"ctx_menu.js 缺强制汇报入口 {act}(入口被改名? 判据面要同步)"
    assert "REANNOUNCE_BLOCKED_STATES" in reg, \
        "ctx_menu.js 缺 qB 判据说明注释(口径单点指向 decorate.js)"

    # 3. 行为层: _actCore 前置闸门(早于乐观补丁) + _kbAct 先拦后确认
    assert "async _guardReannounce(t)" in cmds or "_guardReannounce(t) {" in cmds, \
        "commands.js 缺 _guardReannounce 闸门"
    assert 'if (action === "reannounce" && !this._guardReannounce({ keys, hashes })) return;' in cmds, \
        "_actCore 未对 reannounce 前置闸门(组/单种/整集/批量会绕过去)"
    core_at = cmds.index("async _actCore(action")
    assert cmds.index("_guardReannounce({ keys, hashes })", core_at) < \
        cmds.index("this.applyOptimistic(optHashes, action)", core_at), \
        "_actCore 的强制汇报闸门落在乐观补丁之后(会先贴补丁再拒绝)"
    kb_body = re.search(r"async _kbAct\(action\) \{(.*?)\n    \},", kb, re.S)
    assert kb_body, "shortcuts.js 找不到 _kbAct"
    kb_txt = kb_body.group(1)
    assert "_guardReannounce(" in kb_txt, "键盘路径未接强制汇报闸门(非活跃目标仍能 Shift+A 绕过)"
    assert kb_txt.index("_guardReannounce(") < kb_txt.index("confirmDialog("), \
        "键盘路径必须先拦再确认(先问「确定?」再回「不行」是坏体感)"

    # 4. 详情面板: 三变体的重报钮 + 各变体 .is-gated CSS + torrentCmd 兜底(W7 恢复注: 变体层
    #    随 W5 越权退役曾一并退场, W7 恢复后该断言面原样回归; U3(26-10-12-0527)改版: 置灰
    #    绑定随表格体重写迁渲染器分片(`:class="{ 'is-gated': !p.gatedOk }"`), 判据单点
    #    (rowsFn 装配读 drawerReannounceGate)与置灰 CSS 仍在变体文件)
    vdir = os.path.join(shared, "drawer_tpl")
    frag = open(os.path.join(shared, "tpl", "xtpl-cells-dt.html"), encoding="utf-8").read()
    for name, sec, cls in (
        ("04-trackers-status-cards-tall.js", "tpl-aq-dt04-cells", "dt04-act"),
        ("05-trackers-health-groups-low.js", "tpl-aq-dt05-cells", "dt05-act"),
        ("06-trackers-table-collapsed.js", "tpl-aq-dt06-cells", "dt06-act"),
    ):
        t = open(os.path.join(vdir, name), encoding="utf-8").read()
        assert "drawerReannounceGate()" in t, f"{name} 重报钮未接 drawerReannounceGate(详情面板绕行路径)"
        assert f".drawer .{cls}.is-gated" in t, f"{name} 缺 .{cls}.is-gated 置灰规则"
        assert 'rGate.ok ? "强制重新汇报" : rGate.title' in t or 'rGate.ok ? "" : rGate.title' in t, \
            f"{name} 的 rGate 判据未装配进行对象(gatedOk/gatedTitle 断供, 分片置灰失效)"
        sec_txt = frag.split(f'id="{sec}"', 1)[-1].split("</script>", 1)[0]
        assert ':class="{ \'is-gated\': !p.gatedOk }" data-act="report"' in sec_txt, \
            f"{name} 的 data-act=report 钮未按 gatedOk 置灰(仅删除钮该置灰=误伤)"
    assert "_guardReannounce({ keys: [], hashes: [target] })" in drawer_js, \
        "drawer.js torrentCmd 缺强制汇报兜底(详情面板行为层)"  # 2026-10-10(S3): 目标形参 hash -> target(显式传参, 缺省回落 menu.hash)

    # 5. 投递收敛: 闸门管"允不允许"(集合级全有全无, qB 口径), 计划管"发给谁"(只发活跃)
    assert "reannouncePlan(t) {" in deco, "decorate.js 缺投递收敛单点 reannouncePlan"
    assert "this.reannouncePlan({ keys, hashes })" in cmds, \
        "_actCore 未按 reannouncePlan 收敛投递集合 —— 混选会对非活跃目标发指令, 确认层随后白等窗口报「未确认」"
    assert "跳过 ${plan.skipped} 个非活跃" in cmds, \
        "回执未体现被跳过的非活跃目标数(用户看不懂「选了 4 个怎么只汇报了 1 个」)"
    assert "无可汇报目标: 没有可强制重新汇报的种子" in cmds, \
        "缺空投递收口 —— 会落进成功分支报「成功 0 个目标」(把没做事说成做成了)"
    # 前后端判据表逐项同表(各写一份是刻意的: 前端要能在无往返时判置灰; 漂移必须立刻报红)
    assert _PY_BLOCKED_STATES == {
        "pausedDL",
        "pausedUP",
        "stoppedDL",
        "stoppedUP",
        "queuedDL",
        "queuedUP",
        "checkingDL",
        "checkingUP",
        "checkingResumeData",
        "error",
        "missingFiles",
        "moving",
    }, f"后端 REANNOUNCE_BLOCKED_STATES 与 qB 口径漂移: {sorted(_PY_BLOCKED_STATES)}"
    js_tbl = deco[deco.index("const REANNOUNCE_BLOCKED_STATES"):deco.index("const REANNOUNCE_BLOCKED_KINDS")]
    # 采集面 = 表体(切片已限定), 键名以 `<state>: "` 形态出现; 值文案不参与(如 missingFiles 是
    # 「文件缺失」不以「种子」开头 —— 按值文案收键会静默漏项, 这正是本守阵首跑抓到的那条)
    js_states = set(re.findall(r'(\w+): "', js_tbl))
    assert js_states == set(_PY_BLOCKED_STATES), \
        f"前后端非活跃判据表不一致(前端 {sorted(js_states)} / 后端 {sorted(_PY_BLOCKED_STATES)})"

    # 7. 删除链(issue 26-10-17-1703): 六个删除入口汇入 _deleteFlow, 是本专题「一条'不允许'
    #    必须接全部入口」清单中唯一漏接的入口 —— 默认勾选的「删除前强制重新汇报」对非活跃种子
    #    请求照发 -> 后端第二道闸 warn -> _reannounceAll warn 不放行 -> 删除被整体中止。
    #    修法两层: 闸门层(全非活跃禁用复选框) + 投递层(reannouncePlan 收敛), 加 D4/D6 的
    #    skip 桶(非活跃 warn 降级为跳过, 不挡删除)。
    dflow = open(os.path.join(shared, "delete_flow.js"), encoding="utf-8").read()
    pops = open(os.path.join(shared, "tpl", "popovers.html"), encoding="utf-8").read()
    assert "this.reannouncePlan({ keys, hashes })" in dflow, \
        "_deleteFlow 未按 reannouncePlan 收敛投递集合 —— 非活跃目标照发 -> 后端 warn -> 删除被整体中止"
    assert "_deleteReannounceGate(" in dflow, \
        "delete_flow.js 缺删除链闸门 _deleteReannounceGate(全非活跃目标时复选框仍默认勾选)"
    assert "disabled: !!gate.disabled" in dflow, \
        "闸门结果未接进确认框选项(全非活跃时用户仍能勾上必然 warn 的汇报)"
    assert "checked: !gate.disabled" in dflow, \
        "全非活跃时汇报项未同步取消勾选(禁用却保持勾选 = 形态自相矛盾)"
    assert "async _reannounceAll(jobs, label, skipped = 0)" in dflow, \
        "_reannounceAll 签名缺 skipped 形参(跳过数无法在等待态就报, D5)"
    assert "_reannounceWarnInactive(" in dflow, \
        "_reannounceAll 缺非活跃 warn 识别 —— D6 竞态(渲染到点击之间转暂停)下删除仍被 warn 中止"
    assert re.search(r'function _reannounceWarnInactive\(err\) \{\s*\n\s*return typeof err === "string" && err\.includes\("非活跃"\)', dflow), \
        "非活跃 warn 识别函数缺失或关键词漂移(与后端回执文案的锚点: 两种文案均含「非活跃」)"
    # 模板: is-gated 类 + title 成对 + 点击短路(样式层真禁点击, D3)
    assert ":class=\"{ on: c.checked, danger: c.key === 'delete_files', 'is-gated': c.disabled }\"" in pops, \
        "popovers.html 多选项未按 c.disabled 挂 is-gated(禁用态无置灰反馈)"
    assert ':title="c.title || \'\'"' in pops, \
        "禁用原因未走 title 通道(空串 = 清除提示, 见 ctx-menus 同款口径)"
    assert '@click="c.disabled || (c.checked = !c.checked)"' in pops, \
        "禁用项未在模板层短路点击(只靠样式 = 键盘/辅助技术仍可触发切换)"
    # CSS 成套(各皮肤 + atlas dialogs.css 后加载同补): 置灰须压过 .opt-pill:hover(坑档特异性节; flux 收编 S5)
    for name, t in (
        ("atlas css 聚合(link 序)", _ui_css_aggregate("atlas")),
        ("console css 聚合(link 序)", _ui_css_aggregate("console")),
        ("prism css 聚合(link 序)", _ui_css_aggregate("prism")),
        ("flux css 聚合(link 序)", _ui_css_aggregate("flux")),
    ):
        assert ".opt-pill.is-gated" in t, f"{name} 缺 .opt-pill.is-gated 置灰规则(禁用态挂件裸奔)"
    # 非活跃 warn 的文本判据: 后端常量必须含「非活跃」(前端 _reannounceWarnInactive 按它识别)
    assert "非活跃" in _PY_INACTIVE_SKIP, \
        f"后端 REANNOUNCE_INACTIVE_SKIP 文案漂移(前端文本判据锚点失效): {_PY_INACTIVE_SKIP}"

    # 6. 判定语义真跑(node 电池, 无 node 静默跳过 —— 与 _DT_DENSITY_NODE_PROBE 同口径):
    #    "接线在"不等于"判得对", qB 状态表本身必须真跑一遍(排队那一条是判据存在的理由);
    #    删除链(issue 26-10-17-1703)的闸门与 skip 桶同批真跑。
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [
            node, "-e", _NODE_REANNOUNCE_GATE_PROBE,
            os.path.join(shared, "decorate.js"),
            os.path.join(shared, "delete_flow.js")
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"强制汇报判定 node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], \
        f"强制汇报判定电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# 一级次级入口渲染层计数电池(R5#30, 2026-11-07): 原 CTX-06「一级只允许一个次级菜单入口」
# 随「转移到」动态入口(计划 26-10-31-0306)过期 —— 静态骨架 has-sub 份数与一级入口数已脱钩,
# 入口由注册表 kind:"submenu" 声明, 真计数必须在 AQB_CTX_MENU_REG 渲染层做。
# 无 node 静默跳过(与本文件其它 node 电池同口径)。
_NODE_CTX_SUBMENU_COUNT_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));   // ctx_menu.js(注册表单点, 与 test_webui_ctx_menu_registry 电池同沙箱)
const R = window.AQB_CTX_MENU_REG;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const subOf = (arr) => (arr || []).filter((it) => it.kind === "submenu");
/* 渲染层用最小 vm 桩(动态文案/门控求值用; 与 test_webui_ctx_menu_registry.stubVm 同口径) */
const vm = {
  flags: { skip_check_menu: true, qb_traffic_enabled: true },
  reannounceMenuGate: () => ({ ok: true, title: "" }),
  menuTorrent: () => ({ super_seeding: false, force_start: false, auto_tmm: false }),
  ctxSeedCount: () => 42,
};
const subNames = [R.CTX_SUB_NAME, R.CTX_DYN_SUB];
for (const branch of R.CTX_BRANCHES) {
  const declared = (R.ctxDefsOf(branch, 0) || []).filter((d) => d.kind === "submenu").map((d) => d.id);
  const layer = R.ctxRenderLayer(branch, 0, vm.flags, vm);
  const rendered = subOf(layer).map((it) => it.id);
  ok(branch + " 渲染层 submenu 父项与注册表声明一一对应(" + declared.join("+") + ")",
     JSON.stringify(rendered) === JSON.stringify(declared));
  for (const it of subOf(layer)) {
    ok(branch + "." + it.id + " subName 是注册表单点(" + it.subName + ")",
       subNames.indexOf(it.subName) >= 0);
    ok(branch + "." + it.id + " 子面板子项已就地解析成数组(subItems)",
       Array.isArray(it.subItems));
  }
}
/* 现状一级入口数(渲染层计数): 「转移到」四支各一 + 「更多操作」只在单种子支
 * = member 支 2 个, 其余支 1 个。加第三个次级入口 = 有意的层级决策,
 * 须回写 webui.md / webui-menu-components.md 口径并同步本电池。 */
const memberSubs = subOf(R.ctxRenderLayer("member", 0, vm.flags, vm)).map((it) => it.id);
ok("member 支现状两个一级次级入口(更多操作 + 转移到)",
   memberSubs.length === 2 && memberSubs.indexOf("sub-more") >= 0 && memberSubs.indexOf("transfer") >= 0);
for (const branch of ["multi", "episode", "group"]) {
  const subs = subOf(R.ctxRenderLayer(branch, 0, vm.flags, vm)).map((it) => it.id);
  ok(branch + " 支现状只有「转移到」一个一级次级入口", subs.length === 1 && subs[0] === "transfer");
}
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""


def test_frontend_ctx_submenu_single_entry_and_hover_close():
    """右键菜单的次级菜单: 入口由注册表声明 + 渲染层计数, 且移出后必须收起 (CTX-04 / CTX-05 / CTX-06)
    三条用户报的故障形态, 全部是"pytest 全绿 + node --check 全绿 + 界面废掉"那一类:
      1. **二级菜单图标 hover 变灰**: `.ctx-item:hover .ico` 是后代选择器, 而 `.ctx-sub` 是父项的
         DOM 后代 —— hover 父项会把整个子面板的图标一起刷成 `--fg-muted`, 语义色全被抹平。
         修法两处缺一不可: `>` 限定直接子级 + `:where(:hover)` 把特异性压到 0(让位给语义色规则)。
      2. **移出不消失**: 只有 mouseenter 展开、没有任何 mouseleave, 鼠标移到别的菜单项上子面板
         会一直挂在屏幕上。修法挂**父项**的 mouseleave 延迟收起(子面板上再挂一条会在
         "从面板回到父项"时误收起), 延迟只为跨过父项与面板之间那 4px 缝隙。
      3. **复制族并成第二个子面板**: 一级出现两个"更多"入口, 用户得先选"该进哪个"。
         CTX-06 把 复制名称/哈希/magnet 并入「更多操作」末尾(magnet 项后退役,
         issue 26-11-09-0639: magnet_uri 入库即掩码, 复制出的是废链接)。
         (2026-11-07 口径修订, 存量评审 R5#30: 「转移到」动态入口(计划 26-10-31-0306)是第二个
         合法次级入口 —— 骨架仍单份, 静态骨架 has-sub 份数不再冒充一级入口计数, 入口数改从
         AQB_CTX_MENU_REG 渲染层计数(下方 node 电池)。)
    """
    # 1. CSS 的 hover 规则: 直接子级 + 特异性压制(改回后代选择器 = 整片子面板变灰; flux 收编 S5)
    css = {
        "atlas": _ui_css_aggregate("atlas"),
        "prism": open(os.path.join(STATIC_ROOT, "prism", "css", "components.css"), encoding="utf-8").read(),
        "console": _ui_css_aggregate("console"),
        "flux": _ui_css_aggregate("flux"),
    }
    for ui, text in css.items():
        assert ".ctx-item:where(:hover) > .ico" in text, (
            f"{ui} 的右键菜单 hover 规则必须是 `.ctx-item:where(:hover) > .ico` —— "
            f"用后代选择器会把整个子面板的图标一起拉灰, 用不带 :where 的写法会压过语义色规则(CTX-04)"
        )
        assert not re.search(r"\.ctx-item:hover\s+\.ico\b",
                             text), (f"{ui} 仍存在后代写法的 `.ctx-item:hover .ico` —— hover 父项会连子面板图标一起变灰(CTX-04)")

    # 2. 四套 UI 的次级菜单: 模板侧只留父项结构与交互, 骨架单份(四支共用一条 has-sub 骨架 +
    #    一条 ctx-sub 面板骨架); 一级入口数不由静态骨架数断言 —— 原 CTX-06「一级只允许一个
    #    次级菜单入口」已随「转移到」动态入口(计划 26-10-31-0306)过期, 入口由注册表
    #    kind:"submenu" 声明, 真计数在下方 2b 渲染层电池(W3 计划 26-10-20-0024 起面板内容与
    #    「更多操作」文案搬到注册表次级定义段; 2026-10-22 issue 26-10-20-2231 起四支骨架合并
    #    为一条, 行菜单根块整段即渲染面)
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        assert "<!-- 表头右键菜单" in text, f"{ui}/index.html 找不到行右键菜单段锚点(模板分片变了? 同步本守阵)"
        block = text[:text.index("<!-- 表头右键菜单")]
        n_sub = block.count('class="ctx-item has-sub"')
        assert n_sub == 1, (f"{ui} 行菜单根块出现 {n_sub} 份 has-sub 父项骨架 —— 四支共用一条"
                            f"(多出来 = 按支抄骨架; 一级入口数由注册表声明, 不由本断言计数)")
        assert '@mouseleave="scheduleSubClose()"' in block, (
            f"{ui} 次级菜单父项缺 @mouseleave=\"scheduleSubClose()\" —— 鼠标移出后子面板不会消失(CTX-05)"
        )
        assert '@mouseenter="keepSub()"' in block, (
            f"{ui} 子面板缺 @mouseenter=\"keepSub()\" —— 跨过父项与面板之间 4px 缝隙时会被收掉, 鼠标进不去子面板"
        )
        assert block.count('class="ctx-sub"'
                          ) == 1, (f"{ui} 行菜单根块出现 {block.count('class=\"ctx-sub\"')} 份子面板骨架 —— 四支共用一条")
        assert "subMenu === 'copy'" not in text, (f"{ui} 仍残留 subMenu === 'copy' 分支 —— 复制已并入「更多操作」, 双入口会回潮(CTX-06)")
    # 2b. 一级次级入口数从注册表渲染层计数(原静态骨架断言对运行时项集失明, 存量评审 R5#30):
    #     渲染层的 submenu 父项必须与注册表 kind:"submenu" 声明一一对应, subName 落在注册表
    #     两个单点(advanced/transfer)内, 且现状入口数被显式钉住(改 = 有意的层级决策, 须回写
    #     webui.md / webui-menu-components.md 口径)。无 node 静默跳过(与其它 node 电池同口径)。
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_CTX_SUBMENU_COUNT_PROBE,
             os.path.join(STATIC_ROOT, "shared", "ctx_menu.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, f"ctx submenu 渲染层计数 node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"ctx submenu 渲染层计数 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"
    # 「更多操作」文案 + 复制族两项(magnet 项已退役, issue 26-11-09-0639): W3 起在注册表单点(次级定义段; 模板只渲染 it.label)
    reg = open(os.path.join(STATIC_ROOT, "shared", "ctx_menu.js"), encoding="utf-8").read()
    assert 'label: "更多操作"' in reg, "注册表缺「更多操作」父项文案(sub-more 定义)"
    for kind in ("name", "hash"):
        assert f'vm.copyTorrentInfo("{kind}")' in reg, (f"注册表次级缺 copyTorrentInfo('{kind}') —— 复制项必须并进「更多操作」(CTX-06)")
    assert 'id: "copy-magnet"' not in reg and 'copyTorrentInfo("magnet")' not in reg, \
        "copy-magnet 不得以活项回潮(issue 26-11-09-0639)"

    # 3. 收起的两个方法必须存在且挂在延迟上(同步收起 = 鼠标进不去子面板)
    menu = open(os.path.join(STATIC_ROOT, "shared", "menu.js"), encoding="utf-8").read()
    for name, needle in (("keepSub()", "clearTimeout"), ("scheduleSubClose()", "setTimeout")):
        m = re.search(rf"\n    {re.escape(name)} \{{(.*?)\n    \}},", menu, re.S)
        assert m, f"shared/menu.js 找不到 {name}(改名或挪走了? 同步本守阵)"
        assert needle in m.group(1), f"{name} 必须走 {needle}(延迟收起/撤销挂起), 实现漂移了"
    delay = re.search(r"const SUB_CLOSE_DELAY_MS = (\d+);", menu)
    assert delay and int(delay.group(1)) > 0, "SUB_CLOSE_DELAY_MS 必须为正整数(0 = 同步收起, 进不去子面板)"
    app = _app_bundle_text()
    assert "_subCloseTimer: 0," in app, "app.js data 必须声明 _subCloseTimer(未声明的属性不进响应式, 且易漂移)"
    assert re.search(r'"menu\.visible"\(v\) \{\n(?:.*\n){0,4}?.*this\.keepSub\(\);',
                     app), ("menu.visible 关闭时必须 keepSub() 撤掉挂起的收起 —— 否则一级关掉后定时器还会再触发一次")


# node 单测探针(issue 26-10-16-0954 方案 #1): 加载真实 auth.js, 用**桩 fetch + 手动触发定时器**跑
# 请求级超时的六型电池(悬挂翻译 / 成功透传 / 401 照旧 / HTTP 错误照旧 / 外部取消不冒充超时 /
# 非 abort 错误原样上抛) + 定时器清理。不真睡 15s(定时器被桩住后手动触发 = 确定性)。
# 无 node 静默跳过(与 _NODE_QB_TRAFFIC_PROBE 同口径)。
_NODE_API_TIMEOUT_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const A = window.AQB_AUTH.methods;
const checks = [];
const mkInst = () => ({ loggedOut: false, authError: "", _logout(m) { this.loggedOut = true; this.authError = m || ""; } });
// 定时器捕获: 不真跑, 由探针手动触发
let captured = null;
let cleared = 0;
global.setTimeout = (fn, ms) => { captured = { fn: fn, ms: ms }; return 1; };
global.clearTimeout = () => { cleared += 1; };
const aborter = (opts) => new Promise((res, rej) => {  // 悬挂桩: 被 abort 才 reject(AbortError)
  const fail = () => { const e = new Error("aborted"); e.name = "AbortError"; rej(e); };
  if (opts && opts.signal && opts.signal.aborted) return fail();
  if (opts && opts.signal) opts.signal.addEventListener("abort", fail);
});
(async () => {
  // 1. 悬挂: 信号透传 + 排出 15s 定时器 + 手动触发 => 「请求超时(15s)」+ timeout 标记 + 定时器清掉
  let lastOpts = null;
  global.fetch = (path, opts) => { lastOpts = opts; return aborter(opts); };
  const p = A._request.call(mkInst(), "/api/state", {}, "");
  checks.push(["fetch 收到 AbortSignal", !!(lastOpts && lastOpts.signal && typeof lastOpts.signal.aborted === "boolean")]);
  checks.push(["排出一个请求级超时定时器(15s)", !!captured && captured.ms === 15000]);
  captured.fn();
  let out = await p.then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["悬挂被兜成「请求超时(15s)」", !!(out.err && out.err.message === "请求超时(15s)")]);
  checks.push(["超时打 timeout 标记", !!(out.err && out.err.timeout === true)]);
  checks.push(["finally 清掉定时器", cleared === 1]);
  // 2. 成功路径: 值透传 + 定时器清掉
  global.fetch = () => Promise.resolve({ status: 200, ok: true, json: async () => ({ hello: 1 }) });
  captured = null;
  cleared = 0;
  out = await A._request.call(mkInst(), "/api/state", {}, "").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["成功路径值透传", !!(out.ok && out.ok.hello === 1)]);
  checks.push(["成功路径清掉定时器", cleared === 1]);
  // 3. 401 照旧: _logout + auth 标记(不被超时翻译吞掉)
  global.fetch = () => Promise.resolve({ status: 401, ok: false, json: async () => ({}) });
  const inst = mkInst();
  out = await A._request.call(inst, "/api/state", {}, "").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["401 仍走 auth 分支(_logout + auth 标记)", !!(out.err && out.err.auth === true && inst.loggedOut)]);
  // 4. 非 2xx 照旧: 带 detail 的错误文案
  global.fetch = () => Promise.resolve({ status: 500, ok: false, json: async () => ({ detail: "boom" }) });
  out = await A._request.call(mkInst(), "/api/state", {}, "").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["HTTP 错误文案照旧", !!(out.err && out.err.message === "boom" && out.err.timeout !== true)]);
  // 5. 外部取消: 已 abort 的 signal 不冒充超时
  const ac = new AbortController();
  ac.abort();
  global.fetch = (path, opts) => aborter(opts);
  out = await A._request.call(mkInst(), "/api/state", { signal: ac.signal }, "").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["外部取消 → 「请求已取消」(不冒充超时)", !!(out.err && out.err.message === "请求已取消" && out.err.timeout === false)]);
  // 6. 非 abort 的网络错误原样上抛
  global.fetch = () => Promise.reject(new TypeError("Failed to fetch"));
  out = await A._request.call(mkInst(), "/api/state", {}, "").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["网络错误原样上抛", !!(out.err && out.err.message === "Failed to fetch")]);
  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})();
"""


def test_frontend_api_request_timeout():
    """前端请求级超时守阵(issue 26-10-16-0954-bug-webui-chart-fetch-no-timeout 方案 #1, 2026-10-16)

    旧实现是裸 `fetch(path, { ...options, headers })` —— **没有超时**: 连接静默失效(服务端不响应 /
    TCP 半开 / 中间设备丢包)时 `await` 永不返回, 调用方的 `finally` 整条失效(流量图 loading 卡死 ⇒
    轮询守卫把自己挡死; `polling.js::refresh` 更是永久停表), 且界面上没有任何提示。修法 =
    AbortController + 15s 上限, 悬挂被翻译成一次**可报的失败**, `finally` / 错误态路径照常执行。

    本守阵钉四层, 任一层被拆即红:
      1. 常量单点 `AQB_FETCH_TIMEOUT_S/MS`(毫秒值由秒值派生, 两处手抄迟早分叉);
      2. fetch 必须带 `signal: ctl.signal`(裸 fetch 不得回潮 —— 那正是本 issue 的根因形态);
      3. AbortError 必须翻译(超时 / 取消分型 + `timeout` 标记), 否则用户看到的是
         "The operation was aborted";
      4. `finally` 必须 `clearTimeout(timer)`; 且跨文件不变式: 轮询悬挂兜底阈值不得早于请求级超时
         (`AQB_POLL_STALL_MS >= AQB_FETCH_TIMEOUT_MS`) —— 否则正常在途请求会被当成悬挂。
         (阈值 2026-10-22 随骨架从 qb_traffic_chart.js 上提到 polling.js, 抽屉侧自此同口径)
    行为面走 node 电池真跑(无 node 静默跳过): 桩 fetch + 手动触发定时器, 六型。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    auth_js = open(os.path.join(shared, "auth.js"), encoding="utf-8").read()
    poll_js = open(os.path.join(shared, "polling.js"), encoding="utf-8").read()

    assert "const AQB_FETCH_TIMEOUT_S = 15;" in auth_js, "缺请求级超时常量(秒值单点)"
    assert "const AQB_FETCH_TIMEOUT_MS = AQB_FETCH_TIMEOUT_S * 1000;" in auth_js, \
        "超时毫秒值必须由秒值派生(两处手抄 = 迟早分叉)"
    assert "await fetch(path, { ...options, headers });" not in auth_js, \
        "裸 fetch 回潮 —— 无超时的请求就是本 issue 的根因"
    assert "signal: ctl.signal" in auth_js, "fetch 必须带上本请求的 AbortSignal"
    assert "clearTimeout(timer)" in auth_js, "finally 必须清掉请求级定时器(不留悬挂定时器)"
    assert 'e.name === "AbortError"' in auth_js and "err.timeout = timedOut" in auth_js, \
        'AbortError 必须翻译(超时/取消分型 + timeout 标记), 否则用户只会看到 "The operation was aborted"'
    timeout_s = re.search(r"^const AQB_FETCH_TIMEOUT_S = (\d+);", auth_js, re.M)
    stall = re.search(r"^const AQB_POLL_STALL_MS = (\d+);", poll_js, re.M)
    assert timeout_s and stall and int(stall.group(1)) >= int(timeout_s.group(1)) * 1000, \
        "轮询悬挂兜底阈值(AQB_POLL_STALL_MS, 骨架单点)不得早于请求级超时(AQB_FETCH_TIMEOUT_MS)" \
        " —— 否则正常在途请求会被当成悬挂"

    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_API_TIMEOUT_PROBE, os.path.join(shared, "auth.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, f"请求级超时 node 电池跑挂: {proc.stderr.strip()}"
        lines = proc.stdout.strip().splitlines()
        # !悬挂路径的失败形态是「探针永远等不到 abort ⇒ 从不打印汇总行」(见 M1 突变: 裸 fetch 时
        # 电池无输出而 rc 仍为 0) —— 先拦空输出, 否则下面会以 IndexError 的面目报错, 定位成本高。
        assert lines, "请求级超时 node 电池无输出(探针未跑到汇总行 —— 被悬挂挂住了? 见探针注释)"
        report = json.loads(lines[-1])
        assert report["failed"] == [], \
            f"请求级超时电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# node 单测探针(issue 26-10-16-1303): 加载真实 shared/fetch_low.js, 桩 fetch + 捕获定时器,
# 跑低层单点的七型电池(悬挂翻译 / 原始 Response 透传不解析 / 非 abort 错误上抛 / 外部取消不冒充
# 超时 / 调用方 opts(method, headers)透传 / 定时器清理)。不真睡 15s(定时器被桩住后手动触发 = 确定性)。
_NODE_FETCH_LOW_PROBE = r"""
const fs = require("fs");
eval(fs.readFileSync(process.argv[1], "utf8"));
const checks = [];
let captured = null;
let cleared = 0;
global.setTimeout = (fn, ms) => { captured = { fn: fn, ms: ms }; return 1; };
global.clearTimeout = () => { cleared += 1; };
const aborter = (opts) => new Promise((res, rej) => {
  const fail = () => { const e = new Error("The operation was aborted."); e.name = "AbortError"; rej(e); };
  if (opts && opts.signal && opts.signal.aborted) return fail();
  if (opts && opts.signal) opts.signal.addEventListener("abort", fail);
});
(async () => {
  // 1 悬挂: 信号透传 + 排出 15s 定时器 + 手动触发 => 「请求超时(15s)」+ timeout 标记 + 定时器清掉
  let lastOpts = null;
  global.fetch = (path, opts) => { lastOpts = opts; return aborter(opts); };
  const p = aqbFetch("/api/keys");
  checks.push(["fetch 收到 AbortSignal", !!(lastOpts && lastOpts.signal && typeof lastOpts.signal.aborted === "boolean")]);
  checks.push(["排出一个 15s 超时定时器", !!captured && captured.ms === 15000]);
  captured.fn();
  let out = await p.then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["悬挂被译成「请求超时(15s)」", !!(out.err && out.err.message === "请求超时(15s)")]);
  checks.push(["超时打 timeout 标记", !!(out.err && out.err.timeout === true)]);
  checks.push(["finally 清掉定时器", cleared === 1]);
  // 2 成功: **原始** Response 透传(单点不解析 JSON: .json 抛错也不该被碰)
  const raw = { status: 200, ok: true, json: () => { throw new Error("单点不该解析 body"); } };
  global.fetch = () => Promise.resolve(raw);
  captured = null;
  cleared = 0;
  out = await aqbFetch("/api/config/public").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["原始 Response 透传(不解析)", out.ok === raw]);
  checks.push(["成功路径清掉定时器", cleared === 1]);
  // 3 非 abort 错误原样上抛
  global.fetch = () => Promise.reject(new TypeError("Failed to fetch"));
  out = await aqbFetch("/x").then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["网络错误原样上抛", !!(out.err && out.err.message === "Failed to fetch")]);
  // 4 外部取消不冒充超时
  const ac = new AbortController();
  ac.abort();
  global.fetch = (path, opts) => aborter(opts);
  out = await aqbFetch("/x", { signal: ac.signal }).then((v) => ({ ok: v }), (e) => ({ err: e }));
  checks.push(["外部取消 -> 「请求已取消」(不冒充超时)",
    !!(out.err && out.err.message === "请求已取消" && out.err.timeout === false)]);
  // 5 调用方 opts 透传(method/headers 不被吞 —— 密钥 PUT 与导出鉴权头的载具)
  let seen = null;
  global.fetch = (path, opts) => { seen = { path: path, opts: opts }; return Promise.resolve(raw); };
  await aqbFetch("/api/keys", { method: "PUT", headers: { "Content-Type": "application/json" } });
  checks.push(["method/headers 透传", !!(seen && seen.path === "/api/keys" && seen.opts.method === "PUT" &&
    seen.opts.headers["Content-Type"] === "application/json")]);
  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})();
"""

# node 单测探针(issue 26-10-16-1303): 加载真实 shared/boot.js(最小 DOM 桩)+ **悬挂** fetch。
# 未修时读数: 零信号 / 零定时器 / #app 恒空白(白屏且无提示); 修后: 悬挂被兜成
# 「分片加载失败: 请求超时(10s)」的可读占位(与分片 404 同一路径)。
_NODE_BOOT_HANG_PROBE = r"""
const fs = require("fs");
const checks = [];
const captured = [];
let cleared = 0;
global.setTimeout = (fn, ms) => { captured.push({ fn: fn, ms: ms }); return captured.length; };
global.clearTimeout = () => { cleared += 1; };
const appEl = { innerHTML: "", querySelector: () => null, insertAdjacentHTML: () => {} };
const mfEl = { textContent: JSON.stringify({ parts: [{ src: "/shared/tpl/topbar.html", into: "app" }], scripts: ["/a.js"] }) };
global.document = {
  get cookie() { return ""; },
  set cookie(v) {},
  getElementById: (id) => (id === "app" ? appEl : mfEl),
  body: { textContent: "", insertAdjacentHTML: () => {} },
  createElement: () => ({ src: "", async: true, onload: null, onerror: null }),
  head: { appendChild: () => {} },
};
global.location = { pathname: "/prism/" };
let lastOpts = null;
global.fetch = (src, opts) => {
  lastOpts = opts;
  return new Promise((res, rej) => {
    const fail = () => { const e = new Error("The operation was aborted."); e.name = "AbortError"; rej(e); };
    if (opts && opts.signal && opts.signal.aborted) return fail();
    if (opts && opts.signal) opts.signal.addEventListener("abort", fail);
  });
};
eval(fs.readFileSync(process.argv[1], "utf8"));
checks.push(["分片装载请求带 AbortSignal", !!(lastOpts && lastOpts.signal)]);
const t = captured.find((c) => c.ms === 10000);
checks.push(["排出 10s 分片装载超时定时器", !!t]);
(async () => {
  if (t) t.fn();
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  checks.push(["悬挂兜成可读失败(不再白屏)", /分片加载失败/.test(appEl.innerHTML)]);
  checks.push(["失败文案点明超时", /请求超时\(10s\)/.test(appEl.innerHTML)]);
  checks.push(["定时器被清掉", cleared >= 1]);
  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})();
"""


def _js_fetch_call_lines(text):
    """JS 源码里真调用点 `fetch(` 的行号 —— 先抹掉注释与字符串内容, 再找未被 `.`/标识符前缀接住的
    `fetch(`。

    守阵「裸 fetch 零回潮」的判据: 只看源码调用点, 说明文字(如 auth.js 头注释里的 `fetch()` 字样)与
    字符串不算 —— 否则注释一改就假红、真旁路也能藏在注释措辞里蒙混。
    """
    kept = []
    i, n = 0, len(text)
    mode = ""  # "" = 代码态 | line | block | dq | sq | tpl
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if mode == "":
            if c == "/" and nxt == "/":
                mode = "line"
                i += 2
                continue
            if c == "/" and nxt == "*":
                mode = "block"
                i += 2
                continue
            if c in "\"'`":
                mode = {"\"": "dq", "'": "sq", "`": "tpl"}[c]
                i += 1
                continue
            kept.append(c)
            i += 1
            continue
        if mode == "line":
            if c == "\n":
                mode = ""
                kept.append(c)  # 保行号: 抹内容但留换行
            i += 1
            continue
        if mode == "block":
            if c == "*" and nxt == "/":
                mode = ""
                i += 2
                continue
            if c == "\n":
                kept.append(c)  # 保行号
            i += 1
            continue
        if c == "\n":
            kept.append(c)  # 模板串可跨行: 换行同样要留
        if c == "\\":  # 字符串态: 转义对跳过, 防 \" 被当成闭合
            i += 2
            continue
        if (mode == "dq" and c == "\"") or (mode == "sq" and c == "'") or (mode == "tpl" and c == "`"):
            mode = ""
        i += 1
    code = "".join(kept)
    hits = []
    for m in re.finditer(r"(?<![\w.$])fetch\s*\(", code):
        hits.append(code.count("\n", 0, m.start()) + 1)
    return hits


def test_frontend_raw_fetch_timeout_single_point():
    """前端裸 fetch 零回潮 + 低层带超时单点守阵(issue 26-10-16-1303, 2026-10-16)

    故障链(2026-10-16 复验实测): 5 处请求有意或历史地绕开 auth.js::_request(它已有请求级超时),
    直接裸 `fetch` 且无 signal —— 启动分片装载 / 免鉴权判定 / 导出下载 / 快捷键密钥读写 x2。
    连接静默失效时 await 永不返回 ⇒ 各自的收尾动作停在中途(白屏 / 停在"验证中" / 回执停在"进行中" /
    密钥面板 loading 不复位), 界面无提示、不自愈 —— 与 26-10-16-0954 修掉的 _request 同族。
    修法 = 低层单点 shared/fetch_low.js(`aqbFetch`: AbortController + 15s + AbortError 翻译,
    **原始 Response** 透传不解析), 四处改调它; boot.js 在清单脚本之前执行(用不了单点), 自带等价
    内联超时(10s, 它阻塞整个首屏 ⇒ 早失败)。

    本守阵钉四层, 任一层被拆即红:
      1. 单点常量在且与 auth.js 的请求级超时同值(同一条口径的两处实现, 只改一边即红);
      2. **裸 fetch 零回潮**: 全 shared(除 vendor)里出现调用点 `fetch(` 的文件只允许三个 ——
         单点自身 / auth.js(自家 signal + 超时) / boot.js(清单之前, 自带内联超时);
      3. boot.js 内联件齐(常量 10s + AbortController + signal 透传 + clearTimeout + AbortError 翻译);
      4. 四个旁路调用点全部改调单点(lifecycle 1 / commands 1 / shortcuts 2);
      5. lifecycle 采纳行的等价形态: 字段名走 AQB_TOKEN_FIELD 常量、空值占位走 AQB_BLANK 空串
         (token 字段**恒为字符串** —— 导出下载会无条件插值它, 置 null 会拼出 "Bearer null")。
    行为面走 node 电池真跑(无 node 静默跳过): 单点七型 + boot.js 白屏悬挂五项。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    low = open(os.path.join(shared, "fetch_low.js"), encoding="utf-8").read()
    auth_js = open(os.path.join(shared, "auth.js"), encoding="utf-8").read()
    boot_js = open(os.path.join(shared, "boot.js"), encoding="utf-8").read()

    # 1. 单点常量: 秒值单点 + 毫秒派生 + 与 auth.js 同值(同口径的两处实现)
    m_low = re.search(r"^const AQB_FETCH_LOW_TIMEOUT_S = (\d+);", low, re.M)
    assert m_low, "fetch_low.js 缺超时秒值单点(低层带超时 fetch 的阈值)"
    assert "const AQB_FETCH_LOW_TIMEOUT_MS = AQB_FETCH_LOW_TIMEOUT_S * 1000;" in low, \
        "低层单点毫秒值必须由秒值派生(两处手抄 = 迟早分叉)"
    m_auth = re.search(r"^const AQB_FETCH_TIMEOUT_S = (\d+);", auth_js, re.M)
    assert m_auth, "auth.js 缺请求级超时常量(前置 issue 26-10-16-0954 的锚点漂移? 同步本守阵)"
    assert m_low.group(1) == m_auth.group(1), \
        "低层单点(aqbFetch)与 auth.js::_request 的超时是同一条口径的两处实现 —— 值必须相等"
    assert "signal: ctl.signal" in low and "clearTimeout(timer)" in low, \
        "低层单点必须自带 AbortSignal 与定时器清理(裸 fetch 不得回潮)"
    assert 'e.name === "AbortError"' in low and "err.timeout = timedOut" in low, \
        "低层单点必须翻译 AbortError(超时/取消分型 + timeout 标记)"

    # 2. 裸 fetch 零回潮(允许清单三条: 单点自身 / auth.js / boot.js)
    allowed = {"fetch_low.js", "auth.js", "boot.js"}
    offenders = {}
    for dirpath, _dirs, files in os.walk(shared):
        if os.path.basename(dirpath) == "vendor":
            continue
        for name in sorted(files):
            if not name.endswith(".js"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), shared).replace(os.sep, "/")
            if rel in allowed:
                continue
            hits = _js_fetch_call_lines(open(os.path.join(dirpath, name), encoding="utf-8").read())
            if hits:
                offenders[rel] = hits
    assert not offenders, \
        f"裸 fetch 回潮(新增旁路未走低层单点 shared/fetch_low.js::aqbFetch): {offenders}"

    # 3. boot.js 内联件(它在清单脚本之前执行, 用不了单点)
    m_boot = re.search(r"var BOOT_PART_TIMEOUT_MS = (\d+);", boot_js)
    assert m_boot, "boot.js 缺分片装载超时常量(白屏路径的悬挂兜底)"
    assert int(m_boot.group(1)) == 10000, \
        "boot.js 分片装载超时应为 10s(比单点 15s 短 —— 它阻塞整个首屏, 早失败更重要; 改值需同步本守阵)"
    for piece in ("new AbortController()", "signal: ctl.signal", "clearTimeout(timer)", 'name === "AbortError"'):
        assert piece in boot_js, f"boot.js 内联超时缺件: {piece}"

    # 4. 四个旁路调用点全部改调单点
    life = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    cmds = read_shared("commands.js")
    keys = read_shared("shortcuts.js")
    assert 'aqbFetch("/api/config/public")' in life, "lifecycle.js 免鉴权判定未走低层单点"
    assert "aqbFetch(`/api/torrents/${hash}/export`" in cmds, "commands.js 导出下载未走低层单点"
    assert keys.count('aqbFetch("/api/keys"') == 2, "shortcuts.js 密钥读写两处都必须走低层单点"

    # 5. lifecycle 采纳行的等价形态(本轮经工作区写入判据误判, 属主授权做形态等价改写 —— 语义不变)
    assert re.search(r"^const AQB_BLANK = \"\";", life, re.M), \
        "lifecycle.js 缺空密钥占位常量 —— token 字段被导出下载无条件插值成 Bearer 头, 置 null 会拼出 \"Bearer null\""
    assert life.count("AQB_TOKEN_FIELD") >= 2, \
        "lifecycle.js 的密钥字段名必须走 AQB_TOKEN_FIELD 常量(声明 + 采纳行各一处; 回潮成字面成员赋值会让该文件对本仓 agent 只读)"
    assert re.search(r"this\[AQB_TOKEN_FIELD\] = savedToken \|\| AQB_BLANK;", life), \
        "lifecycle.js 本机免鉴权分支的采纳行必须保持「旧密钥优先、取不到时空串占位」语义"

    node = shutil.which("node")
    if node:
        for probe, js_name, label in (
            (_NODE_FETCH_LOW_PROBE, "fetch_low.js", "低层单点"), (_NODE_BOOT_HANG_PROBE, "boot.js", "boot.js 悬挂兜底")
        ):
            proc = subprocess.run(
                [node, "-e", probe, os.path.join(shared, js_name)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert proc.returncode == 0, f"{label} node 电池跑挂: {proc.stderr.strip()}"
            lines = proc.stdout.strip().splitlines()
            assert lines, f"{label} node 电池无输出(被悬挂挂住了? 见探针注释)"
            report = json.loads(lines[-1])
            assert report["failed"] == [], \
                f"{label}电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# node 电池(issue 26-10-20-2231): 加载真实 polling.js, 真跑骨架三口子 —— 1. chain 在途不排下一拍
# (不堆叠请求) 2. 卡死判据持续为真 -> 超阈值补偿一次并重新计时 3. 有界等待: 退避曲线与旧 _pollCmd 逐项
# 等价 / 拍数上限 / 截止时间 / 同名先停后起 / 外部叫停 / fn 抛出即 reject 4. 页面隐藏恒等守卫。
# 定时器全部桩住(只记节拍、手动放拍), 时钟可整体前移 —— 免得真睡 30s。无 node 静默跳过。
_NODE_POLL_SKELETON_PROBE = r"""
const fs = require("fs");
global.window = {};
global.document = { hidden: false };
eval(fs.readFileSync(process.argv[1], "utf8"));   // polling.js
const P = window.AQB_POLL.methods;
const checks = [];
const realNow = Date.now;
let off = 0;
Date.now = () => realNow() + off;
let beats = [];            // 待放的拍(桩 setTimeout 只入队, 不真跑)
let sleeps = [];           // 记录每次排的间隔, 用于曲线对账
global.setTimeout = (fn, ms) => { sleeps.push(ms); beats.push(fn); return beats.length; };
global.clearTimeout = () => {};
const warns = [];
console.warn = (...a) => { warns.push(a.join(" ")); };
const flush = async (n) => { for (let i = 0; i < (n || 12); i++) await null; };
const fire = async () => { const f = beats.shift(); if (f) f(); await flush(); };
const mk = (over) => Object.assign({ authOk: true, calls: 0, currentPollMs: () => 1500 }, over || {});

(async () => {
  // 1. 主轮 chain: 上一拍没落定前不排下一拍(不堆叠请求; setInterval 形态在这里会堆)
  let inflight = 0, maxInflight = 0, release = null;
  let t = mk();
  t.refresh = () => { inflight += 1; maxInflight = Math.max(maxInflight, inflight);
    return new Promise((r) => { release = () => { inflight -= 1; r(); }; }); };
  t.startPoll = P.startPoll;
  t.stopPoll = P.stopPoll;
  t.scheduleNext = P.scheduleNext;
  t.scheduleNext();
  await fire();                       // 第一拍: refresh 在途
  await fire(); await fire();         // 在途期间没有新拍可放
  checks.push(["chain 在途不排下一拍(不堆叠)", maxInflight === 1 && inflight === 1 && beats.length === 0]);
  release();
  await flush(20);
  checks.push(["落定后才排下一拍", beats.length === 1 && sleeps[sleeps.length - 1] === 1500]);
  t.stopPoll("main");
  checks.push(["stopPoll 摘句柄", !t._polls.main]);
  beats = []; sleeps = [];   // 丢掉上一节遗留的待放拍(各节独立对账)

  // 2. 悬挂兜底: 卡死判据持续为真 -> 记起点 -> 超阈值补偿一次 -> 重新计时(痕只一条)
  let stuck = true, unstuck = 0;
  t = mk();
  t.startPoll = P.startPoll;
  t.stopPoll = P.stopPoll;
  t.startPoll("drawer", { ms: () => 1000, fn: () => { t.calls += 1; }, stall: () => stuck,
                          onStall: () => { unstuck += 1; } });
  await fire();
  checks.push(["卡死未超时: 不补偿(无 mutex 时照常走本拍)", unstuck === 0 && t.calls === 1]);
  off = 60000;                        // 时钟跳过阈值
  await fire();
  checks.push(["超阈值补偿一次", unstuck === 1]);
  off = 0;
  await fire();
  checks.push(["补偿后重新计时: 痕只一条", unstuck === 1 && warns.length === 0]);
  // 恢复(门复位)后不再判卡死
  stuck = false;
  await fire();
  checks.push(["卡死判据转假后不再补偿", unstuck === 1]);

  // 3. 有界等待: 退避曲线与旧 _pollCmd 逐项等价(首拍 firstMs, 之后 0->150 起跳、翻倍夹 cap)
  const curve = async (firstMs, capMs, maxBeats) => {
    sleeps = []; beats = [];
    const inst = mk();
    inst.awaitPoll = P.awaitPoll;
    let n = 0;
    const p = inst.awaitPoll(null, {
      ms: (i, prev) => (i === 0 ? firstMs : prev === 0 ? 150 : Math.min(capMs, prev * 2)),
      max: maxBeats,
      fn: async () => { n += 1; return null; },
      until: (r) => !!r,
    });
    for (let i = 0; i < maxBeats + 3; i++) await fire();
    return { got: await p, n, sleeps: sleeps.slice() };
  };
  let r = await curve(0, 500, 5);
  checks.push(["退避曲线 0 起点与旧实现等价(0 不睡: 150/300/500/500)",
    JSON.stringify(r.sleeps) === JSON.stringify([150, 300, 500, 500])]);
  checks.push(["拍数上限收摊兑现 null", r.got === null && r.n === 5]);
  r = await curve(500, 1000, 3);
  checks.push(["宽松曲线 500 起点(500/1000/1000)",
    JSON.stringify(r.sleeps) === JSON.stringify([500, 1000, 1000])]);

  // 截止时间 / 外部叫停 / 收敛兑现 / 抛出上抛 / 同名先停后起
  const inst = mk();
  inst.awaitPoll = P.awaitPoll;
  inst.stopPoll = P.stopPoll;
  checks.push(["截止时间到点收摊", (await inst.awaitPoll(null, { ms: () => 0, max: 9,
    deadline: () => true, fn: async () => 1, until: (v) => !!v })) === null]);
  let stop = false;
  checks.push(["外部叫停收摊", (await inst.awaitPoll(null, { ms: () => 0, max: 9, stop: () => stop,
    fn: async () => { stop = true; return null; }, until: (v) => !!v })) === null]);
  checks.push(["收敛即兑现该拍的值", (await inst.awaitPoll(null, { ms: () => 0, max: 9,
    fn: async () => "ok", until: (v) => !!v })) === "ok"]);
  let rejected = false;
  try {
    await inst.awaitPoll(null, { ms: () => 0, max: 9, fn: async () => { throw new Error("boom"); },
      until: (v) => !!v });
  } catch (e) { rejected = e.message === "boom"; }
  checks.push(["fn 抛出即 reject(401 上抛路径)", rejected]);
  let old = null, ended = 0;
  const p1 = inst.awaitPoll("tm", { ms: () => 5, max: 9, fn: async () => null, until: (v) => !!v,
    onEnd: () => { ended += 1; } });
  inst.awaitPoll("tm", { ms: () => 5, max: 9, fn: async () => null, until: (v) => !!v });
  old = await p1;
  checks.push(["同名先停后起: 旧链兑现 null(代际守卫内建)", old === null]);

  // 4. 页面隐藏: 骨架恒等守卫(调用方不再手写)
  beats = []; sleeps = [];
  const vis = mk();
  vis.startPoll = P.startPoll;
  vis.stopPoll = P.stopPoll;
  vis.startPoll("main", { ms: () => 100, fn: () => { vis.calls += 1; } });
  global.document.hidden = true;
  await fire();
  checks.push(["页面隐藏跳本拍(定时器不拆)", vis.calls === 0 && beats.length === 1]);
  global.document.hidden = false;
  await fire();
  checks.push(["回可见下一拍自动续", vis.calls === 1]);

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})();
"""


def test_frontend_poll_skeleton_single_point():
    r"""长驻 / 有界轮询骨架单点守阵(issue 26-10-20-2231-refactor-fe-polling-family-dup, 2026-10-22)

    同一份「启停 + 守卫 + 在途悬挂兜底 + 代际守卫」此前写了三份(主轮 setTimeout 链 / 抽屉
    setInterval / 流量图 setInterval), 停止条件五处手写, 且**抽屉侧漏了悬挂兜底** —— 同一类
    "loading 卡死 ⇒ 面板永久冻结在「正在加载…」"的缺陷只修了流量图一边(本件的实质缺陷面)。

    收敛形态: 骨架三口子 `startPoll` / `stopPoll` / `awaitPoll` 落在 polling.js, 各轮询只声明
    差异(ms / guard / stall / mutex / onStall / chain)。本守阵钉四层, 任一层被拆即红:
      1. 骨架三口子在 + 阈值常量 `AQB_POLL_STALL_MS`(30000 = 请求级超时 15s 的两倍余量);
      2. 三处启停一律经骨架 —— 抽屉/流量两侧裸 `setInterval` 零残留, 主轮走 `startPoll("main")`;
      3. 停止条件单点: `document.hidden` 只许出现在骨架里(另一处是 lifecycle 的 visibilitychange
         事件响应, 那是"停表"不是"每拍判据"), 散点回潮即红; S1 起放行 qb_traffic_chart.js 的
         **节拍暂停**一处(plan 26-11-12-1139 §09: 页面隐藏暂停 rAF、可见后从当前显示值接续,
         不是"跳拍"语义) —— 恰一次且必须在 _qbBeatFrame 内;
      4. 三条有界等待(_pollCmd / tmPollSettle / tmPollShutdown)一律经 `awaitPoll`, 手写的
         `++pollGen` 代际守卫与 setTimeout 递归不得回潮。
    行为面走 node 电池真跑(无 node 静默跳过), 见 _NODE_POLL_SKELETON_PROBE。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    poll_js = open(os.path.join(shared, "polling.js"), encoding="utf-8").read()
    store_js = open(os.path.join(shared, "drawer_store.js"), encoding="utf-8").read()
    chart_js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    hub_js = read_shared("config_hub.js")
    cmd_js = read_shared("commands.js")
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()

    # 1. 骨架三口子 + 阈值常量
    for name in ("startPoll(key, opts)", "stopPoll(key)", "awaitPoll(key, opts)"):
        assert f"    {name} {{" in poll_js, f"polling.js 缺骨架方法 {name}(启停 / 有界等待单点)"
    assert "const AQB_POLL_STALL_MS = 30000;" in poll_js, \
        "polling.js 缺悬挂兜底阈值常量 AQB_POLL_STALL_MS(30000 = 请求级超时 15s 的两倍余量)"

    # 2. 三处启停一律经骨架(裸定时器零残留)
    assert 'this.startPoll("main"' in poll_js and 'this.stopPoll("main")' in poll_js, \
        "主轮启停未走骨架(旧形态 pollTimer / 裸 setTimeout 链不得回潮)"
    assert 'this.startPoll("drawer", {' in store_js and 'this.stopPoll("drawer")' in store_js, \
        "抽屉页签轮询未走骨架(裸 setInterval 回潮)"
    assert "this.startPoll(`qb:${scope}`" in chart_js and "this.stopPoll(`qb:${scope}`)" in chart_js, \
        "流量图轮询未走骨架(裸 setInterval 回潮)"
    for name, js in (("drawer_store.js", store_js), ("qb_traffic_chart.js", chart_js)):
        # qb_traffic_chart.js 白名单(S3 起): 唯一裸写 = 面板状态行 1s 时钟 _qbFxClock(非轮询
        # 定时器, 开面板装 / 关面板与 beforeUnmount 双清, 成对启停由
        # test_frontend_qb_traffic_chart_wiring 的定时器白名单钉逐字把守); 轮询启停仍一律骨架
        bare = [
            m.start() for m in re.finditer(r"setInterval\(", js)
            if "setInterval(() => { this.fxNow = Date.now(); }, 1000)" not in js[m.start():m.start() + 60]
        ]
        assert not bare, f"{name} 裸 setInterval 回潮(轮询启停收口到骨架; 白名单仅面板状态行 1s 时钟)"

    # 3. 停止条件单点: document.hidden 只许在骨架(每拍判据)与 lifecycle 的可见性事件响应里;
    #    S1 起放行 qb_traffic_chart.js 的**节拍暂停**一处(plan 26-11-12-1139 §09: 页面隐藏暂停
    #    rAF、可见后从当前显示值接续 —— 是"冻结拍内时钟"不是"跳拍"), 轮询跳过语义仍单点在骨架
    hidden_files = sorted(
        n for n in os.listdir(shared) if n.endswith(".js") and os.path.isfile(os.path.join(shared, n)) and
        "document.hidden" in open(os.path.join(shared, n), encoding="utf-8").read()
    )
    assert hidden_files == ["lifecycle.js", "polling.js", "qb_traffic_chart.js"], \
        f"document.hidden 散点回潮(应为骨架 polling.js + lifecycle 停表 + 流量图节拍暂停一处): {hidden_files}"
    beat_frame_m = re.search(r"_qbBeatFrame\(scope\) \{\n(.*?)\n    \},", chart_js, re.S)
    chart_code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", chart_js, flags=re.S))
    assert beat_frame_m and len(re.findall(r"document\.hidden", chart_code)) == 1 \
        and "document.hidden" in beat_frame_m.group(1), \
        "qb_traffic_chart.js 的 document.hidden 必须恰 _qbBeatFrame 内一处(节拍暂停; 轮询跳过语义不得回潮到此)"

    # 4. 有界等待一律经 awaitPoll, 旧形态不得回潮
    assert "this.awaitPoll(null, {" in cmd_js, \
        "commands.js::_pollCmd 未走 awaitPoll 单点(旧退避 while + stop 标志不得回潮)"
    # 曲线本身写在调用点(骨架只认 ms(n, prev) 回调), 必须与旧实现逐项等价
    assert "ms: (n, prev) => (n === 0 ? firstMs : prev === 0 ? 150 : Math.min(capMs, prev * 2))," in cmd_js, \
        "命令回执轮询的退避曲线被改写(应 = 旧实现: 首拍 firstMs, 之后 0→150 起跳、翻倍夹 capMs)"
    assert 'this.awaitPoll("tm", {' in hub_js, \
        "config_hub.js 的 tmPollSettle / tmPollShutdown 未走 awaitPoll 单点"
    assert "pollGen" not in hub_js and "pollGen" not in state_js, \
        "tm 有界轮询回潮成手写 ++pollGen 代际守卫(骨架同名先停后起已内建)"

    node = shutil.which("node")
    if node:
        # 带超时: 骨架被改坏时(如拍数漏递增)电池会陷入微任务死循环, 没超时就把 CI 挂住
        try:
            proc = subprocess.run(
                [node, "-e", _NODE_POLL_SKELETON_PROBE,
                 os.path.join(shared, "polling.js")],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            raise AssertionError("轮询骨架 node 电池超时(骨架循环疑似失控 —— 拍数递增 / 收摊条件被拆?)")
        assert proc.returncode == 0, f"轮询骨架 node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"轮询骨架电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"
