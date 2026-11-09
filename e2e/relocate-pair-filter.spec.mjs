// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { withVm } from './lib/vm.mjs';

/**
 * 迁移两排 A→B 的路径 chip 点击筛选(plan 26-11-07-2344 R3 D16/D17) ——
 *
 * pytest 侧钉的是**静态面**(模板结构/f-on 绑定/filterFromChip 锚)与 **node 行为面**
 * (_pathPositions 匹配矩阵, test_webui_relocate_visibility); 本 spec 钉的是**真浏览器接线面**:
 *   1. pair 行不再渲染原单排路径行(A 排承载同一值, R3 实施缺口修正);
 *   2. 点 B 排(目标位置)= 切换路径筛选 pathFilter, 被点行不被自己筛走
 *     (D17: 进行中 dst 参与匹配 —— 旧 chip 的「点自己带的值, 筛完自己还在」不变量保住);
 *   3. 再点一次 = 取消(toggle 语义, 与弹层同款); f-on 选中态随点挂;
 *   4. done 行的历史 dst 不参与匹配(D17 active 边界): 桩里 done 行的 dst 与进行中行同为
 *     Relocated, 筛 dst 后 done 行必须离场(node 探针同款矩阵的真机对照)。
 * 桩面: ui_harness._inject_relocate_jobs 给 torrents[0..3] 灌 moving/armed(pending_finalize)/
 * failed/done 四态, src=R:\Downloads\Set000, dst=R:\Downloads\Relocated; 轮询每 2s 服务端
 * 重建, 标注随 rebuild 稳定重现。种子页平铺视图一行一粒种子(m 分支)。
 */

const DST = 'R:\\Downloads\\Relocated';
const SRC = 'R:\\Downloads\\Set000';

for (const skin of SKINS) {
  test.describe(`迁移两排路径 chip 点击筛选 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`pair 替换单排 + A/B 排点击筛位置集 + toggle 与 f-on @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 种子页平铺: moving/armed/failed 三行带 .rel-pair(done 行回落单排)。
      // 注入四粒是 torrents[0..3] = added_on 最旧 —— 默认「添加于」降序落在行窗口(P1-2 只渲染
      // 视口附近切片)之外; 点「添加于」表头一击切升序(三态: 首击降序→再点升序, 默认已是降序),
      // 四行进窗口顶部。真实手势, 不注入 vm 内部态。
      await page.click('nav.tabs [data-view="torrents"]');
      // sticky 表头持续重排会让 Playwright 的 stability 判定超时 —— 走键盘激活(a11y 路径,
      // table-head-a11y.spec 同款: focus + Enter = headActivate)
      const sortCell = page.locator('[data-table="torrent"].group-head .h-cell.hc-added_on');
      await sortCell.focus();
      await page.keyboard.press('Enter');
      const pair = page.locator('.torrent-row .rel-pair').first();
      await expect(pair).toBeVisible({ timeout: 15_000 });

      // 1. pair 行内不得再有原单排路径行(.sp-body 隐藏, A 排承载同一值)
      const cell = page.locator('.torrent-row .g-save-path.has-relpair').first();
      await expect(cell.locator('.sp-body')).toHaveCount(0);

      // 2. 点 B 排(目标位置) = 筛 dst; 进行中三行(0/1/2)命中, done 行(3)历史 dst 不参与
      await pair.locator('.rel-pb').click();
      await expect.poll(() => withVm(page, 'return (vm.pathFilter || []).join("|");')).toBe(DST);
      await expect.poll(() => withVm(page, 'return vm.filteredTorrents.length;')).toBe(3);
      // 被点行不被自己筛走(自锁不复存在); f-on 挂在 B 排上
      await expect(page.locator('.torrent-row .rel-pair').first()).toBeVisible();
      await expect(page.locator('.torrent-row .rel-pb.f-on').first()).toBeVisible();

      // 3. 再点一次 = 取消(toggle, 与顶栏弹层同语义)
      await pair.locator('.rel-pb').click();
      await expect.poll(() => withVm(page, 'return (vm.pathFilter || []).length;')).toBe(0);

      // 4. 点 A 排(当前位置) = 筛 src: 0/1 两粒 save_path==Set000 + 2 号(failed)src==Set000
      // 经位置集命中 —— 三行; done 行不参与(D17)
      await pair.locator('.rel-pa').click();
      await expect.poll(() => withVm(page, 'return (vm.pathFilter || []).join("|");')).toBe(SRC);
      await expect.poll(() => withVm(page, 'return vm.filteredTorrents.length;')).toBe(3);
      await expect(page.locator('.torrent-row .rel-pa.f-on').first()).toBeVisible();
    });
  });
}
