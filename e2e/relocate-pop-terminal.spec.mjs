// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { withVm } from './lib/vm.mjs';

/**
 * 迁移悬停浮窗终态窄放行(issue 26-11-15-0345; plan 26-11-15-0914 S3 D5/D11)——
 *
 * pytest 侧钉的是静态面(接线守阵 test_webui_relocate_pop)与 node 行为面(assembleRelPop
 * 组装矩阵 + relPopEnter 调度矩阵); 本 spec 钉**真浏览器接线面**:
 *   1. done 终态 + 穷尽恢复账余量行(桩 torrents[3]): 悬停 save_path 单元格浮窗弹出,
 *      verdict = 已完成(词表复用) + 「待恢复成员」kv 在场(穷尽文案「不再补发」, 与抽屉
 *      入口一致) + 中性 tone 替身生效;
 *   2. cancelled 终态无账行(桩 torrents[4]): 门谓词 false -> 不弹(窄放行要求账非空);
 *   3. 无标注行(桩 torrents[5]): 门谓词 false -> 不弹(照旧)。
 * 负向面 = 即时 DOM 断言(pop 未出现)+ 门谓词 vm 探针(pair-filter.spec 同款 withVm 内部
 * 读数; 谓词无 DOM 之外的取径, 而调度矩阵已由 pytest node 探针 timers 钉死)。
 * 行内边界不动(D11): done/cancelled 行内仍单排正常色 —— done+账行的 save_path 单元格
 * 不得出现 .rel-pair 两排或 .rel-tone-* 着色类。
 * 桩面: ui_harness._inject_relocate_jobs 灌 5 个 job —— moving / armed(pending_finalize) /
 * failed / done(+穷尽账) / cancelled(无账); 轮询每 2s 服务端重建, 标注稳定重现。
 * 行定位: 行挂 :data-hash(桩 hash = f"{i:040x}", ui_harness._make_torrents) —— 不用名称
 * hasText: 行 textContent 是跨单元格无分隔拼接, 名称后紧跟下一格数字, \b 类断言不可靠。
 * 手势: 注入 job 挂 torrents[0..4](added_on 最旧), 默认「添加于」降序落在行窗口外 ——
 * 键盘激活表头切升序(relocate-pair-filter.spec 同款, sticky 表头不走 hover)。
 * 睡等纪律: hover 自带 scrollIntoViewIfNeeded 的 scroll 事件在 mouseenter 之后送达, 会走
 * 「滚动即关」监听(relocate_pop.js _relPopGlobals)把挂起的 120ms 调度掐掉 —— 先显式滚入
 * 再双 rAF 等渲染沉降(scroll 事件在渲染帧送达), 不落固定睡等(flaky 守阵口径)。
 */

/** 桩 torrents[i] 的 hash(ui_harness._make_torrents: f"{i:040x}") */
const hashOf = (i) => i.toString(16).padStart(40, '0');
/** 种子页平铺视图 torrents[i] 的行 */
const rowOf = (page, i) => page.locator(`.torrent-row[data-hash="${hashOf(i)}"]`);
/** 行内 save_path 触发单元格(浮窗触发面; 排除复用同类名的 tracker 列) */
const cellOf = (row) => row.locator('.g-save-path', { hasText: 'Downloads' });

/** 滚入 + 双 rAF 渲染沉降: scrollIntoViewIfNeeded 引发的 scroll 事件在下一渲染帧送达,
 * 不等它沉降, hover 后事件逆序到达会把挂起的 120ms 调度经「滚动即关」hideNow 掐掉(实测)。 */
const scrollSettle = async (page, loc) => {
  await loc.scrollIntoViewIfNeeded();
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
};

for (const skin of SKINS) {
  test.describe(`迁移浮窗终态窄放行 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`终态+余量行弹含待恢复 kv / 终态无账与无标注行不弹 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      const sortCell = page.locator('[data-table="torrent"].group-head .h-cell.hc-added_on');
      await sortCell.focus();
      await page.keyboard.press('Enter');
      const pop = page.locator('.relpop');

      // 门谓词判别面(vm 内部读数, 无 DOM 取径): done+账 true / cancelled 无账与无标注 false
      await expect.poll(() => withVm(page, `return (() => {
        const m3 = (vm.visibleTorrents || []).find(x => x.hash === '${hashOf(3)}');
        const m4 = (vm.visibleTorrents || []).find(x => x.hash === '${hashOf(4)}');
        const m5 = (vm.visibleTorrents || []).find(x => x.hash === '${hashOf(5)}');
        return m3 && m4 && m5
          ? vm._relPopTerminalGate(m3) && !vm._relPopTerminalGate(m4) && !vm._relPopTerminalGate(m5)
          : false;
      })()`)).toBe(true);

      // 1. done + 穷尽账余量(i=3): 浮窗弹, verdict 词表「已完成」, 待恢复成员 kv 走单点文案。
      //    外层 toPass 兜 2s 轮询重建的残余竞态(hover 后行被重建则 leave 掐调度, 重试即绿)。
      const doneRow = rowOf(page, 3);
      await expect(doneRow).toBeVisible({ timeout: 15_000 });
      // D11 行内边界: 终态行内不得出现两排/着色(「不出已完成结论」)
      await expect(doneRow.locator('.rel-pair')).toHaveCount(0);
      await expect(doneRow.locator('[class*="rel-tone-"]')).toHaveCount(0);
      await expect(async () => {
        await scrollSettle(page, cellOf(doneRow));
        await cellOf(doneRow).hover();
        await expect(pop).toBeVisible({ timeout: 1_500 });
        await expect(pop.locator('.rp-verdict')).toHaveText('已完成');
        await expect(pop.locator('.rp-kv', { hasText: '待恢复成员' })).toContainText('不再补发');
      }).toPass({ timeout: 20_000 });

      // 收尾: 移开鼠标让宽限隐藏走完(160ms), 给负向断言一个干净起点
      await page.mouse.move(4, 4);
      await expect(pop).not.toBeVisible({ timeout: 5_000 });

      // 2. cancelled 无账(i=4): 门谓词 false(已上探针钉) + hover 后浮窗不得出现
      const cancelRow = rowOf(page, 4);
      await expect(cancelRow).toBeVisible({ timeout: 15_000 });
      await scrollSettle(page, cellOf(cancelRow));
      await cellOf(cancelRow).hover();
      await expect(pop).not.toBeVisible();

      // 3. 无标注行(i=5): 照旧不弹
      const plainRow = rowOf(page, 5);
      await expect(plainRow).toBeVisible({ timeout: 15_000 });
      await scrollSettle(page, cellOf(plainRow));
      await cellOf(plainRow).hover();
      await expect(pop).not.toBeVisible();
    });
  });
}
