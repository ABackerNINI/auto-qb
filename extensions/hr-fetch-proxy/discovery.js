// 发现协议纯函数(计划 26-10-14-1241 S4): 选项页 <script> / 后台 importScripts / pytest node 实跑。
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
 * 合并发现结果: 发现的**替换同端点条目**, 保留手填条目; 发现条目标 source:"discovered"。
 * 顺序: 手填在前(保持原顺序), 新发现的追加在后 —— 周期性重发现不抖动列表。
 * 缺 endpoint / 缺 token 的发现条目不收(不给半条 —— 半条会让轮询打出难排查的 401)。
 */
function mergeInstances(current, discovered) {
  const cur = Array.isArray(current) ? current : [];
  const disc = Array.isArray(discovered) ? discovered : [];
  const byEndpoint = new Map();
  for (const d of disc) {
    if (!d || typeof d !== 'object') continue;
    const ep = String(d.endpoint || '');
    const tk = String(d.token || '');
    if (ep && tk) byEndpoint.set(ep, d);
  }
  const used = new Set();
  const out = [];
  for (const c of cur) {
    const ep = String((c && c.endpoint) || '');
    if (byEndpoint.has(ep)) {
      const d = byEndpoint.get(ep);
      used.add(ep);
      out.push({ name: String(d.name || c.name || ep), endpoint: ep, token: String(d.token || ''), source: 'discovered' });
    } else {
      out.push(c); // 手填条目原样保留(发现关闭/失败时的手动兜底路径不变)
    }
  }
  for (const entry of byEndpoint) {
    const ep = entry[0];
    const d = entry[1];
    if (!used.has(ep)) {
      out.push({ name: String(d.name || ep), endpoint: ep, token: String(d.token || ''), source: 'discovered' });
    }
  }
  return out;
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
