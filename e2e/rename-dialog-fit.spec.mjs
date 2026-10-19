// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { clickRow, ctxItem, openApp, tab } from './lib/gestures.mjs';
import { withVm } from './lib/vm.mjs';

/**
 * 重命名对话框几何守阵(2026-10-19 用户报障「WEBUI重命名弹窗太小」)——
 *
 * 缺陷机理: 重命名对话框骑通用 .modal 基档 520px(--modal-w-base, 为确认/提示
 * 一句话设计), 而它的字段值 = **完整种子显示名** —— 真实名称 routinely 80~120
 * 字符。实测(修复前, 1440x900, 双皮肤同数): 对话框 520x226, 输入框仅 474px,
 * 97 字符长名 scrollWidth 695 > clientWidth 472 ⇒ **裁掉 223px**(近三分之一
 * 不可见, 改个名得在输入框里左右滚)。桩名 43 字符恰好不裁, 故既有冒烟从未暴露。
 *
 * 修复(ui_feedback.js + popovers.html + drawer.js + 三皮肤 CSS 成对): _openModal
 * 增 cls 附加类选项(_modalInit 单点声明, 空 = 既有对话框零变化), editRename 传
 * cls: "rename-dialog", 三皮肤 .modal.rename-dialog 宽度走 --modal-w-add(860,
 * 与设定位置/添加种子同档, ctx 菜单相邻两编辑框同宽)。静态接线由
 * test_frontend_rename_dialog_width_wiring 钉。
 *
 * 断言口径: ①对话框 860 宽档; ②真实长名(97 字符)注入后输入框零裁剪
 * (scrollWidth <= clientWidth)且输入框有足够宽(≥800px); ③预填的当前名同样
 * 不裁; ④点取消零提交(不误发 rename POST)。
 */

/**
 * 等对话框子树内全部 CSS 动画/过渡跑完再量几何 —— .modal 的 modal-in 带
 * scale(.985), 量在动画进行中会把宽度压小(实测 856 vs 稳态 860, 同一教训见
 * move-dialog-fit.spec.mjs)。
 * @param {import('@playwright/test').Locator} loc
 */
const settleAnim = (/** @type {import('@playwright/test').Locator} */ loc) =>
  loc.evaluate((el) => Promise.all(el.getAnimations({ subtree: true }).map((a) => a.finished.catch(() => {}))));

/** 97 字符真实感长名(remux 原盘长名形态; 桩名仅 43 字符, 不裁 —— 必须注入才能暴露缺陷)。 */
const LONG_NAME = 'The.Movie.Name.2023.REPACK.1080p.BluRay.REMUX.AVC.DTS-HD.MA.TrueHD.7.1.Atmos-SuperMegaGroup';

/** 量对话框 + 输入框几何(含长名注入后的裁剪量)。 */
const geom = (page) => page.evaluate(() => {
  const d = document.querySelector('.modal.rename-dialog');
  const inp = d.querySelector('.modal-field input');
  return {
    w: Math.round(d.getBoundingClientRect().width),
    inputW: Math.round(inp.getBoundingClientRect().width),
    clientW: inp.clientWidth,
    scrollW: inp.scrollWidth,
    clip: inp.scrollWidth - inp.clientWidth,   // >0 = 名称被输入框裁掉
    value: inp.value,
  };
});

for (const skin of SKINS) {
  test.describe(`重命名对话框几何 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`重命名对话框 860 宽档, 真实长名零裁剪, 取消零提交 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await openApp(page, skin);
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
      await expect(page.locator('.ctx-menu')).toBeVisible();
      await ctxItem(page, '重命名').click();

      const dlg = page.locator('.modal.rename-dialog');
      await expect(dlg).toBeVisible();
      await settleAnim(dlg);

      // —— ① 宽档: 860(--modal-w-add, 与设定位置/添加种子同档; 旧缺陷态 520 基档)
      let m = await geom(page);
      expect(m.w, '重命名对话框宽度(860 宽档; 旧缺陷态骑 520 基档)').toBe(860);

      // —— ② 预填的当前名不裁(桩名 43 字符, 旧态也恰好不裁 —— 这条只防更宽的回归)
      expect(m.clip, '预填的当前种子名不得被输入框裁掉').toBeLessThanOrEqual(0);

      // —— ③ 真实长名(97 字符)零裁剪: 旧态 520 档裁 223px; 注入 = D4 第①类桩态
      //     (名称由详情 API 预填, 桩名太短不暴露缺陷, 注入模拟真实长名种子)
      await withVm(page, 'vm.modal.fields[0].value = ' + JSON.stringify(LONG_NAME) + ';');
      await expect.poll(async () => (await geom(page)).value).toBe(LONG_NAME);
      m = await geom(page);
      expect(m.inputW, '输入框宽(860 档减内外边距; 旧态仅 474)').toBeGreaterThanOrEqual(800);
      expect(m.clip, `97 字符真实长名不得被裁(旧缺陷态裁 ${695 - 472}px)`).toBeLessThanOrEqual(0);

      // —— ④ 取消零提交: 不误发 rename POST(改的是显示名, 误提交即脏数据)
      const posts = [];
      page.on('request', (r) => {
        if (r.method() === 'POST' && /\/api\/torrents\/[^/]+\/rename(\?|$)/.test(r.url())) posts.push(r.url());
      });
      await dlg.locator('.modal-actions .bt.ghost').click();
      await expect(dlg).toBeHidden();
      expect(posts, '点取消不得提交 rename').toEqual([]);
    });
  });
}
