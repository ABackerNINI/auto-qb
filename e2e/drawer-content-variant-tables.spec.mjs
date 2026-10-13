// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
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
 * 10 = 3 列(name/size/prog), 11 = 5 列(ck/name/size/prog/av)。
 *
 * 手势清单(每条都是真手势, 不借道 vm):
 *   10: 树渲染(目录聚合徽章/缩进层级) + 交互件收编 name 格(折叠钮在格首/徽章在格尾, 3 列
 *       行 = 不占列) + 折叠(子树真收拢) + 筛选 chips + 行选中联动右详情(点行/取消)
 *       + 行级键盘(roving ArrowDown + Enter 激活, issue 26-10-07-0846 真机红验)
 *       + 徽章点击不夺行选中;
 *   11: 5 列表头 + 勾选(点行 = 勾选/目录 = 子树三态, 批量条浮出) + 目录三态框 indeterminate
 *       + 徽章循环真提交(POST files/priority 载荷断言) + 拖宽落盘 + 右键隐藏(locked 列无隐藏项)
 *       + 刷新偏好回放 + 可用性列常驻(无 availability 数据值出 — 占位)。
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

    test(`dt10 树 + 详情: 折叠/筛选/选中联动右详情/行级键盘 roving @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFiles()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '10' })));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
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
    });

    test(`dt11 树表批量: 勾选/子树三态/批量条/徽章循环真提交/拖宽/右键隐藏(locked)/omitEmpty @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFiles()) }));
      const prioPosts = [];
      await page.route('**/api/torrents/*/files/priority', async (route) => {
        prioPosts.push(route.request().postDataJSON());
        await route.fulfill({ contentType: 'application/json', body: '{}' });
      });
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openContentVariant(page, '11');
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV11"]');
      const rows = anchor.locator('.group-row[data-table="drawerContentV11"]');

      // 5 列引擎表头(有 availability 数据 → 可用性列在座) + 行体 = 2 目录 + 4 文件
      await expect(anchor.locator('.group-head .h-cell')).toHaveCount(5);
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

      // 徽章循环(单文件, 逐次真实提交): E01 正常(1) → 高(6)
      await rows.filter({ hasText: 'E01 - intro.mkv' }).first().locator('.dt11-pbadge').click();
      await expect.poll(() => prioPosts.length).toBe(2);
      expect(prioPosts[1]).toMatchObject({ priority: 6, indices: [0] });

      // 清除勾选 → 批量条回落汇总条
      await drawer.locator('.dt11-foot .dt11-clear').click();
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

      // 右键隐藏: ck/name 两列 locked(交互件在格内: 勾选框/折叠钮/徽章 —— 隐藏动作项变必显提示,
      // 不可执行); size 列可隐藏 + 落盘
      await anchor.locator('.h-cell.hc-ck').click({ button: 'right' });
      await expect(page.locator('.ctx-menu').locator('.ctx-item', { hasText: '为必显列' }),
        'locked 列(勾选)只出必显提示 —— 隐藏动作不可执行(隐藏即废勾选功能)').toHaveCount(1);
      await expect(page.locator('.ctx-menu').locator('.ctx-item', { hasText: /^隐藏「/ }),
        'locked 列无隐藏动作项').toHaveCount(0);
      await page.mouse.click(300, 60); // 点空白收层(Esc 是全局关抽屉快捷键, 不能用)
      await anchor.locator('.h-cell.hc-name').click({ button: 'right' });
      await expect(page.locator('.ctx-menu').locator('.ctx-item', { hasText: '「名称」为必显列' }),
        'name 列 locked: 折叠钮+徽章在格内, 隐藏 name = 废掉两个交互件(L4)').toHaveCount(1);
      await page.mouse.click(300, 60);
      await anchor.locator('.h-cell.hc-size').click({ button: 'right' });
      await page.locator('.ctx-menu').locator('.ctx-item', { hasText: '隐藏「大小」' }).click();
      await expect(anchor.locator('.group-head .h-cell'), '右键隐藏即时生效').toHaveCount(4);

      // 刷新偏好回放: 模板 + 列偏好都持久化
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer2 = await openContentVariant(page, '11');
      const anchor2 = drawer2.locator('[data-dt-table-anchor="drawerContentV11"]');
      await expect(anchor2.locator('.group-head .h-cell'), '刷新后隐藏偏好回放(4 列)').toHaveCount(4);
    });

    test(`dt11 可用性列常驻: 全部文件无 availability → 列不省略, 值出 — 占位(5 列; 26-10-13-0811 删 omitEmpty) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFiles(false)) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openContentVariant(page, '11');
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV11"]');

      /* 2026-10-13 行为变更(计划 26-10-13-0811 L1 铁律): 原 omitEmpty 渐进列随数据整列
       * 消失 —— 轨道数浮动, 是「多一格/少一列」类症状的温床, 已删。列常驻(5 列),
       * 缺值由渲染器 avTxt 出 — 占位。几何一致性另见 dt-table-layout-parity.spec.mjs。 */
      await expect(anchor.locator('.group-head .h-cell'), '列常驻(渐进已删)').toHaveCount(5);
      await expect(anchor.locator('.group-head .hc-av')).toHaveCount(1);
      const avCells = anchor.locator('.group-row .dt11-av');
      const n = await avCells.count();
      expect(n, '值格与行数一致').toBeGreaterThan(0);
      for (let i = 0; i < n; i++) {
        await expect(avCells.nth(i), '缺 availability 出 — 占位').toHaveText('—');
      }
    });
  });
}
