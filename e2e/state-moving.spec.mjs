// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { withVm } from './lib/vm.mjs';

/**
 * 种子搬迁态 moving 的状态呈现(2026-10-29) ——
 *
 * 为什么需要它: qbittorrent-api 的 TorrentState.MOVING **不属于任何谓词集合**
 * (is_downloading/is_uploading/is_complete/is_checking/is_errored/is_stopped 全都不含),
 * 此前被 `views.py::state_kind` 兜底成 other ⇒ 主表显示「其他」, 而抽屉徽章直译 qB 原始 state
 * 显示「移动中」——同一颗种子两处打架。修复把它升格为第 7 档 kind=moving。
 *
 * pytest 侧钉的是**静态面**(后端分类 / 前后端两张 rank 表一致 / 命令闸门前后端同表 / CSS
 * 令牌 parity); 本用例钉的是**渲染面** —— 那四处各自 drills:
 *   ①行状态文案「移动中」+ 行类 `.s-moving`(走 kind 渲染);
 *   ②分布条与筛选 chip 出现 moving(distSegments 的 order 漏了 ⇒ 既统计不到也筛不到);
 *   ③点击 chip 能按 moving 筛(`kindFilter` 路径);
 *   ④CSS 真算出色值(三皮肤各有一套 `.k-*` / `.s-*`, 漏一套就掉回默认色 —— 只能靠浏览器验)。
 *
 * 桩态注入(D4 第①类 evaluate, 走 withVm 单点): 桩服务 ui_harness._STATES 不含 moving
 * (为此给桩加一个模式维度不划算), 我们把**末行**改成 moving —— 合成数据里 added_on 最大者
 * 排在最前(见 ui_harness._inject_site_alerts 的同款取位注释), 保证在首屏窗口内可见。
 * !桩的轮询每 2s 用服务端数据复原 ⇒ 注入后立刻断言, 不在这中间加长等待。
 */

/** rgb()/rgba()/#hex -> [r,g,b], 用于「令牌值 vs 计算色」比对(令牌可能 hex, 计算值恒 rgb)。 */
const parseRgb = (s) => {
  const str = String(s || '').trim();
  const m = str.match(/rgba?\(([^)]+)\)/);
  if (m) return m[1].split(',').map((x) => parseFloat(x));
  const h = str.match(/^#([0-9a-f]{6})$/i);
  if (h) return [0, 2, 4].map((i) => parseInt(h[1].slice(i, i + 2), 16));
  return null;
};

for (const skin of SKINS) {
  test.describe(`搬家中(moving)状态呈现 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`移动中: 行文案 · 分布/筛选 · 配色 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 种子页平铺视图: 一行一粒种子, 行类 `.torrent-row.s-<kind>`
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 注入 moving 桩态: state = 原始串(闸门判据读它), kind = 后端分类结果(渲染读它)
      const hash = await withVm(page, `
        const list = vm.torrents || [];
        const t = list[list.length - 1];
        if (!t) throw new Error('vm.torrents 为空(桩数据没起来)');
        t.state = 'moving'; t.kind = 'moving';
        return t.hash;
      `);
      expect(hash, '注入目标应有 hash(window 化行按 hash 定位)').toBeTruthy();

      const row = page.locator(`.torrent-row[data-hash="${hash}"]`);
      await expect(row, '注入的 moving 行应落在首屏窗口内').toBeVisible({ timeout: 5_000 });

      // ① 行类名 + 状态列文案: 此前这里是「其他」
      await expect(row).toHaveClass(/s-moving/, { timeout: 5_000 });
      await expect(row.locator('.state-text')).toHaveText('移动中', { timeout: 5_000 });

      // ② 分布条 + 筛选 chip(distSegments order 的产物 —— 缺表 = 统计/筛选双瞎)
      const seg = page.locator('.dist-bar span.k-moving');
      await expect(seg, '分布条应出现 moving 段').toHaveCount(1, { timeout: 5_000 });
      const chip = page.locator('.dist-legend button.dist-chip.k-moving');
      await expect(chip, '状态筛选器应出现「移动中」可选项').toHaveCount(1, { timeout: 5_000 });
      await expect(chip).toContainText('移动中');

      // ③ 点击 chip 按 moving 筛选: 筛完之后留下的应是这一类行
      await chip.click();
      await expect(chip).toHaveClass(/active/, { timeout: 5_000 });
      const shown = page.locator('.torrent-row');
      await expect(shown, '筛选后应只剩 moving 行').toHaveCount(1, { timeout: 5_000 });
      await expect(page.locator(`.torrent-row[data-hash="${hash}"]`)).toBeVisible();
      await chip.click();  // 复原取消筛选(后续门控与 companion 用例不受影响)

      // ④ 配色: .k-moving 的计算色必须等于 --blue 令牌(不是落回默认前景色)
      const [ token, computed ] = await page.evaluate(() => {
        const root = getComputedStyle(document.documentElement);
        const el = document.querySelector('.dist-bar span.k-moving');
        return [root.getPropertyValue('--blue').trim(), el ? getComputedStyle(el).color : ''];
      });
      expect(computed, '.k-moving 元素应已渲染').toBeTruthy();
      const a = parseRgb(token), b = parseRgb(computed);
      expect(b, `计算色无法解析: ${computed}`).not.toBeNull();
      if (a) {
        expect(b.slice(0, 3), `.k-moving 应取 --blue(${token}), 实得 ${computed}`)
          .toEqual(a.map((n) => Math.round(n)));
      }
    });
  });
}
