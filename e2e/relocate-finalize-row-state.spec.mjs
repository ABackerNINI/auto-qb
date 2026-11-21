// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS, SKINS_ALL } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { withVm } from './lib/vm.mjs';

/**
 * 收尾窗种子行迁移状态细化(B3-4, 计划 26-11-21-1600 D8) ——
 *
 * pytest 侧钉的是投影函数面(finalize_state 纯派生矩阵 + member_relocate.finalize 档位,
 * test_webui_relocate_visibility)与词值面 node 探针(relocateRowStateText, 同文件 +
 * test_webui_relocate_pop); 本 spec 钉**真浏览器接线面**: 收尾窗三态在种子行的呈现面
 * (行状态词 = 悬停浮窗 verdict 槽, 与抽屉迁移状态行消费 decorate.relocateRowStateText
 * 同一单点):
 *   1. armed + qB 最后已知离线 -> 「qB 下线等改写窗」(finalize=await_window);
 *   2. rewritten(journal 合并态)-> 「已改写待回连核验」(finalize=await_recheck);
 *   3. done -> 「收尾完成(新保存路径 <dst>)」(新保存路径取既有账面 dst, 零新增)。
 * 数据面(vm 探针)先钉桩->标注派生链(mgr._last_conn_ok=False -> status_snapshot()
 * .connected -> _relocate_member.finalize), 呈现面走悬停浮窗真手势(relPopEnter 120ms
 * 调度, 真机装配与 relocate-foreign-notification 同款纪律)。
 *
 * 桩面: ui_harness._inject_relocate_jobs 灌 6 个 job —— i=1 armed / i=7 rewritten(src/dst
 * 用独立路径 Set003/Relocated3, 不与 i=0..2 的 Set000/Relocated 共值, relocate-pair-filter
 * 的位置集计数断言不被新 pair 行冲掉)/ i=3 done+穷尽账; 桩置 qB 断开(mgr._last_conn_ok=
 * False, 收尾窗场景同真, 状态徽标显「qB 断开」—— 全库 e2e 无状态徽标断言, 已核对零冲突)。
 * 行状态断言读**桩侧稳定态**(标注首轮 rebuild_views 即带, 无 route 改写翻腿 —— 坑档
 * route-leg-flip-incremental-polling 的翻腿空转形态不适用: 本 spec 无 A/B 状态翻转腿)。
 * 行定位: 行挂 :data-hash(桩 hash = f"{i:040x}", 不用名称 hasText —— 行 textContent 跨格
 * 拼接不可靠); 手势与既有 relocate spec 同款 —— 键盘激活「添加于」表头切升序把注入行
 * (i=0..7 added_on 最旧)拉进行窗口, hover 前显式滚入 + 双 rAF 渲染沉降(scroll 即关监听
 * 会掐挂起的 120ms 调度)。
 * 四皮肤矩阵(SKINS_ALL): 钉 rewritten 态(本批新增面)全皮肤; 其余两态按 SKINS 双皮肤先例。
 */

const hashOf = (i) => i.toString(16).padStart(40, '0');
const rowOf = (page, i) => page.locator(`.torrent-row[data-hash="${hashOf(i)}"]`);
const cellOf = (row) => row.locator('.g-save-path', { hasText: 'Downloads' });

/** 滚入 + 双 rAF 渲染沉降(relocate-pop-terminal 同款纪律): hover 自带 scrollIntoView 的
 * scroll 事件若在 mouseenter 之后送达, 会经「滚动即关」监听把挂起的 120ms 调度掐掉。 */
const scrollSettle = async (page, loc) => {
  await loc.scrollIntoViewIfNeeded();
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
};

/** 导航到指定皮肤的种子页并把注入行切进行窗口(真实手势; 每测试独立 goto)。 */
const gotoTorrentsSorted = async (page, skin) => {
  await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  // sticky 表头持续重排会让 Playwright 的 stability 判定超时 —— 走键盘激活(a11y 路径)
  const sortCell = page.locator('[data-table="torrent"].group-head .h-cell.hc-added_on');
  await sortCell.focus();
  await page.keyboard.press('Enter');
};

/** 悬停浮窗 verdict 断言(toPass 兜轮询重建残余竞态, relocate-pop-terminal 同款);
 * 收尾即移开鼠标走完 160ms 宽限隐藏, 给下一面一个干净起点。 */
const expectPopVerdict = async (page, pop, row, verdict) => {
  await expect(async () => {
    await expect(row).toBeVisible({ timeout: 15_000 });
    await scrollSettle(page, cellOf(row));
    await cellOf(row).hover();
    await expect(pop).toBeVisible({ timeout: 1_500 });
    await expect(pop.locator('.rp-verdict')).toHaveText(verdict);
  }).toPass({ timeout: 20_000 });
  await page.mouse.move(4, 4);
  await expect(pop).not.toBeVisible({ timeout: 5_000 });
};

for (const skin of SKINS) {
  test.describe(`收尾窗种子行迁移状态细化 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`收尾窗三态行呈现(数据面 + 悬停浮窗) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await gotoTorrentsSorted(page, skin);

      // 数据面: qB 断开桩(status.connected=false) -> 三行标注派生值就位
      await expect.poll(() => withVm(page, `return (() => {
        const rows = vm.visibleTorrents || [];
        const rel = (hh) => { const m = rows.find(x => x.hash === hh); return m && m.relocate; };
        const armed = rel('${hashOf(1)}') || {};
        const rewritten = rel('${hashOf(7)}') || {};
        const done = rel('${hashOf(3)}') || {};
        return JSON.stringify({
          qbDown: (vm.status && vm.status.connected) === false,
          armedFinalize: armed.finalize || '',
          rewrittenFinalize: rewritten.finalize || '',
          doneDst: done.dst || '',
        });
      })()`)).toBe(JSON.stringify({
        qbDown: true,
        armedFinalize: 'await_window',
        rewrittenFinalize: 'await_recheck',
        doneDst: 'R:\\Downloads\\Relocated',
      }));

      const pop = page.locator('.relpop');
      // 呈现面 1: armed + qB 离线行(i=1)浮窗 verdict = 「qB 下线等改写窗」
      await expectPopVerdict(page, pop, rowOf(page, 1), 'qB 下线等改写窗');
      // 呈现面 2: rewritten 行(i=7)浮窗 verdict = 「已改写待回连核验」+ 独立路径在场
      await expectPopVerdict(page, pop, rowOf(page, 7), '已改写待回连核验');
      // 呈现面 3: done 行(i=3)浮窗 verdict = 收尾完成词 + 既有账面 dst 作新保存路径
      await expectPopVerdict(page, pop, rowOf(page, 3), '收尾完成(新保存路径 R:\\Downloads\\Relocated)');
    });
  });
}

/** SKINS_ALL 四皮肤矩阵(B3-4 验收: 至少一态全皮肤) —— 钉 rewritten 态(本批新增面):
 * 数据面 finalize=await_recheck + 浮窗 verdict 细分词, 全皮肤同口径。 */
for (const skin of SKINS_ALL) {
  test.describe(`收尾窗行状态细化四皮肤矩阵 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`rewritten 态行呈现全皮肤 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await gotoTorrentsSorted(page, skin);
      await expect.poll(() => withVm(page, `return (() => {
        const m = (vm.visibleTorrents || []).find(x => x.hash === '${hashOf(7)}'.padStart(40, '0'));
        return m && m.relocate ? m.relocate.finalize : '';
      })()`)).toBe('await_recheck');
      await expectPopVerdict(
        page, page.locator('.relpop'), rowOf(page, 7), '已改写待回连核验',
      );
    });
  });
}
