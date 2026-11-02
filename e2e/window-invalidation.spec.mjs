// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, TORRENTS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { INST } from './lib/vm.mjs';

/**
 * 行窗失效签名守阵(2026-11-02 关抽屉/切页卡死取证, 报告 26-11-02-0339 计划 26-11-02-0351 后续):
 * 两个根因各钉一条, 红验数字取自修复前同桩(3000 种子)实测:
 *  ①切页全量重渲: _measureRowH 的 _rowHSig 签名含 viewMode —— 每次切页把三 kind 行高全表作废,
 *    返回种子页走一轮全量渲染量齐, 实测 5.8~8.4s 长任务(用户「切标签页卡死几秒」)。
 *  ②关抽屉假 bump: 收场动画 .drawer 转 absolute(.drawer-leave-active), .drawer-body clientWidth
 *    跳 1894->1918, RO 逐帧触发 _winCtnSync 假 bump 共享的 _winResize ⇒ 下一拍 updated 钩子按签名
 *    失配作废主表行高, 3000 行全量重渲实测 5.6s 长任务(用户「关抽屉后卡死; 能滚不能点」——
 *    滚轮走合成器不进主线程, 鼠标事件被长任务饿死; 关闭前后 elementFromPoint 均干净, 无残留遮罩)。
 * 判别力门控同 perf.spec: TORRENTS>500(全量/窗口化行数差才有判别力)。
 * 皮肤口径: 本 spec 自带 flux —— 本次卡死三皮肤都报, 守阵三皮肤都进(harness SKINS 维持
 * 冒烟双皮肤既定口径不动, 逐条 spec 按需扩)。
 */

/** 本守阵的三皮肤(harness.SKINS 两皮肤 + flux)。 */
const SKINS3 = ['prism', 'atlas', 'flux'];

/** 灾难冻结粗界(同 perf W4/W5 口径 500ms; 修复前实测 5.6~8.4s, 判别力充分)。 */
const FREEZE_MS = 500;

/** longtask 探针(第②类时序探针, perf.spec 同款)。 */
const INSTALL_LT = `(() => {
  window.__lt = [];
  if (window.__po) window.__po.disconnect();
  window.__po = new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lt.push(Math.round(e.duration)); });
  window.__po.observe({ entryTypes: ['longtask'] });
})()`;

for (const skin of SKINS3) {
  test.describe(`行窗失效签名 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test('切页往返不重置行窗(签名不含 viewMode)', async ({ page }) => {
      test.skip(TORRENTS <= 500, `切页行窗断言仅种子数 >500 有判别力; 当前 E2E_TORRENTS=${TORRENTS}(默认档 300)`);
      test.setTimeout(120_000);
      collectRuntimeErrors(page);
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 20_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 30_000 });
      await page.waitForTimeout(2500); // 首访量齐全量轮 settle(设计内一次; 3000 种子实测 ~5.4s 长任务在此窗内完成)
      const total = await page.evaluate(`(async () => { const vm = ${INST}; return vm.filteredTorrents.length; })()`);
      expect(await page.locator('.torrent-row').count(), '量齐后主表窗口化(常驻 << 数据)').toBeLessThan(total * 0.5);

      await page.evaluate(INSTALL_LT);
      // 切走再切回(修复前: 切走即作废行高, 切回全量渲染 5.8~8.4s)
      await page.click('nav.tabs [data-view="shows"]');
      await page.waitForTimeout(600);
      await page.click('nav.tabs [data-view="torrents"]');
      await page.waitForTimeout(500); // 全量渲染进行中就要读数(修复后窗口化即时, 修复前 3000 行 patch 中)
      const rowsEarly = await page.locator('.torrent-row').count();
      await page.waitForTimeout(2000);

      expect(rowsEarly, `切回种子页 500ms 内即窗口化常驻(实测 ${rowsEarly}, 数据 ${total}; ` +
        `签名含 viewMode 时此处全量渲染中) `).toBeLessThan(total * 0.5);
      const lt = await page.evaluate('window.__lt || []');
      expect(Math.max(0, ...lt), `切页往返无灾难冻结(实测 longtask ${lt.join('/') || '无'}; 粗界 ${FREEZE_MS}ms)`)
        .toBeLessThan(FREEZE_MS);
      const measured = await page.evaluate(`(async () => { const vm = ${INST}; return vm._winMeasured.torrent; })()`);
      expect(measured, '切页往返后行高实测态保持(不被签名作废)').toBe(true);
    });

    test('关抽屉不假 bump 宽度代(general 与 content 两轮)', async ({ page }) => {
      test.skip(TORRENTS <= 500, `关抽屉行窗断言仅种子数 >500 有判别力; 当前 E2E_TORRENTS=${TORRENTS}(默认档 300)`);
      test.setTimeout(120_000);
      collectRuntimeErrors(page);
      await page.route('**/api/torrents/*/files', (route) => route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify([{ name: 'D/a.mkv', size: 1, progress: 1, priority: 1 },
          { name: 'D/b.mkv', size: 1, progress: 1, priority: 0 }]),
      }));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 20_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 30_000 });
      await page.waitForTimeout(2500); // 量齐轮 settle
      const total = await page.evaluate(`(async () => { const vm = ${INST}; return vm.filteredTorrents.length; })()`);
      await page.evaluate(INSTALL_LT);
      const rowPt = await page.locator('.torrent-row').first().boundingBox();
      expect(rowPt, '种子行可量测(视口内)').toBeTruthy();

      for (const round of ['general', 'content']) {
        await page.dblclick('.torrent-row >> nth=0', { force: true }); // force: 轮询重渲抢点击(smoke.md)
        const drawer = page.locator('.drawer-dock > .drawer');
        await expect(drawer).toBeVisible({ timeout: 5_000 });
        if (round === 'content') {
          await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();
          await expect(drawer.locator('.drawer-body .group-row').first()).toBeVisible({ timeout: 10_000 });
        }
        await page.waitForTimeout(800);
        const resize0 = await page.evaluate(`(async () => { const vm = ${INST}; return vm._winResize; })()`);

        await page.click('.drawer-dock .drawer-close');
        await expect(drawer).toHaveCount(0, { timeout: 5_000 }); // 面板真卸载(收场动画含 220ms 退场)
        await page.waitForTimeout(600); // 收场 RO 余波落定(修复前 bump 在此窗内发生)

        const resize1 = await page.evaluate(`(async () => { const vm = ${INST}; return vm._winResize; })()`);
        expect(resize1, `关抽屉(${round})不假 bump 宽度代: _winResize ${resize0} -> ${resize1}`).toBe(resize0);

        // 下一拍数据回合(确定性触发 updated 钩子; 修复前此处按失配签名全量重渲 3000 行 5.6s)
        await page.evaluate(`(async () => {
          const vm = ${INST};
          vm.lastRid = null;
          await vm.refresh();
          await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
        })()`);
        const rows = await page.locator('.torrent-row').count();
        expect(rows, `关抽屉(${round})后下一拍仍窗口化(实测 ${rows} 行, 数据 ${total})`).toBeLessThan(total * 0.5);
        const measured = await page.evaluate(`(async () => { const vm = ${INST}; return vm._winMeasured.torrent; })()`);
        expect(measured, `关抽屉(${round})后行高实测态保持`).toBe(true);

        // 关后鼠标可命中(elementFromPoint; 修复前长任务饿死主线程 = 用户「能滚不能点」)
        const hit = await page.evaluate(([x, y]) => {
          const el = document.elementFromPoint(x, y);
          return el ? { tag: el.tagName, inRow: !!el.closest('.torrent-row') } : null;
        }, [Math.round(rowPt.x + 8), Math.round(rowPt.y + Math.min(8, rowPt.height / 2))]);
        expect(hit && hit.inRow, `关抽屉(${round})后行上 hit-test 命中种子行(实测 ${JSON.stringify(hit)})`).toBe(true);
      }

      const lt = await page.evaluate('window.__lt || []');
      expect(Math.max(0, ...lt), `两轮关抽屉全程无灾难冻结(实测 longtask ${lt.join('/') || '无'}; 粗界 ${FREEZE_MS}ms)`)
        .toBeLessThan(FREEZE_MS);
    });
  });
}
