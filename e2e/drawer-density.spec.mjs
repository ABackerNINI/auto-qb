// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 抽屉密度档端到端验收(计划 26-10-11-2106 W5, D2 拍板 A) —— 15 个过程式变体退役后,
 * 「换版式」能力收敛为每页签 2 档的声明式密度档(经典 / 紧凑), 本 spec 钉两条验收线:
 *
 * 1. 旧变体 id 显式迁移(升级不破坏): localStorage 预置旧变体 id(混 tall/low/脏值) →
 *    页面启动**不报错**, 读侧 autoqb.ui.drawerTpl 经 DENSITY_REG.normalize 一次性归一:
 *    tall(01/04/07/10/13)→classic、low/collapsed→compact、白名单外脏值→classic。
 *    档位在 DOM 的生效事实 = 描述符消费: 密度类 dd-compact 挂组件根(.dt-host), 结构开关
 *    raw/hint 是模板 v-if **真隐藏**(general 的 details.drawer-raw / content 的
 *    .drawer-toolbar-hint) —— 断言全锚可见事实, 不借道 vm。
 *    !traffic 页签不在本 spec: 流量页签按钮 v-if=qbTrafficOn 受功能门控, 桩服务默认不启用
 *    (页签不渲染); traffic 的 legacy 迁移与 tierOf 由静态守阵的 node 电池
 *    (_DT_DENSITY_NODE_PROBE)钉住。
 *
 * 2. 右键切档 + 刷新持久化: 右键正文 → 菜单选「紧凑」→ 档位即时生效; dtPersistSel 单漏斗
 *    写回 localStorage(autoqb.ui.drawerTpl), 刷新后读侧归一路径原样生效(仍紧凑)。
 *    再选回「经典」→ 反向过渡 + 持久化, 页签记忆互不牵连(general 动, content 不动)。
 *
 * 页签切换用页签栏按钮(hasText 锚文案); 单栏下当前页签宿主用 `:visible` 取
 * (四页签组件恒在 DOM, v-show 门控显隐 —— 类断言对隐藏元素也成立, 但逐页签断言只认可见者)。
 */

const WIDE = { width: 2560, height: 1200 };
const TPL_KEY = 'autoqb.ui.drawerTpl';

async function openDrawer(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  await page.waitForTimeout(300);
  return drawer;
}

async function gotoApp(page, skin) {
  await page.setViewportSize(WIDE);
  await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
}

async function pickTab(page, drawer, name) {
  await drawer.locator('.drawer-tabs button', { hasText: name }).click();
  await page.waitForTimeout(300);
  return drawer.locator('.drawer-body .dt-host:visible');
}

async function tplStore(page) {
  return page.evaluate((key) => JSON.parse(localStorage.getItem(key) || '{}'), TPL_KEY);
}

for (const skin of SKINS) {
  test.describe(`抽屉密度档 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`旧变体 id 预置: tall→classic / low→compact / 脏值→classic, 无报错 @fast (${skin})`, async ({ page }) => {
      /* 预置覆盖三个迁移去向各至少一枚 + 一枚脏值: general=01(tall→classic),
       * trackers=06(low→compact), peers=zz(脏值→classic), content=10(tall→classic)。
       * 任一页签启动报错 / 静默丢档(runtime error guard + 下方 DOM 断言)即红。
       * (traffic=14 的腿不在 e2e: 流量页签受 qbTrafficOn 门控, 见头注。) */
      collectRuntimeErrors(page);
      await page.addInitScript((val) => {
        localStorage.setItem('autoqb.ui.drawerTpl', val);
      }, JSON.stringify({ general: '01', trackers: '06', peers: 'zz', content: '10' }));
      await gotoApp(page, skin);
      const drawer = await openDrawer(page);

      // general(01→classic): 原始键值区在(raw=true), 根无密度类
      const genHost = await pickTab(page, drawer, /^常规$/);
      await expect(genHost, '01 迁 classic: 根无密度类').not.toHaveClass(/dd-compact/);
      await expect(drawer.locator('.drawer-body details.drawer-raw'), 'classic 档原始键值区在').toBeVisible();

      // trackers(06→compact): 根挂 dd-compact
      const trkHost = await pickTab(page, drawer, /^Tracker$/);
      await expect(trkHost, '06 迁 compact: 根挂密度类').toHaveClass(/dd-compact/);

      // peers(zz→classic): 白名单外脏值回落 classic, 不报错
      const peerHost = await pickTab(page, drawer, /^用户$/);
      await expect(peerHost, '脏值回落 classic: 根无密度类').not.toHaveClass(/dd-compact/);

      // content(10→classic): 工具条提示行在(hint=true)
      await pickTab(page, drawer, /^内容$/);
      await expect(drawer.locator('.drawer-body .drawer-toolbar-hint'), 'classic 档提示行在').toBeVisible();
    });

    test(`右键切档 + 刷新持久化 + 回切 @fast (${skin})`, async ({ page }) => {
      /* 默认全 classic → 右键正文选「紧凑」→ 即时生效(dd-compact + 结构开关 v-if 真隐藏)且
       * 写盘; 刷新后经读侧归一原样恢复(持久化单漏斗 dtPersistSel)。再回切「经典」→ 反向 +
       * 写盘; 期间不动其他页签的档位(content 记忆保持 classic = 列记忆互不影响在单栏的投影)。 */
      collectRuntimeErrors(page);
      await gotoApp(page, skin);
      const drawer = await openDrawer(page);

      // 默认 classic: general 原始键值区在
      const genHost = drawer.locator('.drawer-body .dt-host:visible');
      await expect(drawer.locator('.drawer-body details.drawer-raw')).toBeVisible();

      // 右键 → 选「紧凑」→ 即时生效
      await drawer.locator('.drawer-body').click({ button: 'right' });
      const menu = page.locator('.ctx-menu');
      await expect(menu).toBeVisible();
      await menu.locator('.ctx-item', { hasText: '紧凑' }).click();
      await expect(genHost, '紧凑档: 组件根挂 dd-compact').toHaveClass(/dd-compact/, { timeout: 5_000 });
      await expect(drawer.locator('.drawer-body details.drawer-raw'), '紧凑档: 原始键值区 v-if 真隐藏')
        .toHaveCount(0);
      // 写盘: general=compact, 且不得牵连其他页签
      let store = await tplStore(page);
      expect(store.general, '切档必须写盘').toBe('compact');
      expect(store.content, '切 general 档不得牵连 content 记忆').toBe('classic');

      // 刷新 → 重开: 持久化生效(读侧归一原样恢复紧凑档)
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer2 = await openDrawer(page);
      const genHost2 = drawer2.locator('.drawer-body .dt-host:visible');
      await expect(genHost2, '刷新后紧凑档必须恢复').toHaveClass(/dd-compact/, { timeout: 5_000 });
      await expect(drawer2.locator('.drawer-body details.drawer-raw')).toHaveCount(0);

      // 回切经典: 右键 → 「经典」→ 密度类移除 + 原始键值区回来 + 写盘 classic
      await drawer2.locator('.drawer-body').click({ button: 'right' });
      await expect(menu).toBeVisible();
      await menu.locator('.ctx-item', { hasText: '经典' }).first().click();
      await expect(genHost2, '回切经典: 密度类移除').not.toHaveClass(/dd-compact/, { timeout: 5_000 });
      await expect(drawer2.locator('.drawer-body details.drawer-raw'), '回切经典: 原始键值区回来')
        .toBeVisible();
      store = await tplStore(page);
      expect(store.general, '回切必须写盘').toBe('classic');
    });
  });
}
