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
 * 候选表(C7): base 起连号 3 个(+0/+1/+2), 上限 65535 截断 —— 推导与后端
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
  for (let i = 0; i < 3; i += 1) {
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

/**
 * 发现响应形态判定(计划 S4: 仅接受 200 + 合法发现响应形态): 实例数组字段齐全。
 * 普通应用误占端口返回的异形应答 / 404 / 连接拒绝一律按「非本服务」忽略(调用方并行探测,
 * 多候选同时应答取最先成功者)。
 */
function validDiscoveryPayload(payload) {
  if (!payload || typeof payload !== 'object' || !Array.isArray(payload.instances)) return false;
  return payload.instances.every(
    (e) => Boolean(e) && typeof e === 'object' && typeof e.endpoint === 'string' && typeof e.token === 'string'
  );
}
