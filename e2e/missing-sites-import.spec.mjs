// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';

/**
 * 设置 → 站点 → 「导入缺失站点」三分支 GUI 回归(issue 26-11-04-2312)
 *
 * 背景: 计划 26-11-03-2337 M4 的三路径验收曾靠一次性 Playwright 脚本 + gitignore 的
 * `tests-real/.work` 证据, 仓库内只有 test_frontend_sites_import_wiring 的静态子串断言 ——
 * 改 config_hub_tracker.js 的 hubImportSites / _hubImportPerDomain 或三钮模板时, 静态断言仍绿
 * 而真实 DOM 分支已坏。本 spec 用 ui_harness 桩服务 + page.route 注入三形态载荷, 把三分支钉成
 * 可重复执行的回归。
 *
 * 三分支(代码单点 src/auto_qb/webui/static/shared/config_hub_tracker.js::hubImportSites):
 *   1. sites 空            → 「无需导入」toast, 不弹框;
 *   2. 无 >=2 域名组        → 两钮 confirmDialog(okText=导入), 逐域名各填一条;
 *   3. 存在 >=2 域名组      → 三钮 confirmThreeDialog(ok=合并导入 / extra=拆分导入 ghost / 取消),
 *                            Enter 默认 = 合并(键=groups[i].name); 拆分 = 逐域名旧路径。
 * 两条分支都只填编辑器待审 —— 全程不得 PUT /api/config(保存是用户显式动作), 本 spec 逐条计数。
 *
 * 断言口径: 文案 + 按钮类 + 默认焦点 + 请求计数 + 填入后的 pill 集合。只验文案会漏掉
 * 「文案对、按钮类/焦点/动作错」这个最容易犯的形态(smoke.md 断言设计约定)。
 *
 * 旧断言名 → 本 spec 映射:
 *   tests/test_web_backend_misc_sites.py::test_frontend_sites_import_wiring
 *     (静态子串 confirmThreeDialog( / trackers[g.name] = g.entry / 三钮模板)
 *     → 本 spec 的分支选型(分支 2 两钮 vs 分支 3 三钮)、ghost 类、默认焦点与填入 pill 行为断言;
 *       静态断言仍保留(改字即红的低成本第一层), 本 spec 是行为层回归。
 */

/** 分支 1: 后端无可导入站点(sites 空, groups 可缺省)。 */
const EMPTY = { sites: [] };

/** 分支 2: 全单元素组 —— groups 与 sites 一一对应, 不存在 >=2 域名组合并路径。 */
const SINGLE = {
  sites: [
    { name: 'e2e_alpha_io', domain: 'e2e.alpha.io', entry: { domains: ['e2e.alpha.io'] } },
    { name: 'e2e_beta_net', domain: 'e2e.beta.net', entry: { domains: ['e2e.beta.net'] } },
  ],
  groups: [
    { name: 'e2e_alpha_io', domains: ['e2e.alpha.io'], entry: { domains: ['e2e.alpha.io'] } },
    { name: 'e2e_beta_net', domains: ['e2e.beta.net'], entry: { domains: ['e2e.beta.net'] } },
  ],
};

/**
 * 分支 3: 一个 >=2 域名组 + 一个单域名组。组名刻意与全部 sites 名不同 ——
 * 合并后 pill = 组名, 拆分后 pill = 逐域名名, 两种结果集合可分辨(否则同名会让断言互相冒充)。
 */
const MULTI = {
  sites: [
    { name: 'e2e_multi_a_pt', domain: 'e2e.multi.a.pt', entry: { domains: ['e2e.multi.a.pt'] } },
    { name: 'e2e_multi_b_pt', domain: 'e2e.multi.b.pt', entry: { domains: ['e2e.multi.b.pt'] } },
    { name: 'e2e_gamma_io', domain: 'e2e.gamma.io', entry: { domains: ['e2e.gamma.io'] } },
  ],
  groups: [
    {
      name: 'e2e_multi_group',
      domains: ['e2e.multi.a.pt', 'e2e.multi.b.pt'],
      entry: { domains: ['e2e.multi.a.pt', 'e2e.multi.b.pt'] },
    },
    { name: 'e2e_gamma_group', domains: ['e2e.gamma.io'], entry: { domains: ['e2e.gamma.io'] } },
  ],
};

/**
 * 收 PUT /api/config 计数 —— 导入只填编辑器, 落盘必须留给用户显式「保存」。
 * @param {import('@playwright/test').Page} page
 * @returns {string[]} 命中过的 PUT url 列表(空 = 零落盘)
 */
function trackConfigPuts(page) {
  /** @type {string[]} */
  const puts = [];
  page.on('request', (r) => {
    if (r.method() === 'PUT' && r.url().includes('/api/config')) puts.push(r.url());
  });
  return puts;
}

/**
 * 打开设置 → 站点分区, 返回「导入缺失站点」按钮定位器。
 * @param {import('@playwright/test').Page} page
 * @param {string} skin
 */
async function openTrackers(page, skin) {
  await openApp(page, skin);
  await page.locator('nav.tabs-right button', { hasText: '设置' }).click();
  await expect(page.locator('.hb-card-t', { hasText: /^站点$/ })).toBeVisible({ timeout: 20_000 });
  await page.locator('.hb-card', { has: page.locator('.hb-card-t', { hasText: /^站点$/ }) }).click();
  const importBtn = page.locator('.hb-pill-tail button', { hasText: '导入缺失站点' });
  await expect(importBtn).toBeVisible();
  return importBtn;
}

/** 若干 pill 的可见性断言(名称逐个按 pill 文本命中)。 */
async function expectPills(page, names) {
  await expect(page.locator('.hb-pills .hb-pill')).toHaveCount(names.length);
  for (const n of names) {
    await expect(page.locator('.hb-pill', { hasText: n })).toBeVisible();
  }
}

for (const skin of SKINS) {
  test.describe(`缺失站点导入三路径 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`1. 无可导入站点: 无需导入 toast, 不弹框 @fast (${skin})`, async ({ page }) => {
      const puts = trackConfigPuts(page);
      await page.route('**/api/sites/missing', (route) => route.fulfill({ json: EMPTY }));
      const importBtn = await openTrackers(page, skin);

      await importBtn.click();

      const toast = page.locator('.toast-wrap .toast.ok');
      await expect(toast).toBeVisible({ timeout: 10_000 });
      await expect(toast).toContainText('无需导入');
      await expect(page.locator('.modal'), '无可导入项不得弹确认框').toHaveCount(0);
      // 等导入链收尾(按钮从 busy 复位)再取请求快照, 否则推迟到 toast 之后的异步保存会漏计
      await expect(importBtn).toBeEnabled();
      expect(puts, '导入不得落盘: 全程零 PUT /api/config').toEqual([]);
    });

    test(`2. 全单域名组: 两钮确认(Enter)按域名填入 @fast (${skin})`, async ({ page }) => {
      const puts = trackConfigPuts(page);
      await page.route('**/api/sites/missing', (route) => route.fulfill({ json: SINGLE }));
      const importBtn = await openTrackers(page, skin);

      await importBtn.click();

      const modal = page.locator('.modal');
      await expect(modal.locator('.modal-title')).toContainText('导入 2 个缺失站点');
      await expect(modal.locator('.modal-title')).not.toContainText('含多域名站点');
      // 两钮形态: 取消 + 导入, 不该出现第三钮(拆分只属于多域名组分支)
      await expect(modal.locator('.modal-actions .bt')).toHaveCount(2);
      const ok = modal.locator('.modal-actions .bt.primary');
      await expect(ok).toHaveText('导入');
      await expect(ok, '默认焦点必须落在确认钮(Enter = 导入)').toBeFocused();

      await page.keyboard.press('Enter');

      await expectPills(page, ['e2e_alpha_io', 'e2e_beta_net']);
      await expect(page.locator('.toast-wrap .toast.ok')).toContainText('已填入 2 个站点');
      await expect(modal, '确认后弹框必须关闭').toHaveCount(0);
      await expect(importBtn).toBeEnabled();
      expect(puts, '导入不得落盘: 全程零 PUT /api/config').toEqual([]);
    });

    test(`3. 多域名组: 三钮 + 拆分 ghost + Enter 默认合并 @fast (${skin})`, async ({ page }) => {
      const puts = trackConfigPuts(page);
      await page.route('**/api/sites/missing', (route) => route.fulfill({ json: MULTI }));
      const importBtn = await openTrackers(page, skin);

      await importBtn.click();

      const modal = page.locator('.modal');
      await expect(modal.locator('.modal-title')).toContainText('导入 3 个缺失站点(含多域名站点)');
      await expect(modal.locator('.modal-body')).toContainText('合并明细');
      const ok = modal.locator('.modal-actions .bt.primary');
      await expect(ok).toHaveText('合并导入');
      await expect(ok, '默认焦点必须落在确认钮(Enter = 合并, 推荐分支)').toBeFocused();
      const splitBtn = modal.locator('.modal-actions .bt', { hasText: '拆分导入' });
      // 拆分不丢数据 ⇒ 按次钮渲染(ghost), 不得沿用缺省的破坏性红钮
      await expect(splitBtn).toHaveClass(/\bghost\b/);
      await expect(splitBtn).not.toHaveClass(/danger-solid/);

      await page.keyboard.press('Enter');

      await expectPills(page, ['e2e_multi_group', 'e2e_gamma_group']);
      await expect(page.locator('.toast-wrap .toast.ok')).toContainText('已填入 2 组');
      await expect(page.locator('.toast-wrap .toast.ok')).toContainText('共 3 个域名');
      await expect(importBtn).toBeEnabled();
      expect(puts, '导入不得落盘: 全程零 PUT /api/config').toEqual([]);
    });

    test(`3. 多域名组: 拆分导入逐域名填入 @fast (${skin})`, async ({ page }) => {
      const puts = trackConfigPuts(page);
      await page.route('**/api/sites/missing', (route) => route.fulfill({ json: MULTI }));
      const importBtn = await openTrackers(page, skin);

      await importBtn.click();

      const modal = page.locator('.modal');
      await expect(modal.locator('.modal-title')).toContainText('含多域名站点');
      const splitBtn = modal.locator('.modal-actions .bt', { hasText: '拆分导入' });
      await expect(splitBtn).toHaveClass(/\bghost\b/);
      await splitBtn.click();

      // 拆分走逐域名旧路径: 二次两钮确认框(不是直接落编辑器)
      await expect(modal.locator('.modal-title')).toContainText('导入 3 个缺失站点');
      await expect(modal.locator('.modal-title')).not.toContainText('含多域名站点');
      await modal.locator('.modal-actions .bt.primary', { hasText: '导入' }).click();

      await expectPills(page, ['e2e_multi_a_pt', 'e2e_multi_b_pt', 'e2e_gamma_io']);
      await expect(page.locator('.hb-pill', { hasText: 'e2e_multi_group' }), '拆分不得留下合并组名')
        .toHaveCount(0);
      await expect(page.locator('.toast-wrap .toast.ok')).toContainText('已填入 3 个站点');
      await expect(importBtn).toBeEnabled();
      expect(puts, '导入不得落盘: 全程零 PUT /api/config').toEqual([]);
    });
  });
}
