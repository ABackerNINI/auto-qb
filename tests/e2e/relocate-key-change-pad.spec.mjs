// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, TORRENTS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { INST } from './lib/vm.mjs';

/**
 * 组键换键窗口的行高占位守阵(issue 26-11-11-0553, 计划 26-11-15-2340 §03.6 刀1 顺带面):
 *
 * 组键 = (规范化 save_path, 文件) —— 整组迁移收官瞬间 qB 侧 save_path 变更 -> 组行 data-key
 * 换键, 行高表(`_rowHs`)里旧键实测值成孤儿、新键无实测, 该行在窗口前缀和按全局均值 est 兜底,
 * 占位/滚动总高短暂失真(列表跳一下; issue 定性的真实缺口 —— 双排渲染本身四皮肤实测健康)。
 *
 * 修法(issue §06 建议其一「键替换时沿用旧键实测值」): columns_grid._measureRowH 的键集过渡
 * 携带 —— 消失键(孤儿, 带实测高)与新出现且未实测的键在两侧待领池间确定性配对(两侧各恰一个
 * 才配, 多孤儿/多新键 = 歧义维持 est 兜底不猜; 池条目带 TTL 防删除组的高度被无关新组误领)。
 * 本 spec 钉绿色行为: 换键落定后, 新键在 _rowHs 拿到旧键的实测高度(不经 est 兜底)。
 * 先红后绿取证: 修复前本 spec 末条断言判红(新键无实测值, est 兜底占位失真), 修复后绿。
 *
 * 判别力门控(同 window-invalidation/perf 口径): 行窗口化需组数 >= ROW_WIN_MIN(200),
 * 桩两两配对 => E2E_TORRENTS >= 400 才有「目标组不在渲染窗口、换键后无人量它」的稳定形态;
 * 小数据档全量渲染换键行当场被量齐, 断言无判别力。默认档(300)下本 spec 恒 skip —— 真跑
 * 走手工抬档(perf-serial 的抬档清单只收 CPU 敏感量具, 本 spec 非量具不入其 args, 评审
 * minor-4 处置 = 头注注明手工命令):
 *   E2E_TORRENTS=400 commands run dev.e2e -- tests/e2e/relocate-key-change-pad.spec.mjs
 * 先红后绿取证(2026-11-16): 修复前末条「换键携带」断言 15s 超时判红; 修复后 1 passed。
 * 桩面: POST /__harness__/set_save_path(hash=逗号分隔多 hash)改 FakeTorrent.save_path 并按
 * 桩直写口径重建 groups(一次调用一代发布, 换键的加/删两半原子到达), 见 ui_harness.py。
 */

const SKIN = 'flux'; // 单皮肤: 换键携带是 columns_grid 引擎行为, 与皮肤无关(引擎单点)

for (const skin of [SKIN]) {
  test.describe(`组键换键行高携带 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test('换键后新键沿用旧键实测高度(est 兜底消失) @fast', async ({ page }) => {
      test.skip(TORRENTS < 400, `换键占位断言需组数 >= 200(行窗口化)才稳定; 当前 E2E_TORRENTS=${TORRENTS}(默认档 300)`);
      test.setTimeout(120_000); // 400 种子档整页加载 + 量齐 poll + 换键落定观察窗(时间预算, 非睡等)
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 20_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 量齐就位(首访全量轮 settle, window-invalidation 同款 poll)
      await expect.poll(
        () => page.evaluate(`(async () => { const vm = ${INST}; return vm._winMeasured.group; })()`),
        { timeout: 30_000, message: '首访量齐全量轮 settle(行高实测态就位)' },
      ).toBe(true);

      // 取表尾组(行窗口化下不在渲染窗口; 成员项按 build 兼容 hash 串/成员视图两种形态取 hash)。
      // filteredGroups 兼容虚拟行(u-<hash>, selection.js 同款口径), 虚拟行无 store 组键, 跳过。
      const target = await page.evaluate(`(async () => {
        const vm = ${INST};
        const real = vm.filteredGroups.filter((g) => !String(g.key || "").startsWith("u-"));
        const g = real[real.length - 1];
        return { key: g.key, hashes: g.members.map((m) => (typeof m === "string" ? m : m.hash)) };
      })()`);
      expect(target.hashes.length).toBeGreaterThan(0);
      await page.evaluate((k) => { window.__tOld = k; }, target.key);

      // 滚到表尾把目标组量齐, 再滚回顶部(它的实测值留在 _rowHs, 行卸出窗口)。
      // 行窗口化滚动源 = 文档(WIN_SRC_DOC: window.scrollY/innerHeight, columns.js 单点)
      await page.evaluate(() => { window.scrollTo(0, document.body.scrollHeight); });
      await expect.poll(
        () => page.evaluate(`(async () => { const vm = ${INST}; return vm._rowHs["group:" + ${JSON.stringify(target.key)}]; })()`),
        { timeout: 20_000, message: '表尾组已被实测' },
      ).not.toBe(undefined);
      const h1 = await page.evaluate(`(async () => { const vm = ${INST}; return vm._rowHs["group:" + ${JSON.stringify(target.key)}]; })()`);
      await page.evaluate(() => { window.scrollTo(0, 0); });

      // 换键: 两成员 save_path 同步改到新路径(单次调用 = 单代发布, 加/删两半原子到达)
      const resp = await page.request.post(`${baseUrl()}/__harness__/set_save_path`, {
        params: { hashes: target.hashes.join(','), save_path: 'R:\\Downloads\\SetX-Moved' },
      });
      expect((await resp.json()).changed, JSON.stringify({ status: resp.status() })).toBe(true);

      // 换键落定(旧键离场且新键在场) —— expect.poll 只回 matcher 结果, 落定键经闭包捕获
      let k2 = null;
      await expect
        .poll(
          async () => {
            const v = await page.evaluate(`(async () => {
              const vm = ${INST};
              const want = ${JSON.stringify(target.hashes)};
              const hOf = (m) => (typeof m === "string" ? m : m.hash);
              const has = (k) => vm.filteredGroups.some((x) => x.key === k);
              const g = vm.filteredGroups.find((x) => x.members.some((m) => want.includes(hOf(m))));
              if (!g || g.key === ${JSON.stringify(target.key)} || has(${JSON.stringify(target.key)})) return null;
              return g.key;
            })()`);
            if (v) k2 = v;
            return v;
          },
          { timeout: 30_000, message: '换键落定: 新组键在场且旧组键离场' },
        )
        .not.toBe(null);
      expect(k2, '落定键确与旧键不同(换键发生)').toBeTruthy();

      // 绿色行为: 新键拿到旧键实测高度(携带), 不落 est 兜底 —— 修复前此处判红
      // (新键在 _rowHs 无实测, 窗口前缀和按全局均值兜底 -> 占位/滚动总高失真)
      await expect.poll(
        () => page.evaluate(`(async () => { const vm = ${INST}; return vm._rowHs["group:" + ${JSON.stringify(k2)}]; })()`),
        { timeout: 15_000, message: '换键携带: 新键沿用旧键实测高度(issue 26-11-11-0553 修法)' },
      ).not.toBe(undefined);
      const h2 = await page.evaluate(`(async () => { const vm = ${INST}; return vm._rowHs["group:" + ${JSON.stringify(k2)}]; })()`);
      expect(Math.abs(h2 - h1), '携带值 == 旧键实测值(同组换键, 行高不变)').toBeLessThanOrEqual(0.5);
    });
  });
}
