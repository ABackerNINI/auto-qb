"""`webui_static_scan_js` 支撑: 从 `test_webui_static_skins.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import json

import os

import re

import shutil

import subprocess

from webui_helpers import (
    STATIC_ROOT,
    _UI_ALL,
    _ui_manifest,
    _ui_aggregate,
    _ui_css_files,
    _ui_css_aggregate,
    _ui_css_effective,
    _app_bundle_files,
    _app_bundle_text,
    _tpl_path,
)

from webui_static_scan_common import (
    _EP_MEMBERS_RE,
    _MSG_NEUTRAL_KINDS,
    _MSG_TONE_EXPECT,
    _NODE_SYNTAX_CHECK,
    _PAGE_HOOK_CLASSES,
    _computed_body,
    _section_members,
    _strip_js_comments,
    _toast_kinds_in_use,
    _toast_literal_texts,
)
from webui_static_scan_css import (
    _scan_backdrop_filter,
    _scan_column_cells_paired,
    _scan_css_blocks,
    _scan_css_comments,
    _scan_flux_modal_frost,
    _scan_progress_val_parity,
    _scan_state_color_tokens,
)


def _scan_template_transitions(path, rel, problems):
    """模板 `<transition>` 结构守阵: 必须配对, 且弹窗不得落在 `<transition>` 内

    (2026-09-17 实测: 抽屉外层多了一个未闭合的 `<transition name="pop">`, 于是统计/限速/添加/
    管理/确认框全被浏览器解析成它的子节点 —— `Transition` 只渲染第一个子节点, **所有弹窗被静默
    丢弃**: 点击毫无反应、控制台也不报错。配对计数 + 弹窗嵌套双查, 二者都能抓住这个 bug。)
    """
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    depth = 0
    for i, line in enumerate(lines, 1):
        low = line.lower()
        if "modal-mask" in low and depth > 0:
            problems.append(f"{rel}:{i} 弹窗(.modal-mask)落在 <transition> 内(Transition 只渲染首个子节点 -> 弹窗会被丢弃)")
        depth += low.count("<transition") - low.count("</transition>")
        if depth < 0:
            problems.append(f"{rel}:{i} 多余的 </transition>")
            depth = 0
    if depth != 0:
        problems.append(f"{rel} `<transition>` 未闭合(差 {depth})")


def _scan_js_syntax_with_node(js_files, problems):
    """有 node 时对前端 JS 做**真**语法校验(2026-09-17 起本机已装 node)

    这是启发式扫描(注释孤儿续行等)之上的一道硬闸: 任何语法错误都能以 `文件:行` 形式报出。
    无 node(未装的机器/精简 CI)时**静默跳过**本项 —— 不引入 pytest skip(基线是 0 skipped),
    启发式扫描仍在拦最常见的那类损坏。

    !2026-09-23 由「逐文件起一个 `node --check`」改为**单进程批量**: 20 个文件 = 20 次进程启动,
    实测 7.4s, 其中 95% 是进程启动开销(批量 0.38s)。校验语义已逐样本对齐过 ——
    6 个故障样本(注释孤儿续行 / 未闭括号 / 未闭字符串 / 未闭模板串 / 坏正则 / 未闭圆括号)
    + 1 个正常样本 + 1 个顶层 `return` 边界样本, 判定与 `node --check` **8/8 一致**。
    """
    node = shutil.which("node")
    if not node:
        return
    paths = [path for path, _rel in js_files]
    if not paths:
        return
    proc = subprocess.run([node, "-e", _NODE_SYNTAX_CHECK, *paths], capture_output=True, text=True)
    if proc.returncode == 0:
        return
    rel_of = {os.path.normcase(path): rel for path, rel in js_files}
    for line in (proc.stderr or proc.stdout).strip().splitlines():
        name, _, message = line.partition("\t")
        rel = rel_of.get(os.path.normcase(name.strip()), name.strip())
        problems.append(f"{rel} node 语法校验报错: {message.strip() or 'unknown'}")


def _scan_mixin_wiring(problems):
    """拆分接线守阵(2026-09-20): 片段文件必须「HTML 引用了」且「app.js 注入了」, 且成员不得重名

    拆成多文件后有两类**静默**故障形态(pytest 全绿 / 界面局部废掉):
    1. 文件写了但漏加 <script> 或漏 app.mixin() —— 那一整块功能凭空消失, 控制台不报错
       (Vue 直接把没注册的 mixin 当不存在);
    2. 两个片段里出现同名成员 —— Vue 的 mixin 合并是**后者覆盖前者**, 不报错, 但被覆盖的那个
       实现从此永不执行(表现为"点了没反应"或行为回到旧逻辑)。
    """
    bundle = _app_bundle_files()
    refs = {rel for _p, rel in bundle}
    # boot.js 走 shell 静态 <script src>(它自己负责按清单放行其余脚本, 不在清单内), 两张 shell 的
    # 静态引用同样算"已接线"
    for ui in _UI_ALL:
        shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        refs |= {m.lstrip("/") for m in re.findall(r'<script src="(/shared/[^"]+\.js)"></script>', shell)}
    for dirpath, _dirs, files in os.walk(os.path.join(STATIC_ROOT, "shared")):
        if os.path.basename(dirpath) == "vendor":  # 第三方压缩产物, 不参与本仓库的片段约定
            continue
        for name in sorted(files):
            if not name.endswith(".js"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            if rel in refs:
                continue
            problems.append(f"{rel} 未被 tpl-manifest 清单或 shell 静态 <script> 引用(拆分片段漏挂 -> 整块功能静默消失)")

    app_text = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    # 三种"已接线"形态:
    #   1. mixin    —— window.AQB_* 注入 Vue 实例
    #   2. component —— 注册为组件(如 hub-field 走 app.component)
    #   3. **行为基座** —— 被另一个全局用 `Object.assign({}, window.X, …)` 拷走复用(如 config_hub.js
    #      的 HUB_FIELD_COMPONENT 拷 config_editor.js 的 CE_FIELD_BASE)。它本身不是组件、不注册,
    #      但成员确实在跑 ⇒ 不该报"定义了没注入"。
    #      WARN: 只认 `Object.assign({}, window.X` 这一种形态(本项目唯一的复用写法), 不要放宽成"出现即算"。
    #      (2026-09-25: 经典设置页移除后 ce-field 组件与 tpl-ce-field 模板删除, 基座随之改名去组件化。)
    #   4. **根选项展开** —— `...window.X` 展开进 createApp 根组件选项(W2b: state.js 的 data/computed/watch
    #      与 lifecycle.js 的生命周期)。!这类成员**不许**走 app.mixin: 全局 mixin 会波及 hub-field 等
    #      组件实例(watch/mounted 双份执行)。只认 app.js 里 `...window.X` 展开形态, 不放宽。
    registered = set(re.findall(r"app\.mixin\(window\.(\w+)\)", app_text))
    registered |= set(re.findall(r"app\.component\(\s*\"[^\"]+\"\s*,\s*window\.(\w+)\)", app_text))
    registered |= set(re.findall(r"\.\.\.window\.(\w+)", app_text))
    for path, _rel in bundle:
        registered |= set(re.findall(r"Object\.assign\(\{\},\s*window\.(\w+)", open(path, encoding="utf-8").read()))
    seen = {}
    for path, rel in bundle:
        text = open(path, encoding="utf-8").read()
        for glob in re.findall(r"^window\.(\w+) = \{", text, re.M):
            if glob not in registered:
                problems.append(f"{rel} 定义了 window.{glob} 但 app.js 没有 app.mixin(window.{glob})(片段漏注入)")
        for section in ("methods", "computed"):
            for member in _section_members(text, section):
                if member in seen:
                    problems.append(
                        f"{rel} 的 {section}.{member} 与 {seen[member]} 重名 —— Vue mixin 后者覆盖前者, "
                        "被盖掉的实现永不执行且不报错"
                    )
                seen[member] = rel


def _scan_episode_member_hashes(text, rel, problems):
    """追剧视图"集成员 -> hash"守阵 (2026-09-19 实测事故)

    后端 shows 视图的 `members` 是 **hash 数组**, 而前端 `decoratedShows` 会把它换成**成员对象**
    (带 hit 标记, 供行内渲染/筛选)。菜单与命令只认 hash —— 一旦把对象当 hash 传出去, 拼进
    URL/JSON 时字符串化成 `[object Object]` ⇒ 后端查不到该 hash ⇒ 404「种子不存在」:
    整集/整剧的 开始/暂停/强制汇报/打开目标文件夹/删除 全线哑火(单种子菜单传的是 `member.hash`,
    不受影响 —— "种子右键正常、剧/集右键失败"就是这形状)。故凡是"从集成员取 hash"的地方
    一律走 `memberHashesOf`(两形态都收), 这里只做静态拦截。
    """
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        if not _EP_MEMBERS_RE.search(line):
            continue
        wants_hash = "hashes" in line or ".hash" in line or "for (const h of" in line
        if wants_hash and "memberHashesOf(" not in line:
            problems.append(
                f"{rel}:{i} 集成员取 hash 未走 memberHashesOf"
                "(members 在前端已是对象 -> 传出去会变成 [object Object], 后端 404「种子不存在」)"
            )


def _scan_state_rank(text, rel, problems):
    """状态优先级表守阵: 前端 `STATE_RANK` 必须与后端 `_SHOW_STATE_RANK` 逐项一致(2026-09-19)

    两表是**同一概念**("一组/一集种子该显示成什么状态")的两份实现:
    前端那份决定辅种页组行取哪个成员状态着色(`decoratedGroups.status.primary`),
    后端那份决定追剧页集行的 `e.state`。漂移的后果有两层 ——
    1. 同一批种子在辅种页与追剧页显示成**不同颜色**(用户没法解释, 只会觉得"颜色乱");
    2. 乐观 UI: 前端按自己的表算出"点击后的颜色", 下一轮回执却按后端的表算真值 ⇒ 颜色弹回。
    实测曾漂移两处({downloading,checking} 与 {paused,seeding} 两组取值相反), 人眼不可能发现,
    故机械比对(改一边必须改另一边 —— 这正是本守阵要逼出来的动作)。

    表外兜底秩(2026-10-15, issue 26-10-11-0310): 表里没有的 kind 排最后, 前端
    `STATE_RANK_LAST` ↔ 后端 `_SHOW_STATE_RANK_LAST` 也必须同值 —— 它俩管的是同一件事
    ("未知状态排多后"), 漂移的后果是某页把未知状态排到了已知状态中间。
    """
    from auto_qb.webui.views import _SHOW_STATE_RANK, _SHOW_STATE_RANK_LAST

    m = re.search(r"const STATE_RANK = \{([^}]*)\}", text)
    if not m:
        problems.append(f"{rel} 找不到 `const STATE_RANK = {{...}}`(状态优先级单点表, 见 isPending 一带注释)")
        return
    front = {k: int(v) for k, v in re.findall(r"(\w+)\s*:\s*(\d+)", m.group(1))}
    if front != _SHOW_STATE_RANK:
        problems.append(
            f"{rel} STATE_RANK 与后端 _SHOW_STATE_RANK 不一致"
            f"(前端 {front} / 后端 {_SHOW_STATE_RANK}) —— 同一批种子会在辅种页与追剧页显示成不同颜色"
        )
    m_last = re.search(r"const STATE_RANK_LAST = (\d+)", text)
    if not m_last:
        problems.append(f"{rel} 找不到 `const STATE_RANK_LAST = <n>`(表外 kind 兜底秩单点, 见 decorate.js rankKind)")
    elif int(m_last.group(1)) != _SHOW_STATE_RANK_LAST:
        problems.append(
            f"{rel} STATE_RANK_LAST({m_last.group(1)}) 与后端 _SHOW_STATE_RANK_LAST"
            f"({_SHOW_STATE_RANK_LAST})不一致 —— 未知 kind 的兜底排序两页不同(某页会把未知状态排进已知状态中间)"
        )
    # 顺序语义(2026-09-21): 做种必须排在**暂停之前** —— 组内"部分暂停部分做种中"取**做种色**。
    # 上面的逐项比对只能保证"两页同色", 保证不了"同成哪个色": 2026-09-19 的 BUG-7 把前端表整体
    # 对齐后端时, 顺手把 {paused,seeding} 也翻成 paused ⇒ 辅种页做种中的组整行变灰(用户报
    # "辅种页状态色错误, 以前是对的")。两表一起改才不会重蹈覆辙, 故此处单独钉住顺序。
    if front and front.get("seeding", _SHOW_STATE_RANK_LAST) >= front.get("paused", -1):
        problems.append(
            f"{rel} STATE_RANK 把 paused 排在 seeding 之前或同级(前端 {front}) —— "
            "组/集内\"部分暂停部分做种中\"会取暂停色(灰), 用户口径是取**做种色**(绿); "
            "见 app.js STATE_RANK 注释与 memory-bank/pitfalls.md"
        )


def _scan_keys_serial_re(text, rel, problems):
    """键位归一化正则跨层守阵: 后端 `_KEYS_SERIAL_RE` ↔ 前端 `KB_DEF_RE` 逐字同源(2026-10-15, issue 26-10-11-0310)

    两端各一份是刻意的: 前端录制/保存自定义键位时要能在无往返时判形态(shortcuts.js),
    后端读 webui-keys.json 时要能校验(routes/keys.py)。但两边正则只要差一个字符,
    症状就是**单边静默**: 前端放行的串后端 422(自定义键位存不进去), 或后端放行的串
    前端判非法(录完即被丢弃) —— 不报错, 只是"键位莫名其妙存不上/失效"。
    故逐字比对两侧正则源(JS 字面量剥定界符后与 Python pattern 比); "找不到声明"同样报红
    (判据被改名/搬走后不许空转, 见 pitfall guard-dead-branch)。
    """
    from auto_qb.webui.server.routes.keys import _KEYS_SERIAL_RE

    m = re.search(r"const KB_DEF_RE = /([^/\n]+)/;", text)
    if not m:
        problems.append(f"{rel} 找不到 `const KB_DEF_RE = /.../`(键位归一化正则单点被改名/删除? 见 routes/keys.py::_KEYS_SERIAL_RE)")
        return
    js_src = m.group(1)
    if js_src != _KEYS_SERIAL_RE.pattern:
        problems.append(
            f"{rel} KB_DEF_RE 与后端 _KEYS_SERIAL_RE 不一致"
            f"(JS /{js_src}/ vs Python {_KEYS_SERIAL_RE.pattern!r}) —— "
            "前端放行的键位形态后端可能拒收(422), 或反向(录完即被前端判非法丢弃)"
        )


def _scan_eta_sentinel(problems):
    """ETA 哨兵跨层守阵: 后端 `_ETA_SENTINEL` ↔ 前端全部 `sec/eta >= <数>` 比较点同值(2026-10-15, issue 26-10-11-0310)

    同一事实(qB 协议"无 ETA"哨兵)有多处表示: 后端 views.py `_ETA_SENTINEL` 定聚合口径
    (`_min_valid_eta` 只收 0<eta<哨兵), 前端 format.js `fmtEta` 与模板 `zero:` 类判据定
    显示口径(>= 哨兵即空白/弱化)。任何一边改值另一边没跟, 症状是**静默**的: 后端已不把
    某个 eta 当哨兵而前端还显示空白(或反向) —— 无报错, 只是"该有 ETA 的地方恒空"。
    故按全静态树(.js/.html, 除 vendor)抓比较点逐个比对; **零命中即红** —— "没扫到"必须
    与"没违规"可区分(判据被改名/删光时守阵不许空转, 见 pitfall guard-dead-branch)。
    """
    from auto_qb.webui.views import _ETA_SENTINEL

    hits = []
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith((".js", ".html")):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            if "/vendor/" in f"/{rel}":
                continue
            with open(path, encoding="utf-8") as f:
                for i, line in enumerate(f.read().splitlines(), 1):
                    for m in re.finditer(r"\b(?:sec|eta) >= (\d+)", line):
                        hits.append((rel, i, int(m.group(1))))
    if not hits:
        problems.append("静态树找不到任何 `sec/eta >= <数>` 哨兵比较点(fmtEta / 模板 zero 判据被改名或删除? 见 views._ETA_SENTINEL)")
        return
    for rel, i, v in hits:
        if v != _ETA_SENTINEL:
            problems.append(
                f"{rel}:{i} ETA 哨兵 {v} 与后端 _ETA_SENTINEL({_ETA_SENTINEL})不一致 —— "
                "前端空白/弱化判据与后端聚合口径分家(该显示 ETA 的行恒空, 或哨兵值被当成真 ETA 计时)"
            )


def _scan_pending_settle(text, rel, problems):
    """乐观 UI「撤下」守阵(2026-09-19, 与主线 32f531d / 12657ee 同一族缺陷的第二道锁)

    背景: 「点击 → 行恢复正常」曾实测 3785~5178ms, 根因是 pending 只有 3s 常量兜底一个出口 ——
    systemPatterns 明写的「真值匹配即清」**从未实现过**; 而且这个兜底还只在 refresh() 里被顺带
    求值 ⇒ 撤下 = 3000ms + 等到下一次 /api/state。真机连报三次同一现象, 前三次修复全只动"贴上",
    因为没人量过"撤下"。

    主线修法落地后有两处**极易被改回去/写反**的地方, 本守阵逐条钉住:
      1. `_snapshotTruth(state)` 必须在 `reapplyPending()` **之前** —— 快照要的是服务端原始值;
         挪到之后就变成"行上的补丁值 vs 补丁值", 恒真 ⇒ pending 一瞬间就清(实测 28ms),
         而且冒烟里「落回的是真值」那条**照样 PASS**(补丁值还留在行上, 看着就像真值)。
      2. 判定必须走 `_optimisticSettled`(比真值快照)而不是"拿行上的当前值比" —— 同上。

    !2026-09-21 P3 后1.2.**仍然保留, 且必须保留**: 真值现在主要由 `truth` 事件(SSE)推送,
      但 **SSE 断线期间推的事件会丢**; 这时 `_optimisticSettled` 是唯一的安全网 —— 轮询带回的
      `/api/state` 一旦已经含真值就提前收工, 不用干等到 TRUTH_HOLD_MS(8s)超时回滚。
      没有它, SSE 一断就会出现"命令其实成功了, 8 秒后却回滚"的假失败。
    !已删除的旧机制(勿复活): `_settleFromTruth`(回执带真值就地撤下)、
      `_pullTruthAfterCmd`(回执后拉全量, 1500ms 预算) —— 真值改由事件推送后它们成了死代码。
    """
    i_snap = text.find("this._snapshotTruth(state)")
    i_reap = text.find("this.reapplyPending()")
    if i_snap < 0:
        problems.append(f"{rel} 找不到 `this._snapshotTruth(state)` —— 判「真值是否对齐」没有服务端原始值可比")
    elif i_reap >= 0 and i_snap > i_reap:
        problems.append(
            f"{rel} _snapshotTruth 写在 reapplyPending **之后** —— 快照到的是被补丁改过的行值,"
            "判定恒真 ⇒ pending 立刻清、失败路径留假状态(红线)"
        )
    if "this._optimisticSettled(" not in text:
        problems.append(
            f"{rel} 找不到 _optimisticSettled 的调用点 —— 它是 **SSE 断线时的安全网**: 没有它,"
            "推送丢失就只能干等 TRUTH_HOLD_MS 超时回滚(命令其实成功 ⇒ 假失败)"
        )
    # 反向守阵: 已删的机制不许复活(它们是真值改推送后遗留的死代码)
    for dead in ("_settleFromTruth", "_pullTruthAfterCmd"):
        if dead in text:
            problems.append(f"{rel} 残留已删机制 {dead} —— 真值已改由 truth 事件推送, 它只会拖慢撤下")


def _scan_filter_facets(text, rel, problems):
    """筛选器选项"取数面"守阵(2026-09-21, 用户报「种子页筛选器无数据」)

    选项必须走**单点取数面** `facetRows`(filters.js): 组视图/追剧视图按组(计数=含该值的组数),
    种子页按种子(计数=含该值的种子数)。四个筛选器(标签/分类/站点/路径)原先各自遍历 `groups`
    计算, 而种子页按视图分片**不回 groups**(`VIEW_ARRAYS["torrent"] = ("torrents",)`) ⇒
    四个弹层恒空、只剩"暂无数据"(H&R 是固定两档, 表现为 0/0 —— 更隐蔽)。
    这类"跨视图的常驻消费者去依赖按视图裁剪的阵列"本项目**已犯三次**:
    状态栏速度(issue 26-09-20-1646) / 追剧页成员索引(BUG-8) / 本次筛选器,
    故机械钉住: 每个选项 computed 必须出现单点调用, 且按组算的旧实现不得复活。
    """
    text = _strip_js_comments(text)  # 注释里出现这些名字不算数(见 _strip_js_comments)
    if not re.search(r"^\s*facetRows\(\)\s*\{", text, re.M):
        problems.append(f"{rel} 找不到 facetRows() —— 筛选器选项的取数面单点(见 filters.js 注释)")
    for name in ("tagOptions", "categoryOptions", "siteOptions", "pathOptions"):
        body = _computed_body(text, name)
        if body is None:
            problems.append(f"{rel} 找不到 computed.{name}(改名前请同步本守阵)")
        elif "_facetOptions(" not in body:
            problems.append(
                f"{rel} computed.{name} 没走 _facetOptions 单点 —— 各自遍历集合会在种子页"
                "(按视图分片不回 groups)算出空选项, 弹层只剩\"暂无数据\""
            )
    for name in ("hrOptions", "hrSrcOptions"):
        body = _computed_body(text, name)
        if body is not None and "facetRows" not in body:
            problems.append(f"{rel} computed.{name} 没走 facetRows 单点 —— 种子页不回 groups ⇒ H&R 档位恒 0/0")
    if "_memberValueOptions" in text:
        problems.append(f"{rel} 残留 _memberValueOptions —— 选项一律走 facetRows/_facetOptions 单点"
                        "(按组算的第二条口径正是本次故障的成因)")


def _scan_page_class_wiring(problems):
    """挂件类名配对: HTML 的 `<main class="X ...">` 里出现的挂件类名必须在 CSS 里有规则

    现象(2026-09-21, 用户报"输入框缺发光 + 排版竖着"):
    CSS 里 `.hb-page`(前缀化时手滑)定义 `--tone` 等, 而 HTML 上是 `class="ce-page hub-page"` ——
    `.hb-page` 选择器**永远不命中**任何元素 ⇒ `--tone` 从未定义 ⇒ 所有 `var(--tone)` 派生值
    替换时判为无效 ⇒ 描边回退、发光整条消失、等宽字体也不生效(剩下字体 fallback)。
    静悄悄地废掉一整块视觉,**没有运行时报错**, 靠真浏览器量 computedStyle 才看得出来。

    为防止再犯: 每张 index.html 的 `<main class="...">` 里出现的挂件类名, 都必须能在某份
    CSS(shared/* 或同目录的 *.css)里找到对应的选择器规则。
    """
    css_text = ""
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".css"):
                continue
            if "/vendor/" in f"/{dirpath}/{name}":
                continue
            css_text += open(os.path.join(dirpath, name), encoding="utf-8").read() + "\n"
    selectors = set(re.findall(r"^\s*\.([A-Za-z_][\w-]*)\s*[\{,]", css_text, re.M))
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), STATIC_ROOT).replace(os.sep, "/")
            if "/vendor/" in f"/{rel}":
                continue
            text = open(os.path.join(dirpath, name), encoding="utf-8").read()
            for m in re.finditer(r"<\s*main\b[^>]*\bclass=\"([^\"]+)\"", text):
                for cls in m.group(1).split():
                    if cls not in _PAGE_HOOK_CLASSES:
                        continue
                    if cls not in selectors:
                        problems.append(
                            f"{rel} `<main class=\"...{cls}...\">` 在所有 CSS 里都找不到 `{cls}` "
                            f"的选择器规则 —— 该挂件类上的令牌/变量定义永不生效, 派生样式全部失效"
                            f"(参考 2026-09-21 把 .hb-page 错写成 .hub-page 之外的类名, 整页无发光)"
                        )


def _scan_message_surface_parity(problems):
    """消息面材质守阵(2026-11-02, flux): 提示条与站内确认框共用表面与语义档, 但**通知不切角**

    背景(用户报障): 「强制汇报投递」的提示条与刚点过的确认框看起来像两个产品的控件 ——
    提示条是 fork 时带过来的平面方角老配方(方角 + --bg-card + --shadow-2), 弹窗是 flux 的
    glass 语言(对角切角 + 高光渐变面 + 毛玻璃)。统一口径 = **材质同源, 形态各守其位**:
    位置/交互语义不变, 材质与语义档语法收成一份; 形状**不统一** —— 用户二轮口径
    「消息通知不要切角」: 切角只属弹窗级大面浮层, 通知是过路小条。

    钉五件事(每条都是"看着还能跑、观感却分家"或"新增 kind 静默变中性"的静默故障):
    ① `--msg-surface` 在 flux 内**恰一处**声明(提示条/确认框共用的供给面单点) —— 两处各写一份
      渐变表达式就是本次要消灭的漂移;
    ② `.toast` 基线消费 `background: var(--msg-surface` + `border: ... var(--msg-line)`,
      且**不得**带 clip-path(切角只属弹窗; 本轮先统一成切角, 被用户退回并反向钉);
    ③ `.modal` 基线同样消费 `--msg-surface` 与 `--msg-line`(只换其中一边 = 材质又分家);
    ④ 语义档值 = 期望表(ok→green / warn→warn / error→error / busy→accent / timeout→warn):
      值漂移(如 warn 改回 border-strong)会让 warn 档重新与 info 同貌;
    ⑤ **模板与 JS 里出现的每个 toast kind 都必须有对应 `.toast.<kind>` 规则**(info 除外 ——
      中性档就是基线, 不单列)。warn 档此前正是整档缺失: 21 处调用点在四套皮肤下与 info
      完全同貌(既无琥珀描边也无琥珀图标), 肉眼读成"普通提示";
    ⑥ **文字排版 = D6-2「倒计时进度条」骨架**(用户四轮口径): `.toast` 基座顶对齐 + 600 字重,
      `.toast-txt/.toast-s` 两行块级(13/600 + 12/--fg-muted/400), 且 flux/fx-mount.js 的
      toastSync 必须调 `shapeToastText(n)` —— 共享模板只有一条 span, 两段由挂载层拆; JS 缺席
      时全部退回单行而 CSS 守阵看不出来, 故这条要连 JS 一起钉。

    WARN: 只钉 flux —— 另三套皮肤仍是 fork 前的平面方角配方(本轮范围守恒, 未统一它们);
      本条与该范围一并对齐, 将来三皮肤也统一时把 _UI_ALL 换上来即可。
    """
    flux_dir = os.path.join(STATIC_ROOT, "flux")
    surface_rules = []  # 声明(:) --msg-surface 的规则(选择器)
    bodies = {"toast": [], "modal": []}  # 同名基类可能有多条规则(如 .modal 另有动画覆盖), 合并判
    tone = {}  # kind -> --msg-tone 取的令牌名
    modal_tone = {}  # tone 档 -> --msg-line 取的令牌名
    ico = set()  # 声明 --msg-ico(mask 圈内字形)的选择器集合; "*" = 基线档(.toast)
    typo = {}  # 文字区选择器 -> 规则体(.toast-txt / .toast-t / .toast-s)
    for dirpath, _dirs, files in os.walk(flux_dir):
        for name in sorted(files):
            if not name.endswith(".css"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), STATIC_ROOT).replace(os.sep, "/")
            text = re.sub(r"/\*.*?\*/", "", open(os.path.join(dirpath, name), encoding="utf-8").read(), flags=re.S)
            for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
                sel = " ".join(sel.split())
                if re.search(r"--msg-surface\s*:", body):
                    surface_rules.append(sel)
                if sel == ".toast":
                    bodies["toast"].append((rel, body))
                elif sel == ".modal":
                    bodies["modal"].append((rel, body))
                if re.search(r"--msg-ico\s*:", body):
                    for one in [s.strip() for s in sel.split(",")]:
                        if one == ".toast":
                            ico.add("*")
                        elif one.startswith(".toast."):
                            ico.add(one[len(".toast."):])
                for one in [s.strip() for s in sel.split(",")]:
                    if one in (".toast-txt", ".toast-t", ".toast-s", ".toast-wrap"):
                        typo[one] = typo.get(one, "") + body
                    m = re.fullmatch(r"\.toast\.([a-z]+)", one)
                    if m:
                        mt = re.search(r"--msg-tone\s*:\s*var\((--[\w-]+)", body)
                        if mt:
                            tone[m.group(1)] = mt.group(1)
                    m = re.fullmatch(r"\.modal\.tone-([a-z]+)", one)
                    if m:
                        ml = re.search(r"--msg-line\s*:\s*var\((--[\w-]+)", body)
                        if ml:
                            modal_tone[m.group(1)] = ml.group(1)

    if len(surface_rules) != 1:
        problems.append(
            f"flux 的 --msg-surface 声明数 = {len(surface_rules)}({surface_rules})"
            " —— 消息面供给面必须恰一处单点: 提示条/确认框各写一份渐变表达式就会漂移"
            "(用户报障原症状: 两种消息浮层像两个产品的控件)"
        )
    for key, must in (
        ("toast", ("var(--msg-surface", "var(--msg-line)")), ("modal", ("var(--msg-surface", "var(--msg-line)"))
    ):
        if not bodies[key]:
            problems.append(f"flux 缺 `.{key}` 基线规则 —— 消息面统一的前提(表面/语义档)无处落")
            continue
        rel = bodies[key][0][0]
        body = "\n".join(b for _r, b in bodies[key])
        for token in must:
            if token not in body:
                problems.append(f"{rel} `.{key}` 基线缺 {token} —— 提示条与确认框会退回两套材质"
                                "(本次统一前: 平面卡 vs 玻璃面)")
    # 形状反向钉(用户二轮口径 2026-11-02: 「消息通知不要切角」): 切角是 flux 大面浮层(弹窗/限速浮层)
    # 的语言, 通知是过路小条 —— 切角在小面积上读作装饰缺口, 还会啃掉底部倒计时条右端。故提示条
    # **不得**出现 clip-path: 被"顺手统一"回来即红(本轮就先统一成切角、被用户退回)。
    if bodies["toast"]:
        rel = bodies["toast"][0][0]
        for _r, body in bodies["toast"]:
            if "clip-path" in body:
                problems.append(
                    f"{rel} `.toast` 出现 clip-path —— 消息通知不切角(用户口径 2026-11-02):"
                    "切角只属弹窗级大面浮层; 通知是过路小条, 切角会啃掉倒计时条右端"
                )

    for kind, want in _MSG_TONE_EXPECT.items():
        got = tone.get(kind)
        if got is None:
            problems.append(
                f"flux 缺 `.toast.{kind}` 的 --msg-tone 声明 —— 该档会落回中性基线,"
                "与 info 同貌(warn 档 21 处调用点就是这么静默丢档的)"
            )
        elif got != want:
            problems.append(f"flux `.toast.{kind}` 的 --msg-tone = {got}(应为 {want}) —— 语义档漂移")
    for level, want in (("warn", "--warn-line"), ("error", "--error-line")):
        got = modal_tone.get(level)
        if got != want:
            problems.append(
                f"flux 缺 `.modal.tone-{level}` 的 --msg-line = {want}(实际 {got})"
                " —— 弹窗语义档不染描边, 就只有提示条一侧染色, 两处语义语法又分家"
            )

    # 图标族(用户三轮口径 2026-11-02: 「复用 showcase toast 例子的图标样式」= 圈内字形): 基线一张
    # mask + 每档一张。漏一张的后果比"没图标"更糟 —— mask 无效时 background-color 会把 18px 方框
    # 铺成实心色块(旧 sprite 字形又被 color: transparent 藏掉了), 屏幕上就是一块彩色方块。
    if "*" not in ico:
        problems.append(
            "flux 缺提示条图标的基线 --msg-ico(声明在 `.toast` 或 `.toast.info` 上)"
            " —— 圈内字形族无处落; mask 缺失时 background-color 会把图标位铺成实心色块"
        )
    for kind in _MSG_TONE_EXPECT:
        if kind not in ico:
            problems.append(
                f"flux 缺 `.toast.{kind}` 的 --msg-ico —— 该档图标退成实心色块/无字形"
                "(mask 表在 views.css 的 @supports 块内, 新增 kind 要一并补一张)"
            )

    # 文字排版(用户四轮口径 2026-11-02: 「文字内容排版样式也使用 showcase 中 D6-2 倒计时进度条的样式」):
    # 标题行 + 明细行两段块级堆叠、图标顶对齐。回退成单行居中 = 用户选定前的老观感。
    toast_body = "\n".join(b for _r, b in bodies["toast"])
    for token, why in (
        ("align-items: flex-start", "图标顶对齐(同 D6-2 .tst): 回退 center 时多行文本把图标压到垂直中线"),
        ("font-weight: 600", "标题行字重(同 D6-2 .tst-title): 拆不开的单行条也要读作标题行"),
    ):
        if token not in toast_body:
            problems.append(f"flux `.toast` 基线缺 {token} —— {why}")
    for sel, must, why in (
        (".toast-txt", ("min-width: 0", ), "长 err.message 折不了行(会把条撑破/溢出)"),
        (".toast-s", ("font-size: 12px", "var(--fg-muted)", "font-weight: 400"), "明细行字级/色/字重"),
    ):
        body = typo.get(sel)
        if body is None:
            problems.append(f"flux 缺 `{sel}` 规则 —— {why} 无处落(D6-2 的两行排版不成立)")
            continue
        for token in must:
            if token not in body:
                problems.append(f"flux `{sel}` 缺 {token} —— {why} 漂移")
    # 拆段器: 共享模板只有一条 `<span>{{ t.text }}</span>`(四皮肤共用, 不动模板), 两段由
    # flux/fx-mount.js::shapeToastText 在挂载层拆。JS 缺席 = 全部退回单行, CSS 守阵看不出这事。
    mount_js = os.path.join(STATIC_ROOT, "flux", "fx-mount.js")
    js = open(mount_js, encoding="utf-8").read() if os.path.isfile(mount_js) else ""
    if "shapeToastText(n);" not in js:
        problems.append(
            "flux/fx-mount.js 的 toastSync 未调 shapeToastText(n) —— 提示条退回单行,"
            "D6-2 的标题/明细两行排版落不了地(CSS 侧看不出来)"
        )
    elif '"toast-t"' not in js or '"toast-s"' not in js:
        problems.append("shapeToastText 拆出的段名不是 toast-t / toast-s —— 与 views.css 文字区选择器对不上")

    # 位置与队列(用户八轮, 2026-11-02): ① 提示条必须坐在状态栏**之上** —— 状态栏是常驻仪表盘,
    # 压上去等于盖住速率(报障原话「通知挡住了状态栏」); ② 队列重排要真做: toastSync/toastDrop
    # 都得调 flipStack, 缺一处就回到"新条插入/旧条退场时邻居瞬移"(报障的「互相重叠」另一半)。
    wrap_body = typo.get(".toast-wrap")
    if wrap_body is None:
        problems.append("flux 缺 `.toast-wrap` 基线规则 —— 提示条栈的定位无处落")
    elif "var(--statusbar-h" not in wrap_body:
        problems.append("flux `.toast-wrap` 未按状态栏高度抬升(bottom 缺 var(--statusbar-h))"
                        " —— 提示条会压住底部状态栏的速率/连接数(用户八轮报障)")
    if js.count("flipStack();") < 2:
        problems.append(
            "flux/fx-mount.js 的队列重排不完整 —— toastSync(插入/结算)与 toastDrop(退场)"
            " 都要调 flipStack(); 少一处, 邻居条就会瞬移并与入场条同帧叠画"
        )

    # 队列推入不叠画(九轮, 2026-11-02): 光有 FLIP 还不够 —— 新条若沿用原地 rise(只下移 10px),
    # 它会在旧条还没让开时就落在同一块地方(实测 5 帧重叠、最大 49px = 旧条整个高度, 用户报的
    # 「互相重叠」)。新条必须**从下方一整格**起步(自身高度 + 栈间距), 与旧条上移同速。
    css_path = os.path.join(STATIC_ROOT, "flux", "css", "fx-mount.css")
    fxcss = ""
    if os.path.isfile(css_path):
        fxcss = re.sub(r"/\*.*?\*/", "", open(css_path, encoding="utf-8").read(), flags=re.S)
    if "@keyframes fx-toast-queue-in" not in fxcss:
        problems.append("flux/css/fx-mount.css 缺 fx-toast-queue-in 关键帧 —— 队列推入没有"
                        "\"从下方一整格起步\"的形态, 新条会与正在让位的旧条叠画")
    elif "[data-fx-queue]" not in fxcss:
        problems.append("flux/css/fx-mount.css 没有 [data-fx-queue] 规则 —— 队列推入形态无处挂")
    if 'setAttribute("data-fx-queue"' not in js:
        problems.append("flux/fx-mount.js 不给栈内新条打 data-fx-queue —— 首条之外的推入仍走"
                        "原地 rise, 新条与让位中的旧条重叠")

    # 进行中 → 结果 统一两段式(九~十轮, 2026-11-02 "统一收"): 所有 sticky 进行中条必须经
    # `_runningToast` 建(唯一工厂), 结果必须经 `_settleRunningToast` 另起一条 —— 退回"同一条
    # 原位改字"时, 本地回执快得只剩几百毫秒, 用户读作「第一个窗口被第二个顶掉」。
    # 三条判据, 都是"看着还能跑、但用户看到的是另一回事"的静默故障:
    shared_dir = os.path.join(STATIC_ROOT, "shared")
    cmds_path = os.path.join(shared_dir, "commands.js")
    cmds = open(cmds_path, encoding="utf-8").read() if os.path.isfile(cmds_path) else ""
    offenders, banned_hits = [], []
    for name in sorted(os.listdir(shared_dir)) if os.path.isdir(shared_dir) else []:
        if not name.endswith(".js"):
            continue
        text = open(os.path.join(shared_dir, name), encoding="utf-8").read()
        for lineno, line in enumerate(text.splitlines(), 1):
            # ① sticky 条只能由 _runningToast 建(手搓 { sticky: true } = 绕开最短展示与归档口径)
            if "{ sticky: true }" in line and "_runningToast" not in line:
                offenders.append(f"shared/{name}:{lineno}")
        # ② 归档条文案必须**归档后仍成立**: 它会留在队列里与结果条并存, 不能自称"进行中/等待"。
        # 先剥注释再扫: 注释里既有用法示例(_runningToast(`…`)), 也有带引号的解释词("进行中"),
        # 都会被字面量正则误抓 —— 只留真代码里的模板/字符串。
        stripped = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        stripped = re.sub(r"(?m)//[^\n]*", "", stripped)
        for m in re.finditer(r"_runningToast\(", stripped):
            window = stripped[m.end():m.end() + 240]
            lits = [a or b for a, b in re.findall(r"`([^`]*)`|\"([^\"]*)\"", window)]
            joined = " ".join(lits)
            for banned in ("进行中", "正在", "等待 tracker", "确认中"):
                if banned in joined:
                    banned_hits.append(f"shared/{name}: `_runningToast` 文案含「{banned}」")
                    break
    # 工厂自身那行 `{ sticky: true }` 是合法供给面(唯一一处), 其余任何手搓都算绕开
    if len(offenders) > 1 or (offenders and not offenders[0].startswith("shared/commands.js")):
        problems.append(
            f"有 sticky 提示条绕开了统一工厂 _runningToast({', '.join(offenders[:3])})"
            " —— 手搓 sticky 条没有最短展示保护, 回执快时会一闪而过被结果条顶掉"
        )
    if banned_hits:
        problems.append(f"归档条文案写成了进行时态({banned_hits[0]}) —— 它结算后要留在队列里"
                        "继续被读到, 文案必须归档后仍成立(用「已投递/已开始/已提交」)")
    # ③ 结算点下限护栏(全 shared 汇总, 不单看 commands.js —— 单文件计数会被 docstring 里的
    # 用法示例撑起来, 虚绿)。目前 5 条链路(强制汇报/导出/删除前置/跳检/转移)共 12 处(含定义);
    # 阈值取 10 = 允许删掉一两条分支, 但整条链路退回"原位改字"时必红。
    settle_total = 0
    for name in sorted(os.listdir(shared_dir)) if os.path.isdir(shared_dir) else []:
        if name.endswith(".js"):
            body = open(os.path.join(shared_dir, name), encoding="utf-8").read()
            body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
            body = re.sub(r"(?m)//[^\n]*", "", body)
            settle_total += len(re.findall(r"_settleRunningToast\(", body))
    if "async _settleRunningToast(" not in cmds or settle_total < 10:
        problems.append(
            f"进行中条的结算没有走 _settleRunningToast(定义缺失或全量调用点仅 {settle_total}"
            " 处, 下限 10) —— 退回同一条 _finishToast 原位改字, 进行中条会被结果瞬间顶掉"
        )

    # 倒计时归属(十一轮, 2026-11-02 · 用户报「强制重新汇报失败的窗口时间指示条到了但没消失」):
    # --fx-life(进度条时长)必须与**这一条**的退场定时器同源。此前 toastSync 的 stamp 分支用
    # "整栈共用"的 ttl 给所有未挂载的新条挂条 —— 而 _settleRunningToast 在同一个 tick 里先给
    # 归档条发 4000(settle)、再推结果条(12000), 两份 $nextTick 按注册序执行, 4000 先落到刚渲染的
    # 结果条上: 进度条 4s 走完, 条按 12s 才移除, 中间 8s 干挂(实测 anim finished t=5106ms /
    # 节点消失 t=13013ms)。修法 = 挂条处按 data-id 命中本条。三条判据缺一条就回到错位:
    if "var own = id != null" not in js or "own && ttl > 0" not in js:
        problems.append(
            "flux/fx-mount.js::toastSync 的倒计时没按 data-id 命中本条(缺 own 判定)"
            " —— 同一 tick 里归档条(4000)的 ttl 会贴到新推入的回执条(12000)上,"
            " 用户看到「时间指示条到了但窗口不消失」"
        )
    elif js.count('setAttribute("data-fx-cd"') != 1:
        problems.append("flux/fx-mount.js 挂 data-fx-cd 的不止一处 —— 唯一一处必须在 own 守卫内,"
                        " 旁路会绕过归属判定, 把别人的 ttl 挂到本条上")
    ui_fb_path = os.path.join(shared_dir, "ui_feedback.js")
    ui_fb = open(ui_fb_path, encoding="utf-8").read() if os.path.isfile(ui_fb_path) else ""
    for m in re.finditer(r"toastSync\(\s*([^)]*)\)", ui_fb):
        args = [a.strip() for a in m.group(1).split(",")]
        if len(args) != 2 or args[1] != "id":
            problems.append(
                f"shared/ui_feedback.js 的 {m.group(0).strip()} 没传本条 id —— 倒计时会"
                "按「整栈 ttl 先到先得」落到别的条上(进度条与退场错位)"
            )

    used = _toast_kinds_in_use()
    for kind in sorted(used - set(_MSG_NEUTRAL_KINDS) - set(tone)):
        problems.append(
            f"toast kind `{kind}` 在模板/JS 里有调用, 但 flux 没有 `.toast.{kind}` 规则"
            " —— 新 kind 必须登记语义档, 否则静默落成中性提示(与 info 同貌)"
        )


def _scan_toast_copy_two_part(problems):
    """toast 文案守阵(2026-11-02 六轮): 每条提示条文案都要是「主标题: 说明」

    背景: 提示条排版改成标题行 + 说明行(见 _scan_message_surface_parity), 但两行的前提是
    **文案本身带分隔符**。用户口径「都改成主标题+说明」= 生产文案也统一 —— 本轮把 58 处没有
    分隔符的回执补上了说明句(「已导出 .torrent」→「已导出: .torrent 文件已保存」之类),
    否则同一屏里永远混着"只有标题"的条, 与选定形态不一致。

    判据(与 `flux/fx-mount.js` 的 `TOAST_SPLIT` 同一条规则, 改一处要同步另一处):
      `主标题` = 首个 `:` / `：` / `,` / `，` 之前, ≤14 字且不含括号;
      `说明` = 其后 ≥2 字。说明门槛低到 2 字是刻意的 —— 「已执行: 重命名」这种短回执的说明
      就是一个名字, 门槛再高它们又会退回单行。

    只判**首参是字面量/模板**的调用: `this.toast(g.title)` / `toast(text, ...)` 这类文案由
    调用方运行时决定, 静态无从判定(它们的实参往往来自后端或常量表), 跳过而不是误报。
    注释与字符串里的 `toast(` 不算调用(注释里讨论 toast 的地方很多)。
    """
    pattern = re.compile(r"^([^:：,，()（）\n]{1,14})[:：,，]\s*([\s\S]{2,})$")
    for name in sorted(os.listdir(os.path.join(STATIC_ROOT, "shared"))):
        if not name.endswith(".js"):
            continue
        path = os.path.join(STATIC_ROOT, "shared", name)
        src = open(path, encoding="utf-8").read()
        for line_no, text in _toast_literal_texts(src):
            if not pattern.match(text):
                problems.append(
                    f"shared/{name}:{line_no} toast 文案不是「主标题: 说明」形态: {text[:40]!r}"
                    " —— 主标题 ≤14 字且不含括号, 其后用 `: ` 或 `, ` 接说明(≥2 字); "
                    "文案决定提示条能不能排成两行, 单行条会与选定形态分家"
                )


def _scan_frontend_assets():
    """扫描 webui/static 返回问题清单(空 = 健康)

    检查项(均为"整页白屏 / 整块功能静默失效"级故障, 且 Python 侧测试天然看不见):
    1. 合并冲突标记残留(`<<<<<<<` / `>>>>>>>` / 单独一行 `=======`) —— 语法错误;
    2. JS 里"注释已闭合却仍留续行"(上一非空行以 `*/` 结尾, 本行又以 `*` 起头) ——
       整包 SyntaxError, app.js 不执行, Vue 从不 mount, `v-cloak` 的 #app 恒 display:none;
    3. JS 语法硬校验: 有 node 时单进程批量校验(语义同 `node --check`, 见 _scan_js_syntax_with_node);
    4. CSS 规则块漏闭合(浏览器会把其后规则整段当声明丢弃) —— 见 _scan_css_blocks;
    5. 模板 `<transition>` 不配对 / 把弹窗包进 `<transition>`(只渲染首子节点 -> 弹窗全丢);
    6. 模板/样式里以 `/` 开头的 src|href 引用, 在 static 根下必须真实存在(防改名/漏档 404);
    7. 追剧视图"集成员 -> hash"必须走 `memberHashesOf`(见 _scan_episode_member_hashes);
    8. `STATE_RANK` 必须与后端 `_SHOW_STATE_RANK` 逐项一致(见 _scan_state_rank) ——
       两表分别决定"辅种页组行"与"追剧页集行"的颜色, 漂移的后果是同一批种子两页不同色;
       该项同时钉住**顺序语义**: seeding 必须排在 paused 之前(混合态取做种色, 2026-09-21 用户口径);
    9. 乐观 UI 的**撤下**路径: 真值快照必须早于补丁重贴、判定必须走 `_optimisticSettled`、
       回执后必须调 `_pullTruthAfterCmd`(见 _scan_pending_settle) —— 任一被绕过, 撤下就退回
       3s 常量兜底(真机连报三次的那条), 或判定恒真导致失败路径留假状态(红线)。
    10. 拆分接线: 片段文件必须被 HTML 引用 + 被 app.js `app.mixin()` 注入, 且成员不得重名
       (见 _scan_mixin_wiring) —— 漏挂/漏注入 = 整块功能静默消失, 重名 = 被覆盖者永不执行。

    11. 筛选器选项必须走 `facetRows` 单点取数面(见 _scan_filter_facets) —— 各自遍历 `groups`
       会在种子页(按视图分片不回数组)算出空选项, 弹层只剩"暂无数据"。
    12. 页面"挂件类名"必须配对存在 CSS 规则: HTML 的 `<main class="...hub-page...">` / `ce-page` /
       `layout` 这类挂件类名, 都必须在对应 CSS(shared/console_hub.css / prism/views.css /
       atlas/style.css)里有规则, 否则**整段页面没样式**(实测: 把 `.hub-page` 错写成 `.hb-page`
       后 `--tone` 从未定义, 所有 `var(--tone)` 派生的描边/发光/语义色全部失效, 还以为"页面正常"
       只是"缺发光"; 真浏览器量 computedStyle 才看得出来)。
       (见 _scan_page_class_wiring)

    13. 毛玻璃(backdrop-filter)不得挂在全屏遮罩 / 吸顶吸底条上, 三旧皮肤声明数相等(恒 0),
       flux 走显式档恰 4 处(顶栏/状态栏/详情面板/弹窗面板, R2 精修 V2; 遮罩对 flux 也禁)
       (见 _scan_backdrop_filter) —— 嵌套毛玻璃会让"点状态栏历史流量"这类开弹层的动作明显卡顿,
       且**只在星图侧复现**(棱镜 .modal-mask 从不带 backdrop-filter), 属于"两边都能跑、一边更卡"
       的差异, 肉眼走查看不出来, 只能靠计数兜底。

    14. 列模型每个列 key 必须在对应模板有值单元格分支(见 _scan_column_cells_paired) ——
       模板漏写分支无任何报错(表头在、列选择器可勾、值永远空白); 明细列两份模板
       (groups.html/shows.html)必须成对; loadColState 必须消费 DEFAULT_HIDDEN_KEYS 单点
       (默认隐藏列注入单点, 列定义禁止再写 hide:true)。

    15. CSS 注释体内不得出现 `*/`(见 _scan_css_comments) —— 注释被提前终止后, 尾巴落成
       代码态垃圾, 浏览器按错误恢复把紧跟的规则整条静默丢弃(2026-09-28 实测: console 皮肤
       进度条注释 `(s-*/member-row 族)` 吞掉 `.m-progress { display: flex }`, 三处表格
       进度条只剩百分比没有条)。

    16. 三套皮肤的 `.m-progress .val` 基础规则必须恰 1 条且带 min-width 定宽(见
       _scan_progress_val_parity) —— 条吃剩余空间, 数值盒不定宽时进度条长度随百分比
       文本宽度逐行漂移(2026-09-28 实测: 「100.0%」的行比「5.2%」的行条短)。

    17. ETA 哨兵跨层一致(见 _scan_eta_sentinel, 2026-10-15 issue 26-10-11-0310):
       后端 `_ETA_SENTINEL` ↔ 全静态树每一处 `sec/eta >= <数>` 比较点(format.js fmtEta
       + 模板 zero 判据)必须同值 —— 聚合口径与显示口径分家是静默故障(该有 ETA 的行恒空);
       零命中即红(判据被改名/删光不许空转)。

    18. 键位归一化正则跨层一致(见 _scan_keys_serial_re, 2026-10-15 issue 26-10-11-0310):
       后端 `_KEYS_SERIAL_RE` ↔ 前端 `KB_DEF_RE` 逐字同源 —— 差一个字符就是单边静默
       (前端放的串后端 422 / 后端放的串前端录完即丢弃)。

    19. 状态色令牌四处成对(见 _scan_state_color_tokens, 2026-11-02): 每个皮肤 7 个 kind 都要
       声明 `--st`/`--st-soft`(值 = 期望表: checking→--warn, moving→--violet), 且进度条
       `.bar > i` 恰 1 条且取 `var(--st` —— 漏一个状态/漏一套皮肤 = 该状态回落写死色,
       校验中与下载中重新同蓝(本次修复前的原症状)。

    20. 消息面材质同源(见 _scan_message_surface_parity, 2026-11-02, 只钉 flux): 提示条与站内
       确认框共用 `--msg-surface` 单点 + 语义档描边(--msg-line)/图标(--msg-tone), 但提示条
       **不得切角**(用户二轮口径「消息通知不要切角」, 反向钉 clip-path); 模板与 JS 里出现的
       每个 toast kind 都必须登记语义档 —— 缺档的 kind 与 info 同貌(warn 档 21 处调用点此前
       整档没样式, 用户报障的"消息弹窗样式没统一"一半来自这里)。
       八~十轮追加队列口径: `.toast-wrap` 必须按 `--statusbar-h` 抬升(不许压住状态栏);
       FLIP 要 `flipStack();` 至少两处(toastSync 插入/结算 + toastDrop 退场); 队列推入要有
       `fx-toast-queue-in` 关键帧 + `[data-fx-queue]` 规则 + JS 盖章(否则新条与让位中的旧条叠画);
       **进行中 → 结果统一两段式**: 所有 `{ sticky: true }` 只能出现在统一工厂 `_runningToast` 体内
       (手搓 = 绕开最短展示与归档口径), 结算一律走 `_settleRunningToast`(全 shared 汇总调用点下限 10,
       防整条链路退回原位改字), 归档条文案不许写进行时态(它结算后要留在队列里与结果条并存)。
    21. toast 文案 = 「主标题: 说明」(见 _scan_toast_copy_two_part, 2026-11-02 六轮): 每条提示条
       文案都要能被 fx-mount.js 的 `TOAST_SPLIT` 拆成两行 —— 主标题 ≤14 字(不含括号) + `: ` / `, `
       后接说明(≥2 字)。提示条排版改成标题行 + 说明行之后, "文案本身没有说明"就是新的分家来源
       (用户六轮口径「都改成主标题+说明」, 本轮把 58 处没有分隔符的回执补上了说明句)。
       只判首参是字面量/模板的调用; `toast(g.title)` 这类运行时决定的文案跳过(静态无从判定)。

    22. flux 弹窗毛玻璃与浮层不透明底对照(见 _scan_flux_modal_frost, 2026-11-03): `.modal` 必须
       同时保留无前缀与 `-webkit-` blur, 且底走 `--msg-base: var(--bg-card)` 半透明角色面 ——
       26-11-02 消息面统一把弹窗底换成 `--bg-elev`(92%)后 blur 仅剩 8% 透视, 肉眼读成"毛玻璃被
       上一次透明修复弄丢"; 反向同时钉透明修复侧(`--bg-pop` 不透明 + 八类无 blur 浮层仍消费它),
       防只修一边又翻烧饼。


    WARN: 7/8/9/11/18 五项按 **app.js 整包**(HTML 加载顺序拼接 app.js + 各片段)扫描, 不按单文件 ——
      拆分后同一条不变量的代码可能分处两个文件, 只看一个文件必然漏(2026-09-20 实测);
      17 按**全静态树**(含模板分片, 哨兵比较点在 tpl 里也有)扫描, 同样不按单文件。
    """
    problems = []
    js_files = []
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            if not name.endswith((".js", ".css", ".html")):
                continue
            with open(path, encoding="utf-8") as f:
                lines = f.read().splitlines()
            for i, line in enumerate(lines, 1):
                if line.startswith(("<<<<<<<", ">>>>>>>")) or line == "=======":
                    problems.append(f"{rel}:{i} 合并冲突标记残留")
            # 只扫自家前端(vendor 为第三方压缩产物, 不适用本仓库注释/结构规范)
            if "/vendor/" not in f"/{rel}":
                if name.endswith(".js"):
                    js_files.append((path, rel))
                    for i, line in enumerate(lines):
                        if not re.match(r"^\s*\*(?!/)", line):
                            continue
                        prev = next((l for l in reversed(lines[:i]) if l.strip()), "")
                        if prev.rstrip().endswith("*/"):
                            problems.append(f"{rel}:{i + 1} 注释块已闭合后仍有续行(会造成整包 SyntaxError)")
                elif name.endswith(".css"):
                    _scan_css_blocks(path, rel, problems)
                    _scan_css_comments(path, rel, problems)
                elif name.endswith(".html"):
                    _scan_template_transitions(path, rel, problems)
            for ref in re.findall(r'(?:src|href)="(/[^"]+)"', "\n".join(lines)):
                if not os.path.exists(os.path.join(STATIC_ROOT, ref.lstrip("/"))):
                    problems.append(f"{rel} 引用不存在的静态资源 {ref}")
    _scan_js_syntax_with_node(js_files, problems)
    # app.js 已按域拆分(2026-09-20): 跨文件不变量按**整包**(HTML 加载顺序拼接)扫描 ——
    # 只看 app.js 会把搬进片段的那半漏掉, 只看片段又拿不到 app.js 里的表格常量与 refresh 主链。
    bundle = _app_bundle_files()
    bundle_text = "\n".join(open(p, encoding="utf-8").read() for p, _r in bundle)
    rel = "shared/app.js(整包 %d 个文件)" % len(bundle)
    _scan_episode_member_hashes(bundle_text, rel, problems)
    _scan_state_rank(bundle_text, rel, problems)
    _scan_keys_serial_re(bundle_text, rel, problems)
    _scan_eta_sentinel(problems)
    _scan_pending_settle(bundle_text, rel, problems)
    _scan_filter_facets(bundle_text, rel, problems)
    _scan_mixin_wiring(problems)
    _scan_page_class_wiring(problems)
    _scan_backdrop_filter(problems)
    _scan_column_cells_paired(problems)
    _scan_progress_val_parity(problems)
    _scan_state_color_tokens(problems)
    _scan_message_surface_parity(problems)
    _scan_flux_modal_frost(problems)
    _scan_toast_copy_two_part(problems)
    return problems


def _scan_ui_diff_registry(problems):
    """收集 shared/tpl 里的 UI 差异口(`v-if="ui === ...'"`) —— 「活差异清单」的机械面

    收敛定案(plans/26-09-26-2233 W3): 单一语义模板后, 模板级 UI 差异只允许写成
    `<template v-if="ui === 'atlas'|'prism'">` 条件块, 且块前必须带 `ui-diff:` 注释说明原因;
    新增差异走这个口, **不许另开分片副本**(双模板副本的复发形态就是绕开这个口私拷一份)。
    """
    registry = []
    shared_dir = os.path.join(STATIC_ROOT, "shared", "tpl")
    if not os.path.isdir(shared_dir):
        problems.append("缺 shared/tpl 单一语义分片目录(模板分裂回潮?)")
        return registry
    for name in sorted(os.listdir(shared_dir)):
        if not name.endswith(".html"):
            continue
        lines = open(os.path.join(shared_dir, name), encoding="utf-8").read().split("\n")
        for i, ln in enumerate(lines):
            m = re.search(r"v-if=\"ui\s*===\s*'(\w+)'\"", ln)
            if not m:
                continue
            side = m.group(1)
            if side not in _UI_ALL:
                problems.append(f"shared/tpl/{name}:{i + 1} UI 条件取值非法: {side!r}(只认 {'|'.join(_UI_ALL)})")
            if "ui-diff:" not in "\n".join(lines[max(0, i - 3):i + 1]):
                problems.append(f"shared/tpl/{name}:{i + 1} ui 条件块缺 `ui-diff:` 注释(差异口必须写明原因)")
            registry.append(f"{name}:{i + 1}:{side}")
    return registry
