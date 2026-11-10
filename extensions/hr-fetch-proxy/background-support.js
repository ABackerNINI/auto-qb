// auto-qb HR 取数代理 · 发现 / 徽标 / 网络与配额支撑(从 background.js 原样搬迁)
// 由 background.js 顶层 importScripts 在日志之后、主体之前载入; 与主体共享同一全局作用域。

// ---------- 自动发现(计划 26-10-14-1241 S4; 自愈/可见性于 26-10-15-2357 S2) ----------
//
// 触发器: 启动时(onInstalled/onStartup)/ **任一实例拉取失败时**(1 分钟节流, Q3)/ 每 2 分钟(Q3)/
// 选项页「立即发现」。探测 = 对候选表(发现地址起连号 8 个)**并行 fetch**, 仅接受 200 + 合法
// 发现响应形态 —— 普通应用误占端口的异形应答/404/连接拒绝一律按「非本服务」忽略; 命中的应答
// **全部收集**进裁决状态机(计划 26-11-10-0515 装置二: find-first 已废止, 服务谁由裁决定,
// 命中端口记入状态行)。发现失败不静默(日志 + 状态行 + 结构化快照 + 徽标),
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
    // S4a(计划 26-11-10-0515): 多命中收集 + 显式裁决 —— ports = 全部命中端口, verdict = 裁决态
    // (六态: auto/selected/ambiguous/needsSelection/selectedMissing/noAnswer), served = 本轮实际
    // 服务条数(与消费面同口径, 见 runDiscovery); 3 条后台外呼(pollAll/requestBackendRefresh/
    // probeAll)已按 servedInstancesOf + servedVerdict 接线, 选项页两处接线属 T4
    ports: Array.isArray(patch.ports) ? patch.ports.map((p) => String(p || '')) : [],
    verdict: String(patch.verdict || ''),
    served: Number(patch.served) || 0,
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
 * 跑一轮发现: 归一化发现地址 -> 候选表并行探测 -> **收集全部命中**(S4a 起 find-first 废止,
 * 每份 ok 应答 = 一个干净 clone) -> 合并全部应答的实例 + 按裁决状态机(adjudicateInstances,
 * 计划 26-11-10-0515 装置二)定「服务谁」/ 401 pairing_required 标记 / 全未命中明确报告(不静默)。
 * lastDiscoveryAt 每次**尝试**后都更新(节流按尝试计);
 * 每次收尾都落结构化快照 + 刷徽标(选项页与工具栏都能看见这一轮的结论)。
 *
 * 裁决落盘口径(S4a):
 *   · 选择存**独立存储键 activeNames**(按标签 name 记)—— 不随 instances 的 mergeInstances
 *     整批替换 / options 三键重建被动改写, 改选/清除只经显式写(选项页接线属 T4);
 *     auto 态且应答标签去重后恰 1 个才持久化 —— legacy 聚合应答(标签 >1, 旧后端随机 uuid)
 *     不 pin: 服务整份照收(D8), 下轮重新裁决(否则 uuid 被 pin, 升级后 selectedMissing 恒态);
 *     pin 前重读一次 activeNames(T4 评审修 3): 与选项页 serveToggleChange 是双写者, 重读非空 =
 *     用户在窗口内已改选, 放弃本次 pin 不覆盖(auto 态的选择只在无选择时产出, 裁决时必读到空);
 *   · >=2 份且无选择 -> 零服务(裁决态 needsSelection, 供 T4 横幅); 手动条目恒服务(P2);
 *   · 每轮都落**服务裁决快照键 servedVerdict = {state, discovered, at}**(discovered = 被服务的
 *     发现条目 endpoint 表): 三条外呼路径(pollAll / requestBackendRefresh / probeAll)消费时经
 *     servedInstancesOf 按它过滤 —— 存储发现条目仍全量(选项页列全), 消费面只打服务集;
 *     四个非服务态默认 discovered = 空(只打手动); 唯一例外是「全部命中应答空 instances」的
 *     C1 沿用(见下方行内注释): 该轮沿用上轮白名单, 不清空;
 *   · 快照 served 数按 servedInstancesOf(合并后清单, 落盘白名单)计, 与外呼实际消费集同源一致
 *     (非 verdict.served.length —— 沿用轮 verdict.served 只含手动, 与快照数不相等)。
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
  const hits = probes.filter((p) => p.ok);
  const responses = hits.map((h) => ({ port: h.port, instances: h.data.instances }));
  const got = await chrome.storage.local.get({ instances: [], activeNames: [], servedVerdict: null });
  const manual = got.instances.filter(isManualEntry);
  const verdict = adjudicateInstances(responses, got.activeNames, manual);
  // 服务裁决落盘(消费面依据): served = 手动 + 被服务应答, 其中发现部分按 endpoint 记 ——
  // 手动部分不记表(消费时 isManualEntry 现判, 裁决轮间隙新加的手动条目照常服务)
  const manualEps = new Set(manual.map((e) => String((e && e.endpoint) || '')));
  let discoveredServed = verdict.served
    .map((e) => String(e.endpoint || ''))
    .filter((ep) => ep && !manualEps.has(ep));
  // C1 消费面对齐(评审轮 2 修 1): 有命中但全部应答空 instances(单 clone 重启、registry 未热身的
  // 「200 + instances:[]」瞬间)—— 落库面 C1 特意保留 prevDiscovered, 消费面若清空白名单 = 停服;
  // 且停服后零外呼零失败, 「失败即发现」自愈触发器打不动(只剩 2 分钟周期), 徽标靠冻结台账失真。
  // 此时沿用上轮白名单 —— 保留语义, 不是改投: 上轮白名单就是上轮正被服务的那些端点, 若它们真
  // 死了, 轮询失败照常触发发现, 自愈链路完整。
  const prevVerdict = got.servedVerdict && typeof got.servedVerdict === 'object' ? got.servedVerdict : null;
  if (
    hits.length > 0 &&
    responses.every((r) => r.instances.length === 0) &&
    discoveredServed.length === 0 &&
    prevVerdict &&
    Array.isArray(prevVerdict.discovered) &&
    prevVerdict.discovered.length > 0
  ) {
    discoveredServed = prevVerdict.discovered.map((e) => String(e || '')).filter(Boolean);
  }
  const servedVerdict = { state: verdict.state, discovered: discoveredServed, at: Date.now() };
  // served 计数与消费面**同一把尺**(评审轮 2 修 3): 直接按 servedInstancesOf(全量实例清单, 落盘
  // 白名单)数 —— 覆盖 C1 沿用(空应答沿带上轮白名单)与手动现判两种口径差, 快照/状态行不说谎。
  // 命中轮要按**合并后**的清单数(新发现条目刚落库, 消费面下轮就能看到它们)
  let servedCount;
  if (hits.length > 0) {
    const merged = mergeInstances(got.instances, responses.flatMap((r) => r.instances));
    servedCount = servedInstancesOf(merged, servedVerdict).length;
    const patch = { instances: merged, pairingNeeded: false, servedVerdict: servedVerdict };
    if (verdict.state === 'auto' && verdict.selection.length > 0) {
      // auto pin 前重读 activeNames(T4 评审修 3): 本处与选项页 serveToggleChange 是 **activeNames 的
      // 双写者** —— 裁决读取到落盘的窗口内用户的勾选会被整组覆盖(last-write-wins, 下轮按被覆盖值
      // 裁决)。auto 态的选择只在「无选择」时产出(adjudicateInstances: sel 非空走 selected 分支),
      // 故裁决时读到的必是空 —— 重读仍为空才 pin; 非空 = 用户刚改选, 放弃本次 pin, 下轮发现按
      // 用户选择重新裁决, 选择保住。
      const re = await chrome.storage.local.get({ activeNames: [] });
      const stillEmpty = !Array.isArray(re.activeNames) || re.activeNames.length === 0;
      if (stillEmpty) {
        patch.activeNames = verdict.selection; // 唯一标签才记住(legacy 聚合 >1 标签不 pin, 下轮重新裁决)
      }
    }
    await chrome.storage.local.set(patch);
    const ports = hits.map((h) => h.port);
    const totalDisc = responses.reduce((n, r) => n + r.instances.length, 0);
    const msg = `自动发现命中(${ports.join('/')}): 合并 ${totalDisc} 个实例, 共 ${merged.length} 条, 服务 ${servedCount} 条`;
    await noteStatus({ text: msg });
    log('info', '发现', msg, { 触发: trigger || '手动', 候选: candidates.join(' / '), 命中: ports.join(' / '), 裁决: verdict.state });
    await noteDiscoveryResult({
      ok: true, port: ports[0], ports: ports, verdict: verdict.state, served: servedCount,
      merged: merged.length, candidates: candidates, probes: probes, answered: true
    });
    return { ok: true, merged: merged.length, verdict: verdict.state, served: servedCount };
  }
  if (probes.some((p) => p.pairingRequired)) {
    servedCount = servedInstancesOf(got.instances, servedVerdict).length;
    await chrome.storage.local.set({ pairingNeeded: true, servedVerdict: servedVerdict });
    const msg = '发现端点要求配对码: 到选项页「自动发现」填入后端展示码(启动日志/HR 状态卡可见)';
    await noteStatus({ text: msg }, 'warn');
    log('warn', '发现', msg, { 触发: trigger || '手动' });
    await noteDiscoveryResult({ ok: false, reason: 'pairing_required', verdict: verdict.state, served: servedCount, candidates: candidates, probes: probes, answered: true });
    return { ok: false, reason: 'pairing_required' };
  }
  const msg = '自动发现未命中(数据端点照常; 退路 = 选项页「手动端点」显式指定实例)';
  servedCount = servedInstancesOf(got.instances, servedVerdict).length;
  await noteStatus({ text: msg });
  log('warn', '发现', msg, { 触发: trigger || '手动', 候选: candidates.join(' / '), 明细: probes.map((p) => p.note).join(' | ') });
  await chrome.storage.local.set({ servedVerdict: servedVerdict }); // 零应答: 发现条目全部停服(只打手动), 自愈靠下轮发现
  await noteDiscoveryResult({
    ok: false, reason: 'no-hit', verdict: verdict.state, served: servedCount, candidates: candidates, probes: probes, answered: probes.some((p) => p.answered)
  });
  return { ok: false, reason: 'no-hit', verdict: verdict.state };
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
  // !anyOk 按**服务集**算(评审轮 2 修 2): 停服条目(如 needsSelection 后被停的原 clone)的健康台账
  // 是冻结的, 按全量算 anyOk 恒真 = 徽标持续亮「连接正常」, 与裁决态的 P2「显性失败: 亮着等选」
  // 矛盾(T4 横幅接线前徽标是用户唯一可见面)。servedVerdict 缺失(升级瞬态)时退化全量, 行为不变。
  const served = servedInstancesOf(instances, cfg.servedVerdict);
  const health = cfg.instanceHealth && typeof cfg.instanceHealth === 'object' ? cfg.instanceHealth : {};
  const anyOk = served.some((e) => {
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
      servedVerdict: null, // 服务裁决快照: anyOk 按服务集算(停服条目台账冻结, 不能替它亮绿灯)
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
