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
// 地址归一化共用 normalize.js(选项页用 <script> 载入, 这里用 importScripts —— 同一份代码)。

importScripts('normalize.js');

const ALARM_NAME = 'hr-poll';
const POLL_MINUTES = 5; // 与后端下发的 next_poll_s 同量级; 后端才是频控权威
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

async function noteStatus(patch) {
  const prev = await chrome.storage.local.get({ status: {} });
  const status = Object.assign({}, prev.status, patch, { at: Date.now() });
  await chrome.storage.local.set({ status });
}

function schedule() {
  // ❗delayInMinutes 别小于 0.5 分钟: Chrome 对 alarm 有最小间隔限制(非 unpacked 时更严),
  // 违规会直接抛错 —— 那会在安装/启动路径上变成一个看不懂的未捕获异常。
  try {
    chrome.alarms.create(ALARM_NAME, { periodInMinutes: POLL_MINUTES, delayInMinutes: 0.5 });
  } catch (e) {
    noteStatus({ text: `创建定时器失败: ${e.message || e}` });
  }
}

chrome.runtime.onInstalled.addListener(() => {
  schedule();
  noteStatus({ text: '已安装: 请在选项页填实例端点与 token, 并授予站点权限' });
});

chrome.runtime.onStartup.addListener(schedule);

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) {
    pollAll().catch((e) => noteStatus({ text: `轮询异常: ${e}` }));
  }
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === 'poll-now') {
    pollAll()
      .then(() => sendResponse({ ok: true }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true; // 异步 sendResponse
  }
  return false;
});

chrome.permissions.onAdded.addListener(() => noteStatus({ text: '站点权限已更新' }));

// ---------- 主流程 ----------

async function pollAll() {
  const conf = await readConfig();
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
      lines.push(`${inst.name || inst.endpoint}: 失败 ${e}`);
    }
  }
  await noteStatus({ text: lines.join('; ') || '无事可做' });
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

async function pollInstance(inst) {
  const label = inst.name || inst.endpoint || '(未命名)';
  const base = safeEndpoint(inst.endpoint);
  if (!base) {
    return `${label}: 端点写法不对(需 127.0.0.1:<端口> 这种带端口的形式) —— 到选项页重新保存会自动纠正`;
  }
  const tasksUrl = `${base}/api/hr/tasks`;
  let res;
  try {
    res = await fetch(tasksUrl, { headers: headers(inst) });
  } catch (e) {
    return `${label}: ${explainFetchError(tasksUrl, e)}`;
  }
  if (res.status === 401) {
    // 该实例没启用取数通道 / token 不匹配 —— 属正常路径, **不重试**(后端会自己告警)
    return `${label}: 端点拒绝(401, token 或 channel.enabled 未开)`;
  }
  if (!res.ok) return `${label}: 拉清单失败 HTTP ${res.status}`;
  const data = await res.json();
  const tasks = Array.isArray(data.tasks) ? data.tasks : [];
  if (!tasks.length) return `${label}: 无任务`;
  const results = [];
  const rendered = [];
  for (const task of tasks) {
    const got = await runTask(task);
    if (got.rendered) rendered.push(task.url);
    results.push(got.payload);
  }
  let post;
  try {
    post = await fetch(`${base}/api/hr/result`, {
      method: 'POST',
      headers: Object.assign({ 'Content-Type': 'application/json' }, headers(inst)),
      body: JSON.stringify({ results }),
    });
  } catch (e) {
    return `${label}: 取到 ${results.length} 条但回传失败 —— ${explainFetchError(base, e)}`;
  }
  const okCount = results.filter((r) => r.ok).length;
  const how = rendered.length ? `其中 ${rendered.length} 条走渲染` : '全部直取(无界面)';
  return `${label}: 取 ${results.length} 条(成功 ${okCount}; ${how}), 回传 HTTP ${post.status}`;
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
  const res = await fetch(url, { credentials: 'include' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const text = await res.text();
  if (!text) throw new Error('返回内容为空');
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
  try {
    if (task.kind === 'page') {
      const page = await pageText(task.url);
      return { rendered: page.rendered, payload: { id: task.id, ok: true, status: 200, url: task.url, text: page.text } };
    }
    const body = await fetchBinary(task.url);
    return { rendered: false, payload: { id: task.id, ok: true, status: 200, url: task.url, body_b64: body } };
  } catch (e) {
    return { rendered: false, payload: { id: task.id, ok: false, url: task.url, error: String(e && e.message ? e.message : e) } };
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

/** 取 .torrent 二进制: 由 service worker 自己发(credentials include 带上站点 cookie) */
async function fetchBinary(url) {
  const res = await fetch(url, { credentials: 'include' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const buf = new Uint8Array(await res.arrayBuffer());
  if (!buf.length) throw new Error('返回内容为空');
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
