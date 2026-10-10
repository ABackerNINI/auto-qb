/* auto-qb WEB UI · 作用域运行时审计(计划 26-10-10-2001 S4, 第三张网之「运行时审计」)
 *
 * 职责: 在三个统一出口(_actCore / _deleteFlow / _metaBulk)各记账一次「这次触发实际下发的
 * 目标载荷」, 做形状与去重校验; 偏差记进有界环并按签名去重 console.warn 一次。
 * **只记账, 不改行为**(与 cmdStats 同范式: 埋点必须有消费者 —— e2e 每次交互后断言环内
 * 无偏差记录, 排障时可从控制台读 window.__AQB_SCOPE_RING__)。
 *
 * 开关: window.__AQB_AUDIT_SCOPE__ —— 生产默认关(保守默认, 不污染用户 console, 关态
 * O(1) 直返不碰环); e2e 用 Playwright 的注入脚本打开。
 *
 * 环: window.__AQB_SCOPE_RING__, 上限 50 条(有界, 旧记录挤出), 记录字段
 * {t, event, kind, keys, hashes, msg, sig}: kind ∈ ok / shape / dup / empty。
 * 静态守阵 tests/test_webui_trigger_registry.py 钉住: 三出口接线 / 默认关(源码无赋值点)。
 *
 * !本文件在 HTML 里必须排在 triggers.js 之前或之后均可(互不引用), 但须排在 app.js 之前
 *   (app.js 末尾要读 window.AQB_SCOPE_AUDIT 做 app.mixin 注入)。
 */
window.AQB_SCOPE_AUDIT = {
  methods: {
    /* 出口审计: event = 出口标识(如 "actCore:reannounce"), targets = 既有载荷
     * {keys, hashes}(兼容 {groupKeys, memberHashes} 形状 —— metaTargets 等)。
     * 校验全部 O(目标数), 关态 O(1)。 */
    _auditScope(event, targets) {
      if (!window.__AQB_AUDIT_SCOPE__) return;
      const ring = window.__AQB_SCOPE_RING__ || (window.__AQB_SCOPE_RING__ = []);
      const rec = { t: Date.now(), event: String(event || ""), kind: "ok", keys: [], hashes: [], msg: "" };
      const t = targets || {};
      const ks = Array.isArray(t.keys) ? t.keys : Array.isArray(t.groupKeys) ? t.groupKeys : null;
      const hs = Array.isArray(t.hashes) ? t.hashes : Array.isArray(t.memberHashes) ? t.memberHashes : null;
      if (!ks || !hs) {
        rec.kind = "shape";
        rec.msg = "载荷不是 {keys[],hashes[]} 形状(descriptor 缺失/字段越界, 计划 26-10-10-2001 C1)";
      } else {
        rec.keys = ks.map(String);
        rec.hashes = hs.map(String);
        const bad = (a) => a.some((x) => typeof x !== "string" || !x);
        if (bad(ks) || bad(hs)) {
          rec.kind = "shape";
          rec.msg = "keys/hashes 含非串或空串元素(目标没走 _scopeResolve 单点, C1 违例)";
        } else if (new Set(ks).size !== ks.length || new Set(hs).size !== hs.length) {
          rec.kind = "dup";
          rec.msg = "keys/hashes 内部重复(同一目标走了两次通道, M4 违例)";
        } else if (!ks.length && !hs.length) {
          rec.kind = "empty";
          rec.msg = "出口收到空载荷(上游已静默 no-op, 记账供对账)";
        }
      }
      rec.sig = rec.kind + "|" + rec.keys.join(",") + "|" + rec.hashes.join(",");
      /* 按签名去重 warn: 同一签名偏差只 warn 一次(环里已有同签名偏差记录则跳过) */
      if (rec.kind !== "ok" && !ring.some((r) => r.kind !== "ok" && r.sig === rec.sig)) {
        console.warn("[scope-audit] " + rec.event + ": " + rec.msg, { keys: rec.keys, hashes: rec.hashes });
        rec.warned = true;
      }
      ring.push(rec);
      if (ring.length > 50) ring.splice(0, ring.length - 50);
    },
  },
};
