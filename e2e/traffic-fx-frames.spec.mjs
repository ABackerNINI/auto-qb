// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { INST, readInst } from './lib/vm.mjs';
import { installRouteCleanup } from './lib/route-cleanup.mjs';

installRouteCleanup(test);   // 本文件全部用例收尾时卸载全部 route.fetch 桩(收尾竞态兜底, 合流接线)

/**
 * 节拍动效的**帧级采样探针**(plan 26-11-12-1139 §10 建议新增里判给 P8 的画布/真机面;
 * P7 覆盖矩阵 G1/G2/G5 三条的 e2e 端) —— 对应两条用例:
 *
 *   A. 左移连续性(G2/R1): 真窗口每拍滚动一格时, 相邻两拍**边界**的视口位移 <= 1px(不回跳),
 *      拍内视口平滑滑入一格(smooth 档真播)、每拍墙钟 <= animEnd + 采样余量(G1「真值落地
 *      <= 1s」的真机面)、data/xs0 全程冻结且逐拍右移(「L0 不动 data、只改视口」)。
 *      机理解释: 拍 N 收敛在真窗 [T-W, T], 拍 N+1 判定帧把视口摆回 [T-W, T](偏置 = 新真窗
 *      减 dx0), 数学上边界两值恒等 —— 断言 <= 1px 留的是浮点/时序余量; 若有人把偏置摆错
 *      (回跳/跳两格/瞬时落地), 边界位移立刻变成一格宽(数十 px), 必红。
 *
 *   B. 预览拍帧级探针(§05.9 面板拍 + §10 面板探针第 3 条/背景静态 G5): 预览期间逐帧断言
 *      u.data[0](xs)与 u.scales.x.min/max 不变、dx ≡ 0; 背景两点(绘图区中央 / 右缘带)
 *      连拍逐帧 alpha 恒 0 且两点相等(G5「背景 RGB 恒定且两点相等」的画布采样面 —— 画布
 *      未落墨的像素恒为全透明, 装饰描边/曲线/网格的像素 alpha > 0, 所以「alpha 恒 0」
 *      等价于「这两点整轮测试没有任何一笔铺底/呼吸」); 末帧还原真值(假值不留痕);
 *      粒子清单合计 <= 32。
 *
 * 为什么探针点敢选「右缘带」而装饰(束/环/粒子/回声)就在右缘活动: 装饰的空间范围由 I9 常量
 * 决定 —— 环 rMax <= 29px、粒子行程 <= 1.6x29 ≈ 47px、尾光沿末段 6 桶(约 6 格宽)、回声
 * span 用面板下拉钉到 100px; 探针点 2 取 R-130, 与最近装饰行程至少隔 30px。扫描一次透明带
 * 避开曲线/网格的静态像素; 预览期间窗口/轴全程冻结(无 setScale x、y 钉死), 几何不漂移,
 * 静态扫描结果对整窗有效 —— 这是选「预览拍」做像素探针的可行性根据。
 * 断言口径说明: 电池已钉「fx/束体域 fillRect 恰 1 处且 1px 级」(铺底面); 本探针补的是
 * 真渲染面 —— 任何整块铺底/背景呼吸会画到**所有**像素, 探针点虽在装饰行程之外也必红;
 * 装饰描边本身落在探针行程之外是几何常量决定的(见上), 不是断言放水。
 *
 * 采样纪律(对照 drawer-switch-no-flash 的量具模式): 采样器装在页面 rAF 上(Node 侧装不上
 * —— D4 第 2 类 evaluate: vm 内部时序探针), 结束条件是页面侧状态(拍段计数/预览令牌翻转),
 * Node 侧只 expect.poll 这个旗标 —— 零 waitForTimeout、零固定睡等。
 * 容器软件渲染的 rAF 帧距比真机大一个量级: 涉及墙钟的断言(拍时长)用 animEnd + 900ms 余量,
 * 帧数下限压到 3/5/10 —— 帧距变大只减少采样密度, 不改变逐帧不变性断言的语义。
 *
 * 量具裁剪留档(§10 扫描束探针不进 e2e): 束体「逐帧指令 <= 23 / 整块 fillRect = 0 / 回声
 * 行程与硬停」在电池 S1-S8 里用记账 ctx 真跑覆盖; e2e 真渲染下没有指令钩子可挂, 要逐帧数
 * 指令就得给生产热路径包 monkey-patch —— 量具改生产, 违反探针纪律, 故该面按可行性裁剪,
 * e2e 只保留画布像素面(本文件 B 的背景两点 + 左移连续性)。
 *
 * 同批留档(覆盖矩阵 G3/G6 两行「-> P8」的裁决): 曲线像素对比度(G3)与「任一帧 strokeStyle
 * 恒语义色」(G6)也不进 e2e —— 电池级等价 = 曲线描边恒 uPlot 系列原生(I11 黑名单钉: fx 域
 * 零触碰 series/legend/cursor) + 层序钉(drawAxes 整段先于系列原生, I6), 像素面拿不到确定性
 * 基准(描边色走四皮肤令牌现读, 随皮肤/明暗主题变; 抗锯齿混色逐帧噪), 强比对即 flaky。
 *
 * 桩口径(traffic-gap-zones 同款): 只翻 qb_traffic_enabled; /api/traffic/qb/torrent/* 造
 * 真契约形状的 60 桶帧。A 用 interval_s=2(轮询 2s 一拍 = beat 800ms, 三拍 ~7s 采完)且
 * **每次请求恰推进一格**(计数器递增 base, 与墙钟解耦 —— roll 判据 dx0 <= 2 格恒成立);
 * 值恒定 -> L1 静默(needsTail=false), 拍只剩 L0 视口左移, 边界断言不被数值收敛干扰。
 * B 用 interval_s=30(si=30 -> 轮询 30s 一拍)且 base 固定(数据静止): F8 后开场 ~1.5s 有一发
 * 首拍重试拉数(真零变化拍, F6 后带 fx-only anim), 其后 30s 内无真拍 —— 预览交互前经
 * waitForFirstRetryBeat 等第二笔真拍落地, 预览语义断言吃 isPreview 令牌过滤(真拍帧不进
 * 预览断言域)。
 *
 * S3a 复核(plan 26-11-14-1313, B5 批): F3 栅格 floor+1(尾桶恒「进行中桶」)与 F1 恒 >=Lv.1
 * 落地后逐条对照本文件的判据面 —— 结论:
 *   · A 的 L0 判据面(边界 <=1px / 拍内平滑 / 单调不回跳 / dx0>0 / 拍内数据冻结 / xsLen =
 *     真窗口点数或 +1)与 F3/F5 相容: 60 桶整倍窗真点数恒 60 -> rewin 判据(F5 后 = 窗几何
 *     不连续, 点数退役)恒 false, 每拍必走 roll 路径; F5 补尾格使判定帧显示列 +1(收敛帧出列),
 *     点数断言随之放宽为 {60, 61} 两态 —— 旧 ceil 栅格 n 方波翻转(瞬时多格跳)的形态在本桩
 *     下不可再回潮;
 *   · 「L1 静默」指数值收敛(prev==target, needsTail=false), 口径不变; F1 后值>0 的滚窗拍
 *     另带 Lv.1 装饰(S7b 电池口径: anim.fx 恒在场), 装饰不触碰视口/数据断言面;
 *   · 【按新语义改写】拍段切分: F1 后恒定正值滚窗拍的收敛帧衔接**次区相位**(tail 光点窗,
 *     min(period-beat,2000) 恰填满拍间) -> anim 全程为真, 旧的「anim 连续段 = 拍段」分组
 *     把整段采样并成一段、done 条件(3 段后 anim 归位)永不触发 —— 实测 anim 真 30s 连续。
 *     拍段改按**相位**切: 连续 impact 相位帧 = 一个主区拍段(tail 段的视口恒收敛真位, 恰是
 *     下一拍摆回的旧位, 边界连续性判据经 tail 帧对照依然成立)。零流量拍(A3)真 0 -> fx
 *     null -> 无 tail 相位, 新旧切分等价;
 *   · 尾桶语义变化(未完成桶 -> 恒「进行中桶」): advancing 桩恒给尾桶观测, 与 F4 活尾延伸
 *     后的生产形态同构, 尾值恒定断言不受影响。
 * A1/A3/A5 三条专项用例(计划 §01 验收表)与重写的裁剪面用例(C)追加在本文件尾部, 各自注明
 * 判据与桩面。
 *
 * A2 三窗帧采样(plan 26-11-15-1104, F5 批; 评审轮1 finding4 两类翻动拍签名都逐帧钉)追加在
 * 文件尾部: 左端像素连续性全帧判据(曲线左端 <= 1px —— 补尾格后判定帧左端贴住摆回视图左缘,
 * G-B「摆回固有左缺口瞬移」的判别面)覆盖 1m/5m/24h 三窗(24h = 非整倍窗, 脚本化注入两类相位
 * 翻动拍) —— 翻动拍一(498->497 形: 起点 +1 格/末点不动/点数 -1)照常播 L0(旧 rewin 裸点数
 * 判据误判换档即签名缺席); 翻动拍二(497->498 形: 起点不动/末点 +1 格/点数 +1)不 rewin 且
 * 入 roll(dx0=0 位移在 max 侧 —— 评审轮1 finding1 roll 放宽): L0 照播(min 恒驻/max 滑一格),
 * 旧判据瞬跳或 roll 门未放宽缺席即签名红。
 *
 * A3 零变化拍环境层解绑(F6/D3, plan 26-11-15-1104)追加在文件尾部: 稳态零变化拍(base 固定
 * -> dx0=0, 值恒正 -> needsTail false)每拍 anim.fx 在场 lv>=1 + needsShift/needsTail 双 false
 * 签名 + 数据/视口面零改写 —— G-C「粒子时有无」根治面的真机钉(旧判据该类拍整拍静默)。
 *
 * C(裁剪面机制探针, F5/plan 26-11-14-1313, A6 的真机面; B5 改渲染对齐记账): 原版在 rAF
 *   渲染间读右缘带像素 —— 本环境实测渲染管线落定后的画布读不到装饰墨(B5 取证: 装饰墨只在
 *   渲染管线内可观测, rAF 渲染间读数恒 0 假阴性), 像素探针不可落地。改为包住 drawAxes 钩子
 *   + ctx.rect 记账(只读运行时包装, 与 vm 内部时序探针同类), 直接钉 F5 改的那件事本身:
 *   fx 段 clip 实参 = rect(L, T, max(W, canvasW-L), H) —— 右缘放宽到画布右缘、下缘不放宽。
 *   与电池 G0 的 clip 实参记账同契约, 在真浏览器真渲染路径上复核; 近底环心钳制(P3)与粒子
 *   镜像由电池 G11/G12 钉。仍走预览拍(窗口/轴冻结, 几何不漂移)。
 */

const N = 60;

/** 造一帧 payload; advancing 时 base 由调用方按请求序推进一格; vals 可改两轨速率值
 * (A3 用 { up: 0, dl: 0 } 造真 0 稳态流 —— F1 下真 0 仍 Lv.0 静默的对照面) */
function makePayload(base, interval, vals) {
  const up = vals && vals.up !== undefined ? vals.up : 1000;
  const dl = vals && vals.dl !== undefined ? vals.dl : 2000;
  const points = new Array(N).fill(null);
  const totals = new Array(N).fill(null);
  for (let i = 0; i < N; i++) {
    const t = base + i * interval;
    points[i] = { t, dl, up };
    totals[i] = { t, dl, up };
  }
  return {
    points,
    totals,
    limits: [],
    meta: {
      window: '24h',                 // 前端不校验 points 长度 vs window(traffic-gap-zones 同款偏差)
      interval_s: interval,
      // F7(plan 26-11-15-1104 D6)后轮询节奏读生效采样间隔 —— 生产 _meta 单点全窗携带, 桩对齐
      sample_interval_s: interval,
      source: 'qb',
      stale: false,
      server_started_at: base - 3600,  // 远在链末前 -> 接缝提示出 null, 不干扰
    },
  };
}

async function stubFlags(page) {
  await page.route('**/api/webui/flags', async (route) => {
    const json = await (await route.fetch()).json();
    return route.fulfill({ json: { ...json, qb_traffic_enabled: true } });
  });
}

/** A 用: 每次请求恰推进一格(计数器解耦墙钟), interval_s=2 -> 轮询 2s/拍 800ms。
 * 值恒定 -> L1 静默(needsTail=false), 拍只剩 L0 视口左移, 边界断言不被数值收敛干扰。 */
async function stubTrafficAdvancing(page) {
  const interval = 2;
  const b0 = Math.floor(Date.now() / 1000 / interval) * interval - (N - 1) * interval;
  let calls = 0;
  await page.route('**/api/traffic/qb/torrent/*', (route) =>
    route.fulfill({ json: makePayload(b0 + (calls++) * interval, interval) }));
  return interval;
}


/** B 用: base 固定(数据静止), si=30 -> 轮询 30s 一拍: F8 后开场 ~1.5s 有一发首拍重试真拍,
 * 其后 30s 内无真拍(预览交互前经 waitForFirstRetryBeat 垫过首拍窗口) */
async function stubTrafficStill(page) {
  const interval = 30;
  const b0 = Math.floor(Date.now() / 1000 / interval) * interval - (N - 1) * interval;
  await page.route('**/api/traffic/qb/torrent/*', (route) =>
    route.fulfill({ json: makePayload(b0, interval) }));
}

/** A3 零变化拍用(F6/D3, plan 26-11-15-1104): base 固定(窗起点不动 -> dx0=0 -> roll=false)
 * + 值恒正(稳态流) -> 每拍 needsShift/needsTail 双 false(零变化拍); interval_s=2 快拍。
 * 旧判据(spawn 在早退门后)这类拍整拍静默 —— F6 后每拍出环境层。 */
async function stubTrafficZeroChange(page) {
  const interval = 2;
  const b0 = Math.floor(Date.now() / 1000 / interval) * interval - (N - 1) * interval;
  await page.route('**/api/traffic/qb/torrent/*', (route) =>
    route.fulfill({ json: makePayload(b0, interval) }));
  return interval;
}

/** A3 用: 每次请求恰推进一格 + 两轨速率恒 0(真 0 稳态流 —— A3 的「零流量但采样活跃」形态) */
async function stubTrafficAdvancingZero(page) {
  const interval = 2;
  const b0 = Math.floor(Date.now() / 1000 / interval) * interval - (N - 1) * interval;
  let calls = 0;
  await page.route('**/api/traffic/qb/torrent/*', (route) =>
    route.fulfill({ json: makePayload(b0 + (calls++) * interval, interval, { up: 0, dl: 0 }) }));
  return interval;
}

/** A5 停滞态用: base 固定 + 尾部 GAP_N 桶无观测(qB 断连后的真缺口形态, interval_s=30 静图)。
 * 全 0 尾游程不经 F4 活尾延伸(e2e 直接桩 API 帧, 后端延伸面由 B2 电池钉) —— 前端看到的
 * 就是「链末桶之后整段无观测」的诚实缺口。 */
const GAP_N = 6;
async function stubTrafficGapTail(page) {
  const interval = 30;
  const b0 = Math.floor(Date.now() / 1000 / interval) * interval - (N - 1) * interval;
  const payload = makePayload(b0, interval);
  for (let i = N - GAP_N; i < N; i++) {
    payload.points[i] = null;
    payload.totals[i] = null;
  }
  await page.route('**/api/traffic/qb/torrent/*', (route) => route.fulfill({ json: payload }));
}

/** C 用: base 固定 + up 贴底小值(dl 顶格抬 yMax -> up 落绘图区底部 ~2% 处, 近底环探针前提)。
 * up=4200 = yMax(210000) x 2%: 环心上抬钳制 [T+rMax, T+H-rMax] 与底缘镜像反弹都有实料可验;
 * 预览假 Δ(impact 0.425 档)target=4200x(1-0.425)=2415 > 0(真 0 不触发)。 */
async function stubTrafficBottom(page) {
  const interval = 30;
  const b0 = Math.floor(Date.now() / 1000 / interval) * interval - (N - 1) * interval;
  const points = new Array(N).fill(null);
  const totals = new Array(N).fill(null);
  for (let i = 0; i < N; i++) {
    const t = b0 + i * interval;
    points[i] = { t, dl: 200000, up: 4200 };
    totals[i] = { t, dl: 200000, up: 4200 };
  }
  const payload = makePayload(b0, interval);
  payload.points = points;
  payload.totals = totals;
  await page.route('**/api/traffic/qb/torrent/*', (route) => route.fulfill({ json: payload }));
}

/** A2 三窗案(plan 26-11-15-1104)用: 脚本化帧桩 —— 每请求推进一格(墙钟解耦), script 条目
 * 覆盖该请求的窗形态: 'roll' = 正常一格滚动(n 恒) / 'flipA' = 相位翻动拍一(窗起点 +1 格、
 * 窗末点不动、点数 -1 —— 非整倍窗 498->497 形) / 'flipB' = 相位翻动拍二(窗起点不动、窗末点
 * +1 格、点数 +1 —— 497->498 形)。script 尽后恒 roll。meta.window 只作标签(前端不校验
 * points 长度 vs window —— 文件头同款偏差); 三窗(1m/5m/24h)共用同一推进机理, 差异只在桶数
 * (cellPx 级别)。
 * 状态机(base = 下一 roll/flipA 帧的窗起点, 上一帧起点 = base - iv): roll 发
 * [base..base+(cnt-1)iv] 后 base += iv; flipA 发 [base..base+(cnt-2)iv](丢头桶, 末点 =
 * 上一帧末点)后 base += iv / cnt -= 1; flipB 发 [base-iv..base-iv+cnt·iv](起点 = 上一帧
 * 起点不动, 末点 +1 格 —— 评审轮1 finding4: 旧形发 base 起点会把 flipB 变成「起点+1 格/
 * 末点+2 格」的滚动变形)后 cnt += 1(base 不动)。 */
async function stubTrafficScripted(page, n0, interval, windowLabel, script) {
  let base = Math.floor(Date.now() / 1000 / interval) * interval - (n0 - 1) * interval;
  let cnt = n0;
  let calls = 0;
  await page.route('**/api/traffic/qb/torrent/*', (route) => {
    const kind = script && script[calls] ? script[calls] : 'roll';
    calls++;
    const iv = interval;
    let pts;
    let t0;
    if (kind === 'flipA') {
      pts = cnt - 1;            // 丢头桶: 窗起点 +1 格, 末点不动
      t0 = base;
    } else if (kind === 'flipB') {
      pts = cnt + 1;            // 加尾桶: 窗起点不动(= 上一帧起点 = base - iv, base 已前移), 末点 +1 格
      t0 = base - iv;
    } else {
      pts = cnt;                // 正常滚动帧
      t0 = base;
    }
    const up = 1000;
    const dl = 2000;
    const points = new Array(pts).fill(null);
    const totals = new Array(pts).fill(null);
    for (let i = 0; i < pts; i++) {
      const t = t0 + i * iv;
      points[i] = { t, dl, up };
      totals[i] = { t, dl, up };
    }
    const payload = {
      points,
      totals,
      limits: [],
      meta: {
        window: windowLabel,
        interval_s: interval,
        sample_interval_s: interval,   // F7/D6: 轮询节奏读生效采样间隔, 桩对齐生产契约
        source: 'qb',
        stale: false,
        server_started_at: t0 - 3600,
      },
    };
    // 状态推进与发帧同序: roll/flipA 窗起点右移一格; flipB 只涨点数(起点不动)
    if (kind === 'flipB') {
      cnt += 1;
    } else {
      base += iv;
      if (kind === 'flipA') cnt -= 1;
    }
    return route.fulfill({ json: payload });
  });
}

/** 打开种子流量页签(不点窗口档: A 靠 interval_s=2 出快拍, B 靠 interval_s=30 隔离真拍) */
async function openTorrentTraffic(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  // 页签文本含 Alt+5 键帽(f081dd53 起), 定位用「流量 」前缀(traffic-gap-zones 同款)
  await drawer.locator('.drawer-tabs button', { hasText: /^流量 / }).click();
  await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
  return drawer;
}

/**
 * 把轮询周期重排到 interval_s 档(真实 UI 手势: 切走页签再切回流量)。
 * 为什么要这一步: drawer_store._loadDrawerTab('traffic') 的次序是 _qbLoad(异步)后立刻
 * _qbPollStart —— 起拍时 meta 还没落袋, _qbPollMs 读不到 interval_s 回落 30s fallback,
 * arm() 要等第一拍烧完才重读 ms()。切走页签再切回, _qbPollStart 自带先停后起且此刻数据
 * 已在, 新周期 = interval_s x 1000(A 档 2s) —— 拍在 2s 节奏上出, 用例不用陪等首轮 30s。
 */
async function rearmTrafficPoll(page, drawer) {
  // 页签文本含键帽徽标(f081dd53 起 Alt+1..5), 定位一律带尾随空格(traffic-gap-zones 同款)
  await drawer.locator('.drawer-tabs button', { hasText: /^常规 / }).click();
  await drawer.locator('.drawer-tabs button', { hasText: /^流量 / }).click();
  await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
  await expect.poll(() => readInst(page, 'vm._qbPollMs("torrent")'), {
    message: '轮询周期未重排到 interval_s 档(数据未落袋时的 fallback 30s 还在)', timeout: 15_000,
  }).toBeLessThanOrEqual(2100);
}

/** F8 首拍重试窗口垫(预览两案 B/B5 用, 评审轮1 minor): 判定帧只挂续拉快路(_qbBeatStart
 * 唯一调用点), 开门直拉走全量建图不起判定帧 —— fxBeatAt 的**首次写入恰 = F8 首拍重试拉数
 * (~1.5s)落地的真拍判定**(诊断实测: 直拉落袋 meta 已在而 fxBeatAt 恒 0, 重试拍判定才写)。
 * 再等 anim 归位(主区 ~0.6s + 次区 ~2s 全清)—— 下一真拍在 30s 档之外, 预览点击从此既不会
 * 被快路真值抢占(把预览采样窗截断在硬钉 >=3 帧之前, 间歇红面), 也不会撞上真拍主区在途
 * (§05.4 第 4 条: 主区在途预览被忽略不起拍 -> 预览永不收场)。页面侧状态判定, 零睡等。 */
async function waitForFirstRetryBeat(page) {
  await expect.poll(() => readInst(page, `(() => {
    const u = vm._qbCharts && vm._qbCharts.torrent;
    return (vm.fxBeatAt || 0) > 0 && !!u && !!u._qbBeat && !u._qbBeat.anim;
  })()`), {
    message: 'F8 首拍重试真拍未完全落地归位(fxBeatAt 未写或 anim 未清 —— 预览窗会被真值抢占'
      + '/主区在途忽略截断)', timeout: 15_000,
  }).toBe(true);
}

/** 图记录快照(xs 界值/尾值/x 尺) —— 预览前后各取一次, 断言「真值零改写 + 末帧还原」 */
const SNAP_EXPR = `(() => {
  const vm = ${INST};
  const u = vm._qbCharts && vm._qbCharts.torrent;
  if (!u || !u.data || !u.data.length) return null;
  const xs = u.data[0];
  const n = xs.length;
  let cks = 0;
  for (let i = 0; i < n; i++) cks += xs[i];
  return { xsLen: n, xs0: xs[0], xsN: xs[n - 1], xsCks: cks,
    tailUp: u.data[1] ? u.data[1][n - 1] : null, tailDl: u.data[2] ? u.data[2][n - 1] : null,
    min: u.scales.x.min, max: u.scales.x.max };
})()`;

async function readSnapshot(page) {
  const snap = await page.evaluate(SNAP_EXPR);
  if (!snap) throw new Error('图记录取不到(vm._qbCharts.torrent 未建图)');
  return snap;
}

/** 帧序列按「主区拍段」分组: 连续 impact 相位帧为一段(F1 后滚窗拍之间常驻次区相位 tail,
 * anim 全程为真 —— 拍段只能按相位切, 见文件头 S3a 复核注)。A/A1/A3 复用。 */
function beatRuns(frames) {
  const runs = [];
  let cur = null;
  for (const f of frames) {
    if (f.anim && f.phase !== 'tail') {
      if (!cur) { cur = []; runs.push(cur); }
      cur.push(f);
    } else {
      cur = null;
    }
  }
  return runs;
}

/** 语义色现值(--today-up/--today-down)的 computed rgb(traffic-fx-anchor 同款, A5 用) */
async function readTokenColors(page) {
  return page.evaluate(`(() => {
    const probe = document.createElement('span');
    probe.style.display = 'none';
    document.body.appendChild(probe);
    const read = (name) => {
      probe.style.color = 'var(' + name + ')';
      return getComputedStyle(probe).color;
    };
    const out = { up: read('--today-up'), down: read('--today-down') };
    probe.remove();
    return out;
  })()`);
}

/* ============================================================================ */

test.describe('节拍动效 · 左移连续性(G2/R1 帧级探针)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 相邻两拍边界视口位移 <= 1px, 拍内平滑滑入一格, 真值落地 <= animEnd+余量 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTrafficAdvancing(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      await rearmTrafficPoll(page, drawer);

      /* 页面侧 rAF 采样器: 记录每帧的 x 尺/数据界值/拍状态(含相位 —— F1 后拍间被次区相位
       * tail 填满, 拍段按 impact 相位切, 见文件头 S3a 复核注); 第 3 个主区拍段出现且离开
       * impact 相位即停(三个拍段 = 三条边界, 每条边界都有前值可对照)。零固定睡等。 */
      await page.evaluate(`(() => {
        const vm = ${INST};
        window.__fs = { frames: [], starts: 0, prevAnim: false, done: false };
        const tick = () => {
          const fs = window.__fs;
          if (fs.done) return;
          const u = vm._qbCharts && vm._qbCharts.torrent;
          if (u && u._qbBeat && u.data && u.data.length) {
            const a = u._qbBeat.anim;
            const xs = u.data[0];
            const n = xs.length;
            fs.frames.push({
              t: performance.now(),
              anim: !!a,
              phase: a ? a.phase : null,
              dx0: a ? a.dx0 : null,
              animEnd: a && a.tl ? a.tl.animEndMs : null,
              min: u.scales.x.min,
              max: u.scales.x.max,
              w: u.bbox.width,
              dpr: (typeof uPlot !== 'undefined' && uPlot.pxRatio) || 1,
              xsLen: n, xs0: xs[0], xsN: xs[n - 1],
              tailUp: u.data[1] ? u.data[1][n - 1] : null,
              tailDl: u.data[2] ? u.data[2][n - 1] : null,
            });
            const inImpact = !!(a && a.phase !== 'tail');
            if (inImpact && !fs.prevAnim) fs.starts++;
            fs.prevAnim = inImpact;
            if (fs.starts >= 3 && !inImpact) fs.done = true;
          }
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      })()`);
      await expect.poll(() => readInst(page, 'window.__fs === undefined ? false : window.__fs.done === true'), {
        message: '三个拍段未在预算内采满(轮询 2s 一拍, 三拍约 7s; 超时=轮询/节拍链路断了)',
        timeout: 30_000,
      }).toBe(true);
      const frames = await page.evaluate(() => window.__fs.frames);

      /* 拍段 = 连续 impact 相位帧(F1 后主区拍之间常驻次区相位(tail 光点窗), anim 全程为真
       * —— 拍段只能按相位切; 见文件头 S3a 复核注); 段数 >= 3 */
      const runs = beatRuns(frames);
      expect(runs.length, '采样窗内应记录到 >= 3 个拍段(轮询推进的窗口滚动拍)').toBeGreaterThanOrEqual(3);

      for (let i = 0; i < runs.length; i++) {
        const run = runs[i];
        const idx0 = frames.indexOf(run[0]);
        expect(idx0, '拍段前必须有前帧(边界对照值)').toBeGreaterThanOrEqual(1);
        const prev = frames[idx0 - 1];

        /* 边界连续性(G2 本体): 新拍判定帧把视口摆回旧位, 与上一拍收敛位置差 <= 1px。
         * px 换算: plotCssWidth = bbox.width / pxRatio(bbox 是设备像素); 用边界帧自己的
         * 尺度换算(拍前后窗宽同格数, 尺度不跳)。 */
        const pxPerUnit = (run[0].w / run[0].dpr) / (run[0].max - run[0].min);
        const dpx = Math.abs(run[0].min - prev.min) * pxPerUnit;
        expect(dpx, `第 ${i + 1} 拍边界视口位移 ${dpx.toFixed(3)}px 必须 <= 1px(相邻两拍边界曲线不回跳不跳格)` +
          ` [prev.min=${prev.min} -> first.min=${run[0].min}]`).toBeLessThanOrEqual(1);

        /* 拍内平滑(G2 三档口径的 smooth 档): 视口滑过约一格宽, 且逐帧单调不回跳 */
        const cellPx = (run[0].w / run[0].dpr) / run[0].xsLen;
        const glidePx = (run[run.length - 1].min - run[0].min) * pxPerUnit;
        expect(glidePx, `第 ${i + 1} 拍视口行程 ${glidePx.toFixed(2)}px 应约一格(>= ${ (cellPx * 0.5).toFixed(2) }px) —— ` +
          'instant 化(不播 L0)即红').toBeGreaterThanOrEqual(cellPx * 0.5);
        expect(run.length, `第 ${i + 1} 拍应有 >= 3 个采样帧(动画经多帧推进, 非一次跳变)`).toBeGreaterThanOrEqual(3);
        for (let j = 1; j < run.length; j++) {
          expect(run[j].min, `第 ${i + 1} 拍第 ${j} 帧视口单调(不回跳)`).toBeGreaterThanOrEqual(run[j - 1].min - 1e-6);
        }
        expect(run[0].dx0, `第 ${i + 1} 拍 dx0 必须为正(窗口滚动一格驱动)`).toBeGreaterThan(0);

        /* G1 真值落地时限: 拍墙钟 <= animEnd + 900ms(容器软件渲染 rAF 帧距大, dt 钳 100ms
         * 的吞帧机制会拉长墙钟 —— 余量按掉帧形态给, 收紧到 animEnd 是电池面的事) */
        const dur = run[run.length - 1].t - run[0].t;
        expect(dur, `第 ${i + 1} 拍墙钟 ${Math.round(dur)}ms 必须 <= animEnd(${run[0].animEnd}ms)+900ms`).toBeLessThanOrEqual(run[0].animEnd + 900);

        /* 拍内数据冻结: 窗口列与尾值一帧不动(L0 只改视口) */
        for (const f of run) {
          expect(f.xs0, '拍内 xs[0] 冻结(L0 不动 data)').toBe(run[0].xs0);
          expect(f.xsN, '拍内 xs 末值冻结').toBe(run[0].xsN);
        }
      }

      /* 全窗数据不变量(F5 口径): 显示列点数 = 真窗口点数或 +1(判定帧补尾格拍), 拍间 xs[0]
       * 逐拍右移; 尾值恒定(L1 静默: 恒定数据零收敛)。 */
      const f0 = frames[0];
      for (const f of frames) {
        expect(f.xsLen === N || f.xsLen === N + 1, `点数 ${f.xsLen} 必须 = 真窗口 ${N} 或补尾格拍 ${N + 1}`
          + '(旧重定标/方波即红)').toBe(true);
        expect(f.tailUp, '上传尾值恒定(恒定数据零装饰零收敛)').toBe(f0.tailUp);
        expect(f.tailDl, '下载尾值恒定').toBe(f0.tailDl);
      }
      for (let i = 1; i < runs.length; i++) {
        expect(runs[i][0].xs0, '相邻两拍 xs[0] 必须右移(窗口每拍滚动一格)').toBeGreaterThan(runs[i - 1][0].xs0);
      }

      /* A2 左端连续性(G-B「摆回固有左缺口瞬移」的 e2e 判别面, F5): 全帧曲线左端像素位
       * (xs0 - min) x pxPerUnit 必须 <= 1px —— 补尾格后判定帧的曲线左端贴住摆回视图左缘
       * (=0px), 滑动期间被左缘裁剪(负值 = 数据起点已滑出视图左缘); 旧形态(无补点)判定帧
       * 左端跳进一格 = 一格宽的正位(本桩 ~13px), 即红。 */
      for (let i = 0; i < frames.length; i++) {
        const f = frames[i];
        const pxPerUnit = (f.w / f.dpr) / (f.max - f.min);
        const leftEndPx = (f.xs0 - f.min) * pxPerUnit;
        expect(leftEndPx, `第 ${i} 帧曲线左端像素位 ${leftEndPx.toFixed(2)}px 必须 <= 1px(左端贴住`
          + `左缘或已滑出, 格宽 ${((f.w / f.dpr) / f.xsLen).toFixed(2)}px —— 判定帧左端跳进一格即红)`)
          .toBeLessThanOrEqual(1);
      }
    });
  }
});

test.describe('节拍动效 · 预览拍帧级探针(§05.9 面板拍 + G5 背景静态)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 预览期间 xs/x 尺逐帧不变 + dx=0; 背景两点 alpha 恒 0 且相等; 末帧还原真值 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTrafficStill(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      await waitForFirstRetryBeat(page);   // 评审轮1 minor: F8 首拍重试真拍落地后才开预览(抢占截断间歇红)

      /* 开面板 -> 高级折叠 -> 把竖扫回声行程钉到 100px(真手势改字段; 回声 span 100 让
       * 探针点 R-130 站在装饰行程之外) */
      await drawer.locator('.qb-chart-host').click({ button: 'right' });
      const panel = page.locator('.fx-panel');
      await expect(panel).toBeVisible({ timeout: 5_000 });
      await panel.locator('.fx-adv summary').click();
      await panel.locator('.fx-row', { hasText: '竖扫回声行程' }).locator('select').selectOption('100');
      await expect.poll(() => readInst(page, 'window.AQB_FX_CFG && window.AQB_FX_CFG.echoSpan'), {
        message: 'echoSpan=100 未贯通 CFG(预览探针的装饰范围前提)', timeout: 5_000,
      }).toBe('100');

      /* 探针点扫描(D4 第 2 类: vm 内部几何探针): 两列各找一段 >= 8px 的透明带取中点。
       * 列 1 = 绘图区中央; 列 2 = 右缘带 R-130(环 <=29px/粒子 <=47px/尾光 6 格/回声 100px
       * 的行程之外)。扫描天然避开曲线/网格的静态像素; 预览期间轴冻结, 几何不漂移。 */
      const probe = await page.evaluate(`(() => {
        const vm = ${INST};
        const u = vm._qbCharts && vm._qbCharts.torrent;
        if (!u || !u.ctx || !u.bbox) return { error: 'unbuilt' };
        const px = (typeof uPlot !== 'undefined' && uPlot.pxRatio) || 1;
        const L = u.bbox.left / px;
        const T = u.bbox.top / px;
        const W = u.bbox.width / px;
        const H = u.bbox.height / px;
        const R = L + W;
        const devH = u.ctx.canvas.height;
        const pick = (x, tag) => {
          const col = u.ctx.getImageData(Math.round(x * px), 0, 1, devH).data;
          const lo = Math.round((T + 24) * px);
          const hi = Math.round((T + H - 24) * px);
          let best = null;
          let run = 0;
          let runStart = -1;
          for (let dy = lo; dy <= hi; dy++) {
            if (col[dy * 4 + 3] === 0) {
              if (run === 0) runStart = dy;
              run++;
              if (!best || run > best.run) best = { run, start: runStart };
            } else {
              run = 0;
            }
          }
          if (!best || best.run < 8) return tag + ' 列找不到 >= 8px 透明带(扫描区被占满?)';
          return { x, y: (best.start + Math.floor(best.run / 2)) / px };
        };
        const p1 = pick(L + W * 0.45, 'center');
        if (typeof p1 === 'string') return { error: p1 };
        const p2 = pick(R - 130, 'right');
        if (typeof p2 === 'string') return { error: p2 };
        return { p1, p2, R };
      })()`);
      if (!probe || probe.error) {
        throw new Error('探针点扫描失败: ' + ((probe && probe.error) || 'evaluate 返回空'));
      }

      /* 装扫描器前取真值快照(预览前), 装完后点「预览一拍」 */
      const snap = await readSnapshot(page);
      await page.evaluate(`((p1, p2) => {
        const vm = ${INST};
        const u = vm._qbCharts.torrent;
        const px = (typeof uPlot !== 'undefined' && uPlot.pxRatio) || 1;
        const cks0 = () => {
          let s = 0;
          const xs = u.data[0];
          for (let i = 0; i < xs.length; i++) s += xs[i];
          return s;
        };
        window.__pf = { frames: [], done: false, sawAnim: false,
          snap: { min: u.scales.x.min, max: u.scales.x.max, xsCks: cks0() }, p1, p2, dpr: px };
        const tick = () => {
          const pf = window.__pf;
          if (pf.done) return;
          const u2 = vm._qbCharts && vm._qbCharts.torrent;
          if (u2 && u2.ctx && u2.data && u2.data.length) {
            const a = u2._qbBeat && u2._qbBeat.anim;
            let cks = 0;
            const xs = u2.data[0];
            for (let i = 0; i < xs.length; i++) cks += xs[i];
            const g1 = u2.ctx.getImageData(Math.round(pf.p1.x * pf.dpr), Math.round(pf.p1.y * pf.dpr), 1, 1).data;
            const g2 = u2.ctx.getImageData(Math.round(pf.p2.x * pf.dpr), Math.round(pf.p2.y * pf.dpr), 1, 1).data;
            const fx = a && a.fx ? a.fx : null;
            const parts = fx
              ? (fx.specs.up ? fx.specs.up.length : 0) + (fx.specs.dl ? fx.specs.dl.length : 0)
                + (fx.specs.merge ? fx.specs.merge.length : 0)
              : 0;
            pf.frames.push({
              anim: !!a,
              isPreview: !!(a && a.preview !== undefined),
              dx0: a ? a.dx0 : null,
              min: u2.scales.x.min,
              max: u2.scales.x.max,
              xsCks: cks,
              parts,
              g1: [g1[0], g1[1], g1[2], g1[3]],
              g2: [g2[0], g2[1], g2[2], g2[3]],
            });
            if (a && a.preview !== undefined) pf.sawAnim = true;
            if (pf.sawAnim && !a) pf.done = true;
          }
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      })(${JSON.stringify(probe.p1)}, ${JSON.stringify(probe.p2)})`);

      await panel.locator('button', { hasText: '预览一拍' }).click();
      await expect.poll(() => readInst(page, 'window.__pf === undefined ? false : window.__pf.done === true'), {
        message: '预览拍未在预算内收场(预览无 tail 相位, 窗 = animEnd 600ms 档; 超时=预览链路断了或假 Δ 零变化)',
        timeout: 15_000,
      }).toBe(true);
      const frames = await page.evaluate(() => window.__pf.frames);

      /* 帧数与预览在场(S4-b 评审 major2 重标): 预览拍**没有 tail 相位** —— _qbBeatFrame 在
       * clock >= tl.animEndMs 时对 preview 直走 _qbPreviewEnd 收口(tail 相位只属于真拍
       * _qbBeatConverge), 采样窗 = animEnd = max(shiftRatio,0.6) x beat = 600ms 档。
       * 下限按两侧实测帧距落数(2026-11-14 诊断跑实测: testbed anim 帧 38 / Windows 37-38,
       * 600ms 窗两侧都 ≈16ms/帧全速 —— 本量具是轻 canvas, 不是 41.7m/344 例那种重渲染面;
       * 容器慢是重负载 spec 的形态差异): anim 帧 >= 3 证明「预览真的跑了且被逐帧采样」,
       * 全帧 >= 3 再证采样器跨过了「动画在场 -> 归位」边界(done 条件的结构性结果);
       * 下限 3 只吃「预览在途 rAF 完全饿死」的病理形态, 常规负载余量一个量级。
       * 逐帧不变性断言(min/max/xsCks/背景两点)与帧数无关 —— 帧距变大只降低采样密度。 */
      expect(frames.length, '采样窗应有 >= 3 帧(采样器须跨过预览收场边界)').toBeGreaterThanOrEqual(3);
      /* F8/F6 后本桩(静态正值)开场 ~1.5s 处有一次首拍重试拉数 -> 真零变化拍(anim 在场但非
       * 预览)。预览语义断言只吃**预览帧**(isPreview 令牌过滤); 全帧不变量(min/max/xsCks/
       * 背景两点)仍吃全窗 —— 零变化拍零视口/数据提交, 装饰行程不达探针点, 两类帧同窗成立。 */
      const previewFrames = frames.filter((f) => f.isPreview);
      expect(previewFrames.length, '预览动画必须有采样帧(预览一拍真的跑了; 600ms 窗在慢机约 3-4 帧)')
        .toBeGreaterThanOrEqual(3);

      /* 全帧不变量: xs 列与 x 尺逐帧不变(§05.9: 预览不动数据面; 零变化真拍同不改写) */
      for (const f of frames) {
        expect(f.min, 'u.scales.x.min 逐帧不变(预览/零变化拍零 setScale x)').toBe(snap.min);
        expect(f.max, 'u.scales.x.max 逐帧不变').toBe(snap.max);
        expect(f.xsCks, 'u.data[0] 逐帧不变(窗口列零变化)').toBe(snap.xsCks);
      }
      /* 预览帧语义: preview 令牌在场 + dx ≡ 0 + 粒子预算 */
      for (const f of previewFrames) {
        expect(f.dx0, '预览 dx ≡ 0(不动窗口)').toBe(0);
        expect(f.parts, '粒子 spawn 清单合计必须 <= 32(I9 两轨合计)').toBeLessThanOrEqual(32);
      }
      expect(previewFrames[0].parts, '预览假 Δ(Lv.2+)必须有装饰清单在场(零装饰=探针空转)').toBeGreaterThanOrEqual(2);

      /* G5 背景两点: 整窗每帧 alpha 恒 0(任何铺底/呼吸即红)且两点相等(均未落墨) */
      for (const f of frames) {
        expect(f.g1[3], '背景点 1(绘图区中央)alpha 恒 0').toBe(0);
        expect(f.g2[3], '背景点 2(右缘带, 装饰行程之外)alpha 恒 0').toBe(0);
        expect(f.g1, '两点像素相等(均未落墨 —— 「背景 RGB 恒定且两点相等」的画布采样面)').toEqual(f.g2);
      }

      /* 末帧还原真值(假值不留痕): 预览收场后 xs/尾值/x 尺与预览前快照逐值相等 */
      const endSnap = await readSnapshot(page);
      expect(endSnap.tailUp, '预览末帧必须还原上传真值').toBe(snap.tailUp);
      expect(endSnap.tailDl, '预览末帧必须还原下载真值').toBe(snap.tailDl);
      expect(endSnap.min).toBe(snap.min);
      expect(endSnap.max).toBe(snap.max);
      expect(endSnap.xsCks).toBe(snap.xsCks);
    });
  }
});

test.describe('节拍动效 · 裁剪面机制探针(F5/A6, plan 26-11-14-1313; B5 渲染对齐记账)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 预览拍 fx/锚段 clip 实参 = 右缘放宽到画布右缘且下缘不放宽; 预览逐帧出装饰 @fast`, async ({ page }) => {
      /* B5 改版说明(量具面对齐本环境): 原版在 rAF 渲染间读右缘带像素 —— 本环境(Windows
       * 无 testbed, headless 软件光栅)实测渲染管线落定后的画布读不到装饰墨(B5 取证: 装饰
       * 墨只在渲染管线内可观测, rAF 渲染间读数恒 0 假阴性; 真滚窗拍/预览两条路径同样),
       * 像素探针在此不可落地。改为**渲染对齐记账**: 包住图的 drawAxes 钩子 + ctx.rect 记
       * 账(运行时包装, 只读不改生产逻辑 —— 与 vm 内部时序探针同类), 直接钉 F5 改的那一
       * 件事本身: fx 段 clip 实参 = rect(L, T, max(W, canvasW-L), H) —— 右缘放宽到画布右
       * 缘(width >= W 且右沿 = 画布右缘)、下缘不放宽(height = H)。与电池 G0 的 clip 实
       * 参记账同契约, 在真浏览器真渲染路径上复核。预览的假 Δ 让每帧都有提交重绘, 记账
       * 逐渲染可读; 近底环心钳制(P3)与粒子镜像由电池 G11/G12 钉。 */
      await stubFlags(page);
      await stubTrafficBottom(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      await waitForFirstRetryBeat(page);   // 同 B: F8 首拍重试真拍落地后才开预览(记账窗被抢占截断)

      await drawer.locator('.qb-chart-host').click({ button: 'right' });
      const panel = page.locator('.fx-panel');
      await expect(panel).toBeVisible({ timeout: 5_000 });

      /* 渲染对齐记账器: 包 drawAxes 钩子, 记录每次渲染的 fx 段 clip 实参(_qbDrawFx/_qbDrawFxAnchor
       * 各一次 rect)与 anim 态; bbox 每帧现读。 */
      await page.evaluate(`(() => {
        const vm = ${INST};
        const u = vm._qbCharts && vm._qbCharts.torrent;
        if (!u || !u.ctx || !u.bbox) throw new Error('unbuilt');
        window.__cp = { frames: [], sawPreview: false, done: false };
        const orig = u.hooks.drawAxes[0];
        const kc = u.ctx;
        const oRect = kc.rect.bind(kc);
        kc.rect = function (x, y, w, h) {
          const st = u._qbBeat;
          if (st && st.anim && st.anim.fx && window.__cp.rects) {
            window.__cp.rects.push([x, y, w, h]);
          }
          return oRect(x, y, w, h);
        };
        u.hooks.drawAxes[0] = function (uu) {
          window.__cp.rects = [];
          const r = orig.apply(this, arguments);
          try {
            const cp = window.__cp;
            if (cp.done) return r;
            const a = uu._qbBeat && uu._qbBeat.anim;
            const isPreview = !!(a && a.preview !== undefined);
            const px = (typeof uPlot !== 'undefined' && uPlot.pxRatio) || 1;
            cp.frames.push({
              isPreview,
              hasFx: !!(a && a.fx),
              lv: a && a.fx ? a.fx.lv : 0,
              clip: cp.rects.slice(),
              L: uu.bbox.left / px, T: uu.bbox.top / px,
              W: uu.bbox.width / px, H: uu.bbox.height / px,
              cw: uu.ctx.canvas.width / px,
            });
            if (isPreview) cp.sawPreview = true;
            if (cp.sawPreview && !a) cp.done = true;
          } catch (e) { /* 记账异常不干扰渲染 */ }
          return r;
        };
      })()`);
      if (await page.evaluate(() => !window.__cp)) {
        throw new Error('记账器未装上(画布/几何取不到)');
      }

      await panel.locator('button', { hasText: '预览一拍' }).click();
      await expect.poll(() => readInst(page, 'window.__cp === undefined ? false : window.__cp.done === true'), {
        message: '预览拍未在预算内收场(裁剪记账采样窗; 超时=预览链路断了或假 Δ 零变化)',
        timeout: 15_000,
      }).toBe(true);
      const frames = await page.evaluate(() => window.__cp.frames);
      const previewFrames = frames.filter((f) => f.isPreview && f.hasFx);
      expect(previewFrames.length, '预览渲染必须有带 fx 的采样帧(F5 记账要逐渲染核对 clip 实参)')
        .toBeGreaterThanOrEqual(3);

      /* F5 机制钉: 每个 fx 渲染的 clip 实参 = rect(L, T, max(W, canvasW-L), H):
       *   · width = max(W, canvasW-L) 且右沿 = 画布右缘 —— 右缘放宽在位(F5 回潮 = width 恰
       *     W / 右沿 = 绘图区右缘, 即红);
       *   · height = H(下缘不放宽 —— 轴标区零墨的机制面);
       *   · x/y = 绘图区左上(不外溢到 y 轴/顶栏)。 */
      /* 冲击窗(<=0.55xbeat)内的渲染才落 clip(环/粒子/切片的绘制段); 0.55xbeat 后冲击类
       * 零绘制是 I9 口径(fx 在场而零 rect 属正常帧, 不入断言域) */
      const clipped = previewFrames.filter((f) => f.clip.length > 0);
      expect(clipped.length, '冲击窗内的预览渲染必须 >= 3 帧(装饰路径真的在画)').toBeGreaterThanOrEqual(3);
      for (let i = 0; i < clipped.length; i++) {
        const f = clipped[i];
        for (const [x, y, w, h] of f.clip) {
          expect(Math.abs(x - f.L), `第 ${i} 渲染 clip 左沿 ${x} 必须 = 绘图区左沿 ${f.L}`).toBeLessThanOrEqual(1);
          expect(Math.abs(y - f.T), `第 ${i} 渲染 clip 上沿 ${y} 必须 = 绘图区上沿 ${f.T}`).toBeLessThanOrEqual(1);
          expect(w, `第 ${i} 渲染 clip 宽 ${w} 必须 = max(W=${f.W}, canvasW-L=${f.cw - f.L})`
            + '(F5 右缘放宽到画布右缘)').toBeGreaterThanOrEqual(f.W - 1);
          expect(Math.abs(w - Math.max(f.W, f.cw - f.L)), `第 ${i} 渲染 clip 宽 ${w} 必须恰 = `
            + `max(W, canvasW-L) = ${Math.max(f.W, f.cw - f.L)}`).toBeLessThanOrEqual(1);
          expect(Math.abs(x + w - f.cw), `第 ${i} 渲染 clip 右沿 ${x + w} 必须 = 画布右缘 ${f.cw}`
            + '(右缘留白是装饰可见域 —— F5)').toBeLessThanOrEqual(1);
          expect(Math.abs(h - f.H), `第 ${i} 渲染 clip 高 ${h} 必须 = 绘图区高 ${f.H}`
            + '(下缘未放宽 —— 轴标区零墨机制面)').toBeLessThanOrEqual(1);
        }
      }
    });
  }
});

test.describe('节拍动效 · A1 稳态流每拍 Lv.1 反馈(F1 等级门的调度器观测面, plan 26-11-14-1313)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 恒定正值稳态流: 每个滚窗拍 anim.fx 恒在场(lv>=1), 真值零改写 @fast`, async ({ page }) => {
      /* A1 量法口径(计划 §01: 「拍窗内右缘装饰带像素量显著高于拍间基线」)在本环境的落点
       * 说明: 真滚窗拍的渲染管线落定后, 画布在渲染间读不到装饰墨(B5 取证 —— headless
       * 软件光栅), 像素强度面不可落地; 现落点 = 本用例的调度器在场断言(稳态流(delta≈0
       * 且值>0)下每个滚窗拍 anim.fx 恒在场且 lv>=1 —— S7b 电池口径的真机面, 等级门回潮
       * 即 fx 整段缺席)+ 电池 spawn/clip 面(F1e2/S7b/G0), 与计划量法「像素量 >> 基线」
       * 的偏差记 S3b 回写。另钉尾点零改写(装饰不触碰真值面)。 */
      await stubFlags(page);
      await stubTrafficAdvancing(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      await rearmTrafficPoll(page, drawer);

      /* 页面侧 rAF 采样器(A 同款拍段计数): 每帧记 anim 相位/fx 在场与等级/尾值。
       * 恒定值下 L1 零提交(needsTail=false), 拍 = L0 位移 + Lv.1 装饰 spawn(S7b 口径)。 */
      await page.evaluate(`(() => {
        const vm = ${INST};
        const u = vm._qbCharts && vm._qbCharts.torrent;
        if (!u || !u.ctx || !u.bbox) throw new Error('unbuilt');
        const px = (typeof uPlot !== 'undefined' && uPlot.pxRatio) || 1;
        window.__a1 = { frames: [], starts: 0, prevImpact: false, done: false };
        const tick = () => {
          const s1 = window.__a1;
          if (s1.done) return;
          const u2 = vm._qbCharts && vm._qbCharts.torrent;
          if (u2 && u2.ctx && u2.data && u2.data.length) {
            const a = u2._qbBeat && u2._qbBeat.anim;
            const xs = u2.data[0];
            const n = xs.length;
            s1.frames.push({
              anim: !!a,
              phase: a ? a.phase : null,
              fxLv: a && a.fx ? a.fx.lv : 0,
              tailUp: u2.data[1] ? u2.data[1][n - 1] : null,
              tailDl: u2.data[2] ? u2.data[2][n - 1] : null,
            });
            const inImpact = !!(a && a.phase !== 'tail');
            if (inImpact && !s1.prevImpact) s1.starts++;
            s1.prevImpact = inImpact;
            if (s1.starts >= 3 && !inImpact) s1.done = true;
          }
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      })()`);
      await expect.poll(() => readInst(page, 'window.__a1 === undefined ? false : window.__a1.done === true'), {
        message: '三个拍段未在预算内采满(轮询 2s 一拍, 三拍约 7s; 超时=轮询/节拍链路断了)',
        timeout: 30_000,
      }).toBe(true);
      const frames = await page.evaluate(() => window.__a1.frames);
      const runs = beatRuns(frames);
      expect(runs.length, '采样窗内应记录到 >= 3 个拍段(滚窗拍)').toBeGreaterThanOrEqual(3);

      /* A1 本体(调度器面): 每个滚窗拍至少一帧 anim.fx 在场且 lv>=1 —— 稳态流(delta≈0 且
       * 值>0)每拍出 Lv.1 反馈(F1 下限); 等级门回潮(恒 Lv.0 -> spawn null)即整段缺席。 */
      for (let i = 0; i < runs.length; i++) {
        const lvMax = Math.max(...runs[i].map((f) => f.fxLv));
        expect(lvMax, `第 ${i + 1} 拍 anim.fx 最大等级 ${lvMax} 必须 >= 1(A1: 稳态流每拍出 Lv.1`
          + '反馈 —— F1 等级门回潮整段静默即缺席)').toBeGreaterThanOrEqual(1);
      }

      /* 真值面零污染(I4): 恒定数据零收敛, 尾值逐帧恒真值(装饰/插值不写尾桶) */
      const f0 = frames[0];
      for (const f of frames) {
        expect(f.tailUp, '上传尾值逐帧恒定(装饰不触碰真值面)').toBe(f0.tailUp);
        expect(f.tailDl, '下载尾值逐帧恒定').toBe(f0.tailDl);
      }
      expect(f0.tailUp, '稳态流尾值应为正值(值>0 前提)').toBeGreaterThan(0);
    });
  }
});

test.describe('节拍动效 · A3 零流量(F1 真 0 静默 + 环境层不静默, plan 26-11-14-1313)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 值恒 0 滚窗: L0 平滑左移照常 + anim.fx 恒 null(扫描/粒子静默)+ 菱形旋转仍在 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTrafficAdvancingZero(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      await rearmTrafficPoll(page, drawer);

      /* 页面侧 rAF 采样器(A/锚 spec 量具合体, 全部只读): 每帧记 anim 相位/dx0/fx 在场/
       * x 尺/菱形 transform。零流量滚窗拍: L0 照常起拍(窗口每拍推进一格), 但
       * 真 0 轨 level 0 -> _qbFxLead null -> spawn null -> 零装饰(§05.6/D2 口径, S4-a 电池
       * 「双轨真 0 零装饰」的真机面); DOM 常驻菱形是 CSS 合成器动画, 不吃 canvas 装饰门
       * —— 旋转照走(A3: 环境层不静默, B4 电池真 0 轨仍显形的 e2e 面)。 */
      await page.evaluate(`(() => {
        const vm = ${INST};
        const u = vm._qbCharts && vm._qbCharts.torrent;
        if (!u || !u.ctx || !u.bbox) throw new Error('unbuilt');
        window.__z3 = { frames: [], mats: new Set(), starts: 0, prevAnim: false, done: false };
        const tick = () => {
          const s = window.__z3;
          if (s.done) return;
          const u2 = vm._qbCharts && vm._qbCharts.torrent;
          if (u2 && u2.ctx && u2.data && u2.data.length) {
            const a = u2._qbBeat && u2._qbBeat.anim;
            const xs = u2.data[0];
            const el = u2._qbFxAnchors && u2._qbFxAnchors.up;
            if (el && el.isConnected) s.mats.add(getComputedStyle(el).transform);
            s.frames.push({
              anim: !!a,
              phase: a ? a.phase : null,
              fx: !!(a && a.fx),
              dx0: a ? a.dx0 : null,
              min: u2.scales.x.min,
              max: u2.scales.x.max,
              w: u2.bbox.width,
              dpr: (typeof uPlot !== 'undefined' && uPlot.pxRatio) || 1,
              xsLen: xs.length,
            });
            if (a && !s.prevAnim) s.starts++;
            s.prevAnim = !!a;
            if (s.starts >= 2 && !a) s.done = true;
          }
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      })()`);
      await expect.poll(() => readInst(page, 'window.__z3 === undefined ? false : window.__z3.done === true'), {
        message: '两个零流量拍段未在预算内采满(轮询 2s 一拍; 超时=轮询/节拍链路断了)',
        timeout: 30_000,
      }).toBe(true);
      const frames = await page.evaluate(() => window.__z3.frames);
      const runs = beatRuns(frames);
      expect(runs.length, '采样窗内应记录到 >= 2 个拍段(零流量滚窗拍照常起)').toBeGreaterThanOrEqual(2);

      /* A3 本体 1: L0 平滑左移照常 —— 每拍 dx0 > 0 且视口平滑滑入一格、逐帧单调不回跳
       * (A 用例同款判据的轻量版: 零流量不改数据刷新语义) */
      for (let i = 0; i < runs.length; i++) {
        const run = runs[i];
        const idx0 = frames.indexOf(run[0]);
        expect(idx0, '拍段前必须有前帧(边界对照值)').toBeGreaterThanOrEqual(1);
        const pxPerUnit = (run[0].w / run[0].dpr) / (run[0].max - run[0].min);
        const cellPx = (run[0].w / run[0].dpr) / run[0].xsLen;
        const glidePx = (run[run.length - 1].min - run[0].min) * pxPerUnit;
        expect(run[0].dx0, `第 ${i + 1} 拍 dx0 必须为正(零流量也滚窗)`).toBeGreaterThan(0);
        expect(glidePx, `第 ${i + 1} 拍视口行程 ${glidePx.toFixed(2)}px 应约一格(>= ${(cellPx * 0.5).toFixed(2)}px)`
          + ' —— 零流量下 L0 instant 化即红').toBeGreaterThanOrEqual(cellPx * 0.5);
        expect(run.length, `第 ${i + 1} 拍应有 >= 3 个采样帧(平滑过渡经多帧推进)`).toBeGreaterThanOrEqual(3);
        for (let j = 1; j < run.length; j++) {
          expect(run[j].min, `第 ${i + 1} 拍第 ${j} 帧视口单调(不回跳)`).toBeGreaterThanOrEqual(run[j - 1].min - 1e-6);
        }
      }

      /* A3 本体 2: 扫描/粒子静默(F1 真 0 面) —— 每个滚窗拍 anim.fx 恒 null(真 0 -> level 0
       * -> _qbFxLead null -> spawn null; 与 A1 的「值>0 恒在场」成对) */
      for (const f of runs.flat()) {
        expect(f.fx, '零流量滚窗拍 anim.fx 必须恒 null(真 0 静默 —— 装饰回潮即红)').toBe(false);
      }

      /* (B5 评审: 原本体 3「右缘带墨量恒 0」像素断言删除 —— 同量具按本批取证在渲染间
       * 恒读 0, 属死断言; 真 0 静默的真正语义由本体 2 的 anim.fx 恒 null 承载, 像素局限
       * 记 S3b 回写。) */

      /* A3 本体 4: 菱形旋转仍在(环境层不静默) —— 采样窗内 transform >= 2 个不同值
       * (锚 spec 同款判据; DOM 层不吃真 0 静默门) */
      const matCount = await page.evaluate(() => window.__z3.mats.size);
      expect(matCount, `采样窗内菱形 transform 应 >= 2 个不同值(实测 ${matCount}) —— `
        + '零流量下常驻菱形停转即红(A3: 菱形旋转仍在)').toBeGreaterThanOrEqual(2);
    });
  }
});

test.describe('节拍动效 · A5 曲线终点落判定线/真缺口诚实断线(F4 活尾延伸的 e2e 显示面, plan 26-11-14-1313)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 活跃态(尾桶有观测): 两轨曲线墨达判定线 x≈R; 停滞态(尾 6 桶无观测): 判定线右侧零曲线墨且断点恰在链末桶 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTrafficStill(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);

      /* 数据落袋(尾桶有观测)且图静止(恒定数据零变化拍零 rAF —— S12 电池口径, 静图探针前提)。
       * 活跃态 payload = 全 60 桶有观测, 与 F4 活尾延伸后的生产形态同构(尾桶恒有观测);
       * B2 电池已钉后端延伸/停滞不延伸两态, 本用例补前端显示面。 */
      await expect.poll(() => readInst(page,
        'vm._qbCharts && vm._qbCharts.torrent && vm._qbCharts.torrent.data && vm._qbCharts.torrent.data[1]'
        + ' ? vm._qbCharts.torrent.data[1][59] : null'), {
        message: '活跃态数据未落袋(尾桶读不到)', timeout: 15_000,
      }).toBe(1000);

      const tokens = await readTokenColors(page);

      /* 曲线墨探针: 逐列右->左扫语义色墨(x ∈ [L, R], y ∈ [T, T+H]), 记最右含墨列。判据只用
       * 「最右墨柱位置」, 不预设尺度亚像素; 只认曲线描边色(--today-up/down 实测 rgb, 容差
       * 40 全通道合计) —— 静图上语义色墨 = 曲线本体, 网格/轴标灰阶不计数, 零装饰在场。 */
      const scan = async () => page.evaluate(`((rawCols) => {
        const parse = (s) => s.match(/\\d+/g).slice(0, 3).map(Number);
        const cols = { up: parse(rawCols.up), dl: parse(rawCols.down) };
        const vm = ${INST};
        const u = vm._qbCharts && vm._qbCharts.torrent;
        if (!u || !u.ctx || !u.bbox) return { error: 'unbuilt' };
        const px = (typeof uPlot !== 'undefined' && uPlot.pxRatio) || 1;
        const L = u.bbox.left / px;
        const T = u.bbox.top / px;
        const W = u.bbox.width / px;
        const H = u.bbox.height / px;
        const R = L + W;
        const xs = u.data[0];
        const n = xs.length;
        const cellPx = W / (n - 1);
        const x0d = Math.round(L * px);
        const x1d = Math.round(R * px);
        const y0d = Math.round(T * px);
        const y1d = Math.round((T + H) * px);
        const img = u.ctx.getImageData(x0d, y0d, x1d - x0d, y1d - y0d).data;
        const wPx = x1d - x0d;
        const out = {};
        for (const k of ['up', 'dl']) {
          const c = cols[k];
          let maxInkDx = -1;
          for (let dx2 = wPx - 1; dx2 >= 0 && maxInkDx < 0; dx2--) {
            for (let dy = 0; dy < y1d - y0d; dy++) {
              const o = (dy * wPx + dx2) * 4;
              if (img[o + 3] > 0
                && Math.abs(img[o] - c[0]) + Math.abs(img[o + 1] - c[1]) + Math.abs(img[o + 2] - c[2]) <= 40) {
                maxInkDx = dx2;
                break;
              }
            }
          }
          let last = -1;
          const col = u.data[k === 'up' ? 1 : 2];
          for (let i = n - 1; i >= 0; i--) {
            if (col[i] != null) { last = i; break; }
          }
          out[k] = { last, edgeGapPx: maxInkDx < 0 ? null : (R - (x0d + maxInkDx) / px) };
        }
        return { up: out.up, dl: out.dl, cellPx, n };
      })(${JSON.stringify(tokens)})`);
      /* 扫描前等拍收口(anim 归位): 桩 base 若跨 30s 边界, 停滞重拉会带 dx0=1 格的 L0 拍
       * (视口摆回旧位期间曲线终点暂时离判定线 ~1 格) —— 静图探针只在拍外采样, 消掉这个
       * 与被测判据无关的时序自由度。 */
      await expect.poll(() => readInst(page,
        'vm._qbCharts && vm._qbCharts.torrent && vm._qbCharts.torrent._qbBeat'
        + ' ? (vm._qbCharts.torrent._qbBeat.anim ? 1 : 0) : -1'), {
        message: '扫描前拍未收口(anim 在途)', timeout: 10_000,
      }).toBe(0);
      const active = await scan();
      if (active.error) throw new Error('活跃态探针失败: ' + active.error);

      /* A5 活跃态: 尾桶有观测(last = n-1)且两轨曲线墨达判定线(edgeGap <= 3px: 曲线宽 2
       * + 抗锯齿余量) —— F4/B2 保证下的显示面; 尾桶回潮间歇 null 或 spanGaps 断线提前
       * 收点时 edgeGap 变成一格宽(cellPx 级), 必红。 */
      for (const k of ['up', 'dl']) {
        expect(active[k].last, `${k} 轨尾桶必须有观测(活跃态前提)`).toBe(active.n - 1);
        expect(active[k].edgeGapPx, `${k} 轨最右曲线墨距判定线 ${active[k].edgeGapPx.toFixed(2)}px 必须 <= 3px`
          + '(A5 活跃态: 采样器活跃时曲线终点恒落判定线)').toBeLessThanOrEqual(3);
      }

      /* 切停滞态: 尾 6 桶无观测(qB 断连真缺口) —— 追加路由后发(后者胜出), 点「30分」
       * 真手势触发重拉 */
      await stubTrafficGapTail(page);
      await drawer.locator('.hist-summary .qb-tabs button', { hasText: '30分' }).click();
      await expect.poll(() => readInst(page,
        'vm._qbCharts && vm._qbCharts.torrent && vm._qbCharts.torrent.data && vm._qbCharts.torrent.data[1]'
        + ' ? (vm._qbCharts.torrent.data[1][59] === null && vm._qbCharts.torrent.data[1][53] != null ? 1 : 0) : -1'), {
        message: '停滞态数据未落袋(尾 6 桶应无观测且链末桶 53 有观测)', timeout: 15_000,
      }).toBe(1);

      /* 同上: 等停滞重拉的 L0 拍(若有)收口再扫 */
      await expect.poll(() => readInst(page,
        'vm._qbCharts && vm._qbCharts.torrent && vm._qbCharts.torrent._qbBeat'
        + ' ? (vm._qbCharts.torrent._qbBeat.anim ? 1 : 0) : -1'), {
        message: '扫描前拍未收口(anim 在途)', timeout: 10_000,
      }).toBe(0);
      const stalled = await scan();
      if (stalled.error) throw new Error('停滞态探针失败: ' + stalled.error);
      for (const k of ['up', 'dl']) {
        expect(stalled[k].last, `${k} 轨链末桶应 = 53(尾 6 桶真缺口)`).toBe(53);
        /* 真缺口诚实断线: 曲线断点距判定线 = GAP_N x 桶宽 ± 4px —— spanGaps:false 收在最后
         * 观测桶, 既不提前消失也不桥接缺口(诚实性: 不造数据, 也不吞缺口) */
        const expectGap = stalled.cellPx * GAP_N;
        expect(stalled[k].edgeGapPx, `${k} 轨最右墨距判定线 ${stalled[k].edgeGapPx.toFixed(2)}px 应约 `
          + `${expectGap.toFixed(2)}px(6 桶宽 —— 真缺口诚实断线在链末桶)`)
          .toBeGreaterThanOrEqual(expectGap - 4);
        expect(stalled[k].edgeGapPx).toBeLessThanOrEqual(expectGap + 4);
      }
    });
  }
});

test.describe('A2 三窗帧采样 · 左端像素连续 + 24h 非整倍窗相位翻动(F5, plan 26-11-15-1104)', () => {
  installRuntimeErrorGuard(test);

  /* A2(plan §01 验收表 + S3 行): 帧采样覆盖 1m/5m/24h 三窗(24h = 非整倍窗)。
   * 判据面(每窗同构):
   *   · 全帧曲线左端像素位 <= 1px(贴住/滑出左缘 —— G-B 判定帧左端跳进一格即红);
   *   · 滚动拍健康: 边界视口位移 <= 1px / dx0 >= 0 / 拍内平滑滑入一格(min/max 任一缘滑过
   *     半格 —— 翻动拍二位移在 max 侧)/ 双缘单调不回跳 / 拍内数据冻结 / 墙钟 <= animEnd+余量;
   *   · 显示列点数 = 真窗口点数或 +1(补尾格拍)。
   * 24h 案(非整倍窗)额外钉相位翻动拍(R5 两类 +1 来源的帧级面, 评审轮1 finding4: 两类签名
   * 都必须真实采到 —— 脚本双 flip 对前置 + minRuns=6 覆盖):
   *   · 翻动拍一(flipA: 窗起点 +1 格、末点不动、点数 -1 —— 498->497 形)照常播 L0: 签名 =
   *     本拍帧 497+补点=498 点 且 前一静止帧 498 点, 缺席即红(旧点数判据误判换档);
   *   · 翻动拍二(flipB: 窗起点不动、末点 +1 格、点数 +1 —— 497->498 形)不 rewin 且入 roll
   *     (dx0=0 位移在 max 侧): L0 照播, 签名 = 本拍帧数较前一静止帧 +1(无补点)+ dx0=0 +
   *     min 缘零滑动 + max 缘滑过半格, 缺席即红(旧判据瞬跳/未放宽的 roll 门缺席)。
   * 桩口径: stubTrafficScripted(interval_s=2 快拍, 每请求恰推进一格 —— 与 A 同款墙钟解耦);
   * 三窗桶数 41/201/498(F1 桶宽表), cellPx 三档量级都过同一判据。 */
  const CASES = [
    { label: '1m', n: 41, script: null, minRuns: 3 },
    { label: '5m', n: 201, script: null, minRuns: 3 },
    {
      label: '24h', n: 498, minRuns: 6,
      script: ['roll', 'flipA', 'roll', 'flipB', 'roll', 'flipA', 'roll', 'flipB', 'roll', 'roll', 'roll', 'roll'],
    },
  ];
  const skin = SKINS[0];

  for (const c of CASES) {
    test(`[${skin}] ${c.label} 窗(${c.n} 桶): 全帧左端贴左缘 + 滚动拍边界连续`
      + `${c.script ? ' + 相位翻动拍照常播 L0' : ''} @fast`, async ({ page }) => {
      test.setTimeout(90_000);
      await stubFlags(page);
      await stubTrafficScripted(page, c.n, 2, c.label, c.script);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      await rearmTrafficPoll(page, drawer);

      /* 页面侧 rAF 采样器(A 同款, 拍段按 impact 相位切): minRuns 个拍段出现且离开 impact
       * 即停。24h 案 minRuns=6: 脚本双 flip 对前置(评审轮1 finding4 —— 请求序偏移 1-4 的
       * 任何形态下 6 个拍段都同时覆盖两类翻动拍)。 */
      await page.evaluate(`(() => {
        const vm = ${INST};
        window.__fs3 = { frames: [], starts: 0, prevImpact: false, done: false, minRuns: ${c.minRuns} };
        const tick = () => {
          const s = window.__fs3;
          if (s.done) return;
          const u = vm._qbCharts && vm._qbCharts.torrent;
          if (u && u._qbBeat && u.data && u.data.length) {
            const a = u._qbBeat.anim;
            const xs = u.data[0];
            const n = xs.length;
            s.frames.push({
              t: performance.now(),
              anim: !!a,
              phase: a ? a.phase : null,
              dx0: a ? a.dx0 : null,
              animEnd: a && a.tl ? a.tl.animEndMs : null,
              min: u.scales.x.min,
              max: u.scales.x.max,
              w: u.bbox.width,
              dpr: (typeof uPlot !== 'undefined' && uPlot.pxRatio) || 1,
              xsLen: n, xs0: xs[0], xsN: xs[n - 1],
              tailUp: u.data[1] ? u.data[1][n - 1] : null,
              tailDl: u.data[2] ? u.data[2][n - 1] : null,
            });
            const inImpact = !!(a && a.phase !== 'tail');
            if (inImpact && !s.prevImpact) s.starts++;
            s.prevImpact = inImpact;
            if (s.starts >= s.minRuns && !inImpact) s.done = true;
          }
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      })()`);
      await expect.poll(() => readInst(page, 'window.__fs3 === undefined ? false : window.__fs3.done === true'), {
        message: `${c.label} 窗 ${c.minRuns} 个拍段未在预算内采满(轮询 2s 一拍; 超时=轮询/节拍链路断了)`,
        timeout: 60_000,
      }).toBe(true);
      const frames = await page.evaluate(() => window.__fs3.frames);
      const runs = beatRuns(frames);
      expect(runs.length, `采样窗内应记录到 >= ${c.minRuns} 个拍段(滚动拍)`).toBeGreaterThanOrEqual(c.minRuns);

      for (let i = 0; i < runs.length; i++) {
        const run = runs[i];
        const idx0 = frames.indexOf(run[0]);
        expect(idx0, '拍段前必须有前帧(边界对照值)').toBeGreaterThanOrEqual(1);
        const prev = frames[idx0 - 1];
        const pxPerUnit = (run[0].w / run[0].dpr) / (run[0].max - run[0].min);

        /* 边界连续性: 判定帧摆回 = 上一拍收敛视图, 视口位移 <= 1px(含翻动拍 —— 摆回锚按
         * dxN 分离, flipA 的 max 恒驻真窗末点, 摆回视图与上一拍收敛视图逐像素同值) */
        const dpx = Math.abs(run[0].min - prev.min) * pxPerUnit;
        expect(dpx, `${c.label} 第 ${i + 1} 拍边界视口位移 ${dpx.toFixed(3)}px 必须 <= 1px`).toBeLessThanOrEqual(1);

        /* 拍内平滑: dx0 >= 0(翻动拍二 dx0=0, 位移在 max 侧)+ 视口行程约一格(min/max 任一缘
         * 滑过半格)+ 逐帧单调不回跳(min/max 双侧)+ 多帧推进 */
        const cellPx = (run[0].w / run[0].dpr) / run[0].xsLen;
        const glidePx = Math.max(Math.abs(run[run.length - 1].min - run[0].min),
          Math.abs(run[run.length - 1].max - run[0].max)) * pxPerUnit;
        expect(run[0].dx0, `${c.label} 第 ${i + 1} 拍 dx0 必须 >= 0(滚动/翻动拍二位移在 max 侧)`)
          .toBeGreaterThanOrEqual(0);
        expect(glidePx, `${c.label} 第 ${i + 1} 拍视口行程 ${glidePx.toFixed(2)}px 应约一格`
          + `(>= ${(cellPx * 0.5).toFixed(2)}px) —— instant 化即红`).toBeGreaterThanOrEqual(cellPx * 0.5);
        expect(run.length, `${c.label} 第 ${i + 1} 拍应有 >= 3 个采样帧`).toBeGreaterThanOrEqual(3);
        for (let j = 1; j < run.length; j++) {
          expect(run[j].min, `${c.label} 第 ${i + 1} 拍第 ${j} 帧视口单调(不回跳)`)
            .toBeGreaterThanOrEqual(run[j - 1].min - 1e-6);
          expect(run[j].max, `${c.label} 第 ${i + 1} 拍第 ${j} 帧 max 缘单调(不回跳)`)
            .toBeGreaterThanOrEqual(run[j - 1].max - 1e-6);
        }
        const dur = run[run.length - 1].t - run[0].t;
        expect(dur, `${c.label} 第 ${i + 1} 拍墙钟 ${Math.round(dur)}ms 必须 <= animEnd(${run[0].animEnd}ms)+900ms`)
          .toBeLessThanOrEqual(run[0].animEnd + 900);

        /* 拍内数据冻结 */
        for (const f of run) {
          expect(f.xs0, '拍内 xs[0] 冻结(L0 不动 data)').toBe(run[0].xs0);
          expect(f.xsN, '拍内 xs 末值冻结').toBe(run[0].xsN);
        }
      }

      /* 全帧左端连续性(A2 本体): 见文件头 A 用例同款判据 —— 三窗各钉一遍 */
      for (let i = 0; i < frames.length; i++) {
        const f = frames[i];
        const pxPerUnit = (f.w / f.dpr) / (f.max - f.min);
        const leftEndPx = (f.xs0 - f.min) * pxPerUnit;
        expect(leftEndPx, `${c.label} 第 ${i} 帧曲线左端像素位 ${leftEndPx.toFixed(2)}px 必须 <= 1px`
          + `(格宽 ${((f.w / f.dpr) / f.xsLen).toFixed(2)}px)`).toBeLessThanOrEqual(1);
      }

      /* 全帧点数不变量(F5 口径): 显示列 = 真窗口点数或 +1(补尾格拍); 24h 案的翻动拍一收敛后
       * 真窗口恒久 -1(498 -> 497), 静止帧合法下界 = n - 1。 */
      const nLo = c.script ? c.n - 1 : c.n;
      for (const f of frames) {
        expect(f.xsLen >= nLo && f.xsLen <= c.n + 1, `${c.label} 帧点数 ${f.xsLen} 必须在`
          + ` [${nLo}, ${c.n + 1}](真窗口或补尾格拍; 翻动拍一收敛后真窗口 -1)`).toBe(true);
      }

      if (c.script) {
        /* 翻动拍签名(R5 帧级钉, 评审轮1 finding4: 两类都必须真实采到并逐帧断言):
         *   · 翻动拍一(498->497 形): 拍段帧 497 真桶 + 1 补点 = 498 点 且 前一静止帧 498 点
         *     —— 照常播 L0, 签名缺席即红(旧点数判据误判换档);
         *   · 翻动拍二(497->498 形): 拍段帧数较前一静止帧 +1(无补点 —— dx0=0 不补)且 dx0=0/
         *     min 缘零滑动/max 缘滑过半格(位移在 max 侧)—— 旧点数判据/未放宽的 roll 门都会
         *     让该拍缺席或瞬跳, 签名缺席即红。 */
        const runInfo = runs.map((run) => {
          const idx0 = frames.indexOf(run[0]);
          const prev = idx0 >= 1 ? frames[idx0 - 1] : null;
          const pxPerUnit = (run[0].w / run[0].dpr) / (run[0].max - run[0].min);
          return {
            idx0, prev, run,
            minGlidePx: Math.abs(run[run.length - 1].min - run[0].min) * pxPerUnit,
            maxGlidePx: Math.abs(run[run.length - 1].max - run[0].max) * pxPerUnit,
            cellPx: (run[0].w / run[0].dpr) / run[0].xsLen,
          };
        });
        const flipARun = runInfo.some((r) => r.run[0].xsLen === c.n && !!r.prev && r.prev.xsLen === c.n);
        const flipBRun = runInfo.some((r) => r.run[0].xsLen === r.prev.xsLen + 1 && r.run[0].dx0 === 0
          && r.minGlidePx < r.cellPx * 0.5 && r.maxGlidePx >= r.cellPx * 0.5);
        const runSig = runInfo.map((r) => `[run@${r.idx0} xsLen=${r.run[0].xsLen}`
          + ` prevXsLen=${r.prev ? r.prev.xsLen : 'n/a'} dx0=${r.run[0].dx0}`
          + ` minGlide=${r.minGlidePx.toFixed(3)}px maxGlide=${r.maxGlidePx.toFixed(3)}px]`).join(' ');
        expect(flipARun, '翻动拍一(498->497 形)必须照常播 L0(签名拍段在场 —— 旧点数判据误判'
          + '换档致该拍瞬时落地即红; 「翻动拍后紧跟的滚动拍」签名不同: 其前静止帧是 497 点)'
          + ` 实测拍段签名: ${runSig}`).toBe(true);
        expect(flipBRun, '翻动拍二(497->498 形)必须照常播 L0(签名拍段在场: min 缘恒驻/max 缘滑'
          + '一格 —— 旧点数判据误判换档或 roll 门未放宽致该拍瞬跳/缺席即红)'
          + ` 实测拍段签名: ${runSig}`).toBe(true);
      }
    });
  }
});

test.describe('节拍动效 · A3 零变化拍环境层解绑(F6/D3, plan 26-11-15-1104)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 24h 窗零变化拍: 每拍 anim.fx 恒在场 lv>=1(环境层与早退门解绑)+ 数据/视口面零动画 @fast`, async ({ page }) => {
      /* A3(计划 §04 S3 行 / §06 D3): 稳态流量(尾桶值恒定且 >0)在零变化拍(needsShift/
       * needsTail 双 false —— 24h 生产窗 cellPx < 0.75 阈值 -> needsShift 恒 false, 稳态尾值
       * 不变 -> needsTail false)每拍出环境层(扫描/粒子/环, Lv.1 下限)—— G-C「粒子时有无」
       * 的根治面: 旧 spawn 判定帧在早退门之后, 稳态零变化拍整拍被挡。桩 = base 固定(窗起点
       * 不动, dx0=0 -> roll=false)+ 值恒正; 数据面零动画保留面同步钉(anim 不带 shift/tail,
       * 视口/尾值逐帧恒真值)。真 0 对照面(值恒 0 -> spawn null 整拍静默)归既有 A3 零流量用例。 */
      await stubFlags(page);
      await stubTrafficZeroChange(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      await rearmTrafficPoll(page, drawer);

      /* 页面侧 rAF 采样器(A1 同款拍段计数): 每帧记 anim 相位/fx 等级/needsShift/needsTail/
       * x 尺/尾值。零变化拍签名 = anim 在场但 needsShift/needsTail 双 false(与 L0 拍区分)。 */
      await page.evaluate(`(() => {
        const vm = ${INST};
        const u = vm._qbCharts && vm._qbCharts.torrent;
        if (!u || !u.ctx || !u.bbox) throw new Error('unbuilt');
        window.__a3z = { frames: [], starts: 0, prevImpact: false, done: false };
        const tick = () => {
          const s1 = window.__a3z;
          if (s1.done) return;
          const u2 = vm._qbCharts && vm._qbCharts.torrent;
          if (u2 && u2.ctx && u2.data && u2.data.length) {
            const a = u2._qbBeat && u2._qbBeat.anim;
            const xs = u2.data[0];
            const n = xs.length;
            s1.frames.push({
              anim: !!a,
              phase: a ? a.phase : null,
              fxLv: a && a.fx ? a.fx.lv : 0,
              shift: a ? !!a.needsShift : null,
              tail: a ? !!a.needsTail : null,
              min: u2.scales.x.min,
              max: u2.scales.x.max,
              tailUp: u2.data[1] ? u2.data[1][n - 1] : null,
              tailDl: u2.data[2] ? u2.data[2][n - 1] : null,
            });
            const inImpact = !!(a && a.phase !== 'tail');
            if (inImpact && !s1.prevImpact) s1.starts++;
            s1.prevImpact = inImpact;
            if (s1.starts >= 3 && !inImpact) s1.done = true;
          }
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      })()`);
      await expect.poll(() => readInst(page, 'window.__a3z === undefined ? false : window.__a3z.done === true'), {
        message: '三个零变化拍段未在预算内采满(轮询 2s 一拍, 三拍约 7s; 超时=轮询/节拍链路断了)',
        timeout: 30_000,
      }).toBe(true);
      const frames = await page.evaluate(() => window.__a3z.frames);
      const runs = beatRuns(frames);
      expect(runs.length, '采样窗内应记录到 >= 3 个零变化拍段').toBeGreaterThanOrEqual(3);

      /* A3 本体: 每个零变化拍 anim.fx 在场且 lv>=1(F6/D3 —— spawn 与早退门解绑), 且该拍
       * anim 不带 shift/tail(数据面零动画保留面)。needsShift=false 的签名与 L0 拍(A1)区分
       * —— 旧判据下这类拍 anim 整段缺席(整拍静默), anim 在场即解绑生效。 */
      for (let i = 0; i < runs.length; i++) {
        const lvMax = Math.max(...runs[i].map((f) => f.fxLv));
        expect(lvMax, `第 ${i + 1} 拍 anim.fx 最大等级 ${lvMax} 必须 >= 1(A3/F6: 零变化拍环境层`
          + '每拍在场 —— 旧判据整拍静默即缺席)').toBeGreaterThanOrEqual(1);
        expect(runs[i].every((f) => f.shift === false),
          `第 ${i + 1} 拍 needsShift 恒 false(零变化拍签名 —— 桩 base 固定)`).toBe(true);
        expect(runs[i].every((f) => f.tail === false),
          `第 ${i + 1} 拍 needsTail 恒 false(数据面零动画保留面)`).toBe(true);
      }

      /* 数据/视口面零改写(I4/L0 零 rAF 保留): 尾值与 x 尺全程恒定(无 L0 摆回、无 L1 收敛) */
      const f0 = frames[0];
      for (const f of frames) {
        expect(f.tailUp, '上传尾值逐帧恒定(数据面零改写)').toBe(f0.tailUp);
        expect(f.tailDl, '下载尾值逐帧恒定').toBe(f0.tailDl);
        expect(f.min, 'x 尺 min 逐帧恒定(零变化拍零视口提交)').toBe(f0.min);
        expect(f.max, 'x 尺 max 逐帧恒定').toBe(f0.max);
      }
      expect(f0.tailUp, '稳态流尾值应为正值(值>0 前提)').toBeGreaterThan(0);
    });
  }
});
