"""WebUI 迁移悬停浮窗守阵(plan 26-11-07-2344 S3): 锚扫描接线 + assembleRelPop 组装纯函数

## 测试计划
- test_webui_relocate_pop_wiring: 浮窗接线守阵(test_webui_static_dom_page_hr 的 *_wiring 同款
  锚扫描) —— popovers.html aqb:relocate-pop:begin/end 锚成对且段内 teleport body / v-show
  relPop.open / rp-head(r-dot+verdict+phase) / rp-sep / rp-paths(rp-pl+rp-pv, 目标位置挂
  rp-em) / rp-kv / rp-reason 结构齐全; xtpl-cells.html 组行/种子行两分支都挂
  relPopEnter/relPopLeave; relocate_pop.js 调度参数 120/160 + assembleRelPop 单点在场且零请求
  (无 fetch//api); app.js 末尾混入 AQB_RELOCATE_POP; 四皮肤 index.html 清单均引入
  relocate_pop.js 且排在 app.js 之前(文件序不变量); row_lang.css .relpop 段不带 .rl-scope
  前缀(teleport 到 body)且宽度/圆点/固定色/全出血分隔条四拍板值在场。
- test_relocate_pop_assemble_node: node 探针真跑 assembleRelPop(照 test_p1_pair_state_mapping_node
  的 vm harness, format.js + decorate.js + relocate_pop.js 同 context 组装实例) —— 组 pair:
  paths 两行[当前位置/目标位置] + kv 序(成员 -> 来源 -> 更新, 组行无别名行); 组 mixed: 多目标
  行全标「目标位置」且空 dst 丢弃; 种子 failed: reason 前缀「原因: 」+ 别名行; 别名 0 显「—」;
  缺 updated_at 显「—」; 调度面: done / 无标注行 relPopEnter 不调度(relocateView null 短路),
  moving 行调 120ms、leave 调 160ms 宽限。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess

from webui_helpers import STATIC_ROOT, _UI_ALL, _ui_manifest

_SHARED = os.path.join(STATIC_ROOT, "shared")


def _read(*parts: str) -> str:
    with open(os.path.join(_SHARED, *parts), encoding="utf-8") as fh:
        return fh.read()


def test_webui_relocate_pop_wiring():
    """迁移悬停浮窗接线守阵(plan 26-11-07-2344 S3/S4): 漏一处 = 静默失效的故障形态机械钉住"""
    # 1. 模板锚: begin/end 恰好成对各一, 段内 teleport 到 body 级(overflow/特异性纠缠的 HR 教训)
    tpl = _read("tpl", "popovers.html")
    begins = re.findall(r"<!-- aqb:relocate-pop:begin", tpl)
    ends = re.findall(r"<!-- aqb:relocate-pop:end", tpl)
    assert len(begins) == 1 and len(ends) == 1, \
        f"aqb:relocate-pop 扫描锚必须 begin/end 恰好成对各一(实得 begin={len(begins)} / end={len(ends)})" \
        " —— 浮窗段被移走或锚被删? 同步本守阵"
    frag = re.search(r"<!-- aqb:relocate-pop:begin.*?-->(.*?)<!-- aqb:relocate-pop:end.*?-->", tpl, re.S).group(1)
    assert '<teleport to="body">' in frag, "浮窗必须 teleport 到 body 级(脱离列表容器)"
    for needle, what in (
        ('v-show="relPop.open"', "显隐挂 relPop.open(单例状态)"),
        ("relPopKeepOpen", "移入浮窗不关(可悬停选中复制)"),
        ("relPopLeave", "移出浮窗走宽限隐藏"),
        ('class="rp-arrow"', "指向箭头(上下翻两态)"),
        ('class="rp-head"', "verdict 头"),
        ('class="rp-dot"', "状态色圆点(D12 圆点形状随皮肤)"),
        ('class="rp-verdict"', "状态词"),
        ('class="rp-phase"', "相位 mono 小字(D14: 相位进状态词后方)"),
        ('class="rp-sep"', "3px 状态色全出血分隔条(D10)"),
        ('class="rp-paths"', "路径块"),
        ('class="rp-pl"', "路径标签列(D15 固定色)"),
        ('class="rp-pv"', "路径值列"),
        ("'rp-em'", "目标位置状态色强调(D13)"),
        ("'目标位置'", "术语「目标位置」字面量(D13; 当前位置经 kv/paths 载荷下发)"),
        ('class="rp-kv"', "kv 行"),
        ('class="rp-k"', "kv 键列"),
        ('class="rp-v"', "kv 值列"),
        ('class="rp-reason"', "失败原因行"),
    ):
        assert needle in frag, f"浮窗模板缺 {what}(应有 `{needle}`)"

    # 2. 触发面: 组行/种子行两个 save_path 分支都挂 relPopEnter/relPopLeave
    cells = _read("tpl", "xtpl-cells.html")
    assert cells.count('relPopEnter($event, g)') == 1 and cells.count('relPopEnter($event, m)') == 1, \
        "组行与种子行 save_path 单元格都要挂 relPopEnter(浮窗触发面 = 两分支)"
    assert cells.count('relPopLeave') >= 2, "两个分支都要挂 relPopLeave"

    # 3. 调度与组装单点: 参数逐条对齐 hr.js hrPop*(120/160), 数据组装全行载荷零请求
    pop_js = _read("relocate_pop.js")
    assert "window.AQB_RELOCATE_POP" in pop_js, "relocate_pop.js 必须挂 window.AQB_RELOCATE_POP"
    assert ", 120);" in pop_js, "enter 延时必须 120ms(与 hrPop 同参, plan §07 风险表: 守阵钉数值)"
    assert ", 160);" in pop_js, "leave 宽限必须 160ms(与 hrPop 同参)"
    assert "assembleRelPop(row)" in pop_js, "数据组装单点 assembleRelPop 必须在场"
    assert "relocateView(row)" in pop_js, "触发判据必须走 relocateView 单点(done/cancelled 不弹)"
    # 零请求只认代码态(剥块/行注释再查 —— 头注纪律文字里的 /api/relocate_chain 不算使用)
    pop_code = re.sub(r"/\*.*?\*/", "", pop_js, flags=re.S)
    pop_code = re.sub(r"//[^\n]*", "", pop_code)
    assert "fetch(" not in pop_code and "/api/" not in pop_code, \
        "浮窗数据全行载荷零请求(plan 不变量 2): 不得出现 fetch//api"

    # 4. app.js 混入 + 四皮肤 script 清单引入且排在 app.js 之前(文件序不变量, relocate_pop.js 头注)
    app_js = _read("app.js")
    assert "app.mixin(window.AQB_RELOCATE_POP);" in app_js, "app.js 必须混入 AQB_RELOCATE_POP"
    for ui in _UI_ALL:
        scripts = _ui_manifest(ui)["scripts"]
        assert "/shared/relocate_pop.js" in scripts, f"{ui}/index.html 清单缺 relocate_pop.js —— 浮窗静默失效"
        assert scripts.index("/shared/relocate_pop.js") < scripts.index("/shared/app.js"), \
            f"{ui}: relocate_pop.js 必须排在 app.js 之前(app.js 末尾要读 window.AQB_RELOCATE_POP)"

    # 5. 样式段: teleport 到 body 不在 .rl-scope 内 -> .relpop 规则不带前缀(与 .hr-pop 同口径);
    #    拍板值钉住: 宽度 max-content 上限 min(94%,680px)(D11) / 圆点圆角 calc(radius-sm/2)(D12) /
    #    当前位置固定色 --path-src(D15) / 全出血分隔条(D10) / tone 色浮窗域内单给一份
    css = _read("row_lang.css")
    assert ".relpop {" in css, "row_lang.css 缺 .relpop 段(浮窗裸奔)"
    assert ".rl-scope .relpop" not in css and ".rl-scope .rp-" not in css, \
        "teleport 到 body 级: .relpop/.rp-* 选择器不得带 .rl-scope 前缀(否则永不命中)"
    assert "width: max-content" in css and "max-width: min(94%, 680px)" in css, "D11 宽度拍板值"
    assert "calc(var(--radius-sm, 4px) / 2)" in css, "D12 圆点形状单点自适应四皮肤"
    assert css.count("var(--path-src") >= 2, "D15: 当前位置标签+值都要 --path-src 固定色"
    assert ".rp-sep { height: 3px; margin: 6px -12px 8px;" in css, "D10 分隔条 3px 负边距全出血"
    assert ".rp-pv.rp-em { color: currentColor; }" in css, "D13 目标位置 = 状态色强调(currentColor)"
    for tone in ("moving", "pending", "failed", "mixed"):
        assert f".relpop .rel-tone-{tone}" in css, \
            f"浮窗域缺 .rel-tone-{tone} 色义 —— teleport 后行内 .rl-scope 段不命中, currentColor 全靠它"
    assert "T3b" not in css, "T3b 临时兜底段已被 S3/S4 正式样式取代, 注释残留应清理"


_NODE_POP_PROBE = r"""
const fs=require('fs'),vm=require('vm'),path=require('path');
const shared=process.argv[1];
const code=(f)=>fs.readFileSync(path.join(shared,f),'utf8');
const timers=[];  // [ms] 按调度序记录(setTimeout 桩; relPopShowT/relPopHideT 是模块级, 不进响应式)
const sandbox={console, Date,
  window:{addEventListener(){}, AQB_OVERLAY_FIT:{EDGE:8, clampAxis:(v,p,range,m)=>Math.max(m,Math.min(v,range-p-m))}},
  setTimeout:(fn,ms)=>{timers.push(ms);return timers.length;},
  clearTimeout:()=>{}};
vm.createContext(sandbox);
for(const f of ['format.js','decorate.js','relocate_pop.js']) vm.runInContext(code(f),sandbox);
const M=Object.assign({nowSec:1000000},
  sandbox.window.AQB_FORMAT.methods,sandbox.window.AQB_DECORATE.methods,sandbox.window.AQB_RELOCATE_POP.methods);
const assemble=(row)=>M.assembleRelPop.call(M,row);
const grpPair=assemble({members:[{relocate:null}],
  relocate:{state:'moving',src:'R:/src',dst:['R:/dst'],phase:'moving',pending:3,total:12,origin:'rule',updated_at:999880}});
const grpMixed=assemble({members:[{relocate:null}],
  relocate:{state:'mixed',src:'R:/src',dst:['R:/a','','R:/b'],pending:1,total:8,updated_at:999880}});
const seedFail=assemble({relocate:{state:'failed',src:'R:/s',dst:'R:/d',phase:'moving',
  reason:'目标卷剩余空间不足',alias_count:2,origin:'web',updated_at:999880}});
const seedAlias0=assemble({relocate:{state:'moving',src:'R:/s',dst:'R:/d',alias_count:0,updated_at:999880}});
const seedNoUpd=assemble({relocate:{state:'moving',src:'R:/s',dst:'R:/d',alias_count:0,updated_at:0}});
// 调度面: done / 无标注 -> relocateView null 短路不调度; moving -> 120; leave -> 160
M.relPopEnter.call(M,{currentTarget:{}},{relocate:{state:'done',src:'R:/s',dst:'R:/d'}});
M.relPopEnter.call(M,{currentTarget:{}},{relocate:null});
M.relPopEnter.call(M,{currentTarget:{}},{relocate:{state:'moving',src:'R:/s',dst:'R:/d'}});
M.relPopLeave.call(M);
process.stdout.write(JSON.stringify({grpPair,grpMixed,seedFail,seedAlias0,seedNoUpd,timers}));
"""


def test_relocate_pop_assemble_node():
    """assembleRelPop 组装纯函数分支(plan 26-11-07-2344 S3): 全行载荷零请求的数据形态"""
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _NODE_POP_PROBE, _SHARED],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)

    # 组 pair: paths 两行[当前位置/目标位置], kv 序 = 成员 -> 来源 -> 更新(组行无别名行), phase 直传
    gp = out["grpPair"]
    assert gp["verdict"] == "迁移中" and gp["phase"] == "moving" and gp["tone"] == "moving"
    assert gp["paths"] == [["当前位置", "R:/src"], ["目标位置", "R:/dst"]], \
        "组 pair 的路径块 = 当前位置/目标位置两行(D13 术语)"
    assert gp["kv"] == [["成员", "3/12 个成员待收尾"], ["来源", "规则"], ["更新", "2分钟前"]], \
        "kv 序(D14: 来源在更新前), 组行给成员行且无别名行"

    # 组 mixed: 多目标行全标「目标位置」(无当前位置行), 空 dst 丢弃, 无 phase/来源
    gm = out["grpMixed"]
    assert gm["verdict"] == "迁移多任务" and gm["tone"] == "mixed" and gm["phase"] == ""
    assert gm["paths"] == [["目标位置", "R:/a"], ["目标位置", "R:/b"]], \
        "mixed 多目标行必须全标「目标位置」(plan §03 状态矩阵), 空 dst 不给行"
    assert gm["kv"][0] == ["成员", "1/8 个成员待收尾"] and gm["kv"][-1][0] == "更新"
    assert gm["reason"] == "", "非 failed 不给 reason 行"

    # 种子 failed: reason 前缀「原因: 」, 别名行(组行没有的), verdict/tone 走 failed
    sf = out["seedFail"]
    assert sf["verdict"] == "迁移失败" and sf["tone"] == "failed"
    assert sf["paths"] == [["当前位置", "R:/s"], ["目标位置", "R:/d"]]
    assert sf["kv"] == [["别名", "链接位 ×2"], ["来源", "WebUI"], ["更新", "2分钟前"]]
    assert sf["reason"] == "原因: 目标卷剩余空间不足", "failed 的 reason 必须带「原因: 」前缀"

    # 别名 0 -> 显「—」; 缺 updated_at -> 「更新」=「—」
    assert out["seedAlias0"]["kv"][0] == ["别名", "—"], "别名 0 显「—」不隐藏行"
    assert out["seedNoUpd"]["kv"][-1] == ["更新", "—"], "缺 updated_at 不落 NaN/空"

    # 调度面: done/无标注不调度(relocateView null 短路), moving 调 120ms, leave 调 160ms
    assert out["timers"] == [120, 160], \
        f"done/无标注行 relPopEnter 不得调度, moving 应调 120、leave 应调 160(实得 {out['timers']})"
