// auto-qb HR 取数代理 · 后台逻辑(MV3 service worker)
//
// 职责只有三条(计划 §6 的「哑取数器」):
//   1. 定时(chrome.alarms)逐个实例问本地端点要任务;
//   2. 按任务取内容 —— kind=page 用**后台标签页**拿渲染后 DOM(带完整登录态, 能过挑战页,
//      且不抢焦点); kind=torrent 用 service worker 自己的 fetch(credentials: 'include');
//   3. 把结果原样回传(POST), 然后关掉标签页。
//
// 明确**不做**的事: 不解析页面、不判频控、不读 chrome.cookies、不碰 passkey ——
// 解析与策略全在后端(能用 pytest 守住的那一侧), cookie 全程不离开浏览器。
//
// 配置在选项页(实例列表 + 站点权限), 存在 chrome.storage.local。

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
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: POLL_MINUTES, delayInMinutes: 0.2 });
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

async function pollInstance(inst) {
  const base = String(inst.endpoint || '').replace(/\/+$/, '');
  if (!base) return `${inst.name || '(未命名)'}: 端点为空`;
  const res = await fetch(`${base}/api/hr/tasks`, { headers: headers(inst) });
  if (res.status === 401) {
    // 该实例没启用取数通道 / token 不匹配 —— 属正常路径, **不重试**(后端会自己告警)
    return `${inst.name || base}: 端点拒绝(401, token 或 channel.enabled 未开)`;
  }
  if (!res.ok) return `${inst.name || base}: 拉清单失败 HTTP ${res.status}`;
  const data = await res.json();
  const tasks = Array.isArray(data.tasks) ? data.tasks : [];
  if (!tasks.length) return `${inst.name || base}: 无任务`;
  const results = [];
  for (const task of tasks) {
    results.push(await runTask(task));
  }
  const post = await fetch(`${base}/api/hr/result`, {
    method: 'POST',
    headers: Object.assign({ 'Content-Type': 'application/json' }, headers(inst)),
    body: JSON.stringify({ results }),
  });
  const okCount = results.filter((r) => r.ok).length;
  return `${inst.name || base}: 取 ${results.length} 条(成功 ${okCount}), 回传 HTTP ${post.status}`;
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

/** 后台标签页取渲染后 DOM: 带登录态、能过挑战页、不抢焦点 */
async function pageSnapshot(url) {
  const tab = await chrome.tabs.create({ url, active: false });
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
  } finally {
    await chrome.tabs.remove(tab.id).catch(() => {});
  }
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
