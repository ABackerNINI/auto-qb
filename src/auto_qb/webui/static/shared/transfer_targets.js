/* auto-qb WEB UI · 设置页「WebUI」卡的种子转移目标编辑器(计划 26-10-31-0306 W1/T5)
 *
 * 分工(与 ctx_menu_custom.js 一致的分层):
 *   本文件                    目标编辑器的**行为层**: 读 targets -> 用户编辑 -> 整对象替换写回配置树
 *   tpl/transfer-targets.html x-template(aq-transfer-targets 组件, into: body): 只摆表格与控件
 *   tpl/settings-detail.html  <template v-else-if="hub.view === 'webui'"> 里一行挂载
 *
 * 草稿不另存(与 ctx_menu_custom.js 同一结论):
 *   编辑直接落在 cfg.tree.config.web.transfer 上 —— 面板显示的永远是"当前草稿"本身, 不存在
 *   「面板草稿」与「配置树」两份真值。脏标记由 cfgDirty(全树 JSON 对比 baseline)自动接管,
 *   保存走全局 cfgSave(无独立保存钮), 放弃走全局 cfgDiscard —— 与其它配置项一字不差的语义。
 *   写回一律**整对象替换**(this.cfg.tree.config.web = {...}): Vue 3 对新增键也能追踪, 但整对象
 *   替换是既有教训的共同结论(flags 下发 / ctx_menu 初值 / 定制面板) —— 不给"深层新增键没触发
 *   渲染"留任何理论缝隙。targets 变成空列表时**删键**而不是写空列表: 空容器与键缺失不同构,
 *   全树 JSON 对比的脏标记认它是改动(勾了再取消脏标记消不掉, 见 config-field-unexpressable 坑档);
 *   后端空 targets 与缺省同义(TransferConfig() = 未配置任何目标)。
 *
 * 树形状(与磁盘 YAML 同构, 标量全为字符串 —— yaml.BaseLoader 语义):
 *   config.web.transfer.targets = [ { name, type("qb"|"tr"), base_url, username, password,
 *     enabled("true"/"false"), after_state("keep"|"paused"), skip_check("true"/"false"),
 *     fields: { <字段键>: "true"/"false" }, path_map: [ {from, to}, ... ] }, ... ]
 *   合法性全由后端 validate_config 聚合把关(保存 400 拦下), 前端不做平行校验(两份规则必漂移)。
 *
 * 密码处理(计划 D4: 明文落 config.yml, UI 遮显):
 *   树里 targets[].password 是明文, 但**绝不回显** —— 输入框恒显空串, 占位符只提示"已设置/未设置";
 *   键入即整值写树(留空不动键 = 不修改)。自动填充三件套照抄 xtpl.html 密码分支(2026-10-20 报障):
 *   表单形状(隐藏 username + password) + autocomplete="new-password" + 非焦点 input 事件不写树。
 *
 * 测试连接: 走 POST /api/transfer/test(经 cmd 管线回执, 与 bulk 同族); 目标必须**已保存**
 * (树与磁盘一致, 即 !cfgDirty)—— 后端按名字从实时配置里找目标, 未保存的新目标找不到。
 *
 * !装载序: 三份 index.html 清单里本文件排在 ctx_menu_custom.js 之后、app.js 之前(app.js 末尾
 *   app.mixin 注入, 启动时要读 window.AQB_*)。组件件 AQ_TRANSFER_TARGETS_COMPONENT 与
 *   traffic_card.js 同款纯模板件: 模板在 x-template, 数据与动作经 $root 回调根实例,
 *   组件里不写任何方法(重名会被合并盖掉且不报错, _scan_mixin_wiring 钉这种形态)。
 * !与 commands.js / config_editor.js 同款顶层展开形态(无 IIFE 包裹): 守阵
 *   test_webui_trigger_registry 从 4 空格缩进的方法声明定位 POST 调用点归属, IIFE 深一层
 *   缩进会让调用点变"无主"。顶层 const 全部 TT_ 前缀(跨文件撞名守阵按名单对账, 无重名)。
 */

/* per-target 字段集(UI 展示序): 键面单点对应后端 src/auto_qb/config/models.py 的
 * TRANSFER_FIELD_KEYS(元组逐位同序), 默认值对应 default_transfer_fields ——
 * "除超级做种外全开、保存路径锁死必开"。守阵 test_transfer_targets_editor.py 从
 * models.py 提取该元组与 default 逐位核对本表, 两处漂移当场红。
 * locked: 保存路径锁死必开(同机硬约束: 关掉 = 目标侧数据不可达, 后端校验拒绝 false) ——
 * UI 置灰禁编辑; defOff: 高危项新建默认关(超级做种)。 */
const TT_FIELDS = [
  { key: "save_path", label: "保存路径", locked: true },
  { key: "category", label: "分类" },
  { key: "tags", label: "标签" },
  { key: "share_ratio_limit", label: "分享率限制" },
  { key: "seeding_time_limit", label: "做种时长限制" },
  { key: "up_limit", label: "上行限速" },
  { key: "down_limit", label: "下行限速" },
  { key: "super_seeding", label: "超级做种", defOff: true },
];

/* 新建目标模板的字段默认(单点推导: locked 或非 defOff = 开) —— 对应后端
 * default_transfer_fields({key: key != "super_seeding"}), 不手抄第二份布尔表 */
function ttDefaultFields() {
  const out = {};
  for (const f of TT_FIELDS) out[f.key] = f.defOff ? "false" : "true";
  return out;
}

const TT_TYPE_LABELS = { qb: "qBittorrent", tr: "Transmission(预留)" };

/* 挂 window 供守阵探针(test_transfer_targets_editor.py)与未来复用方读取:
 * 与后端 TRANSFER_FIELD_KEYS 的逐位对账就从这里取, 不用正则剖 JS 源码。 */
window.AQB_TRANSFER_FIELDS = TT_FIELDS;
/* 类型展示名同款挂载(T7 确认弹窗的「目标」行复用, 不抄第二份标签表) */
window.AQB_TRANSFER_TYPE_LABELS = TT_TYPE_LABELS;

window.AQB_TRANSFER_TARGETS = {
  computed: {
    /* 首页卡读数与编辑器共用的目标列表(读侧单点; 无配置段 = 空数组) */
    ttList() {
      const t = this.cfgConfig().web && this.cfgConfig().web.transfer;
      const raw = t && typeof t === "object" && !Array.isArray(t) ? t.targets : null;
      return Array.isArray(raw) ? raw : [];
    },
  },
  methods: {
    /* ---------------------------------------------------------- 读写地基 */
    /* targets 写回单点: 非空整对象替换 config.web.transfer; 空 = 删键回到"未配置"(与
     * toggleKey/cfgItemRemove 的「空列表即删键」同口径, 理由见文件头注释) */
    ttPersist(targets) {
      const web = Object.assign({}, this.cfgConfig().web || {});
      if (targets.length) web.transfer = { targets: targets };
      else delete web.transfer;
      this.cfg.tree.config.web = web;
    },
    /* 新建目标模板(计划 §03 字段集表): 字段默认见 ttDefaultFields; enabled 默认关
     * (保守默认, 转移是高风险动作); path_map 缺省不写键(空 = 原样, 零残留) */
    ttTemplate() {
      return {
        name: "",
        type: "qb",
        base_url: "",
        username: "",
        password: "",
        enabled: "false",
        after_state: "keep",
        skip_check: "true",
        fields: ttDefaultFields(),
      };
    },
    ttFields() {
      return TT_FIELDS;
    },
    /* 首页「WebUI」卡读数段: 无目标 = 空串(不占读数), 有目标 = 数量 */
    ttCardReadout() {
      return this.ttList.length ? this.ttList.length + " 个转移目标" : "";
    },
    ttTypeLabel(type) {
      return TT_TYPE_LABELS[type] || type || "qb";
    },
    /* 字段开关真值: 树是原始 YAML(缺键合法), 缺键回退新建模板默认 —— 与后端 loader
     * _load_transfer_target 的"缺失键补模板默认"同口径, 不复制第二份规则 */
    ttFieldOn(target, key) {
      const fields = target && target.fields && typeof target.fields === "object" ? target.fields : {};
      if (fields[key] === undefined) return key !== "super_seeding";
      return this.cfgTruthy(fields[key]);
    },
    ttOn(target, key) {
      return this.cfgTruthy(target ? target[key] : false);
    },
    ttName(target) {
      return String((target && target.name) || "").trim();
    },
    ttHasSecret(target) {
      return !!(target && String(target.password || "") !== "");
    },
    /* 密码输入框占位: 只提示状态, 绝不回显已存值 */
    ttSecretPlaceholder(target) {
      return this.ttHasSecret(target) ? "已设置, 留空 = 不修改" : "未设置";
    },

    /* ---------------------------------------------------------- 列表与编辑器 */
    ttPanelEnter() {
      this.trTgt.edit = -1;
      this.trTgt.test = null;
      this.trTgt.testing = "";
    },
    ttAdd() {
      const targets = this.ttList.slice();
      targets.push(this.ttTemplate());
      this.ttPersist(targets);
      this.trTgt.edit = targets.length - 1;  // 新目标展开编辑器直接填
      this.trTgt.test = null;
    },
    ttToggleEditor(i) {
      this.trTgt.edit = this.trTgt.edit === i ? -1 : i;
      this.trTgt.test = null;
    },
    async ttRemove(i) {
      const targets = this.ttList.slice();
      const t = targets[i];
      if (!t) return;
      const name = this.ttName(t) || "(未命名)";
      const ok = await this.confirmDialog(
        "删除转移目标「" + name + "」",
        "将从配置中移除这个目标下载器(包括它的字段集与路径映射)。已保存后立即生效; 未保存的改动可「放弃改动」找回。",
        { okText: "删除", danger: true }
      );
      if (!ok) return;
      targets.splice(i, 1);
      this.ttPersist(targets);
      // 编辑器开在本行或其后各行: 下标整体左移一位; 开在别行不动
      if (this.trTgt.edit === i) this.trTgt.edit = -1;
      else if (this.trTgt.edit > i) this.trTgt.edit -= 1;
      if (this.trTgt.test && this.trTgt.test.name === this.ttName(t)) this.trTgt.test = null;
      this.toast("已移除「" + name + "」, 保存后生效", "ok", 3500);
    },
    /* 整行替换写回(拷贝 targets 数组再按下标换行 —— 不原地改, 整对象替换是响应式单点) */
    ttReplace(i, next) {
      const targets = this.ttList.slice();
      if (!targets[i]) return;
      targets[i] = next;
      this.ttPersist(targets);
    },
    /* 单目标补丁写回(ttReplace 的浅补丁形态) */
    ttPatch(i, patch) {
      const t = this.ttList[i];
      if (!t) return;
      this.ttReplace(i, Object.assign({}, t, patch));
    },
    ttSet(i, key, value) {
      this.ttPatch(i, { [key]: value });
    },
    ttSetEnabled(i, v) {
      this.ttPatch(i, { enabled: v ? "true" : "false" });
    },
    ttSetSkip(i, v) {
      this.ttPatch(i, { skip_check: v ? "true" : "false" });
    },
    ttSetField(i, key, on) {
      const t = this.ttList[i];
      if (!t) return;
      const fields = Object.assign(
        {},
        t.fields && typeof t.fields === "object" ? t.fields : {},
        { [key]: on ? "true" : "false" }
      );
      this.ttPatch(i, { fields: fields });
    },

    /* ---------------------------------------------------------- 路径映射规则表 */
    ttMapRows(target) {
      const rows = target ? target.path_map : null;
      return Array.isArray(rows) ? rows : [];
    },
    ttMapAdd(i) {
      const t = this.ttList[i];
      if (!t) return;
      const rows = this.ttMapRows(t).slice();
      rows.push({ from: "", to: "" });
      this.ttPatch(i, { path_map: rows });
    },
    ttMapDel(i, j) {
      const t = this.ttList[i];
      if (!t) return;
      const rows = this.ttMapRows(t).slice();
      if (j < 0 || j >= rows.length) return;
      rows.splice(j, 1);
      const next = Object.assign({}, t);
      if (rows.length) next.path_map = rows;
      else delete next.path_map;  // 清空 = 回到"未配置"(键缺失), 不留空列表噪音(见文件头注释)
      this.ttReplace(i, next);
    },
    /* ↑↓: 表序即优先级(首条命中生效), 只换位置不改内容 */
    ttMapMove(i, j, delta) {
      const t = this.ttList[i];
      if (!t) return;
      const rows = this.ttMapRows(t).slice();
      const k = j + delta;
      if (j < 0 || k < 0 || k >= rows.length) return;
      const tmp = rows[j];
      rows[j] = rows[k];
      rows[k] = tmp;
      this.ttPatch(i, { path_map: rows });
    },
    ttMapSet(i, j, side, value) {
      const t = this.ttList[i];
      if (!t) return;
      const rows = this.ttMapRows(t).slice();
      if (!rows[j]) return;
      rows[j] = Object.assign({}, rows[j], { [side]: value });
      this.ttPatch(i, { path_map: rows });
    },

    /* ---------------------------------------------------------- 密码(遮显 + 防自动填充)
     * 三件套照抄 xtpl.html 密码分支(2026-10-20 报障「进常规就脏」):
     * 表单形状由模板出, 这里守"非焦点 input 事件一律不写树"并把显示拉回空串。 */
    ttSecret(ev, i) {
      const el = ev.target;
      if (document.activeElement !== el) {
        el.value = "";
        return;
      }
      this.ttPatch(i, { password: el.value });
    },

    /* ---------------------------------------------------------- 测试连接
     * 只对**已保存**的目标发: 后端按名字从实时配置里找, 未保存的新目标找不到;
     * cfgDirty = 树与磁盘有出入(含改过名字), 一律先保存。 */
    async ttTest(i) {
      const t = this.ttList[i];
      if (!t) return;
      const name = this.ttName(t);
      if (this.cfgDirty) {
        this.toast("有未保存的改动, 请先「保存并应用」再测试连接", "timeout", 6000);
        return;
      }
      if (!name) {
        this.toast("请先填写目标名称并保存, 再测试连接", "timeout", 6000);
        return;
      }
      if (this.trTgt.testing) return;  // 已有一测在途: 不并发(防重复点击)
      this.trTgt.testing = name;
      this.trTgt.test = null;
      try {
        const resp = await this.api("/api/transfer/test", {
          method: "POST",
          body: JSON.stringify({ target_id: name }),
        });
        const r = await this.waitCmd(resp.cmd_id, 40000);
        this.trTgt.test = r.ok
          ? { name: name, ok: true, text: String((r.truth && r.truth.info) || "连接成功") }
          : { name: name, ok: false, text: String(r.error || "测试失败") };
      } catch (e) {
        this.trTgt.test = { name: name, ok: false, text: e.message || "请求失败" };
      } finally {
        this.trTgt.testing = "";
      }
    },
  },
};

/* 组件壳(traffic_card.js 同款纯模板件): 模板在 tpl/transfer-targets.html 的 x-template,
 * 数据与动作经 $root 回调根实例 —— 这里不定义任何方法/数据。inject/provide 透传不可省:
 * 全局 mixin 给每个组件都挂 provide(){ce:this}, 不透传则卡内注入到的 ce 是本组件实例。 */
window.AQ_TRANSFER_TARGETS_COMPONENT = {
  name: "aq-transfer-targets",
  inject: ["ce"],
  provide() {
    return { ce: this.ce };
  },
  template: "#tpl-aq-transfer-targets",
};
