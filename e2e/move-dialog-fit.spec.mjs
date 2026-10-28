// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { clickRow, ctxItem, openApp } from './lib/gestures.mjs';

/**
 * 设定位置对话框守阵 —— 几何(2026-10-19 首修) + 提交语义与过渡(2026-10-29 二修)。
 *
 * 缺陷机理(首修): 保存路径组合框是本表单的**最后一项**, 而下拉朝下开(`.add-pop { top: calc(100% + 4px) }`)
 * ⇒ 整条菜单必然伸到 `.add-dialog-body`(overflow-y:auto 滚动容器)底沿之外: ①被 body 裁掉,
 * 伸出部分还把 body 的 scrollHeight 撑大(实测 123→383); ②`_fitAddPop` 的净空算式量的是「输入行 →
 * body 可见底沿」, 行贴底沿时净空为负, `avail > 0` 门恒不生效 ⇒ 限高兜底也失效。修法 = 根元素按
 * movePathMenu 挂 `.pop-open` + 三皮肤 body 预留 padding-bottom 272px。
 *
 * 二修(2026-10-29 用户报「点下拉框中的选项就触发移动」+「窗口太小, 点下拉框高度跳变」):
 * ①**点选只回填**: 移动只由「设定位置」按钮或手输回车发起(moveApplyPath 不再调 submitMoveDialog);
 * ②**窗口基线 360px**: 收层态原实测 243px(一句说明 + 一个输入框 = 小个子), 三皮肤 min-height 抬到
 *    `min(360px, calc(100vh - 120px))`, 动作条 margin-top:auto 钉底;
 * ③**高度走过渡**: 预留改 `transition: padding-bottom 200ms`(原先 0↔272 硬切 = 一次开/收跳 272px),
 *    高度 360→515 平滑长高、收层平滑回落;
 * ④**打开不自动展开**: 只聚焦(openMoveDialog 置 moveSuppressOpen), 点输入框/方向键才展开 ——
 *    否则「第一眼」是开层态, 一按 Esc 就塌回小窗口, 跳变被放大成两次。
 *
 * 断言口径(量 containment 不量位移 —— 居中弹窗增高时上下对半扩, 量推下量只有真实增量一半,
 * 见 pitfalls/web-ui/dialog-measure):
 *   ①打开即收层态: 下拉未展开、高度 ≥ 基线 360、body 零滚动、空路径按钮置灰;
 *   ②点输入框展开: ResizeObserver 采样到**严格介于基线与终值之间的中间高度**(证明是过渡不是瞬跳),
 *     终值增量 > 120px, 下拉完整落在框内、列表未被限高截断、前 6 项真实可点;
 *   ③Esc 收层: 高度平滑回落到基线(±8px), body 仍零滚动;
 *   ④点选候选: 对话框仍在 + 输入框回填 + **零写请求**; 点「设定位置」才发一次写请求并关窗。
 */

/**
 * 等对话框子树内全部 CSS 动画/过渡跑完再量几何 —— .modal 的 modal-in 带 scale(.985),
 * 量在动画进行中会把 rect 压小(实测关态宽 856 vs 稳态 860)。
 * @param {import('@playwright/test').Locator} loc
 */
const settleAnim = (/** @type {import('@playwright/test').Locator} */ loc) =>
  loc.evaluate((el) => Promise.all(el.getAnimations({ subtree: true }).map((a) => a.finished.catch(() => {}))));

/** 量当前几何: 高度/滚动/下拉包含性/前 6 项可点/按钮禁用态。 */
const geom = (page) => page.evaluate(() => {
  const d = document.querySelector('.modal.move-dialog');
  const body = d.querySelector('.add-dialog-body');
  const row = d.querySelector('.add-input-row');
  const pop = d.querySelector('.pop-menu.add-pop');
  const list = d.querySelector('.add-pop-list');
  const items = list ? [...list.querySelectorAll('.pop-item')] : [];
  const db = body.getBoundingClientRect();
  const rb = row.getBoundingClientRect();
  const btn = d.querySelector('.modal-actions .bt.primary');
  const input = d.querySelector('#move-path');
  // 前 6 项中心点命中: 旧缺陷态第 3 项起被 .modal-actions / 遮罩盖住(elementFromPoint 落空)
  const hits = items.slice(0, 6).map((el) => {
    const b = el.getBoundingClientRect();
    const at = document.elementFromPoint(Math.round(b.left + b.width / 2), Math.round(b.top + b.height / 2));
    return { isItem: !!at && (at === el || el.contains(at)) };
  });
  return {
    w: Math.round(d.getBoundingClientRect().width),
    h: Math.round(d.getBoundingClientRect().height),
    popOpen: !!pop,
    popBelowBody: list ? Math.round(list.closest('.add-pop').getBoundingClientRect().bottom - db.bottom) : null,
    bodyScroll: body.scrollHeight - body.clientHeight,
    modalScroll: d.scrollHeight - d.clientHeight,
    listH: list ? Math.round(list.getBoundingClientRect().height) : 0,
    itemCount: items.length,
    rowBottomGap: Math.round(db.bottom - rb.bottom),  // 开层后行底到 body 底沿的预留量
    btnDisabled: !!(btn && btn.disabled),
    inputValue: input ? input.value : "",
    hits,
  };
});

/** 挂 ResizeObserver 采样对话框高度序列(过渡的中间态只能这样抓, 事后量只有终值)。 */
const samplerOn = (page) => page.evaluate(() => {
  const d = document.querySelector('.modal.move-dialog');
  const arr = [];
  window.__moveH = arr;
  const ro = new ResizeObserver(() => arr.push(Math.round(d.getBoundingClientRect().height)));
  ro.observe(d);
  window.__moveRO = ro;
});

const samplerOff = (page) => page.evaluate(() => {
  const ro = window.__moveRO;
  if (ro) ro.disconnect();
  return window.__moveH || [];
});

for (const skin of SKINS) {
  test.describe(`设定位置对话框 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`收层态基线 360 · 点输入框才展开 · 高度走过渡不跳变 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await openApp(page, skin);
      await clickRow(page, page.locator('.group-row').first(), { button: 'right' });
      await expect(page.locator('.ctx-menu')).toBeVisible();
      await ctxItem(page, '设定位置').click();

      const dlg = page.locator('.modal.move-dialog');
      const pop = dlg.locator('.pop-menu.add-pop');
      await expect(dlg).toBeVisible();
      await settleAnim(dlg);

      // —— ① 打开即收层态(2026-10-29 二修): 不自动展开 + 基线 360 + 空路径按钮置灰
      const closed0 = await geom(page);
      expect(closed0.popOpen, '打开对话框不应自动展开下拉(否则第一眼开层态, 一按 Esc 就塌 = 跳变)').toBe(false);
      expect(closed0.w, '设定位置对话框宽度(860 宽档, 与添加种子同宽)').toBe(860);
      expect(closed0.h, '收层态基线 360px(原实测 243px = 用户报的「窗口太小」)').toBeGreaterThanOrEqual(358);
      expect(closed0.bodyScroll, '收层态 body 无滚动').toBeLessThanOrEqual(0);
      expect(closed0.btnDisabled, '空路径时「设定位置」按钮应置灰(按钮是唯一鼠标提交路径)').toBe(true);

      // —— ② 点输入框展开: 高度必须是**过渡**过来的(采到中间态), 终值含 272 预留
      await samplerOn(page);
      await page.locator('#move-path').click();
      await expect(pop.locator('.pop-item').first()).toBeVisible({ timeout: 10_000 });
      await page.waitForTimeout(450);  // 过渡 200ms + settle 重测 240ms
      await settleAnim(dlg);

      const open = await geom(page);
      const samples = await samplerOff(page);
      const mids = samples.filter((h) => h > closed0.h + 8 && h < open.h - 8);
      expect(open.popOpen, '点输入框后下拉应展开').toBe(true);
      expect(mids.length, '高度必须经过渡到达(采样到中间态); 一步到位 = 跳变回归').toBeGreaterThan(0);
      expect(open.h - closed0.h, '开层增量应≈预留 272(基线 360 → 515)').toBeGreaterThan(120);
      expect(open.popBelowBody, '下拉底缘不得超出 body 客户区底沿').toBeLessThanOrEqual(0);
      expect(open.bodyScroll, '开层后 body 无新增滚动').toBeLessThanOrEqual(0);
      expect(open.modalScroll, '开层后 modal 自身无新增滚动').toBeLessThanOrEqual(0);
      expect(open.listH, '列表未被限高截断(≤210 证明 settle 后净空算式无需兜底)').toBeLessThanOrEqual(211);
      expect(open.itemCount, '桩 300 种子应给出足量候选(足够溢出 210px 列表)').toBeGreaterThan(20);
      expect(open.rowBottomGap, '开层后输入行下方应有预留空间(≈272px)').toBeGreaterThan(200);
      for (const [i, h] of open.hits.entries()) {
        expect(h.isItem, `下拉第 ${i} 项应真实可点(不被动作条/遮罩盖住)`).toBe(true);
      }

      // —— ③ Esc 只收下拉不关对话框: 高度平滑回落到基线
      await page.keyboard.press('Escape');
      await expect(pop).toBeHidden();
      await page.waitForTimeout(350);
      await settleAnim(dlg);
      const closed1 = await geom(page);
      expect(Math.abs(closed1.h - closed0.h), '收层后高度应回到基线(±8px)').toBeLessThanOrEqual(8);
      expect(closed1.w, '收层后宽度不变').toBe(860);
      expect(closed1.bodyScroll, '收层后 body 无新增滚动').toBeLessThanOrEqual(0);
    });

    test(`点选候选只回填 · 点「设定位置」才移动 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      // 写请求计数: 单种子/单组/多选都落在 /api/torrents/bulk(action=location); 回执走 cmd 轮询
      let writes = 0;
      await page.route('**/api/torrents/bulk', async (route) => {
        writes += 1;
        await route.fulfill({ json: { cmd_id: 'e2e-move-cmd' } });
      });
      await page.route('**/api/cmd/e2e-move-cmd', (route) => route.fulfill({ json: { status: 'ok' } }));

      await openApp(page, skin);
      await clickRow(page, page.locator('.group-row').first(), { button: 'right' });
      await expect(page.locator('.ctx-menu')).toBeVisible();
      await ctxItem(page, '设定位置').click();

      const dlg = page.locator('.modal.move-dialog');
      const pop = dlg.locator('.pop-menu.add-pop');
      await expect(dlg).toBeVisible();
      await page.locator('#move-path').click();
      const first = pop.locator('.pop-item').first();
      await expect(first).toBeVisible({ timeout: 10_000 });
      const picked = (await first.innerText()).trim();

      // —— 点选候选 = 只回填 + 收面板, 不移动(2026-10-29 报障「点选项就触发移动」)
      await first.click();
      await expect(pop).toBeHidden();
      await expect(dlg).toBeVisible();
      const afterPick = await geom(page);
      expect(afterPick.inputValue, '点选候选应把路径回填到输入框').toBe(picked);
      expect(writes, '点选候选不得发写请求(移动只由按钮/回车发起)').toBe(0);
      expect(afterPick.btnDisabled, '有路径后按钮应可用').toBe(false);

      // —— 点「设定位置」才真正移动
      await dlg.locator('.modal-actions .bt.primary').click();
      await expect.poll(() => writes, { timeout: 10_000 }).toBe(1);
      await expect(dlg).toBeHidden();
    });
  });
}
