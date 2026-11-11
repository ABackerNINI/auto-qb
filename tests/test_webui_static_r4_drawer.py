"""test_webui_static_r4_drawer 测试计划: 存量评审 R4 static 主题清池 P07 —— 抽屉交互域 + 共享行为电池
3 修复回归(R5#60/61/62) + 5 补测电池(R5#56/145/69/68/148)

## 测试计划(每个测试函数一条)
- test_r4_share_limits_sentinel: R5#60(major) 修复回归 —— editShareLimits 哨兵契约与后端
  commands_limit.py::_cmd_set_share_limits 对齐(-2=用全局, -1=不限制): 输入 -2 三维原样透传
  (ratio_limit/seeding_time_limit/inactive_seeding_time_limit)、其它值透传原值(小时 x3600 转
  秒)、校验域 [-2, 0..] 之外(-1/-3/非数字)拒收且零投递、空输入 = 不修改零投递、文案与占位符
  钉 -2(「输 -2 = 恢复全局默认」, 不再出现 -1)与取消零投递
- test_r4_drawer_del_receipt_close: R5#61 修复回归 —— drawerDel 按删除回执 ok 收口且只收
  「仍是同一 hash」的抽屉: 回执 ok+hash 未变(memberByHash 仍列被删 hash = 主轮询未落地的
  竞态形态)必收、回执 ok+期间换目标不收、回执失败不收、抽屉已关不收、回执 ok+memberByHash
  已移除(轮询已落地)也收; _deleteFlow 回执契约四出口(取消/汇报前置失败/发送异常 => false,
  回执 ok => true; bulk 载荷 action/hashes/delete_files 齐全; 未知目标 falsy 零投递)
- test_r4_deco_fingerprint_pair: R5#56 —— 组行装饰记忆化指纹对 build->hit 往返: 未脏行必命中、
  fp 长度不变量(n*8+3)、逐槽必失配(kind/size/category/site/tags 引用/site_alert/site_alert_msg/
  成员 relocate 签名字段/首成员 save_path/members 引用/成员数增减/组 relocate 签名)、
  失配后恢复原值复命中(逐槽值比对而非一次性)、重算回填后的新指纹对往返命中、
  无 relocate 字段与空成员组边界
- test_r4_delete_details_rows: R5#145 —— 删除确认框行拼装: _hrRiskOf(HR_NO_DELETE 只认 danger,
  failed/warning 不点名; 来源短语去重; 名字最多 3 个 + " 等 N 个" 后缀; 无名回落 hash 前 12)
  与 _deleteDetails(单目标退化名字/多目标计数摘要、站点与路径去重拼接、空集合回落 —、
  实际占用条件行仅 occupy<total 时出现带 hint、组展开含 virtual、keys/hashes 交叠去重)
- test_r4_relocate_confirm_rows: R5#69 —— _relocateConfirmRows/_relocateConfirmCount 纯函数
  (目录别名「未来种子」分支/非别名分支/未知 form 回落/reasons 以 "; " 拼接/notes 取首个/
  多项 #n 前缀/cls 过滤/空结果空表) + submitMoveDialog confirm 回路桩驱动(首投递 "confirm" ->
  收设定位置框 -> 确认框 true -> confirm=true 重发; 取消 -> 不重发带原路径重开; 再 confirm 仍
  "confirm" -> warn + 重开; 一次成功不经确认框; 批量走 _bulkEditPost; 空路径拒发)
- test_r4_drawer_clamp_height: R5#68 —— _drawerClampHeight 三组边界: 240 下界(px<240 提到
  240)/70vh 上界(px>max 压到 max, max=round(vh*0.7))/极小视口(70vh<240 时 min=max, px 双向
  夹到同一值) + 取整(落盘值不带亚像素尾数)
- test_r4_relocate_chain_popover: R5#148 —— 迁移路径链浮窗行为(vm 桩): relChainOpen 开/同 hash
  再开即关(翻转, 焦点回落触发钮)/关后再开重开、换 hash 重开 seq 单调自增、A 慢响应落袋不
  覆写 B(seq 代际守卫: data/loading/hash 全保 B)、关闭后响应不落袋(open 守卫)、relChainPlace
  四向定位(锚下方/左越界夹取/右越界夹取/下方放得下不翻面/极矮视口翻上方/无锚居中/关着零
  写入)、滚动即关(capture 监听; 浮窗内部滚动与浮窗自身不关)、resize 即关、relChainRefresh
  loading 中不重取 + 带 refresh=1
- test_r4_emptyhost_deadvar_gone: R5#62 —— emptyHost 死变量(赋值后零读者, 全仓 grep 证)删除后
  不回潮; 换代守卫注释与现状对齐(_dtUnmountOne 摘桥路径兜住, 不再声称未实现的「old 空必换代」);
  现行换代判据(同 seg 锚元素被换)保持原样

加载口径: drawer 域经 webui_helpers.bundle_file("drawer.js") 聚合(根 + files/general/rows 三片段
清单序); delete_flow.js/decorate.js 单文件直接 eval; relocate_chain.js 走 vm 沙箱(与既有
test_webui_relocate_chain.py 同式)。app.js 常量 L10N_GROUP 由电池自给(值 "辅种", 与 app.js 单点
一致)。confirmDialog/api/waitCmd/toast/closeDrawer 等按浏览器契约给桩。无 node 静默跳过
(与既有 node 电池同口径, 不引入 pytest skip)。
"""

import json
import os
import shutil
import subprocess

from webui_helpers import STATIC_ROOT, bundle_file, read_shared


def _run_probe(probe, *args):
    """跑一个 node 电池: 无 node 静默跳过(返回 None); 输出末行必须是 {ok, total, failed} JSON"""
    node = shutil.which("node")
    if not node:
        return None
    proc = subprocess.run(
        [node, "-e", probe, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"node 电池跑挂: {proc.stderr.strip()}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _assert_battery(report, what):
    assert report is not None, "无 node: 本电池静默跳过(与既有电池同口径)"
    assert report["failed"] == [], f"{what} {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


def _shared_path(name):
    return os.path.join(STATIC_ROOT, "shared", name)


# R5#60(major) 修复回归: editShareLimits 哨兵 -2(与 commands_limit.py -1/-2 语义对齐) ----------
_NODE_SHARE_LIMITS_PROBE = r"""
const fs = require("fs");
global.window = { AQB_DRAWER_TPL_REG: { helpers: {} } };
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_DRAWER;");
const DM = globalThis.__W2__.methods;

const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// 桩: _editDetail 给详情, _openModal 回放表单值并留档, _editPost 记录投递载荷
const mkCtx = (res) => {
  const c = Object.assign({}, DM, {
    menu: { hash: "H1", visible: true },
    drawer: { open: false, hash: "H1", detail: null },
    opened: [], posts: [], toasts: [],
  });
  c._editDetail = async () => null;
  c._openModal = async (opts) => { c.opened.push(opts); return res; };
  c.toast = (msg, kind) => c.toasts.push({ msg, kind });
  c._editPost = async (hash, action, body, okText) => { c.posts.push({ hash, action, body, okText }); return true; };
  return c;
};
const warnOf = (c) => c.toasts.filter((t) => t.kind === "warn").map((t) => t.msg).join(" | ");

(async () => {
  // 1. 输入 -2 三维: 透传 -2(用全局), 不再有任何哨兵改写
  let c = mkCtx({ ratio: "-2", time: "-2", inactive: "-2" });
  await c.editShareLimits();
  ok("输入 -2 三维透传 -2(回执语义=用全局, 不再写 -1 永不限制)",
     c.posts.length === 1 && JSON.stringify(c.posts[0].body) === JSON.stringify({
       ratio_limit: -2, seeding_time_limit: -2, inactive_seeding_time_limit: -2 }));
  ok("投递端点与目标正确", c.posts[0].action === "share-limits" && c.posts[0].hash === "H1");
  ok("输入 -2 无校验告警", warnOf(c) === "");

  // 2. 其它值透传原值: 小时 x3600 转秒, 分享率原值
  c = mkCtx({ ratio: "1.5", time: "24", inactive: "0" });
  await c.editShareLimits();
  ok("常规值透传原值(1.5 / 24h=86400s / 0 原样)",
     c.posts.length === 1 && JSON.stringify(c.posts[0].body) === JSON.stringify({
       ratio_limit: 1.5, seeding_time_limit: 86400, inactive_seeding_time_limit: 0 }));

  // 3. 混合: 空 = 不修改, -2 哨兵只落在有值维度
  c = mkCtx({ ratio: "", time: "-2", inactive: "3.5" });
  await c.editShareLimits();
  ok("空维度不投递, -2 只落在有值维度(3.5h=12600s)",
     c.posts.length === 1 && JSON.stringify(c.posts[0].body) === JSON.stringify({
       seeding_time_limit: -2, inactive_seeding_time_limit: 12600 }));

  // 4. 校验域 [-2, 0..] 之外拒收(照现行校验形态: 负数只放行 -2): 零投递 + warn
  for (const [field, val, re] of [
    ["ratio", "-1", /分享率无效.*-2/], ["ratio", "-3", /分享率无效/],
    ["time", "-1", /时长无效.*-2/], ["inactive", "abc", /时长无效/],
  ]) {
    c = mkCtx({ ratio: "", time: "", inactive: "", [field]: val });
    await c.editShareLimits();
    ok(`域外值拒收: ${field}=${val}(零投递 + 文案钉 -2)`, c.posts.length === 0 && re.test(warnOf(c)));
  }

  // 5. 全空 = 不修改: 零投递
  c = mkCtx({ ratio: "", time: "", inactive: "" });
  await c.editShareLimits();
  ok("全空输入零投递(未作修改提示)", c.posts.length === 0 && /未作修改/.test(c.toasts.map((t) => t.msg).join("|")));

  // 6. 文案与占位符钉 -2(用户可见面与后端 docstring 同语义)
  c = mkCtx(null);
  await c.editShareLimits();
  const opts = c.opened[0];
  ok("对话框文案写清「输 -2 = 恢复全局默认」", opts && /输 -2 = 恢复全局默认/.test(opts.body));
  ok("三字段占位符均钉 -2 = 全局, 全框不再出现 -1",
     opts && opts.fields.length === 3 && opts.fields.every((f) => /-2 = 全局/.test(f.placeholder)) &&
     !/-1/.test(opts.body) && opts.fields.every((f) => !/-1/.test(f.placeholder)));

  // 7. 取消(res=null): 零投递
  c = mkCtx(null);
  await c.editShareLimits();
  ok("取消零投递", c.posts.length === 0);
})().then(() => {
  console.log(JSON.stringify({
    ok: checks.filter((x) => x[1]).length, total: checks.length,
    failed: checks.filter((x) => !x[1]).map((x) => x[0]),
  }));
}).catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

# R5#61 修复回归: drawerDel 按删除回执 ok 收口(竞态判据退役) ---------------------------------
_NODE_DRAWER_DEL_PROBE = r"""
const fs = require("fs");
global.window = { AQB_DRAWER_TPL_REG: { helpers: {} } };
global.L10N_GROUP = "辅种";   // app.js 单点(电池自给)
const srcDrawer = fs.readFileSync(process.argv[1], "utf8");
eval(srcDrawer + "\n;globalThis.__W2__ = window.AQB_DRAWER;");
const srcDel = fs.readFileSync(process.argv[2], "utf8");
eval(srcDel + "\n;globalThis.__W3__ = window.AQB_DELETE;");
const DM = globalThis.__W2__.methods;
const DE = globalThis.__W3__.methods;

const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const settle = async (n = 6) => { for (let i = 0; i < n; i++) await new Promise((r) => setTimeout(r, 0)); };

/* 桩: memberByHash 是 Map(轮询每 1.5~3s 才落地; 桩静态 = 钉「回执后成员仍在」的竞态形态)。
 * _confirmDelete 回放确认结果, waitCmd 回放聚合回执, closeDrawer 记次。 */
const mkCtx = ({ confirm = {}, receipt = {}, known = ["H1"], apiFail = false,
                singles = [{ hash: "H1", name: "种子甲" }] } = {}) => {
  const c = Object.assign({}, DM, DE, {
    menu: { hash: "", visible: false },
    drawer: { open: true, hash: "H1", detail: null },
    memberByHash: new Map(known.map((h) => [h, { hash: h, name: "N_" + h }])),
    singles, torrents: [], filteredGroups: [],
    closed: 0, posts: [], toasts: [], cleared: 0,
  });
  c.closeDrawer = () => { c.closed += 1; };
  c.toast = (msg, kind) => c.toasts.push({ msg, kind });
  c.clearSelection = () => { c.cleared += 1; };
  c._auditScope = () => {};
  c._confirmDelete = async () => confirm;             // {checks:{...}} 或 null(取消)
  c._reannounceAll = async () => true;
  c.reannouncePlan = () => ({ keys: [], hashes: [], skipped: 0 });
  c.reannounceBlocked = () => false;
  c.selSizeSummaryOf = () => ({ total: 0, occupy: 0 });
  c.fmtSize = (n) => String(n);
  // S2(计划 26-11-11-0820)起 _deleteDetails 消费 selection.js 的部分组谓词; 本电池不加载
  // selection.js, 桩空返回=「无部分组」负例口径(真跑集成见 node_batteries 的删除链部分组行电池)
  c._partialGroupsOf = () => [];
  c.api = async (url, opts) => {
    if (apiFail) throw new Error("boom");
    c.posts.push({ url, body: JSON.parse(opts.body) });
    return { cmd_id: "c1" };
  };
  c.waitCmd = async () => receipt;                     // {ok: ...} 聚合回执
  return c;
};

(async () => {
  const OKCONFIRM = { checks: { reannounce: false, delete_files: false } };

  // 1. 回执 ok + hash 未变 + memberByHash 仍列被删 hash(主轮询未落地) -> 必收(修复前红:
  //    旧判据 !memberByHash.get() 为假 => 不收, 抽屉停在已删种子上)
  let c = mkCtx({ confirm: OKCONFIRM, receipt: { ok: true }, known: ["H1"] });
  c.drawerDel();
  await settle();
  ok("回执 ok+hash 未变 -> 收抽屉(即使 memberByHash 还没落地)", c.closed === 1);
  ok("pending 标志收口复位", c._drawerDeletePending === false);
  ok("bulk 删除载荷齐全", c.posts.length === 1 && c.posts[0].body.action === "delete" &&
     c.posts[0].body.hashes.join() === "H1" && c.posts[0].body.delete_files === false);

  // 2. 回执 ok + 期间用户换了 drawer 目标 -> 不收(判据 hash 必须是调用点捕获的被删 hash)
  c = mkCtx({ confirm: OKCONFIRM, receipt: { ok: true }, known: ["H1"] });
  c.waitCmd = async () => { c.drawer.hash = "H2"; return { ok: true }; };
  c.drawerDel();
  await settle();
  ok("回执 ok+已换目标 -> 不收新目标的抽屉", c.closed === 0 && c.drawer.hash === "H2");

  // 3. 回执失败 -> 不收
  c = mkCtx({ confirm: OKCONFIRM, receipt: { ok: false, error: "qB 拒绝" }, known: ["H1"] });
  c.drawerDel();
  await settle();
  ok("回执失败 -> 不收(且报删除未完全成功)",
     c.closed === 0 && /删除未完全成功/.test(c.toasts.map((t) => t.msg).join("|")));

  // 4. 抽屉已关 -> 不收(回执慢于手动关面板)
  c = mkCtx({ confirm: OKCONFIRM, receipt: { ok: true }, known: ["H1"] });
  c.waitCmd = async () => { c.drawer.open = false; return { ok: true }; };
  c.drawerDel();
  await settle();
  ok("回执到达时抽屉已关 -> 不收", c.closed === 0);

  // 5. 回执 ok + memberByHash 已移除(轮询先落地) -> 照样收(判据只认回执, 不读成员表)
  c = mkCtx({ confirm: OKCONFIRM, receipt: { ok: true }, known: [] });
  c.drawerDel();
  await settle();
  ok("回执 ok+成员表已移除 -> 收", c.closed === 1);

  // ---- _deleteFlow 回执契约(delTorrent 的返回来源) ----
  // 6. 用户取消确认框 -> false
  c = mkCtx({ confirm: null, known: ["H1"] });
  ok("取消确认框 -> delTorrent false", await c.delTorrent("H1") === false && c.posts.length === 0);
  // 7. 汇报前置失败 -> false(保守口径不放宽)
  c = mkCtx({ confirm: { checks: { reannounce: true, delete_files: true } }, known: ["H1"] });
  c.reannouncePlan = () => ({ keys: ["g1"], hashes: [], skipped: 0 });
  c._reannounceAll = async () => false;
  ok("汇报前置失败 -> false 零删除投递", await c.delTorrent("H1") === false && c.posts.length === 0);
  // 8. 发送异常 -> false
  c = mkCtx({ confirm: OKCONFIRM, receipt: { ok: true }, known: ["H1"], apiFail: true });
  ok("发送异常 -> false", await c.delTorrent("H1") === false && c.closed === 0);
  // 9. 未知目标(找不到成员) -> falsy
  c = mkCtx({ known: [], singles: [] });
  ok("未知目标 -> falsy 不投递", !(await c.delTorrent("H1")) && c.posts.length === 0);
})().then(() => {
  console.log(JSON.stringify({
    ok: checks.filter((x) => x[1]).length, total: checks.length,
    failed: checks.filter((x) => !x[1]).map((x) => x[0]),
  }));
}).catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

# R5#56: 组行装饰记忆化指纹对 build->hit 往返 --------------------------------------------------
_NODE_DECO_FP_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__X = { B: _decoFpBuild, H: _decoFpHit };");
const B = globalThis.__X.B;
const H = globalThis.__X.H;

const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

const mkMember = (over) => Object.assign({
  hash: "h1", kind: "seeding", size: 100, category: "cat", site: "s1",
  tags: ["t1"], site_alert: "", site_alert_msg: "",
  relocate: { state: "moving", phase: "watching", job_id: "j1", mover: true, origin: "web",
              alias_kind: "symlink", alias_count: 2, src: "R:/a", dst: "R:/b",
              created_at: 1, armed_at: 2, updated_at: 3, reason: "" },
  save_path: "R:/a",
}, over);
const mkGroup = (members, relocate) => ({ key: "g1", members, relocate: relocate || null });

const m1 = mkMember();
const m2 = mkMember({ hash: "h2", kind: "downloading", size: 200, site: "s2", save_path: "R:/c" });
const g = mkGroup([m1, m2], { state: "mixed", pending: 1, total: 2, job_ids: ["j1"], dst: ["R:/b"], updated_at: 9 });

// 1. 未脏行必命中 + 长度不变量
const fp = B(g);
ok("未脏行 build->hit 命中", H(g, fp) === true);
ok("fp 长度不变量 n*8+3(与 build 槽清单逐字对应)", fp.length === 2 * 8 + 3);

// 2. 逐槽必失配(成员 8 列值槽 + save_path); 每槽配对还原(值槽换引用, relocate 是原地改值
// 槽 —— 签名槽的还原必须写回原字段值, 只还原引用不够)
const relSnap = JSON.parse(JSON.stringify(m1.relocate));
const snap = { kind: m1.kind, size: m1.size, category: m1.category, site: m1.site, tags: m1.tags,
               site_alert: m1.site_alert, site_alert_msg: m1.site_alert_msg, save_path: m1.save_path };
const mutAndMiss = (name, fn, undo) => {
  fn();
  const missed = H(g, fp) === false;
  undo();
  ok(name + "(改槽必失配, 还原复命中)", missed && H(g, fp) === true);
};
const setRel = (field, v) => { m1.relocate[field] = v; };
mutAndMiss("槽: kind", () => { m1.kind = "pausedDL"; }, () => { m1.kind = snap.kind; });
mutAndMiss("槽: size", () => { m1.size = 111; }, () => { m1.size = snap.size; });
mutAndMiss("槽: category", () => { m1.category = "cat2"; }, () => { m1.category = snap.category; });
mutAndMiss("槽: site", () => { m1.site = "s9"; }, () => { m1.site = snap.site; });
mutAndMiss("槽: tags 引用(换新数组即失配)", () => { m1.tags = ["t1"]; }, () => { m1.tags = snap.tags; });
mutAndMiss("槽: site_alert", () => { m1.site_alert = "err"; }, () => { m1.site_alert = snap.site_alert; });
mutAndMiss("槽: site_alert_msg", () => { m1.site_alert_msg = "boom"; }, () => { m1.site_alert_msg = snap.site_alert_msg; });
mutAndMiss("槽: 成员 relocate.state(P0 相位推进只改值)",
           () => setRel("state", "done"), () => setRel("state", relSnap.state));
mutAndMiss("槽: 成员 relocate.src(P1 详情段消费)",
           () => setRel("src", "R:/z"), () => setRel("src", relSnap.src));
mutAndMiss("槽: 成员 relocate.armed_at",
           () => setRel("armed_at", 99), () => setRel("armed_at", relSnap.armed_at));
mutAndMiss("槽: 首成员 save_path", () => { m1.save_path = "R:/q"; }, () => { m1.save_path = snap.save_path; });

// 3. 结构面: members 引用 / 成员数增减 / 组 relocate 签名
const membersRef = g.members;
g.members = [m1, m2];
ok("槽: members 引用被换(内容相等也失配, 引用槽)", H(g, fp) === false);
g.members = membersRef;
g.members.push(mkMember({ hash: "h3" }));
ok("成员新增必失配", H(g, fp) === false);
g.members.pop();
g.members.pop();
ok("成员减少必失配", H(g, fp) === false);
g.members.push(m2);
ok("成员还原(引用同前)复命中", H(g, fp) === true);
const rel = g.relocate;
g.relocate = Object.assign({}, rel, { updated_at: 10 });
ok("槽: 组 relocate.updated_at(徽标 title 消费)", H(g, fp) === false);
g.relocate = Object.assign({}, rel, { pending: 5 });
ok("槽: 组 relocate.pending", H(g, fp) === false);
g.relocate = rel;
ok("组 relocate 还原复命中", H(g, fp) === true);

// 4. 重算回填后再往返: 改值 -> 新 fp -> 命中(缓存回填口径)
m1.kind = "error";
const fp2 = B(g);
ok("失配重算后的新指纹对自身往返命中", H(g, fp2) === true && H(g, fp) === false);

// 5. 边界: 无 relocate(签名空串)/空成员组
const gPlain = mkGroup([mkMember({ relocate: undefined })], null);
ok("无 relocate 字段照常往返命中", H(gPlain, B(gPlain)) === true);
const gEmpty = mkGroup([], null);
ok("空成员组往返命中(save_path 槽落 undefined)", H(gEmpty, B(gEmpty)) === true);
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#145: 删除确认框行拼装(_hrRiskOf/_deleteDetails) ------------------------------------------
_NODE_DELETE_DETAILS_PROBE = r"""
const fs = require("fs");
global.window = {};
global.L10N_GROUP = "辅种";   // app.js 单点(电池自给)
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W3__ = window.AQB_DELETE;");
const DE = globalThis.__W3__.methods;

const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

const mkMember = (over) => Object.assign({
  hash: "h1", name: "种子甲", site: "s1", save_path: "R:/a", size: 100,
  hr_safety: "", hr_safety_text: "",
}, over);
const mkCtx = (groups, members, summary) => Object.assign({}, DE, {
  _findGroup: (k) => groups.find((g) => g.key === k) || null,
  memberByHash: new Map(members.map((m) => [m.hash, m])),
  selSizeSummaryOf: () => summary || { total: 300, occupy: 300 },
  fmtSize: (n) => n + "B",
  // S2(计划 26-11-11-0820)起 _deleteDetails 末尾消费 selection.js 的部分组谓词追加警示行;
  // 本电池不加载 selection.js, 桩空返回=「无部分组」负例口径(真跑集成见 node_batteries
  // 的 test_r4_delete_details_partial_group_row 电池)
  _partialGroupsOf: () => [],
});
const rowOf = (rows, label) => rows.find((r) => r.label === label);
const val = (rows, label) => (rowOf(rows, label) || {}).value;

// ---- _hrRiskOf: HR_NO_DELETE 只认 danger ----
const c = mkCtx([], [], null);
ok("空目标 -> null(不加风险行)", DE._hrRiskOf.call(c, []) === null);
ok("failed/warning 不点名(HR_NO_DELETE 只认 danger)",
   DE._hrRiskOf.call(c, [mkMember({ hr_safety: "failed", hr_safety_text: "考核未过" }),
                         mkMember({ hash: "h2", hr_safety: "warning", hr_safety_text: "疑似辅种" })]) === null);
let risk = DE._hrRiskOf.call(c, [mkMember({ hr_safety: "danger", hr_safety_text: "考察中" })]);
ok("danger 点名: 计数/来源/名字", risk && risk.count === 1 && risk.srcs === "考察中" && risk.names === "种子甲" && risk.more === "");
risk = DE._hrRiskOf.call(c, [
  mkMember({ hr_safety: "danger", hr_safety_text: "考察中" }),
  mkMember({ hash: "h2", name: "种子乙", site: "s2", hr_safety: "danger", hr_safety_text: "考察中" }),
]);
ok("来源短语去重(同文案只列一次)", risk.srcs === "考察中");
ok("多名字以、拼接", risk.names === "种子甲、种子乙" && risk.count === 2);

// 名字截 3 + more 后缀; 无名回落 hash 前 12
const many = ["甲", "乙", "丙", "丁"].map((n, i) =>
  mkMember({ hash: "hash" + i, name: "种子" + n, hr_safety: "danger", hr_safety_text: "T" + i }));
risk = DE._hrRiskOf.call(c, many);
ok("名字最多列 3 个 + 「 等 4 个」后缀", risk.names === "种子甲、种子乙、种子丙" && risk.more === " 等 4 个");
risk = DE._hrRiskOf.call(c, [mkMember({ hash: "abcdefghij1234", name: "", hr_safety: "danger", hr_safety_text: "T" })]);
ok("无名成员回落 hash 前 12 位", risk.names === "abcdefghij12");

// ---- _deleteDetails: 行拼装 ----
// 单目标: 退化成名字, 五行基准面
const groups = [];
const members = [mkMember()];
let rows = DE._deleteDetails.call(mkCtx(groups, members), [], ["h1"]);
ok("单目标: 目标行退化成名字", val(rows, "目标") === "种子甲");
ok("单目标: 五行基准(成员/站点/保存路径/总大小)",
   rows.length === 5 && val(rows, "成员") === "1 个种子" && val(rows, "站点") === "s1" &&
   val(rows, "保存路径") === "R:/a" && val(rows, "总大小") === "300B");
ok("occupy==total 不加实际占用行", !rowOf(rows, "实际占用"));

// 实际占用条件行: occupy<total 才出现, 带 hint
rows = DE._deleteDetails.call(mkCtx(groups, members, { total: 300, occupy: 100 }), [], ["h1"]);
const occ = rowOf(rows, "实际占用");
ok("occupy<total 追加实际占用行 + hint", !!occ && occ.value === "100B" &&
   /多站点副本只计一份/.test(occ.hint || ""));

// 站点/路径去重与拼接; 空集合回落 —
const two = [mkMember(), mkMember({ hash: "h2", name: "种子乙", site: "s1", save_path: "R:/a" })];
rows = DE._deleteDetails.call(mkCtx(groups, two), [], ["h1", "h2"]);
ok("站点/路径去重(重复值只列一次)", val(rows, "站点") === "s1" && val(rows, "保存路径") === "R:/a");
ok("双目标多 hash 走计数摘要", val(rows, "成员") === "2 个种子" && val(rows, "目标") === "0 个辅种 · 2 个种子");
const diff = [mkMember(), mkMember({ hash: "h2", name: "种子乙", site: "s2", save_path: "R:/b" })];
rows = DE._deleteDetails.call(mkCtx(groups, diff), [], ["h1", "h2"]);
ok("异值站点 ', ' 拼接 / 路径 ' · ' 拼接", val(rows, "站点") === "s1, s2" && val(rows, "保存路径") === "R:/a · R:/b");
rows = DE._deleteDetails.call(mkCtx(groups, [mkMember({ site: "", save_path: "" })]), [], ["h1"]);
ok("空站点/路径回落 —", val(rows, "站点") === "—" && val(rows, "保存路径") === "—");

// 组展开: 常规组展到成员; virtual 组取 members[0]; keys/hashes 交叠去重
const gNormal = { key: "g1", members: [mkMember(), mkMember({ hash: "h2", name: "种子乙" })] };
const gVirtual = { key: "u-h9", virtual: true, members: [mkMember({ hash: "h9", name: "虚拟" })] };
const all = [mkMember(), mkMember({ hash: "h2", name: "种子乙" }), mkMember({ hash: "h9", name: "虚拟" })];
rows = DE._deleteDetails.call(mkCtx([gNormal, gVirtual], all), ["g1"], []);
ok("常规组展开到成员级(2 个)", val(rows, "成员") === "2 个种子");
rows = DE._deleteDetails.call(mkCtx([gNormal, gVirtual], all), ["u-h9"], []);
ok("virtual 组只取 members[0]", val(rows, "成员") === "1 个种子" && val(rows, "目标") === "虚拟");
rows = DE._deleteDetails.call(mkCtx([gNormal, gVirtual], all), ["g1"], ["h1"]);
ok("keys/hashes 交叠按 hash 去重(仍 2 个)", val(rows, "成员") === "2 个种子");
console.log(JSON.stringify({
  ok: checks.filter((x) => x[1]).length, total: checks.length,
  failed: checks.filter((x) => !x[1]).map((x) => x[0]),
}));
"""

# R5#69: 迁移确认框行表纯函数 + submitMoveDialog confirm 回路 ---------------------------------
_NODE_RELOCATE_CONFIRM_PROBE = r"""
const fs = require("fs");
global.window = { AQB_DRAWER_TPL_REG: { helpers: {} } };
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_DRAWER;");
const DM = globalThis.__W2__.methods;

const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// ---- _relocateConfirmCount / _relocateConfirmRows 纯函数 ----
const ctx = Object.assign({}, DM);
ok("无 truth -> count 0", DM._relocateConfirmCount.call(ctx, {}) === 0);
ok("truth.summary.confirm 直读", DM._relocateConfirmCount.call(ctx, { truth: { summary: { confirm: 2 } } }) === 2);

const item = (over) => Object.assign({
  cls: "confirm", form: "dir_alias", save_path: "R:/src", target: "R:/dst",
  reasons: [{ text: "别名" }, { text: "长路径" }, {}], notes: ["note1", "note2"],
}, over);
const rcpt = (items) => ({ truth: { summary: { confirm: items.length }, results: items } });

// 单项目录别名: 「未来种子」别名分支 + reasons 拼接 + notes 首个 + 无 #n 前缀
let rows = DM._relocateConfirmRows.call(ctx, rcpt([item()]));
ok("单项目: 无 #n 前缀, 形态映射目录别名", rows.length >= 4 &&
   rows[0].label === "迁移形态" && /目录别名/.test(rows[0].value));
ok("目录别名分支: 未来种子=受影响(以后新增也落新位置)",
   /受影响/.test(rows[3].value) && /以后新增\/写入的文件也会落到新目标路径/.test(rows[3].value));
ok("reasons 以 '; ' 拼接且空项滤掉", rows.some((r) => r.label === "原因" && r.value === "别名; 长路径"));
ok("notes 取首个", rows.some((r) => r.label === "提示" && r.value === "note1"));
ok("别名行 icon 走 warn", rows[3].icon === "#i-warn");

// 多项: #n 前缀; 非别名分支; 未知 form 回落
rows = DM._relocateConfirmRows.call(ctx, rcpt([
  item(),
  item({ form: "file_links", reasons: [], notes: [] }),
  item({ form: "mystery", reasons: [], notes: [] }),
]));
ok("多项 #n 前缀(#1/#2/#3 同 label 不撞键)",
   rows.some((r) => r.label === "#1 迁移形态") && rows.some((r) => r.label === "#2 迁移形态") &&
   rows.some((r) => r.label === "#3 迁移形态"));
ok("非别名分支: 未来种子=不受影响(只链接现有文件)",
   rows.some((r) => r.label === "#2 未来种子" && /不受影响/.test(r.value) &&
                    /以后新增的种子仍按各自保存路径落盘/.test(r.value)));
ok("未知 form 回落 String(form)", rows.some((r) => r.label === "#3 迁移形态" && r.value === "mystery"));
ok("无 reasons/notes 的项不加行", !rows.some((r) => r.label === "#2 原因" || r.label === "#2 提示"));

// 非 confirm 项过滤 + 空结果
ok("cls!=confirm 的项被过滤",
   DM._relocateConfirmRows.call(ctx, rcpt([item({ cls: "ok" })])).length === 0);
ok("空/缺 truth -> 空行表", DM._relocateConfirmRows.call(ctx, {}).length === 0 &&
   DM._relocateConfirmRows.call(ctx, { truth: { results: [] } }).length === 0);

// ---- submitMoveDialog confirm 回路(桩驱动) ----
const mkMoveCtx = (script) => {
  // script: { first, gate, second } —— first/second 为投递返回值, gate 为确认框结果;
  // 返回 "confirm" 时按真 _editPost 契约挂 _pendingRelocateConfirm(在途回执)。
  const c = Object.assign({}, DM, {
    moveBusy: false, moveOpen: true, movePathInput: "R:/dst",
    moveSingleHash: "H1", moveTargets: { groupKeys: [], memberHashes: ["H1"] }, moveScope: "",
    movePathMenu: false, movePathHi: -1,
    _pendingRelocateConfirm: null,
    posts: [], toasts: [], gates: 0,
  });
  c.$nextTick = (fn) => fn();
  c.$refs = {};
  c.toast = (msg, kind) => c.toasts.push({ msg, kind });
  c.loadMoveOptions = () => {};
  // issue 26-11-11-0633: openMoveDialog 开框时补拉 flags —— 本电池只验确认回路, 计数替身
  c.ensureWebFlags = () => { c.ensures = (c.ensures || 0) + 1; };
  c._relocateConfirmGate = async () => { c.gates += 1; return script.gate; };
  const postImpl = (via, confirm) => {
    c.posts.push({ via, confirm, location: c.movePathInput });
    const rv = confirm ? script.second : script.first;
    if (rv === "confirm") c._pendingRelocateConfirm = { truth: { summary: { confirm: 1 } } };
    return rv;
  };
  c._editPost = async (hash, action, body) => postImpl("single", !!body.confirm);
  c._bulkEditPost = async (targets, action, body) => postImpl("bulk", !!body.confirm);
  return c;
};
const msgs = (c) => c.toasts.map((t) => t.msg).join("|");

(async () => {
  // 1. 完整确认回路: 首发零副作用 "confirm" -> 收框 -> 确认 -> confirm=true 重发 -> 成功收口
  let c = mkMoveCtx({ first: "confirm", gate: true, second: true });
  await c.submitMoveDialog();
  ok("回路 1: 两次投递(首发无 confirm, 重发带 confirm=true)",
     c.posts.length === 2 && c.posts[0].confirm === false && c.posts[1].confirm === true &&
     c.posts[1].location === "R:/dst" && c.posts.every((p) => p.via === "single"));
  ok("回路 1: 确认框只开一次, 成功后框收不再重开", c.gates === 1 && c.moveOpen === false);
  ok("回路 1: 在途回执被消费清空", c._pendingRelocateConfirm === null && c.moveBusy === false);

  // 2. 取消: 确认框 false -> 不重发, 带原路径重开
  c = mkMoveCtx({ first: "confirm", gate: false, second: true });
  await c.submitMoveDialog();
  ok("回路 2: 取消只投递一次(零副作用不重发)", c.posts.length === 1 && c.posts[0].confirm === false);
  ok("回路 2: 带原路径重开设定位置框", c.moveOpen === true && c.movePathInput === "R:/dst"
     && c.ensures === 1);  // 重开走 openMoveDialog -> flags 惰性补拉挂点(issue 26-11-11-0633), 计数钉住回归面

  // 3. 再 confirm 仍 "confirm"(后端仍在等确认): warn + 重开, 不误报成功
  c = mkMoveCtx({ first: "confirm", gate: true, second: "confirm" });
  await c.submitMoveDialog();
  ok("回路 3: 二发仍 confirm -> warn + 重开(两次投递)",
     c.posts.length === 2 && c.moveOpen === true && c.ensures === 1 &&
     /迁移未发起.*仍在等确认/.test(msgs(c)));

  // 4. 一次成功不经确认框; 5. 批量路径走 _bulkEditPost
  c = mkMoveCtx({ first: true, gate: true, second: true });
  await c.submitMoveDialog();
  ok("一次成功: 单次投递 + 收框(确认框不开)", c.posts.length === 1 && c.gates === 0 && c.moveOpen === false);
  c = mkMoveCtx({ first: true, gate: true, second: true });
  c.moveSingleHash = null;
  await c.submitMoveDialog();
  ok("批量目标走 _bulkEditPost", c.posts.length === 1 && c.posts[0].via === "bulk");

  // 6. 空路径拒发
  c = mkMoveCtx({ first: true, gate: true, second: true });
  c.movePathInput = "   ";
  await c.submitMoveDialog();
  ok("空路径拒发(warn + 零投递)", c.posts.length === 0 && /路径不能为空/.test(msgs(c)));
})().then(() => {
  console.log(JSON.stringify({
    ok: checks.filter((x) => x[1]).length, total: checks.length,
    failed: checks.filter((x) => !x[1]).map((x) => x[0]),
  }));
}).catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

# R5#68: 抽屉面板高度夹取纯函数 ----------------------------------------------------------------
_NODE_CLAMP_PROBE = r"""
const fs = require("fs");
global.window = { AQB_DRAWER_TPL_REG: { helpers: {} } };
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_DRAWER;");
const DM = globalThis.__W2__.methods;
const clamp = (px, vh) => DM._drawerClampHeight.call(Object.assign({}, DM), px, vh);

const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// 1. 240 下界(vh=1000: max=700)
ok("px<240 提到下界 240", clamp(100, 1000) === 240 && clamp(0, 1000) === 240 && clamp(-50, 1000) === 240);
ok("区间内原值返回", clamp(500, 1000) === 500 && clamp(700, 1000) === 700);
// 2. 70vh 上界
ok("px>max 压到 70vh 上界", clamp(1000, 1000) === 700 && clamp(99999, 1000) === 700);
ok("上界随视口取整(round(vh*0.7)): 999*0.7=699.3 -> 699", clamp(99999, 999) === 699);
// 3. 极小视口: 70vh<240 时 min/max 互换, 区间保持合法且不越过 70vh 红线
ok("vh=342(max=239): 上下界同为 239, 两侧输入夹到同一值",
   clamp(100, 342) === 239 && clamp(5000, 342) === 239);
ok("vh=200(max=140): px 双向夹到 140", clamp(50, 200) === 140 && clamp(1000, 200) === 140);
ok("vh=343(max=240): 恰在 240 红线上, 双向夹 240", clamp(100, 343) === 240 && clamp(1000, 343) === 240);
// 4. 取整(落盘值不带亚像素尾数)
ok("亚像素输入取整", clamp(500.4, 1000) === 500 && clamp(500.6, 1000) === 501);
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#148: 迁移路径链浮窗行为(vm 桩) ------------------------------------------------------------
_NODE_REL_CHAIN_PROBE = r"""
const fs = require("fs"), vm = require("vm");
const listeners = [];
const popInner = { nodeType: 1 };
const pop = { nodeType: 1, contains: (t) => t === popInner, focus() {} };
const sandbox = {
  window: { innerWidth: 1024, innerHeight: 800,
            addEventListener: (t, fn, cap) => listeners.push({ t, fn, cap: !!cap }) },
  console,
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), sandbox);
const RC = sandbox.window.AQB_RELOCATE_CHAIN;
const M = RC.methods;
const settle = async (n = 5) => { for (let i = 0; i < n; i++) await new Promise((r) => setTimeout(r, 0)); };

const mkCtx = () => {
  const pending = [];
  const calls = [];
  const c = Object.assign({}, M, {
    relChain: RC.data().relChain,
    $refs: { relChainPop: pop },
    $nextTick: (fn) => fn(),
  });
  c.api = async (url) => new Promise((res) => { calls.push(url); pending.push({ url, res }); });
  c.pending = pending;
  c.calls = calls;
  return c;
};
const anchorOf = (o, focusCalls) => ({ focusCalls: focusCalls || 0,
  focus() { this.focusCalls += 1; },
  getBoundingClientRect: () => Object.assign({ left: 0, top: 0, width: 100, height: 40, right: 100, bottom: 40 }, o) });

const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

(async () => {
  // ---- ctx1: 开关翻转 / seq 代际守卫 / 滚动与 resize 即关(全局监听只挂一次, 归 ctx1) ----
  const opener = anchorOf({ left: 600, top: 60, width: 200, bottom: 100 });
  const c1 = mkCtx();
  c1.relChainOpen("A", opener);
  ok("1. 开浮窗: open/hash/subtitle/loading 置位", c1.relChain.open === true && c1.relChain.hash === "A" &&
     c1.relChain.loading === true && c1.relChain.subtitle === "A");
  ok("1. 取数 URL 只带 hash(客户端零探测, 服务端派生起点)", c1.calls.length === 1 &&
     c1.calls[0] === "/api/relocate/chain?hash=A");
  ok("1. seq 自增", c1.relChain.seq >= 1);
  const sc = listeners.find((l) => l.t === "scroll");
  const rz = listeners.find((l) => l.t === "resize");
  ok("1. 全局监听已挂: scroll capture + resize", !!sc && sc.cap === true && !!rz);

  c1.relChainOpen("A", opener);
  ok("1. 同 hash 再开即关(开/关翻转) + 焦点回落触发钮", c1.relChain.open === false && opener.focusCalls === 1);
  c1.relChainOpen("A", opener);
  ok("1. 关后再开重开浮窗", c1.relChain.open === true && c1.relChain.hash === "A");

  // 2. A 慢响应落袋不覆写 B(seq 代际守卫)
  const seqBefore = c1.relChain.seq;
  c1.relChainOpen("B", opener);
  ok("2. 换 hash 重开: hash=B, loading, seq 再自增",
     c1.relChain.hash === "B" && c1.relChain.loading === true && c1.relChain.seq > seqBefore);
  const aRes = c1.pending[c1.pending.length - 2].res;   // A 的响应(B 之前挂起的那笔)
  aRes({ nodes: [{ path: "A-chain" }], cached: false });
  await settle();
  ok("2. A 慢响应被 seq 守卫丢弃: data 不被旧响应覆写",
     c1.relChain.data === null && c1.relChain.loading === true && c1.relChain.hash === "B");
  ok("2. B 的取数已发出", c1.calls[c1.calls.length - 1] === "/api/relocate/chain?hash=B");
  c1.pending[c1.pending.length - 1].res({ nodes: [{ path: "B-chain" }], cached: true });
  await settle();
  ok("2. B 响应落袋: data= B, loading 收口", c1.relChain.data && c1.relChain.data.nodes[0].path === "B-chain" &&
     c1.relChain.loading === false && c1.relChain.data.cached === true);

  // 3. 关闭后到达的响应同样丢弃(代际 + open 双守卫)
  c1.relChainClose();
  c1.relChainOpen("C", opener);
  c1.relChainClose();
  c1.pending[c1.pending.length - 1].res({ nodes: [{ path: "C-chain" }] });
  await settle();
  ok("3. 关闭后响应不落袋", c1.relChain.data === null && c1.relChain.open === false);

  // 5. 滚动即关(capture; 浮窗内部滚动/浮窗自身不关) + resize 即关
  c1.relChainOpen("A", opener);
  const focusBefore = opener.focusCalls;
  sc.fn({ target: { nodeType: 1 } });
  ok("5. 外部滚动即关(强制收口, 不回焦)", c1.relChain.open === false && opener.focusCalls === focusBefore);
  c1.relChainOpen("A", opener);
  sc.fn({ target: popInner });
  ok("5. 浮窗内部滚动不关(长链滚得动)", c1.relChain.open === true);
  sc.fn({ target: pop });
  ok("5. 目标即浮窗自身不关", c1.relChain.open === true);
  rz.fn();
  ok("5. resize 即关", c1.relChain.open === false);

  // 6. refresh: loading 中不重取; 空闲时带 refresh=1
  c1.relChainOpen("A", opener);
  c1.relChainRefresh();
  ok("6. loading 中不重取", c1.calls.filter((u) => u.includes("refresh=1")).length === 0);
  c1.pending[c1.pending.length - 1].res({ nodes: [] });
  await settle();
  c1.relChainRefresh();
  ok("6. 空闲刷新带 refresh=1", c1.calls[c1.calls.length - 1] === "/api/relocate/chain?hash=A&refresh=1");

  // ---- 4. relChainPlace 四向定位(独立 ctx) ----
  const c2 = mkCtx();
  c2.relChain.open = true;
  c2.relChain.hash = "A";
  c2.relChainPlace(anchorOf({ left: 600, width: 200, top: 60, bottom: 100 }));
  ok("4. 锚下方: left=r.right-width, top=r.bottom+8",
     c2.relChain.left === 340 && c2.relChain.top === 108 && c2.relChain.width === 460);
  c2.relChainPlace(anchorOf({ left: 0, width: 50, top: 300, bottom: 340 }));
  ok("4. 左越界夹到 pad", c2.relChain.left === 8);
  c2.relChainPlace(anchorOf({ left: 900, width: 200, top: 60, bottom: 100 }));
  ok("4. 右越界夹到 vw-width-pad", c2.relChain.left === 1024 - 460 - 8);
  c2.relChainPlace(anchorOf({ left: 600, width: 200, top: 380, bottom: 392 }));
  ok("4. 下方放得下不翻面", c2.relChain.top === 400);
  sandbox.window.innerHeight = 400;   // 极矮视口: top+360 超界 -> 翻到锚上方
  c2.relChainPlace(anchorOf({ left: 600, width: 200, top: 380, bottom: 392 }));
  ok("4. 下方放不下翻上方(max(pad, r.top-360))", c2.relChain.top === 20);
  sandbox.window.innerHeight = 800;
  c2.relChainPlace(null);
  ok("4. 无锚居中", c2.relChain.left === Math.max(8, (1024 - 460) / 2) &&
     c2.relChain.top === Math.max(8, (800 - 400) / 2));
  c2.relChain.open = false;
  c2.relChainPlace(anchorOf({ left: 600, width: 200, bottom: 100 }));
  ok("4. 关着不定位(零写入)", c2.relChain.left === Math.max(8, (1024 - 460) / 2) &&
     c2.relChain.top === Math.max(8, (800 - 400) / 2));
})().then(() => {
  console.log(JSON.stringify({
    ok: checks.filter((x) => x[1]).length, total: checks.length,
    failed: checks.filter((x) => !x[1]).map((x) => x[0]),
  }));
}).catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""


def test_r4_share_limits_sentinel():
    """R5#60(major) 修复回归: editShareLimits 哨兵 -2 与后端 commands_limit.py 对齐 + 校验域 + 文案"""
    report = _run_probe(_NODE_SHARE_LIMITS_PROBE, bundle_file("drawer.js"))
    _assert_battery(report, "分享率哨兵电池")


def test_r4_drawer_del_receipt_close():
    """R5#61 修复回归: drawerDel 按删除回执 ok 收口且只收同一 hash 的抽屉 + _deleteFlow 回执契约"""
    report = _run_probe(_NODE_DRAWER_DEL_PROBE, bundle_file("drawer.js"), _shared_path("delete_flow.js"))
    _assert_battery(report, "抽屉删除回执收口电池")


def test_r4_deco_fingerprint_pair():
    """R5#56: 装饰记忆化指纹对 build->hit 往返(未脏行必命中 / 逐槽必失配 / 还原复命中)"""
    report = _run_probe(_NODE_DECO_FP_PROBE, _shared_path("decorate.js"))
    _assert_battery(report, "装饰指纹对电池")


def test_r4_delete_details_rows():
    """R5#145: 删除确认框行拼装(_hrRiskOf danger 点名/名字截 3 + _deleteDetails 去重与条件行)"""
    report = _run_probe(_NODE_DELETE_DETAILS_PROBE, _shared_path("delete_flow.js"))
    _assert_battery(report, "删除明细行电池")


def test_r4_relocate_confirm_rows():
    """R5#69: _relocateConfirmRows/_relocateConfirmCount 纯函数 + submitMoveDialog confirm 回路桩驱动"""
    report = _run_probe(_NODE_RELOCATE_CONFIRM_PROBE, bundle_file("drawer.js"))
    _assert_battery(report, "迁移确认回路电池")


def test_r4_drawer_clamp_height():
    """R5#68: _drawerClampHeight 边界(240 下界 / 70vh 上界 / 极小视口 min-max 互换 / 取整)"""
    report = _run_probe(_NODE_CLAMP_PROBE, bundle_file("drawer.js"))
    _assert_battery(report, "面板高度夹取电池")


def test_r4_relocate_chain_popover():
    """R5#148: 路径链浮窗行为(vm 桩): 开关翻转 / seq 代际守卫 / relChainPlace 四向定位 / 滚动即关"""
    report = _run_probe(_NODE_REL_CHAIN_PROBE, _shared_path("relocate_chain.js"))
    _assert_battery(report, "路径链浮窗电池")


def test_r4_emptyhost_deadvar_gone():
    """R5#62: emptyHost 死变量删除后不回潮; 换代守卫注释与现状对齐(摘桥路径兜住)"""
    js = read_shared("drawer_templates.js")
    assert "emptyHost" not in js, "emptyHost 死变量回潮(赋值后零读者)"
    assert "var _k in old" not in js, "死变量配套的空遍历残留"
    # 注释不再声称「old 空 => 必须换代」的判别在本循环实现; 指名 _dtUnmountOne 摘桥兜住
    assert "_dtUnmountOne 摘桥兜住" in js, "换代守卫注释须与现状对齐(指名 _dtUnmountOne 摘桥路径)"
    # 现行换代判据(同 seg 锚元素被换)保持原样
    assert "old[s] !== seen[t][s]" in js, "同 seg 锚元素被换的换代判据不得被误删"
