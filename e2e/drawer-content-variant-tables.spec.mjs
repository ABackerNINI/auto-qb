// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * U4 内容树两变体(10 树 + 详情 / 11 树表批量) 表格体接引擎后的表面手势守阵
 * (计划 26-10-12-0527 U4 验收面: 树行为(展开/缩进/目录聚合)等价 + 手势用例) ——
 *
 * U4 起两变体的表格体不再是手搓 DOM: 变体外壳只留版式(10 右详情/工具条/统计条,
 * 11 工具条/批量条), 树行由 <aq-dt-bridge> 按 DRAWER_TABLE_DEFS 描述符 Teleport 进变体锚
 * (drawerContentV10/V11)。D4=A 树缩进格进渲染器(折叠钮/勾选框/缩进/图标/名称在格内);
 * 排序不适用(树序 = 树语义, dyn 空键); 11 的拖宽/右键隐藏/偏好持久化首次落地
 * (勾选/折叠列 locked), 可用性列 omitEmpty 渐进(原 hasav/noav 双 grid 手搓退役)。
 *
 * 2026-10-14 用户复查修法(报告 26-10-14-0136 §02「操作按钮独立成列 / 展开按钮没有层级」):
 * tgl/prio 两条交互轨道删除 —— 折叠钮收编进 name 格首部(随缩进 = 层级可视), 徽章收编进
 * name 格尾部(margin-left:auto 右对齐, 不占轨道); name 列 locked(交互件随格走)。终态:
 * 10 = 3 列(name/size/prog), 11 = 5 列(ck/name/size/prog/av).
 * !2026-10-14 用户二次复查(报告 26-10-14-0136 §02 续): ck 勾选框仍独立成列且拖宽可调 ——
 * 勾选框收进 name 格首(随缩进); ck 列删除(终态 11 = name/size/prog/av 四列), 勾选框随
 * name 格走 ⇒ name 列 locked 续效(隐藏 name = 一并废掉勾选框/折叠钮/徽章三个交互件).
 *
 * 手势清单(每条都是真手势, 不借道 vm):
 *   10: 树渲染(目录聚合徽章/缩进层级) + 交互件收编 name 格(折叠钮在格首/徽章在格尾, 3 列
 *       行 = 不占列) + 折叠(子树真收拢) + 筛选 chips + 行选中联动右详情(点行/取消)
 *       + 行级键盘(roving ArrowDown + Enter 激活, issue 26-10-07-0846 真机红验)
 *       + 徽章点击不夺行选中 + 工具条全局展开/折叠(R5#124)
 *       + 右详情优先级分段真提交(R5#121: POST {priority, indices: 整棵子树}, S5 批量通道
 *       在 10 号的唯一入口) + 空态行兜底(R5#110: __empty 出「该筛选下没有文件」+ 透明样式);
 *   11: 4 列表头 + 勾选(点行 = 勾选/目录 = 子树三态, 批量条浮出) + 目录三态框 indeterminate
 *       + 徽章循环真提交(POST files/priority 载荷断言) + 拖宽落盘 + 右键隐藏(locked 列无隐藏项)
 *       + 刷新偏好回放 + 可用性列常驻(无 availability 数据值出 — 占位)
 *       + 主勾选框三态(R5#122: 全选 POST 覆盖全部 indices/再点全不选回落/部分半选)
 *       + 工具条全局展开/折叠(R5#124) + 行级键盘(R5#123: roving + Enter 勾选翻 is-chk)
 *       + 未完成判据与计数同源(R5#109: progress∈[0.995,1) 计数计入且筛选可见);
 *   12: 真手势首轮(R5#120): 悬停互联(块<->榜行互加/摘 hl) + 组头折叠/展开 + 点选联动
 *       信息条(块选中态/对侧 is-sel/取消钮) + 仅看未完成 + 键盘选中(roving + Enter)。
 *
 * POST 桩口径(R5#121/122 起): 沿用 drawer-fileprio-optimistic 的「约定 cmd_id + 回执桩」
 * 形态 —— POST 捕获载荷后回 {queued, cmd_id}, /api/cmd/{id} 回 {status:'ok'} 让 waitCmd
 * 即刻终结(旧 '{}' 桩让 waitCmd 干等 10s 超时, 每条 POST 白付 10s)。
 *
 * 数据口径: page.route 桩掉 /api/torrents/{hash}/files(裸数组, 同族 spec 手法) ——
 *   3 目录 4 文件覆盖: 完整/半程/未开始 × 优先级三档 × availability 有/无/低。
 * 手法同族: drawer-trackers-variant-tables.spec(拖宽/右键/偏好回放全套)。
 */

const WIDE = { width: 2560, height: 1200 };

/** 合成文件列表(3 目录 4 文件; availability 覆盖有/低/无 —— 无的那条供 "—" 回退渲染)。 */
function makeFiles(withAv = true) {
  const av = (v) => (withAv ? v : undefined);
  return [
    { name: 'Season 1/E01 - intro.mkv', size: 1_000_000, progress: 1, priority: 1, availability: av(1.5) },
    { name: 'Season 1/E02 - part.mkv', size: 2_000_000, progress: 0.5, priority: 6, availability: av(0.4) },
    { name: 'Season 2/E01 - finale.mkv', size: 4_000_000, progress: 0, priority: 0, availability: av(0.8) },
    { name: 'bonus.txt', size: 100_000, progress: 1, priority: 1, availability: undefined },
  ];
}

/** 空态行数据(R5#110): 全部完整 + 无跳过 —— miss/skip 筛选都无命中, rowsFn 合成 __empty 行。 */
function makeFilesClean() {
  return [
    { name: 'E01 - done.mkv', size: 100_000, progress: 1, priority: 1, availability: 1 },
    { name: 'E02 - done.mkv', size: 200_000, progress: 1, priority: 1, availability: undefined },
  ];
}

/** 舍入界数据(R5#109): 0.999 被 drawerFileRows 整数舍入成 100, 但 derive 计数按原始值
 * prog<1 计入 —— 修前「未完成 1」计数却在筛选列表里看不到该文件。 */
function makeFilesRounding() {
  return [
    { name: 'Rnd/E01 - done.mkv', size: 1_000_000, progress: 1, priority: 1, availability: 1 },
    { name: 'Rnd/E02 - almost.mkv', size: 2_000_000, progress: 0.999, priority: 1, availability: 1 },
  ];
}

/** 树图数据(R5#120): 单目录占 ~98% 体积 —— 组头最小尺寸判据(块 >=110x44)确定性成立。 */
function makeFiles12() {
  return [
    { name: 'Big/A - alpha.mkv', size: 9_000_000, progress: 1, priority: 1, availability: 1.5 },
    { name: 'Big/B - beta.mkv', size: 500_000, progress: 0.5, priority: 6, availability: 0.4 },
    { name: 'Wee/C - gamma.mkv', size: 100_000, progress: 0, priority: 0, availability: 0.8 },
    { name: 'root.txt', size: 50_000, progress: 1, priority: 1, availability: undefined },
  ];
}

/** priority POST 桩(R5#121/122): 捕获载荷 + 约定 cmd_id 即刻回 ok(见文件头 POST 桩口径)。
 * filesState 传入时把 priority 应用回状态(GET files 每次从它现 stringify)—— 模拟 qB
 * 已落库, 回执后静默重拉带回新值, 徽章循环等后续手势读到的是持久化后的真值。 */
async function stubPrioPosts(page, tag, prioPosts, filesState = null) {
  await page.route('**/api/torrents/*/files/priority', async (route) => {
    const body = route.request().postDataJSON();
    prioPosts.push(body);
    if (filesState) {
      for (const i of body.indices || []) {
        if (filesState[i]) filesState[i] = { ...filesState[i], priority: body.priority };
      }
    }
    await route.fulfill({ json: { queued: true, cmd_id: `e2e-${tag}-prio` } });
  });
  await page.route(`**/api/cmd/e2e-${tag}-prio`, (route) =>
    route.fulfill({ json: { status: 'ok' } }));
}

async function openTorrentDrawer(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  return drawer;
}

/** 开抽屉 → 内容页签 → 等变体外壳与引擎行体点亮; 返回 drawer */
async function openContentVariant(page, variantId) {
  const drawer = await openTorrentDrawer(page);
  await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();
  await expect(drawer.locator(`.dt${variantId}-wrap`)).toBeVisible({ timeout: 10_000 });
  const anchor = drawer.locator(`[data-dt-table-anchor="drawerContentV${variantId}"]`);
  await expect(anchor.locator(`.group-row[data-table="drawerContentV${variantId}"]`).first(),
    '变体桥行体点亮(U4: 表格体归引擎)').toBeVisible({ timeout: 10_000 });
  return drawer;
}

for (const skin of SKINS) {
  test.describe(`内容树两变体手势 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`dt10 树 + 详情: 折叠/筛选/选中联动右详情/行级键盘 roving/全局展开折叠/优先级分段 POST @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      const filesState = makeFiles();
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(filesState) }));
      const prioPosts = [];
      await stubPrioPosts(page, 'dt10', prioPosts, filesState);
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '10' })));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openContentVariant(page, '10');
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV10"]');
      const rows = anchor.locator('.group-row[data-table="drawerContentV10"]');

      // 无表头设计: 引擎列头 CSS 隐藏(D5/Q3 记档); 行体 = 2 目录 + 4 文件
      await expect(anchor.locator('.group-head[data-table="drawerContentV10"]'), '列头隐藏(无表头设计)').toBeHidden();
      await expect(rows).toHaveCount(6);

      // 交互件收编 name 格(2026-10-14 复查: 按钮不占列 / 展开钮有层级): 行 = 3 格(name/size/prog),
      // 折叠钮在 name 格首部(随缩进), 徽章在 name 格尾部 —— 不再有 tgl/prio 两条独立轨道
      const s1 = rows.filter({ hasText: 'Season 1' }).first();
      await expect(s1).toHaveClass(/dir/);
      await expect(s1).toHaveJSProperty('children.length', 3);
      await expect(s1.locator('.dt10-n .dt10-tgl'), '折叠钮在 name 格内(随缩进 = 层级)').toBeVisible();
      await expect(s1.locator('.dt10-n .dt10-pbadge'), '目录行无徽章(优先级是文件动作)').toHaveCount(0);

      // 目录聚合徽章(树行为等价): Season 1 目录行 meta = 2 文件; 文件行缩进 = 目录层 × 14px
      await expect(s1.locator('.dt10-meta')).toContainText('2 文件');
      const e1 = rows.filter({ hasText: 'E01 - intro.mkv' }).first();
      const e1Indent = await e1.locator('.dt10-n').evaluate((el) => parseInt(getComputedStyle(el).paddingLeft, 10));
      const s1Indent = await s1.locator('.dt10-n').evaluate((el) => parseInt(getComputedStyle(el).paddingLeft, 10));
      expect(e1Indent - s1Indent, '树缩进层级差 = 14px/层(D4: 缩进在渲染器)').toBe(14);
      await expect(e1.locator('.dt10-n .dt10-pbadge'), '徽章在 name 格内(不占列)').toBeVisible();

      // 折叠: 子树真收拢, 再点展开
      await s1.locator('.dt10-tgl').click();
      await expect(rows.filter({ hasText: 'E01 - intro.mkv' }), '折叠后子树收拢').toHaveCount(0);
      await expect(rows).toHaveCount(4);
      await s1.locator('.dt10-tgl').click();
      await expect(rows).toHaveCount(6);

      // 工具条全局「展开/折叠」(R5#124): 折叠 = 全目录集入账(目录子树全收拢), 展开还原。
      // 根级文件(bonus.txt)不属于任何目录, 不受折叠影响 —— 剩 2 目录行 + 1 根级文件
      await drawer.locator('.dt10-tools [data-fold="close"]').click();
      await expect(rows.filter({ hasText: 'intro.mkv' }), '折叠: 目录内文件全收拢').toHaveCount(0);
      await expect(rows.filter({ hasText: 'part.mkv' })).toHaveCount(0);
      await expect(rows.filter({ hasText: 'finale.mkv' })).toHaveCount(0);
      await expect(rows, '剩 2 目录行 + 1 根级文件').toHaveCount(3);
      await drawer.locator('.dt10-tools [data-fold="open"]').click();
      await expect(rows, '全局展开后行数还原').toHaveCount(6);

      // 筛选 chips(版式语义): 未完成 = 目录(含缺口) + 两个缺口文件, 完整文件离场
      await drawer.locator('.dt10-chip[data-f="miss"]').click();
      await expect(drawer.locator('.dt10-chip[data-f="miss"]'), '激活态随筛选输出').toHaveClass(/active/);
      await expect(rows.filter({ hasText: 'E01 - intro.mkv' }), '完整文件离场').toHaveCount(0);
      await expect(rows.filter({ hasText: 'E02 - part.mkv' })).toHaveCount(1);
      await drawer.locator('.dt10-chip[data-f="all"]').click();
      await expect(rows).toHaveCount(6);

      // 行选中联动右详情(点行 = 选中, 再点取消); 徽章点击不夺行选中(stopPropagation)
      await e1.locator('.dt10-pbadge').click();
      await expect(drawer.locator('.dt10-right .dt10-dname'), '徽章点击不触发行选中(stopPropagation)').toHaveCount(0);
      await e1.click();
      await expect(drawer.locator('.dt10-right .dt10-dname')).toHaveText('E01 - intro.mkv');
      await expect(e1, '选中行高亮(_cls sel)').toHaveClass(/sel/);
      await e1.click();
      await expect(drawer.locator('.dt10-right .dt10-empty'), '再点取消 → 未选中态').toBeVisible();

      // 行级键盘(issue 26-10-07-0846 真机红验): roving 锚点(首行 tabindex=0) → ArrowDown 移焦
      // → Enter 激活 = 行选中联动右详情
      await rows.first().focus();
      await page.keyboard.press('ArrowDown');
      const focused = await page.evaluate(() => document.activeElement.getAttribute('data-dt-key'));
      expect(focused, '方向键移焦(引擎行容器 data-dt-key 身份锚): 首行目录 → 首个文件').toBe('Season 1/E01 - intro.mkv');
      await page.keyboard.press('Enter');
      await expect(drawer.locator('.dt10-right .dt10-dname'), 'Enter 激活 = 选中文件').toHaveText('E01 - intro.mkv');

      // 右详情优先级分段(R5#121): 选目录 → 点分段 = setFilePriority(p, subtreeIndices)
      // 真实 POST —— S5 批量通道在本变体的唯一入口, 目录 = 整棵子树收集
      await s1.click();
      await expect(drawer.locator('.dt10-right .dt10-dname'), '目录选中 → 右详情切目录').toHaveText('Season 1');
      await expect(drawer.locator('.dt10-right .dt10-seg[data-setp="6"]'), '目录分段带作用面提示')
        .toHaveAttribute('data-aq-tip', /作用于目录内全部 2 个文件/);
      await drawer.locator('.dt10-right .dt10-seg[data-setp="6"]').click();
      await expect.poll(() => prioPosts.length, '分段真提交(POST files/priority)').toBe(1);
      expect(prioPosts[0], '目录 = 整棵子树 indices 收集').toMatchObject({ priority: 6, indices: [0, 1] });
    });

    test(`dt11 树表批量: 勾选/子树三态/批量条/徽章循环真提交/主框三态/全局展开折叠/行级键盘/拖宽/右键隐藏(locked)/omitEmpty @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      const filesState = makeFiles();
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(filesState) }));
      const prioPosts = [];
      await stubPrioPosts(page, 'dt11', prioPosts, filesState);
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openContentVariant(page, '11');
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV11"]');
      const rows = anchor.locator('.group-row[data-table="drawerContentV11"]');

      // 4 列引擎表头(有 availability 数据 → 可用性列在座) + 行体 = 2 目录 + 4 文件
      await expect(anchor.locator('.group-head .h-cell')).toHaveCount(4);
      await expect(rows).toHaveCount(6);

      // 点行 = 勾选(目录 = 整棵子树): 点 Season 1 目录行 → 2 文件全勾 + 批量条浮出
      const s1 = rows.filter({ hasText: 'Season 1' }).first();
      await s1.click();
      await expect(drawer.locator('.dt11-foot'), '批量条浮出(2 文件)').toContainText('已选 2 个文件');
      await expect(s1, '目录行 is-chk').toHaveClass(/is-chk/);
      await expect(rows.filter({ hasText: 'E01 - intro.mkv' }).first(), '子树文件行同步勾选').toHaveClass(/is-chk/);
      const s1ck = s1.locator('input.dt11-ck');
      await expect(s1ck, '目录三态框全勾').toBeChecked();
      await expect(s1ck).not.toHaveAttribute('indeterminate', ''); // 全勾态无半选

      // 部分勾选 = 目录三态框半选(native indeterminate 声明式直持): 取消 E01 后 Season 1 半选
      await rows.filter({ hasText: 'E01 - intro.mkv' }).first().click();
      await expect(s1ck, '子树部分勾选 → 半选态').toHaveJSProperty('indeterminate', true);
      await rows.filter({ hasText: 'E01 - intro.mkv' }).first().click();
      await expect(s1ck, '恢复全勾').toBeChecked();

      // 批量条设优先级(真提交): 「最高」→ POST files/priority { priority: 7, indices: [0,1] }
      await drawer.locator('.dt11-foot .dt11-bp.max').click();
      await expect.poll(() => prioPosts.length, '批量优先级真提交').toBe(1);
      expect(prioPosts[0]).toMatchObject({ priority: 7, indices: [0, 1] });

      // 徽章循环(单文件, 逐次真实提交): E01 已随批量「最高」= 7(乐观写当帧可见, 桩把
      // priority 应用回 filesState = 模拟 qB 落库, 回执重拉后仍 7) → PRIO_CYCLE [0,1,6,7]
      // 循环 7 → 0(跳过)
      await rows.filter({ hasText: 'E01 - intro.mkv' }).first().locator('.dt11-pbadge').click();
      await expect.poll(() => prioPosts.length).toBe(2);
      expect(prioPosts[1]).toMatchObject({ priority: 0, indices: [0] });

      // 清除勾选 → 批量条回落汇总条
      await drawer.locator('.dt11-foot .dt11-clear').click();
      await expect(drawer.locator('.dt11-foot')).toContainText('个文件 · 合计');

      // 主勾选框三态(R5#122): 点主框 = toggleSet 全量文件路径 —— 全部文件行 is-chk +
      // 批量条计数 + POST indices 覆盖全部文件; 再点一次全不选回落; 部分勾选 = 半选态
      const master = drawer.locator('.dt11-tools input[data-ckmaster]');
      const fileRows = anchor.locator('.group-row.file[data-table="drawerContentV11"]');
      await master.click();
      await expect(master, '主框全勾态').toBeChecked();
      await expect(fileRows, '全量文件行在场').toHaveCount(4);
      for (let i = 0; i < 4; i++) await expect(fileRows.nth(i), `文件行 ${i} is-chk`).toHaveClass(/is-chk/);
      await expect(drawer.locator('.dt11-foot'), '批量条计数 = 全部文件').toContainText('已选 4 个文件');
      await drawer.locator('.dt11-foot .dt11-bp[data-bp="1"]').click();
      await expect.poll(() => prioPosts.length, '主框全选后批量条真提交').toBe(3);
      expect(prioPosts[2], 'POST indices 覆盖全部文件').toMatchObject({ priority: 1, indices: [0, 1, 2, 3] });
      await master.click();
      await expect(master, '再点主框 = 全不选回落').not.toBeChecked();
      for (let i = 0; i < 4; i++) await expect(fileRows.nth(i)).not.toHaveClass(/is-chk/);
      await expect(drawer.locator('.dt11-foot'), '批量条回落汇总条').toContainText('个文件 · 合计');
      await rows.filter({ hasText: 'E01 - intro.mkv' }).first().click();
      await expect(master, '部分勾选 = 主框半选(native indeterminate)').toHaveJSProperty('indeterminate', true);
      await rows.filter({ hasText: 'E01 - intro.mkv' }).first().click();
      await expect(master, '清掉部分勾选 → 主框回未勾态').not.toBeChecked();

      // 工具条全局「展开/折叠」(R5#124): 折叠 = 全目录集入账(目录子树全收拢), 展开还原。
      // 根级文件(bonus.txt)不属于任何目录, 不受折叠影响 —— 剩 2 目录行 + 1 根级文件
      await drawer.locator('.dt11-tools [data-fold="close"]').click();
      await expect(rows.filter({ hasText: 'intro.mkv' }), '折叠: 目录内文件全收拢').toHaveCount(0);
      await expect(rows.filter({ hasText: 'part.mkv' })).toHaveCount(0);
      await expect(rows.filter({ hasText: 'finale.mkv' })).toHaveCount(0);
      await expect(rows, '剩 2 目录行 + 1 根级文件').toHaveCount(3);
      await drawer.locator('.dt11-tools [data-fold="open"]').click();
      await expect(rows, '全局展开后行数还原').toHaveCount(6);

      // 行级键盘(R5#123, 照 dt10 键盘段): roving 锚点 → ArrowDown 移焦 → Enter 勾选翻 is-chk
      await rows.first().focus();
      await page.keyboard.press('ArrowDown');
      const focused = await page.evaluate(() => document.activeElement.getAttribute('data-dt-key'));
      expect(focused, '方向键移焦: 首行目录 → 首个文件').toBe('Season 1/E01 - intro.mkv');
      await page.keyboard.press('Enter');
      await expect(rows.filter({ hasText: 'E01 - intro.mkv' }).first(), 'Enter = 勾选该文件').toHaveClass(/is-chk/);
      await expect(drawer.locator('.dt11-foot'), '批量条随键盘勾选浮出').toContainText('已选 1 个文件');
      // 重渲后焦点链被打断(锚移动), 重取焦再 Enter = 取消勾选(与 click 同口径双向)
      await rows.filter({ hasText: 'E01 - intro.mkv' }).first().focus();
      await page.keyboard.press('Enter');
      await expect(rows.filter({ hasText: 'E01 - intro.mkv' }).first(), '再 Enter = 取消勾选').not.toHaveClass(/is-chk/);
      await expect(drawer.locator('.dt11-foot')).toContainText('个文件 · 合计');

      // 拖宽: 名称列 resizer 右拖 60px → 按 table-id 落盘(autoqb_cols_v5)
      const resizer = anchor.locator('.h-cell.hc-name .resizer');
      const rb = await resizer.boundingBox();
      await page.mouse.move(rb.x + rb.width / 2, rb.y + rb.height / 2);
      await page.mouse.down();
      await page.mouse.move(rb.x + rb.width / 2 + 60, rb.y + rb.height / 2, { steps: 6 });
      await page.mouse.up();
      const cols = JSON.parse(await page.evaluate(() => localStorage.getItem('autoqb_cols_v5') || '{}'));
      expect(cols?.pages?.drawerContentV11?.w?.name, '拖宽必须按 table-id 持久化(引擎同一漏斗)').toBeTruthy();

      // 右键隐藏: name 列 locked(交互件在格内: 勾选框/折叠钮/徽章 —— 隐藏动作项变必显提示,
      // 不可执行); size 列可隐藏 + 落盘
      await anchor.locator('.h-cell.hc-name').click({ button: 'right' });
      await expect(page.locator('.ctx-menu').locator('.ctx-item', { hasText: '「名称」为必显列' }),
        'name 列 locked: 勾选框+折叠钮+徽章在格内, 隐藏 name = 废掉三个交互件(L4)').toHaveCount(1);
      await expect(page.locator('.ctx-menu').locator('.ctx-item', { hasText: /^隐藏「/ }),
        'locked 列无隐藏动作项').toHaveCount(0);
      await page.mouse.click(300, 60); // 点空白收层(Esc 是全局关抽屉快捷键, 不能用)
      await anchor.locator('.h-cell.hc-size').click({ button: 'right' });
      await page.locator('.ctx-menu').locator('.ctx-item', { hasText: '隐藏「大小」' }).click();
      await expect(anchor.locator('.group-head .h-cell'), '右键隐藏即时生效').toHaveCount(3);

      // 刷新偏好回放: 模板 + 列偏好都持久化
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer2 = await openContentVariant(page, '11');
      const anchor2 = drawer2.locator('[data-dt-table-anchor="drawerContentV11"]');
      await expect(anchor2.locator('.group-head .h-cell'), '刷新后隐藏偏好回放(3 列)').toHaveCount(3);
    });

    test(`dt11 可用性列常驻: 全部文件无 availability → 列不省略, 值出 — 占位(4 列; 26-10-13-0811 删 omitEmpty) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFiles(false)) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openContentVariant(page, '11');
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV11"]');

      /* 2026-10-13 行为变更(计划 26-10-13-0811 L1 铁律): 原 omitEmpty 渐进列随数据整列
       * 消失 —— 轨道数浮动, 是「多一格/少一列」类症状的温床, 已删. 列常驻(4 列),
       * 缺值由渲染器 avTxt 出 — 占位. 几何一致性另见 dt-table-layout-parity.spec.mjs. */
      await expect(anchor.locator('.group-head .h-cell'), '列常驻(渐进已删)').toHaveCount(4);
      await expect(anchor.locator('.group-head .hc-av')).toHaveCount(1);
      const avCells = anchor.locator('.group-row .dt11-av');
      const n = await avCells.count();
      expect(n, '值格与行数一致').toBeGreaterThan(0);
      for (let i = 0; i < n; i++) {
        await expect(avCells.nth(i), '缺 availability 出 — 占位').toHaveText('—');
      }
    });

    test(`dt11 未完成判据与计数同源: progress∈[0.995,1) 计入计数且筛选可见(R5#109 整数舍入漂移) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFilesRounding()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openContentVariant(page, '11');
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV11"]');
      const rows = anchor.locator('.group-row[data-table="drawerContentV11"]');

      // 计数侧(derive 原始 0-1 prog<1): 0.999 被计入「未完成 1」—— 该文件确实未完成
      const missChip = drawer.locator('.dt11-chip[data-f="miss"]');
      await expect(missChip.locator('b'), 'chip 计数按原始值(0.999 计入)').toHaveText('1');
      // 筛选侧: 修前用 drawerFileRows 的整数舍入 r.progress(0.999 -> 100)判 r.progress<100,
      // 同屏「未完成 1」计数与筛选列表自相矛盾(文件被计数却被藏掉); 10 号同数据一位小数
      // 判据会显示 —— 跨变体漂移。修后与计数同源(原始值), 0.999 文件必须可见。
      await missChip.click();
      await expect(rows.filter({ hasText: 'E02 - almost.mkv' }), '舍入界文件在「未完成」筛选下可见').toHaveCount(1);
      await expect(rows.filter({ hasText: 'E01 - done.mkv' }), '完整文件离场').toHaveCount(0);
      // 目录行(dirMatch 用 s.missCnt 原始值)与子文件同屏一致
      await expect(rows, '目录行 + 可见文件行').toHaveCount(2);
    });

    test(`dt10 空态行兜底: 筛选无命中出「该筛选下没有文件」+ 透明样式(R5#110 非 29px 幽灵行) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFilesClean()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '10' })));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openContentVariant(page, '10');
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV10"]');
      const rows = anchor.locator('.group-row[data-table="drawerContentV10"]');
      await expect(rows).toHaveCount(2);

      // 「不下载」筛选无命中(数据无 priority=0)→ rowsFn 合成 __empty 占位行
      await drawer.locator('.dt10-chip[data-f="skip"]').click();
      const emptyRow = anchor.locator('.group-row.empty-row[data-table="drawerContentV10"]');
      await expect(emptyRow, '空态占位行在场').toHaveCount(1);
      await expect(emptyRow, '提示文案与 11 号同口径').toContainText('该筛选下没有文件');
      // 样式兜底(修前: 29px 定高 + hairline 底边框 + 首格吃引擎 --bg-card 重锚的幽灵行)
      const style = await emptyRow.evaluate((el) => ({
        bbw: getComputedStyle(el).borderBottomWidth,
        cellBg: getComputedStyle(el.firstElementChild).backgroundColor,
      }));
      expect(style.bbw, '空态行无底边框').toBe('0px');
      expect(style.cellBg, '空态行首格透明(不吃 --bg-card 重锚)').toBe('rgba(0, 0, 0, 0)');
      await emptyRow.hover();
      const hoverBg = await emptyRow.evaluate((el) => getComputedStyle(el).backgroundColor);
      expect(hoverBg, '空态行 hover 仍透明(不并行 hover 底色)').toBe('rgba(0, 0, 0, 0)');
      // 切回「全部」筛选 → 占位行离场
      await drawer.locator('.dt10-chip[data-f="all"]').click();
      await expect(emptyRow).toHaveCount(0);
      await expect(rows).toHaveCount(2);
    });

    test(`dt12 空间树图真手势: 悬停互联/组头折叠/点选联动信息条/仅看未完成/键盘选中(R5#120 首轮) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFiles12()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '12' })));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();
      await expect(drawer.locator('.dt12-wrap')).toBeVisible({ timeout: 10_000 });

      // 树图绘制 + 主导目录组头(占 ~98% 体积, 块必超组头最小尺寸判据 110x44)
      const alpha = drawer.locator('.dt12-blk[data-blk="Big/A - alpha.mkv"]');
      await expect(alpha, '树图块绘制(squarify 布局)').toBeVisible({ timeout: 10_000 });
      const gh = drawer.locator('.dt12-gh[data-gh="Big"]');
      await expect(gh, '主导目录组头在场').toBeVisible();

      // 悬停互联(纯前端): 悬停树图块 → 体积榜对侧行加 hl; 移开 → 摘
      const alphaRow = drawer.locator('.dt12-row[data-row="Big/A - alpha.mkv"]');
      await alpha.hover();
      await expect(alphaRow, '块悬停 → 对侧行高亮').toHaveClass(/hl/);
      await drawer.locator('.dt12-hint').hover();
      await expect(alphaRow, '移开 → 高亮摘除').not.toHaveClass(/hl/);

      // 组头折叠: 目录收成单块聚合; 再点展开还原叶块
      await gh.click();
      await expect(drawer.locator('.dt12-blk[data-blk="Big"]'), '折叠 → 整目录单块').toBeVisible();
      await expect(alpha, '折叠 → 叶块离场').toHaveCount(0);
      await gh.click();
      await expect(alpha, '展开 → 叶块还原').toBeVisible();

      // 点选联动信息条: 块选中 → 信息条浮出 + 块 sel + 对侧行 is-sel; 取消钮收条
      await alpha.click();
      await expect(drawer.locator('.dt12-info.on .dt12-fin .nm'), '信息条浮出').toHaveText('A - alpha.mkv');
      await expect(alpha, '选中块描边').toHaveClass(/sel/);
      await expect(alphaRow, '对侧行选中态').toHaveClass(/is-sel/);
      await drawer.locator('.dt12-close').click();
      await expect(drawer.locator('.dt12-info.on'), '取消选中 → 信息条收起').toHaveCount(0);

      // 仅看未完成: wrap 挂 fmiss 类(完整块/行降透明度), 再点还原
      await drawer.locator('.dt12-chip[data-fmiss]').click();
      await expect(drawer.locator('.dt12-wrap'), 'fmiss 态在 wrap 上').toHaveClass(/fmiss/);
      await drawer.locator('.dt12-chip[data-fmiss]').click();
      await expect(drawer.locator('.dt12-wrap')).not.toHaveClass(/fmiss/);

      // 键盘选中(issue 26-10-07-0846): 榜行 roving(首行 tabindex=0) → ArrowDown 移焦
      // → Enter = 选中联动信息条
      const listRows = drawer.locator('.dt12-row[data-row]');
      await listRows.first().focus();
      await page.keyboard.press('ArrowDown');
      const focused = await page.evaluate(() => document.activeElement.getAttribute('data-row'));
      expect(focused, '方向键移焦(体积榜行)').toBe('Big/B - beta.mkv');
      await page.keyboard.press('Enter');
      await expect(drawer.locator('.dt12-info.on .dt12-fin .nm'), 'Enter 选中 → 信息条联动').toHaveText('B - beta.mkv');
    });
  });
}
