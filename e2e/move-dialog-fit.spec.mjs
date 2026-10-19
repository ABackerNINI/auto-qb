// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { clickRow, ctxItem, openApp } from './lib/gestures.mjs';

/**
 * 设定位置对话框几何守阵(2026-10-19 用户报障「弹窗太小, 新保存位置下拉显示不全, 需要滚动」)——
 *
 * 缺陷机理: 保存路径组合框是本表单的**最后一项**, 而下拉朝下开(`.add-pop { top: calc(100% + 4px) }`)
 * ⇒ 整条菜单必然伸到 `.add-dialog-body`(overflow-y:auto 滚动容器)底沿之外: ①被 body 裁掉,
 * 伸出部分还把 body 的 scrollHeight 撑大(实测 123→383, 弹窗体内多出一条滚动条, 用户必须滚弹窗
 * 才能用下半截下拉); ②`_fitAddPop` 的净空算式量的是「输入行 → body 可见底沿」, 行贴底沿时净空
 * 为负, `avail > 0` 门恒不生效 ⇒ 限高兜底也失效。实测(修复前, 1440x900): 对话框仅 560x243,
 * 下拉 300 候选只露出约 2 项, 第 3 项起被 .modal-actions 与遮罩盖住, elementFromPoint 全部落空。
 *
 * 修复(模板 + 三皮肤 CSS 成对): ①`.modal.move-dialog` 宽度 560(--modal-w-form) → 860
 * (--modal-w-add, 与添加种子对话框同宽, 路径项 nowrap+ellipsis 多显示); ②下拉开层时根元素挂
 * `.pop-open`(模板 `:class`), body 加 padding-bottom 272px 给下拉预留整高(面板头 ~46 + 列表
 * 210 + 顶距 4 + 余量) ⇒ 预留后净空 ≈216px > 列表 210, `_fitAddPop` 不再限高, 下拉完整落在
 * 对话框内, 弹窗体零新增滚动。对话框打开即自动聚焦输入框展开下拉(openMoveDialog: focus →
 * @focus 开层), 所以「用户第一眼」就是开层态。
 *
 * 断言口径(量 containment 不量位移 —— 居中弹窗增高时上下对半扩, 量推下量只有真实增量一半,
 * 见 pitfalls/web-ui/dialog-measure): ①自动开层态: 对话框 860 宽档, 下拉底缘不超出 body 客户区
 * 底沿, body/modal 均无新增滚动, 列表未被限高截断(≤210 证明净空算式无需兜底), 前 6 项中心点
 * elementFromPoint 命中自身(旧缺陷态第 3 项起命中 .modal-actions/遮罩 = 真实不可点);
 * ②Esc 收层态: 预留回落, 对话框缩回, body 仍零滚动; ③再点输入框重开: 包含性依旧成立。
 */

/**
 * 等对话框子树内全部 CSS 动画/过渡跑完再量几何 —— .modal 的 modal-in 带 scale(.985),
 * .pop-menu 的 drop-in 同理; 量在动画进行中会把 rect 压小(实测关态宽 856 vs 稳态 860)。
 * @param {import('@playwright/test').Locator} loc
 */
const settleAnim = (/** @type {import('@playwright/test').Locator} */ loc) =>
  loc.evaluate((el) => Promise.all(el.getAnimations({ subtree: true }).map((a) => a.finished.catch(() => {}))));

/** 量开层态几何: 下拉是否完整落在对话框内、弹窗体有无新增滚动、可见项是否真实可点。 */
const geomOpen = (page) => page.evaluate(() => {
  const d = document.querySelector('.modal.move-dialog');
  const body = d.querySelector('.add-dialog-body');
  const row = d.querySelector('.add-input-row');
  const list = d.querySelector('.add-pop-list');
  const items = [...list.querySelectorAll('.pop-item')];
  const db = body.getBoundingClientRect();
  const rb = row.getBoundingClientRect();
  // 前 6 项中心点命中: 旧缺陷态第 3 项起被 .modal-actions / 遮罩盖住(elementFromPoint 落空)
  const hits = items.slice(0, 6).map((el) => {
    const b = el.getBoundingClientRect();
    const at = document.elementFromPoint(Math.round(b.left + b.width / 2), Math.round(b.top + b.height / 2));
    return { isItem: !!at && (at === el || el.contains(at)) };
  });
  return {
    w: Math.round(d.getBoundingClientRect().width),
    popBelowBody: Math.round(list.closest('.add-pop').getBoundingClientRect().bottom - db.bottom),
    bodyScroll: body.scrollHeight - body.clientHeight,
    modalScroll: d.scrollHeight - d.clientHeight,
    listH: list.getBoundingClientRect().height,
    itemCount: items.length,
    rowBottomGap: Math.round(db.bottom - rb.bottom),  // 开层后行底到 body 底沿的预留量
    hits,
  };
});

for (const skin of SKINS) {
  test.describe(`设定位置对话框几何 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`路径下拉完整落在对话框内, 弹窗体零新增滚动 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await openApp(page, skin);
      await clickRow(page, page.locator('.group-row').first(), { button: 'right' });
      await expect(page.locator('.ctx-menu')).toBeVisible();
      await ctxItem(page, '设定位置').click();

      const dlg = page.locator('.modal.move-dialog');
      const pop = dlg.locator('.pop-menu.add-pop');
      await expect(dlg).toBeVisible();
      // 开对话框即聚焦输入框展开下拉(openMoveDialog); 候选异步到位, 等首项落袋再量
      await expect(pop.locator('.pop-item').first()).toBeVisible({ timeout: 10_000 });
      await settleAnim(dlg);

      // —— ① 自动开层态(用户第一眼): 860 宽档 + 下拉完整落在对话框内 + 零新增滚动 + 项可点
      let m = await geomOpen(page);
      expect(m.w, '设定位置对话框宽度(860 宽档, 与添加种子同宽)').toBe(860);
      expect(m.popBelowBody, '下拉底缘不得超出 body 客户区底沿(旧缺陷态恒正 ~103px)').toBeLessThanOrEqual(0);
      expect(m.bodyScroll, '开层后 body 无新增滚动(旧缺陷态 scrollHeight 123→383)').toBeLessThanOrEqual(0);
      expect(m.modalScroll, '开层后 modal 自身无新增滚动(900 视口内 515px < 780 上限)').toBeLessThanOrEqual(0);
      expect(m.listH, '列表未被限高截断(≤210 证明净空算式无需兜底)').toBeLessThanOrEqual(211);
      expect(m.itemCount, '桩 300 种子应给出足量候选(足够溢出 210px 列表)').toBeGreaterThan(20);
      expect(m.rowBottomGap, '开层后输入行下方应有预留空间(≈272px)').toBeGreaterThan(200);
      for (const [i, h] of m.hits.entries()) {
        expect(h.isItem, `下拉第 ${i} 项应真实可点(不被动作条/遮罩盖住)`).toBe(true);
      }

      // —— ② Esc 只收下拉不关对话框(onMovePathKeydown stopPropagation): 预留回落, 零滚动
      await page.keyboard.press('Escape');
      await expect(pop).toBeHidden();
      await settleAnim(dlg);
      const closed = await page.evaluate(() => {
        const d = document.querySelector('.modal.move-dialog');
        const b = d.querySelector('.add-dialog-body');
        return { w: Math.round(d.getBoundingClientRect().width), bodyScroll: b.scrollHeight - b.clientHeight };
      });
      expect(closed.w, '收层后宽度不变').toBe(860);
      expect(closed.bodyScroll, '收层后 body 无新增滚动').toBeLessThanOrEqual(0);

      // —— ③ 显式点击输入框重开: 包含性依旧成立(开层 watcher 重限高路径)
      await page.locator('#move-path').click();
      await expect(pop.locator('.pop-item').first()).toBeVisible({ timeout: 10_000 });
      await settleAnim(dlg);
      m = await geomOpen(page);
      expect(m.popBelowBody, '重开后下拉仍完整落在对话框内').toBeLessThanOrEqual(0);
      expect(m.bodyScroll, '重开后 body 仍无新增滚动').toBeLessThanOrEqual(0);
      expect(m.rowBottomGap, '重开后预留空间仍在').toBeGreaterThan(200);
      for (const [i, h] of m.hits.entries()) {
        expect(h.isItem, `重开后下拉第 ${i} 项仍可点`).toBe(true);
      }
    });
  });
}
