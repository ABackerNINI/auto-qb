// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst } from './lib/vm.mjs';
import { tab, ctxItem, clickRow, openApp } from './lib/gestures.mjs';

/**
 * 站点 chip 两槽图标(计划 26-10-19-2007 S3/S6) —— 真浏览器断言。
 *
 * 静态守阵 `test_frontend_site_alert_icon_wiring` 只能钉"样式齐备 / 模板带槽 / 映射单点";
 * 本 spec 钉**数据落到行上**: 后端给了 site_alert, 前端真的画出图标; 命令回执带 truth.results
 * 时, 前端真的把"哪几个失败"落到对应行上(而不是只发一条聚合 toast)。
 *
 * 桩数据(scripts/ui_harness.py --site-alert on, 默认开):
 *   · 种子 #0: tracker_conf=None + 真实 tracker URL -> site_alert=no_site_conf(橙 i-warn)
 *   · 种子 #1: tracker_health_msg 非空           -> site_alert=tracker_error(红 i-x-circle)
 *   两者同属第 0 组 ⇒ 组行的两个 chip 上能**同时**看到两种告警(位置即语义, R5)。
 *
 * 右槽(命令结果): 命令泵对 reannounce 回执带 truth.results(与后端 check_pending 同形),
 * 其中 site_alert=tracker_error 的行判"拒绝" —— 于是"3 个目标、1 个被拒"可复现:
 * 只有失败行出现红叉, 其余两行绿勾; 聚合 toast 文案与改动前逐字一致。
 */

const NO_CONF_TITLE = '站点未在配置中';
const TRACKER_MSG = '由本地系统中止网络连接。';
/* 右槽寿命(计划 D7): 成功 10s / 失败 180s —— 用例只验 until 差值(真等 180s 没有意义) */
const OK_MS = 10_000;
const ERR_MS = 180_000;

for (const skin of SKINS) {
  test.describe(`站点 chip 两槽图标 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`左槽: 缺配置与 tracker 报错各就各位(title 为后端给出的字符串) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openApp(page, skin); // 默认分组视图: 组行 = 每成员一个 chip

      const noConf = page.locator('.site-chip .sa.sa-no_site_conf');
      const tracker = page.locator('.site-chip .sa.sa-tracker_error');
      await expect(noConf.first(), '缺站点配置的 chip 应出现左槽告警').toBeVisible({ timeout: 30_000 });
      // title 在落 DOM 时被 ui_feedback.js 迁成 data-aq-tip(原生气泡退役), 断言后者
      await expect(noConf.first()).toHaveAttribute('data-aq-tip', NO_CONF_TITLE);
      await expect(tracker.first(), 'tracker 报错的 chip 应出现左槽告警').toBeVisible({ timeout: 15_000 });
      await expect(tracker.first()).toHaveAttribute('data-aq-tip', TRACKER_MSG);

      // 同一组行里两种告警可并存(两槽互不覆盖的口径同样适用于同类告警的两个 chip)
      const row = page.locator('.group-row[data-table="group"]').filter({ has: tracker.first() }).first();
      await expect(row.locator('.site-chip .sa')).toHaveCount(2);

      // 种子页平铺行同一口径(三处站点 cell 都接了槽)
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await expect(page.locator('.torrent-row .site-chip .sa-no_site_conf').first()).toBeVisible({ timeout: 15_000 });
      await expect(page.locator('.torrent-row .site-chip .sa-tracker_error').first())
        .toHaveAttribute('data-aq-tip', TRACKER_MSG);
    });

    test(`右槽: 3 个目标 1 个被拒 —— 仅失败行红叉、其余绿勾, 聚合 toast 文案不变 (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openApp(page, skin);
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 桩把两态注在**末尾两个**种子上(added_on 最大 = 默认序最前), 行窗口化下必然被渲染
      const picked = /** @type {string[]} */ (await readInst(page, `(() => {
        const rows = vm.visibleTorrents || [];
        const active = rows.filter((r) => r.kind === 'seeding' || r.kind === 'downloading');
        const bad = active.find((r) => r.site_alert === 'tracker_error');
        if (!bad) return [];
        const others = active.filter((r) => r.hash !== bad.hash).slice(0, 2);
        return [bad.hash, ...others.map((r) => r.hash)];
      })()`));
      expect(picked.length, '窗口内应能挑到 1 个报错目标 + 2 个健康活跃目标').toBe(3);
      const [badHash] = picked;

      for (const h of picked) {
        await clickRow(page, page.locator(`.torrent-row[data-hash="${h}"]`), { modifiers: ['Control'] });
      }
      expect(await readInst(page, 'vm.selMembers.length'), 'Ctrl+click 选中 3 行').toBe(3);

      // 右键选中行 -> 批量菜单 -> 强制重新汇报(真实手势)
      await clickRow(page, page.locator(`.torrent-row[data-hash="${badHash}"]`), { button: 'right' });
      await ctxItem(page, '强制重新汇报').click();

      // 逐目标结果落到行上: 失败 1 行(红叉) / 成功 2 行(绿勾)
      const errIcon = page.locator('.site-chip .sx.sx-error');
      const okIcon = page.locator('.site-chip .sx.sx-ok');
      await expect(errIcon, '失败行出现红叉').toHaveCount(1, { timeout: 30_000 });
      await expect(okIcon, '其余两行出现绿勾').toHaveCount(2, { timeout: 15_000 });
      // 红叉必须落在被拒的那一行上(不是随便某行)
      await expect(page.locator(`.torrent-row[data-hash="${badHash}"] .site-chip .sx-error`)).toHaveCount(1);

      // 寿命按 D7: 成功 10s / 失败 180s(读 until 差值, 不真等 180s)
      const spans = await readInst(page, `(() => {
        const out = {};
        for (const [h, v] of Object.entries(vm.alertIcons)) out[h] = { kind: v.kind, ms: v.until - Date.now() };
        return out;
      })()`);
      expect(Object.keys(spans).sort()).toEqual([...picked].sort());
      expect(spans[badHash].kind, '被拒目标是 error').toBe('error');
      expect(spans[badHash].ms, `失败图标寿命应≈${ERR_MS}ms`).toBeGreaterThan(ERR_MS - 15_000);
      for (const h of picked) {
        if (h === badHash) continue;
        expect(spans[h].kind, '健康目标是 ok').toBe('ok');
        expect(spans[h].ms, `成功图标寿命应≈${OK_MS}ms`).toBeGreaterThan(0);
        expect(spans[h].ms).toBeLessThanOrEqual(OK_MS);
      }

      // 聚合 toast 文案与改动前逐字一致(成功/失败/未确认三桶 + 首条原因)
      const toasts = await readInst(page, 'vm.toasts.map((t) => t.text).join("\\n")');
      expect(toasts).toContain('强制重新汇报: 成功 2, 失败 1, 未确认 0');
      expect(toasts).toContain('失败: tracker 未接受汇报(not working)');
    });
  });
}
