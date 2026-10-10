// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { CMD_RESULT, requireMode } from './lib/mode.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst } from './lib/vm.mjs';
import { tab, clickRow, openApp, openMenuTexts, pickRows, bulkTap, groupActionTap, torrentActionTap } from './lib/gestures.mjs';
import { armScopeAudit, readScopeRing, expectScopeRingClean, injectScopeDeviation } from './lib/scope_ring.mjs';

/**
 * 触发点 × 选中态 一致性参数化矩阵(计划 26-10-10-2001 S5, 第三张网之「真浏览器矩阵」)。
 *
 * 用户动议的四类场景逐位落地, 每条断言**三层**(计划 §5.4):
 *   ① 下发载荷 —— 拦截 POST, 比对目标集合与期望闭包(真实 UI 手势驱动, 不借道 vm 注入动作;
 *      evaluate 只用第①类注入桩态 / 第②类读内部埋点, D4 守则见 lib/vm.mjs 头注);
 *   ② 审计环为空 —— scope_ring.expectScopeRingClean(载荷对 ≠ 还要"说谎为零");
 *   ③ 文案 —— toast / 菜单明示作用对象(C5 口径甲: 选中 N 项右键 = 对全部生效, 但界面明示)。
 *
 * 用例与登记表(TRIGGER_DEFS)的咬合: 场景 1–4 + 键盘覆盖 dispatch ∈ action / delete 之外的全部
 * 一级动作形态(per-skin); 场景 6 从页面读登记表(接线真浏览器探针)。新增触发点走统一出口即被
 * 场景 1–5 的审计环自动罩住; 绕开出口则 T1(静态)先红, 真浏览器侧本矩阵的环断言兜底。
 *
 * 模式门控: 主路径组只在 cmd-result ok 跑(requireMode) —— toast 成功文案断言在 error 桩下
 * 不存在(menus.spec S3 对账同款结论)。@fast 全组(「改前端必跑」门禁)。
 */

for (const skin of SKINS) {
  test.describe(`皮肤 ${skin}(触发点 × 选中态矩阵 @fast)`, () => {
    requireMode(test, { cmdResult: 'ok' });
    installRuntimeErrorGuard(test);

    test('T-1 选中A触发A: 选中2行右键锚点行 -> 批量菜单 -> 载荷==选中集合 + toast计数(选中态锚点在集合内)', async ({ page }) => {
      await openApp(page, skin);
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await armScopeAudit(page);
      const picked = await pickRows(page, 2); // [h0, h1]

      // 锚点行在选中集合内 -> 批量菜单(C5 口径甲: 菜单明示"批量", 作用对象=整个选中集合)
      await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
      const texts = await openMenuTexts(page);
      expect(texts.some((t) => t.includes('批量开始')), `应渲染批量菜单: ${texts.slice(0, 8).join(' / ')}`).toBe(true);

      const { hits, off } = bulkTap(page);
      await page.locator('.ctx-item', { hasText: '批量开始' }).first().click();
      await expect.poll(() => hits.n, { message: '应恰好 1 条 bulk POST', timeout: 8_000 }).toBe(1);
      off();
      const posted = JSON.parse(/** @type {string} */ (hits.body));
      expect(posted.action, `载荷: ${JSON.stringify(posted).slice(0, 140)}`).toBe('resume');
      expect([...posted.hashes].sort(), 'hashes == 选中集合(整份闭包, 不多不少)').toEqual([...picked].sort());
      expect(posted.keys, '纯成员选中无组 key').toEqual([]);
      // 文案层: countText 明示目标数(C5 口径甲的"界面明示作用范围")
      await expect.poll(async () => {
        const ts = await readInst(page, "(vm.toasts || []).map((t) => t.kind + '|' + t.text)");
        return (ts || []).some((s) => s.startsWith('ok|') && s.includes('(2 个目标)'));
      }, { message: '成功 toast 应含 countText「(2 个目标)」', timeout: 5_000 }).toBe(true);
      await expectScopeRingClean(page);
    });

    test('T-2 选中A触发B: 选中2行右键未选中行 -> 单目标菜单 -> 目标==锚点行(锚点不在集合内不静默扩选)', async ({ page }) => {
      await openApp(page, skin);
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await armScopeAudit(page);
      const picked = await pickRows(page, 2);

      // 锚点行(nth(5))不在选中集合 -> 单目标菜单(不是批量) —— C5 口径甲的另一侧
      const anchorRow = page.locator('.torrent-row').nth(5);
      const anchorHash = await anchorRow.getAttribute('data-hash');
      await clickRow(page, anchorRow, { button: 'right' });
      const texts = await openMenuTexts(page);
      expect(texts.some((t) => t.includes('批量开始')), `不得渲染批量菜单: ${texts.slice(0, 8).join(' / ')}`).toBe(false);
      expect(texts.some((t) => t.includes('开始该种子')), `应有单目标「开始该种子」: ${texts.slice(0, 8).join(' / ')}`).toBe(true);

      const { hits, off } = torrentActionTap(page);
      await page.locator('.ctx-item', { hasText: '开始该种子' }).first().click();
      await expect.poll(() => hits.n, { message: '应恰好 1 条单目标 POST', timeout: 8_000 }).toBe(1);
      off();
      expect(hits.action, '动作 == resume').toBe('resume');
      expect(hits.hash, '目标 == 被右键的锚点行(不静默扩到选中集合)').toBe(anchorHash);
      expect(picked, '选中集合确实与锚点无关(前置自检)').not.toContain(anchorHash);
      await expectScopeRingClean(page);
    });

    test('T-3 无选中触发C: 不选右键行 -> 单目标菜单 -> 目标==锚点行(空选中靠锚点)', async ({ page }) => {
      await openApp(page, skin);
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await armScopeAudit(page);
      // 前置自检: 无选中
      expect(await readInst(page, 'vm.selMembers.length + vm.selGroups.length'), '无选中').toBe(0);

      const anchorRow = page.locator('.torrent-row').nth(0);
      const anchorHash = await anchorRow.getAttribute('data-hash');
      await clickRow(page, anchorRow, { button: 'right' });
      const texts = await openMenuTexts(page);
      expect(texts.some((t) => t.includes('暂停该种子')), `单目标菜单: ${texts.slice(0, 8).join(' / ')}`).toBe(true);

      const { hits, off } = torrentActionTap(page);
      await page.locator('.ctx-item', { hasText: '暂停该种子' }).first().click();
      await expect.poll(() => hits.n, { message: '应恰好 1 条单目标 POST', timeout: 8_000 }).toBe(1);
      off();
      expect(hits.action, '动作 == pause').toBe('pause');
      expect(hits.hash, '目标 == 锚点行').toBe(anchorHash);
      await expectScopeRingClean(page);
    });

    test('T-4a 选中A触发A(组形态): 选中1组右键该组行 -> 单组支菜单(集合==锚点范围不升批量) -> 目标==该组', async ({ page }) => {
      await openApp(page, skin); // 默认落在分组视图
      const gRows = page.locator('.group-row[data-table="group"]');
      await expect(gRows.first()).toBeVisible({ timeout: 30_000 });
      await armScopeAudit(page);
      const groupKey = await gRows.nth(0).getAttribute('data-key');
      await clickRow(page, gRows.nth(0), { modifiers: ['Control'] });
      expect(await readInst(page, 'vm.selGroups.slice()'), 'Ctrl+click 后组选中').toEqual([groupKey]);
      const closure = await readInst(page, '[...vm.selHashSet]'); // 组选中 -> 成员闭包(selHashSet 口径)
      expect(closure.length, '组闭包非空(前置自检)').toBeGreaterThan(0);

      await clickRow(page, gRows.nth(0), { button: 'right' });
      const texts = await openMenuTexts(page);
      // C2 口径: 集合与锚点行范围一致 = 只选中了它自己 -> 单组支(不是批量菜单) —— 2026-10-10 实测锚定
      expect(texts.some((t) => t.includes('批量开始')), `单组选中不得升批量: ${texts.slice(0, 8).join(' / ')}`).toBe(false);
      expect(texts.some((t) => t.includes('开始整组')), `应有单组支「开始整组」: ${texts.slice(0, 8).join(' / ')}`).toBe(true);

      const { hits, off } = groupActionTap(page);
      await page.locator('.ctx-item', { hasText: '开始整组' }).first().click();
      await expect.poll(() => hits.n, { message: '单组 resume 应走组路径 POST', timeout: 8_000 }).toBe(1);
      off();
      expect(hits.action, '动作 == resume').toBe('resume');
      expect(hits.key, '目标 == 选中的组 key(选中与触发同指一组)').toBe(groupKey);
      await expectScopeRingClean(page);
    });

    test('T-4b 选中A触发全部: 选中2组右键锚点组 -> 批量菜单 -> bulk keys==两组(选中整份生效)', async ({ page }) => {
      await openApp(page, skin);
      const gRows = page.locator('.group-row[data-table="group"]');
      await expect(gRows.first()).toBeVisible({ timeout: 30_000 });
      await armScopeAudit(page);
      const k0 = await gRows.nth(0).getAttribute('data-key');
      const k1 = await gRows.nth(1).getAttribute('data-key');
      await clickRow(page, gRows.nth(0), { modifiers: ['Control'] });
      await clickRow(page, gRows.nth(1), { modifiers: ['Control'] });
      expect(await readInst(page, 'vm.selGroups.length'), 'Ctrl+click 两组').toBe(2);

      await clickRow(page, gRows.nth(0), { button: 'right' });
      const texts = await openMenuTexts(page);
      // 集合(2 组)比锚点行(1 组)大 -> 升级批量菜单(C5 口径甲: 选中 N 项右键 = 对全部生效)
      expect(texts.some((t) => t.includes('批量开始')), `应渲染批量菜单: ${texts.slice(0, 8).join(' / ')}`).toBe(true);

      const { hits, off } = bulkTap(page);
      await page.locator('.ctx-item', { hasText: '批量开始' }).first().click();
      await expect.poll(() => hits.n, { message: '多组应走 bulk POST', timeout: 8_000 }).toBe(1);
      off();
      const posted = JSON.parse(/** @type {string} */ (hits.body));
      expect(posted.action, `载荷: ${JSON.stringify(posted).slice(0, 140)}`).toBe('resume');
      expect([...posted.keys].sort(), 'keys == 选中的两组(整份, 不多不少)').toEqual([k0, k1].sort());
      await expectScopeRingClean(page);
    });

    test('T-5 键盘无选中走光标: 种子页光标行按S -> 目标==光标行(空选中光标兜底, C5 cursor 侧)', async ({ page }) => {
      await openApp(page, skin);
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await armScopeAudit(page);
      // 键盘光标: Seed 页直接 ↓ 建 KB 光标(kbd-members 同款真实手势)
      await page.keyboard.press('ArrowDown');
      await expect(page.locator('.torrent-row.kb-cursor'), '光标应落在种子行').toHaveCount(1, { timeout: 5_000 });
      expect(await readInst(page, 'vm.selMembers.length + vm.selGroups.length'), '无选中(纯光标)').toBe(0);
      const cursorId = await readInst(page, 'vm.kbCursor && vm.kbCursor.id');

      const { hits, off } = torrentActionTap(page);
      await page.keyboard.press('KeyS'); // 注册表 act-resume = KeyS(scope list)
      await expect.poll(() => hits.n, { message: 'KeyS 应发出 1 条单目标 POST', timeout: 8_000 }).toBe(1);
      off();
      expect(hits.action, '动作 == resume').toBe('resume');
      expect(hits.hash, '目标 == 光标行(无选中时光标才有资格当目标, C5)').toBe(cursorId);
      await expectScopeRingClean(page);
    });
  });
}

test.describe('触发矩阵: 登记表接线与审计红验(皮肤无关, 单皮肤跑 @fast)', () => {
  installRuntimeErrorGuard(test);

  test('T-6 登记表真浏览器探针: triggerDefs() 可读 + ctx-menu 四支齐(接线问题的真机侧探针)', async ({ page }) => {
    await openApp(page, 'prism');
    // 登记表经 window.AQB_TRIGGERS.methods.triggerDefs() 暴露(S2 落地形态: mixin 片段, 方法在
    // methods 层); 若清单/mixin 接线断裂, 静态守阵(T5 形状)与运行时页面会各自失明 —— 本探针
    // 把「生产页面真的读得到」钉死。
    const defs = await page.evaluate('window.AQB_TRIGGERS && window.AQB_TRIGGERS.methods && window.AQB_TRIGGERS.methods.triggerDefs && window.AQB_TRIGGERS.methods.triggerDefs()');
    expect(defs, '登记表应可从生产页面读到').toBeTruthy();
    const variants = [...new Set(defs.ui.filter((/** @type {{ui:string}} */ r) => r.ui === 'ctx-menu').map((/** @type {{variant:string}} */ r) => r.variant))].sort();
    expect(variants, 'ctx-menu 四支变体齐(multi/episode/member/group)').toEqual(['episode', 'group', 'member', 'multi']);
  });

  test('T-7 审计红验: 审计模式下故意造一次不一致 -> 环里出现记录 + warn(S4 完成判据的真机红验)', async ({ page }) => {
    await openApp(page, 'prism');
    await armScopeAudit(page);
    const probe = await injectScopeDeviation(page);
    expect(probe.dupN, '注入的重复目标载荷必须在环里留下 dup 记录(审计真的会记账)').toBe(1);
    expect(probe.warned, '首次偏差必须带 console.warn(按签名去重的 warn 一次)').toBe(true);
    // 环内偏差即 T-1..T-5 的收口断言对象 —— 红验与消费端同环, 口径自洽
    const ring = await readScopeRing(page);
    expect(ring.some((/** @type {{event:string}} */ r) => r.event === 'red-probe'), '环记录应带触发标识').toBe(true);
  });
});
