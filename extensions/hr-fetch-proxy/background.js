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
// 运行日志(分级 + 环形上限, 选项页④区过滤查看)也落 chrome.storage.local —— 见下方「运行日志」节。
// 地址归一化共用 normalize.js(选项页用 <script> 载入, 这里用 importScripts —— 同一份代码)。

importScripts('normalize.js');
importScripts('site-caps.js');

const ALARM_NAME = 'hr-poll';
// ❗轮询周期必须**小于**后端 `channel.request_timeout` 的等待窗口(默认 180s): 任务只有在窗口内
// 等到下一次轮询才会被取走。v2.6 前按 5 分钟轮询, 每条任务约四成概率直接超时
// (2026-09-25 实报「取 .torrent 失败: 等待浏览器扩展取数超时(180s)」)。1 分钟轮询只打本机
// loopback 一次 GET, 成本可忽略; 后端才是站点频控的唯一权威 —— 空轮询不会碰到站点。
const POLL_MINUTES = 1;
const PAGE_LOAD_TIMEOUT_MS = 60000;
const PAGE_SETTLE_MS = 800; // 页面 complete 后再等一小会儿(部分站点是 XHR 填表)
const OFFSCREEN_X = -32000; // 离屏坐标: 渲染兜底用的窗口放在屏幕外(Windows 允许完全离屏)
const OFFSCREEN_Y = -32000;

async function readConfig() {
  const got = await chrome.storage.local.get({
    enabled: true,
    instances: [],
    siteOrigins: [],
  });
  return {
    enabled: Boolean(got.enabled),
    instances: Array.isArray(got.instances) ? got.instances : [],
    siteOrigins: Array.isArray(got.siteOrigins) ? got.siteOrigins : [],
  };
}

async function noteStatus(patch, lvl) {
  const prev = await chrome.storage.local.get({ status: {} });
  const status = Object.assign({}, prev.status, patch, { at: Date.now() });
  await chrome.storage.local.set({ status });
  // 状态栏只留**最后一句**, 同样的内容同步进运行日志(level 由调用方给: 配额/异常要标 warn/error)
  if (patch && patch.text) log(lvl || 'info', '状态', patch.text);
}

// ---------- 运行日志(分级 + 环形上限, 落 chrome.storage.local) ----------
//
// ❗为什么需要: 状态栏只有**最后一句**, 一轮里多实例多任务的经过全被覆盖掉; 排查「这条为什么失败 /
// 后端到底收到了什么」必须看时序。故把关键事件逐条落成带级别的日志, 选项页④区可按级别过滤查看:
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
 * ❗绝不让日志反噬主流程: 初始化/追加/落盘任何一步失败都吞掉, 取数照跑。
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
  const prev = logFlushChain; // ❗先取队尾再排队: 回调里若按名字引用 logFlushChain, 那时它已被改成
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
  // ❗delayInMinutes 别小于 0.5 分钟: Chrome 对 alarm 有最小间隔限制(非 unpacked 时更严),
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
  noteStatus({ text: '已安装: 请在选项页填实例端点与 token, 并授予站点权限' });
});

chrome.runtime.onStartup.addListener(() => {
  schedule();
  log('info', '系统', '浏览器启动, 轮询已排程');
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) {
    pollAll('定时').catch((e) => noteStatus({ text: `轮询异常: ${e}` }, 'error'));
  }
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === 'poll-now') {
    log('info', '命令', '收到命令: 立即拉取(来自选项页)');
    pollAll('手动(选项页)')
      .then(() => sendResponse({ ok: true }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true; // 异步 sendResponse
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

chrome.permissions.onAdded.addListener(() => noteStatus({ text: '站点权限已更新' }));

// ---------- 主流程 ----------

async function pollAll(trigger) {
  try {
    const conf = await readConfig();
    log('info', '轮询', `轮询开始(${trigger || '定时'}): ${conf.instances.length} 个实例`, { 扩展启用: conf.enabled ? '是' : '否' });
    if (!conf.enabled) return;
    if (!conf.instances.length) {
      await noteStatus({ text: '未配置实例端点(打开选项页填写)' });
      return;
    }
    const lines = [];
    for (const inst of conf.instances) {
      try {
        lines.push(await pollInstance(inst));
      } catch (e) {
        // pollInstance 内部错误都自己消化了, 走到这是意外异常(如响应 JSON 解析炸了) —— 原样记下来
        const line = `${inst.name || inst.endpoint}: 失败 ${e}`;
        lines.push(line);
        log('error', '轮询', line);
      }
    }
    await noteStatus({ text: lines.join('; ') || '无事可做' });
  } finally {
    await Promise.all([flushLogs(), flushEvents()]); // 本轮立刻落盘: 「立即拉取」一返回, 选项页日志与两表都新鲜
  }
}

function headers(inst) {
  return { 'X-Hr-Token': inst.token || '' };
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
      `连不上 ${url}。逐条确认: ① 后端主程序在跑吗(--hr-once 是只读走查, **不会**起端点); ` +
      '② config.yml 里 hr_check.enabled=true、至少一个站点 mode != off、且 hr_check.channel.enabled=true' +
      '(三者缺一, 端点根本不会启动); ③ 端口对不对(后端启动日志会打「HR 取数通道端点已启动: http://127.0.0.1:<端口>」);' +
      '④ 同机多实例端口是否撞车'
    );
  }
  return msg;
}

// ---------- 扩展侧硬上限(第二道闸: 后端出错时的兜底) ----------
//
// ❗为什么扩展也要限: 后端有自己的频控(间隔 + 两级配额 + 熔断), 但那是**同一个进程里的代码**。
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

async function pollInstance(inst) {
  const label = inst.name || inst.endpoint || '(未命名)';
  const base = safeEndpoint(inst.endpoint);
  if (!base) {
    log('warn', '请求', `${label}: 端点写法不对, 本实例跳过`, { 端点: inst.endpoint });
    return `${label}: 端点写法不对(需 127.0.0.1:<端口> 这种带端口的形式) —— 到选项页重新保存会自动纠正`;
  }
  const tasksUrl = `${base}/api/hr/tasks`;
  const t0 = Date.now();
  let res;
  try {
    res = await fetch(tasksUrl, { headers: headers(inst) });
  } catch (e) {
    log('error', '请求', `拉任务清单失败: ${explainFetchError(tasksUrl, e)}`, reqDetail('拉任务清单', tasksUrl, t0, { 实例: label }));
    return `${label}: ${explainFetchError(tasksUrl, e)}`;
  }
  if (res.status === 401) {
    // 该实例没启用取数通道 / token 不匹配 —— 属正常路径, **不重试**(后端会自己告警)
    log('warn', '请求', '端点拒绝(401, token 或 channel.enabled 未开)', reqDetail('拉任务清单', tasksUrl, t0, { 实例: label, HTTP: '401' }));
    return `${label}: 端点拒绝(401, token 或 channel.enabled 未开)`;
  }
  if (!res.ok) {
    log('error', '请求', `拉清单失败 HTTP ${res.status}`, reqDetail('拉任务清单', tasksUrl, t0, { 实例: label, HTTP: String(res.status) }));
    return `${label}: 拉清单失败 HTTP ${res.status}`;
  }
  const data = await res.json();
  const tasks = Array.isArray(data.tasks) ? data.tasks : [];
  log('info', '命令', `任务清单到手: ${tasks.length} 条`, reqDetail('拉任务清单', tasksUrl, t0, { 实例: label, HTTP: '200' }));
  if (!tasks.length) return `${label}: 无任务`; // 与旧行为一致: 无任务**不回传**(不打后端的 result 端点)
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
    return `${label}: 取到 ${results.length} 条但回传失败 —— ${explainFetchError(base, e)}`;
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
  return `${label}: 取 ${results.length} 条(成功 ${okCount}; ${how})${blocked}, 回传 HTTP ${post.status}`;
}

/**
 * 页面取数: **先无界面直取**(service worker 的 fetch 带站点 cookie, 零标签零窗口),
 * 只有当拿到的内容「看起来没渲染出来」时才退到离屏窗口拿 DOM。
 *
 * ❗为什么要这样: 开任何界面都会打扰用户, 而用户已实报两次 —— 先是「抓数据时打开新标签」
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
 * ① 没表格 ⇒ 多半要 JS 渲染, 或命中了挑战页;
 * ② 有密码输入框 ⇒ 拿到的是登录页。❗第二种是 SameSite 的安全网: 无 `SameSite` 属性的 cookie 按
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
  try {
    if (task.kind === 'page') {
      const page = await pageText(task.url);
      return { rendered: page.rendered, payload: { id: task.id, ok: true, status: 200, url: task.url, text: page.text } };
    }
    const body = await fetchBinary(task.url);
    return { rendered: false, payload: { id: task.id, ok: true, status: 200, url: task.url, body_b64: body } };
  } catch (e) {
    // 配额拒发在 requireAllowance 里已记 warn, 不重复; 登录页降半级记 warn(不是故障, 是要人处置)
    if (!(e instanceof ExtQuotaError)) {
      log(e instanceof LoginPageError ? 'warn' : 'error', '任务', `任务 ${task.id} 失败(kind=${task.kind}): ${e && e.message ? e.message : e}`, {
        站点: hostOf(task.url),
        url: task.url,
      });
    }
    // 事件环与日志同源双写: quota/login/error 三类失败都进表(让位不是故障, 但用户要能在表里看到)
    pushEvent({
      host: hostOf(task.url),
      kind: task.kind,
      ok: false,
      ms: Date.now() - t0,
      tag: e instanceof ExtQuotaError ? 'quota' : e instanceof LoginPageError ? 'login' : 'error',
      note: String(e && e.message ? e.message : e),
    });
    const payload = { id: task.id, ok: false, url: task.url, error: String(e && e.message ? e.message : e) };
    if (e instanceof ExtQuotaError) {
      // 扩展侧硬上限: 让后端能把它与「取数失败」区分开(前者只让位, 后者才计失败/熔断)
      payload.kind = 'ext-quota';
      payload.retry_after = e.retryAfter || 0;
    } else if (e instanceof LoginPageError) {
      // 登录页: 后端按「HR 登录失效」处置(不计失败 / 不推熔断 / 每站报一次并给动作)
      payload.kind = 'login-page';
    }
    return { rendered: false, payload: payload };
  }
}

/**
 * 在**隐藏窗口**里取渲染后 DOM: 带登录态、能过挑战页、不抢焦点、不占用用户窗口
 *
 * ❗为什么不能直接在用户自己的窗口里 `chrome.tabs.create({ active: false })`:
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
 * ❗拿到 HTML 必须报「登录页」而不是原样回传: 与页面直取的 needsRender 同一个根因(SameSite 剥
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
