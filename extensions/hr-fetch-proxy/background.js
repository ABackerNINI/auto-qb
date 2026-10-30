// auto-qb HR 取数代理 · 后台逻辑(MV3 service worker)
//
// 职责只有三条(计划 §6 的「哑取数器」):
//   1. 定时(chrome.alarms)逐个实例问本地端点要任务;
//   2. 按任务取内容 —— kind=page **先无界面直取**(service worker 的 fetch 带站点 cookie, 零标签零窗口),
//      只在「拿到的内容看起来没渲染出来」时才退到**离屏 popup 窗口**里取 DOM; kind=torrent 也是
//      service worker 自己 fetch(credentials: 'include');
//   3. 把结果原样回传(POST)。
//
// 明确**不做**的事: 不解析页面、不判频控、不读 chrome.cookies、不碰 passkey ——
// 解析与策略全在后端(能用 pytest 守住的那一侧), cookie 全程不离开浏览器。
//
// 配置在选项页(实例列表 + 站点权限), 存在 chrome.storage.local。
// 运行日志(分级 + 环形上限, 选项页4.区过滤查看)也落 chrome.storage.local —— 见下方「运行日志」节。
// 地址归一化共用 normalize.js(选项页用 <script> 载入, 这里用 importScripts —— 同一份代码)。

importScripts('normalize.js');
importScripts('discovery.js');
importScripts('site-caps.js');

const ALARM_NAME = 'hr-poll';
// !轮询周期必须**小于**后端 `channel.request_timeout` 的等待窗口(默认 180s): 任务只有在窗口内
// 等到下一次轮询才会被取走。v2.6 前按 5 分钟轮询, 每条任务约四成概率直接超时
// (2026-09-25 实报「取 .torrent 失败: 等待浏览器扩展取数超时(180s)」)。1 分钟轮询只打本机
// loopback 一次 GET, 成本可忽略; 后端才是站点频控的唯一权威 —— 空轮询不会碰到站点。
const POLL_MINUTES = 1;
// 自动发现(计划 26-10-14-1241 S4/C2; 自愈节奏与触发面于计划 26-10-15-2357 S2/Q3 收紧):
// 周期 2 分钟 —— 数据端口每次重启都可能变, 2 分钟是「端口换了但用户零操作」的上界; 与 60s 轮询解耦,
// 免得发现流变成第二轮询。
// 触发器: 启动时 / **任一实例拉取失败时**(1 分钟节流, 覆盖「1 死 1 活不算全失败」的漏网)/ 每 2 分钟 /
// 选项页「立即发现」(随时)。
// !发现地址留空 = 用户显式关闭: 完全静默跳过, 不打一行日志(手动指定路径是完整退路)。
const DISCOVERY_EVERY_MINUTES = 2;
const DISCOVERY_MIN_GAP_MS = 60 * 1000;
const DEFAULT_DISCOVERY_ADDRESS = 'http://127.0.0.1:' + DISCOVERY_DEFAULT_PORT; // 端口常量与后端同源(discovery.js)
const PAGE_LOAD_TIMEOUT_MS = 60000;
const PAGE_SETTLE_MS = 800; // 页面 complete 后再等一小会儿(部分站点是 XHR 填表)
const OFFSCREEN_X = -32000; // 离屏坐标: 渲染兜底用的窗口放在屏幕外(Windows 允许完全离屏)
const OFFSCREEN_Y = -32000;

async function readConfig() {
  const got = await chrome.storage.local.get({
    enabled: true,
    instances: [],
    siteOrigins: [],
    discoveryAddress: DEFAULT_DISCOVERY_ADDRESS,
    pairingCode: '',
  });
  return {
    enabled: Boolean(got.enabled),
    instances: Array.isArray(got.instances) ? got.instances : [],
    siteOrigins: Array.isArray(got.siteOrigins) ? got.siteOrigins : [],
    discoveryAddress: String(got.discoveryAddress || '').trim(),
    pairingCode: String(got.pairingCode || '').trim(),
  };
}

async function noteStatus(patch, lvl) {
  const prev = await chrome.storage.local.get({ status: {} });
  const status = Object.assign({}, prev.status, patch, { at: Date.now() });
  await chrome.storage.local.set({ status });
  // 状态栏只留**最后一句**, 同样的内容同步进运行日志(level 由调用方给: 配额/异常要标 warn/error)。
  // 同文重复降为 debug: 轮询 1 分钟一轮, 连败期/闲轮期每轮都是同一句话, 原样刷 info 会把日志环
  // 灌成复读机; 状态栏本身每轮照常刷新(时间戳/文案), 不受影响。
  if (patch && patch.text) {
    log(prev.status && prev.status.text === patch.text ? 'debug' : lvl || 'info', '状态', patch.text);
  }
}

// ---------- 运行日志(分级 + 环形上限, 落 chrome.storage.local) ----------
//
// !为什么需要: 状态栏只有**最后一句**, 一轮里多实例多任务的经过全被覆盖掉; 排查「这条为什么失败 /
// 后端到底收到了什么」必须看时序。故把关键事件逐条落成带级别的日志, 选项页4.区可按级别过滤查看:
//   · 分级: debug/info/warn/error。低于「记录级别」的直接丢弃(选项页可设, 默认 info);
//   · 环形上限: 只留最近 N 条(选项页可设 10–10000, 默认 1000; 10000 是用户指定的硬上限) ——
//     再大单次落盘的序列化开始拖慢 SW, 且 storage.local 配额(10MB)吃紧;
//   · 字段收敛: 每条 = 时间 + 级别 + 类别 + 摘要 + 明细(站点/url/类型/HTTP/耗时/字节数/后端响应…),
//     单字段超长一律截断 —— 页面 HTML 动辄几 MB, 整份进日志 10000 条就把配额打爆了。
//
// MV3 的 service worker 随时被回收, 所以**唯一事实源是 storage**: SW 醒来后第一次写日志时把存量
// 读进内存当缓冲底, 之后只增删内存数组, 防抖 300ms **整份**写回。整份写回(而不是读→append→写)是
// 故意的: log() 是 fire-and-forget, 读改写在两个并发 log 之间会互相覆盖丢条 —— 内存数组是唯一写入口。
const LOG_LEVELS = { debug: 0, info: 1, warn: 2, error: 3 };
const LOG_KEY = 'logs';
const LOG_MAX_KEY = 'logMax';
const LOG_LEVEL_KEY = 'logLevel';
const LOG_DEFAULT_MAX = 1000;
const LOG_HARD_MAX = 10000; // 用户指定的硬上限: 条数设置再大也不许超过它
const LOG_FLUSH_MS = 300;
const LOG_TRUNC = 400; // 单字段截断长度(字符)

let logBuf = null; // 环形缓冲(initLogBuffer 之后才有值; log() 会先等它)
let logMaxCache = LOG_DEFAULT_MAX;
let logLevelCache = 'info';
let logInitPromise = null;
let logFlushTimer = null;
let logFlushChain = Promise.resolve();
let logSelfWriteAt = 0; // 最近一次自己落盘的时刻: 区分「自己写的」与「外部改的」(见 onChanged)

function clampLogMax(v) {
  const n = Math.round(Number(v) || 0);
  return Math.min(LOG_HARD_MAX, Math.max(10, n));
}

/** 明细字段收敛: 空值剔除、非字符串 JSON 化、超长截断 —— 10000 条也撑不爆 storage 配额 */
function compactDetail(detail) {
  const out = {};
  if (!detail || typeof detail !== 'object') return out;
  for (const [k, v] of Object.entries(detail)) {
    if (v === undefined || v === null || v === '') continue;
    let s = typeof v === 'string' ? v : JSON.stringify(v);
    if (s === undefined) continue; // JSON.stringify(函数) === undefined
    if (s.length > LOG_TRUNC) s = s.slice(0, LOG_TRUNC) + `…(共 ${s.length} 字符)`;
    out[k] = s;
  }
  return out;
}

/**
 * 写一条日志(fire-and-forget, 返回值仅供测试 await): 低于记录级别的直接丢。
 * !绝不让日志反噬主流程: 初始化/追加/落盘任何一步失败都吞掉, 取数照跑。
 */
function log(lvl, cat, msg, detail) {
  if (!logInitPromise) logInitPromise = initLogBuffer();
  const lvlName = Object.prototype.hasOwnProperty.call(LOG_LEVELS, lvl) ? lvl : 'info';
  return logInitPromise.then(() => {
    if (LOG_LEVELS[lvlName] < LOG_LEVELS[logLevelCache]) return;
    logBuf.push(
      Object.assign(
        {
          t: Date.now(),
          lvl: lvlName,
          cat: String(cat || '').slice(0, 20) || '其它',
          msg: String(msg === undefined || msg === null ? '' : msg).slice(0, LOG_TRUNC * 2),
        },
        compactDetail(detail)
      )
    );
    if (logBuf.length > logMaxCache) logBuf.splice(0, logBuf.length - logMaxCache);
    scheduleLogFlush();
  }).catch(() => {});
}

async function initLogBuffer() {
  try {
    const got = await chrome.storage.local.get({ [LOG_KEY]: [], [LOG_MAX_KEY]: LOG_DEFAULT_MAX, [LOG_LEVEL_KEY]: 'info' });
    logBuf = Array.isArray(got[LOG_KEY]) ? got[LOG_KEY] : [];
    logMaxCache = clampLogMax(got[LOG_MAX_KEY]);
    if (Object.prototype.hasOwnProperty.call(LOG_LEVELS, got[LOG_LEVEL_KEY])) logLevelCache = got[LOG_LEVEL_KEY];
    if (logBuf.length > logMaxCache) logBuf.splice(0, logBuf.length - logMaxCache);
  } catch (e) {
    logBuf = logBuf || []; // 读不到就当空: 丢一轮日志可以接受, 主流程不能被它卡住
  }
}

/** 条数/记录级别设置的统一入口(storage.onChanged 与测试都走这里), 收紧上限时顺手裁剪 */
function applyLogSettings(maxValue, levelValue) {
  if (maxValue !== undefined) logMaxCache = clampLogMax(maxValue);
  if (levelValue !== undefined && Object.prototype.hasOwnProperty.call(LOG_LEVELS, levelValue)) logLevelCache = levelValue;
  if (logBuf && logBuf.length > logMaxCache) logBuf.splice(0, logBuf.length - logMaxCache);
}

function scheduleLogFlush() {
  if (logFlushTimer) return;
  logFlushTimer = setTimeout(() => {
    logFlushTimer = null;
    flushLogs();
  }, LOG_FLUSH_MS);
}

/** 整份写回(串行化: 前一笔没写完不叠下一笔); pollAll 收尾会 await 它, 让「立即拉取」立刻可见 */
function flushLogs() {
  if (!logInitPromise) return Promise.resolve();
  const prev = logFlushChain; // !先取队尾再排队: 回调里若按名字引用 logFlushChain, 那时它已被改成
  const p = logInitPromise.then(() => // 「本次 flush 自己」, 等自己 = 首刷即死锁(实测抓过)
    prev.then(() => {
      logSelfWriteAt = Date.now();
      return chrome.storage.local.set({ [LOG_KEY]: logBuf }).catch((e) => {
        console.warn('日志落盘失败(等下一笔再试):', e);
      });
    })
  );
  logFlushChain = p.catch(() => {});
  return p;
}

async function clearLogs() {
  if (!logInitPromise) logInitPromise = initLogBuffer();
  await logInitPromise;
  logBuf.length = 0;
  await flushLogs();
  log('info', '命令', '日志已清空(选项页)'); // 留一条证明清过 + 时间点; 随下一次防抖落盘
}

// 设置缓存联动: 选项页改了条数/级别, SW 不重启也要生效。
// 外部清空采纳: 选项页在后台没应答时会直接把 storage 里的 logs 置空 —— 内存必须采纳这份新数组,
// 否则旧缓冲在下一次落盘时会把「已清空」盖回去。1 秒内自己刚写过的忽略(那本来就是同一份数据)。
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== 'local') return;
  if (changes[LOG_MAX_KEY] || changes[LOG_LEVEL_KEY]) {
    applyLogSettings(
      changes[LOG_MAX_KEY] ? changes[LOG_MAX_KEY].newValue : undefined,
      changes[LOG_LEVEL_KEY] ? changes[LOG_LEVEL_KEY].newValue : undefined
    );
  }
  if (changes[LOG_KEY] && logBuf && Date.now() - logSelfWriteAt > 1000) {
    logBuf.length = 0;
    if (Array.isArray(changes[LOG_KEY].newValue)) logBuf.push(...changes[LOG_KEY].newValue);
  }
});

// ---------- 结构化事件环(选项页「站点现状 / 最近取数明细」两张表的数据源) ----------
//
// 与运行日志**同源双写**: 日志是给人排障的逐条叙述(文案会改), 这份是给表格渲染的结构化记录 ——
// 解析日志文案做表太脆。字段收敛到表格要用的几个: 时间/站点/类型/结果分类(tag)/HTTP/耗时/字节/备注。
// 只增删内存数组 + 防抖整份写回(与 logs 同一套纪律, 唯一写入口在后台); 上限 50 条 ——
// 表格本就只展示最近一段, 更早的完整经过在折叠的运行日志里。
const EVENT_KEY = 'events';
const EVENT_CAP = 50;
const EVENT_FLUSH_MS = 300;
let eventBuf = null;
let eventInitPromise = null;
let eventFlushTimer = null;
let eventFlushChain = Promise.resolve();

function initEventBuffer() {
  return chrome.storage.local
    .get({ [EVENT_KEY]: [] })
    .then((got) => {
      eventBuf = Array.isArray(got[EVENT_KEY]) ? got[EVENT_KEY] : [];
      if (eventBuf.length > EVENT_CAP) eventBuf.splice(0, eventBuf.length - EVENT_CAP);
    })
    .catch(() => {
      eventBuf = eventBuf || []; // 读不到就当空: 丢一段表格数据可以接受, 取数主流程不能被它卡住
    });
}

/**
 * 记一条取数事件(fire-and-forget, 返回值仅供测试 await): 绝不让它反噬取数主流程。
 * tag: ok=成功 | quota=扩展侧硬上限让位 | login=登录页 | error=取数失败
 */
function pushEvent(ev) {
  if (!eventInitPromise) eventInitPromise = initEventBuffer();
  return eventInitPromise.then(() => {
    eventBuf.push(
      Object.assign({ t: Date.now(), host: '', kind: '', ok: false, status: 0, ms: 0, bytes: 0, tag: 'error', note: '' }, ev)
    );
    if (eventBuf.length > EVENT_CAP) eventBuf.splice(0, eventBuf.length - EVENT_CAP);
    scheduleEventFlush();
  }).catch(() => {});
}

function scheduleEventFlush() {
  if (eventFlushTimer) return;
  eventFlushTimer = setTimeout(() => {
    eventFlushTimer = null;
    flushEvents();
  }, EVENT_FLUSH_MS);
}

/** 整份写回(与 flushLogs 同一套串行化纪律); pollAll 收尾会一并 await, 「立即拉取」一返回表格就新鲜 */
function flushEvents() {
  if (!eventInitPromise) return Promise.resolve();
  const prev = eventFlushChain;
  const p = eventInitPromise.then(() =>
    prev.then(() => chrome.storage.local.set({ [EVENT_KEY]: eventBuf }).catch((e) => {
      console.warn('事件环落盘失败(等下一笔再试):', e);
    }))
  );
  eventFlushChain = p.catch(() => {});
  return p;
}

function schedule() {
  // !delayInMinutes 别小于 0.5 分钟: Chrome 对 alarm 有最小间隔限制(非 unpacked 时更严),
  // 违规会直接抛错 —— 那会在安装/启动路径上变成一个看不懂的未捕获异常。
  try {
    chrome.alarms.create(ALARM_NAME, { periodInMinutes: POLL_MINUTES, delayInMinutes: 0.5 });
  } catch (e) {
    noteStatus({ text: `创建定时器失败: ${e.message || e}` }, 'error');
  }
}

chrome.runtime.onInstalled.addListener(() => {
  schedule();
  // 把上限写进 storage: 选项页据此展示「两道闸的当前额度」, 免得两处各写一份阈值(必漂移)
  chrome.storage.local.set({ siteCaps: SITE_CAPS });
  log('info', '系统', `扩展安装/更新: v${(chrome.runtime.getManifest && chrome.runtime.getManifest().version) || '?'}, 轮询周期 ${POLL_MINUTES} 分钟`);
  noteStatus({ text: '已安装: 通常零配置 —— 自动发现会拿到端点与 token; 手动指定见选项页「手动端点」' });
  refreshBadge(); // 徽标是常驻信号: 装上就有态(未配置也是态), 别等第一次轮询
  runDiscovery('启动').catch((e) => log('warn', '发现', `启动发现失败: ${e && e.message ? e.message : e}`));
});

chrome.runtime.onStartup.addListener(() => {
  schedule();
  log('info', '系统', '浏览器启动, 轮询已排程');
  refreshBadge();
  runDiscovery('启动').catch((e) => log('warn', '发现', `启动发现失败: ${e && e.message ? e.message : e}`));
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) {
    pollAll('定时').catch((e) => noteStatus({ text: `轮询异常: ${e}` }, 'error'));
  }
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === 'refresh-now') {
    // 立即拉取(计划 26-09-30-0240): 请求后端立即开波(置一次性 force 旗标, 跳过复用窗与
    // 拉取间隔; 账号频控后端自己守) + 排空已生成的任务。首任务通常在波启动后数秒内入队,
    // 后续任务由 1 分钟定时轮询接管 —— 本消息不等取数完成。
    log('info', '命令', '收到命令: 立即拉取(来自选项页)');
    requestBackendRefresh()
      .then((requested) => pollAll('手动(选项页)').then(() => requested))
      .then((requested) => sendResponse({ ok: true, requested }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }
  if (msg && msg.type === 'discover-now') {
    log('info', '命令', '收到命令: 立即发现(来自选项页)');
    runDiscovery('手动(选项页)')
      .then((r) => sendResponse({ ok: Boolean(r && r.ok), reason: r && r.reason, merged: r && r.merged }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }
  if (msg && msg.type === 'probe-all') {
    // 重测全部(计划 26-10-16-0214 S2/R3): 逐实例只读探测, 结论落台账后选项页表格自动刷新;
    // probe-one 已随 R3 取消(逐实例探测统一由本消息承载)
    log('info', '命令', '收到命令: 重测全部实例(来自选项页)');
    probeAll()
      .then((results) => sendResponse({ ok: true, results }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }
  if (msg && msg.type === 'clear-logs') {
    // 清空必须走后台: 后台内存里留着环形缓冲, 选项页直接改 storage 会在下一次落盘时被盖回去
    clearLogs()
      .then(() => sendResponse({ ok: true }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }
  return false;
});

/**
 * 逐实例请求后端立即开波(计划 26-09-30-0240)。返回全部实例受理的站点总数。
 * - 404 = 旧后端: 降级为纯排空, 日志提示升级 —— 不报错(新旧版本共存是常态);
 * - 网络层失败: 走 explainFetchError 排查清单(与轮询同一套降噪口径, 不另起一套);
 * - 401/其它非 200: 记日志跳过该实例, 不中断其它实例。
 */
async function requestBackendRefresh() {
  const conf = await readConfig();
  if (!conf.enabled || !conf.instances.length) return 0;
  let total = 0;
  for (const inst of conf.instances) {
    const label = inst.name || inst.endpoint || '(未命名)';
    const base = safeEndpoint(inst.endpoint);
    if (!base) continue;
    const url = `${base}/api/hr/refresh`;
    const t0 = Date.now();
    let res;
    try {
      res = await fetch(url, {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, headers(inst)),
        body: '{}',
      });
    } catch (e) {
      log('error', '请求', `立即拉取失败: ${explainFetchError(url, e)}`, reqDetail('立即拉取', url, t0, { 实例: label }));
      continue;
    }
    if (res.status === 404) {
      log(
        'warn',
        '请求',
        `${label}: 后端版本较旧, 请升级主程序后才有立即拉取(本次仅排空既有任务)`,
        reqDetail('立即拉取', url, t0, { 实例: label, HTTP: '404' })
      );
      continue;
    }
    if (res.status === 401) {
      log('warn', '请求', '立即拉取被拒(401, token 或 channel.enabled 未开)', reqDetail('立即拉取', url, t0, { 实例: label, HTTP: '401' }));
      continue;
    }
    if (!res.ok) {
      log('error', '请求', `立即拉取失败 HTTP ${res.status}`, reqDetail('立即拉取', url, t0, { 实例: label, HTTP: String(res.status) }));
      continue;
    }
    const data = await res.json().catch(() => ({}));
    const n = Array.isArray(data.requested) ? data.requested.length : 0;
    total += n;
    log('info', '命令', `${label}: 后端已受理立即拉取(${n} 个站点)`, reqDetail('立即拉取', url, t0, { 实例: label, HTTP: '200' }));
  }
  return total;
}

/**
 * 授权变化后重算缓存(计划 26-10-29-0147 W1/D5): 用户点「授权」或被浏览器撤销时,
 * 徽标与选项页要**立刻**跟着变 —— 否则会出现「已经授权了, 图标还红着」的反向谎言。
 */
async function recheckSitePerms() {
  let got;
  try {
    got = await chrome.storage.local.get({ sitePerms: {} });
  } catch (e) {
    return;
  }
  const perms = got.sitePerms || {};
  const origins = Object.keys(perms);
  if (!origins.length) return;
  for (const origin of origins) {
    const g = await siteGranted(origin);
    if (g !== null) perms[origin] = { granted: g, checkedAt: Date.now() };
  }
  try {
    await chrome.storage.local.set({ sitePerms: perms });
  } catch (e) {}
  await refreshBadge();
}

if (chrome.permissions && chrome.permissions.onAdded) {
  chrome.permissions.onAdded.addListener(() => {
    noteStatus({ text: '站点权限已更新' }).catch(() => {});
    recheckSitePerms().catch(() => {});
  });
}
if (chrome.permissions && chrome.permissions.onRemoved) {
  chrome.permissions.onRemoved.addListener(() => {
    // 撤销站点权限 = 取数一定会失败: 抬头就要红, 别等下一轮取数才发现
    noteStatus({ text: '站点权限被撤销, 取数会失败(回「站点权限」重新授权)' }).catch(() => {});
    recheckSitePerms().catch(() => {});
  });
}

// ---------- 主流程 ----------

async function pollAll(trigger) {
  let endpoints = null;
  try {
    const conf = await readConfig();
    endpoints = conf.instances.map((e) => String((e && e.endpoint) || ''));
    log('info', '轮询', `轮询开始(${trigger || '定时'}): ${conf.instances.length} 个实例`, { 扩展启用: conf.enabled ? '是' : '否' });
    if (!conf.enabled) return;
    if (!conf.instances.length) {
      await noteStatus({ text: '未配置实例端点(打开选项页填写)' });
      await maybeDiscover(0); // !实例为空也要跑周期发现(R1): 否则发现集为空时连接再也回不来
      return;
    }
    const lines = [];
    let failCount = 0;
    for (const inst of conf.instances) {
      try {
        const outcome = await pollInstance(inst);
        lines.push(outcome.line);
        if (!outcome.ok) failCount += 1;
      } catch (e) {
        // pollInstance 内部错误都自己消化了, 走到这是意外异常(如响应 JSON 解析炸了) —— 原样记下来
        const line = `${inst.name || inst.endpoint}: 失败 ${e}`;
        lines.push(line);
        failCount += 1;
        await noteInstanceHealth(inst && inst.endpoint, false, line, 'http');
        log('error', '轮询', line);
      }
    }
    await noteStatus({ text: lines.join('; ') || '无事可做' });
    await maybeDiscover(failCount); // 发现触发器: 任一实例失败(节流)优先, 否则按周期(Q3)
  } finally {
    // 本轮立刻落盘: 「立即拉取」一返回, 选项页日志/两表都新鲜
    await Promise.all([flushLogs(), flushEvents()]);
    await flushInstanceHealth(endpoints); // !台账先落, 徽标才读得到本轮的结论(顺序有意义, 别并进上面那批)
    await refreshBadge();
  }
}

function headers(inst) {
  return { 'X-Hr-Token': inst.token || '' };
}

// ---------- 自动发现(计划 26-10-14-1241 S4; 自愈/可见性于 26-10-15-2357 S2) ----------
//
// 触发器: 启动时(onInstalled/onStartup)/ **任一实例拉取失败时**(1 分钟节流, Q3)/ 每 2 分钟(Q3)/
// 选项页「立即发现」。探测 = 对候选表(发现地址起连号 3 个)**并行 fetch**, 仅接受 200 + 合法
// 发现响应形态 —— 普通应用误占端口的异形应答/404/连接拒绝一律按「非本服务」忽略, 多候选同时
// 应答取最先成功者(命中端口记入状态行)。发现失败不静默(日志 + 状态行 + 结构化快照 + 徽标),
// 退路 = 手动**指定**端点(不再是「兜底」口径, Q11)。

async function readDiscoveryConfig() {
  const got = await chrome.storage.local.get({
    discoveryAddress: DEFAULT_DISCOVERY_ADDRESS,
    pairingCode: '',
    lastDiscoveryAt: 0,
  });
  return {
    discoveryAddress: String(got.discoveryAddress || '').trim(),
    pairingCode: String(got.pairingCode || '').trim(),
    lastDiscoveryAt: Number(got.lastDiscoveryAt) || 0,
  };
}

/**
 * 触发裁决(Q3): **任一实例拉取失败**即触发一次发现(1 分钟节流不变) —— 覆盖旧口径「全部实例连败」的
 * 漏网(1 死 1 活时旧口径不触发, 只能干等周期)。否则按周期(2 分钟)。发现关闭时零日志静默。
 * !实例清单为空也走周期分支(R1): 后端重启瞬间发现集可能为空, 此时连「失败即发现」都不触发,
 * 若周期分支也跳过, 连接就再也回不来。
 */
async function maybeDiscover(failCount) {
  const now = Date.now();
  const dconf = await readDiscoveryConfig();
  if (!dconf.discoveryAddress) return; // 用户显式关闭发现: 完全静默(手动指定路径是完整退路)
  if (failCount >= 1 && now - dconf.lastDiscoveryAt >= DISCOVERY_MIN_GAP_MS) {
    await runDiscovery('实例失败');
    return;
  }
  if (now - dconf.lastDiscoveryAt >= DISCOVERY_EVERY_MINUTES * 60 * 1000) {
    await runDiscovery('定期');
  }
}

/**
 * 落结构化发现快照(S2): 选项页顶部「连接状态」总览与逐候选结果都从它渲染 —— 此前发现结果只进
 * 状态栏(最后一句)与日志, 选项页拿不到, 于是「后台发现了但页面看不见」(用户实报的静默感)。
 * `answered` = 候选表**至少一个给出了 HTTP 应答** —— 徽标「重连中」与「发现失败」的边界靠它判(C4),
 * 属徽标判据所需的附加字段。收尾顺手刷一次徽标(发现是连接态的变化点)。
 */
async function noteDiscoveryResult(patch) {
  const candidates = Array.isArray(patch.candidates) ? patch.candidates : [];
  const probes = Array.isArray(patch.probes) ? patch.probes : [];
  const snapshot = {
    at: Date.now(),
    ok: Boolean(patch.ok),
    port: String(patch.port || ''),
    merged: Number(patch.merged) || 0,
    reason: String(patch.reason || ''),
    answered: Boolean(patch.answered),
    candidates: candidates.map((url, i) => ({ url: String(url), note: String((probes[i] && probes[i].note) || '') })),
  };
  try {
    await chrome.storage.local.set({ lastDiscovery: snapshot });
  } catch (e) {
    console.warn('发现快照落盘失败(下一轮再试):', e);
  }
  await refreshBadge();
}

/**
 * 跑一轮发现: 归一化发现地址 -> 候选表并行探测 -> 命中合并实例 / 401 pairing_required 标记 /
 * 全未命中明确报告(不静默)。lastDiscoveryAt 每次**尝试**后都更新(节流按尝试计);
 * 每次收尾都落结构化快照 + 刷徽标(选项页与工具栏都能看见这一轮的结论)。
 */
async function runDiscovery(trigger) {
  const dconf = await readDiscoveryConfig();
  if (!dconf.discoveryAddress) {
    return { ok: false, reason: 'disabled' }; // 显式关闭: 连手动触发也不打日志(选项页状态行会说明)
  }
  let base;
  try {
    base = normalizeDiscovery(dconf.discoveryAddress);
  } catch (e) {
    const msg = `发现地址写法不对: ${e && e.message ? e.message : e}`;
    await noteStatus({ text: msg }, 'warn');
    log('warn', '发现', msg, { 地址: dconf.discoveryAddress });
    await noteDiscoveryResult({ ok: false, reason: 'bad-address' });
    return { ok: false, reason: 'bad-address' };
  }
  const candidates = discoveryCandidates(base);
  const probes = await Promise.all(candidates.map((c) => probeCandidate(buildDiscoveryUrl(c), dconf.pairingCode)));
  await chrome.storage.local.set({ lastDiscoveryAt: Date.now() });
  const hit = probes.find((p) => p.ok);
  if (hit) {
    const cur = await chrome.storage.local.get({ instances: [] });
    const merged = mergeInstances(cur.instances, hit.data.instances);
    await chrome.storage.local.set({ instances: merged, pairingNeeded: false });
    const msg = `自动发现命中(${hit.port}): 合并 ${hit.data.instances.length} 个实例, 共 ${merged.length} 条`;
    await noteStatus({ text: msg });
    log('info', '发现', msg, { 触发: trigger || '手动', 候选: candidates.join(' / '), 命中: hit.port });
    await noteDiscoveryResult({
      ok: true, port: hit.port, merged: merged.length, candidates: candidates, probes: probes, answered: true
    });
    return { ok: true, merged: merged.length };
  }
  if (probes.some((p) => p.pairingRequired)) {
    await chrome.storage.local.set({ pairingNeeded: true });
    const msg = '发现端点要求配对码: 到选项页「自动发现」填入后端展示码(启动日志/HR 状态卡可见)';
    await noteStatus({ text: msg }, 'warn');
    log('warn', '发现', msg, { 触发: trigger || '手动' });
    await noteDiscoveryResult({ ok: false, reason: 'pairing_required', candidates: candidates, probes: probes, answered: true });
    return { ok: false, reason: 'pairing_required' };
  }
  const msg = '自动发现未命中(数据端点照常; 退路 = 选项页「手动端点」显式指定实例)';
  await noteStatus({ text: msg });
  log('warn', '发现', msg, { 触发: trigger || '手动', 候选: candidates.join(' / '), 明细: probes.map((p) => p.note).join(' | ') });
  await noteDiscoveryResult({
    ok: false, reason: 'no-hit', candidates: candidates, probes: probes, answered: probes.some((p) => p.answered)
  });
  return { ok: false, reason: 'no-hit' };
}

/**
 * 单候选探测: 仅接受 200 + 合法发现响应形态; 401 pairing_required 单独带回(触发配对提示)。
 * `answered` = 该候选**给出了 HTTP 应答**(哪怕 401/404/异形) —— 与「网络层连不上」区分开:
 * 候选全无应答才叫「发现失败」, 有应答但无可用实例只是「重连中」(C4, 后者可自愈)。
 */
async function probeCandidate(url, pairingCode) {
  const t0 = Date.now();
  try {
    const res = await fetch(url, { headers: { 'X-Hr-Pairing': pairingCode || '' } });
    if (res.status === 401) {
      const data = await res.json().catch(() => ({}));
      const err = String((data && data.error) || '');
      return {
        ok: false,
        answered: true,
        pairingRequired: pairingNeeded({ status: 401, error: err }),
        note: `401 ${err}`
      };
    }
    if (res.status !== 200) {
      return { ok: false, answered: true, note: `HTTP ${res.status}` };
    }
    const data = await res.json().catch(() => null);
    if (!validDiscoveryPayload(data)) {
      return { ok: false, answered: true, note: '异形应答(非本服务?)' };
    }
    return { ok: true, answered: true, data, port: new URL(url).port || '' };
  } catch (e) {
    log('debug', '发现', `候选探测失败: ${url}`, { 耗时: `${Date.now() - t0}ms` });
    return { ok: false, answered: false, note: '连接失败' };
  }
}

// ---------- 连接状态徽标(计划 26-10-15-2357 S2/Q4: 不静默) ----------
//
// !为什么需要: 连接失败此前只在「状态栏最后一句」与运行日志里可见 —— 不打开选项页就看不到, 用户对
// 「扩展到底还连不连得上」零感知(实报「可能静默失败」)。图标是**常驻可见信号**: 浏览器工具栏图标
// 上就有四态, 点一下进选项页看细节(chrome.action.onClicked; manifest 无 default_popup 才能收到点击)。
// !文案一律 ASCII: 徽标字号极小, 图形符号(对勾/省略号)在部分平台渲染成方框, 且 code-style 明令
// 代码禁图形符号 —— 语义靠颜色 + 悬停标题表达。
// !R4(计划 26-10-16-0214 S6): 徽标文字由浏览器固定渲染, 挡住图标且无 API 可调 —— 唯一路径是
// setIcon 重画图标本体(状态色外框, 预生成 PNG 见 scripts/gen_ext_icons.py)。文字通道折中:
// 平时徽标文本清空(纯外框零遮挡), 仅「发现失败」态追加红色 `!`(故障时恢复文字报警 + 色觉冗余)。
const BADGE = {
  unconfigured: { text: '', color: '#5a6673', label: '未配置' },
  ok: { text: '', color: '#2e7d46', label: '连接正常' },
  reconnecting: { text: '', color: '#b8802f', label: '重连中' },
  discoveryFailed: { text: '!', color: '#b0453d', label: '发现失败' },
  // 计划 26-10-29-0147 D5: 通道通、但站点没授权 —— 取数**一定全失败**, 必须抬头可见
  noSitePermission: { text: '!', color: '#b0453d', label: '站点未授权' },
};

/**
 * 徽标态推导(纯函数, 守阵直测): 五态判据见计划 §3.3 + 26-10-29-0147 D5 ——
 * 未配置(发现地址空**且**实例清单空) / 连接正常(最近一轮**至少一个实例成功**) /
 * 发现失败(候选表全无应答 **且** 无任何可用实例, C4) / 重连中(其余: 有发现地址但当前无成功实例) /
 * **站点未授权**(有实例成功, 但已判定的站点里有未授权的 —— 排在 ok 之前, 否则「连接正常」是假话)。
 */
function badgeStateOf(cfg) {
  const instances = Array.isArray(cfg.instances) ? cfg.instances : [];
  const hasDiscovery = Boolean(String(cfg.discoveryAddress || '').trim());
  if (!instances.length && !hasDiscovery) return 'unconfigured';
  const health = cfg.instanceHealth && typeof cfg.instanceHealth === 'object' ? cfg.instanceHealth : {};
  const anyOk = instances.some((e) => {
    const h = health[String((e && e.endpoint) || '')];
    return Boolean(h && h.ok);
  });
  const perms = cfg.sitePerms && typeof cfg.sitePerms === 'object' ? cfg.sitePerms : {};
  const anyDenied = Object.keys(perms).some((k) => perms[k] && perms[k].granted === false);
  // !anyOk 是前置条件: 端点本身连不上时, 「站点未授权」会盖掉更严重的连接故障 —— 那才是撒谎
  if (anyOk && anyDenied) return 'noSitePermission';
  if (anyOk) return 'ok';
  const last = cfg.lastDiscovery;
  if (hasDiscovery && last && last.ok === false && last.answered === false) return 'discoveryFailed';
  return 'reconnecting';
}

// 四态 -> 图标基础名(R4: 8 个 PNG 入库, 基础无框 = 未配置态与安装初始态共用; 判据仍是 badgeStateOf)
const BADGE_ICON = {
  unconfigured: 'icon',
  ok: 'icon-ok',
  reconnecting: 'icon-warn',
  discoveryFailed: 'icon-bad',
  noSitePermission: 'icon-bad',
};

/** 五态 -> {16, 32} 两档图标路径(纯函数, 守阵直测): 未知态回落基础图 */
function badgeIconOf(state) {
  const base = BADGE_ICON[state] || BADGE_ICON.unconfigured;
  return { '16': `icons/${base}16.png`, '32': `icons/${base}32.png` };
}

/** 按五态落图标外框 + 悬停标题; 徽标文本只在「发现失败」与「站点未授权」两态非空(都是红 `!`,
 * 语义靠悬停标题区分); 禁用时清空(不显示"看着正常"的图标) */
async function refreshBadge() {
  let cfg;
  try {
    cfg = await chrome.storage.local.get({
      enabled: true,
      instances: [],
      discoveryAddress: DEFAULT_DISCOVERY_ADDRESS,
      instanceHealth: {},
      lastDiscovery: null,
      sitePerms: {},   // 站点授权缓存(判据见 badgeStateOf): 徽标是同步纯函数, 只能读缓存
    });
  } catch (e) {
    return; // 读不到就不动徽标: 状态信号不值得赌主流程
  }
  const state = cfg.enabled ? badgeStateOf(cfg) : 'unconfigured';
  const spec = BADGE[state];
  const alarmed = cfg.enabled && state === 'discoveryFailed';
  try {
    await chrome.action.setBadgeText({ text: alarmed ? spec.text : '' });
    if (alarmed) await chrome.action.setBadgeBackgroundColor({ color: spec.color });
    await chrome.action.setIcon({ path: badgeIconOf(state) });
    await chrome.action.setTitle({ title: `auto-qb HR 取数代理 - ${cfg.enabled ? spec.label : '已停用'}` });
  } catch (e) {
    // 徽标 API 在个别平台/权限组合下不可用: 吞掉(连接态另有状态栏与日志, 不为此反噬主流程)
  }
}

/** 图标点击(无 default_popup) -> 打开选项页: 徽标报警后用户的第一动作就该是「看一眼」 */
if (chrome.action && chrome.action.onClicked) {
  chrome.action.onClicked.addListener(() => {
    chrome.runtime.openOptionsPage().catch((e) => log('warn', '系统', `打开选项页失败: ${e && e.message ? e.message : e}`));
  });
}

/**
 * 取数端点归一化(直接复用 normalize.js): 旧版本存下来的值可能是裸 host:port, 而
 * `fetch("127.0.0.1:8788/x")` 会被当成**相对地址**解析到扩展自己的 origin, 失败时只报一句
 * `TypeError: Failed to fetch`, 完全查不出原因。不合法(非回环/无端口)时返回空串, 由调用方报错。
 */
function safeEndpoint(raw) {
  try {
    return normalizeEndpoint(raw);
  } catch (e) {
    return '';
  }
}

/** 网络层失败只会给 TypeError: Failed to fetch —— 替用户展開成可操作的排查清单 */
function explainFetchError(url, e) {
  const msg = String((e && e.message) || e);
  if (msg.includes('Failed to fetch')) {
    return (
      `连不上 ${url}。逐条确认: 1. 后端主程序在跑吗(--hr-once 是只读走查, **不会**起端点); ` +
      '2. config.yml 里 hr_check.enabled=true、至少一个站点 mode != off、且 hr_check.channel.enabled=true' +
      '(三者缺一, 端点根本不会启动); 3. 端口对不对(后端启动日志会打「HR 取数通道端点已启动: http://127.0.0.1:<端口>」);' +
      '4. 同机多实例端口是否撞车'
    );
  }
  return msg;
}

// ---------- 连接失败降噪(故障期只打头尾, 2026-09-28 用户实报) ----------
//
// !为什么需要: 轮询 1 分钟一轮, 后端不在跑时每轮都打一条**全量排查清单** ERROR —— 日志环
// (默认 1000 条)几小时就被同一句话灌满, 有用的历史全被冲掉。故按「故障期」记连败轮数:
//   · 首次失败: 全量 ERROR(排查清单照旧);
//   · 连败期: 降为 debug 短句(默认记录级别 info 下不落盘), 每连败 30 轮(约半小时)重打一次全量,
//     防「彻底失联无感」;
//   · 恢复(端点给出**任何** HTTP 应答, 含 401/5xx —— 应答即连接已通): INFO 一句恢复 + 连败轮数。
// 连败数必须落 storage.local: MV3 的 SW 随时被回收, 内存态活不过一次回收, 落内存等于没降噪。
const NET_FAIL_KEY = 'netFailStreak';
const NET_FAIL_REMIND_EVERY = 30;

/** 连败轮数 +1 并落盘(键=任务清单 URL), 返回最新连败轮数; storage 不可用就退化为现状(每轮全量) */
async function bumpNetFailStreak(key) {
  let n = 1;
  try {
    const got = await chrome.storage.local.get({ [NET_FAIL_KEY]: {} });
    const all = got[NET_FAIL_KEY] || {};
    n = ((all[key] && all[key].n) || 0) + 1;
    all[key] = { n: n };
    await chrome.storage.local.set({ [NET_FAIL_KEY]: all });
  } catch (e) {
    // 存不进去就不降噪: 宁可日志回到复读机, 也不为降噪赌主流程
  }
  return n;
}

/** 故障期结束(端点应答了): 清连败计数并返回此前轮数(0=本来就没在故障期, 无需打恢复) */
async function clearNetFailStreak(key) {
  let prev = 0;
  try {
    const got = await chrome.storage.local.get({ [NET_FAIL_KEY]: {} });
    const all = got[NET_FAIL_KEY] || {};
    prev = (all[key] && all[key].n) || 0;
    if (prev) {
      delete all[key];
      await chrome.storage.local.set({ [NET_FAIL_KEY]: all });
    }
  } catch (e) {}
  return prev;
}

// ---------- 扩展侧硬上限(第二道闸: 后端出错时的兜底) ----------
//
// !为什么扩展也要限: 后端有自己的频控(间隔 + 两级配额 + 熔断), 但那是**同一个进程里的代码**。
// 它写错 / 配置被改坏 / 有人手工灌任务时, 浏览器会把站点打爆 —— 而承受后果的是用户的账号。
// 故这里加一道**独立**计数: 口径与阈值见 site-caps.js(唯一事实源), 用户可在选项页看到用量。
// 超限时**拒绝该次请求**并如实回传 kind='ext-quota'(后端据此让位, 不计失败、不推熔断)。

/** 计数窗口键(本地时区, 与后端 hour_key/day_key 同口径, 便于对账) */
function pad2(n) {
  return String(n).padStart(2, '0');
}

function hourKey(now) {
  const d = new Date(now);
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}`;
}

function dayKey(now) {
  const d = new Date(now);
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

function secondsToNextHour(now) {
  const next = new Date(now);
  next.setMinutes(0, 0, 0);
  next.setHours(new Date(now).getHours() + 1);
  return Math.max(1, Math.round((next.getTime() - now) / 1000));
}

function secondsToNextDay(now) {
  const next = new Date(now);
  next.setHours(0, 0, 0, 0);
  next.setDate(new Date(now).getDate() + 1);
  return Math.max(1, Math.round((next.getTime() - now) / 1000));
}

function hostOf(url) {
  try {
    return new URL(url).hostname;
  } catch (e) {
    return '';
  }
}

/** `https://pt.example.com/x` -> `https://pt.example.com`(权限判定与展示都以 origin 为单位) */
function originOf(url) {
  try {
    const u = new URL(url);
    return `${u.protocol}//${u.hostname}`;
  } catch (e) {
    return '';
  }
}

// ---------- 站点权限预检(计划 26-10-29-0147 W1) ----------
//
// !为什么要在取数**之前**判: `fetch` 对「没有该站 host 权限」与「DNS/代理不通」给的是**同一句**
// `TypeError: Failed to fetch`, 事后归因只能猜。而 `chrome.permissions.getAll()` 能**明确**回答
// 「我到底有没有这个站」, 于是「缺权限」从一句猜谜变成一条可展示、可回传的事实。
// 生产实证 2026-10-28: 扩展重装后可选站点权限被重置, 三档全失败 12h, 日志却一直写「页面取数失败」。

/** 把匹配模式拆成 {scheme, host}; 非法返回 null(裸域名 / 缺 scheme 的一律不认) */
function splitPattern(pat) {
  const m = /^(\*|https?|file|ftp):\/\/([^/]+)/i.exec(String(pat || '').trim());
  if (!m) return null;
  return { scheme: m[1].toLowerCase(), host: m[2].toLowerCase() };
}

/**
 * 该 origin 是否已被授予(纯函数, 守阵直测)
 *
 * !不要用 `chrome.permissions.contains({origins: [...]})` 判多个: 它只在**全部**都授予时返回 true,
 * 于是「一个站没授权」会被读成「全都授权了」(或反过来), 整个逐站展示就失去意义。
 * 这里改成「拿全量已授予模式 + 逐个匹配」。
 */
function originGranted(origin, patterns) {
  const target = splitPattern(`${String(origin || '').replace(/\/+$/, '')}/*`);
  if (!target) return false;
  for (const pat of patterns || []) {
    const got = splitPattern(pat);
    if (!got) continue;
    if (got.scheme !== '*' && got.scheme !== target.scheme) continue;
    if (got.host === '*' || got.host === target.host) return true;
    // `*.example.com` 覆盖子域(Chrome 的匹配模式语义), 但不覆盖 example.com 本身
    if (got.host.indexOf('*.') === 0 && target.host.slice(-(got.host.length - 1)) === got.host.slice(1)) return true;
  }
  return false;
}

/**
 * 站点授权现状: true=已授权 / false=明确未授权 / null=无法判定(API 不可用或 URL 非法)
 *
 * !null 与 false 必须分开: 测试桩与老环境没有 `permissions.getAll`, 把「判不了」当成「没授权」
 * 会让所有取数被误拒 —— 判不了就照旧走, 由 `Failed to fetch` 兜底归因。
 */
async function siteGranted(url) {
  const origin = originOf(url);
  if (!origin) return null;
  if (!chrome.permissions || typeof chrome.permissions.getAll !== 'function') return null;
  let all;
  try {
    all = await chrome.permissions.getAll();
  } catch (e) {
    return null;
  }
  return originGranted(origin, (all && all.origins) || []);
}

/** 把一次判定写进 storage 缓存(徽标是同步纯函数, 只能读缓存; 选项页也读这份) */
async function noteSitePerm(origin, granted) {
  if (!origin) return;
  try {
    const got = await chrome.storage.local.get({ sitePerms: {} });
    const perms = Object.assign({}, got.sitePerms || {});
    perms[origin] = { granted: Boolean(granted), checkedAt: Date.now() };
    await chrome.storage.local.set({ sitePerms: perms });
  } catch (e) {
    // 缓存写不进去不影响取数: 展示层降级为「不知道」, 不为此反噬主流程
  }
}

/** 请求日志的标准明细(类型/站点/url/耗时) + 调用方补充 —— 每条请求带同一套字段, 排查才有可比性 */
function reqDetail(reqType, url, t0, extra) {
  return Object.assign(
    { 类型: reqType, 站点: hostOf(url), url: url, 耗时: t0 === undefined ? undefined : `${Date.now() - t0}ms` },
    extra || {}
  );
}

/** 超限(或将要超限)时抛它 —— 与「取数失败」区分开: 后端收到后只让位, 不计失败、不告警级联 */
class ExtQuotaError extends Error {
  constructor(message, retryAfter) {
    super(message);
    this.name = 'ExtQuotaError';
    this.retryAfter = Math.round(retryAfter || 0);
  }
}

/** 取 .torrent 时拿到的是 HTML(登录页/未登录): 抛它让后端按「登录失效」处置(不计取数失败) */
class LoginPageError extends Error {
  constructor(message) {
    super(message);
    this.name = 'LoginPageError';
    this.kind = 'login-page';
  }
}

/**
 * 领一次额度: 超限返回 {ok:false, reason, retryAfter}; 否则计数 +1 并返回 {ok:true}。
 * 拿不到域名(畸形 URL)时不计数直接放行 —— 后端有 URL 白名单, 正常不会走到这类输入。
 */
async function takeAllowance(kind, url) {
  const cap = SITE_CAPS[kind];
  const host = hostOf(url);
  if (!cap || !host) return { ok: true, host: host };
  const now = Date.now();
  const hk = hourKey(now);
  const dk = dayKey(now);
  const got = await chrome.storage.local.get({ [SITE_LEDGER_KEY]: {} });
  const ledger = got[SITE_LEDGER_KEY] || {};
  const site = ledger[host] || {};
  const rec = site[kind] || {};
  const usedHour = rec.hk === hk ? (rec.hour || 0) : 0; // 窗口键不同 = 新窗口, 计数从头算
  const usedDay = rec.dk === dk ? (rec.day || 0) : 0;
  if (usedHour + 1 > cap.perHour) {
    return { ok: false, host: host, retryAfter: secondsToNextHour(now), reason: `${cap.label} 本小时达硬上限 ${cap.perHour} 次` };
  }
  if (usedDay + 1 > cap.perDay) {
    return { ok: false, host: host, retryAfter: secondsToNextDay(now), reason: `${cap.label} 本日达硬上限 ${cap.perDay} 次` };
  }
  site[kind] = { hk: hk, dk: dk, hour: usedHour + 1, day: usedDay + 1 };
  ledger[host] = site;
  await chrome.storage.local.set({ [SITE_LEDGER_KEY]: ledger });
  return { ok: true, host: host, used: usedHour + 1, cap: cap.perHour };
}

/** 取数前的最后一道检查: 超限即拒发(并把原因写进状态栏, 用户能看出是"第二道闸"挡的) */
async function requireAllowance(kind, url) {
  const got = await takeAllowance(kind, url);
  if (got.ok) return got;
  await noteStatus(
    { text: `扩展侧硬上限挡下(${got.reason}); 后端频控可能失效(也可能扩展上限本就低于后端配额) —— 本次请求未发出` },
    'warn'
  );
  log('warn', '配额', `扩展侧硬上限拒发(kind=${kind}): ${got.reason}`, { 站点: got.host, url: url });
  throw new ExtQuotaError(`${got.reason}(host=${got.host})`, got.retryAfter);
}

// ---------- 实例健康台账(计划 26-10-15-2357 S2: 供选项页「疑似失效」标记) ----------
//
// !为什么需要: 实例列表此前只有 [自动] 徽标, 看不出**哪条在失败** —— 手动条目连续拉不通时用户既
// 不知道, 也不知道该不该删(而计划明令「只提示不代删」)。台账按端点记最近一轮的成败与**连续失败轮数**,
// 选项页据此打「疑似失效」标记(C3 阈值 >=3 轮, 免得瞬时抖动误报)。
// !落盘纪律(R3): 内存累积、pollAll 收尾**按轮整份写一次**(不每请求写, 免 storage 写风暴);
// 剪掉已不在实例清单里的端点, 防死端点台账堆积。MV3 的 SW 随时被回收 ⇒ 下一轮首写前先读回来。
const HEALTH_KEY = 'instanceHealth';
let healthBuf = null;
let healthInitPromise = null;

function initHealthBuffer() {
  if (!healthInitPromise) {
    healthInitPromise = chrome.storage.local
      .get({ [HEALTH_KEY]: {} })
      .then((got) => {
        const all = got[HEALTH_KEY];
        healthBuf = all && typeof all === 'object' && !Array.isArray(all) ? all : {};
      })
      .catch(() => {
        healthBuf = healthBuf || {}; // 读不到就当空: 丢一段健康台账可以接受, 取数主流程不能被它卡住
      });
  }
  return healthInitPromise;
}

/** 记一轮实例健康(仅内存): 连续失败计数供「疑似失效」阈值判定; state 为结构化态(计划 26-10-16-0214 S2) */
function noteInstanceHealth(endpoint, ok, note, state) {
  const ep = String(endpoint || '');
  if (!ep) return Promise.resolve(); // 端点写不对的条目没有可用的键, 由轮询文案自己报
  return initHealthBuffer()
    .then(() => {
      const prev = healthBuf[ep] || {};
      healthBuf[ep] = {
        ok: Boolean(ok),
        at: Date.now(),
        note: String(note || ''),
        // state ∈ ok / 401 / 403 / http / down / bad-endpoint; 旧条目无此键按 C2 降级(ok 布尔)
        state: state ? String(state) : '',
        failStreak: ok ? 0 : (Number(prev.failStreak) || 0) + 1,
      };
    })
    .catch(() => {});
}

/** 整份落盘并剪掉已不在实例清单里的端点(endpoints 为 null 时不剪: 调用方没给出清单就别猜) */
function flushInstanceHealth(endpoints) {
  if (!healthInitPromise) return Promise.resolve();
  return initHealthBuffer()
    .then(() => {
      if (Array.isArray(endpoints)) {
        const allowed = new Set(endpoints.map((e) => String(e || '')));
        for (const ep of Object.keys(healthBuf)) {
          if (!allowed.has(ep)) delete healthBuf[ep];
        }
      }
      return chrome.storage.local.set({ [HEALTH_KEY]: healthBuf }).catch((e) => {
        console.warn('实例健康台账落盘失败(等下一轮再试):', e);
      });
    })
    .catch(() => {});
}

/**
 * 逐实例拉任务 + 记健康台账。拉取本身的实现见 pollInstanceOnce(全部失败路径都返回 ok/line,
 * 台账直接取这份结论 —— 不另设一套成败判定, 免得两处口径漂移)。
 */
async function pollInstance(inst) {
  const outcome = await pollInstanceOnce(inst);
  await noteInstanceHealth(inst && inst.endpoint, outcome.ok, outcome.line, outcome.state);
  return outcome;
}

async function pollInstanceOnce(inst) {
  const label = inst.name || inst.endpoint || '(未命名)';
  const base = safeEndpoint(inst.endpoint);
  if (!base) {
    log('warn', '请求', `${label}: 端点写法不对, 本实例跳过`, { 端点: inst.endpoint });
    return { ok: false, state: 'bad-endpoint', line: `${label}: 端点写法不对(需 127.0.0.1:<端口> 这种带端口的形式) —— 到选项页重新保存会自动纠正` };
  }
  const tasksUrl = `${base}/api/hr/tasks`;
  const t0 = Date.now();
  let res;
  try {
    res = await fetch(tasksUrl, { headers: headers(inst) });
  } catch (e) {
    const reason = explainFetchError(tasksUrl, e);
    const detail = reqDetail('拉任务清单', tasksUrl, t0, { 实例: label });
    const streak = await bumpNetFailStreak(tasksUrl);
    if (streak === 1) {
      log('error', '请求', `拉任务清单失败: ${reason}`, detail); // 首报: 全量排查清单
    } else if (streak % NET_FAIL_REMIND_EVERY === 0) {
      log('error', '请求', `拉任务清单失败(已连续 ${streak} 轮): ${reason}`, detail);
    } else {
      log('debug', '请求', `拉任务清单失败(已连续 ${streak} 轮, 降噪: 排查清单见首报)`, detail);
    }
    return { ok: false, state: 'down', line: `${label}: ${reason}` };
  }
  // 端点给了应答(含 401/5xx —— 应答即连接已通): 关故障期; 之前挂着故障就补一句恢复
  const prevFail = await clearNetFailStreak(tasksUrl);
  if (prevFail > 0) {
    log('info', '请求', `端点恢复(此前连续失败 ${prevFail} 轮)`, reqDetail('拉任务清单', tasksUrl, t0, { 实例: label }));
  }
  if (res.status === 401) {
    // 该实例没启用取数通道 / token 不匹配 —— 属正常路径, **不重试**(后端会自己告警)
    log('warn', '请求', '端点拒绝(401, token 或 channel.enabled 未开)', reqDetail('拉任务清单', tasksUrl, t0, { 实例: label, HTTP: '401' }));
    // 401 = 端点有应答(连接是通的), 属配置态而非连接失败 —— ok:true, 不触发「全失败」发现;
    // state:'401' 供选项页行级标红(要人改 token/extension_id), 徽标判据不受影响(S2: 自愈逻辑不动)
    return { ok: true, state: '401', line: `${label}: 端点拒绝(401, token 或 channel.enabled 未开)` };
  }
  if (!res.ok) {
    log('error', '请求', `拉清单失败 HTTP ${res.status}`, reqDetail('拉任务清单', tasksUrl, t0, { 实例: label, HTTP: String(res.status) }));
    return { ok: false, state: 'http', line: `${label}: 拉清单失败 HTTP ${res.status}` };
  }
  const data = await res.json();
  const tasks = Array.isArray(data.tasks) ? data.tasks : [];
  log('info', '命令', `任务清单到手: ${tasks.length} 条`, reqDetail('拉任务清单', tasksUrl, t0, { 实例: label, HTTP: '200' }));
  if (!tasks.length) return { ok: true, state: 'ok', line: `${label}: 无任务` }; // 与旧行为一致: 无任务**不回传**(不打后端的 result 端点)
  const results = [];
  const rendered = [];
  for (const task of tasks) {
    log('info', '命令', `收到命令: kind=${task.kind} id=${task.id}`, { 站点: hostOf(task.url), url: task.url, 实例: label });
    const got = await runTask(task);
    if (got.rendered) rendered.push(task.url);
    results.push(got.payload);
  }
  const resultUrl = `${base}/api/hr/result`;
  const pt0 = Date.now();
  let post;
  try {
    post = await fetch(resultUrl, {
      method: 'POST',
      headers: Object.assign({ 'Content-Type': 'application/json' }, headers(inst)),
      body: JSON.stringify({ results }),
    });
  } catch (e) {
    log('error', '请求', `回传失败: ${explainFetchError(base, e)}`, reqDetail('回传结果', resultUrl, pt0, { 实例: label, 条数: results.length }));
    return { ok: false, state: 'http', line: `${label}: 取到 ${results.length} 条但回传失败 —— ${explainFetchError(base, e)}` };
  }
  // 「返回后端结果」: 响应体也留一份截断快照 —— 对账「扩展说发了, 后端说没收到」就靠它
  const respText = await post.text().catch(() => '');
  const okCount = results.filter((r) => r.ok).length;
  const quotaCount = results.filter((r) => r.kind === 'ext-quota').length;
  log(
    post.ok ? 'info' : 'error',
    '请求',
    `回传 ${results.length} 条(成功 ${okCount}${quotaCount ? `, 配额让位 ${quotaCount}` : ''}) → HTTP ${post.status}`,
    reqDetail('回传结果', resultUrl, pt0, { 实例: label, HTTP: String(post.status), 后端响应: respText })
  );
  const how = rendered.length ? `其中 ${rendered.length} 条走渲染` : '全部直取(无界面)';
  const blocked = quotaCount ? `; 扩展侧硬上限挡下 ${quotaCount} 条(后端频控可能失效)` : '';
  return { ok: true, state: 'ok', line: `${label}: 取 ${results.length} 条(成功 ${okCount}; ${how})${blocked}, 回传 HTTP ${post.status}` };
}

/**
 * 单实例**只读探测**(计划 26-10-16-0214 S2/R3): 复用 pollInstanceOnce 的「拉任务清单」一步
 * (GET /api/hr/tasks, 只读, 不执行任务 —— C3), 判成败/结构化 state 的口径与轮询完全一致,
 * 结论经 noteInstanceHealth 落台账 —— 选项页实例表「状态」列的单一数据源。
 * !不碰 netFailStreak / 不触发发现 / 不动徽标: 探测是用户手势下的即时诊断, 不是轮询替代品。
 */
async function probeInstance(inst) {
  const label = inst.name || inst.endpoint || '(未命名)';
  const base = safeEndpoint(inst.endpoint);
  if (!base) {
    const line = `${label}: 端点写法不对(需 127.0.0.1:<端口> 这种带端口的形式)`;
    await noteInstanceHealth(inst && inst.endpoint, false, line, 'bad-endpoint');
    return { ok: false, state: 'bad-endpoint', line };
  }
  const tasksUrl = `${base}/api/hr/tasks`;
  const t0 = Date.now();
  let res;
  try {
    res = await fetch(tasksUrl, { headers: headers(inst) });
  } catch (e) {
    const line = `${label}: 连不上端点(${e && e.message ? e.message : e})`;
    log('debug', '请求', `探测失败: ${tasksUrl}`, reqDetail('探测', tasksUrl, t0, { 实例: label }));
    await noteInstanceHealth(inst && inst.endpoint, false, line, 'down');
    return { ok: false, state: 'down', line };
  }
  if (res.status === 401) {
    // 与轮询同口径: 401 = 端点有应答, 记 ok(配置态, 不触发发现); state 供选项页标红
    const line = `${label}: 端点拒绝(401, token 或 channel.enabled 未开)`;
    log('debug', '请求', '探测: 端点拒绝(401)', reqDetail('探测', tasksUrl, t0, { 实例: label, HTTP: '401' }));
    await noteInstanceHealth(inst && inst.endpoint, true, line, '401');
    return { ok: true, state: '401', line };
  }
  if (!res.ok) {
    const line = `${label}: 拉清单失败 HTTP ${res.status}`;
    log('debug', '请求', `探测失败 HTTP ${res.status}`, reqDetail('探测', tasksUrl, t0, { 实例: label, HTTP: String(res.status) }));
    await noteInstanceHealth(inst && inst.endpoint, false, line, 'http');
    return { ok: false, state: 'http', line };
  }
  const data = await res.json().catch(() => ({}));
  const n = Array.isArray(data.tasks) ? data.tasks.length : 0;
  const line = `${label}: 探测可达(本批 ${n} 条任务)`;
  log('debug', '请求', `探测可达(本批 ${n} 条任务)`, reqDetail('探测', tasksUrl, t0, { 实例: label, HTTP: '200' }));
  await noteInstanceHealth(inst && inst.endpoint, true, line, 'ok');
  return { ok: true, state: 'ok', line };
}

/**
 * 「重测全部」(选项页 probe-all): 逐实例只读探测, 收尾整份落台账 —— 选项页经 storage.onChanged
 * 即时刷新实例表状态列(C1 单一写入口: 台账唯一写者是后台, 选项页只读 + 消息触发)。
 * probe-one 已随计划 R3 取消(逐实例探测统一由本消息承载)。
 */
async function probeAll() {
  const conf = await readConfig();
  const endpoints = conf.instances.map((e) => String((e && e.endpoint) || ''));
  const results = [];
  for (const inst of conf.instances) {
    try {
      results.push(await probeInstance(inst));
    } catch (e) {
      results.push({ ok: false, state: 'http', line: `${inst.name || inst.endpoint}: 探测异常 ${e}` });
    }
  }
  await flushInstanceHealth(endpoints); // !立刻落盘: 选项页 onChanged 通道要读得到本轮结论
  return results;
}

/**
 * 页面取数: **先无界面直取**(service worker 的 fetch 带站点 cookie, 零标签零窗口),
 * 只有当拿到的内容「看起来没渲染出来」时才退到离屏窗口拿 DOM。
 *
 * !为什么要这样: 开任何界面都会打扰用户, 而用户已实报两次 —— 先是「抓数据时打开新标签」
 * (`tabs.create({active:false})` 不保证窗口不被抬起来), 改成自建隐藏窗口后又变成「打开新窗口」
 * (`state:'minimized'` 在用户平台上仍会先显示出来)。而站点侧页面(NexusPHP 这类)本来就是
 * **服务端渲染**的表格, 直取即可; 需要 JS 的站点才走渲染通道。
 */
async function pageText(url) {
  const html = await fetchText(url);
  if (!needsRender(html)) return { text: html, rendered: false };
  await noteStatus({ text: `直取到的内容不像已登录的页面, 改用离屏窗口渲染: ${url}` });
  return { text: await pageSnapshot(url), rendered: true };
}

/** 直取(无界面): 与 .torrent 同一条路 —— service worker 发请求, `credentials:'include'` 带站点 cookie */
async function fetchText(url) {
  await requireAllowance('page', url);
  const t0 = Date.now();
  const res = await fetch(url, { credentials: 'include' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`); // 失败由 runTask 的 catch 统一记 error, 这层不重复记
  const text = await res.text();
  if (!text) throw new Error('返回内容为空');
  log('info', '请求', `页面直取成功(${text.length} 字符)`, reqDetail('页面直取', url, t0, { HTTP: '200', 字符数: String(text.length) }));
  pushEvent({ host: hostOf(url), kind: 'page', ok: true, status: 200, ms: Date.now() - t0, bytes: text.length, tag: 'ok' });
  return text;
}

/**
 * 直取的内容该不该改用渲染通道拿 —— 两个**通用结构信号**(不做站点解析):
 * 1. 没表格 ⇒ 多半要 JS 渲染, 或命中了挑战页;
 * 2. 有密码输入框 ⇒ 拿到的是登录页。!第二种是 SameSite 的安全网: 无 `SameSite` 属性的 cookie 按
 *    Lax 对待, 而扩展发起的 fetch 算**跨站**请求 ⇒ 有可能不带 cookie 而拿到登录页。
 *    这时必须升级到渲染通道(那是真正的顶层导航, 一定带 cookie), 否则会把「未登录」误报成站点改版。
 */
function needsRender(html) {
  return !hasTable(html) || /<input[^>]+type=["']?password/i.test(html);
}

/** 传输层粗判(不是站点解析): 连 `<table>` 都没有 ⇒ 多半要 JS 渲染, 或命中了挑战页 */
function hasTable(html) {
  return typeof html === 'string' && /<table[\s>]/i.test(html);
}

async function runTask(task) {
  const t0 = Date.now();
  log('debug', '任务', `开始执行 id=${task.id}(kind=${task.kind})`, { 站点: hostOf(task.url), url: task.url });
  const origin = originOf(task.url);
  // ---- 取数前预检站点权限(计划 26-10-29-0147 W1/D1) ----
  // 没权限时**一个字节都不发**(发也发不出去), 直接回 kind=no-permission: 后端据此归通道层,
  // 用户看到的是「去扩展选项页授权」而不是「站点改版」。
  const grant = await siteGranted(task.url);
  if (grant !== null) await noteSitePerm(origin, grant);
  if (grant === false) {
    const msg = `站点未授权(${origin}): 到扩展选项页 →「站点权限」勾选该站 → 点「申请勾选站点的权限」`;
    log('warn', '任务', `任务 ${task.id} 跳过(未授权): ${msg}`, { 站点: hostOf(task.url), url: task.url });
    pushEvent({ host: hostOf(task.url), kind: task.kind, ok: false, ms: 0, tag: 'no-permission', note: msg });
    return { rendered: false, payload: { id: task.id, ok: false, url: task.url, error: msg, kind: 'no-permission' } };
  }
  try {
    if (task.kind === 'page') {
      const page = await pageText(task.url);
      return { rendered: page.rendered, payload: { id: task.id, ok: true, status: 200, url: task.url, text: page.text } };
    }
    const body = await fetchBinary(task.url);
    return { rendered: false, payload: { id: task.id, ok: true, status: 200, url: task.url, body_b64: body } };
  } catch (e) {
    const emsg = String(e && e.message ? e.message : e);
    // 「预检说已授权、fetch 仍报 Failed to fetch」= 站点请求在网络层就挂了(DNS/代理/断网)。
    // 归因成 kind=network: 与「缺权限」同属通道层但**动作不同**(查网络 vs 去授权), 见计划 D3。
    const isNetFail = grant === true && emsg.indexOf('Failed to fetch') >= 0;
    // 配额拒发在 requireAllowance 里已记 warn, 不重复; 登录页降半级记 warn(不是故障, 是要人处置)
    if (!(e instanceof ExtQuotaError)) {
      log(e instanceof LoginPageError || isNetFail ? 'warn' : 'error', '任务', `任务 ${task.id} 失败(kind=${task.kind}): ${emsg}`, {
        站点: hostOf(task.url),
        url: task.url,
      });
    }
    // 事件环与日志同源双写: quota/login/no-permission/network/error 五类失败都进表
    pushEvent({
      host: hostOf(task.url),
      kind: task.kind,
      ok: false,
      ms: Date.now() - t0,
      tag: e instanceof ExtQuotaError ? 'quota' : e instanceof LoginPageError ? 'login' : isNetFail ? 'network' : 'error',
      note: emsg,
    });
    const payload = { id: task.id, ok: false, url: task.url, error: emsg };
    if (e instanceof ExtQuotaError) {
      // 扩展侧硬上限: 让后端能把它与「取数失败」区分开(前者只让位, 后者才计失败/熔断)
      payload.kind = 'ext-quota';
      payload.retry_after = e.retryAfter || 0;
    } else if (e instanceof LoginPageError) {
      // 登录页: 后端按「HR 登录失效」处置(不计失败 / 不推熔断 / 每站报一次并给动作)
      payload.kind = 'login-page';
    } else if (isNetFail) {
      // 网络层失败: 后端归通道层(不计档位失败 / 不带「页面改版」前缀), 文案指向网络/代理
      payload.kind = 'network';
    }
    return { rendered: false, payload: payload };
  }
}

/**
 * 在**隐藏窗口**里取渲染后 DOM: 带登录态、能过挑战页、不抢焦点、不占用用户窗口
 *
 * !为什么不能直接在用户自己的窗口里 `chrome.tabs.create({ active: false })`:
 * `active:false` 只保证「不是那个窗口的活动标签」, **不保证窗口不被抬起来** —— 扩展被 alarm 唤醒时
 * 用户往往正在别的程序里, Chrome 仍会把窗口连同新标签一起显示出来(2026-09-25 实报 "打开新标签");
 * 改成 `state:'minimized'` 的自建窗口后, 用户又实报 "打开新窗口" —— 最小化在部分平台上仍会先显示一下。
 * 故这条路径只当**兜底**: 真正隐形靠 **离屏坐标 + popup(不进任务栏) + 不聚焦** 三重手段。
 */
async function pageSnapshot(url) {
  await requireAllowance('page', url); // 渲染是**第二次**访问同一站(顶层导航), 同样计额
  const t0 = Date.now();
  log('info', '请求', '离屏窗口渲染开始', reqDetail('页面渲染(离屏窗口)', url));
  const restoreFocus = await focusGuard();
  const win = await createOffscreenWindow(url);
  const tabId = win.tabs && win.tabs[0] ? win.tabs[0].id : 0;
  try {
    if (!tabId) throw new Error('离屏窗口没拿到标签页');
    await waitForComplete(tabId, PAGE_LOAD_TIMEOUT_MS);
    await sleep(PAGE_SETTLE_MS);
    const frames = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => document.documentElement.outerHTML,
    });
    const html = frames && frames[0] ? frames[0].result : '';
    if (!html) throw new Error('页面为空(未授予站点权限?)');
    log('info', '请求', `渲染取到 DOM(${html.length} 字符)`, reqDetail('页面渲染(离屏窗口)', url, t0, { 字符数: String(html.length) }));
    // 渲染是同一任务的**第二次**真实站点访问(计额也第二次), 事件里标注出来便于对账用量
    pushEvent({ host: hostOf(url), kind: 'page', ok: true, status: 200, ms: Date.now() - t0, bytes: html.length, tag: 'ok', note: '离屏渲染' });
    return html;
  } finally {
    await chrome.windows.remove(win.id).catch(() => {}); // 连窗口带标签一起删: 不留脏窗口
    const note = await restoreFocus();
    if (note) await noteStatus({ text: note });
  }
}

/** 离屏 + 不聚焦 + 不进任务栏(popup): 三重手段都是为了用户看不见它(逐个降级试) */
async function createOffscreenWindow(url) {
  const base = { url, focused: false, left: OFFSCREEN_X, top: OFFSCREEN_Y, width: 900, height: 700 };
  const attempts = [
    Object.assign({ type: 'popup', state: 'minimized' }, base),
    Object.assign({ type: 'popup' }, base),
    Object.assign({ state: 'minimized' }, base),
  ];
  let lastError = null;
  for (const options of attempts) {
    try {
      return await chrome.windows.create(options);
    } catch (e) {
      lastError = e; // 某些平台不接受 popup / 不接受创建时就最小化 ⇒ 继续降级
    }
  }
  throw lastError || new Error('建离屏窗口失败');
}

/**
 * 焦点守卫: 新建窗口在个别平台仍会把浏览器抬到前台 ⇒ 记下**原聚焦窗口**, 取完还回去。
 * 只还焦点, 不关不切用户自己的窗口与标签。
 */
async function focusGuard() {
  const before = await chrome.windows.getLastFocused().catch(() => null);
  return async function restore() {
    if (!before || !before.id) return '';
    const now = await chrome.windows.getLastFocused().catch(() => null);
    if (!now || now.id === before.id) return '';
    const ok = await chrome.windows.update(before.id, { focused: true }).then(() => true).catch(() => false);
    return ok ? `取数后已把焦点还回原窗口(${before.id})` : '';
  };
}

/** 取 .torrent 二进制: 由 service worker 自己发(credentials include 带上站点 cookie)
 *
 * !拿到 HTML 必须报「登录页」而不是原样回传: 与页面直取的 needsRender 同一个根因(SameSite 剥
 * cookie / 登录态失效会让 download.php 返回登录页), 但二进制没有解析层兜底 —— 不检测的话,
 * 后端只会说「不是合法 .torrent」并烧掉该 tid 的重试额度(3 次后冷却 12h), 真因被埋掉。
 */
async function fetchBinary(url) {
  await requireAllowance('torrent', url);
  const t0 = Date.now();
  const res = await fetch(url, { credentials: 'include' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const buf = new Uint8Array(await res.arrayBuffer());
  if (!buf.length) throw new Error('返回内容为空');
  const contentType = ((res.headers && typeof res.headers.get === 'function' && res.headers.get('content-type')) || '').toLowerCase();
  const head = new TextDecoder().decode(buf.subarray(0, 64)).trimStart().toLowerCase();
  if (contentType.includes('text/html') || head.startsWith('<!doctype') || head.startsWith('<html')) {
    throw new LoginPageError('download.php 返回 HTML(疑似登录页/未登录 —— 请在浏览器里登录该站点)');
  }
  log('info', '请求', `种子下载成功(${buf.length} 字节)`, reqDetail('种子下载', url, t0, { HTTP: '200', 字节数: String(buf.length) }));
  pushEvent({ host: hostOf(url), kind: 'torrent', ok: true, status: 200, ms: Date.now() - t0, bytes: buf.length, tag: 'ok' });
  return toBase64(buf);
}

function waitForComplete(tabId, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const check = async () => {
      const tab = await chrome.tabs.get(tabId).catch(() => null);
      if (!tab) return reject(new Error('标签页已关闭'));
      if (tab.status === 'complete') return resolve();
      if (Date.now() > deadline) return reject(new Error('页面加载超时(需人工过挑战页?)'));
      setTimeout(check, 300);
    };
    check();
  });
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

/** 分块 base64, 避免 String.fromCharCode(...big) 爆栈 */
function toBase64(bytes) {
  const chunk = 0x8000;
  let binary = '';
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}
