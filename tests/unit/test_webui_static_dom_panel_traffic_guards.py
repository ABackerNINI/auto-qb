"""test_webui_static_dom_panel_traffic_guards 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

原 test_webui_static_dom_panel_traffic.py 按域拆分(move-only, 2026-11-27); 测试 ID/名称/断言零变化。

## 测试计划(每个测试函数一条)
- test_frontend_qb_traffic_scope_stale_polarity: 流量图三挂点 stale 谓词极性守阵(2026-10-12 修「种子流量图加载不出来」) —— W2–W6 机械改名把 torrent/group 两处 `!(...)` 写成 `!!(...)`(取反变双重取反), 恰在本图活跃时判「响应已过期」⇒ 数据不落袋 + loading 不复位 + 早退不建图 ⇒ 种子「流量」页签恒停「正在加载流量数据…」且轮询被 loading 卡住不自愈(global 未中招, 故症状只在种子/分组图)。既有静态锚(源码字符串级)对单/双 bang 天然失明, 本守阵补两层: 1. node 电池用 `new Function(源码 + "return _QB_SCOPES;")` 取出作用域表, 对三挂点喂「活跃/切走/关闭/换目标/功能关」五类上下文断言 stale 真假 + `active => stale === false` 同向性; 2. 静态极性兜底钉 `!(...)` 书写形态、`!!(...)` 不得回潮
- test_frontend_qb_traffic_yaxis_and_annotation: 流量图纵轴固定模式 + 画布注解层守阵(2026-10-08, issue 26-10-07-0149 认领一并做; 缺口/缝判据点列适配 26-11-18-0037 阶段 3) —— _qbYRange/_qbGapRuns 纯函数 node 真跑(自动 = peak*1.05 / 固定上限取 max(cap, peak*1.05) 峰值超上限按峰值显示 / 缺口 = 上下行皆 null 才算 —— schema=2 显式空值点与旧契约 null 桶转列后同判); 限速三作用域同源 = qB 全局限速上下行**较大者**(_qbGlobalLimit -> speedLimitBytes); 上限派生单点 _qbYCapOf(limit×1.2 / manual MiB); 三作用域**各自独立**持久化(qbYAxisStoreKey 三键 + qbInitialYAxis 只认合法模式与正数 + persistQbYAxis 吞异常) + 切档落盘重排(qbSetYAxisMode/qbSetYAxisManual -> _qbChartRescale 走 setData 重算 scale 不重建) + 限速变化重排 watcher(mounted 注册, this.drawer 守卫剔除 BaseTransition 假实例); 建图 y range 接纯函数 + draw/drawClear 两钩子画限速虚线/缺口斜纹(共享图面三挂点全生效, uPlot.pxRatio 设备像素换算, 限速线只画落在可视值域内的); 模板 .qb-tools/.qb-seg 控件 + CSS 三皮肤成对 + **控件组唯一挂点**(图下统计栏 .qb-statctl; 2026-10-16 版式改: 流量形态头部不再挂控件, 全局/分组与种子流量图三挂点对齐, 上限读数 qbYAxisCapText/.qb-tools-hint 随 UI 移除退役) + P4 重启缝提示(plan 26-10-15-0829; 左端口径修订 2026-10-16, issue 26-10-16-0954): _qbSeamHint 判据纯函数 node 真跑(重启贴近链末->提示(含首采即链末桶的实测帧形态)/链到右沿或链确已接续或旧后端->null, 边界含尾区起点、右沿与左端前一桶三点; schema=2 形态 26-11-18-0037 阶段 3: 链末按列值判(显式空值点不算观测)/右沿 = 末点真值 t(旧等距外推退役)/尾组真值点链到右沿->null/全空值点空态面->null) + computed qbCurSeamHint 消费单点 + drawer.html 提示行文案单源带重启时刻锚 + 断线语义不变(spanGaps:false ×2)
- test_frontend_qb_traffic_drawer_page_guard: 流量图抽屉的页面守卫(2026-10-06 修「qB 全局流量图出现在设置页」) —— drawerVisible 两形态先挡非主内容页且状态位不随切页翻(回页连数据/窗口选择一起回来) + 轮询与建图 active 同源含 page 判据(面板不在 DOM 还拉还画 = 对空气取数) + openDrawerTraffic 先切回主内容页 + state.js drawerVisible watcher 退场销毁图/进场补拉(种子详情支路 !s 的 $nextTick _dtSync 回页变体重挂, 归 test_drawer_seed_reentry_variant_remount)
- test_frontend_qb_traffic_load_stall_fallback: 流量图轮询「在途悬挂」兜底守阵(issue 26-10-16-0954-bug-webui-chart-fetch-no-timeout 方案 #2, 2026-10-16; T4a 起 GET 轮询骨架为降级态取数路径, 本守阵语义不变) —— loading 是单向「请求在途」标志(_qbLoad 入口无条件置 true, 唯一复位路径是它的 finally), 请求悬挂时 finally 不执行 ⇒ tick 守卫把之后每一拍都挡掉, 图表永久停在旧帧且无提示(与 10-12 修的同链另一入口 stale 谓词取反不同)。三层静态锚: 1. 阈值常量 _QB_LOAD_STALL_MS(=30000, 请求级超时的两倍余量); 2. 判据单点 _qbLoadStalled 在且 tick 必须经它(合体写法 `document.hidden || this[def.loading]` 不得回潮); 3. _qbLoad 置位处写计时起点 _qbLoadAt[scope] 且 finally 不擦(擦会把换目标场景下新请求的起点抹成 0)。行为面 node 电池真跑(无 node 静默跳过): 真 _qbLoad + 永不 settle 的 api 桩 —— 在途未悬挂照旧挡拍 / 悬挂放行且只留一条警告 / 新起点生效故后续照常挡拍 / 图不活跃与页面隐藏照旧跳过 / 判据边界(29s 不判、31s 判、无起点不判); 附 R5#182 死代码反向锚(loadQbHistory 兼容别名零残留, 入口全走 openQbHistory/openDrawerTraffic)
- test_frontend_qb_poll_rhythm_and_immediate_first_beat: F7/F8/A7 电池(plan 26-11-15-1104; 组距口径 26-11-18-0037 阶段 3; T4a 子波 2 起 GET 轮询骨架 = 降级态取数路径, 逐拍面不变) —— 轮询节奏 = 采样间隔全窗统一(D6): _qbPollMs 读 meta.sample_interval_s(生效采样间隔)经 [1.5s,600s] 防御夹取, si 1.5/30/600/900/0.8 逐值 + 只带 interval_s 的旧形状(桶宽 3600)不吃(30000 兜底, 旧「被夹成 600000」形态即旧口径回潮) + meta 缺失/si 非法(0/负)兜底; A7 状态行两组值同源: 周期实算 qbFxPeriodS/beat qbFxBeatMs 与采样行 qbFxSampleText 都从 sample_interval_s 来(schema=2 样本分组契约两值形态 si=1.5/iv=174(schema 2, stride 116) -> 「1.5 s · 组距 174.0 s」(interval_s = 组距标称 k x si, 桶面退役)+ beat 600, 旧口径吃组距 beat 恒 1000 即回潮; agg 段窗无 schema 键二值仍「1.5 s · 桶宽 3600.0 s」(D4 零改动); 相等形态回落单值逐字一致); F8 冷开首拍立即(D4): startPoll immediate 首拍立即(delay 0)/非 immediate 调用面零变化/直拉在途首拍被 mutex 挡掉不双发 + 短重试 AQB_POLL_FIRST_RETRY_MS=1500 不落 30s fallback/直拉落定后首拍真实执行记账清位回归节律周期/隐藏期首拍跳过拉数但重排仍短间隔; 静态钉: AQB_POLL_FIRST_RETRY_MS=1500 + 骨架首拍记账表达式 + 流量侧 immediate: true 声明; 行为面 node 电池真跑(真骨架 + 真 _qbPollMs/_qbLoad/computed, 无 node 静默跳过)
- test_frontend_qb_tick_label_and_isolated_idxs: R5#192 —— x 轴刻度与孤点索引 node 电池(同文件其余纯函数均有电池, 唯这两处标着纯函数却零执行): _qbTickLabel 四族分支 13 档逐档断言(1m/5m 标到秒 / 30m-24h 只标时刻 / 3d/7d/30d 标日期 / 6mo/1y/all 标年月; 期望值由同一 Date 本地时区现算, 与机器时区无关)+ torrent 挂点读自己的窗口字段(三挂点窗口互不串) + _qbIsolatedIdxs 三态(两侧皆 null 的孤点收/任一侧非 null 的链中链端不收/贴边孤点与空系列边界)

## 皮肤档位口径
- 皮肤清单单点注记见 test_webui_static_dom_panel_traffic_wiring.py docstring「## 皮肤档位口径」节(单点保留处)。
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

from webui_dom_panel_support import _tpl_body

from webui_dom_panel_support import _NODE_STDIN_WRAPPER


def _tpl_top_level_tags(body: str):
    """返回模板体里 **depth-0** 的元素 (tag, attrs) 清单 —— 即该片段的根元素, 忽略注释/文本。

    为什么需要它(而不是数类名出现次数): W3(计划 26-10-11-2106)把档位/纵轴控件组收进**多根**
    片段 <aq-qb-ctl>(tpl/drawer-head.html), 其两根 `.qb-tabs` / `.qb-tools` 是**直接子元素**这件事
    被三皮肤 CSS 依赖 —— `.qb-statctl > .qb-tabs` / `.qb-statctl > .qb-tools` 与
    `.hist-summary > .qb-statctl`(atlas prism views.css / console dialogs.css)全是**直接子选择器**。
    一旦有人给片段包一层 wrapper(哪怕只是"顺手加个容器"),
    这些规则全部**静默**不命中: 类名 count 一个不变, 观感却错版。故这里按**结构**判根数 ——
    单个根 = 有人加了 wrapper, 立刻判红。
    """
    import html.parser as _hp  # 局部导入: 仅本助手需要, 不污染模块级命名空间

    class _Roots(_hp.HTMLParser):
        # HTML 空元素(不改变嵌套深度) —— 片段里出现的只有这些是无闭合标签的
        VOID = frozenset(
            [
                "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track",
                "wbr"
            ]
        )

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.depth = 0
            self.roots = []

        def handle_starttag(self, tag, attrs):
            if self.depth == 0:
                self.roots.append((tag, dict(attrs)))
            if tag not in self.VOID:
                self.depth += 1

        def handle_startendtag(self, tag, attrs):
            if self.depth == 0:
                self.roots.append((tag, dict(attrs)))

        def handle_endtag(self, tag):
            if tag not in self.VOID and self.depth > 0:
                self.depth -= 1

    parser = _Roots()
    parser.feed(body)
    return parser.roots


# 纵轴固定模式 + 缺口游程 + 重启缝判据 node 电池(2026-10-08; P4 追加 _qbSeamHint, plan 26-10-15-0829):
# 模块级纯函数 _qbYRange/_qbGapRuns/_qbChainBounds/_qbGapZone/_qbPointsColumns/_qbSeamHint 真跑。无 node 静默跳过(与 _NODE_QB_TRAFFIC_PROBE 同口径)。
_NODE_QB_YAXIS_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const checks = [];
const eq = (n, got, want) => checks.push([n, JSON.stringify(got) === JSON.stringify(want)]);
const ok = (n, cond) => checks.push([n, !!cond]);
// 值域: 自动 = peak*1.05(无数据回落 1); 固定上限取 max(cap, peak*1.05) —— 峰值超上限按峰值显示
eq("auto 无数据回落 1", _qbYRange(0, 0), [0, 1]);
eq("auto 峰值", _qbYRange(100, 0), [0, 105]);
eq("固定上限高于峰值(上限即顶)", _qbYRange(100, 120), [0, 120]);
eq("峰值超固定上限按峰值显示", _qbYRange(200, 120), [0, 210]);
eq("手动上限无峰值(上限即顶)", _qbYRange(0, 50), [0, 50]);
// 缺口游程: 上下行皆 null 才算缺口(单列 null 防御性不误判)
eq("缺口游程 中段+尾段", _qbGapRuns([1, null, null, 4, null], [1, null, null, 4, null]), [[1, 2], [4, 4]]);
eq("缺口游程 前导", _qbGapRuns([null, 2, 3], [null, 2, 3]), [[0, 0]]);
eq("缺口游程 全 null", _qbGapRuns([null, null], [null, null]), [[0, 1]]);
eq("缺口游程 无缺口", _qbGapRuns([1, 2, 3], [1, 2, 3]), []);
eq("单列 null 不算缺口", _qbGapRuns([null, 2], [1, 2]), []);

// 缺口**区段归类**(2026-10-30): 数据链之外只陈述「没有数据」, 链中间的洞才谈「中断」。
// 边界只认本帧 points, 不用种子 added_on —— 跳检是删同 hash 再重加且流量按 infohash 留存,
// 拿 added_on 切一刀会把早期真实数据误判成「尚未添加」(与本次要修的失真同型反向)。
eq("数据链边界 前导空洞", _qbChainBounds([null, null, 3, 4], [null, null, 3, 4]), [2, 3]);
eq("数据链边界 尾随空洞", _qbChainBounds([3, 4, null], [3, 4, null]), [0, 1]);
eq("数据链边界 全空", _qbChainBounds([null, null], [null, null]), [-1, -1]);
eq("数据链边界 无缺口", _qbChainBounds([1, 2], [1, 2]), [0, 1]);
eq("数据链边界 单列有点即算观测", _qbChainBounds([null, 3], [5, null]), [0, 1]);
eq("区段 链首之前->outside", _qbGapZone(0, 2, 3), "outside");
eq("区段 链尾之后->outside", _qbGapZone(3, 0, 1), "outside");
eq("区段 全空->outside(>-1 恒真)", _qbGapZone(0, -1, -1), "outside");
eq("区段 链中间的洞->mid", _qbGapZone(2, 0, 4), "mid");
eq("区段 恰在链首->mid(首桶有观测)", _qbGapZone(0, 0, 3), "mid");
// hover 侧把 points 转成 uPlot 同形状两列, 与画布侧共用上面同一判据
eq("转列 对齐 uPlot 形状(旧契约 null 桶)", _qbPointsColumns([null, { t: 10, up: 1, dl: 2 }]), [[null, 1], [null, 2]]);
eq("转列 全空", _qbPointsColumns([null, null]), [[null, null], [null, null]]);
// schema=2 显式空值点(26-11-18-0037 E3): 元素恒为字典, 双 null 值转列后同缺口判据
const GP = (t) => ({ t, dl: null, up: null });
eq("转列 显式空值点 = 双 null 列位", _qbPointsColumns([GP(5), { t: 10, up: 1, dl: 2 }]), [[null, 1], [null, 2]]);
eq("缺口游程 显式空值点游程", _qbGapRuns([1, null, null, 4], [1, null, null, 4]), [[1, 2]]);
eq("链边界 显式空值点不算观测", _qbChainBounds([null, null, 3, 4], [null, null, 3, 4]), [2, 3]);

// 重启缝提示判据(P4, plan 26-10-15-0829; 左端口径修订 2026-10-16, issue 26-10-16-0954): _qbSeamHint 真跑
// —— 数据链末点早于右沿 + 重启贴近链末(∈ [链末桶前一桶起点, 右沿]) -> 提示; 链到右沿/链确已接续/旧后端不提示
// 场景重建: 链止于 t=130 桶(覆盖端 160), 尾区 [160, 250], 服务 178 起 -> 提示
const mkP = (t, dl, up) => ({ t, dl, up });
const seamPts = [mkP(100, 5, 5), mkP(130, 6, 6), null, null, null];
eq("重启缝 尾区含重启->提示", _qbSeamHint(seamPts, 30, { server_started_at: 178 }), { startedAt: 178 });
eq("重启缝 边界 恰在尾区起点->提示", _qbSeamHint(seamPts, 30, { server_started_at: 160 }), { startedAt: 160 });
eq("重启缝 边界 恰在右沿->提示", _qbSeamHint(seamPts, 30, { server_started_at: 250 }), { startedAt: 250 });
eq("重启缝 链到右沿->null(末桶观测/当前桶未采完是常态)", _qbSeamHint([mkP(100, 5, 5), mkP(130, 6, 6)], 30, { server_started_at: 178 }), null);
eq("重启缝 重启落在链末桶覆盖窗->提示(修订: 链末桶晚于重启时刻不再是豁免)", _qbSeamHint(seamPts, 30, { server_started_at: 140 }), { startedAt: 140 });
eq("重启缝 边界 恰在链末前一桶起点->提示", _qbSeamHint(seamPts, 30, { server_started_at: 100 }), { startedAt: 100 });
eq("重启缝 早于链末前一桶->null(链确已接续)", _qbSeamHint(seamPts, 30, { server_started_at: 99 }), null);
eq("重启缝 重启远早于链末->null(链确已接续)", _qbSeamHint(seamPts, 30, { server_started_at: 40 }), null);
eq("重启缝 晚于右沿->null(防御)", _qbSeamHint(seamPts, 30, { server_started_at: 300 }), null);
eq("重启缝 旧后端无新键->null(不猜)", _qbSeamHint(seamPts, 30, {}), null);
eq("重启缝 meta缺失->null", _qbSeamHint(seamPts, 30, null), null);
eq("重启缝 interval非法->null", _qbSeamHint(seamPts, 0, { server_started_at: 178 }), null);
eq("重启缝 全null->null(空态面)", _qbSeamHint([null, null], 30, { server_started_at: 178 }), null);
eq("重启缝 空数组->null", _qbSeamHint([], 30, { server_started_at: 178 }), null);
// 反例回归(issue 26-10-16-0954 实测帧重建): 1m 窗 interval=2s —— 04:45:00 记 100, 04:45:01 重启(101),
// 首采桶 04:45:02(102, 全窗唯一非 null; 左侧停机洞 + 右侧开放零游程读侧未交付均 null), 右沿 140;
// 修订前判据在 started < 链末桶覆盖端(104) 处恒返回 null(现场 04:45:40 帧零提示的机制)
const seamFrame = new Array(30).fill(null);
seamFrame[11] = mkP(102, 0, 0);
eq("重启缝 实测帧 首采即链末桶->提示(旧口径恒 null)", _qbSeamHint(seamFrame, 2, { server_started_at: 101 }), { startedAt: 101 });
eq("重启缝 实测帧 边界 恰在链末前一桶起点->提示", _qbSeamHint(seamFrame, 2, { server_started_at: 100 }), { startedAt: 100 });
eq("重启缝 实测帧 早一桶宽->null", _qbSeamHint(seamFrame, 2, { server_started_at: 99 }), null);

// —— schema=2 显式空值点形态(26-11-18-0037 阶段 3): 链末按**列值**判(空值点不算观测),
//    右沿 = 末点真值 t(旧等距外推 (n-last)*interval 退役; 旧契约末桶无 t 时承袭外推) ——
const seamPts2 = [mkP(100, 5, 5), mkP(130, 6, 6), GP(160), GP(190), GP(220)];
eq("重启缝(schema=2) 尾部显式空值点 + 重启贴近链末->提示", _qbSeamHint(seamPts2, 30, { server_started_at: 178 }), { startedAt: 178 });
eq("重启缝(schema=2) 边界 恰在末点真值 t(右沿)->提示", _qbSeamHint(seamPts2, 30, { server_started_at: 220 }), { startedAt: 220 });
eq("重启缝(schema=2) 晚于末点真值 t->null(链在重启前已断/重启尚未产生观测, 断连走徽标面)", _qbSeamHint(seamPts2, 30, { server_started_at: 250 }), null);
eq("重启缝(schema=2) 边界 恰在链末前一个组距起点->提示", _qbSeamHint(seamPts2, 30, { server_started_at: 100 }), { startedAt: 100 });
eq("重启缝(schema=2) 早于链末前一个组距->null(链确已接续)", _qbSeamHint(seamPts2, 30, { server_started_at: 99 }), null);
eq("重启缝(schema=2) 链末真值点(尾组恒真值, 链到右沿)->null", _qbSeamHint([mkP(100, 5, 5), GP(130), mkP(190, 1, 1)], 30, { server_started_at: 178 }), null);
eq("重启缝(schema=2) 链末即显式空值点->按列值判不算观测", _qbSeamHint([mkP(100, 5, 5), mkP(130, 6, 6), GP(160)], 30, { server_started_at: 145 }), { startedAt: 145 });
eq("重启缝(schema=2) 全空值点->null(空态面)", _qbSeamHint([GP(100), GP(130)], 30, { server_started_at: 178 }), null);

/* ---------- 缺口斜纹**配色 + 几何**真跑(2026-10-08 两轮) ----------
 * 用记账式假 ctx 调**真实的** AQB_QB_TRAFFIC.methods._qbDrawGaps, 断言:
 *   1. 配色: 写进画布的 strokeStyle/globalAlpha 是高对比专用令牌而非 --hairline 系极低 alpha;
 *   2. 几何: 逐 run 追加的**缺口矩形 clip** 恰好等于 [xa, xb] x [T, T+H], 且每条斜纹线段都被该
 *      矩形包含(端点 x 落在 [xa, xb])—— 钉死"斜纹铺成竖矩形"的语义: 若有人删掉 per-run clip
 *      (退回只裁绘图区), 斜带(宽 H 的平行四边形)的端点会越出 [xa, xb], 断言立刻变红。
 * 这条电池的价值: 把"颜色够不够看得见""斜纹落在哪"从"读源码字符串"升级为"实跑取真值并做数值/
 * 几何判定" —— 静态锚可能被同步改掉, 数值下界与几何包含判定不会。 */
function _mkCtx2() {
  const noop = () => {};
  return {
    style: null, alpha: null, segCount: 0, _x0: 0,
    clips: [], _pendingRect: null, _segs: [],
    save: noop, restore: noop, beginPath: noop, setLineDash: noop,
    rect(x, y, w, h) { this._pendingRect = { x, y, w, h }; },
    clip() { if (this._pendingRect) this.clips.push(this._pendingRect); },
    moveTo(x, y) { this._sx = x; },
    lineTo(x, y) { this.segCount++; this._segs.push([this._sx, x]); },
    stroke() {},
    set strokeStyle(v) { this.style = v; },
    get strokeStyle() { return this.style; },
    set globalAlpha(v) { this.alpha = v; },
    get globalAlpha() { return this.alpha; },
    set lineWidth(v) {}, get lineWidth() { return 1; },
  };
}
(function () {
  const AQB2 = global.window.AQB_QB_TRAFFIC;
  const fn = AQB2 && AQB2.methods && AQB2.methods._qbDrawGaps;
  ok("_qbDrawGaps 可取(配色电池)", !!fn);
  if (!fn) return;
  const xs2 = [0, 60, 120, 180, 240];
  const ctx2 = _mkCtx2();
  const u2 = {
    data: [xs2, [5, 5, null, null, 5], [5, 5, null, null, 5]],
    bbox: { left: 50, top: 17, width: 825, height: 233 },
    ctx: ctx2,
    valToPos: (v) => (xs2.indexOf(v) / 4) * 825,
  };
  /* tk.gap = 高对比专用令牌值; tk.grid = 旧的 --hairline 极低 alpha 值 —— 必须选前者 */
  fn.call({ _qbCanvasScale: (uu) => { uu.ctx.save(); return 1; } }, u2,
    { grid: "rgba(255,255,255,.055)", gap: "rgba(255,255,255,.22)" });
  eq("斜纹取 gap 专用令牌(不取 --hairline)", ctx2.style, "rgba(255,255,255,.22)");
  eq("斜纹不再叠 globalAlpha 折半", ctx2.alpha, 1);
  ok("斜纹确实画了线段(>0 条)", ctx2.segCount > 0);
  /* 数值下界: 令牌 alpha 必须 >= 0.15(--hairline 系 0.055 量级的 3 倍以上才算"看得见") */
  const m2 = /rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([\d.]+)\s*\)/.exec(
    "rgba(255,255,255,.22)");
  ok("专用令牌 alpha 量级 >= 0.15(0.05 级别等同不可见)", m2 && parseFloat(m2[1]) * ctx2.alpha >= 0.15);

  // ---- 几何: per-run 缺口矩形 clip + 扫线覆盖 ----
  // 注: 真实 ctx 的 clip 是**画布操作**, 不会改写我们记账到的原始端点 —— 故原始 moveTo/lineTo
  // 端点本就会越出 [xa, xb](越界部分由 canvas clip 收掉)。几何正确性由两点钉死:
  //   1. per-run 缺口矩形 clip 存在且 == [xa, xb] x [T, T+H](删掉它即退回"只裁绘图区"= 平行四边形缺陷);
  //   2. 扫线范围**覆盖**缺口带(有线段右下端 >= xb, 有线段左上端 <= xa)—— 保证裁剪后左/右竖直边都铺满, 无半边留白。
  const xa = 50 + (xs2.indexOf(120) / 4) * 825;   // 缺口 = 桶 2..3
  const xb = 50 + (xs2.indexOf(180) / 4) * 825;
  const T = 17, H = 233;
  const gapClips = ctx2.clips.filter((c) => Math.abs(c.x - xa) < 1e-6 && Math.abs(c.w - (xb - xa)) < 1e-6
    && Math.abs(c.y - T) < 1e-6 && Math.abs(c.h - H) < 1e-6);
  ok("存在逐 run 缺口矩形 clip(ctx.rect(xa, T, xb-xa, H))", gapClips.length >= 1);
  ok("缺口矩形 clip 与绘图区 clip 并存(外层仍收在绘图区)",
    ctx2.clips.some((c) => Math.abs(c.w - 825) < 1e-6));
  const segs = ctx2._segs || [];
  // 扫线覆盖: 每条线段 = [左上端 x0, 右下端 x1](x0 = x-H, x1 = x); 需有 x1 >= xb(右端铺满)
  // 且有 x0 <= xa(左端铺满)。
  ok("扫线覆盖缺口左边界(有线段左上端 <= xa)", segs.some((s) => s[0] <= xa + 1e-6));
  ok("扫线覆盖缺口右边界(有线段右下端 >= xb)", segs.some((s) => s[1] >= xb - 1e-6));
  // 扫线步长恒定 8px(斜纹间距), 且每条线段水平跨度 = H(45 度硬约束)
  ok("每条斜纹线段跨度 = H(45 度)", segs.every((s) => Math.abs((s[1] - s[0]) - H) < 1e-6));
})();

(function () {
  /* ---------- 缺口斜纹**只给数据链中段**(2026-10-30) ----------
   * 斜纹是「中断」的视觉记号; 链外的空白(首次采样之前 / 最后一次之后 / 全帧无观测)同样是
   * 「不知道原因的没有数据」, 铺斜纹等于在视觉上重复一遍 tooltip 已纠掉的归因错误。
   * 用同一份记账式假 ctx 实跑真 _qbDrawGaps, 断言那些段**一笔都没画**。 */
  const fn3 = global.window.AQB_QB_TRAFFIC && global.window.AQB_QB_TRAFFIC.methods._qbDrawGaps;
  ok("_qbDrawGaps 可取(区段电池)", !!fn3);
  if (!fn3) return;
  const xs3 = [0, 60, 120, 180];
  const paint = (up, dl) => {
    const c = _mkCtx2();
    fn3.call({ _qbCanvasScale: (z) => { z.ctx.save(); return 1; } }, {
      data: [xs3, up, dl],
      bbox: { left: 50, top: 17, width: 825, height: 233 },
      ctx: c,
      valToPos: (v) => (xs3.indexOf(v) / 3) * 825,
    }, { grid: "rgba(255,255,255,.055)", gap: "rgba(255,255,255,.22)" });
    return c;
  };
  const head = paint([null, null, 5, 6], [null, null, 5, 6]);     // 链首之前的空白
  ok("链首之外的空白不铺斜纹(0 条线段)", head.segCount === 0);
  ok("链首之外不落逐 run 缺口 clip", head.clips.length === 0);
  const tail = paint([5, 6, null, null], [5, 6, null, null]);     // 链尾之后的空白
  ok("链尾之外的空白不铺斜纹(0 条线段)", tail.segCount === 0);
  const none = paint([null, null, null, null], [null, null, null, null]);
  ok("全帧无观测不铺斜纹(0 条线段)", none.segCount === 0);
  const inner = paint([5, null, null, 6], [5, null, null, 6]);    // 链中间的洞
  ok("链中间的洞照旧铺斜纹", inner.segCount > 0);
  ok("链中间的洞仍落逐 run 缺口 clip", inner.clips.length >= 2);
})();

(function () {
  /* ---------- 限速分段(plan 26-10-12-0535 D4/D7)真跑: _qbLimitSegs/_qbLimitAt ----------
   * 用真实的模块级纯函数断言: 每段几何(区间/末段到 tEnd)/退化段不画/悬停二分取值
   * (含记录起点前 null)。若有人把分段改回单值画满整窗, 本电池立刻红。 */
  ok("_qbLimitSegs 可取", typeof _qbLimitSegs === "function");
  ok("_qbLimitAt 可取", typeof _qbLimitAt === "function");
  const EV = [[100, 1024, 2048], [200, 0, 4096], [300, 512, 512]];
  eq("分段几何: 每段 = 相邻事件区间", _qbLimitSegs(EV, 400),
    [{ t0: 100, t1: 200, up: 1024, down: 2048 }, { t0: 200, t1: 300, up: 0, down: 4096 }, { t0: 300, t1: 400, up: 512, down: 512 }]);
  eq("分段: 末段延伸到 tEnd", _qbLimitSegs(EV.slice(0, 1), 250), [{ t0: 100, t1: 250, up: 1024, down: 2048 }]);
  eq("分段: 空事件空段", _qbLimitSegs([], 400), []);
  eq("分段: 非法输入空段", _qbLimitSegs(null, 400), []);
  eq("分段: tEnd 非法空段", _qbLimitSegs(EV, 0), []);
  eq("分段: 越出右沿的退化段不画", _qbLimitSegs([[500, 1, 1]], 400), []);
  eq("悬停二分: 取 <= ts 最近事件", _qbLimitAt(EV, 250), [0, 4096]);
  eq("悬停二分: 精确命中", _qbLimitAt(EV, 200), [0, 4096]);
  eq("悬停二分: 记录起点前 null(D5 不猜)", _qbLimitAt(EV, 50), null);
  eq("悬停二分: 空事件 null", _qbLimitAt([], 100), null);
  eq("悬停二分: 末事件之后仍取末值", _qbLimitAt(EV, 999), [512, 512]);
})();
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""

# _QB_SCOPES 是模块级 `const`, sloppy 模式下的直接 eval 不会把它漏到外层作用域(只有 function/var
# 声明会漏) —— 故这里用 `new Function(源码 + "return _QB_SCOPES;")` 把它从函数体内部取出来,
# 再对三个作用域的 `stale` 谓词喂真值上下文做**行为**断言(不读源码字符串)。
_NODE_QB_SCOPE_STALE_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const SCOPES = new Function(src + "\nreturn _QB_SCOPES;")();
const checks = [];
const ok = (n, cond) => checks.push([n, !!cond]);

/* stale 谓词语义(见 qb_traffic_chart.js 文件头): stale=true = 在途响应**已过期** -> 丢弃
 * (不落袋 + loading 不清)。故「本图正在被看」必须 stale=false, 其余一律 stale=true。
 * 2026-10-12 修: W2–W6 机械改名把 torrent/group 两处 `!(...)` 写成 `!!(...)`, 语义整个翻转
 * (恰在本图活跃时判过期) -> 数据永不落袋、loading 卡死 -> 种子流量页签恒停「正在加载…」。
 * 本电池就是那个漏网的运行时判据: 取反写反(单/双 bang 互换)立刻红。 */
const G = (over) => Object.assign(
  { drawer: { open: true, scope: "global" }, drawerIsTraffic: true, drawerIsSeed: false, page: "groups" },
  over || {});
ok("global: 正看全局图 stale=false(数据必须落袋)", SCOPES.global.stale(G()) === false);
ok("global: 已切到分组图 stale=true(旧响应丢弃)",
  SCOPES.global.stale(G({ drawer: { open: true, scope: "group" } })) === true);
ok("global: 面板已关 stale=true", SCOPES.global.stale(G({ drawer: { open: false, scope: "global" } })) === true);

const H = "a".repeat(40);
const T = (over) => Object.assign(
  { drawer: { open: true, tab: "traffic", hash: H }, drawerIsSeed: true, qbTrafficOn: true }, over || {});
ok("torrent: 正看该种子流量页签 stale=false(本次报障点: 恒 true 即卡在加载态)",
  SCOPES.torrent.stale(T(), H) === false);
ok("torrent: 已换目标(hash 不符) stale=true", SCOPES.torrent.stale(T(), "b".repeat(40)) === true);
ok("torrent: 已切到别的页签 stale=true",
  SCOPES.torrent.stale(T({ drawer: { open: true, tab: "general", hash: H } }), H) === true);
ok("torrent: 面板已关 stale=true",
  SCOPES.torrent.stale(T({ drawer: { open: false, tab: "traffic", hash: H } }), H) === true);
ok("torrent: 非种子形态(流量形态) stale=true",
  SCOPES.torrent.stale(T({ drawerIsSeed: false }), H) === true);
ok("torrent: 功能未启用 stale=true", SCOPES.torrent.stale(T({ qbTrafficOn: false }), H) === true);

const K = "Z3JvdXA";  // 分组 key(base64url 形态, 内容无关)
const R = (over) => Object.assign(
  { drawer: { open: true, scope: "group" }, drawerIsTraffic: true, qbGroupKey: K, qbTrafficOn: true },
  over || {});
ok("group: 正看分组流量图 stale=false", SCOPES.group.stale(R(), K) === false);
ok("group: 已换分组 stale=true", SCOPES.group.stale(R(), "other") === true);
ok("group: 面板已关 stale=true", SCOPES.group.stale(R({ drawer: { open: false, scope: "group" } }), K) === true);
ok("group: 已切到全局图 stale=true",
  SCOPES.group.stale(R({ drawer: { open: true, scope: "global" } }), K) === true);

/* active 与 stale 必须**同向**: active=true(该图应显示/可拉)时 stale 必须=false —— 两谓词
 * 若各自漂移(本次根因), 这一条把「图该显示但数据被判过期」的组合直接钉死。 */
ok("同向性: global active 时 stale=false",
  !SCOPES.global.active(G()) || SCOPES.global.stale(G()) === false);
ok("同向性: torrent active 时 stale=false",
  !SCOPES.torrent.active(T()) || SCOPES.torrent.stale(T(), H) === false);
ok("同向性: group active 时 stale=false",
  !SCOPES.group.active(R()) || SCOPES.group.stale(R(), K) === false);

/* ---------- 消费端真跑: _qbLoad 落袋 + loading 复位(用户可见症状的判据) ----------
 * 只钉谓词还不够 —— 真正让用户看到「加载不出来」的是 _qbLoad 里 stale=true 触发的
 * 「数据不落袋 + loading 不复位 + 早退不建图」。这里用真实的方法体配一个假 vm 跑一遍,
 * 断言成功响应确实落进 qbTorrentData/qbGroupData 且 loading 归位(即图会画)。 */
const M = global.window.AQB_QB_TRAFFIC.methods;
const mkVm = (scope) => ({
  qbTrafficOn: true,
  drawer: { open: true, tab: "traffic", hash: H, scope: scope === "torrent" ? undefined : "group" },
  drawerIsSeed: scope === "torrent",
  drawerIsTraffic: scope !== "torrent",
  page: "groups",
  qbGroupKey: K,
  qbTorrentWindow: "24h", qbTorrentLoading: false, qbTorrentData: null, qbTorrentError: "",
  qbGroupWindow: "24h", qbGroupLoading: false, qbGroupData: null, qbGroupError: "",
  api: async () => ({ points: [{ t: 1000, up: 10, dl: 20 }], totals: [{ up: 10, dl: 20 }], limits: [],
    meta: { interval_s: 30 } }),
  $nextTick: (fn) => { if (fn) fn(); },
  _qbChartBuild: () => {}, _qbPollResync: () => {}, _drawerDone: () => {},
  _qbStreamOnLoad: () => {},  // T4a: GET 落袋的对账基准单点(无流态零操作 —— 桩面同生产守卫)
});
(async () => {
  const vt = mkVm("torrent");
  await M._qbLoad.call(vt, "torrent");
  ok("落袋: 种子流量响应进入 qbTorrentData(非 null)", vt.qbTorrentData !== null);
  ok("落袋: 种子 loading 已复位(false)", vt.qbTorrentLoading === false);
  ok("落袋: 无错误态", vt.qbTorrentError === "");

  const vg = mkVm("group");
  await M._qbLoad.call(vg, "group");
  ok("落袋: 分组流量响应进入 qbGroupData(非 null)", vg.qbGroupData !== null);
  ok("落袋: 分组 loading 已复位(false)", vg.qbGroupLoading === false);

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})();
"""


def test_frontend_qb_traffic_scope_stale_polarity():
    """流量图三挂点 stale 谓词极性守阵(2026-10-12 修「种子流量图加载不出来」)

    缺陷: W2–W6 抽屉重构的机械改名(``drawer.kind === "seed"`` -> ``drawerIsSeed``)把 torrent 与
    group 两处 ``stale`` 谓词从 ``!(...)`` 写成 ``!!(...)`` —— 取反变双重取反, 语义**整个翻转**:
    恰在本图活跃时判「响应已过期」。后果链: ``_qbLoad`` 里 ``stale=true`` -> 数据不落袋 + loading
    不复位 + 早退不建图 -> ``qbCurPending``(loading && 无数据 && 无错误)恒真 -> 种子「流量」页签
    永远停在「正在加载流量数据…」; 轮询 tick 又被 ``loading`` 卡住 -> 不会自愈。global 挂点未中招
    (仍是 ``!(...)``), 故症状只在种子/分组图。

    为什么既有守阵没拦住: 本文件对 ``_QB_SCOPES`` 的断言全是**源码字符串**级的(字段名/字面量
    在不在), 而 ``!!`` 与 ``!`` 的差别只在运行时语义 —— 静态锚对它天然失明。

    本守阵两层:
    1. **运行时行为**(node 电池, 主判据): 用 ``new Function(源码 + "return _QB_SCOPES;")`` 取出
       作用域表, 对三挂点喂「本图活跃 / 已切走 / 已关闭 / 换目标 / 功能关闭」五类真值上下文, 断言
       ``stale`` 取假/取真与契约一致, 并钉 ``active => stale === false`` 同向性;
    2. **静态极性**(无 node 兜底, 也钉书写形态): 两处 ``stale`` 谓词必须是否定式 ``!(``, ``!!(``
       形态不得回潮(本次根因的书写面)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()

    # 1. 静态极性: stale 谓词是否定式(`!(`), 禁双重取反 `!!(`
    scopes = re.search(r"const _QB_SCOPES = \{\n(.*?)\n\};", js, re.S)
    assert scopes, "缺 _QB_SCOPES 作用域表(三挂点单一描述源)"
    sb = "\n" + scopes.group(1)
    for scope in ("torrent", "group"):
        seg = sb.split("\n  %s: {" % scope)[1].split("stale:")[1]
        expr = seg.split("),")[0]
        assert re.search(r"=>\s*!\(t", expr), \
            f"{scope}.stale 必须是否定式 `!(...)`(stale=true 表示响应已过期丢弃; " \
            f"写成 `!!(...)` 语义翻转 -> 图恒不加载), 实测: stale:{expr[:60]}"
        assert "!!(" not in expr, \
            f"{scope}.stale 出现双重取反 `!!(...)`(2026-10-12 事故书写形态: 恰在活跃时判过期)"

    # 2. 运行时行为(node 电池; 无 node 静默跳过, 静态极性仍已生效)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_STDIN_WRAPPER,
             os.path.join(shared, "qb_traffic_chart.js")],
            input=_NODE_QB_SCOPE_STALE_PROBE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"stale 极性 node 电池跑挂: {proc.stderr.strip()}"
        rep = json.loads(proc.stdout.strip().splitlines()[-1])
        assert rep["failed"] == [], f"stale 极性电池 {rep['ok']}/{rep['total']} 过, 失败: {rep['failed']}"


def test_frontend_qb_traffic_yaxis_and_annotation():
    """流量图纵轴固定模式 + 画布注解层守阵(2026-10-08, issue 26-10-07-0149 认领一并做)

    用户需求: 纵轴最大值可固定(自动 / 限速+20% / 手动 MiB/s), 峰值超出固定上限时**按峰值显示**;
    附限速虚线 + 缺口斜纹注解层(共享图面, 三挂点 + 经典/所有变体全生效)。钉住四条静默失效面:
    1. 值域语义(_qbYRange 纯函数 node 真跑): 自动 = peak*1.05(无数据回落 1); 固定上限取
       max(cap, peak*1.05) —— **上限只保底不裁剪**(峰值超上限按峰值显示, 用户拍板); 限速三
       作用域同源 = qB 全局限速上下行**较大者**(单点 _qbGlobalLimit -> speedLimitBytes);
    2. 缺口游程(_qbGapRuns node 真跑): 上下行**皆** null 才算缺口(单列 null 防御性不误判;
       schema=2 显式空值点与旧契约 null 桶转列后同判, 26-11-18-0037 阶段 3);
    3. 持久化粒度 = **三作用域各自独立**(qbYAxisStoreKey 三键, 与窗口档位的「全局单独/组种
       共用」不同); 初值 qbInitialYAxis 只认合法模式 + 正数手动值, 坏值/无存储回落默认;
    4. 接线与三皮肤成对: 切模式/改值/落盘/重排四件 + 建图 y range 走 _qbYRange(_qbYCapOf(scope))
       + draw/drawClear 两钩子画注解层(uPlot 1.6.x ctx 无 transform = 设备像素, 按 uPlot.pxRatio
       换算; 限速线只画落在可视值域内的)+ 模板控件(.qb-seg 三态 + 手动输入 + 生效上限读数) +
       CSS .qb-seg/.qb-yaxis-input 三皮肤成对。
    5. 缺口斜纹**配色**(2026-10-08 修用户报「颜色几乎不可分辨」): 斜纹色原走 tk.grid =
       --hairline(装饰性 1px 发丝线令牌, 实测 alpha 仅 0.05~0.08)再叠 globalAlpha 0.5 ⇒ 有效
       不透明度约 3%, 深浅底上**都**等于没画。守阵 = node 电池实跑 _qbDrawGaps 取真值断言
       strokeStyle 走专用令牌 --qb-gap-hatch 且不叠 alpha 折半 + 令牌量级下界 >=0.15; 静态锚
       钉令牌在三皮肤 + prism 五主题成对定义、亮主题(frost/golden)不得用白色(镜面缺陷)。
       附: 斜纹**几何**经逐条线段比对与代数验证与原式恒等, 故**不设**"位移"类锚(该说法经实测
       证伪, 设了就是假锚)。
    6. 重启缝提示(P4, plan 26-10-15-0829; 左端口径修订 2026-10-16, issue 26-10-16-0954;
       右沿改真值 t + 链末按列值判 26-11-18-0037 阶段 3): 判据单点 _qbSeamHint 纯函数 node 真跑
       (重启贴近链末 -> 提示, 含「重启后首采即链末桶」的实测帧形态 / 链到右沿或链确已接续
       (重启早于链末前一桶)或旧后端无新键 -> null, 边界含尾区起点、右沿与左端「链末桶前一桶
       起点」三点; schema=2 显式空值点形态: 显式空值点不算观测/右沿 = 末点真值 t/尾组真值点
       链到右沿 -> null/全空值点空态面 -> null) + computed qbCurSeamHint 消费单点 + drawer.html
       提示行(三挂点共用正文块一处, 文案单源, 带服务重启时刻锚 fmtTime) + null 不连线
       spanGaps:false 原样。
    7. 缺口的**区段分治**(2026-10-30, 用户报「种子添加之前的时间提示说成 qB 断联不符合实际」):
       判据 _qbChainBounds/_qbGapZone node 真跑(数据链 = 首/末个非空桶; outside = 链首之前 /
       链尾之后 / 全帧无观测, 判据**只认本帧 points**、不碰种子 added_on —— 跳检即删同 hash
       再重加且流量按 infohash 留存, 用 added_on 切一刀会把早期真实数据误判成「尚未添加」);
       斜纹只给链中段的洞(node 电池实跑 _qbDrawGaps: 链外段线段数与 clip 数皆 0, 链中段照旧
       铺), 链外空白由 tooltip 用中性文字陈述; 文案按「区段 × 作用域」收在 computed 单点
       qbCurGapText(全局态没有"种子"这一主语, 一律套「此种子」是又一次瞎编)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()
    # W3(计划 26-10-11-2106): 档位/纵轴控件组的唯一实现住在这里(<aq-qb-ctl>)
    head_tpl = open(os.path.join(shared, "tpl", "drawer-head.html"), encoding="utf-8").read()

    # 1. 常量单点(模式清单 / 默认 / 倍率 / MiB 换算)
    assert 'const QB_YAXIS_MODES = ["auto", "limit", "manual"];' in js, "缺 QB_YAXIS_MODES 三态单点"
    assert 'QB_YAXIS_DEFAULT = "auto"' in js, "缺 QB_YAXIS_DEFAULT(初值/坏值回落)"
    assert "QB_YAXIS_LIMIT_FACTOR = 1.2" in js, "缺限速倍率 1.2 单点"
    assert "QB_YAXIS_MIB = 1024 * 1024" in js, "缺手动值 MiB 换算单点"

    # 2. 值域 + 缺口游程 node 真跑(无 node 静默跳过)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_STDIN_WRAPPER,
             os.path.join(shared, "qb_traffic_chart.js")],
            input=_NODE_QB_YAXIS_PROBE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"纵轴值域/缺口游程 node 电池跑挂: {proc.stderr.strip()}"
        rep = json.loads(proc.stdout.strip().splitlines()[-1])
        assert rep["failed"] == [], f"纵轴/缺口电池 {rep['ok']}/{rep['total']} 过, 失败: {rep['failed']}"

    # 3. 限速来源单点(三作用域同源): qB 全局限速上下行较大者
    lim = re.search(r"_qbGlobalLimit\(\) \{\n(.*?)\n    \},", js, re.S)
    assert lim, "缺 _qbGlobalLimit(全局限速单点)"
    lb = lim.group(1)
    assert "this.speedLimitBytes" in lb, "_qbGlobalLimit 必须取 speedLimitBytes 单点(与状态栏/速度染色同源)"
    # 2026-10-08 版式改后常驻说明区退役; D4 文案挂在统计栏悬浮说明单点(qbCurSummaryHint)
    assert "限速虚线 = 当时生效的 qB 全局限速" in js and "记录起点前不显示" in js, \
        "缺 D4 文案(限速线取值口径 + 记录起点前不显示, qbCurSummaryHint 单点)"
    assert "up" in lb and "down" in lb and "best" in lb, \
        "全局限速必须取上下行**较大者**(纵轴上下行共用一条, 取大者两条曲线都落在上限内)"

    # 4. 上限派生单点: limit = 全局限速×1.2 / manual = MiB 换算 / auto = 0(不固定)
    cap = re.search(r"_qbYCapOf\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert cap, "缺 _qbYCapOf(固定上限派生单点)"
    cb = cap.group(1)
    assert 'y.mode === "limit"' in cb and "* QB_YAXIS_LIMIT_FACTOR" in cb, "limit 模式必须 = 全局限速 ×1.2"
    assert 'y.mode === "manual"' in cb and "* QB_YAXIS_MIB" in cb, "manual 模式必须按 MiB 换算"

    # 5. 建图接线: y range 走纯函数 + 两钩子画注解层(共享图面)
    assert "y: { range: (u, dmin, dmax) => _qbYRange(dmax, this._qbYCapOf(scope)) }" in js, \
        "建图 y range 未接 _qbYRange/_qbYCapOf(固定上限不生效)"
    # S2-a 起钩子序即 I6 图层序(vendor 1.6.32 实证: drawAxes 在 Dl.axes 末尾 = 网格后、系列前):
    # drawClear = 斜纹(恒最底), drawAxes = 几何/N 层(网格后系列前), draw = 限速线 → 锚(系列之上)
    assert "drawClear: [(u) => this._qbDrawGaps(u, tk)]" in js, \
        "缺缺口斜纹 drawClear 钩子(恒最底, 与网格相互独立)"
    assert "drawAxes: [(u) => this._qbDrawFx(u, tk)]" in js, \
        "缺 fx 装饰段 drawAxes 钩子(网格之后、系列原生之前 —— 挂 drawClear 会被网格盖住, I6 层序)"
    assert "draw: [(u) => this._qbDrawLimits(u, tk), (u) => this._qbDrawFxCurveGlow(u, tk), (u) => this._qbDrawFxAnchor(u, tk)]" in js, \
        "缺限速虚线 draw 钩子(画在系列之上; 曲线辉光常驻段居中, 锚段紧随其后)"

    # 6. 重启缝提示(P4, plan 26-10-15-0829): 判据单点 + computed 消费单点 + 模板提示行
    #    (node 真跑在上面第 2 段电池里; 这里钉接线与文案单源)
    assert js.count("function _qbSeamHint") == 1, "缺/多 _qbSeamHint 判据定义(重启缝 vs 停机洞区分判据必须单点)"
    # 左端口径活性锚(issue 26-10-16-0954): 左端必须为「链末桶前一桶起点」而非链末桶覆盖端 —— 旧口径
    # 把「重启后首采已入账」形态静默漏判; 整行匹配, 改口径须同步 node 电池(判据语义由电池钉住)
    assert "if (started < chainPrevStart || started > rightEdge) return null;" in js, \
        "缺 重启缝判据左端行(chainPrevStart = 链末桶前一桶起点; 修订见 issue 26-10-16-0954)"
    seam_cmp = re.search(r"qbCurSeamHint\(\) \{\n(.*?)\n    \},", js, re.S)
    assert seam_cmp and "_qbSeamHint(d.points" in seam_cmp.group(1), \
        "缺 qbCurSeamHint computed(模板消费单点, 必须经 _qbSeamHint 判据)"
    assert 'v-if="qbCurSeamHint"' in drawer_tpl and "qb-seam" in drawer_tpl, \
        "drawer.html 缺重启缝提示行(数据接缝中, 三挂点共用正文块)"
    assert drawer_tpl.count("数据接缝中") == 1, "接缝文案必须单源(只此一处)"
    assert "fmtTime(qbCurSeamHint.startedAt)" in drawer_tpl, "接缝提示必须带服务重启时刻锚(fmtTime)"
    # 断线语义不变(P4 纪律): null 不连线与斜纹钩子原样, 提示只是追加状态行
    assert js.count("spanGaps: false") == 2, "断线语义不得变(spanGaps:false 上下载两系列都在)"
    for member in ("_qbCanvasScale(u)", "_qbDrawGaps(u, tk)", "_qbDrawLimits(u, tk)"):
        assert member in js, f"缺画布注解层成员 {member}"
    assert "uPlot.pxRatio" in js, "画布注解层必须按 uPlot.pxRatio 换算设备像素(uPlot ctx 无 transform)"
    dl = re.search(r"_qbDrawLimits\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert dl, "缺 _qbDrawLimits(限速虚线注解)"
    dlb = dl.group(1)
    # D4(plan 26-10-12-0535)分段化: 取值改图记录上的事件序列(不再读 speedLimitBytes 单值),
    # 段几何走纯函数, 可见性逐段(0 < v < ymax), 末段延伸到图右沿
    assert "u._qbLimits" in dlb, "_qbDrawLimits 必须取图记录上的限速事件序列(u._qbLimits, D4 分段)"
    assert "speedLimitBytes" not in dlb, "_qbDrawLimits 不得再读单点当前值(旧「单值画满整窗」回潮)"
    assert "_qbLimitSegs(" in dlb, "限速段必须走 _qbLimitSegs 纯函数(段几何 node 电池同源)"
    assert "seg.up < ymax" in dlb and "seg.down < ymax" in dlb, \
        "限速虚线可见性必须逐段判(每段每方向 0 < v < ymax)"
    assert "seg.up > 0" in dlb and "seg.down > 0" in dlb, "0(不限速)/缺值段不画"
    # 快路/建图两路都要把 limits 暂存在图记录上(否则限速变更要等整图重建才可见)
    assert js.count("prev._qbLimits =") == 1 and js.count("u._qbLimits =") == 1, \
        "limits 暂存必须同时接在 setData 快路(prev._qbLimits)与整图重建(u._qbLimits)两路"
    # D7: 悬停读数走纯函数 _qbLimitAt + 模板两支(正常/缺口)都接当时限速行
    assert "_qbLimitAt(d.limits || [], ts)" in js, "悬停读数必须走 _qbLimitAt(当时值, D7)"
    assert drawer_tpl.count('v-if="qbCurHover.lim"') == 2, \
        "当时限速行必须在正常/缺口两支 tooltip 各接一处(限速是时间真值, 缺口也读)"
    assert 'class="h-limit"' in drawer_tpl, "当时限速行缺 h-limit 类(样式挂点)"

    # 5b. 缺口斜纹**配色 + 几何**守阵(2026-10-08 两轮: 先修「颜色几乎不可分辨」, 再修「未落到
    # 正确区域 / 倾斜超出范围」)
    # 配色根因: 斜纹色原走 tk.grid = --hairline(装饰性 1px 发丝线令牌, 实测 alpha 仅 0.05~0.08),
    # 再叠 globalAlpha 0.5 ⇒ 有效不透明度约 3%, 深/亮底色上**都**等于没画。修法 = 专用高对比
    # 令牌 --qb-gap-hatch + 去掉多余的 globalAlpha 折半。
    # 几何根因(第二轮, 首轮曾误判为"颜色不可见导致无法判读落点"): 斜纹原只按底端 x 扫
    # [xa-H, xb+H] 再让外层 clip 收到**整个绘图区** —— 45 度线段水平跨度恒为 H, 并集是"宽 H 的
    # **斜向平行四边形**"(左右边界皆斜边), 缺口右段下半留白、左段上半越界到缺口左侧, 即用户报
    # 「未落到正确区域, 倾斜超出范围」。修法 = **逐 run 追加一次 clip 到缺口矩形**(见 _qbDrawGaps
    # 内「几何硬约束」注释), 斜纹被裁成以缺口区间为左右竖直边的竖矩形。
    gp = re.search(r"_qbDrawGaps\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert gp, "缺 _qbDrawGaps(缺口斜纹注解)"
    gb = gp.group(1)
    assert "ctx.strokeStyle = tk.gap || tk.grid;" in gb, \
        "缺口斜纹色必须走专用令牌 tk.gap(回退 tk.grid 兜底), 不得直用极低 alpha 的 tk.grid"
    assert "ctx.globalAlpha = 1;" in gb, \
        "缺口斜纹不得再叠 globalAlpha <1(--hairline 已是 0.055, 再砍半等于不可见)"
    assert "ctx.moveTo(x - H, T + H)" in gb and "ctx.lineTo(x, T)" in gb, \
        "斜纹线段必须为 (x-H, T+H) -> (x, T)(45 度, 右下角在 x)"
    assert "ctx.rect(L, T, W, H)" in gb and "ctx.clip()" in gb, \
        "缺口斜纹必须裁剪在绘图区内(两端超出部分不得越 y 轴/时间轴)"
    # 几何硬约束: 逐 run 裁到**缺口矩形** [xa, xb] x [T, T+H](把斜带裁成竖矩形)
    assert "ctx.rect(xa, T, xb - xa, H)" in gb, \
        "缺口斜纹必须逐 run 裁到缺口矩形 ctx.rect(xa, T, xb-xa, H) —— 否则 45 度斜带铺成" \
        "平行四边形: 缺口右段留白、斜边越出缺口带(用户报「未落到正确区域/倾斜超出范围」)"
    assert "if (!(xb > xa)) continue;" in gb, \
        "缺口宽度非正(退化 run)必须跳过, 不得画零宽/负宽矩形"
    tkb = re.search(r"_qbChartTokens\(\) \{\n(.*?)\n    \},", js, re.S)
    assert tkb, "缺 _qbChartTokens(建图令牌单点)"
    assert 'gap: pick("--qb-gap-hatch"' in tkb.group(1), \
        "建图令牌必须产出 gap = --qb-gap-hatch(缺口斜纹专用高对比令牌)"
    # 令牌各皮肤 + prism 五主题必须各自定义(缺一个就是那套皮肤下斜纹不可见; flux 收编 S5)
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas"),
        (_ui_css_aggregate("console"), "console"),
        (_ui_css_aggregate("prism"), "prism"),
        (_ui_css_aggregate("flux"), "flux"),
    ):
        assert "--qb-gap-hatch:" in css, f"{name} 皮肤缺 --qb-gap-hatch 令牌(缺口斜纹不可见)"
    for theme in ("ocean", "galaxy", "orbit", "frost", "golden"):
        tf = os.path.join(STATIC_ROOT, "prism", "css", "themes", f"{theme}.css")
        tt = open(tf, encoding="utf-8").read()
        assert "--qb-gap-hatch:" in tt, f"prism 主题 {theme} 缺 --qb-gap-hatch 令牌"
        # 亮主题必须用深墨色而非白色(白纹在白底/米底上等于无 —— 与深主题同式的镜面缺陷)
        if theme in ("frost", "golden"):
            hx = re.search(r"--qb-gap-hatch:\s*([^;]+);", tt).group(1)
            assert "255, 255, 255" not in hx, f"亮主题 {theme} 的斜纹色不得用白色(底纹不可见)"

    # 6. 持久化: 三作用域各自独立 + 键单点 + 初值校验 + 落盘吞异常 + 切档重排(不重取数)
    for scope, key in (
        ("global", "autoqb.ui.qbYAxisGlobal"), ("torrent", "autoqb.ui.qbYAxisTorrent"),
        ("group", "autoqb.ui.qbYAxisGroup")
    ):
        assert f'{scope}: "{key}"' in js, f"缺 {scope} 纵轴存储键(三作用域各自独立一份)"
    yk = re.search(r"function qbYAxisStoreKey\(scope\) \{\n(.*?)\n\}", js, re.S)
    assert yk and "QB_YAXIS_STORE_KEYS[scope]" in yk.group(1), "qbYAxisStoreKey 必须按 scope 单点分派"
    yi = re.search(r"function qbInitialYAxis\(scope\) \{\n(.*?)\n\}", js, re.S)
    assert yi, "缺 qbInitialYAxis(纵轴初值读取)"
    yib = yi.group(1)
    assert "localStorage.getItem(qbYAxisStoreKey(scope))" in yib and "QB_YAXIS_MODES.includes(v.mode)" in yib, \
        "初值必须读存储且只认合法模式(坏值回落默认)"
    assert "catch" in yib, "初值读取失败必须吞异常回落默认"
    ps = re.search(r"persistQbYAxis\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert ps and "localStorage.setItem(qbYAxisStoreKey(scope)" in ps.group(1) and "catch" in ps.group(1), \
        "persistQbYAxis 必须写键单点且吞写入异常(与 persistQbWindow 同纪律)"
    for sig in ("qbSetYAxisMode(mode)", "qbSetYAxisManual(v)"):
        blk = re.search(rf"{re.escape(sig)} \{{\n(.*?)\n    \}},", js, re.S)
        assert blk, f"缺 {sig}(纵轴切换入口)"
        bd = blk.group(1)
        assert "this.persistQbYAxis(s);" in bd and "this._qbChartRescale(s);" in bd, \
            f"{sig} 必须落盘 + 立即重排 y 轴(不改数据/不重建图, 重取数等于白拉一发)"
    rs = re.search(r"_qbChartRescale\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert rs and "u.setData([u.data[0], u.data[1], u.data[2]]);" in rs.group(1) \
        and 'u.setScale("x", { min: stR.anchor - stR.span, max: stR.anchor });' in rs.group(1), \
        "_qbChartRescale 必须走 setData 重算 scale + 显式锚视口重申(重跑 range 与 draw 钩子, 不重建" \
        "图 —— 旧 dropPad slice 形随单列恒等退役)"
    # 限速随主轮询变化重排(mounted 注册; 全局 mixin 必须先按 this.drawer 守卫剔除假实例)
    assert "this._qbLimitUnwatch = this.$watch(() => this._qbGlobalLimit()" in js, \
        "缺限速变化重排 watcher(长窗轮询可夹到 600s, 不重排则固定上限迟迟不生效)"
    assert "if (!this.drawer) return;" in js, \
        "mounted 注册必须先按 this.drawer 守卫剔除 BaseTransition 假实例(全局 mixin 会注入它)"

    # 7. 作用域表三挂点各持 yaxis 字段(单一描述源)
    scopes = re.search(r"const _QB_SCOPES = \{\n(.*?)\n\};", js, re.S)
    assert scopes, "缺 _QB_SCOPES 作用域表"
    sb = scopes.group(1)
    for field in ('yaxis: "qbHistYAxis"', 'yaxis: "qbTorrentYAxis"', 'yaxis: "qbGroupYAxis"'):
        assert field in sb, f"_QB_SCOPES 缺 {field}(三挂点各自独立纵轴字段)"

    # 8. state.js 三字段按 scope 取初值 + computed 单点
    for field in (
        'qbHistYAxis: qbInitialYAxis("global")', 'qbTorrentYAxis: qbInitialYAxis("torrent")',
        'qbGroupYAxis: qbInitialYAxis("group")'
    ):
        assert field in state_js, f"state.js 缺 {field}(根选项显式建字段)"
    for comp in ("qbCurYAxis()", "qbYAxisMode()", "qbYAxisManual()"):
        assert comp in js, f"缺纵轴 computed {comp}"
    # 2026-10-16(用户动议): 工具条上限读数 qbYAxisCapText(「上限 …(全局限速 ×1.2)」)随 UI 移除,
    # computed 退役不得回潮(图面自解释, 不再要常驻读数)。
    assert "qbYAxisCapText" not in js, "qbYAxisCapText 已随 2026-10-16 上限字样移除退役, 不得回潮"

    # 9. 模板控件(2026-10-16 版式改: 三挂点统一落图下统计栏 .qb-statctl, 头部不再挂控件)
    # W3(计划 26-10-11-2106): 控件组收进 <aq-qb-ctl>(**唯一实现**), 故旧口径
    # 「三态 × 2 处 = 6」改为「实现里三态各一(3) + drawer.html 零复写 + 唯一挂点接它」——
    # 覆盖强度不降反升(单点强于同源): 谁把按钮抄回 drawer.html, 下面的 == 0 与挂点断言同时判红。
    # 26-10-20-2231(R23-B-17): 纵轴三态改 <aq-seg> —— 模板不再有 3 个按钮, 判据换成
    # 「模板一处接 qbYAxisTabs + 三档合法值与文案在 JS 单点各一份」: 覆盖强度不降(谁把档位
    # 写回模板, 下面的 count == 0 与 qbYAxisTabs 投影断言同时判红), 且「加一档要改几处」从
    # 3 处(清单/文案/模板)降到 2 处(清单/文案, 同域相邻)。
    assert head_tpl.count("qbSetYAxisMode(") == 0, \
        "<aq-qb-ctl> 不应手写纵轴三态按钮(应交 <aq-seg>, 清单单点在 qbYAxisTabs)"
    assert ':items="$root.qbYAxisTabs"' in head_tpl and ':on-pick="$root.qbSetYAxisMode"' in head_tpl, \
        "<aq-qb-ctl> 纵轴三态必须吃 qbYAxisTabs + 回调 qbSetYAxisMode"
    assert re.search(r"qbYAxisTabs\(\) \{\n\s*return QB_YAXIS_MODES\.map\(", js), \
        "qbYAxisTabs 必须投影自 QB_YAXIS_MODES(合法值仍只有一份清单)"
    assert drawer_tpl.count("qbSetYAxisMode(") == 0, \
        "drawer.html 仍手写纵轴按钮(复写回潮: 控件组只有 <aq-qb-ctl> 一份实现)"
    traffic_call = re.search(r'<aq-drawer-head v-if="drawerIsTraffic"[^>]*>(.*?)</aq-drawer-head>', drawer_tpl, re.S)
    assert traffic_call and '<aq-qb-ctl>' not in traffic_call.group(1), \
        "纵轴控件不得落在流量形态头部内(2026-10-16 版式改: 三挂点统一落图下统计栏)"
    assert 'class="qb-tools"' in head_tpl and 'class="qb-seg"' in head_tpl, \
        "<aq-qb-ctl> 缺纵轴控件本体(.qb-tools/.qb-seg)"
    # 9b. **结构**守阵(数类名探不到 wrapper): <aq-qb-ctl> 必须恰两根(.qb-tabs / .qb-tools), 无 wrapper。
    # 三皮肤 CSS 的 `.qb-statctl > .qb-tabs` / `.qb-statctl > .qb-tools` 与
    # `.hist-summary > .qb-statctl` 全是**直接子选择器**(2026-10-16 起统计栏是唯一挂点,
    # 头部侧的 `.drawer-head > .qb-*` 选择器已随挂点退役删除) —— 片段被包一层
    # (任何理由的容器)即全部静默失配(类名 count 不变, 观感错版)。Vue 3 片段不留 wrapper 元素,
    # 唯二会破坏它的就是源模板里自己写一个, 故此处在源文本上钉根数。
    ctl_roots = _tpl_top_level_tags(_tpl_body(head_tpl, "tpl-aq-qb-ctl"))
    assert len(ctl_roots) == 2, (
        f"<aq-qb-ctl> 必须是**多根**片段(恰两根), 实测 {len(ctl_roots)} 根 —— "
        "包 wrapper 会隔开 .qb-statctl > .qb-tabs 这些直接子选择器, "
        "三皮肤下控件错版且无报错(静默失效)"
    )
    assert [t for t, _ in ctl_roots] == ["div", "div"], \
        "<aq-qb-ctl> 两个根必须是 div(.qb-tabs 档位 / .qb-tools 纵轴)"
    ctl_classes = [a.get("class") for _, a in ctl_roots]
    assert ctl_classes == ["qb-tabs", "qb-tools"], \
        f"<aq-qb-ctl> 两根的类必须依序为 qb-tabs/qb-tools(直接子选择器按类名命中), 实测 {ctl_classes}"
    # 头部壳片段同理: 恰一个根 <header class="drawer-head">(两形态共用一处; 再长出第二个 = 复写回潮)
    head_roots = _tpl_top_level_tags(_tpl_body(head_tpl, "tpl-aq-drawer-head"))
    assert len(head_roots) == 1 and head_roots[0][0] == "header" \
        and head_roots[0][1].get("class") == "drawer-head", \
        f"<aq-drawer-head> 必须恰一个根 <header class=\"drawer-head\">(两形态共用的唯一头部壳), 实测 {head_roots}"
    assert "v-if=\"$root.qbYAxisMode === 'manual'\"" in head_tpl \
        and "$root.qbSetYAxisManual($event.target.value)" in head_tpl, \
        "<aq-qb-ctl> 手动模式必须给输入框且 @change 走 qbSetYAxisManual(经 $root 回调根实例)"
    # 2026-10-16(用户动议): 生效上限读数(qb-tools-hint / qbYAxisCapText)已随 UI 移除, 不得回潮。
    assert "qb-tools-hint" not in head_tpl and "$root.qbYAxisCapText" not in head_tpl, \
        "纵轴工具条的上限读数字样已移除(2026-10-16), 不得回潮"
    # 2026-10-09 第 2 轮: 种子「流量」页签同款控件组改落图下统计栏(.qb-statctl; 2026-10-16 起为唯一挂点)
    stat_hdr = drawer_tpl[drawer_tpl.index('class="hist-summary"'):drawer_tpl.index('种子详情形态正文(五页签)')]
    assert 'class="qb-statctl"' in stat_hdr and '<aq-qb-ctl></aq-qb-ctl>' in stat_hdr, \
        "纵轴/档位控件组必须落在图下统计栏 .hist-summary 内(2026-10-09 第 2 轮; 2026-10-16 起为唯一挂点; W3 起经 <aq-qb-ctl>)"

    # 10. CSS 各皮肤成对(纵轴控件 + 图下统计栏控件组版式; flux 收编 S5)
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合"),
        (_ui_css_aggregate("console"), "console css 聚合"),
        (_ui_css_aggregate("prism"), "prism css 聚合"),
        (_ui_css_aggregate("flux"), "flux css 聚合"),
    ):
        for rule in (
            ".qb-tools {",
            ".qb-seg button.active",
            ".qb-yaxis-input",
            ".hist-summary > .qb-statctl {",
        ):
            assert rule in css, f"{name} 缺 {rule}(纵轴控件/图下统计栏控件组三套 UI 必须成对改)"
        # 2026-10-16(用户动议「统计栏未对齐」): 统计栏 .hist-summary 各子项必须**垂直居中**。
        # 判据: flex 默认 align-items:stretch 把纯文本读数(「窗口 N 点」/上下载累计)拉到与
        # 控件组同高、文字贴顶(实测比中线高 3.7px), 而图例(.hs-leg)与控件组(.qb-statctl)
        # 自带 align-items:center 使内容居中 —— 三族文字因此落成三条线, 真浏览器量布局才现形
        # (类名/结构断言全绿)。三皮肤成对钉住, 只改一处即判红。
        assert re.search(r"\.hist-summary\s*\{[^}]*align-items:\s*center", css), \
            f"{name} 的 .hist-summary 缺 align-items:center(统计栏子项错行: 文本贴顶 vs 图例/控件居中)"


def test_frontend_qb_traffic_drawer_page_guard():
    r"""流量图抽屉的页面守卫(2026-10-06 修「qB 全局流量图错误地出现在设置页」)

    抽屉是 app 级 sticky 吸底的停靠面板(.drawer-dock), 而 drawerVisible 原先对流量形态无条件为真
    (口径「任意页可开」) —— 在设置页(整幅配置工作台, 自己的滚动容器铺满)面板会压住页面底部内容,
    看着像设置页自带的一块。四类**守不全就复发**的形态钉住:
    1. 可见性单点 drawerVisible: 两形态一律先挡非主内容页(page !== "groups"); **状态位不随切页翻**
       (面板 DOM 退场、抽屉状态保住 —— 回主内容页连数据/窗口选择一起回来 = 方案A W1 验收项);
    2. 轮询与建图的 active 同源守卫: 三挂点一律含 page 判据 —— 面板不在 DOM 还拉还画 = 对着空气取数
       (同 pitfalls/web-ui/dock-panel「停靠面板隐藏后轮询要随可见性收口」);
    3. 入口可达性: 状态栏按钮与全局快捷键(Ctrl+Backslash)任意页可达 —— openDrawerTraffic 必须先把页
       切回主内容页, 否则「点了没反应」(状态翻了、面板不在 DOM);
    4. 图的生命周期(state.js watch drawerVisible): Vue 的 v-if 拆装会**换掉建图宿主**, uPlot 的
       root/canvas 挂在被拆走的旧 .qb-chart-host 上且不自愈(要等下一拍轮询, 而间隔可能夹到 600s)
       ⇒ 症状「回主内容页后面板里有文字没图」—— 退场销毁图、进场补拉一发(_qbLoad 内含建图);
       种子详情支路(!s)的变体宿主回页重挂归 test_drawer_seed_reentry_variant_remount。
    5. 同目标幂等短路(2026-10-07 修「再按 Ctrl+\ 闪烁」): 抽屉已开着同一形态同一目标时重按入口
       (快捷键/状态栏钮)必须短路返回 —— 全量路径会把收图销毁 + 抽屉重建 + 首拉 loading 各闪一遍
       (pitfalls/web-ui/drawer-switch-flicker「快中间态本身就是闪」)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    drawer_js = read_shared("drawer.js")

    # 1. 可见性单点: 守卫在形态分支之前, 状态位不被改写
    vis = re.search(r"drawerVisible\(\) \{\n(.*?)\n    \},", drawer_js, re.S)
    assert vis, "drawer.js 缺 drawerVisible(面板可见性单点, 移动了就同步本守阵)"
    vb = vis.group(1)
    assert "if (!this.drawer.open) return false;" in vb, "抽屉可见性必须先挡 drawer.open"
    assert 'if (this.page !== "groups") return false;' in vb, \
        "drawerVisible 缺主内容页守卫(设置页会浮着一张不属于它的流量图/种子详情面板)"
    assert 'return this.viewMode === "torrents";' not in vb, \
        "种子详情不得再限种子视图(2026-10-08 计划 26-10-08-1217: 三视图共用面板, 成员行三视图同源)"
    assert re.search(r"^      return true;", vb, re.M), \
        "drawerVisible 末尾必须无条件 return true(过了主内容页守卫即显示; 形态分支已收归页面级)"
    assert "this.drawer.open = false" not in vb, \
        "可见性不得改写抽屉状态位(面板 DOM 退场 ≠ 关闭: 回主内容页状态还要回来)"

    # 2. 三挂点 active 同源守卫(轮询 tick / 建图判据同宽)
    scopes = re.search(r"const _QB_SCOPES = \{\n(.*?)\n\};", js, re.S)
    assert scopes, "qb_traffic_chart.js 缺 _QB_SCOPES 作用域表(三挂点单一描述源)"
    body = "\n" + scopes.group(1)  # 还原段首换行(正则捕获从 `  global: {` 起), 便于按段切分
    for scope in ("global", "group", "torrent"):
        seg = body.split("\n  %s: {" % scope)[1].split("stale:")[0]
        assert 'page === "groups"' in seg, \
            f"{scope} 挂点 active 缺主内容页守卫(面板已退场仍拉 /api/traffic/qb/* 且继续画不可见的图)"

    # 3. 入口可达(状态栏/快捷键任意页可达): 触发即切回主内容页
    op = re.search(r"async openDrawerTraffic\(scope, key\) \{\n(.*?)\n    \},", js, re.S)
    assert op, "qb_traffic_chart.js 缺 openDrawerTraffic(打开流量形态抽屉的单点)"
    ob = op.group(1)
    assert 'if (this.page !== "groups") this.page = "groups";' in ob, \
        "openDrawerTraffic 缺页面归一: 在设置页点状态栏入口/按 Ctrl+Backslash 会「点了没反应」"
    assert ob.index('this.page !== "groups"') < ob.index("this._stopDrawerPoll()"), \
        "页面归一必须在重置抽屉状态之前(切页会引发重排, 先于所有副作用)"

    # 5. 同目标幂等短路: 已开着同一形态同一目标(分组再比 key)时重按入口不重建(否则收图销毁+
    #    抽屉重建+首拉各闪一遍); 短路必须落在 _stopDrawerPoll 等副作用之前才算短路
    assert 'this.drawerIsTraffic' in ob and "this.qbGroupKey === key" in ob, \
        "openDrawerTraffic 缺同目标幂等短路: 再按 Ctrl+\\ 会把收图+重建+首拉各闪一遍(W6 起形态判据走单点)"
    assert ob.index('this.drawerIsTraffic') < ob.index("this._stopDrawerPoll()"), \
        "同目标短路必须在收图/重建副作用之前(落在后面 = 短路失效, 闪烁回归)"

    # 4. watch(drawerVisible): 退场销毁图 / 进场补拉重建(uPlot 宿主随 v-if 拆装被换掉)
    #    种子详情支路(!s)W7 恢复进场补挂($nextTick 等 aside 补进 DOM 再 _dtSync; 见
    #    test_drawer_seed_reentry_variant_remount 全套钉法, 此处只钉挂点存在)
    wt = re.search(r"drawerVisible\(v\) \{\n(.*?)\n    \},", state_js, re.S)
    assert wt, "state.js 缺 watch(drawerVisible)(换宿主后图不自愈 = 回页只剩文字)"
    wb = wt.group(1)
    assert "const s = this.qbCurScope;" in wb and "if (!s) {" in wb and "$nextTick(() => this._dtSync())" in wb, \
        "watcher 缺种子详情支路进场补挂(!s 分支 $nextTick -> _dtSync; W7 随变体层恢复)"
    assert "this._qbChartDestroy(s);" in wb and "this._qbReloadOnEnter(s);" in wb, \
        "drawerVisible watcher 必须退场销毁图 + 进场补拉重画(补拉内含 $nextTick 建图单点)"
    re_b = re.search(r"_qbReloadOnEnter\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert re_b, "qb_traffic_chart.js 缺 _qbReloadOnEnter(面板进场补拉单点)"
    rb = re_b.group(1)
    assert "this._qbLoad(scope);" in rb, "_qbReloadOnEnter 必须走 _qbLoad 单点(内含建图, 不另写请求)"
    assert 'this[def.loading]' in rb, \
        "_qbReloadOnEnter 缺在途不叠加守卫(打开路径已先发一发, 进场 watcher 会把首次请求翻倍)"


# node 单测探针(issue 26-10-16-0954 方案 #2; 2026-10-22 随轮询骨架改写): 加载真实 polling.js +
# qb_traffic_chart.js, 用**真骨架 + 真 _qbLoad** 驱动「在途悬挂」兜底路线 —— api 桩返回永不 settle 的
# promise(悬挂), 断言: 在途未悬挂照旧挡拍 / 悬挂(超阈值)放行且只留一条警告 / 补偿后重新计时故后续
# 照常挡拍 / 图不活跃与页面隐藏照旧跳过 / 停止后句柄摘除。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE)。
_NODE_QB_POLL_STALL_PROBE = r"""
const fs = require("fs");
global.window = {};
global.document = { hidden: false };
eval(fs.readFileSync(process.argv[1], "utf8"));   // polling.js(骨架)
eval(fs.readFileSync(process.argv[2], "utf8"));   // qb_traffic_chart.js
const P = window.AQB_POLL.methods;
const M = window.AQB_QB_TRAFFIC.methods;
const checks = [];
let tick = null;
global.setTimeout = (fn) => { tick = fn; return 1; };   // 捕获下一拍, 不真跑定时器
global.clearTimeout = () => {tick = null;};
const realNow = Date.now; let off = 0;
Date.now = () => realNow() + off;                       // 可控时钟: 免得真睡 30s
const warns = [];
console.warn = (...a) => { warns.push(a.join(" ")); };
const mk = (over) => {
  const t = Object.assign({
    qbTrafficOn: true,
    drawerIsTraffic: true,
    drawer: { open: true, scope: "global" },
    page: "groups",
    qbHistData: { meta: { interval_s: 30, sample_interval_s: 30 } },
    qbHistLoading: false,
    apiCalls: 0,
  }, over || {});
  t.api = () => { t.apiCalls += 1; return new Promise(() => {}); };  // 悬挂: await 永不返回
  t.startPoll = P.startPoll;
  t.stopPoll = P.stopPoll;
  t._qbPollStop = M._qbPollStop;
  t._qbPollMs = M._qbPollMs;
  t._qbLoad = M._qbLoad;
  return t;
};
const run = (t) => { M._qbPollStart.call(t, "global"); tick(); };
// 1. 在途未悬挂(刚置位): 照旧挡拍(骨架记下计时起点后 mutex 挡住)
off = 0;
let t = mk({ qbHistLoading: true });
run(t);
checks.push(["在途未悬挂照旧挡拍", t.apiCalls === 0 && warns.length === 0]);
// 2. 悬挂(起点记下后时钟跳过 60s): 放行 + 一条警告; 补偿后重新计时 => 后续拍照常挡、警告只一条
warns.length = 0;
t = mk({ qbHistLoading: true });
run(t);          // 第一拍只记起点
off = 60000;     // 时钟跳过阈值
tick();
checks.push(["悬挂放行(强制续拉)", t.apiCalls === 1 && warns.length === 1 && t.qbHistLoading === true]);
for (let i = 0; i < 5; i++) tick();
checks.push(["补偿后重新计时: 后续照常挡拍且警告只一条", t.apiCalls === 1 && warns.length === 1]);
// 3. 图不活跃(切走页面) / 页面隐藏: 照旧跳过(兜底不越界)
t = mk({ qbHistLoading: true, page: "settings" });
run(t);
checks.push(["图不活跃跳过", t.apiCalls === 0]);
global.document.hidden = true;
t = mk({ qbHistLoading: true });
run(t);
checks.push(["页面隐藏跳过", t.apiCalls === 0]);
global.document.hidden = false;
// 4. 停止收口: _qbPollStop 后句柄从表里摘掉(不再有拍)
t = mk({ qbHistLoading: false });
run(t);
t._qbPollStop("global");
checks.push(["停止后句柄摘除", !t._polls["qb:global"]]);
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_traffic_load_stall_fallback():
    """流量图轮询「在途悬挂」兜底守阵(issue 26-10-16-0954-bug-webui-chart-fetch-no-timeout 方案 #2)

    故障链(2026-10-16 复验实测): loading 是单向「请求在途」标志 —— `_qbLoad` 入口无条件置 true,
    唯一复位路径是它的 finally; 请求悬挂时 finally 不执行 ⇒ 轮询 tick 的守卫(`this[def.loading]`)
    把之后每一拍都挡掉, 图表永久停在旧帧、无提示也不自愈(10-12 修的是同链另一入口: stale 谓词取反)。

    2026-10-22(issue 26-10-20-2231-refactor-fe-polling-family-dup): 兜底随轮询生命周期收进
    polling.js 骨架, 阈值常量上提为 `AQB_POLL_STALL_MS`(抽屉侧自此同口径 —— 此前同一类卡死只修了
    流量图一边)。!T4a(plan 26-11-18-0037)起 GET 轮询骨架为降级态取数路径(E7), 本守阵钉的
    stall/mutex 声明与行为面随之服务于降级态 —— 语义不变。本守阵改钉三层, 任一层被拆即红:
      1. 阈值常量 `AQB_POLL_STALL_MS` 在 polling.js(30000 = 请求级超时 15s 的两倍余量);
      2. 流量侧**声明**齐全: `stall: () => this[_QB_SCOPES[scope].loading]` + `mutex: true`
         (合体式早退 `document.hidden || this[def.loading]` 不得回潮 —— 那正是本 issue 的成因形态);
      3. 抽屉侧必有同口径兜底(`stall` + `onStall`), 否则「同一类卡死只修一边」复发。
    行为面走 node 电池真跑(无 node 静默跳过): 真骨架 + 真 `_qbLoad` + 永不 settle 的 api 桩。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    js_path = os.path.join(shared, "qb_traffic_chart.js")
    store_path = os.path.join(shared, "drawer_store.js")
    poll_path = os.path.join(shared, "polling.js")
    js = open(js_path, encoding="utf-8").read()
    store_js = open(store_path, encoding="utf-8").read()
    poll_js = open(poll_path, encoding="utf-8").read()

    m = re.search(r"^const AQB_POLL_STALL_MS = (\d+);", poll_js, re.M)
    assert m, "polling.js 缺 AQB_POLL_STALL_MS 常量(悬挂兜底阈值, 骨架单点)"
    assert int(m.group(1)) == 30000, \
        "兜底阈值应 = 请求级超时(15s)的两倍余量 30000 —— 改它必须同步本守阵与常量注释里的依据"
    assert "document.hidden || this[def.loading]" not in js, \
        "tick 跳过判据回潮成 loading 合体式 —— loading 卡死即永久挡拍(issue 26-10-16-0954 的成因)"
    assert "stall: () => this[_QB_SCOPES[scope].loading]," in js and "mutex: true," in js, \
        "流量轮询缺在途悬挂兜底声明(stall)或在途互斥(mutex)"
    # 抽屉侧同口径(2026-10-22 补的实质缺陷面): 卡死判据 + 补偿动作都在, 否则面板仍可能永久冻结
    dp = re.search(r"_startDrawerPoll\(\) \{\n(.*?)\n    \},", store_js, re.S)
    assert dp, "drawer_store.js 缺 _startDrawerPoll(结构漂移? 同步本守阵)"
    assert "stall: () => this._drawerPollStuck()," in dp.group(1) and "onStall:" in dp.group(1), \
        "抽屉页签轮询缺悬挂兜底声明 —— 同一类卡死只修了流量图一边(issue 26-10-20-2231 的实质缺陷面)"

    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_STDIN_WRAPPER, poll_path, js_path],
            input=_NODE_QB_POLL_STALL_PROBE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, f"悬挂兜底 node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"悬挂兜底电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# F7/F8/A7 电池(plan 26-11-15-1104): 轮询节奏 = 采样间隔全窗统一(D6) + 冷开首拍立即(D4) +
# 状态行两组值同源(A7)。真骨架(polling.js)+ 真 _qbPollMs/_qbLoad/computed 驱动; setTimeout
# 桩捕获 (fn, delay) 二元组 —— F8 的断言面就是重排 delay 本身(0 / 短重试 / 节律周期三态)。
_NODE_QB_POLL_RHYTHM_PROBE = r"""
const fs = require("fs");
global.window = {};
global.document = { hidden: false };
eval(fs.readFileSync(process.argv[1], "utf8"));   // polling.js(骨架)
eval(fs.readFileSync(process.argv[2], "utf8"));   // qb_traffic_chart.js
const P = window.AQB_POLL.methods;
const M = window.AQB_QB_TRAFFIC.methods;
const C = window.AQB_QB_TRAFFIC.computed;
const checks = [];
const ok = (n, c) => checks.push([n, !!c]);

// —— F7: _qbPollMs 读 meta.sample_interval_s(生效采样间隔)全窗统一, [1.5s,600s] 防御夹取 ——
const pollMs = (meta) => M._qbPollMs.call({ qbHistData: { meta } }, "global");
ok("F7 si=1.5 -> 1500(生产档, D6 全窗统一)", pollMs({ sample_interval_s: 1.5 }) === 1500);
ok("F7 si=30 -> 30000", pollMs({ sample_interval_s: 30 }) === 30000);
ok("F7 si=600 -> 600000(上界恰触)", pollMs({ sample_interval_s: 600 }) === 600000);
ok("F7 si=900 -> 600000(防御夹取; 旧口径吃桶宽的形态不再存在)", pollMs({ sample_interval_s: 900 }) === 600000);
ok("F7 si=0.8 -> 1500(下界夹取)", pollMs({ sample_interval_s: 0.8 }) === 1500);
ok("F7 只带 interval_s=3600(旧形状缺键) -> 30000 兜底, 不吃桶宽(旧口径会被夹成 600000)",
  pollMs({ interval_s: 3600 }) === 30000);
ok("F7 meta 缺失 -> 30000 兜底", pollMs(undefined) === 30000);
ok("F7 si 非法(0/负) -> 30000 兜底", pollMs({ sample_interval_s: 0 }) === 30000
  && pollMs({ sample_interval_s: -2 }) === 30000);

// —— A7: 状态行两组值(采样行 / beat·周期派生量)同源一致 —— 都从 sample_interval_s 来 ——
// 26-11-18-0037 阶段 3: schema=2 样本分组契约下 interval_s = 组距标称 k x si(桶面退役),
// 二值形态出「组距」; agg 段窗(D4 零改动)无 schema 键, 二值仍「桶宽」。
const mkVm = (meta) => {
  const vm = Object.assign({}, M, C, {
    qbCurScope: "global", qbHistData: { meta }, fxNow: 0, fxBeatAt: 0,
  });
  // Vue 运行时 computed 经 this.X 解析为**求值结果**; 裸合并 vm 上是函数本体 —— 把被其它
  // computed 引用的展示值钉成求值结果(qbFxSampleText 相等/缺失回落分支读 qbFxPeriodS)。
  Object.defineProperty(vm, "qbFxPeriodS", { get: () => C.qbFxPeriodS.call(vm), configurable: true });
  return vm;
};
{
  const vm = mkVm({ interval_s: 174, sample_interval_s: 1.5, schema: 2, stride: 116 });
  ok("A7 两值形态(schema=2 样本分组契约): 周期实算 1.5(与采样行同源) + 采样行「1.5 s · 组距 174.0 s」"
    + "(interval_s = 组距标称 116 x si, 桶面退役)+ beat 600ms(旧口径吃组距 174 -> beat 恒 1000 即回潮)",
    C.qbFxPeriodS.call(vm) === "1.5"
    && C.qbFxSampleText.call(vm) === "1.5 s · 组距 174.0 s"
    && C.qbFxBeatMs.call(vm) === 600);
}
{
  const vm = mkVm({ interval_s: 3600, sample_interval_s: 1.5 });
  ok("A7 两值形态(agg 段窗, D4 零改动): 无 schema 键二值仍「1.5 s · 桶宽 3600.0 s」",
    C.qbFxSampleText.call(vm) === "1.5 s · 桶宽 3600.0 s");
}
{
  const vm = mkVm({ interval_s: 30, sample_interval_s: 30 });
  ok("A7 相等形态: 采样行回落单值与周期实算逐字一致(「30.0 s」)",
    C.qbFxSampleText.call(vm) === "30.0 s" && C.qbFxPeriodS.call(vm) === "30.0");
}

// —— F8: startPoll immediate 首拍立即 + 首拍未落地短重试不落 fallback + mutex 不双发 ——
{
  const timers = [];
  let seq = 0;
  global.setTimeout = (fn, ms) => { timers.push({ fn, ms, id: ++seq }); return seq; };
  global.clearTimeout = () => {};
  const mk = (over) => {
    const t = Object.assign({
      qbTrafficOn: true, drawerIsTraffic: true, drawer: { open: true, scope: "global" },
      page: "groups", qbHistData: { meta: {} },   // 冷开: meta 未落袋 -> ms() 回 30000 fallback
      qbHistLoading: false, apiCalls: 0,
    }, over || {});
    t.api = () => { t.apiCalls += 1; return new Promise(() => {}); };  // 悬挂桩
    t.startPoll = P.startPoll;
    t.stopPoll = P.stopPoll;
    t._qbPollStop = M._qbPollStop;
    t._qbPollMs = M._qbPollMs;
    t._qbLoad = M._qbLoad;   // 真 _qbLoad(同步置 loading -> api 悬挂, 与生产时序同构)
    return t;
  };
  const opts = (t) => ({ immediate: true, ms: () => t._qbPollMs("global"),
    fn: () => t._qbLoad("global"), guard: () => true, stall: () => t.qbHistLoading, mutex: true });

  // a. immediate 首拍立即(delay 0); 非 immediate 首臂照旧 = period(主轮/抽屉调用面零变化)
  const t1 = mk();
  P.startPoll.call(t1, "qb:global", opts(t1));
  ok("F8 immediate 首拍立即(首臂 delay=0, 非 30000 fallback 干等)", timers[0].ms === 0
    && t1.apiCalls === 0);   // 尚未 fire, 只验排程形态
  timers.length = 0;
  P.stopPoll.call(t1, "qb:global");
  const t1b = mk();
  P.startPoll.call(t1b, "qb:global", Object.assign({}, opts(t1b), { immediate: false }));
  ok("F8 非 immediate 首臂 = period(30000 兜底; 旧语义不回归)", timers[0].ms === 30000);
  timers.length = 0;
  P.stopPoll.call(t1b, "qb:global");

  // b. 冷开时序: 直拉在途(loading true) -> 首拍被 mutex 挡掉不双发 + 短重试(1500)不落 30s
  const t2 = mk();
  t2.qbHistLoading = true;   // 开门直拉已发出(_qbLoad 同步置位)
  P.startPoll.call(t2, "qb:global", opts(t2));
  timers[0].fn();            // 首拍: loading true -> mutex 跳过
  ok("F8 直拉在途: 首拍被 mutex 挡掉不双发(apiCalls 0), 短重试重排 1500(不落 30000 干等)",
    t2.apiCalls === 0 && timers[1].ms === 1500);
  // c. 直拉落定(loading false) -> 重试拍真实拉数, 首拍记账清位 -> 重排回归节律周期
  t2.qbHistLoading = false;
  timers[1].fn();            // 重试拍: loading false -> 真实拉数(api 悬挂 -> loading 又 true)
  ok("F8 直拉落定后重试拍真实拉数(apiCalls 1), 首拍落地后重排回归节律周期(30000 兜底)",
    t2.apiCalls === 1 && timers[2].ms === 30000);
  // d. 首拍落地后 mutex 跳拍重排恒节律周期(短重试只在首拍未落地窗口)
  timers[2].fn();            // 下一拍: loading true -> mutex 跳过
  ok("F8 首拍落地后 mutex 跳拍重排 = 节律周期(30000)", timers[3].ms === 30000);
  P.stopPoll.call(t2, "qb:global");

  // e. 页面隐藏首拍: 跳过拉数但重排仍短间隔(回页后下一拍即续, 不落 30s)
  const t3 = mk();
  global.document.hidden = true;
  P.startPoll.call(t3, "qb:global", opts(t3));
  timers[0].fn();
  ok("F8 隐藏期首拍: 跳过拉数(apiCalls 0), 重排短间隔 1500(回页即续)",
    t3.apiCalls === 0 && timers[1].ms === 1500);
  global.document.hidden = false;
  P.stopPoll.call(t3, "qb:global");
  timers.length = 0;
}
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_poll_rhythm_and_immediate_first_beat():
    """F7/F8/A7 电池(plan 26-11-15-1104): 轮询节奏 = 采样间隔全窗统一 + 冷开首拍立即 + 状态行同源

    !T4a(plan 26-11-18-0037 阶段 3 子波 2)起本电池钉的 GET 轮询骨架(_qbPollStart/_qbPollMs)
    是**降级态取数路径**(E7: SSE 主路径 _qbStreamStart 接管事件驱动判定帧, 票据满额/连续
    重连失败才回退轮询) —— 骨架语义与旧「打开期间按 si 续拉」完全一致, 本电池逐拍面不变。
    - F7/D6: _qbPollMs 读 meta.sample_interval_s(生效采样间隔)全窗统一, [1.5s,600s] 防御夹取;
      只带 interval_s 的旧形状(桶宽)不吃 —— 缺键回 30s 兜底(G-F「轮询=桶宽节律错配」的回潮钉)。
    - A7: 状态行两组值同源 —— 周期实算(qbFxPeriodS)/beat(qbFxBeatMs)与采样行(qbFxSampleText)
      都从 sample_interval_s 来; 两值形态(si=1.5/iv=174, schema=2)下 beat=600(旧口径吃组距
      174 -> beat 恒 1000 即回潮; agg 段窗无 schema 键二值仍「桶宽」, D4 零改动), 相等形态
      回落单值逐字一致。
    - F8/D4: startPoll immediate 首拍立即(delay 0); 非 immediate 调用面零变化; 冷开直拉在途
      首拍被 mutex 挡掉不双发 + 短重试(AQB_POLL_FIRST_RETRY_MS=1500)不落 30s fallback; 直拉
      落定后首拍真实执行、记账清位回归节律周期; 隐藏期首拍跳过拉数但重排仍短间隔(回页即续)。
    行为面走 node 电池真跑(真骨架 + 真 _qbPollMs/_qbLoad/computed, 无 node 静默跳过)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    poll_path = os.path.join(shared, "polling.js")
    js_path = os.path.join(shared, "qb_traffic_chart.js")
    poll_js = open(poll_path, encoding="utf-8").read()
    js = open(js_path, encoding="utf-8").read()

    # 静态钉: 短重试常量与首拍记账在骨架; 流量侧声明 immediate
    m = re.search(r"^const AQB_POLL_FIRST_RETRY_MS = (\d+);", poll_js, re.M)
    assert m, "polling.js 缺 AQB_POLL_FIRST_RETRY_MS 常量(F8 首拍未落地窗口的短重试单点)"
    assert int(m.group(1)) == 1500, \
        "短重试应 = 采样间隔配置下限 1500(直拉落定后下一拍即回归节律, 落定前只是空转计时)"
    assert "st.first ? Math.min(st.period, AQB_POLL_FIRST_RETRY_MS) : st.period" in poll_js, \
        "骨架重排必须带首拍记账(first 未清位按短重试, 清位后节律周期 —— 删记账即回 30s 干等)"
    assert "immediate: true," in js, \
        "流量轮询缺 immediate 首拍立即声明(F8/D4)"

    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_STDIN_WRAPPER, poll_path, js_path],
            input=_NODE_QB_POLL_RHYTHM_PROBE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, f"节奏/首拍 node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"节奏/首拍电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# R5#192: x 轴刻度四族 + 孤点索引三态(同文件其余纯函数均有 node 电池, 唯这两处一直零执行)。
# _qbTickLabel 是 methods 上的方法(消费 this[_QB_SCOPES[scope].window]) —— 经导出面真跑;
# _QB_WINDOW_NAMES/_QB_SCOPES 是模块级 const 不随 sloppy eval 外泄, 用 new Function 取出(同
# _NODE_QB_SCOPE_STALE_PROBE 口径); _qbIsolatedIdxs 是顶层 function 声明, eval 后可直接取用。
_NODE_QB_TICK_ISOLATED_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src);
const M = window.AQB_QB_TRAFFIC.methods;
const CST = new Function(src + "\nreturn { WN: QB_WINDOW_NAMES, SCOPES: _QB_SCOPES };")();
const checks = [];
const ok = (n, c) => checks.push([n, !!c]);
const p2 = (n) => String(n).padStart(2, "0");
const ts = 1767225600;  // 任意固定时刻; 期望值按同一 Date 本地时区现算, 与机器时区无关
const d = new Date(ts * 1000);
// 四族期望(与 _qbTickLabel 的分支一一对应; 错档 = 族与 QB_WINDOW_NAMES 对应写错, 这里逐档钉死)
const SEC = `${p2(d.getHours())}:${p2(d.getMinutes())}:${p2(d.getSeconds())}`;
const TIME = `${p2(d.getHours())}:${p2(d.getMinutes())}`;
const DATE = `${p2(d.getMonth() + 1)}-${p2(d.getDate())}`;
const MONTH = `${d.getFullYear()}-${p2(d.getMonth() + 1)}`;
const FAM = {
  "1m": SEC, "5m": SEC,
  "30m": TIME, "3h": TIME, "6h": TIME, "12h": TIME, "24h": TIME,
  "3d": DATE, "7d": DATE, "30d": DATE,
  "6mo": MONTH, "1y": MONTH, "all": MONTH,
};
ok("QB_WINDOW_NAMES 恰 13 档", CST.WN.length === 13 && CST.WN.every((w) => FAM[w] !== undefined));

const vm = { qbHistWindow: "24h", qbTorrentWindow: "24h", qbGroupWindow: "24h" };
for (const w of CST.WN) {
  vm.qbHistWindow = w;
  ok(`刻度 ${w} -> ${FAM[w]}`, M._qbTickLabel.call(vm, ts, "global") === FAM[w]);
}
// 三挂点窗口互不串: torrent 挂点读自己的窗口字段(换 global 的档不影响)
vm.qbHistWindow = "24h";
vm.qbTorrentWindow = "3d";
ok("torrent 挂点读 qbTorrentWindow(作用域窗口不串)", M._qbTickLabel.call(vm, ts, "torrent") === DATE);

// _qbIsolatedIdxs 三态(u.data = [xs, up, dl]; 断言走 up 列)
const iso = (up) => _qbIsolatedIdxs({ data: [up.map((_, i) => i), up, up] }, 1);
ok("孤点(两侧皆 null): 收点标", JSON.stringify(iso([null, 5, null, null, 7, 7, null])) === "[1]");
ok("链中/链端(任一侧非 null): 不收", JSON.stringify(iso([null, 5, 6, 7, null])) === "[]");
ok("贴边孤点(一侧出界视作 null): 收", JSON.stringify(iso([5, null, 7])) === "[0,2]");
ok("单元素系列: 收(零长线段不可见, 靠点标可见)", JSON.stringify(iso([9])) === "[0]");
ok("空系列: 空", JSON.stringify(iso([])) === "[]");
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_tick_label_and_isolated_idxs():
    """R5#192: _qbTickLabel 四族 13 档逐档 + _qbIsolatedIdxs 三态 node 电池(无 node 静默跳过)"""
    shared = os.path.join(STATIC_ROOT, "shared")
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _NODE_STDIN_WRAPPER, os.path.join(shared, "qb_traffic_chart.js")],
        input=_NODE_QB_TICK_ISOLATED_PROBE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"刻度/孤点 node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], \
        f"刻度/孤点电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"
