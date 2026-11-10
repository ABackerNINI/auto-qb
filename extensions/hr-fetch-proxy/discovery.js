// 发现协议纯函数(计划 26-10-14-1241 S4; 合并语义于计划 26-10-15-2357 S1 翻转): 选项页 <script> /
// 后台 importScripts / pytest node 实跑。
// !合并语义 = **手动优先 + 发现集整批替换**(见 mergeInstances): 手动条目是不可被自动覆盖的用户显式
// 指定; 发现是自愈通道, 只补齐手动没覆盖的端点 —— 旧实现「同端点被发现覆盖 + 只增不减」已废止。
// 与后端 hr/discovery.py 同源(候选表推导 / 响应形态判定)—— 改一边必改另一边, 守阵双向钉住。
// 纪律与 normalize.js 同款: 不引用 document / chrome, 归一化共用 normalize.js(不在此重复)。

/** 发现端点路径(与后端 hr.discovery.API_DISCOVER 同步, 协议守阵双向钉住) */
const API_DISCOVER = '/api/hr/discover';

/** 缺省发现端口(与后端 hr.discovery.DISCOVERY_DEFAULT_PORT 同步; normalize.js 补端口同值) */
const DISCOVERY_DEFAULT_PORT = 18788;

/** base 去尾斜杠(URL.toString 对空路径恒补 "/", 拼路径前统一剥掉) */
function stripTrailingSlash(text) {
  const s = String(text || '');
  return s.endsWith('/') ? s.slice(0, -1) : s;
}

/** 同一 base 换端口(URL 重解析换 port, 免手写正则) */
function withPort(base, port) {
  const u = new URL(String(base));
  u.port = String(port);
  return stripTrailingSlash(u.toString());
}

/**
 * 候选表(C7/D6): base 起连号 8 个(+0..+7), 上限 65535 截断 —— 推导与后端
 * hr.discovery.discovery_candidates 同源(后端「先绑先得」顺延, 扩展「并行探测」同表)。
 */
function discoveryCandidates(base) {
  let url;
  try {
    url = new URL(String(base || ''));
  } catch (e) {
    return []; // 非法地址 = 无候选(调用方另有归一化报错面; 这里容错不抛)
  }
  const start = Number(url.port);
  if (!Number.isFinite(start) || start < 1) return [];
  const out = [];
  for (let i = 0; i < 8; i += 1) {
    const p = start + i;
    if (p < 1 || p > 65535) continue;
    out.push(withPort(base, p));
  }
  return out;
}

/** 发现地址 base → 完整发现 URL(去尾斜杠拼路径, 免得出现双斜杠) */
function buildDiscoveryUrl(base) {
  return stripTrailingSlash(base) + API_DISCOVER;
}

/** 401 + pairing_required 判定(res = {status, error}, 由调用方先解析响应体) */
function pairingNeeded(res) {
  return Boolean(res) && Number(res.status) === 401 && res.error === 'pairing_required';
}

/**
 * 手动条目判定: `source` 非 `'discovered'` 即手动 —— 含**缺 `source` 字段的旧数据**(C8):
 * 旧条目零迁移即获「优先」语义, 行为等价于「用户显式指定」。
 */
function isManualEntry(e) {
  return !(e && typeof e === 'object' && e.source === 'discovered');
}

/**
 * 合并发现结果(计划 26-10-15-2357 S1 翻转语义): **手动优先 + 发现集整批替换**。
 *
 * - 手动条目(`isManualEntry`)**原样保留**、保持原顺序、恒在前 —— 用户显式指定的实例优先使用、
 *   优先展示, 且**永不**被自动覆盖或删除(Q1/Q9/Q10)。同端点冲突时**手动整条胜**(Q8):
 *   发现的同端点条目直接丢弃(连 name/token 都不取), 发现只负责「补齐手动没覆盖的端点」。
 * - 发现条目按**租约**管理(Q2): 每次成功发现**整批替换**旧的发现集 —— 死端口的条目自然被剪除,
 *   不再像旧实现那样只增不减、永久堆积。
 * - **空集例外(C1)**: `discovered` 为空 ⇒ **不替换**(保留旧发现集)。后端重启瞬间注册表条目可能
 *   已过 TTL 或心跳未落 ⇒ 发现会返回空集; 此时若清空发现集, 扩展就自断了连接(且实例为空时连
 *   「失败即发现」都不触发, 只能干等周期)。此为 Q2「整批替换」的唯一例外。
 * - 缺 endpoint / 缺 token 的发现条目不收(不给半条 —— 半条会让轮询打出难排查的 401)。
 *
 * 顺序: 手动在前(保持原顺序) + 发现追加在后 —— 周期性重发现不抖动列表。
 */
function mergeInstances(current, discovered) {
  const cur = Array.isArray(current) ? current : [];
  const disc = Array.isArray(discovered) ? discovered : [];
  const manual = [];
  const prevDiscovered = [];
  for (const c of cur) {
    if (!c || typeof c !== 'object') continue;
    (isManualEntry(c) ? manual : prevDiscovered).push(c);
  }
  const manualEndpoints = new Set(manual.map((e) => String(e.endpoint || '')));
  const fresh = [];
  const seen = new Set();
  for (const d of disc) {
    if (!d || typeof d !== 'object') continue;
    const ep = String(d.endpoint || '');
    const tk = String(d.token || '');
    if (!ep || !tk) continue; // 半条不收
    if (manualEndpoints.has(ep)) continue; // 手动整条胜(Q8): 同端点让位手动, 不碰它的 name/token
    if (seen.has(ep)) continue; // 发现集内同端点去重(保首个)
    seen.add(ep);
    fresh.push({ name: String(d.name || ep), endpoint: ep, token: tk, source: 'discovered' });
  }
  return manual.concat(disc.length === 0 ? prevDiscovered : fresh);
}

// ---------- 显式裁决(计划 26-11-10-0515 装置二 / S4a) ----------
//
// !为什么需要: 登记簿按 clone 拆分后, 每份发现应答只含本 clone 的实例 —— 但同机多 clone 时
// 会有**多份**应答同时命中, 扩展不得再像 find-first 时代那样随便挑一家开轮(混串的根源)。
// 裁决规则(§06 D2, P2 用户拍板):
//   · 恰 1 份应答且无选择 -> 自动服务它(单实例用户零感知, P3); 标签去重后恰 1 个才持久化
//     选择(legacy 聚合应答不 pin, 下轮重新裁决);
//   · >=2 份应答且无选择 -> 一个都不服务, 裁决态 needsSelection(显性失败: 亮着等选, P2 性质);
//   · 已有选择 -> 只服务所选**标签**的应答; 所选 clone 消失 -> 服务空转, 绝不自动改投别家;
//     多份应答同时带所选标签(撞名) -> ambiguous: 只打手动, 不以「已选择」名义静默全服务;
//   · 手动条目(source != 'discovered')不受裁决约束, 恒服务(P2: 手动 = 用户显式动作);
//   · legacy 兼容(D8 只加不改): 裁决粒度是「应答份」不是「实例条」—— 恰 1 份应答时无论新旧
//     后端都按这份应答的**全部实例**服务(等价今天), >=2 份才进裁决。
// 选择按标签 name 记(独立存储键 activeNames, 由调用方持久化; name 自 S3 起是稳定工作区标签,
// 跨重启不变) —— 所以这里**不需要** id: 合并去重仍按 endpoint, 跨重启识别靠 name, id 被丢弃
// 不影响任何裁决路径。

/** 实例的裁决标签: name 优先, 缺 name 回落 endpoint(S3 前的旧响应 name 是随机 uuid, 但非空;
 * 两处回落共用同一推导, 保证「持久化的选择」与「下轮匹配」永远用同一把钥匙) */
function instanceLabel(e) {
  return String((e && e.name) || (e && e.endpoint) || '').trim();
}

/** 一份应答的标签集(去重保序): 新后端应答内全部实例同属一个 clone, 标签相同; legacy 应答
 * (旧后端聚合全机)各实例标签互异 —— 恰 1 份时整份照收, 所以标签集是全部去重标签 */
function answerLabelNames(instances) {
  const out = [];
  const seen = new Set();
  for (const e of Array.isArray(instances) ? instances : []) {
    const label = instanceLabel(e);
    if (!label || seen.has(label)) continue;
    seen.add(label);
    out.push(label);
  }
  return out;
}

/** 服务条目归一化(与 mergeInstances 的发现条目同形): 缺 endpoint/token 的半条不服务(半条会让
 * 轮询打出难排查的 401, 口径与合并一致) */
function serviceableEntry(e) {
  if (!e || typeof e !== 'object') return null;
  const ep = String(e.endpoint || '');
  const tk = String(e.token || '');
  if (!ep || !tk) return null;
  return { name: String(e.name || ep), endpoint: ep, token: tk };
}

/**
 * 裁决状态机(纯函数, 守阵直测): 输入应答集合 + 当前选择 + 手动实例, 输出服务集合与裁决态。
 *
 * @param responses  全部 ok 应答, 每份 = {port, instances}(原始实例列表 + 来源端口); 空应答
 *                   (instances 为空)不算一份候选 —— 它没有可服务的实体
 * @param activeNames 当前选择(标签数组, 读自独立存储键; 空 = 无选择)
 * @param manual     手动实例(source != 'discovered'; 调用方从存储条目里筛好) —— 恒服务(P2)
 * @returns {state, served, selection}
 *   state: 'auto'(唯一应答自动服务; selection 非空 = 应持久化的选择, 见下)
 *          'selected'(按选择服务)
 *          'ambiguous'(有选择但**多份**应答都带着所选标签 —— 两 clone 撞名或 legacy 应答含同名条:
 *                      不允许以「用户已选择」名义静默全服务, 只打手动, 绝不改投/不清选择)
 *          'needsSelection'(>=2 份应答且无选择: 一个都不服务, 供选项页横幅)
 *          'selectedMissing'(有选择但本轮没有一份应答带着所选标签: 服务空转)
 *          'noAnswer'(本轮零应答且无选择)
 *   served: 应服务的实例条目 = 手动(恒在前, **原样透传** —— 与消费面 servedInstancesOf 同口径:
 *           手动按 isManualEntry 现判放行, 不做半条过滤, 计数不虚低) + 被服务应答的全部实例
 *           (归一化, 半条不收; 同一份应答内 endpoint 重复去重保首个, 对齐 mergeInstances,
 *           计数不虚高; 与手动同端点的发现条目按 Q8「手动整条胜」让位, 不重复进服务集)
 *   selection: 'auto' 态且该应答标签去重后**恰 1 个**时 = 要持久化的选择; legacy 聚合应答
 *              (标签 >1, 旧后端随机 uuid)不给 —— 服务仍整份照收(D8), 但不 pin 标签, 下轮
 *              重新裁决(否则旧后端 uuid 被 pin, 升级后 selectedMissing 恒态且无 UI 可清);
 *              其余态 = 现有选择原样
 */
function adjudicateInstances(responses, activeNames, manual) {
  const respList = (Array.isArray(responses) ? responses : []).filter(
    (r) => r && typeof r === 'object' && Array.isArray(r.instances) && r.instances.length > 0
  );
  const sel = (Array.isArray(activeNames) ? activeNames : [])
    .map((n) => String(n || '').trim())
    .filter(Boolean);
  // 手动原样透传(评审轮 2 修 3b): 消费面对手动不做半条过滤, 服务集计数必须同一把尺
  const manualEntries = (Array.isArray(manual) ? manual : []).filter((e) => e && typeof e === 'object');
  const manualEps = new Set(manualEntries.map((e) => String((e && e.endpoint) || '')));
  // 手动整条胜(Q8)延伸到服务面 + 同一份应答内 endpoint 去重保首个(评审轮 2 修 3a, 对齐 mergeInstances)
  const answerServiceable = (r) => {
    const out = [];
    const seen = new Set();
    for (const e of r.instances.map(serviceableEntry)) {
      if (!e || manualEps.has(e.endpoint) || seen.has(e.endpoint)) continue;
      seen.add(e.endpoint);
      out.push(e);
    }
    return out;
  };
  if (sel.length > 0) {
    const matched = respList.filter((r) =>
      r.instances.some((e) => sel.includes(instanceLabel(e)))
    );
    if (matched.length === 1) {
      return {
        state: 'selected',
        served: manualEntries.concat(answerServiceable(matched[0])),
        selection: sel,
      };
    }
    if (matched.length > 1) {
      // 撞名歧义: 静默全服务 = 以「用户已选择」名义混串 —— 显性停下, 只打手动(P2 性质: 显眼地不服务)
      return { state: 'ambiguous', served: manualEntries, selection: sel };
    }
    return { state: 'selectedMissing', served: manualEntries, selection: sel };
  }
  if (respList.length === 1) {
    const labels = answerLabelNames(respList[0].instances);
    return {
      state: 'auto',
      served: manualEntries.concat(answerServiceable(respList[0])),
      selection: labels.length === 1 ? labels : [], // legacy 聚合应答(标签 >1)不持久化, 服务照收(D8)
    };
  }
  if (respList.length >= 2) {
    return { state: 'needsSelection', served: manualEntries, selection: [] };
  }
  return { state: 'noAnswer', served: manualEntries, selection: [] };
}

/**
 * 消费面过滤(纯函数, 守阵直测): 从存储实例清单里筛出**本轮裁决实际服务**的条目 —— 外呼路径
 * (pollAll / requestBackendRefresh / probeAll)只消费这份, 选项页列表仍读全量。
 *
 * @param instances 存储实例清单(全量: 手动 + 全部发现条目)
 * @param verdict   裁决落盘({state, discovered: [被服务发现条目的 endpoint, ...]}, 由
 *                  runDiscovery 每轮写); 手动条目在消费时按 isManualEntry 现判 —— 裁决轮间隙
 *                  用户新加的手动条目照常服务(P2 不依赖落盘快照的新鲜度)
 * !verdict 缺失(升级后首轮发现之前的旧存储)退化全量 = 等价升级前行为, 首轮发现落地即收敛。
 */
function servedInstancesOf(instances, verdict) {
  const all = Array.isArray(instances) ? instances : [];
  if (!verdict || typeof verdict !== 'object' || !verdict.state) return all;
  const allow = new Set(
    (Array.isArray(verdict.discovered) ? verdict.discovered : []).map((e) => String(e || ''))
  );
  return all.filter(
    (e) => e && typeof e === 'object' && (isManualEntry(e) || allow.has(String(e.endpoint || '')))
  );
}

/**
 * 发现响应形态判定(计划 S4: 仅接受 200 + 合法发现响应形态): 实例数组字段齐全。
 * 普通应用误占端口返回的异形应答 / 404 / 连接拒绝一律按「非本服务」忽略(调用方并行探测,
 * 多候选同时应答**全部收集**进裁决 —— S4a 起 find-first 已废止)。
 */
function validDiscoveryPayload(payload) {
  if (!payload || typeof payload !== 'object' || !Array.isArray(payload.instances)) return false;
  return payload.instances.every(
    (e) => Boolean(e) && typeof e === 'object' && typeof e.endpoint === 'string' && typeof e.token === 'string'
  );
}
