// 选项页: 读/写 chrome.storage.local, 申请站点权限, 自测端点连通性, 手动触发一次拉取。
//
// ❗这里是**唯一**能替用户挡住"格式写错"的地方 —— 浏览器 API 对格式极其严格且报错难懂:
//   · chrome.permissions.request 只吃**匹配模式**(必须带 scheme), 裸域名报
//     "Invalid value for origin pattern xxx: Missing scheme separator." 且是**未捕获的拒绝**;
//   · fetch 的 URL 必须带 scheme 与回环主机, 否则报一句 "TypeError: Failed to fetch"(什么都看不出来)。
// 所以本页一律"先归一化、再落盘", 并把失败逐条翻译成中文可操作提示; 绝不让 Promise 裸抛。
//
// 策略与频控判断**不在这里** —— 那唯一权威在后端。
// 地址归一化共用 normalize.js(与后台同一份, 免得两条路径各自演化)。

const $ = (id) => document.getElementById(id);

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

// ---------- 动作 ----------

async function load() {
  const got = await chrome.storage.local.get({
    enabled: true, instances: [], siteOrigins: [], status: {}, siteLedger: {},
  });
  $('enabled').checked = Boolean(got.enabled);
  $('instances').value = got.instances.map((i) => JSON.stringify(i)).join('\n');
  $('origins').value = got.siteOrigins.join('\n');
  const st = got.status || {};
  if (st.text) setStatus(`${new Date(st.at || Date.now()).toLocaleString()} — ${st.text}`);
  renderCaps(got.siteLedger || {});
}

/**
 * 展示两道闸的额度与今日/本小时用量。
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

async function save() {
  try {
    const instances = parseInstances();
    const { good, bad } = parseOrigins();
    await chrome.storage.local.set({ enabled: $('enabled').checked, instances, siteOrigins: good });
    // 把归一化后的结果写回输入框: 用户才能看到"实际存进去的是什么"
    $('instances').value = instances.map((i) => JSON.stringify(i)).join('\n');
    $('origins').value = good.join('\n');
    const tail = bad.length ? `; ${bad.length} 条站点源被跳过(格式不对): ${bad.join(' / ')}` : '';
    setStatus(`已保存: ${instances.length} 个实例, ${good.length} 个站点源${tail}`);
    hint(bad.length ? '格式不对的站点源已跳过, 修正后重新保存即可。' : '');
  } catch (e) {
    setStatus(`保存失败: ${e.message || e}`);
    hint('');
  }
}

async function grant() {
  const { good, bad } = parseOrigins();
  if (!good.length) {
    setStatus(`没有可申请的站点源${bad.length ? ':' + bad.join(' / ') : ''}`);
    return;
  }
  hint('申请的是这些匹配模式: ' + good.join(', '));
  try {
    // ❗授权窗必须由用户手势直接触发: 这里前面不能有 await(否则 Chrome 报"not during a user gesture")
    const ok = await chrome.permissions.request({ origins: good });
    const badTail = bad.length ? `; 跳过 ${bad.length} 条格式不对的: ${bad.join(' / ')}` : '';
    setStatus(ok ? `已授予 ${good.length} 个站点源` : `站点权限被拒绝(再点一次授权即可重试)${badTail}`);
  } catch (e) {
    // 典型: 某个模式仍不合法 / 非用户手势 —— 必须消化掉, 不能让 Promise 裸抛(用户只会看到红字英文)
    setStatus(`申请站点权限失败: ${e.message || e}`);
  }
}

/** 直连后端端点自测: 把"通了/401/连不上"分清楚, 并给出下一步该查什么 */
async function testEndpoint() {
  let instances;
  try {
    instances = parseInstances();
  } catch (e) {
    setStatus(`自测中止: ${e.message || e}`);
    return;
  }
  const inst = instances[0];
  if (!inst) {
    setStatus('先填一个实例端点再自测');
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
      hint('打开后端数据目录下的 hr.token, 把内容整串粘到实例的 token 字段再保存。');
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
      setStatus(`拉取失败: ${(res && res.error) || '未知'}(详见扩展的后台 console)`);
    }
  } catch (e) {
    // SW 未就绪/已休眠时会走到这里 —— 别让红字裸奔
    setStatus(`与服务线程通信失败: ${e.message || e}`);
    hint('重开一次选项页再试; 若仍失败, 到 chrome://extensions 看本扩展的「Service Worker」控制台。');
  }
}

// 兜底: 任何漏网的拒绝都在这里落到状态栏, 不再出现 "Uncaught (in promise)"
window.addEventListener('unhandledrejection', (ev) => {
  setStatus(`未处理的错误: ${(ev.reason && ev.reason.message) || ev.reason}`);
});

$('save').addEventListener('click', () => save().catch((e) => setStatus(String(e))));
$('grant').addEventListener('click', () => grant().catch((e) => setStatus(String(e))));
$('test').addEventListener('click', () => testEndpoint().catch((e) => setStatus(String(e))));
$('poll').addEventListener('click', () => poll().catch((e) => setStatus(String(e))));
$('enabled').addEventListener('change', () => save().catch((e) => setStatus(String(e))));
load().catch((e) => setStatus(`读取配置失败: ${e.message || e}`));
