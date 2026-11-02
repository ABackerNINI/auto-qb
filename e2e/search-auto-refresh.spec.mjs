/*
 * 搜索自动更新 e2e(plan 26-11-03-0120 P3) —— 三皮肤全跑: /atlas/ /prism/ /flux/
 *
 * 缺陷症状: 搜索进行中/完成后, 新加入的种子名称命中当前搜索词也不会出现在结果里, 必须重搜。
 * 根因: 前端只在发起搜索时取一次结果快照, 轮询只更新分组视图(不重跑搜索) ⇒ 结果集冻结。
 *
 * 修复闭环: 服务端 search_rev 随搜索相关数据变化自增(S1/S2) -> /api/state 恒回传(S3) ->
 * 前端轮询发现落后, 冷却(SEARCH_REFRESH_MIN_MS=2000ms)后静默重查(doSearch(true), 不武装
 * searchPending) -> 整集替换命中集 + 共享 topbar 提示「结果已更新(+N 个种子)」(3s 自收)。
 *
 * 本 spec 验证的两种场景:
 *   ① 0 命中 -> 新增命中种子: 一个轮询周期内自动出现, 提示 +1, 且列表不闪成全量(行数恒 1);
 *   ② 搜索叠加分类筛选: 新命中种子的分类满足筛选时同样自动并入(筛选条件不被静默刷新绕过)。
 *
 * 数据面: 桩服务**运行期**增删种子走 `/__harness__/add_torrent` / `/__harness__/remove_torrent`
 * (仅测试端点, scripts/ui_harness.py)。实现刻意复用生产路径 `QbManager._refresh_torrents` ——
 * 由 apply_sync 推出 added/removed, search_rev 自然自增; 若手写版本号, 这里测的就是假通路。
 * 桩是长驻共享实例, 每条用例 afterEach 必须删除自己加的种子, 否则污染种子总数/视图用例。
 */
import { expect, test } from '@playwright/test';
import { BASE_URL } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { tab } from './lib/gestures.mjs';
import { readInst } from './lib/vm.mjs';

/* 计划 P3 指定三皮肤(harness.mjs 的 SKINS 只含 prism/atlas, 故此处单列; 含 flux)。 */
const SEARCH_SKINS = ['atlas', 'prism', 'flux'];

const SEARCH_INPUT = 'input[placeholder="搜索种子或文件名..."]';

/** 桩控制面: 运行期新增一个合成种子(名称含 token), 返回 hash 供收尾删除。 */
async function addSeed(request, name, category = '') {
    const res = await request.post(
        `${BASE_URL}/__harness__/add_torrent?name=${encodeURIComponent(name)}` +
        `&category=${encodeURIComponent(category)}`,
    );
    expect(res.ok(), '桩控制面 add_torrent 必须 200').toBeTruthy();
    return await res.json();
}

for (const skin of SEARCH_SKINS) {
    test.describe(`搜索自动更新 (${skin})`, () => {
        installRuntimeErrorGuard(test);

        /** @type {string|null} 本条用例新增的种子 hash(收尾必删, 桩共享实例) */
        let addedHash = null;

        test.afterEach(async ({ request }) => {
            if (!addedHash) return;
            await request.post(`${BASE_URL}/__harness__/remove_torrent?hash=${addedHash}`);
            addedHash = null;
        });

        /** 进皮肤页并切到种子视图(搜索态的行数可直接观察)。 */
        async function gotoTorrents(page) {
            await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
            await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
            await tab(page, 'torrents').click();
            await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        }

        /** 打到 0 命中的搜索态: 搜索词命中现有 300 个合成种子之外。 */
        async function searchToEmpty(page, token) {
            const input = page.locator(SEARCH_INPUT);
            await input.fill(token);
            await input.press('Enter');
            await expect.poll(() => readInst(page, 'vm.searchPending'), { timeout: 15_000 }).toBe(false);
            await expect.poll(() => readInst(page, 'vm.filteredTorrents.length'), { timeout: 15_000 }).toBe(0);
            // 0 命中 = 真 0 行(排除"pending 时空列表"的假象)
            expect(await page.locator('.torrent-row[data-hash]').count()).toBe(0);
        }

        test(`0 命中 -> 新增命中种子: 轮询周期内自动出现, 提示 +1, 不闪全列表 @fast (${skin})`,
              async ({ page, request }) => {
            collectRuntimeErrors(page);
            await gotoTorrents(page);
            const token = `尼古丁${skin}${Date.now()}`;
            await searchToEmpty(page, token);

            const added = await addSeed(request, `${token}.1080p.WEB-DL.x265-GROUPNEW`);
            addedHash = added.hash;

            /* 300 种子档轮询 2s + 冷却 2s => 最坏约 4s; 25s 是故障余量而非期望值。
             * 不 sleep —— expect.poll 在真实轮询/静默重查完成后立刻返回。 */
            await expect.poll(() => readInst(page, 'vm.filteredTorrents.length'), { timeout: 25_000 }).toBe(1);
            await expect.poll(() => readInst(page, 'vm.searchHits.size'), { timeout: 5_000 }).toBe(1);
            // 静默刷新全程不武装 pending => 不出现"待响应遮罩"式闪断
            expect(await readInst(page, 'vm.searchPending'), '静默刷新不得置 searchPending').toBe(false);
            // 结果整集替换成 1 行(若走成"清空后重搜"会先闪全列表/空态)
            expect(await page.locator('.torrent-row[data-hash]').count()).toBe(1);

            const hint = page.locator('.search-refresh-note');
            await expect(hint, '新增命中必须给出可发现提示').toBeVisible({ timeout: 5_000 });
            await expect(hint).toHaveText('· 结果已更新（+1 个种子）');
        });

        test(`搜索叠加分类筛选: 新命中种子同样自动并入 @fast (${skin})`, async ({ page, request }) => {
            collectRuntimeErrors(page);
            await gotoTorrents(page);

            // 叠加筛选: 分类 = Movies(只用真实点击, 不注入 vm 状态)
            const catBtn = page.locator('.filter-btn', { hasText: '分类' });
            await catBtn.click();
            await page.locator('.pop-item', { hasText: 'Movies' }).click();
            await catBtn.click();  // 收起弹层
            await expect.poll(() => readInst(page, 'vm.categoryFilter.length'), { timeout: 5_000 }).toBe(1);

            const token = `尼古丁${skin}F${Date.now()}`;
            await searchToEmpty(page, token);

            // 新种子分类满足叠加筛选 -> 静默重查后应保留在结果里(筛选不被绕过)
            const added = await addSeed(request, `${token}.1080p.WEB-DL.x265-GROUPNEW`, 'Movies');
            addedHash = added.hash;

            await expect.poll(() => readInst(page, 'vm.filteredTorrents.length'), { timeout: 25_000 }).toBe(1);
            const hint = page.locator('.search-refresh-note');
            await expect(hint).toBeVisible({ timeout: 5_000 });
            await expect(hint).toHaveText('· 结果已更新（+1 个种子）');
        });
    });
}
