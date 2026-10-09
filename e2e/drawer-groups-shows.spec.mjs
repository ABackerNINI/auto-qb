// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 辅种页 / 追剧页支持种子详情面板(计划 26-10-08-1217) —— 补 e2e 断言钉住三视图一体化。
 *
 * 为什么需要它: 面板原先被两处守卫锁在种子页(`drawerVisible` 的 `viewMode === "torrents"` 与
 * `openTorrentDrawer` 首行同款守卫)。辅种页/追剧页的成员行右键菜单**早已**复用单种子菜单
 * (menu.hash 分支含「详细信息」), 菜单项渲染、hash 正确, 点下去却因守卫**静默失效** ——
 * 不报错、不提示、什么也不发生, 静态守阵看不出这类「点了没反应」, 只能靠真实手势。
 *
 * 覆盖三条:
 *   1. 辅种页: 展开组 -> 成员行双击 -> 面板打开且头部标题 = 该成员种子名;
 *   2. 追剧页: 展开剧 -> 展开集 -> 成员行双击 -> 面板打开;
 *   3. 三视图共用槽位: 面板在辅种页打开后切到种子页, 面板**不随切视图消失**(状态保持语义,
 *      与既有跨页保持同口径); 切到设置页则退场(drawerVisible 只认主内容页)。
 *
 * 断言口径: 真实手势(click / dblclick), 不借道 vm。整表 2s 重渲染会抢点击 ⇒ 双击一律 force
 * (与 drawer-peers.spec / drawer-dock-stability.spec 同款)。
 */

for (const skin of SKINS) {
  test.describe(`辅种/追剧页种子详情面板 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`辅种页成员行双击打开详情面板 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 展开第一组(左键单击 = 展开明细), 等成员行出现。
      // !点**名称格**而非行中心: 行中心多半落在站点/标签挂件上(挂件 @click.stop 走筛选, 不展开)。
      await page.locator('.group-row').first().locator('.g-name').click({ force: true });
      const member = page.locator('.member-row').first();
      await expect(member).toBeVisible({ timeout: 10_000 });

      // 成员行双击: 面板必须打开(此前静默失效)
      // 成员行的 :data-hash 是断言"目标是被双击的这一行"的依据(明细表无名称列, 不能按名比对)
      const wantHash = await member.getAttribute('data-hash');
      expect(wantHash, '成员行必须带 data-hash(面板目标断言依赖它)').toBeTruthy();

      await member.dblclick({ force: true });
      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer, '辅种页成员行双击必须打开详情面板(此前被视图守卫静默吞掉)')
        .toBeVisible({ timeout: 5_000 });

      // 面板头部标题非空(drawerTitle 取 memberByHash 本地记录, 切换瞬间即正确 —— 不得是空/hash 占位)
      const title = (await drawer.locator('.drawer-title').first().innerText()).trim();
      expect(title.length, `面板头部标题="${title}" 不得为空`).toBeGreaterThan(0);
      expect(title, `面板标题不得退化成裸 hash(拿到的是 "${title}")`).not.toMatch(/^[0-9a-f]{40}$/i);
    });

    test(`追剧页集明细成员行双击打开详情面板 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await page.click('nav.tabs [data-view="shows"]');
      await expect(page.locator('.show-row').first()).toBeVisible({ timeout: 30_000 });

      // 展开剧 -> 展开集 -> 等成员行(同样点名称格 .ep-name, 避开集行的站点挂件)
      await page.locator('.show-row').first().locator('.g-name').click({ force: true });
      const epRow = page.locator('.ep-row').first();
      await expect(epRow).toBeVisible({ timeout: 10_000 });
      await epRow.locator('.ep-name').click({ force: true });
      const member = page.locator('.member-row').first();
      await expect(member).toBeVisible({ timeout: 10_000 });

      await member.dblclick({ force: true });
      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer, '追剧页集明细成员行双击必须打开详情面板(此前被视图守卫静默吞掉)')
        .toBeVisible({ timeout: 5_000 });
    });

    test(`面板跨视图保持 / 切设置页退场 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      await page.locator('.group-row').first().locator('.g-name').click({ force: true });
      const member = page.locator('.member-row').first();
      await expect(member).toBeVisible({ timeout: 10_000 });
      await member.dblclick({ force: true });

      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 5_000 });

      // 切到种子页: 面板**保持**(三视图共用槽位, 状态位不随切视图翻)
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await expect(drawer, '三视图共用槽位: 切到种子页面板必须保持')
        .toBeVisible({ timeout: 5_000 });

      // 切到设置页: 面板**退场**(drawerVisible 只认主内容页, 设置页不得浮着一张面板)。
      // 设置入口是顶栏里含 .ico-config 图标的按钮(@click="openSettings"), 无 data-page 属性。
      await page.locator('button', { has: page.locator('.ico-config') }).first().click();
      await expect(drawer, '切到设置页面板必须退场(停靠落点只存在于主内容页)')
        .toHaveCount(0, { timeout: 5_000 });
    });
  });
}
