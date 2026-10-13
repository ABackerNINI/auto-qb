// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { expectNoDeadClass } from './lib/dt-dead-class.mjs';

/**
 * 抽屉页签合并(R2 计划 26-10-09-2219 · R3 修订) —— 单开关 / 合并页签 / 双列布局 / 宽度门:
 *   1. 宽视口(≥1920): 正文右键 → 菜单「合并页签」可用 → 点击 → 页签栏收敛为
 *      [常规&内容][Tracker&用户] 两张合并页签, 正文双列(列头 常规/内容, 两列各挂本页签当前所选实现);
 *      再右键 → 勾选态在 → 再点已开启项 → 关闭, 页签栏回四页签单栏。
 *   2. R3 回归(用户报「选择并排后 tracker/用户标签显示常规/内容且为空」): 合并开启下点
 *      [Tracker&用户] 合并页签 → 列头变 Tracker/用户 且两列有内容(不再渲染旧对列头 + 空列)。
 *   3. 窄视口(<1920): 菜单项置灰(.is-gated), 点击零状态变化(dtToggleMerge 双保险拦截), 四页签原样。
 *   4. 2026-10-10 模板选择迁右键: 合并态右键左列弹常规变体、右列弹内容变体(菜单选项集按命中列),
 *      两列各自选择互不影响。
 *   5. 2026-10-10 用户报「合并后右侧空白右键弹左列模板」回归: 右列(内容)通常短于左列, 其下方
 *      空白格区/列间隙不落在任何 .dt-col 元素上 —— 右键仍须归右列(不得回落当前/左列)。
 * 断言口径: 真实手势(右键 click button:'right'), 不借道 vm。
 *
 * !W7(计划 26-10-11-2106)恢复注: W5 曾把右键模板选择改声明式密度档、变体整体退役 —— 用户裁定
 * 越权, 变体与选择层已按 W4 期形态原样恢复, 本 spec 同轮恢复 W5 前口径:
 *   ·页签正文是「经典 Vue 组件 / 变体字符串 DOM」双实现: 经典组件根带 `.dt-host` 类但**不带**
 *    data-dt-host(互斥双分支保证同一锚全 DOM 唯一), 变体挂在 `[data-dt-host]` 宿主上(挂载态
 *    加 `.dt-tpl` 类);
 *   ·列表锚点: 经典走接壳后的表壳(.group-table + .group-row[data-table="drawer<Tab>"] + cells
 *    渲染器, 拖宽/排序/右键隐藏/列偏好与主视图同源), 变体自带模板 DOM。
 */

const WIDE = { width: 2560, height: 1200 };
const NARROW = { width: 1280, height: 800 };

const MERGE_ITEM = '.ctx-item:has-text("合并页签")';

async function openTorrentDrawer(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  return drawer;
}

for (const skin of SKINS) {
  test.describe(`抽屉页签合并 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`宽视口: 合并页签开关 + 双列 + 切对不受污染 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await page.waitForTimeout(300);

      // 默认四页签(合并关闭): Tracker 单页签在
      await expect(drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ })).toBeVisible();

      // 开启合并: 右键 → 单开关「合并页签」(门内可点)
      await drawer.locator('.drawer-body').click({ button: 'right' });
      const menu = page.locator('.ctx-menu');
      await expect(menu).toBeVisible();
      const item = menu.locator(MERGE_ITEM);
      await expect(item).not.toHaveClass(/is-gated/);
      await item.click();

      // 页签栏收敛为两合并页签(四页签隐去)
      await expect(drawer.locator('.drawer-tabs button', { hasText: '常规&内容' })).toBeVisible();
      await expect(drawer.locator('.drawer-tabs button', { hasText: 'Tracker&用户' })).toBeVisible();
      await expect(drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ })).toHaveCount(0);

      // gc 双列: 列头 常规/内容; 两列正文都渲染出来(经典 = Vue 组件, 组件根 .dt-host)
      const split = drawer.locator('.drawer-split');
      await expect(split).toBeVisible({ timeout: 5_000 });
      await expect(split).toHaveAttribute('data-merge', 'gc');
      await expect(split.locator('.dt-col-head', { hasText: '常规' })).toBeVisible();
      await expect(split.locator('.dt-col-head', { hasText: '内容' })).toBeVisible();
      const genCol = split.locator('.dt-col[data-dt-tab="general"]');
      const conCol = split.locator('.dt-col[data-dt-tab="content"]');
      await expect(genCol.locator('.dt-host .drawer-sec').first()).toBeVisible();
      await expect(conCol.locator('.dt-host .drawer-toolbar')).toBeVisible();
      // 桩灌了文件数据: 内容列表格渲染出行(目录聚合行)
      // !W2 起内容列表格已接表壳: 行容器 .group-table + 行 .group-row[data-table="drawerFile"]
      // (不再是 <table class="drawer-table"><tbody><tr>)。
      await expect(conCol.locator('.dt-host .group-row[data-table="drawerFile"]').first()).toBeVisible();

      // R3 回归: 点 [Tracker&用户] 合并页签 → 列组换成 Tracker/用户 且两列有内容(不再空列)
      await drawer.locator('.drawer-tabs button', { hasText: 'Tracker&用户' }).click();
      await expect(split).toHaveAttribute('data-merge', 'tp');
      await expect(split.locator('.dt-col-head', { hasText: 'Tracker' })).toBeVisible();
      await expect(split.locator('.dt-col-head', { hasText: '用户' })).toBeVisible();
      // trackers 正文恒渲染工具栏(添加 tracker); peers 正文非空(表格或加载/空态)
      await expect(split.locator('.dt-col[data-dt-tab="trackers"] .dt-host .drawer-toolbar')).toBeVisible();
      await expect(split.locator('.dt-col[data-dt-tab="peers"] .dt-host')).not.toBeEmpty();
      await expect(split).not.toHaveAttribute('data-merge', 'gc');

      // 再右键 → 勾选态在 → 再点已开启项 = 关 → 双列消失, 页签栏回四页签(单栏宿主回归)
      await drawer.locator('.drawer-body').click({ button: 'right' });
      await expect(menu).toBeVisible();
      await expect(menu.locator(MERGE_ITEM).locator('.ctx-tick')).toHaveCount(1);
      await menu.locator(MERGE_ITEM).click();
      await expect(split).toHaveCount(0);
      await expect(drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ })).toBeVisible();
      await expect(drawer.locator('.drawer-tabs button', { hasText: 'Tracker&用户' })).toHaveCount(0);
    });

    test(`窄视口: 门内置灰可见, 点击零状态变化 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(NARROW);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);

      await drawer.locator('.drawer-body').click({ button: 'right' });
      const menu = page.locator('.ctx-menu');
      await expect(menu).toBeVisible();
      const item = menu.locator(MERGE_ITEM);
      await expect(item).toHaveClass(/is-gated/);

      // 置灰项点击 = 零状态变化(菜单保持打开, 不出双列, 页签栏仍四页签)
      await item.click();
      await expect(menu).toBeVisible();
      await expect(drawer.locator('.drawer-split')).toHaveCount(0);
      await expect(drawer.locator('.drawer-tabs button', { hasText: '常规&内容' })).toHaveCount(0);
      await expect(drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ })).toBeVisible();
      // 单栏正文不受扰动(常规面板的分组键值仍在; 单栏下只有当前页签渲染正文)
      await expect(drawer.locator('.drawer-body .dt-host .drawer-sec').first()).toBeVisible();
    });

    test(`门跨越: 窄视口无合并(标志保留) → 拉宽自动恢复 → 缩窗回落 @fast (${skin})`, async ({ page }) => {
      /* W4(计划 26-10-11-2106): 门是**暂态遮蔽** —— 缩窗过门双列回落单栏(drawerMerge 标志
       * 不动), 拉宽自动恢复。合并的两条监听(resize 防抖 150ms 回写 dtWinW + drawerMerge
       * $watch)W4 自 drawer_templates.js 迁 drawer.js, 本用例真手势钉住这条链: 预置
       * drawerMerge=on → 1280 开面板(无双列/页签栏四页签) → 拉宽 2560(双列自动恢复 + 页签栏
       * 收敛 + 第二列数据补给到位) → 缩回 1280(回落单栏) → 再拉宽(直接恢复 = 标志未被门撤销)。 */
      collectRuntimeErrors(page);
      await page.addInitScript(() => localStorage.setItem("autoqb.ui.drawerMerge", JSON.stringify("on")));
      await page.setViewportSize(NARROW);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);

      // 窄视口: 门遮蔽 —— 无双列, 页签栏仍是四页签(合并页签不在)
      const split = drawer.locator('.drawer-split');
      await expect(split).toHaveCount(0);
      await expect(drawer.locator('.drawer-tabs button', { hasText: '常规&内容' })).toHaveCount(0);
      await expect(drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ })).toBeVisible();

      // 拉宽过门: 双列自动恢复(列组 = gc, 初值常规页); 第二列(内容)数据补给到位(行渲染出来)
      await page.setViewportSize(WIDE);
      await expect(split, '拉宽过门后双列必须自动恢复(门是暂态遮蔽, 标志未被撤销)').toBeVisible({ timeout: 5_000 });
      await expect(split).toHaveAttribute('data-merge', 'gc');
      await expect(split.locator('.dt-col-head', { hasText: '常规' })).toBeVisible();
      await expect(split.locator('.dt-col[data-dt-tab="content"] .group-row[data-table="drawerFile"]').first())
        .toBeVisible({ timeout: 5_000 });
      await expect(drawer.locator('.drawer-tabs button', { hasText: '常规&内容' })).toBeVisible();

      // 缩回门外: 双列回落单栏, 四页签回来; 再拉宽直接恢复(标志仍在, 不需重新开合并)
      await page.setViewportSize(NARROW);
      await expect(split).toHaveCount(0);
      await expect(drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ })).toBeVisible();
      await page.setViewportSize(WIDE);
      await expect(split, '再拉宽必须直接恢复(门只遮蔽, 不撤销用户的合并意图)').toBeVisible({ timeout: 5_000 });
    });

    test(`合并态快捷键: Alt+1/2 切两合并页签, Alt+4 停用 @fast (${skin})`, async ({ page }) => {
      /* 2026-10-10 用户报「标签合并后没有同步修改快捷键」的回归: 合并成功时 Alt+1..5 按位次重排到
       * 三张可见页签(1=常规&内容 / 2=Tracker&用户 / 3=流量), 4/5 停用。此处真按键验 Alt+1/2 切对、
       * Alt+4 零变化(不借道 vm; 判据读双列 data-merge, 与用户所见一致)。 */
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await page.waitForTimeout(300);

      // 开合并: 右键单开关 -> 页签栏收敛, 默认双列 = gc
      await drawer.locator('.drawer-body').click({ button: 'right' });
      await page.locator('.ctx-menu').locator(MERGE_ITEM).click();
      const split = drawer.locator('.drawer-split');
      await expect(split).toHaveAttribute('data-merge', 'gc', { timeout: 5_000 });

      // Alt+2 -> Tracker&用户(tp); Alt+1 -> 回常规&内容(gc); Alt+4 合并态停用 -> 零变化(仍 gc)
      await page.keyboard.press('Alt+Digit2');
      await expect(split, 'Alt+2 必须切到 Tracker&用户 对').toHaveAttribute('data-merge', 'tp', { timeout: 5_000 });
      await page.keyboard.press('Alt+Digit1');
      await expect(split, 'Alt+1 必须切回 常规&内容 对').toHaveAttribute('data-merge', 'gc', { timeout: 5_000 });
      await page.keyboard.press('Alt+Digit4');
      await expect(split, 'Alt+4 合并态停用, 双列不得切换').toHaveAttribute('data-merge', 'gc', { timeout: 5_000 });
    });

    test(`合并态切换: 桥变体列换代不得抛错且内容不丢 @fast (${skin})`, async ({ page }) => {
      /* 2026-10-14 用户报「种子详情模板合并态切换时内容消失」的守阵。
       * 病根: 布局换代(合并开关 / 门跨越)的 patch 顺序 = 「先拆旧分支(旧锚随之离场) → 再挂新分支」,
       * 而父级 v-if 的 dtBridgeOn 是在**拆之前**求值的 —— 那一窗里 <teleport> 被挂到已消失的锚上;
       * Vue 生产版对此**静默不挂子节点**(无警告), 之后卸载该 teleport 时对 null component 解构抛
       * TypeError, 整次 patch 中断 ⇒ 抽屉停在半渲染态(用户所见「内容消失」, 且再开合并也回不去)。
       * 修法: teleport 的目标存在性判据(dtBridgeTargetOn)放进**桥组件自己的渲染拍** —— 与 teleport
       * 的 mount 同拍, 拿到的才是真值。
       * 断言口径(两层, 都不借道 vm):
       *   ①零运行期错误 —— patch 中断必留 console.error, 是本缺陷最直接的证据(installRuntimeErrorGuard
       *     会在 afterEach 兜底; 这里逐点提前断言, 让失败落在具体步骤上);
       *   ②内容不丢 —— 关合并后单栏当前页签的桥变体表格行仍在; 再开合并时双列与右列桥表行都回来。 */
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await page.waitForTimeout(300);

      const menu = page.locator('.ctx-menu');
      const noErr = (where) => expect(collectRuntimeErrors(page),
        `${where}: 合并态换代不得抛运行期错误(Teleport 目标缺失 ⇒ patch 中断 ⇒ 内容消失)`).toEqual([]);
      const pick = async (target, label) => {
        await target.click({ button: 'right' });
        await expect(menu).toBeVisible();
        await menu.locator('.ctx-item', { hasText: label }).first().click();
      };
      const toggleMerge = async () => {
        await drawer.locator('.drawer-body').click({ button: 'right' });
        await expect(menu).toBeVisible();
        await menu.locator(MERGE_ITEM).click();
      };

      // ---- gc 对: 右列(内容)挂桥变体「树 + 详情」, 桥表行渲染出来
      await toggleMerge();
      const split = drawer.locator('.drawer-split');
      await expect(split).toHaveAttribute('data-merge', 'gc', { timeout: 5_000 });
      await pick(split.locator('.dt-col[data-dt-tab="content"]'), '树 + 详情');
      await expect(split.locator('.dt-col[data-dt-tab="content"] .group-row[data-table="drawerContentV10"]').first())
        .toBeVisible({ timeout: 5_000 });
      await noErr('gc 双列挂桥变体');

      // 关合并: 单栏回落当前页签(常规), 且不得抛错(patch 未中断)
      await toggleMerge();
      await expect(split).toHaveCount(0);
      await expect(drawer.locator('.drawer-body .dt-host .drawer-sec').first()).toBeVisible();
      await noErr('gc 关合并');

      // 再开合并: 双列与右列桥表行都必须回来(内容不丢 = patch 未被打断的可见证据)
      await toggleMerge();
      await expect(split).toHaveAttribute('data-merge', 'gc', { timeout: 5_000 });
      await expect(split.locator('.dt-col[data-dt-tab="content"] .group-row[data-table="drawerContentV10"]').first())
        .toBeVisible({ timeout: 5_000 });
      await noErr('gc 再开合并');

      // ---- tp 对: 两列都挂桥变体(trackers 04 / peers 07)。
      // 关合并后当前页签(trackers)的桥表行必须还在 —— 报障现场: 修前此处行数归零, 单栏只剩外壳。
      await drawer.locator('.drawer-tabs button', { hasText: 'Tracker&用户' }).click();
      const split2 = drawer.locator('.drawer-split');
      await expect(split2).toHaveAttribute('data-merge', 'tp', { timeout: 5_000 });
      await pick(split2.locator('.dt-col[data-dt-tab="trackers"]'), '状态卡片栅格');
      await pick(split2.locator('.dt-col[data-dt-tab="peers"]'), '四卡仪表');
      await expect(split2.locator('.dt-col[data-dt-tab="peers"] .group-row[data-table="drawerPeerV07"]').first())
        .toBeVisible({ timeout: 5_000 });
      await noErr('tp 双列挂桥变体');

      await toggleMerge();
      await expect(split2).toHaveCount(0);
      await expect(drawer.locator('.drawer-body .group-row[data-table="drawerTrackerV04"]').first(),
        '关合并后当前页签(trackers)的桥变体表格行必须仍在(修前: patch 中断 ⇒ 行全丢)')
        .toBeVisible({ timeout: 5_000 });
      await noErr('tp 关合并');

      // 再开合并: 双列与两列桥表行都回来(内容不丢)
      await toggleMerge();
      await expect(split2).toHaveAttribute('data-merge', 'tp', { timeout: 5_000 });
      await expect(split2.locator('.dt-col[data-dt-tab="peers"] .group-row[data-table="drawerPeerV07"]').first())
        .toBeVisible({ timeout: 5_000 });
      await noErr('tp 再开合并');

      // 门跨越(同一 patch 顺序的另一条路径): 缩窗过门回落单栏、拉宽自动恢复, 全程零错且内容在
      await page.setViewportSize(NARROW);
      await expect(split2).toHaveCount(0);
      await expect(drawer.locator('.drawer-body .group-row[data-table="drawerTrackerV04"]').first()).toBeVisible();
      await page.setViewportSize(WIDE);
      await expect(split2).toHaveAttribute('data-merge', 'tp', { timeout: 5_000 });
      await expect(split2.locator('.dt-col[data-dt-tab="peers"] .group-row[data-table="drawerPeerV07"]').first())
        .toBeVisible({ timeout: 5_000 });
      await noErr('门跨越往返');
    });

    test(`宽视口: 右键各列弹各自模板选择(左常规/右内容) @fast (${skin})`, async ({ page }) => {
      /* 2026-10-10 用户动议「模板选择改为右键选择, 在对应的区域弹右键; 合并时左边弹常规的模板选择,
       * 右边弹内容的模板选择」: 头部下拉退役, 右键命中的列决定菜单里的模板选项集(左列=常规变体,
       * 右列=内容变体), 两列选择互不影响(各自页签记忆)。断言口径: 真实手势(右键 click button:'right'),
       * 不借道 vm; 变体挂载态经宿主 .dt-tpl 类(DOM 可见事实)。 */
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await page.waitForTimeout(300);
      // 死类守阵(坑档 esc-attr-quote-dead-class): 经典(Vue :class)态全文档零「类名含引号」
      await expectNoDeadClass(page, '合并前经典态');

      // 开合并 -> gc 双列
      await drawer.locator('.drawer-body').click({ button: 'right' });
      await page.locator('.ctx-menu').locator(MERGE_ITEM).click();
      const split = drawer.locator('.drawer-split');
      await expect(split).toHaveAttribute('data-merge', 'gc', { timeout: 5_000 });

      const menu = page.locator('.ctx-menu');
      const leftCol = split.locator('.dt-col[data-dt-tab="general"]');
      const rightCol = split.locator('.dt-col[data-dt-tab="content"]');
      const leftItem = menu.locator('.ctx-item', { hasText: '英雄行·键值栅格' }); // general 变体 01
      const rightItem = menu.locator('.ctx-item', { hasText: '树 + 详情' }); // content 变体 10

      // 左列右键 -> 菜单出常规变体, 不出内容变体
      await leftCol.click({ button: 'right' });
      await expect(menu).toBeVisible();
      await expect(leftItem).toBeVisible();
      await expect(menu.locator('.ctx-item', { hasText: '树 + 详情' })).toHaveCount(0);
      await leftItem.click();
      // 左列挂上变体(宿主加 .dt-tpl), 右列仍是经典(W2: 经典 = 组件分支, v-else 宿主不渲染)
      await expect(split.locator('[data-dt-host="general"]')).toHaveClass(/dt-tpl/, { timeout: 5_000 });
      await expect(split.locator('[data-dt-host="content"]')).toHaveCount(0);
      // 死类守阵: 变体 01(dtHtml 字符串 DOM)挂载态全文档零「类名含引号」
      await expectNoDeadClass(page, '常规变体 01 挂载态');

      // 右列右键 -> 菜单出内容变体, 不出常规变体
      await rightCol.click({ button: 'right' });
      await expect(menu).toBeVisible();
      await expect(rightItem).toBeVisible();
      await expect(menu.locator('.ctx-item', { hasText: '英雄行·键值栅格' })).toHaveCount(0);
      await rightItem.click();
      await expect(split.locator('[data-dt-host="content"]')).toHaveClass(/dt-tpl/, { timeout: 5_000 });
      // 左列选择不受右列影响(两列各自记忆)
      await expect(split.locator('[data-dt-host="general"]')).toHaveClass(/dt-tpl/);
      // 死类守阵: 变体 10 挂载态 + 双变体并存态全文档零「类名含引号」
      await expectNoDeadClass(page, '内容变体 10 挂载态');

      // 2026-10-10 用户报「右侧空白右键弹左列模板」回归: 右列(内容)短于左列(常规), 右列下方
      // 空白格区不属于任何 .dt-col(align-items:start 不撑高) —— 右键该处仍须归右列(内容页签),
      // 不得回落当前/左列。真实手势点右列底缘 + 40px(钳在正文可视底内), 菜单出内容变体。
      const rightBox = await rightCol.boundingBox();
      const bodyBox = await drawer.locator('.drawer-body').boundingBox();
      const blankY = Math.min(rightBox.y + rightBox.height + 40, bodyBox.y + bodyBox.height - 8);
      await page.mouse.click(rightBox.x + rightBox.width / 2, blankY, { button: 'right' });
      await expect(menu, '右列下方空白右键必须仍弹右列(内容)模板菜单').toBeVisible();
      await expect(rightItem, '右列空白命中须归内容页签, 不得回落左列').toBeVisible();
      await expect(menu.locator('.ctx-item', { hasText: '英雄行·键值栅格' })).toHaveCount(0);
      await page.mouse.click(5, 5); // 收菜单, 不点任何项(避免改动选择)
    });
  });
}
