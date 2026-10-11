// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst } from './lib/vm.mjs';

/**
 * 详情面板三张列表接入公共表壳(计划 26-10-11-2106 W2「三列表接表壳」) —— 面板内必须与主视图
 * **同源**的四件列交互: 拖宽 / 排序 / 右键隐藏 / 列偏好持久化, 外加列选择器的恢复入口。
 *
 * 为什么必须单独钉: 接壳前抽屉列表是自带 `<table class="drawer-table">` 的字符串 DOM —— 它**没有
 * 列模型**(对齐靠模板里手挂的 .num 类), 所以拖宽/排序/右键隐藏这四件在面板里**一件都没有**;
 * 接壳后它们全部来自 columns.js 这一套引擎(表头 <aq-table grid> 渲出的 .h-cell 挂 resizer /
 * 排序 click / contextmenu)。这套接线有三种**静默**坏法, 静态守阵一个都抓不住:
 *   ① 表头的 ref 拿不到 —— 表头在**页签组件**模板里, 根实例 $refs 取不到它; 若 columns.js 的
 *      `_headEl` 没有 DOM 兜底(按 `.group-head[data-table=…]` 查), 拖宽会**毫无反应**(不报错);
 *   ② 排序 scope 落错表 —— 表壳列头若把 scope 传成 undefined, `setSort` 会按**当前视图**解析,
 *      于是点抽屉列头排的是主视图, 抽屉自己的箭头永远不出现;
 *   ③ 列偏好没进同一份 v5 载荷 —— 隐藏的列刷新后自己回来。
 * 三条的真实手势就是本 spec 的①~④, ⑤ 钉"隐藏之后有地方能恢复"(抽屉表在列选择器里必须成组出现)。
 *
 * ⑥ 行键盘在面板内可用(W2 验收的第四件) —— 这条**不是**"面板自己吃 ↑↓", 而是方案A(计划
 * 26-10-03-0917 §3.2)定下的反身语义: 停靠面板是种子列表的**附属**不是浮层, 所以面板开着时
 * **列表行键盘必须保持存活**(scope 恒 "list"、drawer.open 不在 _kbOverlayBusy 名单), 面板再
 * 经 _kbFollowDrawer(200ms 防抖)跟着换目标。重写渲染层时这两处(渲染 vs 键位)分属不同文件,
 * 静态守阵只查得到"成员行在不在光标链上", 查不到"按下去被不被吞" —— 只能真按键。若哪天有人
 * 顺手把 drawer.open 塞回浮层名单, 面板一开 ↑↓ 全哑、面板永远停在同一颗种子上, 本用例先红。
 *
 * 锚点口径: 全部落在接壳后的**经典**(= Vue)态网格上 —— 行容器 .group-table、行
 * `.group-row[data-table="drawerTracker"]`、表头 `.group-head[data-table="drawerTracker"]`。
 * data-table 是列对齐(colAlignCss)与行宽(gridStyle)的锚, 也是本 spec 认表的方式(与主视图
 * 四张表同名同源, 但 id 前缀 drawer* 区分)。
 */

const WIDE = { width: 2560, height: 1200 };

const HEAD = '.group-head[data-table="drawerTracker"]';

async function openTrackerTab(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  await drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ }).click();
  return drawer;
}

for (const skin of SKINS) {
  test.describe(`抽屉三列表接表壳 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`Tracker 列表: 拖宽 / 排序 / 右键隐藏 / 列偏好持久化 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      const drawer = await openTrackerTab(page);

      const head = drawer.locator(HEAD);
      await expect(head).toBeVisible({ timeout: 5_000 });
      const cells = head.locator('.h-cell');
      // 列定义单点 = app.js 的 DRAWER_TRACKER_COLUMNS(URL/状态/种子/用户/消息/操作)
      await expect(cells).toHaveCount(6);

      // 表头在**页签组件内部**却不吸顶: .group-head 自带 position:sticky 是页面级口径(相对文档
      // 滚动), 面板里会盖住列表上方的工具条 —— 抽屉作用域把它改回 static(三皮肤成对)。
      expect(await head.evaluate((el) => getComputedStyle(el).position)).toBe('static');

      // ① 拖宽: 拖首列把手 +60px → 首列**生效宽度**写进 grid 模板(表头与行同取 gridStyle 一个引用)。
      // 这一条同时证明 `_headEl` 的 DOM 兜底成立 —— 拿不到表头元素时 startResize 第一行就 return,
      // 表现为"拖了完全没反应"(无报错, 静态守阵也看不见)。
      const firstTrack = () => head.evaluate((el) => parseFloat(getComputedStyle(el).gridTemplateColumns));
      const before = await firstTrack();
      const box = await cells.first().locator('.resizer').boundingBox();
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.down();
      await page.mouse.move(box.x + box.width / 2 + 60, box.y + box.height / 2, { steps: 10 });
      await page.mouse.up();
      expect(await firstTrack(), `拖宽后首列轨道应加宽(拖前 ${before}px)`).toBeGreaterThan(before + 30);

      // ② 排序: 点「状态」列头 → 该格出现排序箭头。箭头是 `v-if="sortKey === col.key"` 渲的, 而
      // sortKey 来自**本表**的 dtrkSortKey(`${DRAWER_TABLE_DEFS}.sort.gk`) —— scope 若落回主视图,
      // 本表箭头恒不出现(这条断言即失配)。
      const statusCell = cells.nth(1);
      await statusCell.click();
      await expect(statusCell.locator('.arrow .ico'), '点列头后本表排序箭头必须出现').toHaveCount(1);
      // 箭头只此一处 = 排序键确实写进了本表, 没顺带改到别的列
      await expect(head.locator('.h-cell:has(.arrow .ico)')).toHaveCount(1);
      // 行序也真的按它排(数据桩里状态值不唯一, 只断言"渲染出来了"以免绑死桩内容)
      await expect(drawer.locator('.group-row[data-table="drawerTracker"]').first()).toBeVisible();

      // ③ 右键隐藏: 表头右键 → 菜单(逐列"隐藏「X」") → 点击 → 该列出表。
      // !表头**独占右键**: 面板把"档位选择"的右键入口挂在 .drawer-body 上, 表头在里面 —— 列头
      // 若不拦冒泡就同时弹出密度档菜单。故这里顺带钉住"档位菜单没被带出来"(W5 后正文只有
      // 密度档一种右键菜单, 无模板菜单文案可言, 断言口径 = 完全无 ctx-menu)。
      await cells.nth(4).click({ button: 'right' });
      const hideItem = page.locator('.ctx-item', { hasText: '隐藏「消息」' });
      await expect(hideItem).toBeVisible({ timeout: 5_000 });
      await expect(page.locator('.ctx-menu').locator('.ctx-item', { hasText: '紧凑' }),
        '列头右键不得连带弹出密度档菜单').toHaveCount(0);
      await hideItem.click();
      await expect(head.locator('.h-cell.hc-msg')).toHaveCount(0);
      await expect(cells).toHaveCount(5);

      // ④ 持久化: 刷新 → 重开抽屉 → 仍是 5 列(列偏好落在**与主视图同一份** v5 载荷的独立 page 子树
      // 下 —— 新增 page 是向后兼容扩展, COLS_STORE_KEY 不升版本)
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer2 = await openTrackerTab(page);
      const head2 = drawer2.locator(HEAD);
      await expect(head2).toBeVisible({ timeout: 5_000 });
      await expect(head2.locator('.h-cell')).toHaveCount(5);
      await expect(head2.locator('.h-cell.hc-msg')).toHaveCount(0);

      // ⑤ 恢复入口: 列选择器必须把抽屉三表也列成组(「Tracker 列表 / 用户列表 / 文件列表」)。
      // 这是与计划 §07 括注的**有意偏差**(它说"不进 TABLE_PAGES 否则列选择器多出分组")—— 但右键
      // 隐藏是不可逆动作, 选择器不给入口就只能改 localStorage 才能把列找回来。用户 26-10-11 拍板
      // 「以与主视图一致为准则」, 计划 §11 变更记录已登记该偏差。
      await page.locator('.col-picker .table-tool').click();
      const colMenu = page.locator('.col-menu');
      await expect(colMenu).toBeVisible({ timeout: 5_000 });
      await expect(colMenu.locator('.col-menu-title', { hasText: 'Tracker 列表' })).toHaveCount(1);
      await expect(colMenu.locator('.col-menu-title', { hasText: '用户列表' })).toHaveCount(1);
      await expect(colMenu.locator('.col-menu-title', { hasText: '文件列表' })).toHaveCount(1);
      // 被隐藏的「消息」在选择器里呈**未勾选**态 —— 再点它即可恢复(round-trip)
      await expect(colMenu.locator('.col-menu-item:has-text("消息")')).not.toHaveClass(/\bon\b/);
      await colMenu.locator('.col-menu-item', { hasText: '消息' }).click();
      await expect(head2.locator('.h-cell.hc-msg')).toHaveCount(1);
      await expect(head2.locator('.h-cell')).toHaveCount(6);
    });

    test(`面板开着行键盘仍可用并驱动面板跟随(W2 第四件: 键位不被面板夺走) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // DOM 行序 = _kbRows 序(种子页 = filteredTorrents 平铺; 行窗口只是它的连续切片)
      const hashes = await page.locator('.torrent-row').evaluateAll((els) =>
        els.map((e) => e.getAttribute('data-hash')));
      expect(hashes.length, '需要 ≥2 个种子才能证"换了一行"(单行列表下光标不动也"通过")').toBeGreaterThan(1);

      // 双击首行开面板(双击前的两次 click 已把光标落在首行 —— 与显式打开同一行)
      await page.dblclick('.torrent-row >> nth=0', { force: true }); // force: 整表 2s 重渲染抢点击
      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 5_000 });
      await expect.poll(() => readInst(page, 'vm.drawer.hash'), { message: '面板应停在被双击的首行' })
        .toBe(hashes[0]);

      // ↓ : 面板开着时列表键位必须仍存活。面板若被误判成浮层(_kbOverlayBusy 含 drawer.open),
      //    这一键会被 502 行那道闸吞掉 —— 光标不动, 下一行断言即失配(无报错, 静默哑火)。
      await page.keyboard.press('ArrowDown');
      await expect(
        page.locator('.torrent-row.kb-cursor'),
        '面板开着时 ↓ 必须仍能移动列表光标(列表键位不得被面板夺走)',
      ).toHaveAttribute('data-hash', hashes[1]);

      // 面板跟随: _kbApplyCursor 尾部挂 _kbFollowDrawer(200ms 防抖 -> _switchDrawerTarget 换 hash)。
      // 跟随是**软切换**(保留旧数据 + 延迟遮罩), 故面板必须仍在 —— 掉成"跟随=先关再开"会闪。
      await expect.poll(() => readInst(page, 'vm.drawer.hash'), {
        message: '面板必须跟随行键盘换目标(200ms 防抖内)', timeout: 8_000,
      }).toBe(hashes[1]);
      await expect(drawer).toBeVisible();
    });

    test(`单栏: 正文右键弹当前页签的密度档选择(锚点解析回归) @fast (${skin})`, async ({ page }) => {
      /* W2 曾钉"右键锚点解析路径": _drawerMenuTab 首选旧插件宿主 data-dt-host(组件态不存在),
       * 落 closest("[data-dt-tab]") 再回落当前页签。W5(计划 26-10-11-2106)变体退役后插件宿主
       * 从 DOM 消失, 落点只剩 data-dt-tab / 当前页签两跳; 且各页签密度档选项集**同名**
       * (经典/紧凑), 菜单归属只能靠**效果**判别 —— 在 Tracker 页签右键选「紧凑」, 必须落到
       * trackers 的记忆(localStorage trackers=compact, general 不动)。若有人把菜单页签解析
       * 接错(比如固定 "general"), 菜单照样弹出、不报错 —— 只有这条效果断言能抓到。
       * 换档即换渲染分支(Vue 响应式, 无重挂机械): host 类即时翻转, 网格正文不中断。 */
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      const drawer = await openTrackerTab(page);
      const grid = drawer.locator('.group-row[data-table="drawerTracker"]');
      await expect(grid.first(), '正文即接壳后的网格').toBeVisible({ timeout: 5_000 });
      // W5 退役确认: 插件宿主(data-dt-host)不得复活
      await expect(drawer.locator('[data-dt-host]'), '变体插件宿主已退役, 不得出现在 DOM').toHaveCount(0);

      // 右键**行**(不是表头 —— 表头 @contextmenu.prevent.stop 独占, 见用例一 ③)
      await grid.first().click({ button: 'right' });
      const menu = page.locator('.ctx-menu');
      await expect(menu).toBeVisible({ timeout: 5_000 });
      await expect(menu.locator('.ctx-item', { hasText: '紧凑' }), '右键须弹密度档选项').toBeVisible();

      // 选「紧凑」→ 即时生效且落 trackers 记忆(不是 general)
      await menu.locator('.ctx-item', { hasText: '紧凑' }).click();
      await expect(drawer.locator('.drawer-body .dt-host:visible'), '换档即换渲染分支(host 类即时翻转)')
        .toHaveClass(/dd-compact/, { timeout: 5_000 });
      await expect(grid.first(), '换档不重建网格: 表壳行仍在').toBeVisible();
      const store = JSON.parse(await page.evaluate(() => localStorage.getItem('autoqb.ui.drawerTpl') || '{}'));
      expect(store.trackers, '右键菜单必须落当前页签(trackers)的记忆').toBe('compact');
      expect(store.general, '不得落 general 的记忆').toBe('classic');
    });
  });
}
