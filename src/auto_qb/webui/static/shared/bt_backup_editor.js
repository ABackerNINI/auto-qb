/* auto-qb WEB UI · 设置页「整组迁移」块的 BT_backup 路径表编辑器(计划 26-11-07-0708 S2)
 *
 * 分工(与 transfer_targets.js 一致的分层):
 *   本文件                     行为层: 读 config.bt_backup 映射 -> 用户编辑 -> 整对象替换写回配置树
 *   tpl/bt-backup-editor.html  x-template(aq-bt-backup-editor 组件, into: body): 只摆行表与控件
 *   tpl/settings-detail.html   通用分区分支 config.relocate 块内一行挂载(v-if 按 b.key 定位)
 *
 * 草稿不另存(与 transfer_targets.js 同一结论):
 *   编辑直接落在 cfg.tree.config.bt_backup 上 —— 面板显示的永远是"当前草稿"本身, 不存在
 *   「面板草稿」与「配置树」两份真值。脏标记由 cfgDirty(全树 JSON 对比 baseline)自动接管,
 *   保存走全局 cfgSave(无独立保存钮), 放弃走全局 cfgDiscard —— 与其它配置项一字不差的语义。
 *   写回一律**整对象替换**(cfgSetPath 重写整个映射): 不给"深层新增键没触发渲染"留任何理论缝隙。
 *   映射变成空时**删键**而不是写空对象: 空容器与键缺失不同构, 全树 JSON 对比的脏标记认它是
 *   改动(勾了再取消脏标记消不掉, 见 config-field-unexpressable 坑档); 后端空映射与缺省同义
 *   (_validate_bt_backup: spec None = 未配置 = fastresume 收尾整体未启用)。
 *
 * 树形状(与磁盘 YAML 同构, 标量全为字符串 —— yaml.BaseLoader 语义):
 *   config.bt_backup = { "<host:port>": "<该实例 BT_backup 目录路径>", ... }
 *   键 = qB 连接身份(与 qbittorrent 连接配置的 host/port 一致, 端口 1-65535), 值 = 非空路径字符串。
 *   合法性全由后端 validate_config 聚合把关(保存 400 拦下, 报错经 cfg.saveError 展开),
 *   前端不做平行校验(两份规则必漂移)。本文件**唯一的拦截**是编辑面机制而非校验:
 *   映射是 dict, 表达不了两条同键行 —— 空键行已存在时拒新增、改名撞已有键时拒写
 *   (写前把树按行序原样重挂一次, 输入框弹回树真值), 都用 toast 说明原因。
 *
 * 无视图态: 行常显、无展开/测试连接等交互流, 不像 trTgt 那样需要在 state.js 落视图态。
 *
 * !装载序: 四套 index.html 清单里本文件紧跟 transfer_targets.js 之后、app.js 之前(app.js 末尾
 *   app.mixin 注入, 启动时要读 window.AQB_*)。组件件 AQ_BT_BACKUP_EDITOR_COMPONENT 与
 *   transfer_targets.js 同款纯模板件: 模板在 x-template, 数据与动作经 $root 回调根实例,
 *   组件里不写任何方法(重名会被合并盖掉且不报错, _scan_mixin_wiring 钉这种形态)。
 * !无顶层 const: 只挂 window.AQB_BT_BACKUP_EDITOR / window.AQ_BT_BACKUP_EDITOR_COMPONENT
 *   两个全局(经典 script 共享全局词法作用域, 顶层 const 跨文件撞名即整包 SyntaxError)。
 */

window.AQB_BT_BACKUP_EDITOR = {
  computed: {
    /* 行模型(读侧单点): 映射 -> [{key, value}] 行数组(保持映射的键序); 无配置段 = 空数组。
     * 值统一 String 化(YAML 树里标量全为字符串, 数字残留只在手编 YAML 时出现, 显示面归一) */
    bbRows() {
      const t = this.cfgConfig().bt_backup;
      if (!t || typeof t !== "object" || Array.isArray(t)) return [];
      return Object.keys(t).map((k) => ({ key: k, value: String(t[k] === null || t[k] === undefined ? "" : t[k]) }));
    },
  },
  methods: {
    /* ---------------------------------------------------------- 读写地基 */
    /* 映射写回单点: 非空按行序整对象替换 config.bt_backup; 空 = 删键回到"未配置"
     * (与 ttPersist / cfgItemRemove 的「空集合即删键」同口径, 理由见文件头注释) */
    bbPersist(rows) {
      if (!rows.length) {
        this.cfgDelPath(["config", "bt_backup"]);
        return;
      }
      const map = {};
      for (const r of rows) map[r.key] = r.value;
      this.cfgSetPath(["config", "bt_backup"], map);
    },
    bbAdd() {
      const rows = this.bbRows;
      if (rows.some((r) => r.key === "")) {
        this.toast("先填上一行的实例地址: host:port 是每行的唯一标识, 补全后再新增", "timeout", 6000);
        return;
      }
      this.bbPersist(rows.concat([{ key: "", value: "" }]));
    },
    bbSetKey(i, value) {
      const rows = this.bbRows;
      if (!rows[i] || rows[i].key === value) return;
      if (rows.some((r, j) => j !== i && r.key === value)) {
        /* 撞键: 不写树(写了会把两行折叠成一行 = 静默丢数据), 原样重挂把输入框弹回树真值 */
        this.bbPersist(rows);
        this.toast("实例地址重复: 每行的 host:port 必须唯一, 请换一个未用过的", "timeout", 6000);
        return;
      }
      rows[i] = { key: value, value: rows[i].value };
      this.bbPersist(rows);
    },
    bbSetValue(i, value) {
      const rows = this.bbRows;
      if (!rows[i] || rows[i].value === value) return;
      rows[i] = { key: rows[i].key, value: value };
      this.bbPersist(rows);
    },
    bbRemove(i) {
      const rows = this.bbRows.slice();
      if (!rows[i]) return;
      rows.splice(i, 1);
      this.bbPersist(rows);  // 删到空 = 整段删键(= 未启用), 无确认(与通用列表行 cfgItemRemove 同口径)
    },
  },
};

/* 组件壳(traffic_card.js / transfer_targets.js 同款纯模板件): 模板在 tpl/bt-backup-editor.html
 * 的 x-template, 数据与动作经 $root 回调根实例 —— 这里不定义任何方法/数据。inject/provide 透传
 * 不可省: 全局 mixin 给每个组件都挂 provide(){ce:this}, 不透传则块内注入到的 ce 是本组件实例。 */
window.AQ_BT_BACKUP_EDITOR_COMPONENT = {
  name: "aq-bt-backup-editor",
  inject: ["ce"],
  provide() {
    return { ce: this.ce };
  },
  template: "#tpl-aq-bt-backup-editor",
};
