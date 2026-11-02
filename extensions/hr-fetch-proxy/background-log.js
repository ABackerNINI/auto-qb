// auto-qb HR 取数代理 · 运行日志与结构化事件环(从 background.js 原样搬迁)
// 由 background.js 顶层 importScripts 先行载入; 与主体共享同一全局作用域。

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

