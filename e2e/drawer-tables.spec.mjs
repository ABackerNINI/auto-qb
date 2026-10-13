// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst } from './lib/vm.mjs';
import { expectNoDeadClass } from './lib/dt-dead-class.mjs';

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
 * 锚点口径: 全部落在变体桥渲染出的引擎网格上 —— 行容器 .group-table、行
 * `.group-row[data-table="drawerTrackerV06"]`、表头 `.group-head[data-table="drawerTrackerV06"]`。
 * data-table 是列对齐(colAlignCss)与行宽(gridStyle)的锚, 也是本 spec 认表的方式。
 * !2026-10-14: 四内容页签的经典渲染链(drawerTracker/drawerPeer/drawerFile 三张经典表)已随
 * 「移除四内容页签经典 UI」整体退役 —— 本 spec 的表交互用例改钉变体 06「增强表格」(Tracker
 * 页签唯一带 8 列引擎表头的变体; 04 卡片/05 分段无表头, 列交互本就不适用)。
 */

const WIDE = { width: 2560, height: 1200 };

const HEAD = '.group-head[data-table="drawerTrackerV06"]';

/* 缺省进 Tracker 页签时先把变体钉到 06(缺省档是 04 卡片态, 无表头可交互) */
const TPL06 = { trackers: '06' };

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

    test(`Tracker 变体表(增强表格 06): 拖宽 / 排序 / 右键隐藏 / 列偏好持久化 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.addInitScript(
        (o) => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify(o)),
        TPL06,
      );
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      const drawer = await openTrackerTab(page);

      const head = drawer.locator(HEAD);
      await expect(head).toBeVisible({ timeout: 5_000 });
      const cells = head.locator('.h-cell');
      // 列定义单点 = app.js 的 DRAWER_TRACKER_V06_COLUMNS(状态/Tracker/tier/种子/用户/完成下载/下次重新汇报/操作)
      await expect(cells).toHaveCount(8);

      // 表头在变体外壳里却不吸顶: .group-head 自带 position:sticky 是页面级口径(相对文档
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

      // ② 排序: 点「tier」列头 → 该格出现排序箭头。箭头是 `v-if="sortKey === col.key"` 渲的, 而
      // sortKey 来自**本表**的 dyn 排序态(`${DRAWER_TABLE_DEFS}.sort.dyn`, dtSortState 映射) ——
      // scope 若落回主视图, 本表箭头恒不出现(这条断言即失配)。
      const tierCell = cells.nth(2);
      await tierCell.click();
      await expect(tierCell.locator('.arrow .ico'), '点列头后本表排序箭头必须出现').toHaveCount(1);
      // 箭头只此一处 = 排序键确实写进了本表, 没顺带改到别的列
      await expect(head.locator('.h-cell:has(.arrow .ico)')).toHaveCount(1);
      // 行序也真的按它排(数据桩里 tier 值不唯一, 只断言"渲染出来了"以免绑死桩内容)
      await expect(drawer.locator('.group-row[data-table="drawerTrackerV06"]').first()).toBeVisible();

      // ③ 右键隐藏: 表头右键 → 菜单(逐列"隐藏「X」") → 点击 → 该列出表。
      // !表头**独占右键**: 面板把"模板选择"的右键入口挂在 .drawer-body 上, 表头在里面 —— 列头
      // 若不拦冒泡就同时弹出模板菜单。故这里顺带钉住"模板菜单没被带出来"(变体候选是各页签
      // 模板菜单才有的项, 足以判别)。
      await cells.nth(2).click({ button: 'right' });
      const hideItem = page.locator('.ctx-item', { hasText: '隐藏「tier」' });
      await expect(hideItem).toBeVisible({ timeout: 5_000 });
      await expect(page.locator('.ctx-menu').locator('.ctx-item', { hasText: '状态卡片栅格' }),
        '列头右键不得连带弹出模板选择菜单').toHaveCount(0);
      await hideItem.click();
      await expect(head.locator('.h-cell.hc-tier')).toHaveCount(0);
      await expect(cells).toHaveCount(7);

      // ④ 持久化: 刷新 → 重开抽屉 → 仍是 7 列(列偏好落在**与主视图同一份** v5 载荷的独立 page 子树
      // 下 —— 新增 page 是向后兼容扩展, COLS_STORE_KEY 不升版本)
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer2 = await openTrackerTab(page);
      const head2 = drawer2.locator(HEAD);
      await expect(head2).toBeVisible({ timeout: 5_000 });
      await expect(head2.locator('.h-cell')).toHaveCount(7);
      await expect(head2.locator('.h-cell.hc-tier')).toHaveCount(0);

      // ⑤ 恢复入口: 列选择器必须把**当前选中变体表**也列成组(「Tracker 表·增强表格」)。这是与
      // 计划 §07 括注的**有意偏差**(它说"不进 TABLE_PAGES 否则列选择器多出分组")—— 但右键
      // 隐藏是不可逆动作, 选择器不给入口就只能改 localStorage 才能把列找回来。变体表的过滤口径:
      // 带 variantTab 的表只在对应变体被选中时进选择器(26-10-12-0527 U1)。
      await page.locator('.col-picker .table-tool').click();
      const colMenu = page.locator('.col-menu');
      await expect(colMenu).toBeVisible({ timeout: 5_000 });
      await expect(colMenu.locator('.col-menu-title', { hasText: 'Tracker 表·增强表格' })).toHaveCount(1);
      // 被隐藏的「tier」在选择器里呈**未勾选**态 —— 再点它即可恢复(round-trip)
      await expect(colMenu.locator('.col-menu-item:has-text("tier")')).not.toHaveClass(/\bon\b/);
      await colMenu.locator('.col-menu-item', { hasText: 'tier' }).click();
      await expect(head2.locator('.h-cell.hc-tier')).toHaveCount(1);
      await expect(head2.locator('.h-cell')).toHaveCount(8);
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

    test(`单栏: 正文右键弹当前页签的模板选择(锚点解析回归) @fast (${skin})`, async ({ page }) => {
      /* 2026-10-10 起右键锚点解析路径: _drawerMenuTab 首选宿主 data-dt-host(2026-10-14 起宿主 id
       * 恒等于页签名 —— 流量双宿主已移除), 落 closest("[data-dt-tab]")(合并列才有)再回落当前
       * 页签。四内容页签此后恒为变体态(经典渲染链已删, 宿主恒在), 故本用例的效果断言是: 在
       * Tracker 页签右键选变体, 必须落到 trackers 的记忆(localStorage trackers=<id>, general 不动)。
       * 若有人把菜单页签解析接错(比如固定 "general"), 菜单照样弹出、不报错 —— 只有这条效果断言
       * 能抓到。菜单不再有「经典」项(2026-10-14): 四内容页签只有三个变体候选。 */
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      const drawer = await openTrackerTab(page);
      // 缺省档 = 该页签首个变体 04(状态卡片栅格); 宿主恒在且挂载态带 .dt-tpl(限宽作用域类)
      const host = drawer.locator('.drawer-body .dt-host[data-dt-host="trackers"]');
      await expect(host, '变体宿主恒在(经典渲染链已移除)').toHaveCount(1);
      await expect(host).toHaveClass(/dt-tpl/, { timeout: 5_000 });
      const cardRow = drawer.locator('.group-row[data-table="drawerTrackerV04"]').first();
      await expect(cardRow, '缺省变体 04 正文即接桥后的网格').toBeVisible({ timeout: 5_000 });
      // 死类守阵(坑档 esc-attr-quote-dead-class): 变体(dtHtml 字符串 DOM)态全文档零「类名含引号」
      await expectNoDeadClass(page, '变体 04 挂载态');

      // 右键**行**(不是表头 —— 表头 @contextmenu.prevent.stop 独占, 见用例一 ③)
      await cardRow.click({ button: 'right' });
      const menu = page.locator('.ctx-menu');
      await expect(menu).toBeVisible({ timeout: 5_000 });
      await expect(menu.locator('.ctx-item', { hasText: '经典' }),
        '经典档已整体移除, 模板菜单不得再有该项').toHaveCount(0);
      await expect(menu.locator('.ctx-item', { hasText: '增强表格' }),
        'Tracker 页签菜单须出变体候选').toBeVisible();

      // 选变体「增强表格」→ 即时挂载且落 trackers 记忆(不是 general)
      await menu.locator('.ctx-item', { hasText: '增强表格' }).click();
      await expect(drawer.locator('.group-row[data-table="drawerTrackerV06"]').first(),
        '选变体即挂新表(宿主仍带 .dt-tpl)').toBeVisible({ timeout: 5_000 });
      // 死类守阵: 变体 06(dtHtml 字符串 DOM)态全文档零「类名含引号」—— 全源扫描零「整段属性进
      // 插值」形态, 该缺陷只在 W2 已删的旧经典页存在过; 此 pin 防回潮。
      await expectNoDeadClass(page, '变体 06 挂载态');
      const store = JSON.parse(await page.evaluate(() => localStorage.getItem('autoqb.ui.drawerTpl') || '{}'));
      expect(store.trackers, '右键菜单必须落当前页签(trackers)的记忆').toBe('06');
      expect(store.general, '不得落 general 的记忆(未动页签落其缺省档 = 首个变体 01)').toBe('01');

      // 反向过渡: 变体 DOM 内右键仍归 trackers(宿主分支命中 data-dt-host) —— 换回 04 卡片态
      await host.click({ button: 'right' });
      await expect(menu).toBeVisible({ timeout: 5_000 });
      await menu.locator('.ctx-item', { hasText: '状态卡片栅格' }).click();
      await expect(drawer.locator('.group-row[data-table="drawerTrackerV04"]').first(),
        '反向切换后 04 网格回归').toBeVisible({ timeout: 5_000 });
      const store2 = JSON.parse(await page.evaluate(() => localStorage.getItem('autoqb.ui.drawerTpl') || '{}'));
      expect(store2.trackers, '反向切换仍落 trackers 记忆').toBe('04');
    });
  });
}
