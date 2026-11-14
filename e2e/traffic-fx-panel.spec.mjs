// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS, SKINS_ALL } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { readInst } from './lib/vm.mjs';

/**
 * 动效数值面板的**真浏览器**冒烟链 —— plan 26-11-12-1139 §05.9 面板九项里 P7 覆盖矩阵判给
 * e2e 的那几面(第 5/6/9 项在本文件, 第 3 项「预览拍不动数据」在 traffic-fx-frames.spec.mjs;
 * 静态/电池面已由 test_webui_static_dom_panel_traffic 的收层电池 section 5 与面板接线电池
 * 覆盖, 本 spec 不重复)。
 *
 * 悬停零等待面(§05.9 零回归面)的承接: traffic-gap-zones.spec.mjs 的悬停零等待
 * 回读原样复跑(本计划不改其路径), 另由本文件 Alt 例的「面板在场时指针链」承接面板不拦
 * pointer 的那一半 —— 两处合起来覆盖该零回归面。
 *
 * 为什么要有真机面: 电池能钉「接线在位/公式正确」, 钉不到这几类只有真渲染才暴露的事实:
 *   · 收层顺序(§05.9 第 5 项): Esc 退栈链是 document 级 keydown + 面板根 @keydown.esc 两套
 *     机制的**接力** —— 面板可见才拦(fxEsc), 不可见放行给退栈链; 七处登记的可见性翻转是否
 *     真的把「一次 Esc 只关一层」串对了, 只有真按键能验。退栈顺序 = drawerMenu -> fxPanel
 *     -> drawer(lifecycle._onEscKey 的分支序)。
 *   · 不遮挡(§05.9 第 6 项): openFxPanel 的钳位(host 右缘内缩 8px)与 fitInViewport 的
 *     底边不出视口, 是 getBoundingClientRect 的实测面 —— 电池只钉了常量与调用行。
 *     「与绘图区相交是既定代价」, 本 spec **不作不相交断言**(§05.9 原文)。
 *   · 四皮肤(§05.9 第 9 项): 四套各开一次, rect 断言 + 滑杆可用(改值落到 AQB_FX_CFG)。
 *   · Alt 看穿(§05.1): fx-alt 类切换是 window keydown/keyup 两路监听 + pointer-events:none
 *     的 CSS 组合 —— 穿透的真判据是**画布收到了鼠标**(hoverIdx 随移动变化), 只有真指针能验。
 *   · .ctx-menu 计数不变(§05.9 第 6 项零回归面): 面板不是 .ctx-menu —— e2e/drawer-merge
 *     的 strict-mode 计数靠「面板不进该选择器」成立, 这里显式钉住。
 *
 * 桩口径(traffic-gap-zones.spec 同款纪律): 只翻 qb_traffic_enabled 一个比特, 其余放行真值;
 * /api/traffic/qb/torrent/* 造一份真契约形状的**恒定**帧(60 桶, 桶值不变) —— 恒定数据下
 * 每拍零变化静默(_qbBeatStart 首行判 prev==target 即归位, 零 rAF), 图完全静止, 面板几何
 * 不被动画扰动。interval_s 给 30(轮询 30s 一拍), 用例在两拍之间收尾, 轮询不进断言窗。
 */

const N = 60;
const INTERVAL = 30;

/** 造一帧恒定 payload(全桶有观测, 值恒定 -> 节拍静默, 图静止)。契约同 /api/traffic/qb/* */
function makePayload(base) {
  const points = new Array(N).fill(null);
  const totals = new Array(N).fill(null);
  for (let i = 0; i < N; i++) {
    const t = base + i * INTERVAL;
    points[i] = { t, dl: 2000, up: 1000 };
    totals[i] = { t, dl: 2000, up: 1000 };
  }
  return {
    points,
    totals,
    limits: [],
    meta: {
      window: '24h',
      interval_s: INTERVAL,          // 30 -> 轮询 30s 一拍, 断言窗内无第二拍
      source: 'qb',
      stale: false,
      // 远在链末桶之前 -> _qbSeamHint 出 null, 不给「数据接缝中」行(本 spec 不验接缝)
      server_started_at: base - 3600,
    },
  };
}

/** flags 桩: 只翻 qb_traffic_enabled 这一个比特, 其余放行真值(traffic-gap-zones 同款) */
async function stubFlags(page) {
  await page.route('**/api/webui/flags', async (route) => {
    const json = await (await route.fetch()).json();
    return route.fulfill({ json: { ...json, qb_traffic_enabled: true } });
  });
}

/** 流量帧桩: 静态基准一次算定, 每次请求回同一帧(恒定数据 -> 节拍静默) */
async function stubTraffic(page) {
  const base = Math.floor(Date.now() / 1000 / INTERVAL) * INTERVAL - (N - 1) * INTERVAL;
  await page.route('**/api/traffic/qb/torrent/*', (route) => route.fulfill({ json: makePayload(base) }));
}

/** 打开种子流量页签(traffic-gap-zones.openTorrentTraffic 同款: 30分 一并验重拉) */
async function openTorrentTraffic(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  await drawer.locator('.drawer-tabs button', { hasText: /^流量$/ }).click();
  await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
  await drawer.locator('.hist-summary .qb-tabs button', { hasText: '30分' }).click();
  await expect.poll(async () => readInst(page, 'vm.qbTorrentWindow'),
    { message: 'qbSetWindow 未生效(窗口不是 30m)', timeout: 15_000 }).toBe('30m');
  return drawer;
}

/** 图区右键 -> 面板在场且唯一(每条用例的公共前缀) */
async function openFxPanelByRightClick(page, host) {
  await host.click({ button: 'right' });
  const panel = page.locator('.fx-panel');
  await expect(panel).toBeVisible({ timeout: 5_000 });
  await expect(panel, '图区右键必须恰好开出一个面板(重复右键不得叠第二份)').toHaveCount(1);
  return panel;
}

/* ============================================================================ */

test.describe('动效数值面板 · 开层与计数面(prism/atlas)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 图区右键开出唯一面板, .ctx-menu 计数前后不变(面板不是菜单) @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTraffic(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      const host = drawer.locator('.qb-chart-host');
      const menu = page.locator('.ctx-menu');

      await expect(menu, '开面板前不得有右键菜单在场').toHaveCount(0);
      const panel = await openFxPanelByRightClick(page, host);
      await expect(menu, '面板打开后 .ctx-menu 计数必须不变(0) —— 面板不是 .ctx-menu, ' +
        'e2e/drawer-merge 的 strict-mode 计数靠这一点成立').toHaveCount(0);
      await expect(panel).toHaveAttribute('role', 'dialog');
      await expect(panel).toHaveAttribute('aria-label', '动效数值');

      /* 换个落点再右键一次: 仍只有一份(幂等重开, 不叠加 —— §09「图区右键只有一个面板」) */
      await host.click({ button: 'right', position: { x: 60, y: 40 } });
      await expect(page.locator('.fx-panel')).toHaveCount(1);
      await expect(page.locator('.fx-panel')).toBeVisible();
      await expect(menu).toHaveCount(0);
    });
  }
});

test.describe('动效数值面板 · 收层顺序(prism/atlas)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] Esc 只关面板(焦点在页面) -> 再按 Esc 才轮到抽屉; 点空白只收面板 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTraffic(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      const host = drawer.locator('.qb-chart-host');
      await openFxPanelByRightClick(page, host);

      /* 1. 焦点不在面板内(右键不转移焦点) -> Esc 走 document 退栈链: fxPanel 分支只关面板 */
      await page.keyboard.press('Escape');
      await expect.poll(() => readInst(page, 'vm.fxPanel.visible'), {
        message: 'Esc 后面板可见态必须翻 false(退栈链 fxPanel 分支)',
        timeout: 5_000,
      }).toBe(false);
      await expect(drawer, '一次 Esc 只关一层: 抽屉必须仍开着').toBeVisible();
      /* 退场过渡(fx-pop 120ms)结束后面板 DOM 摘除 */
      await expect(page.locator('.fx-panel')).toHaveCount(0, { timeout: 2_000 });

      /* 2. 第二次 Esc 才轮到抽屉 */
      await page.keyboard.press('Escape');
      await expect(drawer).not.toBeVisible({ timeout: 5_000 });

      /* 3. 点空白只收面板(七处登记的 lifecycle _onDocClick 分支): 重开面板后点导航页签
       *    (当前页重按 = 无副作用落点, 在面板与图宿主之外) */
      await page.dblclick('.torrent-row >> nth=0', { force: true });
      await expect(drawer).toBeVisible({ timeout: 5_000 });
      await drawer.locator('.drawer-tabs button', { hasText: /^流量$/ }).click();
      await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
      await openFxPanelByRightClick(page, host);
      await page.click('nav.tabs [data-view="torrents"]');
      await expect.poll(() => readInst(page, 'vm.fxPanel.visible'), {
        message: '点空白后面板必须收层(_onDocClick 名单)',
        timeout: 5_000,
      }).toBe(false);
      await expect(drawer, '点空白只收浮层, 抽屉不动').toBeVisible();
      await expect(page.locator('.fx-panel')).toHaveCount(0, { timeout: 2_000 });
    });

    test(`[${skin}] 退栈顺序三层: 菜单先退 -> 面板后退 -> 抽屉最后 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTraffic(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      const host = drawer.locator('.qb-chart-host');
      const menu = page.locator('.ctx-menu');
      await openFxPanelByRightClick(page, host);

      /* 右键页签栏开抽屉菜单(drawer-merge 同款手势): 菜单与面板并存, .ctx-menu 计数 1 */
      await drawer.locator('.drawer-tabs').click({ button: 'right' });
      await expect(menu).toHaveCount(1);
      await expect(menu).toBeVisible();
      await expect.poll(() => readInst(page, 'vm.fxPanel.visible'),
        { message: '菜单开着时面板必须仍在场(两层并存)', timeout: 5_000 }).toBe(true);

      /* Esc 三连: 菜单 -> 面板 -> 抽屉(lifecycle._onEscKey 分支序: drawerMenu 先于 fxPanel) */
      await page.keyboard.press('Escape');
      await expect(menu, '第一下 Esc 必须先退菜单(后开先关的同族序: 菜单最上层)').toHaveCount(0, { timeout: 5_000 });
      await expect.poll(() => readInst(page, 'vm.fxPanel.visible'),
        { message: '退菜单那次 Esc 不得连带关面板', timeout: 5_000 }).toBe(true);
      await expect(drawer).toBeVisible();

      await page.keyboard.press('Escape');
      await expect.poll(() => readInst(page, 'vm.fxPanel.visible'),
        { message: '第二下 Esc 退面板', timeout: 5_000 }).toBe(false);
      await expect(drawer, '第二下 Esc 不得连带关抽屉').toBeVisible();

      await page.keyboard.press('Escape');
      await expect(drawer, '第三下才轮到抽屉').not.toBeVisible({ timeout: 5_000 });
    });

    test(`[${skin}] 焦点在面板控件内按 Esc: 面板根 keydown 拦截, 同一次 Esc 不推进抽屉 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTraffic(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      const host = drawer.locator('.qb-chart-host');
      const panel = await openFxPanelByRightClick(page, host);

      /* 点「高级」折叠的 summary: 原生可聚焦元素, 焦点落进面板 -> keydown.esc 走面板根的
       * fxEsc(stopPropagation + preventDefault), document 退栈链收不到这次按键 */
      await panel.locator('.fx-adv summary').click();
      await page.keyboard.press('Escape');
      await expect.poll(() => readInst(page, 'vm.fxPanel.visible'), {
        message: '焦点在面板内按 Esc 必须只关面板(fxEsc 单层)',
        timeout: 5_000,
      }).toBe(false);
      await expect(drawer, 'fxEsc 拦截后同一次按键不得推进抽屉退栈').toBeVisible();
      await page.keyboard.press('Escape');
      await expect(drawer).not.toBeVisible({ timeout: 5_000 });
    });
  }
});

test.describe('动效数值面板 · 字段贯通与 Alt 看穿(prism/atlas)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 滑杆/下拉改值贯通 AQB_FX_CFG 与 localStorage; 面板 opacity <= 0.97 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTraffic(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      const panel = await openFxPanelByRightClick(page, drawer.locator('.qb-chart-host'));

      /* §05.9 不遮挡项的透明度面: 面板本体 opacity .97(不抢图注意力), computed 实测 <= 0.97。
       * 先 poll 到入场过渡(fx-pop 120ms, opacity 0 -> .97)走完再断言, 免得断在半程。 */
      await expect.poll(async () =>
        Number(await panel.evaluate((el) => getComputedStyle(el).opacity)), {
        message: '面板入场过渡未到位(opacity 未到 .97 档)', timeout: 3_000,
      }).toBeGreaterThanOrEqual(0.96);
      const opacity = Number(await panel.evaluate((el) => getComputedStyle(el).opacity));
      expect(opacity, '面板 opacity 必须 <= 0.97(§05.9), 实测 ' + opacity).toBeLessThanOrEqual(0.971);

      /* 滑杆: 显示 0-100 / 存储 0-1(量纲换算单点 fxRange) -> fx + CFG + localStorage 三处同值 */
      const impact = panel.locator('.fx-row', { hasText: '冲击幅度' }).locator('input[type="range"]');
      await impact.fill('40');
      await expect.poll(() => readInst(page, 'window.AQB_FX_CFG && window.AQB_FX_CFG.impact'), {
        message: '滑杆改值必须贯通 window.AQB_FX_CFG(40 -> 0.4)',
        timeout: 5_000,
      }).toBe(0.4);
      const stored = await page.evaluate(() => {
        try { return JSON.parse(localStorage.getItem('autoqb.ui.qbFx') || 'null'); } catch { return null; }
      });
      expect(stored && stored.impact, '滑杆 @change 必须落盘 autoqb.ui.qbFx(impact=0.4)').toBe(0.4);

      /* 下拉(高级折叠内的竖扫回声行程): fxPick 枚举面, 字符串值原样贯通 */
      await panel.locator('.fx-adv summary').click();
      const echo = panel.locator('.fx-row', { hasText: '竖扫回声行程' }).locator('select');
      await echo.selectOption('100');
      await expect.poll(() => readInst(page, 'window.AQB_FX_CFG && window.AQB_FX_CFG.echoSpan'), {
        message: '下拉改值必须贯通 window.AQB_FX_CFG(echoSpan="100")',
        timeout: 5_000,
      }).toBe('100');
    });

    test(`[${skin}] Alt 看穿: fx-alt 类 + pointer-events none + 指针真穿透到画布(hoverIdx 跟手) @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTraffic(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      const host = drawer.locator('.qb-chart-host');
      const hoverIdx = () => readInst(page, 'vm.qbTorrentHoverIdx');

      /* 右键开面板: 落点取宿主中央(宽度不定, 定值可能落进左轴槽)。面板被 fitInViewport
       * 钳进视口后, 顶缘可以比点击点(甚至图宿主顶)高 —— 移动落点必须取「面板盒 x 图宿主
       * 绘图区(u-over)」的交叠带: 面板盖住的那块画布才是穿透判定的落点面。 */
      const hb = await host.boundingBox();
      if (!hb) throw new Error('图宿主取不到盒(.qb-chart-host boundingBox 为空)');
      await host.click({ button: 'right', position: { x: hb.width / 2, y: 120 } });
      const panel = page.locator('.fx-panel');
      await expect(panel).toBeVisible({ timeout: 5_000 });
      const box = await panel.boundingBox();
      if (!box) throw new Error('面板取不到盒(.fx-panel boundingBox 为空)');
      const over = drawer.locator('.qb-chart-host .u-over');
      const ob = await over.boundingBox();
      if (!ob) throw new Error('uPlot 交互层取不到盒(.u-over boundingBox 为空)');
      const ya = Math.min(Math.max(box.y + 20, ob.y + 10), ob.y + ob.height - 20);
      const xa = box.x + 80;
      const xb = box.x + 30;
      expect(ya, '面板与绘图区必须相交(交叠带才有穿透落点 —— 落点选不出来说明布局前提变了)')
        .toBeLessThan(Math.min(box.y + box.height, ob.y + ob.height));

      /* 1. 基线: 面板拦截指针 —— 右键的 mouseup 已把 uPlot 光标清掉(实测 hoverIdx 归 -1),
       *    面板内移动不进画布, hoverIdx 冻结。捕获这个冻结值作对照(不硬钉 -1: 复位与否是
       *    uPlot 内部行为, 看穿判定只依赖「Alt 前后差值」)。 */
      await page.mouse.move(xa, ya);
      const frozen = await hoverIdx();

      /* 2. 按住 Alt: fx-alt 类 + pointer-events none, 指针穿透 -> 画布收到 mousemove,
       *    hoverIdx 落到面板下方那个桶并跟手(两落点相距 50px 约 4 桶, 必不同桶)。 */
      await page.keyboard.down('Alt');
      await expect.poll(() => readInst(page, 'vm.fxPanel.alt'), {
        message: 'Alt keydown 必须把 fxPanel.alt 翻 true', timeout: 5_000,
      }).toBe(true);
      await expect(panel).toHaveClass(/fx-alt/);
      const pe = await panel.evaluate((el) => getComputedStyle(el).pointerEvents);
      expect(pe, 'Alt 态 pointer-events 必须为 none(§05.1 看穿)').toBe('none');
      await page.mouse.move(xb, ya);
      const h2 = await hoverIdx();
      expect(h2, `Alt 态面板内移动必须穿透到画布(hoverIdx 落桶, 基线 ${frozen})`).toBeGreaterThanOrEqual(0);
      expect(h2, '穿透落点必须不同于冻结基线(否则画布根本没收到 move)').not.toBe(frozen);
      await page.mouse.move(xa, ya);
      const h3 = await hoverIdx();
      expect(h3, 'Alt 态继续移动 hoverIdx 必须跟手(两落点不同桶)').not.toBe(h2);

      /* 3. 松开 Alt: 恢复拦截(pointer-events 回 auto)。恢复判定不钉「hoverIdx 冻结在末值」
       *    —— Chrome 在类摘除重渲染后会派发伪 mousemove 边界事件, uPlot 对 u-over 的
       *    mouseleave 会把光标清成 -1(实测), 钉冻结值必碎; 恢复的可操作判据是面板外画布点
       *    重新跟手(指针链健康)。 */
      await page.keyboard.up('Alt');
      await expect.poll(() => readInst(page, 'vm.fxPanel.alt'), {
        message: 'Alt keyup 必须把 fxPanel.alt 翻回 false', timeout: 5_000,
      }).toBe(false);
      await expect(panel, '松开 Alt 后 fx-alt 类必须摘除').not.toHaveClass(/fx-alt/);
      const pe2 = await panel.evaluate((el) => getComputedStyle(el).pointerEvents);
      expect(pe2, '松开 Alt 后 pointer-events 必须恢复(auto)').toBe('auto');
      await page.mouse.move(ob.x + 40, ya);
      const h4 = await hoverIdx();
      expect(h4, '恢复后面板外画布点必须重新跟手(指针链健康)').toBeGreaterThanOrEqual(0);
    });
  }
});

test.describe('动效数值面板 · 四皮肤 rect 实测(§05.9 第 6/9 项)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS_ALL) {
    test(`[${skin}] 右缘钳位(距图宿主右缘 >= 8px) / 底边不出视口 / 宽 320 / 滑杆可用 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTraffic(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      const host = drawer.locator('.qb-chart-host');

      /* 右键点贴图宿主右下角: 钳位面才真正吃到 —— openFxPanel 的
       * x = min(点击x, host.right - 8 - 320) 与 fitInViewport 的底边钳位都只在贴边时生效 */
      const hb = await host.boundingBox();
      if (!hb) throw new Error('图宿主取不到盒(.qb-chart-host boundingBox 为空)');
      await host.click({ button: 'right', position: { x: hb.width - 10, y: hb.height - 10 } });
      const panel = page.locator('.fx-panel');
      await expect(panel).toBeVisible({ timeout: 5_000 });
      const vh = page.viewportSize().height;
      const bottomInViewport = async () => {
        const pb = await panel.boundingBox();
        return pb ? pb.y + pb.height <= vh - 6 : false;
      };
      /* $nextTick 实测重钳位(_qbFxRefit)在开层后一拍内完成 -> poll 到 rect 条件恒定 */
      await expect.poll(async () => {
        const pb = await panel.boundingBox();
        if (!pb) return false;
        const widthOk = Math.abs(pb.width - 320) <= 1;
        const rightOk = pb.x + pb.width <= hb.x + hb.width - 8 + 0.5;   // 右缘距宿主右缘 >= 8px
        const bottomOk = pb.y + pb.height <= vh - 6;                    // 底边不出视口(留 2px 量测余量)
        const topOk = pb.y >= 0;
        return widthOk && rightOk && bottomOk && topOk;
      }, { message: '面板 rect 必须满足: 宽 320 / 右缘距图宿主右缘 >= 8px / 底边不出视口', timeout: 5_000 })
        .toBe(true);

      /* 展开高级折叠(改变面板实高的 refit 触发面, S4-b 评审 major1 的回归面): fxRefitSoon
       * 必须把底边重新钳回视口内 —— 无 @toggle 钳位时高度 +190px 而位置不动, 此处必红
       * (Vue 缺模板处理器只 console.warn, e2e rect 是这条生产行为的行为面回归闸) */
      await panel.locator('.fx-adv summary').click();
      await expect.poll(bottomInViewport, {
        message: '展开高级后面板底边必须仍在视口内(details @toggle -> fxRefitSoon 重钳位 —— §05.9)',
        timeout: 5_000,
      }).toBe(true);

      /* 滑杆可用(§05.9 第 9 项): 四皮肤下改值都贯通 CFG —— 面板不是摆设 */
      const impact = panel.locator('.fx-row', { hasText: '冲击幅度' }).locator('input[type="range"]');
      await impact.fill('60');
      await expect.poll(() => readInst(page, 'window.AQB_FX_CFG && window.AQB_FX_CFG.impact'), {
        message: skin + ' 皮肤下滑杆必须可用(改值贯通 AQB_FX_CFG)', timeout: 5_000,
      }).toBe(0.6);
      await expect(page.locator('.ctx-menu')).toHaveCount(0);
    });
  }
});
