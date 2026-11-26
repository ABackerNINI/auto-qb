// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS, SKINS_ALL } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp, tab } from './lib/gestures.mjs';
import { readInst, withVm } from './lib/vm.mjs';

/**
 * 列风格引擎 e2e(计划 26-11-20-0009 §04 S6 e2e 段 / §07 R7/R9) —— S1-S5 渲染面的真浏览器断言层。
 *
 * 分工: 引擎属性面(<html> 五枚 data-cs-barstyle/-barramp/-speedramp/-numeric/-units)/菜单写链
 * (localStorage 单键 autoqb.colstyle.v1)/跨标签 storage 同步(R8)/首帧无闪烁(R7)/表头菜单五维项
 * torrent 页门控(R9)由 §1-§4 承担; 谱 x 档的**计算色**(颜色映射真落到像素)由 §5 承担 ——
 * 静态守阵(skins_skin 模板类->CSS 配对 / r4_node_batteries 档位装配)只能钉"规则写了 var(--xxx)"
 * 与"类名挂对了档位", 继承/级联/特异性谁赢只有浏览器能证(先例 state-moving.spec 逐通道比对)。
 * console/flux 的「LED 默认形态不变」也由 §5 的四皮肤断言承担(计划 S6 原文口径)。
 *
 * 级联推导纪律(断言期望值按真实级联推导, 不按理想模型):
 *   · 主表行 .g-stat 带状态色规则(.group-row.s-* .g-stat:not(.zero), (0,4,0)); issue 26-11-20-0404
 *     修复后 tone 两档经 :is() 举齐 7 状态也提到 (0,4,0) 且后置, 状态行上真出色; speedramp 选谱 /
 *     numeric=on 的 (0,4,1) 仍压过两者, 期望值仍是谱色/语义色, 不是 numTone 两档色;
 *   · D11 invert 组直接改写 .cs-v/.cs-u 两个 span 自身颜色(span 级规则赢过格级继承) ——
 *     单位断言读 span 的计算色, 不把格色当 span 色;
 *   · 组行速度格刻意不挂 speedramp(S4: 组行现状无速度着色, 挂了破坏默认零变化) —— 速度档
 *     断言只打种子行(种子页平铺行, .group-row.torrent-row 双类, speedramp 唯一消费面)。
 *
 * 注入纪律(D4 两类 evaluate):
 *   · localStorage 预置(addInitScript, drawer-content-dt11-sticky 先例: 必须赶在 app.js 读
 *     localStorage 之前)= 计算色断言的 arrange 手段 —— 写链的真实 UI 路径由 §2 菜单手势承担,
 *     两处不重复; §5 的形态切换用 evaluate 写键 + reload(桩态注入, 装载态读取单点 loadColStyle);
 *   · 速度/数值档的桩数据天然缺分母(桩 server_state 无 dl_rate_limit => speedLimitBytes null =>
 *     speedBand 归 0 档 = 无限速形态不染, 本 spec 先把这个形态钉住)与 HR 伴值, 用 withVm 注入 +
 *     80ms 心跳重注(statusbar-speed-geometry 先例: 真实轮询每 2s 用服务端数据复原, 心跳兜住
 *     竞窗), 断言一律 expect.poll —— 轮询复原只可能让目标色"暂时不见", 不可能让错色"碰巧出现"
 *     (轮询方向无假绿)。
 *
 * 皮肤口径: 菜单/写键/首帧/跨标签走 SKINS(prism/atlas, 冒烟既定口径, 断言与皮肤无关);
 * 计算色走 SKINS_ALL(四皮肤同口径只读测量, harness.mjs 头注) —— 颜色映射规则族单点在
 * shared/console_hub.css, 但"四皮肤 index.html 都 link 了它 + 皮肤基线规则没抢赢"只能逐皮肤验。
 */

/** localStorage 键(单点 app.js COLSTYLE_STORE_KEY; 本文件只读它和按引擎形态写它, 不另立键名)。 */
const COLSTYLE_STORE_KEY = 'autoqb.colstyle.v1';

/** 表头菜单五个维度项可见文案(单点 ctx-menus.html; 顺序 = COLSTYLE_ENUMS 键序)。 */
const FIVE_DIMS = ['进度条样式', '进度条颜色', '速度色阶', '数值色阶', '单位色组'];

/** 五枚 html 属性名(单点 colstyle.js _colStyleSyncAttrs 的 "data-cs-" + COLSTYLE_FIELDS)。 */
const DIM_ATTRS = ['data-cs-barstyle', 'data-cs-barramp', 'data-cs-speedramp', 'data-cs-numeric', 'data-cs-units'];

/** rgb()/rgba()/#hex -> [r,g,b](state-moving.spec 先例同款局部实现; 令牌可能 hex, 计算值恒 rgb,
 * 比对用通道数组规避字符串格式差)。 */
const parseRgb = (/** @type {string} */ s) => {
  const str = String(s || '').trim();
  const m = str.match(/rgba?\(([^)]+)\)/);
  if (m) return m[1].split(',').slice(0, 3).map((x) => Math.round(parseFloat(x)));
  const h = str.match(/^#([0-9a-f]{6})$/i);
  if (h) return [0, 2, 4].map((i) => parseInt(h[1].slice(i, i + 2), 16));
  return null;
};

/** 页面内取令牌真值 -> [r,g,b](计算色比对基准; 令牌真值从 documentElement 的 CSS 变量现读)。 */
async function tokRgb(page, /** @type {string} */ name) {
  const raw = await page.evaluate(
    (/** @type {string} */ n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim(), name);
  const rgb = parseRgb(raw);
  expect(rgb, `令牌 ${name} 应可解析为颜色, 实得「${raw}」`).not.toBeNull();
  return /** @type {number[]} */ (rgb);
}

/**
 * 右键**视口内完整可见的最右列头**(真实手势): 表头随横向滚动同步(syncHeadScroll), DOM 全量在
 * 但越界列头点不到 —— 只挑可见盒; 且刻意取最右一颗, 让菜单右缘被钳到视口右缘, 五维 flyout
 * 必然水平翻转(_subOverflowsRight) —— 钳位断言的确定性前提。
 * @param {import('@playwright/test').Page} page
 * @param {string} tableId aq-table 的 table-id(group = 辅种组表 / torrent = 种子页平铺表)
 */
async function rightClickRightmostHead(page, tableId) {
  const spot = await page.evaluate((/** @type {string} */ tid) => {
    let best = null;
    for (const el of document.querySelectorAll(`.group-head[data-table="${tid}"] .h-cell`)) {
      const r = el.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0) continue;
      if (r.top < 0 || r.bottom > window.innerHeight || r.left < 0 || r.right > window.innerWidth) continue;
      if (!best || r.right > best.right) {
        best = { x: r.left + r.width / 2, y: r.top + r.height / 2, right: r.right };
      }
    }
    return best;
  }, tableId);
  if (!spot) throw new Error(`表头 ${tableId} 视口内无完整可见列头(列结构/视口变了?)`);
  await page.mouse.click(spot.x, spot.y, { button: 'right' });
  await expect(page.locator('.ctx-menu'), '表头右键应弹出列菜单').toBeVisible({ timeout: 5_000 });
  return spot;
}

/** 五维父项(表头菜单直接子项 .ctx-item.has-sub, 按可见文案取; 行菜单的 has-sub 项不在本菜单)。 */
const dimItem = (page, /** @type {string} */ label) =>
  page.locator('.ctx-menu > .ctx-item.has-sub', { hasText: label });

/**
 * 打开五维 flyout(真实手势: 悬停展开 openSub)。不点父项 —— click 是 toggle 语义, 悬停展开后
 * 再点父项反而会收起; 悬停是菜单既定交互(行菜单「更多操作」同款, kbd-reveal 先例)。
 */
async function openFlyout(page, /** @type {string} */ label) {
  const item = dimItem(page, label);
  await item.hover();
  const sub = item.locator('.ctx-sub');
  await expect(sub, `「${label}」flyout 应展开`).toBeVisible({ timeout: 5_000 });
  return { item, sub };
}

/** 预置列风格键(addInitScript 赶在 app.js 读 localStorage 之前) —— 计算色断言的 arrange 手段,
 * 装载态 = "已选好"的状态(D4 第 1 类注入; 真实写链路径由 §2 菜单手势单独承担)。 */
function presetColStyle(page, /** @type {Record<string, string>} */ patch) {
  return page.addInitScript((/** @type {Record<string, string>} */ p) => {
    localStorage.setItem('autoqb.colstyle.v1', JSON.stringify(Object.assign({ v: 1 }, p)));
  }, patch);
}

/** 平铺种子页: 切页签 + 等首行(行窗口化渲染, 种子行 .torrent-row)。 */
async function gotoTorrentView(page) {
  await tab(page, 'torrents').click();
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
}

/* ==========================================================================
 * §1-§4 引擎面: 菜单开合/写键/首帧/跨标签(SKINS 双皮肤 —— 断言与皮肤无关, 冒烟既定口径)
 * ========================================================================== */
for (const skin of SKINS) {
  test.describe(`列风格引擎 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`表头菜单: torrent 页五维在场 + 非 torrent 页不在场(R9) + flyout 钳位翻转 + 色样(D13) @fast (${skin})`, async ({ page }) => {
      await openApp(page, skin);
      const menu = page.locator('.ctx-menu');

      /* 非 torrent 页 = 默认辅种组表(headMenu.page='group'): aq-table 全表共用菜单, 五维项必须
       * 被页面门控拦住(R9) —— 辅种表头菜单里一个都不出现。 */
      await rightClickRightmostHead(page, 'group');
      for (const label of FIVE_DIMS) {
        await expect(menu.locator(`.ctx-item.has-sub:has-text("${label}")`),
          `非 torrent 页(辅种组表)不得出现「${label}」`).toHaveCount(0);
      }
      await page.keyboard.press('Escape');
      await expect.poll(() => readInst(page, 'vm.headMenu.visible'), { message: 'Esc 收起表头菜单' }).toBe(false);

      /* torrent 页(种子页平铺, headMenu.page='torrent'): 五维项全在场。右键最右可见列头 =>
       * 菜单右缘贴视口 => flyout 必翻转 —— 钳位断言(翻转后仍整盒收进视口, EDGE 8)的确定性前提。 */
      await gotoTorrentView(page);
      const spot = await rightClickRightmostHead(page, 'torrent');
      for (const label of FIVE_DIMS) {
        await expect(menu.locator(`.ctx-item.has-sub:has-text("${label}")`),
          `torrent 页应有「${label}」维度项`).toHaveCount(1);
      }

      /* flyout 逐个悬停展开: radio 项数(COLSTYLE_ENUMS 值域 + 默认档)与色样形态(D13)。 */
      const barramp = await openFlyout(page, '进度条颜色');
      await expect(barramp.sub.locator('.ctx-item'), '进度条颜色 = 跟随状态 + 4 谱').toHaveCount(5);
      await expect(barramp.sub.locator('.ctx-item', { hasText: '跟随状态' }).locator('.ctx-tick'),
        '默认档(跟随状态)带勾').toHaveCount(1);
      await expect(barramp.sub.locator('.ctx-item', { hasText: '跟随状态' }).locator('.cs-ramp'),
        'D13: 跟随状态项无色样').toHaveCount(0);
      const cool = barramp.sub.locator('.ctx-item', { hasText: '冷熟谱' });
      await expect(cool.locator('.cs-ramp i'), '色阶谱项 = 六格迷你色带(五档+终点)').toHaveCount(6);
      await expect(cool.locator('.cs-ramp i.cs-indigo'), '色带格色 = 令牌色类(冷熟谱首格 indigo)').toHaveCount(1);
      await expect(cool.locator('.cs-ramp i.cs-green'), '冷熟谱终点格 = green').toHaveCount(1);
      await expect(barramp.sub.locator('.ctx-item', { hasText: '温度谱' }).locator('.cs-ramp i.cs-error'),
        '温度谱终点格 = error').toHaveCount(1);
      await expect(barramp.sub.locator('.ctx-item', { hasText: '主题谱' }).locator('.cs-ramp i.cs-accent-hi'),
        '主题谱终点格 = accent-hi').toHaveCount(1);

      const barstyle = await openFlyout(page, '进度条样式');
      await expect(barstyle.sub.locator('.ctx-item'), '进度条样式 = 跟随皮肤/常规条/LED').toHaveCount(3);
      await expect(barstyle.sub.locator('.cs-bar.cs-bar-led > i'), 'LED 选项带迷你分段条样').toHaveCount(1);
      await expect(barstyle.sub.locator('.cs-bar:not(.cs-bar-led) > i'), '常规条选项带迷你实心条样').toHaveCount(1);
      await expect(barstyle.sub.locator('.ctx-item', { hasText: '跟随皮肤' }).locator('.cs-bar'),
        'D13: 跟随皮肤项无色样').toHaveCount(0);

      const speedramp = await openFlyout(page, '速度色阶');
      await expect(speedramp.sub.locator('.ctx-item'), '速度色阶 = 跟随现状 + 4 谱 + 关').toHaveCount(6);
      await expect(speedramp.sub.locator('.ctx-item', { hasText: '跟随现状' }).locator('.cs-ramp, .cs-dots'),
        'D13: 跟随现状项无色样').toHaveCount(0);
      await expect(speedramp.sub.locator('.ctx-item', { hasText: '关' }).locator('.cs-ramp, .cs-dots'),
        'D13: 关项无色样').toHaveCount(0);

      const numeric = await openFlyout(page, '数值色阶');
      await expect(numeric.sub.locator('.ctx-item'), '数值色阶 = 关/开').toHaveCount(2);
      await expect(numeric.sub.locator('.ctx-item', { hasText: '开' }).locator('.cs-dots i'),
        '数值色阶「开」= 三色点(warn/green/accent-hi)').toHaveCount(3);
      await expect(numeric.sub.locator('.ctx-item', { hasText: '关' }).locator('.cs-dots'),
        'D13: 数值「关」项无色样').toHaveCount(0);

      const units = await openFlyout(page, '单位色组');
      await expect(units.sub.locator('.ctx-item'), '单位色组 = 8 组(D11)').toHaveCount(8);
      await expect(units.sub.locator('.cs-unit'), '除「统一」外各组带迷你样例字').toHaveCount(7);
      await expect(units.sub.locator('.cs-unit.dim'), '单位淡化组样例字带 dim 修饰类').toHaveCount(1);

      /* flyout 钳位(_subFitViewport 契约): 整盒收进视口(EDGE 8, 容差 0.5px); 最右列头右键 =>
       * 父项右缘贴视口右缘 => 必走 flip-x(不翻则 272px 面板探出视口, 钳位没生效)。 */
      const clamp = await openFlyout(page, '进度条颜色');
      const vw = page.viewportSize() ? page.viewportSize().width : 1440;
      const vh = page.viewportSize() ? page.viewportSize().height : 900;
      await expect.poll(async () => {
        const b = await clamp.sub.boundingBox();
        return !!b && b.x >= 7.5 && b.y >= 7.5 && b.x + b.width <= vw - 7.5 && b.y + b.height <= vh - 7.5;
      }, { message: 'flyout 整盒收进视口(EDGE 8, 钳位含二次收口帧)' }).toBe(true);
      /* 翻转断言的确定性前提先行: 列头右缘距视口右缘须小于一个 flyout 面(openSub 估宽 272 + EDGE 8),
       * 菜单弹出才必然溢出 => 钳位才必然翻转。前提漂移(默认可见列集/列宽模板变了)时报「前提失效」,
       * 不误指翻转实现。 */
      expect(spot.right, `钳位前提: 最右列头右缘 ${spot.right} 应落在视口右缘一个 flyout 宽内(vw=${vw})`)
        .toBeGreaterThan(vw - 272 - 8);
      await expect(clamp.sub, '父项右缘贴视口 => flyout 水平翻转').toHaveClass(/flip-x/);

      await page.keyboard.press('Escape');
      await expect.poll(() => readInst(page, 'vm.headMenu.visible'), { message: 'Esc 收起表头菜单' }).toBe(false);
      await expect.poll(() => readInst(page, 'vm.subMenu'),
        { message: '关层连带收 flyout(state.js watch headMenu.visible 清链)' }).toBe('');
    });

    test(`切换写链: flyout 点选 => html 属性即时变 + 键值更新 + 勾选跟手 + 刷新持久 @fast (${skin})`, async ({ page }) => {
      await openApp(page, skin);
      await gotoTorrentView(page);
      await rightClickRightmostHead(page, 'torrent');

      const { sub } = await openFlyout(page, '进度条颜色');
      await sub.locator('.ctx-item', { hasText: '冷熟谱' }).click();

      /* 写链三面: <html> 属性即时变(watch colStyle 派发) / localStorage 单键更新 / 回执 toast。 */
      await expect(page.locator('html')).toHaveAttribute('data-cs-barramp', 'cool');
      const blob = JSON.parse(await page.evaluate((/** @type {string} */ k) => localStorage.getItem(k), COLSTYLE_STORE_KEY));
      expect(blob, 'localStorage 键值更新(单键 JSON+版本, 其余维保持默认)').toMatchObject({ v: 1, barramp: 'cool' });
      await expect(page.locator('.toast', { hasText: '进度条颜色已切换: 冷熟谱' })).toBeVisible();
      await expect(page.locator('.ctx-menu'), '五维写链不关菜单(调参面, D12 与 headMenuTimeFmt 的刻意差异)').toBeVisible();

      /* radio 勾选跟手: 勾移到冷熟谱, 默认档勾消失(菜单开着响应式跟手)。 */
      await expect(sub.locator('.ctx-item', { hasText: '冷熟谱' }).locator('.ctx-tick')).toHaveCount(1);
      await expect(sub.locator('.ctx-item', { hasText: '跟随状态' }).locator('.ctx-tick')).toHaveCount(0);

      /* 连续切另一档: 属性即时跟随(radio 换选)。 */
      await sub.locator('.ctx-item', { hasText: '主题谱' }).click();
      await expect(page.locator('html')).toHaveAttribute('data-cs-barramp', 'theme');

      /* 刷新持久: load 先于首渲染 => 首帧属性即存储真值。 */
      await page.keyboard.press('Escape');
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await expect(page.locator('html'), '刷新后持久').toHaveAttribute('data-cs-barramp', 'theme');
      const blob2 = JSON.parse(await page.evaluate((/** @type {string} */ k) => localStorage.getItem(k), COLSTYLE_STORE_KEY));
      expect(blob2.barramp).toBe('theme');
    });

    test(`首帧无闪烁(R7): 预置键值 => 属性首写即终态, 观察序列无默认档闪烁帧 @fast (${skin})`, async ({ page }) => {
      /* 五维全部预置成非默认值: 若 colstyle 晚于首渲染, 观察序列里会先出现默认档再改写为预置值
       * (闪烁两帧); 修复态(load 先于首渲染 + created 首帧同步写属性)序列首值即预置值。 */
      const preset = { barstyle: 'plain', barramp: 'heat', speedramp: 'off', numeric: 'on', units: 'invert' };
      await page.addInitScript((/** @type {*} */ arg) => {
        localStorage.setItem('autoqb.colstyle.v1', JSON.stringify(Object.assign({ v: 1 }, arg.preset)));
        window.__csWrites = [];
        const obs = new MutationObserver((muts) => {
          for (const m of muts) {
            if (m.attributeName && m.attributeName.indexOf('data-cs-') === 0) {
              window.__csWrites.push([m.attributeName, document.documentElement.getAttribute(m.attributeName)]);
            }
          }
        });
        const install = () => obs.observe(document.documentElement, { attributes: true, attributeFilter: arg.attrs });
        if (document.documentElement) install();
        else document.addEventListener('DOMContentLoaded', install, { once: true });
      }, { preset, attrs: DIM_ATTRS });

      await openApp(page, skin);

      const seq = await page.evaluate(() => /** @type {*} */ (window).__csWrites || []);
      const first = {};
      for (const [k, v] of seq) if (!(k in first)) first[k] = v;
      for (const dim of Object.keys(preset)) {
        expect(first['data-cs-' + dim], `「${dim}」首次写入即预置值(观察序列: ${JSON.stringify(seq)})`).toBe(preset[dim]);
      }
      /* 断言面收窄声明: 本用例钉「首写即终态/无默认档闪烁帧」; 写点时序(首帧前同步 vs mount 后
       * 一次性写对)不在断言面 —— 后者首写仍是预置值, 由 created 时序的静态实现承担(R7 判据
       * theme/timeFmt 先例同口径)。 */
      for (const dim of Object.keys(preset)) {
        await expect(page.locator('html')).toHaveAttribute('data-cs-' + dim, preset[dim]);
      }
    });

    test(`跨标签同步(R8): 第二页写键 => 第一页 storage 事件整份采用, 属性跟随 @fast (${skin})`, async ({ page }) => {
      await openApp(page, skin);
      await expect(page.locator('html')).toHaveAttribute('data-cs-barramp', 'status');

      /* 第二页 = 同 context 的第二页(共享 localStorage, storage 事件照常跨页, column-prefs 先例)。
       * 写入面直接 localStorage.setItem: "另一个标签改了存储"本身没有 UI 路径, 事件采纳侧
       * (adoptColStyle 整份采用)才是本用例的断言对象 —— 写链的 UI 路径已由上一条用例承担。 */
      const tab2 = await page.context().newPage();
      const errors2 = collectRuntimeErrors(tab2);
      await tab2.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(tab2.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      await tab2.evaluate((/** @type {string} */ k) => localStorage.setItem(k, JSON.stringify(
        { v: 1, barstyle: 'led', barramp: 'heat', speedramp: 'rainbow', numeric: 'on', units: 'family' })), COLSTYLE_STORE_KEY);

      /* 五维整份跟随(整份采用而非逐维合并 —— R8): toHaveAttribute 自带重试, 吸收事件传播延迟。 */
      await expect(page.locator('html')).toHaveAttribute('data-cs-barstyle', 'led');
      await expect(page.locator('html')).toHaveAttribute('data-cs-barramp', 'heat');
      await expect(page.locator('html')).toHaveAttribute('data-cs-speedramp', 'rainbow');
      await expect(page.locator('html')).toHaveAttribute('data-cs-numeric', 'on');
      await expect(page.locator('html')).toHaveAttribute('data-cs-units', 'family');
      await expect.poll(() => readInst(page, 'vm.colStyle.units'), { message: 'vm 状态整份采用' }).toBe('family');

      /* 整份采用语义的真分叉点: 半 blob(缺维)写入 —— 整份采用把缺省字段回落默认, 逐维合并则
       * 保留旧值; 上段全维 blob 分不出这两种实现, 本段钉死分叉(barstyle 应回 skin 而非留 led)。 */
      await tab2.evaluate((/** @type {string} */ k) =>
        localStorage.setItem(k, JSON.stringify({ v: 1, units: 'accent' })), COLSTYLE_STORE_KEY);
      await expect(page.locator('html')).toHaveAttribute('data-cs-barstyle', 'skin');
      await expect(page.locator('html')).toHaveAttribute('data-cs-barramp', 'status');
      await expect(page.locator('html')).toHaveAttribute('data-cs-units', 'accent');

      await tab2.close();
      expect(errors2, `第二页运行期错误:\n${errors2.join('\n')}`).toEqual([]);
    });
  });
}

/* ==========================================================================
 * §5 计算色(SKINS_ALL 四皮肤同口径): 谱 x 档真落到像素 + 形态维 + 单位组 + 拆分文本
 * ========================================================================== */
for (const skin of SKINS_ALL) {
  test.describe(`列风格计算色 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`barramp 选谱: 条填充与百分比文字 == 冷熟谱该档令牌值(逐通道比对) @fast (${skin})`, async ({ page }) => {
      await presetColStyle(page, { barramp: 'cool' });
      await openApp(page, skin);
      await gotoTorrentView(page);

      const res = await page.evaluate(() => {
        /* 页内只采集原始颜色串(令牌自定义属性保留书写形态, 多为 hex; 计算值恒 rgb()), 通道比对
         * 统一在 Node 侧单点 parseRgb —— 页内不再复制 parse(先例 state-moving.spec 只留 Node 侧)。 */
        const cs = getComputedStyle(document.documentElement);
        const tokRaw = (n) => cs.getPropertyValue(n).trim();
        /* 条填充色的读取面分两形: atlas/prism 默认实底(backgroundColor 直读); console/flux
         * 皮肤默认 LED 分段底 => 色在 backgroundImage 的 repeating-linear-gradient 首个色阶里
         * (computed 已把 var(--cs-fill,...) 解析进色阶), backgroundColor 是透明。 */
        const fillOf = (el) => {
          const bg = getComputedStyle(el).backgroundImage;
          if (bg && bg.indexOf('gradient') >= 0) {
            const m = bg.match(/rgba?\([^)]+\)/);
            return m ? m[0] : '';
          }
          return getComputedStyle(el).backgroundColor;
        };
        /* 档位 -> 令牌(单点 console_hub.css 冷熟谱段: indigo/blue/cyan/teal/lime, 终点 green,
         * 0% 空端点恒 fg-muted) —— 期望值从档位类推导, 不从行序推导(对桩数据轮转不脆)。 */
        const COOL = { 'csb-0': '--fg-muted', 'csb-1': '--indigo', 'csb-2': '--blue', 'csb-3': '--cyan',
          'csb-4': '--teal', 'csb-5': '--lime', 'csb-t': '--green' };
        const bad = [];
        const bands = new Set();
        const samples = [];
        for (const bar of document.querySelectorAll('.torrent-row .m-progress .bar > i')) {
          const band = [...bar.classList].find((c) => /^csb-(0|[1-5]|t)$/.test(c));
          if (!band) { bad.push('条无档位类: class=' + bar.className); continue; }
          bands.add(band);
          const prog = bar.closest('.m-progress');
          const val = prog ? prog.querySelector('.val') : null;
          const vband = val ? [...val.classList].find((c) => /^csb-/.test(c)) : null;
          samples.push({
            band, token: COOL[band], wantRaw: tokRaw(COOL[band]), fillRaw: fillOf(bar),
            vband, valRaw: val ? getComputedStyle(val).color : '',
          });
        }
        return { bad, bands: [...bands], samples };
      });
      /* 谱 x 档计算色逐通道比对(单点 parseRgb; want=令牌真值, got=计算值)。 */
      const csbBad = [];
      for (const s of res.samples) {
        const want = parseRgb(s.wantRaw);
        const got = parseRgb(s.fillRaw);
        if (!want) csbBad.push(`条 ${s.band}: 令牌 ${s.token} 不可解析「${s.wantRaw}」`);
        else if (!got || want.join(',') !== got.join(',')) csbBad.push(`条 ${s.band}: 期望 ${want} 实得 ${got}`);
        if (!s.vband || s.vband !== s.band) csbBad.push(`百分比文字未挂同档类 ${s.band}: ${s.vband}`);
        else {
          const vgot = parseRgb(s.valRaw);
          if (!vgot || want.join(',') !== vgot.join(',')) csbBad.push(`文字 ${s.band}: 期望 ${want} 实得 ${vgot}`);
        }
      }
      const allBad = res.bad.concat(csbBad);
      expect(allBad, `谱 x 档计算色逐通道比对:\n${allBad.join('\n')}`).toEqual([]);
      expect(res.bands.length, `档位覆盖自证(首窗至少 2 个档位类, 实得 ${res.bands.join('/')})`).toBeGreaterThanOrEqual(2);
    });

    test(`barstyle 形态维: 默认=皮肤形态不变 / led 四皮肤生效 / plain 压过 LED 皮肤默认 @fast (${skin})`, async ({ page }) => {
      await openApp(page, skin);
      const grad = () => page.evaluate(() => {
        const el = document.querySelector('.group-row .m-progress .bar > i');
        return el ? getComputedStyle(el).backgroundImage : null;
      });

      /* 默认档(barstyle=skin): 不出任何规则 => 皮肤基线一字不动 —— atlas/prism 常规实底,
       * console/flux LED 分段底(皮肤默认形态, 计划 S6「console/flux 默认不变」的基线面)。 */
      const dflt = await grad();
      if (skin === 'console' || skin === 'flux') {
        expect(dflt, 'console/flux 默认即 LED 形态(皮肤基线)').toContain('repeating-linear-gradient');
      } else {
        expect(dflt, 'atlas/prism 默认常规实底(backgroundImage 为 none)').toBe('none');
      }

      /* 显式选 LED: 分段底在四皮肤全部生效(console/flux = 与默认同形态, 视觉不变)。 */
      await page.evaluate((/** @type {string} */ k) =>
        localStorage.setItem(k, JSON.stringify({ v: 1, barstyle: 'led' })), COLSTYLE_STORE_KEY);
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      expect(await grad(), 'barstyle=led: 分段底四皮肤生效').toContain('repeating-linear-gradient');

      /* 显式选常规条: 压过 console/flux 的 LED 皮肤默认(shared 规则族后置于皮肤 css + 特异性更高,
       * S3 取舍) —— plain 后四皮肤全部回落实底。 */
      await page.evaluate((/** @type {string} */ k) =>
        localStorage.setItem(k, JSON.stringify({ v: 1, barstyle: 'plain' })), COLSTYLE_STORE_KEY);
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      expect(await grad(), 'barstyle=plain: 四皮肤回落实底(none)').toBe('none');
    });

    test(`speedramp/numeric: 无限速形态不染; 选谱+开数值后档位/语义色压状态色真出色 @fast (${skin})`, async ({ page }) => {
      await presetColStyle(page, { speedramp: 'cool', numeric: 'on' });
      await openApp(page, skin);
      await gotoTorrentView(page);

      /* 无限速形态(D8): 桩 server_state 无 dl_rate_limit => speedLimitBytes null => speedBand
       * 归 0 档 = 无类不染 —— 选了谱也一样, 这是「不染」面的一半证据(0 分母侧)。 */
      expect(await page.evaluate(() =>
        document.querySelectorAll('.torrent-row .g-stat[class*="csp-"]').length),
        '无限速形态(分母 null)不染, 选谱也不染').toBe(0);

      /* 注入分母与行档(D4 第 1 类 + 80ms 心跳重注, statusbar-speed-geometry 先例):
       *   顶行: dlspeed=51200 / limit=102400 => ratio 0.5 => band 3(冷熟谱 = cyan);
       *         ratio 0.5(<1) => cst-warn; eta=30s(<60) => cst-soon;
       *   次行: ratio 1.5(>=1) => cst-good。
       * hr_triggered=false 摘掉 HR 伴值(D10: 有伴值判定让位) —— 桩顶两行是 HR 触发行, 不摘则
       * cellNumScaleRatio 让位, 断言对象消失。 */
      const hashes = await withVm(page, `
        const list = vm.torrents || [];
        if (list.length < 2) throw new Error('vm.torrents 不足 2 行(桩数据没起来)');
        const P1 = { dlspeed: 51200, eta: 30, ratio: 0.5, hr_triggered: false };
        const P2 = { ratio: 1.5, hr_triggered: false };
        const a = list[list.length - 1], b = list[list.length - 2];
        Object.assign(a, P1); Object.assign(b, P2);
        const beat = setInterval(() => {
          vm.statsServer = Object.assign({}, vm.statsServer, { dl_rate_limit: 102400, up_rate_limit: 0 });
          const re = (h, p) => { const t = (vm.torrents || []).find((x) => x.hash === h); if (t) Object.assign(t, p); };
          re(a.hash, P1); re(b.hash, P2);
        }, 80);
        window.__csBeat = beat;
        return [a.hash, b.hash];
      `);
      const [h1, h2] = /** @type {string[]} */ (hashes);
      expect(h1 && h2, '注入目标应有 hash').toBeTruthy();

      /* 探针: 按内容/结构取格, 读 class 与计算色(通道数组, 规避字符串格式差)。轮询每 2s 复原
       * 桩值, 心跳 80ms 重注 —— poll 只会在"暂时被复原"的帧上重试, 目标色出现即过(无假绿)。 */
      const textCellProbe = (/** @type {string} */ hash, /** @type {string} */ text) => page.evaluate((arg) => {
        const row = document.querySelector('.torrent-row[data-hash="' + arg[0] + '"]');
        if (!row) return null;
        const el = [...row.querySelectorAll('.g-stat')].find((c) => c.textContent.indexOf(arg[1]) >= 0);
        if (!el) return null;
        const m = getComputedStyle(el).color.match(/rgba?\(([^)]+)\)/);
        return {
          cls: String(el.className),
          rgb: m ? m[1].split(',').slice(0, 3).map((x) => Math.round(parseFloat(x))) : null,
        };
      }, [hash, text]);
      const selCellProbe = (/** @type {string} */ hash, /** @type {string} */ sel) => page.evaluate((arg) => {
        const row = document.querySelector('.torrent-row[data-hash="' + arg[0] + '"]');
        const el = row && row.querySelector(arg[1]);
        if (!el) return null;
        const m = getComputedStyle(el).color.match(/rgba?\(([^)]+)\)/);
        return {
          cls: String(el.className),
          rgb: m ? m[1].split(',').slice(0, 3).map((x) => Math.round(parseFloat(x))) : null,
        };
      }, [hash, sel]);

      const cyan = await tokRgb(page, '--cyan');
      const warn = await tokRgb(page, '--warn');
      const green = await tokRgb(page, '--green');
      const accentHi = await tokRgb(page, '--accent-hi');

      /* 速度档: csp-3(冷熟谱 band3 = cyan) —— (0,4,1) 新规则压过状态色 (0,4,0), 谱色真可见。 */
      await expect.poll(() => textCellProbe(h1, '50.00 KiB/s'),
        { message: '速度格 csp-3 计算色 == 冷熟谱 band3(--cyan)', timeout: 15_000 })
        .toEqual({ cls: expect.stringContaining('csp-3'), rgb: cyan });

      /* 数值档三色(D10): ratio<1 => warn / ratio>=1 => good / eta<60s => soon。 */
      await expect.poll(() => selCellProbe(h1, '.m-pair.m-ratio'),
        { message: 'ratio<1 格 cst-warn 计算色 == --warn', timeout: 15_000 })
        .toEqual({ cls: expect.stringContaining('cst-warn'), rgb: warn });
      await expect.poll(() => selCellProbe(h2, '.m-pair.m-ratio'),
        { message: 'ratio>=1 格 cst-good 计算色 == --green', timeout: 15_000 })
        .toEqual({ cls: expect.stringContaining('cst-good'), rgb: green });
      await expect.poll(() => selCellProbe(h1, '.g-stat.cst-soon'),
        { message: 'eta<60s 格 cst-soon 计算色 == --accent-hi', timeout: 15_000 })
        .toEqual({ cls: expect.stringContaining('cst-soon'), rgb: accentHi });

      await page.evaluate(() => { if (window.__csBeat) clearInterval(window.__csBeat); }).catch(() => {});
    });

    test(`tone 两档在状态行上真胜出(级联特异性, issue 26-11-20-0404) @fast (${skin})`, async ({ page }) => {
      await openApp(page, skin);
      /* 合成状态行读计算色: 纯 CSS 级联判据不依赖桩数据/行窗口化; 行类名取实模板口径
       * (种子/组行 s-seeding/s-paused, 成员行 seeding/paused —— 仅 prism 有 member tone 规则)。 */
      const res = await page.evaluate(() => {
        const tok = (/** @type {string} */ n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
        const colorOf = (/** @type {string} */ rowCls, /** @type {string} */ cellCls) => {
          const row = document.createElement('div');
          row.className = rowCls;
          const cell = document.createElement('div');
          cell.className = cellCls;
          cell.textContent = '1';
          row.appendChild(cell);
          document.body.appendChild(row);
          const color = getComputedStyle(cell).color;
          row.remove();
          return color;
        };
        return {
          muted: tok('--fg-muted'), hi: tok('--accent-hi'),
          gLow: colorOf('group-row s-seeding', 'g-stat tone-low'),
          gHigh: colorOf('group-row s-paused', 'g-stat tone-high'),
          mLow: colorOf('member-row seeding', 'm-stat tone-low'),
          mHigh: colorOf('member-row paused', 'm-stat tone-high'),
        };
      });
      const muted = parseRgb(res.muted);
      const hi = parseRgb(res.hi);
      expect(muted, `--fg-muted 应可解析, 实得「${res.muted}」`).not.toBeNull();
      expect(hi, `--accent-hi 应可解析, 实得「${res.hi}」`).not.toBeNull();
      expect(parseRgb(res.gLow), '种子/组行 s-* tone-low == --fg-muted(不被状态色压制)').toEqual(muted);
      expect(parseRgb(res.gHigh), '种子/组行 s-* tone-high == --accent-hi(不被状态色压制)').toEqual(hi);
      if (skin === 'prism') {
        expect(parseRgb(res.mLow), 'prism 成员行 tone-low == --fg-muted').toEqual(muted);
        expect(parseRgb(res.mHigh), 'prism 成员行 tone-high == --accent-hi').toEqual(hi);
      }
    });

    test(`units 单位色组: 按档组 .cs-u 计算色 + 拆分文本逐字一致(R2) + invert 改写数值色 @fast (${skin})`, async ({ page }) => {
      await openApp(page, skin);
      /* 选组 = evaluate 写键 + reload(本用例不走 addInitScript 预置 —— init script 每次导航
       * 都会重写键值, 会把 reload 前的写入盖回去; 全部换组走同一条写键+reload 路径)。 */
      await page.evaluate((/** @type {string} */ k) =>
        localStorage.setItem(k, JSON.stringify({ v: 1, units: 'band-cool' })), COLSTYLE_STORE_KEY);
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      const res = await page.evaluate(() => {
        /* 页内只采集原始颜色串(同 barramp 段口径: 比对统一 Node 侧单点 parseRgb)。 */
        const cs = getComputedStyle(document.documentElement);
        const tokRaw = (n) => cs.getPropertyValue(n).trim();
        /* 按档·冷熟(D11 表, 单点 console_hub.css band-cool 段): 期望值从单位档类(csu-*)推导。 */
        const BAND = { 'csu-B': '--fg-muted', 'csu-Bs': '--fg-muted', 'csu-KiB': '--blue', 'csu-KiBs': '--blue',
          'csu-MiB': '--cyan', 'csu-MiBs': '--teal', 'csu-GiB': '--teal', 'csu-GiBs': '--green',
          'csu-TiB': '--lime', 'csu-PiB': '--green' };
        const bad = [];
        const kinds = new Set();
        const samples = [];
        for (const u of document.querySelectorAll('.group-row[data-table="group"] .cs-u')) {
          const kind = [...u.classList].find((c) => /^csu-/.test(c));
          if (!kind || !(kind in BAND)) { bad.push('单位 span 无已知档类: ' + u.className); continue; }
          kinds.add(kind);
          samples.push({ kind, token: BAND[kind], wantRaw: tokRaw(BAND[kind]), gotRaw: getComputedStyle(u).color });
        }

        /* 拆分文本逐字一致(R2 列宽几何的文本面): 格 textContent == fmt 单点串(生产现算), 拆双
         * span 不得多/少一个字符。零值 = 空白(OrDash 口径); 组行 size 格 risk 图标前的 {{ " " }}
         * 是刻意节点 => 该格期望串尾恒多一个空格。列定位走表头文案(不依赖 nth-child —— 单元格
         * DOM 无列标识, 列可隐藏重排)。 */
        const vm = document.querySelector('#app')._vnode.component.proxy;
        const headLabels = [...document.querySelectorAll('.group-head[data-table="group"] .h-cell .h-label')]
          .map((el) => el.textContent.trim());
        const colOf = {
          dlspeed: headLabels.indexOf('下载'), upspeed: headLabels.indexOf('上传'),
          uploaded: headLabels.indexOf('总上传'), size: headLabels.indexOf('大小'),
          total_size: headLabels.indexOf('总大小'), downloaded: headLabels.indexOf('已下载'),
        };
        for (const [key, ci] of Object.entries(colOf)) {
          if (ci < 0) bad.push(`表头找不到「${key}」列文案`);
        }
        const rows = [...document.querySelectorAll('.group-row[data-table="group"][data-key]')].slice(0, 3);
        for (const row of rows) {
          const g = (vm.groups || []).find((x) => x.key === row.dataset.key);
          if (!g) { bad.push('组行模型未找到: ' + row.dataset.key); continue; }
          for (const [key, ci] of Object.entries(colOf)) {
            const cell = row.children[ci];
            if (!cell) { bad.push(`列 ${key} 序 ${ci} 越界(表头/行格错位?)`); continue; }
            const isSpeed = key === 'dlspeed' || key === 'upspeed';
            const val = g[key];
            const base = val ? (isSpeed ? vm.fmtSpeed(val) : vm.fmtSize(val)) : '';
            const want = key === 'size' ? base + ' ' : base;
            if (cell.textContent !== want) {
              bad.push(`组行 ${key} 文本不一致: 期望「${want}」实得「${cell.textContent}」`);
            }
          }
        }
        return { bad, kinds: [...kinds], samples, nRows: rows.length };
      });
      /* 单位色组计算色比对(Node 侧单点 parseRgb)。 */
      const csuBad = [];
      for (const s of res.samples) {
        const want = parseRgb(s.wantRaw);
        const got = parseRgb(s.gotRaw);
        if (!want) csuBad.push(`单位 ${s.kind}: 令牌 ${s.token} 不可解析「${s.wantRaw}」`);
        else if (!got || want.join(',') !== got.join(',')) csuBad.push(`单位 ${s.kind}: 期望 ${want} 实得 ${got}`);
      }
      const unitBad = res.bad.concat(csuBad);
      expect(unitBad, `单位色组计算色与拆分文本:\n${unitBad.join('\n')}`).toEqual([]);
      expect(res.kinds.length, `单位档类覆盖自证(至少 2 档, 实得 ${res.kinds.join('/')})`).toBeGreaterThanOrEqual(2);
      expect(res.nRows, '组行样本(默认辅种视图首窗)').toBeGreaterThanOrEqual(1);

      /* invert 组(D11 唯一改写数值色的组): .cs-v => fg-muted / .cs-u => fg —— span 级规则
       * 直接命中拆分格, 赢过格上的状态/tone/csp 继承(命中面天然限于拆分格, 无需行级限定)。 */
      await page.evaluate((/** @type {string} */ k) =>
        localStorage.setItem(k, JSON.stringify({ v: 1, units: 'invert' })), COLSTYLE_STORE_KEY);
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const inv = await page.evaluate(() => {
        /* 页内只采集原始颜色串(比对统一 Node 侧单点 parseRgb; 失败逐元素出明细)。 */
        const cs = getComputedStyle(document.documentElement);
        const grab = (sel) => [...document.querySelectorAll(sel)]
          .map((el) => ({ cls: el.className, raw: getComputedStyle(el).color }));
        return {
          v: grab('.group-row[data-table="group"] .cs-v'),
          u: grab('.group-row[data-table="group"] .cs-u'),
          wantV: cs.getPropertyValue('--fg-muted').trim(),
          wantU: cs.getPropertyValue('--fg').trim(),
        };
      });
      expect(inv.v.length, '拆分恒产(「统一」组也拆, invert 组同)').toBeGreaterThan(0);
      expect(inv.u.length).toBeGreaterThan(0);
      const invertBad = [];
      const wantV = parseRgb(inv.wantV);
      const wantU = parseRgb(inv.wantU);
      for (const s of inv.v) {
        const g = parseRgb(s.raw);
        if (!wantV || !g || wantV.join(',') !== g.join(',')) invertBad.push(`.cs-v ${s.cls}: 期望 ${wantV} 实得 ${g}`);
      }
      for (const s of inv.u) {
        const g = parseRgb(s.raw);
        if (!wantU || !g || wantU.join(',') !== g.join(',')) invertBad.push(`.cs-u ${s.cls}: 期望 ${wantU} 实得 ${g}`);
      }
      expect(invertBad, `invert 改写逐元素明细:\n${invertBad.join('\n')}`).toEqual([]);
    });
  });
}
