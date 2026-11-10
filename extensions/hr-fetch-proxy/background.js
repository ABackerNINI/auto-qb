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
importScripts('background-log.js');
importScripts('background-support.js');

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
    servedVerdict: null, // 服务裁决快照(runDiscovery 每轮写; 三条外呼路径消费面据此过滤)
  });
  return {
    enabled: Boolean(got.enabled),
    instances: Array.isArray(got.instances) ? got.instances : [],
    siteOrigins: Array.isArray(got.siteOrigins) ? got.siteOrigins : [],
    discoveryAddress: String(got.discoveryAddress || '').trim(),
    pairingCode: String(got.pairingCode || '').trim(),
    servedVerdict: got.servedVerdict && typeof got.servedVerdict === 'object' ? got.servedVerdict : null,
  };
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
  // 消费面过滤(S4a 裁决): 外呼只打服务集(手动恒在; 发现条目按 servedVerdict) —— 存储全量留给选项页
  const serveList = servedInstancesOf(conf.instances, conf.servedVerdict);
  if (!conf.enabled || !serveList.length) return 0;
  let total = 0;
  for (const inst of serveList) {
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
    endpoints = conf.instances.map((e) => String((e && e.endpoint) || '')); // 台账剪枝看全量(裁决翻面不丢历史)
    // 消费面过滤(S4a 裁决): 只轮询服务集(手动恒在; 发现条目按 servedVerdict) ——
    // needsSelection / ambiguous / selectedMissing / noAnswer 态这里只剩手动条目, 不混轮任何 clone
    const serveList = servedInstancesOf(conf.instances, conf.servedVerdict);
    log('info', '轮询', `轮询开始(${trigger || '定时'}): ${serveList.length} 个实例`, {
      扩展启用: conf.enabled ? '是' : '否',
      裁决: conf.servedVerdict && conf.servedVerdict.state ? conf.servedVerdict.state : '(未裁决)',
    });
    if (!conf.enabled) return;
    if (!conf.instances.length) {
      await noteStatus({ text: '未配置实例端点(打开选项页填写)' });
      await maybeDiscover(0); // !实例为空也要跑周期发现(R1): 否则发现集为空时连接再也回不来
      return;
    }
    const lines = [];
    let failCount = 0;
    for (const inst of serveList) {
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
  const endpoints = conf.instances.map((e) => String((e && e.endpoint) || '')); // 台账剪枝看全量
  // 消费面过滤(S4a 裁决): 只探测服务集(手动恒在; 发现条目按 servedVerdict) —— 未被服务的
  // 发现条目不进探测结果(选项页列表仍列全量, 行级开关接线属 T4)
  const serveList = servedInstancesOf(conf.instances, conf.servedVerdict);
  const results = [];
  for (const inst of serveList) {
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
