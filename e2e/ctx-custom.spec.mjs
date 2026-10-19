// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { clickRow, openApp, openMenuTexts, tab } from './lib/gestures.mjs';

/**
 * 设置页「WebUI」卡 · 行右键菜单布局定制(W4, 计划 26-10-20-0024 D1/D8/D14–D17)。
 *
 * 静态守阵能证明模板里有这块、注册表里有那些项, 但证不了四件只有真浏览器才看得见的事:
 *   1) 面板真的把**写回的布局形状**交出去 —— 取消勾选一项 -> 全局保存 -> PUT /api/config 载荷里
 *      ctx_menu.member.hidden 含该项 id, 且 order 仍保留它的槽位(隐藏 ≠ 删除, 勾回来要归位);
 *   2) 保存后**当前标签热应用**(D8): 不刷新页面, 右键菜单里该项当场消失 —— 路径是
 *      cfgSave -> loadWebFlags -> flags.ctx_menu -> ctxItems 重新解析, 任何一环断了这里就红;
 *   3) 「恢复默认」能把它放回来(同一份往返, 方向相反);
 *   4) 面板的分区结构 = 一级 + 固定次级区(D17)、四支 tab(D15) 与两层的行数(含分隔线)。
 *
 * 桩口径: 不往 harness 的真实 config.yml 里写(那是同轮其它 spec 共用的临时文件, 改了会互相污染)。
 * 用 page.route 把 /api/config 的 PUT 拦下来 —— 记下载荷当"已落盘", GET 时把布局注回树、
 * /api/webui/flags 同步回同一份 —— 这正是真后端的往返语义(除了不真写盘), 所以能断言热应用。
 */
test.describe('设置页 · WebUI 卡右键菜单定制(W4)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 定制块: 四支 tab + 隐藏项写回 + 保存后菜单热应用 + 恢复默认`, async ({ page }) => {
      collectRuntimeErrors(page);

      /** 服务端"当前布局" —— PUT 收下的就是它, GET/幂等回放 */
      /** @type {any} */
      let layout = null;
      /** @type {any} */
      let saved = null;

      await page.route('**/api/webui/flags', (route) => route.fulfill({
        json: { skip_check_menu: true, qb_traffic_enabled: true, ctx_menu: layout },
      }));
      await page.route('**/api/config', async (route) => {
        if (route.request().method() !== 'PUT') {
          /* 读树: 真实响应 + 把"已落盘的布局"注回去(cfgSave 保存后会重拉一次树) */
          const res = await route.fetch();
          const json = await res.json();
          if (layout && json && json.tree && json.tree.config) {
            json.tree.config.web = Object.assign({}, json.tree.config.web, { ctx_menu: layout });
          }
          return route.fulfill({ json });
        }
        saved = route.request().postDataJSON();
        layout = (saved && saved.tree && saved.tree.config && saved.tree.config.web && saved.tree.config.web.ctx_menu) || null;
        return route.fulfill({ json: { changes: ['web.ctx_menu'], restart_required: [] } });
      });

      /* ---------- ① 进设置 → 「WebUI」卡: 新卡在, 定制块在, 四支 tab ---------- */
      await openApp(page, skin);
      await page.locator('nav.tabs-right button').first().click();
      await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
      await page.locator('.hb-card', { hasText: '右键菜单布局定制' }).first().click();

      const blk = page.locator('.ctx-custom');
      await expect(blk).toBeVisible({ timeout: 10_000 });
      await expect(blk.locator('.ctx-custom-tab')).toHaveCount(4);
      /* 默认 tab = 单种子(唯一有默认次级内容的一支): 一级 14 项 + 5 线, 次级 11 项 + 2 线
         —— 行数含分隔线, 与注册表逐位一致的直接读数 */
      const secTop = blk.locator('.ctx-custom-sec').nth(0);
      const secSub = blk.locator('.ctx-custom-sec').nth(1);
      await expect(secTop.locator('.ctx-custom-row')).toHaveCount(19);
      await expect(secSub.locator('.ctx-custom-row')).toHaveCount(13);
      /* 跳检开关同卡(D6): 「常规」里的那块已 hidden, 这里必须在 */
      await expect(page.locator('.hb-blk', { hasText: '跳检开关' })).toHaveCount(1);

      /* ---------- ② 取消勾选「详细信息」→ 保存: 载荷形状(隐藏但保留槽位) ---------- */
      const actbar = page.locator('.hb-actbar');
      await expect(actbar).toContainText('已与磁盘同步', { timeout: 20_000 });
      const infoRow = secTop.locator('.ctx-custom-row', { hasText: '详细信息' });
      await infoRow.locator('.ctx-custom-chk input').uncheck();
      await expect(actbar).toContainText('有改动还没保存');

      await actbar.locator('.hb-btn.primary').click();
      await expect.poll(() => saved, { message: 'PUT /api/config 未发出', timeout: 15_000 }).not.toBeNull();
      const member = saved.tree.config.web.ctx_menu.member;
      expect(member.hidden, '隐藏项没写进布局').toContain('info');
      expect(member.order, '隐藏项被从 order 里删掉了(隐藏必须保留槽位, 否则勾回来不归位)').toContain('info');
      expect(member.order).toHaveLength(19);

      /* ---------- ③ 不刷新页面, 右键菜单当场少一项(D8 热应用) ---------- */
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
      const textsHot = await openMenuTexts(page);
      expect(textsHot.some((t) => t.includes('详细信息')), `保存后菜单里「详细信息」还在: ${textsHot.join(' / ')}`).toBe(false);
      expect(textsHot.some((t) => t.includes('重命名…')), '隐藏一项把相邻项也带走了 —— 布局解析错位').toBe(true);
      await page.keyboard.press('Escape');

      /* ---------- ④ 「恢复默认」→ 保存: 项回来(D16 直接写草稿, 无二次确认框) ---------- */
      /* 回设置: hub.view 记得上次停在「WebUI」, 所以多半直接落回定制页; 万一被复位到首页,
         才走"点卡进去"那条路 —— 两条都不做特殊等待, 免得把"回得去"这件事写死在断言里 */
      await page.locator('nav.tabs-right button').first().click();
      if (!(await blk.isVisible().catch(() => false))) {
        await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
        await page.locator('.hb-card', { hasText: '右键菜单布局定制' }).first().click();
      }
      await expect(blk).toBeVisible({ timeout: 10_000 });
      saved = null;
      await blk.getByRole('button', { name: '恢复默认' }).click();
      /* 直接写草稿 = 不出确认框, 脏标记立刻回来 */
      await expect(page.locator('.modal')).toHaveCount(0);
      await expect(actbar).toContainText('有改动还没保存');
      await actbar.locator('.hb-btn.primary').click();
      await expect.poll(() => saved, { message: '恢复默认后 PUT 未发出', timeout: 15_000 }).not.toBeNull();
      expect(saved.tree.config.web.ctx_menu.member.hidden, '恢复默认后仍有隐藏项').toEqual([]);

      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
      const textsBack = await openMenuTexts(page);
      expect(textsBack.some((t) => t.includes('详细信息')), `恢复默认后菜单里没有「详细信息」: ${textsBack.join(' / ')}`).toBe(true);
      await page.keyboard.press('Escape');

      /* 收尾: 整段往返没有 JS 报错(模板编译失败/方法名笔误都会在这里现形) */
      const errs = collectRuntimeErrors(page);
      expect(errs, `运行期报错: ${errs.join(' | ')}`).toEqual([]);
    });
  }
});
