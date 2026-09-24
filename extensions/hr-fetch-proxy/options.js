// 选项页: 读/写 chrome.storage.local, 申请站点权限, 手动触发一次拉取。
// 校验只做「能不能解析」这一件事 —— 频控与鉴权的权威都在后端, 这里不做策略判断。

const $ = (id) => document.getElementById(id);

function setStatus(text) {
  $('status').textContent = text;
}

async function load() {
  const got = await chrome.storage.local.get({
    enabled: true,
    instances: [],
    siteOrigins: [],
    status: {},
  });
  $('enabled').checked = Boolean(got.enabled);
  $('instances').value = got.instances.map((i) => JSON.stringify(i)).join('\n');
  $('origins').value = got.siteOrigins.join('\n');
  const st = got.status || {};
  if (st.text) setStatus(`${new Date(st.at || Date.now()).toLocaleString()} — ${st.text}`);
}

function parseInstances() {
  const out = [];
  const lines = $('instances').value.split('\n').map((l) => l.trim()).filter(Boolean);
  for (const line of lines) {
    let item;
    try {
      item = JSON.parse(line);
    } catch (e) {
      throw new Error(`实例行不是合法 JSON: ${line}`);
    }
    if (!item || !item.endpoint) throw new Error(`实例缺少 endpoint: ${line}`);
    out.push({
      name: String(item.name || item.endpoint),
      endpoint: String(item.endpoint),
      token: String(item.token || ''),
    });
  }
  return out;
}

function parseOrigins() {
  return $('origins').value.split('\n').map((l) => l.trim()).filter(Boolean);
}

async function save() {
  try {
    const instances = parseInstances();
    const siteOrigins = parseOrigins();
    await chrome.storage.local.set({
      enabled: $('enabled').checked,
      instances,
      siteOrigins,
    });
    setStatus(`已保存: ${instances.length} 个实例, ${siteOrigins.length} 个站点源`);
  } catch (e) {
    setStatus(String(e.message || e));
  }
}

async function grant() {
  const origins = parseOrigins();
  if (!origins.length) {
    setStatus('请先填站点源(如 https://pt.example.com/*)');
    return;
  }
  const ok = await chrome.permissions.request({ origins });
  setStatus(ok ? `已授予 ${origins.length} 个站点源` : '站点权限被拒绝');
}

async function poll() {
  setStatus('正在拉取…');
  const res = await chrome.runtime.sendMessage({ type: 'poll-now' });
  const got = await chrome.storage.local.get({ status: {} });
  setStatus(res && res.ok ? (got.status.text || '完成') : `失败: ${(res && res.error) || '未知'}`);
}

$('save').addEventListener('click', save);
$('grant').addEventListener('click', grant);
$('poll').addEventListener('click', poll);
$('enabled').addEventListener('change', save);
load();
