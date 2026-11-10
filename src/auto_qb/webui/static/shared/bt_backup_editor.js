/* auto-qb WEB UI · 设置页「整组迁移」块的 BT_backup 单路径编辑器 + 自动探测(计划 26-11-11-0259 S4)
 *
 * 分工(与 transfer_targets.js 一致的分层):
 *   本文件                     行为层: 读 relocate.bt_backup 标量 -> 用户编辑/探测回填 -> 写回配置树草稿
 *   tpl/bt-backup-editor.html  x-template(aq-bt-backup-editor 组件, into: body): 输入框 + 探测按钮 + 证据区
 *   tpl/settings-detail.html   通用分区分支 config.relocate 块内一行挂载(v-if 按 b.key 定位)
 *
 * 读法2(D3): 「自动探测」按钮是探测的唯一入口 —— 无运行时隐式探测, 无装载期自动请求。
 *   按钮发 POST /api/relocate/bt_backup_probe(无 body, Bearer 随 api() 既有惯例); 端点断连
 *   降级不 503(online=false 继续结构自证, 前端加「未自证」标注), 探测本身零配置写。
 *
 * 草稿不另存(与 transfer_targets.js 同一结论):
 *   编辑直接落在 cfg.tree.config.relocate.bt_backup 上 —— 面板显示的永远是"当前草稿"本身, 不存在
 *   「面板草稿」与「配置树」两份真值。脏标记由 cfgDirty(全树 JSON 对比 baseline)自动接管,
 *   保存走全局 cfgSave(无独立保存钮), 放弃走全局 cfgDiscard —— 与其它配置项一字不差的语义。
 *   schema 的 relocate.bt_backup 打 hidden(S4, 语义 = 组件接管渲染, 与 web.transfer/ctx_menu
 *   同款): 通用编辑树不渲染, 本组件是唯一编辑面 —— 否则同键两个输入框。
 *
 * 树形状(与磁盘 YAML 同构, 标量全为字符串 —— yaml.BaseLoader 语义):
 *   config.relocate.bt_backup = "<qB 的 BT_backup 目录本机路径>"(单实例标量, S1 收编)
 *   留空 = 写空串 = fastresume 收尾未启用(与 S1 校验一致: 空串合法, 空格 strip 后为空亦然);
 *   标量的"空"就是 "" 本身, 不删键。旧顶层 config.bt_backup 映射表及其「整对象替换 / 空映射
 *   删键」写回路径已随 S1 退役, 本文件不再有第二套写法。
 *   合法性全由后端 validate_config 聚合把关(保存 400 拦下, 报错经 cfg.saveError 展开),
 *   前端不做平行校验(两份规则必漂移)。
 *
 * 五态前端行为(计划 §3.2 表; 判定在后端 probe.verdict 单点, 前端只渲染不重判):
 *   hit             回填草稿 + 展示证据; 用户保存才落盘(审计轨迹)。草稿已有值时不覆盖
 *                   (保守默认: 探测不静默丢用户输入), 只提示先清空再采用。
 *   ambiguous       只列全部候选明细; 配置一字不动(D5 拒不猜测)。
 *   miss            列已扫描候选 + 提示手写路径(--profile / 远程 qB 等不可静态探测形态)。
 *   unusable-sqlite 标「不可用」+ 指向 qB 设置(恢复数据存储切回 Legacy); 不回填。
 *   manual-set      提示「已手动配置, 按钮仅供核对」。
 *   offline(online=false) 结果一律加「未自证」标注(hash 自证未参与裁决)。
 *   响应错误(500/网络)在证据区原样展示(e.message 含端点结构化 detail), 不吞。
 *
 * 无持久化视图态: 探测结果只活在内存(bbProbe), 不落任何本地持久化 —— 刷新即回"未探测",
 *   重新点按钮即可; 落盘真值在配置树, 草稿与之同源。
 *
 * !装载序: 四套 index.html 清单里本文件紧跟 transfer_targets.js 之后、app.js 之前(app.js 末尾
 *   app.mixin 注入, 启动时要读 window.AQB_*)。组件件 AQ_BT_BACKUP_EDITOR_COMPONENT 与
 *   transfer_targets.js 同款纯模板件: 模板在 x-template, 数据与动作经 $root 回调根实例,
 *   组件里不写任何方法(重名会被合并盖掉且不报错, _scan_mixin_wiring 钉这种形态)。
 * !无 IIFE 包裹、顶层 const 全部 BB_ 前缀(transfer_targets.js 同款: 跨文件撞名守阵按名单
 *   对账, 无重名); 方法恒 4 空格缩进单行签名(test_webui_trigger_registry 扫描器格式假设)。
 */

/* 五态 -> 用户话术(计划 §3.2「前端行为」列的 UI 落点): 键 = 端点 verdict 字面量, 未知值兜原样。
 * hit 的主行话术按 bbProbe.filled 分流(bbVerdictText): 已回填用本表 "hit" 行; 未回填(草稿已有
 * 值不覆盖)用下方 BB_HIT_KEPT_TEXT —— 主行不得声称「已回填」, 与实际行为矛盾会诱导用户保存。 */
const BB_VERDICT_TEXT = {
  "hit": "已探测到 BT_backup 目录, 已回填到上方输入框(尚未保存, 点「保存并应用」才落盘)",
  "ambiguous": "多个候选合格且无法消歧 —— 未做任何填写, 请核对下方候选后手动填入",
  "miss": "未找到合格的 BT_backup 目录 —— 请手动填写路径",
  "unusable-sqlite": "BT_backup 不可用: qB 的恢复数据存储为 SQLite, fastresume 改写对它无效",
  "manual-set": "已手动配置 BT_backup 路径, 自动探测仅供核对",
};

/* hit 且未回填(草稿已有值, 保守默认不覆盖)的主行话术: 不含「已回填」的中性文案 */
const BB_HIT_KEPT_TEXT = "已探测到 BT_backup 目录 —— 草稿已有值, 探测结果未覆盖";

/* origin 推导渠道 -> 中文(候选明细行展示; 未知值原样) */
const BB_ORIGIN_TEXT = {
  "default-profile": "默认 profile",
  "portable": "便携",
};

window.AQB_BT_BACKUP_EDITOR = {
  data() {
    return {
      /* 探测视图态(内存态, 不持久化): running = 按钮忙; result = 最近一次成功响应(证据区只反映
       * 最近一次探测, 失败即清旧证据); filled = 本次 hit 是否真的回填了(草稿已有值时不回填,
       * 证据区据此区分「已回填」与「保留用户草稿」两种 hit); error = 最近一次失败的结构化文案;
       * seq = 竞态守卫 */
      bbProbe: { running: false, result: null, filled: false, error: "", seq: 0 },
    };
  },
  computed: {
    /* 读侧单点: relocate.bt_backup 标量草稿(无段/无键 = 空串 = 未启用)。值统一 String 化
     * (YAML 树里标量全为字符串, 数字残留只在手编 YAML 时出现, 显示面归一) */
    bbValue() {
      const rel = this.cfgConfig().relocate;
      const v = rel && typeof rel === "object" && !Array.isArray(rel) ? rel.bt_backup : null;
      return v === null || v === undefined ? "" : String(v);
    },
  },
  methods: {
    /* ---------------------------------------------------------- 读写地基 */
    /* 写回单点: relocate.bt_backup 标量。留空 = 写空串(未启用语义, 与 S1 校验一致), 不删键;
     * 中间段不存在时 cfgSetPath 就地建链(与通用编辑树对任意字段的写路径同款)。 */
    bbSet(value) {
      this.cfgSetPath(["config", "relocate", "bt_backup"], value);
    },
    /* ---------------------------------------------------------- 自动探测(D3 读法2: 按钮唯一入口) */
    async bbProbeRun() {
      if (this.bbProbe.running) return;
      const seq = ++this.bbProbe.seq;
      this.bbProbe.running = true;
      this.bbProbe.error = "";
      try {
        const data = await this.api("/api/relocate/bt_backup_probe", { method: "POST" });
        if (seq !== this.bbProbe.seq) return;  // 过期响应: 用户已再点一轮, 丢包不渲染
        this.bbProbe.running = false;
        this.bbProbe.result = data;
        /* hit -> 回填草稿(不自动保存, 用户点「保存并应用」才落盘 —— 审计轨迹)。草稿已有值
         * 不覆盖(保守默认: 探测不静默丢用户输入), 证据区提示先清空再采用; manual_set 是
         * 服务端磁盘口径, 草稿以 bbValue 本地值为准, 故以「草稿非空」为不覆盖判据。
         * filled 在回填**前**取值(回填后 bbValue 必非空, 拿它判会把「已回填」误标成「未覆盖」)。 */
        const draftExisted = !!this.bbValue;
        this.bbProbe.filled = false;
        if (data && data.verdict === "hit" && !draftExisted) {
          /* 回填候选选择: 优先 hash 自证命中的合格候选, 再兜底首个合格 —— verdict=hit 有「多候选
           * 合格、恰一候选 hash 命中」的消歧形态(probe.verdict: len(matched_paths)==1), hash 命中者
           * 未必排在扫描序首位, 取首个 qualified 会回填 hash 未命中的错误路径; 无 hash 命中的 hit
           * (唯一合格 + 离线未自证等)由兜底分支保证仍能回填。 */
          const cands = data.candidates || [];
          const hit = cands.find((c) => c.qualified && c.hash_matched) || cands.find((c) => c.qualified);
          if (hit && hit.path) {
            this.bbSet(hit.path);
            this.bbProbe.filled = true;
          }
        }
      } catch (e) {
        if (seq !== this.bbProbe.seq) return;
        this.bbProbe.running = false;
        this.bbProbe.result = null;  // 证据区只反映最近一次探测: 失败即清旧证据, 重按一次即重探
        this.bbProbe.error = (e && e.message) || "网络或服务端错误";
      }
    },
    /* ---------------------------------------------------------- 证据区文案(模板消费) */
    /* 五态话术(查表 BB_VERDICT_TEXT; 未知 verdict 兜原样 —— 后端加态不白屏)。hit 按 filled
     * 分流: 未回填的主行走 BB_HIT_KEPT_TEXT(与模板「未覆盖」注释行同条件, 两处口径一致) */
    bbVerdictText() {
      const r = this.bbProbe.result;
      if (!r) return "";
      if (r.verdict === "hit" && !this.bbProbe.filled) return BB_HIT_KEPT_TEXT;
      return BB_VERDICT_TEXT[r.verdict] || "探测结果: " + String(r.verdict || "未知");
    },
    /* 五态语义色: hit/manual-set = 正/中性(ok), ambiguous/miss = 提醒(warn), unusable-sqlite = 不可用(bad) */
    bbVerdictCls() {
      const v = this.bbProbe.result && this.bbProbe.result.verdict;
      if (v === "hit" || v === "manual-set") return "ok";
      if (v === "unusable-sqlite") return "bad";
      return "warn";
    },
    /* qB 恢复数据存储展示值(口径对齐 relocate_plan.is_legacy_resume_storage: 0/legacy/空 =
     * Legacy, 1/sqlite = SQLite; 其它原样展示交给用户判断)。空 = 端点没读到该偏好, 不展示 */
    bbStorageText() {
      const st = this.bbProbe.result && this.bbProbe.result.storage_type;
      if (st === "" || st === null || st === undefined) return "";
      const text = String(st).trim().toLowerCase();
      if (text === "0" || text === "legacy") return "Legacy";
      if (text === "1" || text === "sqlite") return "SQLite";
      return String(st);
    },
    /* 候选明细行的推导渠道中文(BB_ORIGIN_TEXT 查表, 未知原样) */
    bbOriginText(origin) {
      return BB_ORIGIN_TEXT[origin] || String(origin || "");
    },
    /* 证据行(后端 notes 原样列出: 后缀枚举来源 / 定位失败 / 离线未自证等) */
    bbNotes() {
      const r = this.bbProbe.result;
      return (r && r.notes) || [];
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
