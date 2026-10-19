// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { clickRow, openApp, tab } from './lib/gestures.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst } from './lib/vm.mjs';

/**
 * Shift 连选的**手势原点**(起点)在鼠标路径上的浏览器钉轨 —— 用户实报缺陷
 * 「使用 shift 连续按后按 esc, 光标指向最后一个选择的种子, 但再次使用 shift
 * 连选时不会以光标为起点」(2026-10-19 提单, 本轮修)。
 *
 * 根因链(取证与修复见本轮守阵 tests/test_web_shortcuts.py::test_shift_anchor_unified
 * 与坑档 memory-bank/pitfalls/web-ui/overlays.md §起点③):
 *   1. Esc 走退栈链兜底 clearSelection() —— 清 selAnchor* 是**选中状态语义, 不是缺陷**
 *      (锚点与选中集合同属"选择", 一起清合理; 光标 kbCursor **不清**, 故 Esc 后光标
 *      仍指向最后选中的种子 = 用户原话);
 *   2. 鼠标五入口(组/成员/种子/剧/集)**先改写 kbCursor、再解析起点** —— 兜底链
 *      (显式锚点 → 当前光标)读到的是**刚点的行** ⇒ from==to ⇒ 区间塌成单行;
 *   3. 键盘 _kbExtend 早有"先 _selSeedAnchorFromCursor() 再 _kbMove"纪律, 鼠标路径
 *      是计划 26-10-02-0608 的覆盖缺口。
 * 修法: 五入口在改写 kbCursor **之前** Shift 限定地调 _selSeedAnchorFromCursor()
 * (手势前光标落起点; 已有有效起点不动, 法则 2 不破), 且该方法泛化为逐 kind
 * (group/member/unit)试落, 收编辅种页成员行的同根未报缺陷。
 *
 * 本 spec 钉三条(静态守阵只查源码结构, "按下去到底动不动"只能靠真实手势):
 *   T1 种子页(原报场景): 普通点击 → Shift 连选 → 同起点再扩(法则 2) → Esc
 *      → 再次 Shift 连选**必须从光标行起算**(修复前 = 只选单行);
 *   T2 辅种页成员行(同根场景, 泛化修复前恒红): Esc 后 Shift 连选成员行同样
 *      以光标为起点;
 *   T3 回归: 无 Esc 的常规路径不变(普通点击落起点 / Shift 不重置起点)。
 *
 * 断言口径: 交互走真实鼠标手势(clickRow 的 CDP 输入管线 + 5 拍落点验证, 机理见
 * lib/gestures.mjs 头注); 判据双轨 —— DOM(.selected 类, 与用户所见一致) +
 * vm 内部字段(selMembers / selAnchorMember / kbCursor, evaluate 第②类,
 * e2e/lib/vm.mjs)。Shift 分支是**并集**语义(selection.js::shiftTorrentSel:
 * 锚点→目标区间并入现有选中, 不取消已选) —— 故 Esc 后区间从空集起算, 计数即区间宽。
 */

/** 选中行数(DOM 轨, 与用户所见一致)。 */
const selCount = (page, rowSel) => page.locator(rowSel).count();

/**
 * 成员行安全落点(相对行盒偏移): 成员行**第一格就是 .m-site**(xtpl.html
 * tpl-aq-member-cells, 带 @click.stop="$root.filterFromChip('site', ...)") ——
 * clickRow 默认的行左缘 8,8 会踩站点格 ⇒ 事件被 stop 不冒泡 ⇒ onMemberClick 从不
 * 触发且列表被过滤 ⇒ 成员行消失(首跑实测: 点击后 .member-row 归零)。
 * kbd-members.spec 文件头"点行一律点名称格"同款纪律的成员行变体。
 * 改取**第二格**(.m-state, 无交互后代)左缘 +8; 偏移从 DOM 现算, 不硬编码列宽。
 * @param {import('@playwright/test').Locator} row
 * @returns {Promise<{x: number, y: number}>}
 */
const memberPoint = (row) => row.evaluate((el) => {
  const cell = el.children[1] || el;
  const cr = cell.getBoundingClientRect();
  const r = el.getBoundingClientRect();
  return { x: cr.left - r.left + 8, y: 8 };
});

/** 读取 vm 选中集合大小(内部轨, 权威在 selMembers 而非 DOM 类)。 */
const selN = (page) => readInst(page, 'vm.selMembers.length');

for (const skin of SKINS) {
  test.describe(`Shift 连选手势原点 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`种子页: Esc 后 Shift 连选以光标为起点(不以刚点的行起算) @fast (${skin})`, async ({ page }) => {
      await openApp(page, skin);
      await tab(page, 'torrents').click();
      const rows = page.locator('.torrent-row');
      await expect(rows.first()).toBeVisible({ timeout: 15_000 });

      // arrange 事实钉死: 取前 5 行 data-hash(行窗口化 ~26 行, 300 档前 5 行恒在窗口内),
      // 供"光标指向哪一行"的 vm 读数比对
      const hashes = await rows.evaluateAll((els) =>
        els.slice(0, 5).map((el) => el.getAttribute('data-hash') || ''));
      expect(hashes.every(Boolean), '前 5 行均有 data-hash').toBe(true);

      // ① 普通点击 row0: 落光标 + 落起点(普通点击不选中, 用户 2026-09-17 口径)
      await clickRow(page, rows.nth(0));
      expect(await selCount(page, '.torrent-row.selected'), '普通点击不选中').toBe(0);
      expect(await readInst(page, 'vm.kbCursor.id'), '普通点击把光标落到 row0').toBe(hashes[0]);

      // ② Shift+点击 row2: 从起点 row0 扩到 row2 = 3 行
      await clickRow(page, rows.nth(2), { modifiers: ['Shift'] });
      expect(await selCount(page, '.torrent-row.selected'), 'Shift+点 row2 = 选 row0..2').toBe(3);
      expect(await selN(page), 'selMembers 与 DOM 同宽').toBe(3);

      // ③ Shift+点击 row4: 同一起点再扩(法则 2: 扩展期间起点不动) = 0..4 共 5 行
      await clickRow(page, rows.nth(4), { modifiers: ['Shift'] });
      expect(await selCount(page, '.torrent-row.selected'), '法则 2: Shift 不重置起点, 仍从 row0 扩').toBe(5);

      // ④ Esc 清选择(退栈链兜底): 选中清空, **锚点清空**, 但光标保留在 row4
      //    —— "光标指向最后一个选择的种子"是用户原话, 这里把它钉成 arrange 事实
      await page.keyboard.press('Escape');
      expect(await selCount(page, '.torrent-row.selected'), 'Esc 后选中清空').toBe(0);
      expect(await readInst(page, 'vm.selAnchorMember'), 'Esc 清锚点(选中状态语义, 非缺陷)').toBeNull();
      expect(await readInst(page, 'vm.kbCursor.id'), 'Esc 不动光标: 仍指向最后点击的 row4').toBe(hashes[4]);

      // ⑤ 核心断言(修复前恒红): Esc 后 Shift+点击 row1 —— 起点缺失, 兜底链必须取到
      //    **手势前光标**(row4), 区间 = row1..row4 = 4 行。修复前兜底读到的是改写后的
      //    光标(row1) ⇒ from==to ⇒ 只选 1 行。
      await clickRow(page, rows.nth(1), { modifiers: ['Shift'] });
      expect(await selCount(page, '.torrent-row.selected'), 'Esc 后 Shift 连选必须以光标 row4 为起点(row1..4 = 4 行)').toBe(4);
      expect(await selN(page), 'selMembers 同宽(4)').toBe(4);

      // ⑥ 收尾: 起点已被手势前光标补上, 再 Shift+点 row3 仍从 row4 起(锚点未被 Shift 重置)
      await clickRow(page, rows.nth(3), { modifiers: ['Shift'] });
      expect(await selCount(page, '.torrent-row.selected'), '补上的起点不被 Shift 重置: row3..4 并入 = 仍 4 行').toBe(4);
      expect(await readInst(page, 'vm.selAnchorMember'), '起点仍是手势前光标 row4(法则 2)').toBe(hashes[4]);
    });

    test(`辅种页成员行: Esc 后 Shift 连选同样以光标为起点(逐 kind 试落收编的同根缺陷) @fast (${skin})`, async ({ page }) => {
      // 同根未报缺陷: _selSeedAnchorFromCursor 原按 _selContext() 单 kind(辅种页恒为
      // group)落点, 覆盖不到成员行的 member kind —— Esc 后 Shift+↓/Shift+点击成员行
      // 同样塌成单行。本轮泛化为逐 kind 试落后一并收编, 这里用真实鼠标手势钉住。
      await openApp(page, skin);
      const gRows = page.locator('.group-row[data-table="group"]');
      await expect(gRows.first()).toBeVisible({ timeout: 30_000 });

      // 展开第一组出成员行(点名称格; 桩 --groups 默认 200 ⇒ 前 200 对两两归组,
      // 300 档下第一组恒有 ≥2 个成员 —— kbd-members.spec 同款 arrange)
      await gRows.first().locator('.g-name').click({ force: true });
      const mRows = page.locator('.member-row');
      await expect(mRows.first()).toBeVisible({ timeout: 10_000 });
      expect(await mRows.count(), '第一组至少 2 个成员(连选前提)').toBeGreaterThanOrEqual(2);
      const mHashes = await mRows.evaluateAll((els) =>
        els.slice(0, 2).map((el) => el.getAttribute('data-hash') || ''));

      // ① 普通点击成员 row0(不选中, 只落光标); 落点走第二格(.m-site 是筛选格, 见 memberPoint)
      await clickRow(page, mRows.nth(0), { point: await memberPoint(mRows.nth(0)) });
      expect(await selCount(page, '.member-row.selected'), '普通点击成员不选中').toBe(0);

      // ② Shift+点击成员 row1: 从 row0 扩到 row1 = 2 行
      await clickRow(page, mRows.nth(1), { modifiers: ['Shift'], point: await memberPoint(mRows.nth(1)) });
      expect(await selCount(page, '.member-row.selected'), 'Shift+点成员 row1 = 选 row0..1').toBe(2);

      // ③ Esc: 清选中 + 清锚点, 光标保留在成员 row1
      await page.keyboard.press('Escape');
      expect(await selCount(page, '.member-row.selected'), 'Esc 后成员选中清空').toBe(0);
      expect(await readInst(page, 'vm.kbCursor.id'), 'Esc 后光标仍指成员 row1').toBe(mHashes[1]);

      // ④ 核心断言(泛化修复前恒红): Esc 后 Shift+点击成员 row0 —— 起点缺失须兜底到
      //    手势前光标(成员 row1) ⇒ 区间 row0..1 = 2 行。修复前只选 row0 单行。
      await clickRow(page, mRows.nth(0), { modifiers: ['Shift'], point: await memberPoint(mRows.nth(0)) });
      expect(await selCount(page, '.member-row.selected'), 'Esc 后成员行 Shift 连选以光标 row1 为起点(0..1 = 2 行)').toBe(2);
    });

    test(`回归: 无 Esc 的常规 Shift 路径不变(起点写入只在非 Shift 点击) @fast (${skin})`, async ({ page }) => {
      // 防"修 Esc 场景把常规路径带坏": 普通点击必须继续落起点, Shift 点击必须继续
      // **不重置**起点(法则 2) —— 这两条是 26-10-02-0608 的原始口径, 浏览器侧复核。
      await openApp(page, skin);
      await tab(page, 'torrents').click();
      const rows = page.locator('.torrent-row');
      await expect(rows.first()).toBeVisible({ timeout: 15_000 });

      await clickRow(page, rows.nth(1));
      expect(await readInst(page, 'vm.selAnchorMember'), '普通点击 row1 落起点').not.toBeNull();
      await clickRow(page, rows.nth(4), { modifiers: ['Shift'] });
      expect(await selCount(page, '.torrent-row.selected'), 'Shift 从 row1 扩到 row4 = 4 行').toBe(4);
      await clickRow(page, rows.nth(0), { modifiers: ['Shift'] });
      expect(await selCount(page, '.torrent-row.selected'), 'Shift 不重置起点: 仍从 row1 起(0..4 = 5 行)').toBe(5);
    });
  });
}
