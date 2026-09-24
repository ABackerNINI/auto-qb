// auto-qb HR 取数代理 · 后台逻辑(MV3 service worker)
//
// 职责只有三条(计划 §6 的「哑取数器」):
//   1. 定时(chrome.alarms)逐个实例问本地端点要任务;
//   2. 按任务取内容 —— kind=page 用**隐藏窗口里的标签页**拿渲染后 DOM(带完整登录态, 能过挑战页,
//      且不抢焦点、不出现在用户窗口里); kind=torrent 用 service worker 自己的 fetch
//      (credentials: 'include');
//   3. 把结果原样回传(POST), 然后关掉标签页。
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
  for (const task of tasks) {
    results.push(await runTask(task));
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
  return `${label}: 取 ${results.length} 条(成功 ${okCount}), 回传 HTTP ${post.status}`;
}

async function runTask(task) {
  try {
    if (task.kind === 'page') {
      const text = await pageSnapshot(task.url);
      return { id: task.id, ok: true, status: 200, url: task.url, text };
    }
    const body = await fetchBinary(task.url);
    return { id: task.id, ok: true, status: 200, url: task.url, body_b64: body };
  } catch (e) {
    return { id: task.id, ok: false, url: task.url, error: String(e && e.message ? e.message : e) };
  }
}

/**
 * 在**隐藏窗口**里取渲染后 DOM: 带登录态、能过挑战页、不抢焦点、不占用用户窗口
 *
 * ❗为什么不能直接在用户自己的窗口里 `chrome.tabs.create({ active: false })`:
 * `active:false` 只保证「不是那个窗口的活动标签」, **不保证窗口不被抬起来** —— 扩展被 alarm 唤醒时
 * 用户往往正在别的程序里, Chrome 仍会把窗口连同新标签一起显示出来, 用户看到的就是「抓数据时会打开
 * 新标签」而不是后台抓取(2026-09-25 实报)。所以取数一律在**自己的、永不聚焦的窗口**里做。
 */
async function pageSnapshot(url) {
  const restoreFocus = await focusGuard();
  const windowId = await ensureHiddenWindow();
  const tab = await chrome.tabs.create({ url, active: false, windowId });
  try {
    await waitForComplete(tab.id, PAGE_LOAD_TIMEOUT_MS);
    await sleep(PAGE_SETTLE_MS);
    const frames = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => document.documentElement.outerHTML,
    });
    const html = frames && frames[0] ? frames[0].result : '';
    if (!html) throw new Error('页面为空(未授予站点权限?)');
    return html;
  } catch (e) {
    // 最小化窗口可能让页面自己的延迟脚本变慢 ⇒ 连续失败时把它恢复成普通状态(仍不聚焦)
    await relaxHiddenWindow(String((e && e.message) || e));
    throw e;
  } finally {
    await chrome.tabs.remove(tab.id).catch(() => {});
    const note = await restoreFocus();
    if (note) await noteStatus({ text: note });
    scheduleHiddenWindowClose();
  }
}

// ---------- 隐藏取数窗口 ----------

const HIDDEN_WINDOW_IDLE_MS = 2 * 60 * 1000; // 空闲就关掉: 不长期留一个窗口占着
let hiddenWindowId = 0;
let hiddenWindowTimer = 0;
let hiddenWindowMinimized = true;

chrome.windows.onRemoved.addListener((id) => {
  if (id === hiddenWindowId) hiddenWindowId = 0; // 用户把它关了: 下次重建
});

chrome.runtime.onSuspend.addListener(() => {
  closeHiddenWindow(); // 挂起路径不能 await, 空闲计时器兜底
});

/** 取数窗口: 最小化 + `focused:false`(两重都要: 前者不占地方, 后者不被聚焦) */
async function ensureHiddenWindow() {
  if (hiddenWindowId) {
    const alive = await chrome.windows.get(hiddenWindowId).catch(() => null);
    if (alive) return hiddenWindowId;
    hiddenWindowId = 0;
  }
  let win;
  try {
    win = await chrome.windows.create({ focused: false, state: 'minimized' });
  } catch (e) {
    // 少数平台不接受直接建最小化窗口 ⇒ 先建再收起来(仍不聚焦)
    win = await chrome.windows.create({ focused: false });
    await chrome.windows.update(win.id, { state: 'minimized' }).catch(() => {});
  }
  hiddenWindowId = win.id;
  hiddenWindowMinimized = true;
  await noteStatus({ text: '取数用隐藏窗口完成(最小化, 不抢焦点; 空闲 2 分钟自动关闭)' });
  return hiddenWindowId;
}

function scheduleHiddenWindowClose() {
  clearTimeout(hiddenWindowTimer);
  hiddenWindowTimer = setTimeout(closeHiddenWindow, HIDDEN_WINDOW_IDLE_MS);
}

async function closeHiddenWindow() {
  clearTimeout(hiddenWindowTimer);
  hiddenWindowTimer = 0;
  const id = hiddenWindowId;
  hiddenWindowId = 0;
  if (id) await chrome.windows.remove(id).catch(() => {});
}

/** 最小化窗口里的页面可能被节流(延迟脚本变慢) ⇒ 失败一次就取消最小化, **仍然不聚焦** */
async function relaxHiddenWindow(why) {
  if (!hiddenWindowId || !hiddenWindowMinimized) return;
  hiddenWindowMinimized = false;
  await chrome.windows.update(hiddenWindowId, { state: 'normal' }).catch(() => {});
  await chrome.windows.update(hiddenWindowId, { focused: false }).catch(() => {});
  await noteStatus({ text: `取数窗口已取消最小化(${why}) —— 若仍失败, 看站点是否需人工过挑战页` });
}

/**
 * 焦点守卫: 新建窗口/标签在个别平台仍会把浏览器抬到前台 ⇒ 记下**原聚焦窗口**, 取完还回去。
 * 只还焦点, 不关不切用户自己的窗口与标签。
 */
async function focusGuard() {
  const before = await chrome.windows.getLastFocused().catch(() => null);
  return async function restore() {
    if (!before || !before.id || before.id === hiddenWindowId) return '';
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
