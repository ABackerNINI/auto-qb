// 选项页: 读/写 chrome.storage.local, 申请站点权限, 自测端点连通性, 手动触发一次拉取。
//
// ❗这里是**唯一**能替用户挡住"格式写错"的地方 —— 浏览器 API 对格式极其严格且报错难懂:
//   · chrome.permissions.request 只吃**匹配模式**(必须带 scheme), 裸域名报
//     "Invalid value for origin pattern xxx: Missing scheme separator." 且是**未捕获的拒绝**;
//   · fetch 的 URL 必须带 scheme 与回环主机, 否则报一句 "TypeError: Failed to fetch"(什么都看不出来)。
// 所以本页一律"先归一化、再落盘", 并把失败逐条翻译成中文可操作提示; 绝不让 Promise 裸抛。
//
// 页面形态(2026-09-26 定稿, 风格选型 A「瑞士网格」, 见 memory-bank/plans/26-09-26-0031):
//   ① 连接端点(表单, 存入即生效) → ② 站点权限(后端拉清单勾选 + 一键授权, GET /api/hr/sites 与
//   后端 hr/channel.API_SITES 同源) → ③ 站点现状表 → ④ 最近取数明细表 → 状态行 →
//   折叠区(运行日志排障用 + 硬上限 + 高级 JSON)。③④ 的数据源是后台与日志同源双写的
//   结构化事件环(chrome.storage `events`) + `siteLedger` 用量台账 —— 解析日志文案做表太脆。
//
// 策略与频控判断**不在这里** —— 那唯一权威在后端。
// 地址归一化共用 normalize.js(与后台同一份, 免得两条路径各自演化)。

const $ = (id) => document.getElementById(id);

// 与后端 hr/channel.py 的 API_SITES 同步(改一边必改另一边, 守阵在 test_extension_proxy)
const API_SITES = "/api/hr/sites";

const DEFAULT_ENDPOINT = "127.0.0.1:8788";
const EVENT_RENDER_CAP = 50; // 与后台事件环上限一致: 再多也只显示最近这些

function setStatus(text) {
  $('status').textContent = text;
}

function hint(text) {
  $('hint').textContent = text || '';
}

// ---------- 输入处理 ----------

// normalizeEndpoint / normalizeOrigin 都是 normalize.js 里的纯函数(与后台共用同一份);
// ❗这里**不要**再定义同名的本地副本 —— 两份分头演化必然漂移, 而漂移的症状是"配了不生效"。

function linesOf(el) {
  return el.value.split('\n').map((l) => l.trim()).filter(Boolean);
}

function parseInstances() {
  const out = [];
  for (const line of linesOf($('instances'))) {
    let item;
    try {
      item = JSON.parse(line);
    } catch (e) {
      throw new Error(`实例行不是合法 JSON: ${line}`);
    }
    if (!item || !item.endpoint) throw new Error(`实例缺少 endpoint: ${line}`);
    out.push({
      name: String(item.name || item.endpoint),
      endpoint: normalizeEndpoint(item.endpoint),
      token: String(item.token || '').trim(),
    });
  }
  return out;
}

/** 当前生效的实例清单(唯一事实源是内存状态; 高级 JSON 文本域是它的可编辑视图, 保存时收编) */
function currentInstances() {
  return instancesState;
}

/** 逐条归一化站点源: 一条坏不该拖垮整批, 好的照收, 坏的单独报 */
function parseOrigins() {
  const good = [];
  const bad = [];
  for (const line of linesOf($('origins'))) {
    try {
      const pattern = normalizeOrigin(line);
      if (!good.includes(pattern)) good.push(pattern);
    } catch (e) {
      bad.push(`${line}( ${e.message} )`);
    }
  }
  return { good, bad };
}

// ---------- 实例端点: 表单 + 列表 ----------

let instancesState = []; // 实例清单(唯一事实源仍是 chrome.storage)

function fillForm(item) {
  $('instEndpoint').value = item ? item.endpoint : DEFAULT_ENDPOINT;
  $('instToken').value = item ? item.token : '';
}

async function persistInstances() {
  await chrome.storage.local.set({ instances: instancesState });
}

/** 高级 JSON 视图与内存状态保持同步: 表单增删后它也刷新, 保存时收编手改的 JSON */
function syncAdvancedView() {
  $('instances').value = instancesState.map((i) => JSON.stringify(i)).join('\n');
}

async function addInstance() {
  try {
    const raw = $('instEndpoint').value.trim();
    if (!raw) {
      setStatus('地址不能为空(本机默认 127.0.0.1:8788)');
      return;
    }
    const endpoint = normalizeEndpoint(raw);
    const item = { name: endpoint, endpoint, token: $('instToken').value.trim() };
    const dup = instancesState.findIndex((i) => i.endpoint === endpoint);
    if (dup >= 0) {
      instancesState[dup] = item;
      setStatus(`已更新实例 ${item.name}(token ${item.token ? '已填' : '未填'})`);
    } else {
      instancesState.push(item);
      setStatus(`已存入实例 ${item.name}, 共 ${instancesState.length} 个 —— token 没填的话先去复制 hr.token`);
    }
    await persistInstances();
    renderInstList();
    syncAdvancedView();
    hint('');
  } catch (e) {
    setStatus(`保存实例失败: ${e.message || e}`);
  }
}

function renderInstList() {
  const box = $('instList');
  if (!instancesState.length) {
    box.innerHTML = '<div class="inst-row"><span class="tk">(还没有实例 —— 上面填好地址与 token 后点「存入实例列表」)</span></div>';
    return;
  }
  box.innerHTML = instancesState
    .map((item, i) => {
      const tk = item.token ? `${item.token.slice(0, 8)}…` : '(未填 token)';
      return (
        `<div class="inst-row"><span class="ep">${esc(item.endpoint)}</span><span class="tk">${esc(tk)}</span>` +
        '<span class="grow"></span>' +
        `<button class="ghost" data-act="edit" data-i="${i}">载入</button>` +
        `<button class="ghost" data-act="del" data-i="${i}">删除</button></div>`
      );
    })
    .join('');
}

async function instListClick(ev) {
  const btn = ev.target.closest('button[data-act]');
  if (!btn) return;
  const i = Number(btn.dataset.i);
  if (!Number.isInteger(i) || !instancesState[i]) return;
  if (btn.dataset.act === 'edit') {
    fillForm(instancesState[i]);
    return;
  }
  const removed = instancesState.splice(i, 1)[0];
  fillForm(null);
  await persistInstances();
  renderInstList();
  syncAdvancedView();
  setStatus(`已删除实例 ${removed.name}`);
}

// ---------- 站点权限: 从后端拉清单勾选(手动填域名降级为兜底) ----------

let backendSites = []; // 后端 /api/hr/sites 报的 [{site, origin}]
let siteSelections = []; // 勾选持久化(重开页面恢复勾选状态)

async function persistSelections() {
  await chrome.storage.local.set({ siteSelections });
}

/** 拉站点清单。manual=true 时把结果/失败亮进状态栏; 自动拉(进页面)保持安静 */
async function fetchSites(manual) {
  let inst;
  try {
    inst = currentInstances()[0];
  } catch (e) {
    if (manual) setStatus(`获取站点中止: ${e.message || e}`);
    return;
  }
  if (!inst) {
    backendSites = [];
    renderSiteChecks();
    if (manual) setStatus('先在 ① 把实例端点存入列表, 再来获取站点');
    return;
  }
  try {
    const res = await fetch(`${inst.endpoint}${API_SITES}`, { headers: { 'X-Hr-Token': inst.token } });
    if (res.status === 401) {
      if (manual) setStatus('获取站点失败: token 不对(HTTP 401) — 把 hr.token 内容粘进 token 字段, 点「存入实例列表」');
      return;
    }
    if (!res.ok) {
      if (manual) setStatus(`获取站点失败: HTTP ${res.status}(若后端配了 channel.extension_id, 要与本扩展一致)`);
      return;
    }
    const data = await res.json();
    if (data.error) {
      if (manual) setStatus(`后端返回: ${data.error}`);
      return;
    }
    backendSites = Array.isArray(data.sites) ? data.sites : [];
    renderSiteChecks();
    if (manual) {
      setStatus(
        backendSites.length
          ? `后端报了 ${backendSites.length} 个站点(默认全勾), 点「申请勾选站点的权限」即可`
          : '后端没有报任何站点: 检查 trackers.<站点>.hr_check.mode 是否还是 off'
      );
    }
  } catch (e) {
    if (manual) setStatus(`✗ 连不上端点(${e.message || e}) — 先点「自测端点连通」按提示排查`);
  }
}

/** 渲染勾选列表; 勾选状态以已存 selections 为准(首次默认全勾) */
function renderSiteChecks() {
  const box = $('siteChecks');
  if (!backendSites.length) {
    box.innerHTML = '<label class="row"><span class="tk">(还没有站点清单 — 配好实例端点后点「重新获取站点」; 后端起来且站点 hr_check.mode 非 off 才会有)</span></label>';
    return;
  }
  box.innerHTML = backendSites
    .map((s) => {
      const origin = String(s.origin || '');
      const checked = siteSelections.includes(origin) || !siteSelections.length ? ' checked' : '';
      return (
        `<label><input type="checkbox" data-origin="${esc(origin)}"${checked}>` +
        `${esc(String(s.site || ''))} <span class="org">${esc(origin)}</span></label>`
      );
    })
    .join('');
}

/** 勾选变化即持久化(不用点保存); 勾选的站点在授权时一并申请 */
async function siteChecksChange() {
  siteSelections = Array.from(document.querySelectorAll('#siteChecks input[type="checkbox"]:checked')).map(
    (c) => c.dataset.origin
  );
  await persistSelections();
}

function selectAllSites() {
  for (const c of document.querySelectorAll('#siteChecks input[type="checkbox"]')) c.checked = true;
  siteChecksChange().catch((e) => setStatus(`保存勾选失败: ${e.message || e}`));
}

async function grant() {
  // 勾选清单(后端给的已是匹配模式) + 手动兜底(逐条归一化)合并去重
  const checked = Array.from(document.querySelectorAll('#siteChecks input[type="checkbox"]:checked')).map(
    (c) => c.dataset.origin
  );
  const manual = parseOrigins();
  const origins = [];
  for (const o of checked.concat(manual.good)) {
    if (!origins.includes(o)) origins.push(o);
  }
  if (!origins.length) {
    setStatus(
      '没有可申请的站点权限: 先「重新获取站点」并勾选, 或在手动填写里加域名' +
      (manual.bad.length ? `; 坏的已跳过: ${manual.bad.join(' / ')}` : '')
    );
    return;
  }
  hint('申请的是这些匹配模式: ' + origins.join(', '));
  try {
    // ❗授权窗必须由用户手势直接触发: 这里前面不能有 await(否则 Chrome 报"not during a user gesture")
    const ok = await chrome.permissions.request({ origins });
    const badTail = manual.bad.length ? `; 跳过 ${manual.bad.length} 条格式不对的: ${manual.bad.join(' / ')}` : '';
    setStatus(ok ? `已授予 ${origins.length} 个站点源` : `站点权限被拒绝(再点一次授权即可重试)${badTail}`);
  } catch (e) {
    // 典型: 某个模式仍不合法 / 非用户手势 —— 必须消化掉, 不能让 Promise 裸抛(用户只会看到红字英文)
    setStatus(`申请站点权限失败: ${e.message || e}`);
  }
}

// ---------- 两张表: 站点现状 + 最近取数明细(数据源 = events 事件环 + siteLedger 台账) ----------

function shortTime(t) {
  const d = new Date(t);
  if (isNaN(d.getTime())) return '—';
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

const KIND_TEXT = { page: 'HR 页', torrent: '.torrent' };

/** 一条事件的「最近动作 · 结果」短语(表一用) */
function eventPhrase(ev) {
  const kind = KIND_TEXT[ev.kind] || ev.kind || '—';
  if (ev.tag === 'ok') return `取 ${kind} · ✓ ${ev.status || 200}${ev.note ? `(${ev.note})` : ''}`;
  if (ev.tag === 'quota') return `取 ${kind} · 让位(扩展侧配额)`;
  if (ev.tag === 'login') return `取 ${kind} · 登录页(需人工登录)`;
  return `取 ${kind} · ✗ ${(ev.note || '失败').slice(0, 30)}`;
}

const TAG_TEXT = { ok: '正常', quota: '受限', login: '登录失效', error: '异常' };

async function refreshTables() {
  const got = await chrome.storage.local.get({ events: [], siteLedger: {} });
  const events = Array.isArray(got.events) ? got.events : [];
  renderSiteStatus(events, got.siteLedger || {});
  renderEvents(events);
}

function renderSiteStatus(events, ledger) {
  const now = Date.now();
  const d = new Date(now);
  const hk = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}T${String(d.getHours()).padStart(2, '0')}`;
  const dk = hk.slice(0, 10);
  const last = new Map(); // host -> 最近一条事件
  for (const ev of events) {
    if (!ev || !ev.host) continue;
    const prev = last.get(ev.host);
    if (!prev || (ev.t || 0) > (prev.t || 0)) last.set(ev.host, ev);
  }
  const hosts = new Set([...Object.keys(ledger || {}), ...last.keys()]);
  const rows = [...hosts].map((host) => {
    const ev = last.get(host);
    let usage = '—';
    if (ledger[host]) {
      const page = ledger[host].page || {};
      const tor = ledger[host].torrent || {};
      const ph = page.hk === hk ? page.hour || 0 : 0;
      const pd = page.dk === dk ? page.day || 0 : 0;
      const th = tor.hk === hk ? tor.hour || 0 : 0;
      const td = tor.dk === dk ? tor.day || 0 : 0;
      // ❗阈值从 site-caps.js 取(唯一事实源), 与后台/硬上限展示同一份 —— 这里写死必漂移
      usage = `${ph}/${SITE_CAPS.page.perHour} · ${th}/${SITE_CAPS.torrent.perHour}` +
              ` ／ ${pd}/${SITE_CAPS.page.perDay} · ${td}/${SITE_CAPS.torrent.perDay}`;
    }
    const tag = ev ? ev.tag || 'error' : 'ok';
    const cls = tag === 'ok' ? '' : 'warn';
    return {
      t: ev ? ev.t || 0 : 0,
      html:
        `<tr><td>${esc(host)}</td><td class="num">${ev ? shortTime(ev.t) : '—'}</td>` +
        `<td class="num">${ev ? esc(eventPhrase(ev)) : '<span class="dim">尚无取数</span>'}</td>` +
        `<td class="num">${esc(usage)}</td><td class="${cls}">${TAG_TEXT[tag] || '正常'}</td></tr>`,
    };
  });
  rows.sort((a, b) => b.t - a.t);
  $('siteTable').innerHTML =
    rows.map((r) => r.html).join('') ||
    '<tr><td class="empty" colspan="5">(还没有记录 — 配好实例并点「立即拉取一次」后出现)</td></tr>';
}

function renderEvents(events) {
  const rows = events.slice(-EVENT_RENDER_CAP).reverse();
  $('eventTable').innerHTML =
    rows
      .map((ev) => {
        if (!ev) return '';
        const cls = ev.tag === 'ok' ? 'num' : 'warn';
        const result =
          ev.tag === 'ok'
            ? `✓ ${ev.status || 200}${ev.note ? `(${esc(ev.note)})` : ''}`
            : ev.tag === 'quota'
              ? '让位 · 扩展侧配额'
              : ev.tag === 'login'
                ? '登录页(需人工登录)'
                : `✗ ${esc((ev.note || '失败').slice(0, 40))}`;
        return (
          `<tr><td class="num">${shortTime(ev.t)}</td><td>${esc(ev.host || '—')}</td>` +
          `<td>${KIND_TEXT[ev.kind] || esc(ev.kind || '—')}</td><td class="${cls}">${result}</td>` +
          `<td class="num">${ev.ms ? `${ev.ms}ms` : '—'}</td><td class="num">${ev.bytes ? `${(ev.bytes / 1024).toFixed(ev.bytes >= 1024 ? 0 : 1)}KB` : '—'}</td></tr>`
        );
      })
      .join('') ||
    '<tr><td class="empty" colspan="6">(还没有取数 — 配好实例并点「立即拉取一次」后出现)</td></tr>';
}

/** 后台每次落盘事件环/台账都自动刷新(防抖), 与日志同款纪律 */
let tableRenderTimer = null;
function scheduleTablesRender() {
  if (tableRenderTimer) return;
  tableRenderTimer = setTimeout(() => {
    tableRenderTimer = null;
    refreshTables().catch((e) => setStatus(`刷新两表失败: ${e.message || e}`));
  }, 300);
}

/**
 * 展示两道闸的额度与今日/本小时用量(折叠排障区)。
 * ❗阈值来自 site-caps.js(唯一事实源, 与后台共用) —— 这里**不写死数字**, 免得改了后台忘改这里,
 * 用户按选项页显示的数字去理解行为, 结果对不上。
 */
function renderCaps(ledger) {
  const now = Date.now();
  const d = new Date(now);
  const hk = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}T${String(d.getHours()).padStart(2, '0')}`;
  const dk = hk.slice(0, 10);
  const lines = Object.entries(SITE_CAPS).map(
    ([kind, cap]) => `  ${cap.label.padEnd(14)} 每小时 ${cap.perHour} / 每天 ${cap.perDay}`
  );
  const hosts = Object.keys(ledger || {}).sort();
  if (!hosts.length) {
    lines.push('', '  用量: (还没有计数 —— 每次取数都从这里扣)', '', '  窗口键在本地时区整点/零点交错, 超限会一直等到下一个窗口。');
  } else {
    lines.push('', '  用量(未显示 = 0):');
    for (const host of hosts) {
      for (const [kind, cap] of Object.entries(SITE_CAPS)) {
        const rec = (ledger[host] || {})[kind] || {};
        const hour = rec.hk === hk ? (rec.hour || 0) : 0;
        const day = rec.dk === dk ? (rec.day || 0) : 0;
        if (hour || day) lines.push(`    ${host}  ${cap.label}: 本小时 ${hour}/${cap.perHour}, 本日 ${day}/${cap.perDay}`);
      }
    }
  }
  $('caps').textContent = lines.join('\n');
}

// ---------- 读档与保存 ----------

async function load() {
  const got = await chrome.storage.local.get({
    enabled: true, instances: [], siteOrigins: [], siteSelections: [], status: {}, siteLedger: {}, logMax: 1000, logLevel: 'info',
  });
  $('enabled').checked = Boolean(got.enabled);
  instancesState = Array.isArray(got.instances) ? got.instances : [];
  siteSelections = Array.isArray(got.siteSelections) ? got.siteSelections : [];
  $('origins').value = got.siteOrigins.join('\n');
  const st = got.status || {};
  if (st.text) setStatus(`${new Date(st.at || Date.now()).toLocaleString()} — ${st.text}`);
  renderCaps(got.siteLedger || {});
  $('logMax').value = String(got.logMax);
  $('logLevel').value = got.logLevel;
  fillForm(instancesState.length ? instancesState[0] : null);
  renderInstList();
  syncAdvancedView();
  renderSiteChecks();
  await Promise.all([refreshLogs(), refreshTables()]); // 首次进页面就出日志与两表; 之后后台落盘经 onChanged 自动刷
  if (instancesState.length) fetchSites(false).catch(() => {}); // 自动拉站点清单, 失败保持安静(手动点才报)
}

async function save() {
  try {
    instancesState = parseInstances();
    const { good, bad } = parseOrigins();
    await chrome.storage.local.set({
      enabled: $('enabled').checked,
      instances: instancesState,
      siteOrigins: good,
      siteSelections,
    });
    // 把归一化后的结果写回输入框: 用户才能看到"实际存进去的是什么"
    $('origins').value = good.join('\n');
    syncAdvancedView();
    const tail = bad.length ? `; ${bad.length} 条站点源被跳过(格式不对): ${bad.join(' / ')}` : '';
    setStatus(`已保存: ${instancesState.length} 个实例, ${good.length} 个手动站点源, ${siteSelections.length} 个勾选站点${tail}`);
    hint(bad.length ? '格式不对的站点源已跳过, 修正后重新保存即可。' : '');
  } catch (e) {
    setStatus(`保存失败: ${e.message || e}`);
    hint('');
  }
}

/** 直连后端端点自测: 把"通了/401/连不上"分清楚, 并给出下一步该查什么 */
async function testEndpoint() {
  const inst = currentInstances()[0];
  if (!inst) {
    setStatus('先在 ① 存入一个实例端点再自测');
    return;
  }
  const url = `${inst.endpoint}/api/hr/tasks`;
  setStatus(`正在自测 ${url} …`);
  hint('');
  try {
    const res = await fetch(url, { headers: { 'X-Hr-Token': inst.token } });
    if (res.status === 200) {
      const data = await res.json();
      setStatus(`✓ 端点可达: 本批 ${(data.tasks || []).length} 条任务, 建议轮询间隔 ${data.next_poll_s}s`);
      hint('后端与扩展的端口/token 一致 ⇒ 保持浏览器开着即可。');
    } else if (res.status === 401) {
      setStatus('端点可达, 但 token 不对(HTTP 401)');
      hint('打开后端数据目录下的 hr.token, 把内容整串粘到 token 字段再「存入实例列表」。');
    } else if (res.status === 403) {
      setStatus('端点拒绝来源(HTTP 403) —— 若后端配了 channel.extension_id, 要填成与本扩展一致的 id');
    } else {
      setStatus(`端点可达但返回 HTTP ${res.status}`);
    }
  } catch (e) {
    // fetch 对网络层失败只会给一句 TypeError: Failed to fetch —— 这里替用户展开成排查清单
    setStatus(`✗ 连不上端点(${e.message || e})`);
    hint(
      '逐条确认: ① 后端正在运行吗(auto-qb 主程序, 不是 --hr-once 走查); ' +
      '② config.yml 里 hr_check.enabled=true、至少一个站点 trackers.<站点>.hr_check.mode != off、' +
      '且 hr_check.channel.enabled=true —— 三者缺一, 端点**根本不会启动**; ' +
      `③ 端口对不对(现在是 ${inst.endpoint} , 后端启动日志会打一行「HR 取数通道端点已启动: http://127.0.0.1:<端口>」); ` +
      '④ 同机多实例是否端口撞车(被占则后端启动即报错)。'
    );
  }
}

async function poll() {
  setStatus('正在拉取…');
  try {
    const res = await chrome.runtime.sendMessage({ type: 'poll-now' });
    const got = await chrome.storage.local.get({ status: {} });
    if (res && res.ok) {
      setStatus(got.status.text || '完成');
    } else {
      setStatus(`拉取失败: ${(res && res.error) || '未知'}(详见折叠区里的运行日志)`);
    }
  } catch (e) {
    // SW 未就绪/已休眠时会走到这里 —— 别让红字裸奔
    setStatus(`与服务线程通信失败: ${e.message || e}`);
    hint('重开一次选项页再试; 若仍失败, 到 chrome://extensions 看本扩展的「Service Worker」控制台。');
  }
}

// ---------- 运行日志(排障用, 默认收起) ----------
//
// 这里只做「读 + 过滤 + 清空 + 设置」; 写入全在后台(环形缓冲, 唯一写入口)。两个设置改动**即时生效**。
// ❗清空必须经后台(clear-logs): 后台内存里还留着缓冲, 选项页直接改 storage 会在它下一次落盘时
// 被旧数据盖回去(后台没应答时的兜底路径除外 —— 后台会采纳外部清空, 见 background.js 的 onChanged)。

const LOG_RANK = { debug: 0, info: 1, warn: 2, error: 3 };
const LOG_LV_TEXT = { debug: 'DEBUG', info: 'INFO', warn: 'WARN', error: 'ERROR' };
const LOG_RENDER_CAP = 3000; // 一次最多渲染的行数: 10000 行 DOM 会把选项页卡住, 更早的靠过滤看
let logAll = [];
let logFilterMin = 0;
let logRenderTimer = null;

function clampLogMaxInput() {
  let n = Math.round(Number($('logMax').value));
  if (!Number.isFinite(n)) n = 1000;
  n = Math.min(10000, Math.max(10, n));
  $('logMax').value = String(n);
  return n;
}

/** 日志明细里有站点 URL / 页面片段, innerHTML 前必须转义 —— 这是选项页自己的注入面 */
function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function logTime(t) {
  const d = new Date(t);
  if (isNaN(d.getTime())) return '(时间缺失)';
  const p = (n, w) => String(n).padStart(w || 2, '0');
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${p(d.getMilliseconds(), 3)}`;
}

function logDetail(e) {
  const fixed = { t: 1, lvl: 1, cat: 1, msg: 1 };
  return Object.keys(e)
    .filter((k) => !fixed[k])
    .map((k) => `${k}=${e[k]}`)
    .join(' · ');
}

function renderLogs() {
  const rows = logAll.filter((e) => (LOG_RANK[e.lvl] === undefined ? 1 : LOG_RANK[e.lvl]) >= logFilterMin);
  const tail = rows.slice(-LOG_RENDER_CAP);
  $('logView').innerHTML =
    tail
      .map((e) => {
        const det = logDetail(e);
        const lv = LOG_RANK[e.lvl] === undefined ? 'info' : e.lvl;
        return (
          `<div class="log-row"><span class="lt">${logTime(e.t)}</span>` +
          `<span class="lv ${lv}">${LOG_LV_TEXT[lv]}</span>` +
          `<span class="lc">${esc(e.cat || '')}</span><span class="lm">${esc(e.msg || '')}</span>` +
          (det ? `<span class="ld">${esc(det)}</span>` : '') +
          '</div>'
        );
      })
      .join('') || '<div class="log-row"><span class="ld">(暂无日志 —— 点「立即拉取一次」, 或把记录级别调到 debug)</span></div>';
  const clipped = rows.length > LOG_RENDER_CAP ? `(只渲染最近 ${LOG_RENDER_CAP} 条, 更早的请收窄过滤)` : '';
  $('logCount').textContent = `共 ${logAll.length} 条 · 过滤后 ${rows.length} 条 ${clipped}`;
}

async function refreshLogs() {
  const got = await chrome.storage.local.get({ logs: [] });
  logAll = Array.isArray(got.logs) ? got.logs : [];
  renderLogs();
}

/** 后台每次落盘都自动重渲染(防抖): 「立即拉取」跑完日志自己刷出来, 不用手点 */
function scheduleLogRender() {
  if (logRenderTimer) return;
  logRenderTimer = setTimeout(() => {
    logRenderTimer = null;
    refreshLogs().catch((e) => setStatus(`刷新日志失败: ${e.message || e}`));
  }, 300);
}

async function applyLogSettings() {
  const max = clampLogMaxInput();
  const lvl = $('logLevel').value;
  await chrome.storage.local.set({ logMax: max, logLevel: lvl });
  setStatus(`日志设置已生效: 最多留 ${max} 条, 记录 ${lvl} 及以上(更低的直接丢弃, 不占额度)`);
}

async function clearLogsClick() {
  try {
    const res = await chrome.runtime.sendMessage({ type: 'clear-logs' });
    if (!(res && res.ok)) setStatus(`清空失败: ${(res && res.error) || '未知原因'}`);
  } catch (e) {
    // 后台没应答(多半刚被回收): 直接落 storage —— 后台醒来初始化时会读到这份空数组
    await chrome.storage.local.set({ logs: [] });
    setStatus(`经 storage 直接清空(后台未应答: ${e.message || e})`);
  }
  await refreshLogs();
}

// 兜底: 任何漏网的拒绝都在这里落到状态栏, 不再出现 "Uncaught (in promise)"
window.addEventListener('unhandledrejection', (ev) => {
  setStatus(`未处理的错误: ${(ev.reason && ev.reason.message) || ev.reason}`);
});

// ---------- 接线 ----------

$('addInstance').addEventListener('click', () => addInstance().catch((e) => setStatus(String(e))));
$('newInstance').addEventListener('click', () => fillForm(null));
$('instList').addEventListener('click', (ev) => instListClick(ev).catch((e) => setStatus(String(e))));
$('fetchSites').addEventListener('click', () => fetchSites(true).catch((e) => setStatus(String(e))));
$('selectAllSites').addEventListener('click', selectAllSites);
$('grantChecked').addEventListener('click', () => grant().catch((e) => setStatus(String(e))));
$('siteChecks').addEventListener('change', () => siteChecksChange().catch((e) => setStatus(String(e))));
$('save').addEventListener('click', () => save().catch((e) => setStatus(String(e))));
$('test').addEventListener('click', () => testEndpoint().catch((e) => setStatus(String(e))));
$('poll').addEventListener('click', () => poll().catch((e) => setStatus(String(e))));
$('enabled').addEventListener('change', () => save().catch((e) => setStatus(String(e))));
$('logMax').addEventListener('change', () => applyLogSettings().catch((e) => setStatus(String(e))));
$('logLevel').addEventListener('change', () => applyLogSettings().catch((e) => setStatus(String(e))));
$('logFilter').addEventListener('change', () => {
  logFilterMin = LOG_RANK[$('logFilter').value] || 0;
  renderLogs();
});
$('logRefresh').addEventListener('click', () => refreshLogs().catch((e) => setStatus(String(e))));
$('logClear').addEventListener('click', () => clearLogsClick().catch((e) => setStatus(String(e))));
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== 'local') return;
  if (changes.logs) scheduleLogRender();
  if (changes.events || changes.siteLedger) scheduleTablesRender(); // 两表随后台落盘自动刷新
});
load().catch((e) => setStatus(`读取配置失败: ${e.message || e}`));
