/*
 * 搜索未归组虚拟行去重 e2e(issue 26-11-03-0254) —— 三皮肤全跑: /atlas/ /prism/ /flux/
 *
 * 缺陷症状: 搜索命中「当时未归组」的种子后, 归组关系一变, 同一 hash 会同时出现两条:
 *   真实组行 + u-<hash> 虚拟行; 若 search_rev 不变(归组关系变化不触发), 一直挂到手动重搜。
 * 根因: searchUncovered 只是 doSearch 落袋那一刻的快照, filteredGroups 渲染期无条件追加。
 * 修复: filteredGroups 用**渲染时的未过滤 this.groups** 现算 groupedNow(与 doSearch 的 grouped
 *   同一口径), 追加前过两道闸 —— ①已不在命中集(!hits.has) ②已在当前真实组内(groupedNow.has)。
 *
 * 复现手法(受桩能力边界约束, 与计划初稿的构造不同, 但打的是同一根因):
 *   · 桩的合成种子全部已归组(150 组 × 2), 且 add_torrent 的新种子也会立刻分进自己的组 =>
 *     默认档没有"真正未归组"的种子, 也无法"让某种子后来才归组"(组键含文件元组, 同 save_path
 *     不等于同组), 故计划初稿的「add 同路径种子成组」「设置页关/开分组」在桩上不可复现
 *     (后者见 ui_harness._materialize_config: reload_config 只回执不应用)。
 *   · 可确定性复现的是**跨视图 stale groups**: 首屏直接落种子页(预置 localStorage
 *     autoqb.ui.view=torrents)时, 首轮 /api/state?view=torrent 不回 groups, this.groups=[] =>
 *     此刻搜索把所有命中判成「未归组」写进 searchUncovered; 切到辅种页后真实 groups 到位,
 *     旧快照被追加 => 同 hash 两遍。search_rev 全程不变(没有数据变更), 自动刷新不会救场 ——
 *     这正是 issue 里"滞留到手动搜索"的形态。
 *
 * 四条场景 = 该根因的四个可观测面(每条三皮肤):
 *   ① 首轮种子页搜索 -> 切辅种页: 同一 hash 只出一条真实组行(核心);
 *   ② 搜索叠加分类筛选 -> 切辅种页: 两道闸与 facet 语义顺序正确, 命中组仍保留、不重复;
 *   ③ 命中种子被删除: ≤1 个搜索刷新增量周期内行消失, 且虚拟行不得滞留;
 *   ④ 搜索后视图往返(种子 -> 辅种 -> 种子 -> 辅种): 幂等, 不得每次都把旧快照再画一遍。
 *
 * 数据面: 运行期增删种子走 `/__harness__/add_torrent` / `/__harness__/remove_torrent`
 * (仅测试端点, scripts/ui_harness.py), 实现复用生产 `QbManager._refresh_torrents`。
 * 桩是长驻共享实例, 每条用例 afterEach 必须删除自己加的种子。
 */
import { expect, test } from '@playwright/test';
import { baseUrl } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { tab } from './lib/gestures.mjs';
import { readInst } from './lib/vm.mjs';

/* 三皮肤全跑(harness.mjs 的 SKINS 只含 prism/atlas, 故此处单列; 含 flux)。 */
const SEARCH_SKINS = ['atlas', 'prism', 'flux'];

const SEARCH_INPUT = 'input[placeholder="搜索种子或文件名..."]';

/** 全库唯一的命中词: 合成种子 GROUP0 那一对(seed0/seed1, 同组同名)独占该词。 */
const TOKEN_PAIR0 = 'x265-GROUP0';

/**
 * 渲染结果体检读数(断言「同一 hash 不得出现两次」的权威口径, evaluate 第②类):
 * 遍历 filteredGroups 全体的 members 计 hash 出现次数 —— 真实组行与虚拟行都在 filteredGroups 里,
 * DOM 是窗口化子集, 只数 visibleGroups 会漏掉窗口外的重复。
 */
const DUPLICATE_REPORT = `(() => {
  const rows = vm.filteredGroups;
  const counts = new Map();
  for (const g of rows) for (const m of g.members) counts.set(m.hash, (counts.get(m.hash) || 0) + 1);
  return {
    rows: rows.length,
    virtual: rows.filter((g) => g.virtual).length,
    dup: [...counts].filter(([, n]) => n > 1).map(([h]) => h),
  };
})()`;

/** 桩控制面: 运行期新增一个合成种子(名称含 token), 返回 hash 供收尾删除。 */
async function addSeed(request, name, category = '') {
    const res = await request.post(
        `${baseUrl()}/__harness__/add_torrent?name=${encodeURIComponent(name)}` +
        `&category=${encodeURIComponent(category)}`,
    );
    expect(res.ok(), '桩控制面 add_torrent 必须 200').toBeTruthy();
    return await res.json();
}

/** 首屏直接落种子页: 首轮 /api/state?view=torrent 不回 groups => this.groups=[]。 */
async function openSeedViewFirst(page, skin) {
    await page.addInitScript(() => localStorage.setItem('autoqb.ui.view', 'torrents'));
    await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
    await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 20_000 });
    /* 前奏必须真的生效: 种子页首轮 groups 为空 —— 否则下面的命中不会被判成「未归组」,
     * 本 spec 就退化成"本来就没有虚拟行"的空转。 */
    await expect.poll(() => readInst(page, 'vm.groups.length'), { timeout: 10_000 }).toBe(0);
}

/** 打一次服务端搜索并等落袋(与 search-auto-refresh.spec 同一手法, 不 sleep)。 */
async function search(page, token) {
    const input = page.locator(SEARCH_INPUT);
    await input.fill(token);
    await input.press('Enter');
    await expect.poll(() => readInst(page, 'vm.searchPending'), { timeout: 15_000 }).toBe(false);
}

/** 切到辅种页并等首行渲染(goView 已置空 lastRid => 一定取一次全量含 groups)。 */
async function gotoTab(page, view, rowSelector) {
    await tab(page, view).click();
    await expect(page.locator(rowSelector).first()).toBeVisible({ timeout: 20_000 });
}

for (const skin of SEARCH_SKINS) {
    test.describe(`搜索虚拟行去重 (${skin})`, () => {
        installRuntimeErrorGuard(test);

        /** @type {string|null} 本条用例新增的种子 hash(收尾必删, 桩共享实例) */
        let addedHash = null;

        test.afterEach(async ({ request }) => {
            if (!addedHash) return;
            await request.post(`${baseUrl()}/__harness__/remove_torrent?hash=${addedHash}`);
            addedHash = null;
        });

        test(`种子页首搜(未回 groups) -> 切辅种页: 同一命中只出一条真实组行 @fast (${skin})`,
              async ({ page }) => {
            collectRuntimeErrors(page);
            await openSeedViewFirst(page, skin);

            await search(page, TOKEN_PAIR0);
            const hits = await readInst(page, 'vm.searchHits.size');
            expect(hits, 'GROUP0 那对种子都应命中(同组同名)').toBe(2);
            /* 落袋快照把两个命中都记成「未归组」—— 这正是缺陷的起点(此时渲染面在种子页, 无碍)。 */
            expect(await readInst(page, 'vm.searchUncovered.length'), 'groups 为空 => 全部命中进未归组快照').toBe(2);

            await gotoTab(page, 'groups', '.group-row');
            /* 修复后: 真实组行恰好一条, 虚拟行 0, 且无任何 hash 重复。
             * 修复前: 真实组行 + 2 条 u- 虚拟行 = rows 3 / virtual 2 / dup 2。 */
            await expect.poll(() => readInst(page, DUPLICATE_REPORT), { timeout: 15_000 })
                .toEqual({ rows: 1, virtual: 0, dup: [] });
            expect(await page.locator('.group-row[data-key^="u-"]').count(), 'DOM 也不得出现虚拟行').toBe(0);
        });

        test(`搜索叠加分类筛选 -> 切辅种页: facet 语义不被去重闸打乱 @fast (${skin})`, async ({ page }) => {
            collectRuntimeErrors(page);
            await openSeedViewFirst(page, skin);

            /* 叠加筛选: 分类 = Movies(只用真实点击, 不注入 vm 状态; 与 search-auto-refresh.spec 同款)。
             * seed0 分类空 / seed1 是 Movies, 同组 => 组行因成员命中而保留。 */
            const catBtn = page.locator('.filter-btn', { hasText: '分类' });
            await catBtn.click();
            await page.locator('.pop-item', { hasText: 'Movies' }).click();
            await catBtn.click();  // 收起弹层
            await expect.poll(() => readInst(page, 'vm.categoryFilter.length'), { timeout: 5_000 }).toBe(1);

            await search(page, TOKEN_PAIR0);
            expect(await readInst(page, 'vm.searchHits.size')).toBe(2);

            await gotoTab(page, 'groups', '.group-row');
            /* 修复前: 组行 + 分类为 Movies 的虚拟行 = rows 2 / virtual 1 / dup 1。
             * 修复后: 只剩组行(virtual 行连 facet 之前就被「已归组」闸挡掉)。 */
            await expect.poll(() => readInst(page, DUPLICATE_REPORT), { timeout: 15_000 })
                .toEqual({ rows: 1, virtual: 0, dup: [] });
        });

        test(`命中种子被删除: ≤1 个搜索刷新周期内虚拟行消失 @fast (${skin})`, async ({ page, request }) => {
            collectRuntimeErrors(page);
            await openSeedViewFirst(page, skin);

            const token = `尼古丁去重${skin}${Date.now()}`;
            const added = await addSeed(request, `${token}.1080p.WEB-DL.x265-NEW`);
            addedHash = added.hash;

            await search(page, token);
            expect(await readInst(page, 'vm.searchHits.size'), '新增种子应命中').toBe(1);
            /* 桩的增量归组相位不在 _refresh_torrents 里跑(合成组是启动时手搭的), 故运行期新增种子
             * 一直是「未归组」单种子 => 这里得到的是**合法**的虚拟行(设计契约的兜底面, 不是重复)。 */
            expect(await readInst(page, 'vm.searchUncovered.length')).toBe(1);

            await gotoTab(page, 'groups', '.group-row');
            await expect.poll(() => readInst(page, DUPLICATE_REPORT), { timeout: 15_000 })
                .toEqual({ rows: 1, virtual: 1, dup: [] });
            /* 兜底行与命中集一一对应(同一 hash 只出现一次) —— 这是修复前后都该成立的语义基线。 */
            expect(await readInst(page, 'vm.searchUncovered.length'), '未归组快照恰一条').toBe(1);

            const hashRows = `vm.filteredGroups.filter((g) => g.members.some((m) => m.hash === ${JSON.stringify(added.hash)})).length`;
            const staleVirtual = `vm.filteredGroups.some((g) => g.virtual && g.members.some((m) => m.hash === ${JSON.stringify(added.hash)}))`;

            // 删除走生产路径 => search_rev 自增 => 静默重查(冷却 2s + 轮询 2s; 25s 是故障余量)
            await request.post(`${baseUrl()}/__harness__/remove_torrent?hash=${added.hash}`);
            await expect.poll(() => readInst(page, 'vm.searchHits.has(' + JSON.stringify(added.hash) + ')'), { timeout: 25_000 }).toBe(false);
            await expect.poll(() => readInst(page, hashRows), { timeout: 25_000 }).toBe(0);
            await expect.poll(() => readInst(page, staleVirtual), { timeout: 5_000 }).toBe(false);
            expect(await page.locator('.group-row[data-key^="u-"]').count(), '删除后不得留下 u- 虚拟行').toBe(0);
        });

        test(`搜索后视图往返: 旧快照不得每次都重画一遍 @fast (${skin})`, async ({ page }) => {
            collectRuntimeErrors(page);
            await openSeedViewFirst(page, skin);
            await search(page, TOKEN_PAIR0);
            expect(await readInst(page, 'vm.searchUncovered.length')).toBe(2);

            for (let round = 0; round < 2; round++) {
                await gotoTab(page, 'groups', '.group-row');
                await expect.poll(() => readInst(page, DUPLICATE_REPORT), { timeout: 15_000 })
                    .toEqual({ rows: 1, virtual: 0, dup: [] });
                await gotoTab(page, 'torrents', '.torrent-row');
                /* 种子页不消费虚拟行(命中门单点走 searchHits): 命中数恒 2, 行不重复。 */
                expect(await readInst(page, 'vm.filteredTorrents.length')).toBe(2);
            }
            // 往返两轮后快照仍是旧的(搜索未变), 但渲染面始终只有一条真实组行
            expect(await readInst(page, 'vm.searchUncovered.length')).toBe(2);
            await expect.poll(() => readInst(page, DUPLICATE_REPORT), { timeout: 15_000 })
                .toEqual({ rows: 1, virtual: 0, dup: [] });
        });
    });
}
