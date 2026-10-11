// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 抽屉页签合并(R2 计划 26-10-09-2219 · R3 修订) —— 单开关 / 合并页签 / 双列布局 / 宽度门:
 *   1. 宽视口(≥1920): 正文右键 → 菜单「合并页签」可用 → 点击 → 页签栏收敛为
 *      [常规&内容][Tracker&用户] 两张合并页签, 正文双列(列头 常规/内容, 两列各挂本页签当前所选实现);
 *      再右键 → 勾选态在 → 再点已开启项 → 关闭, 页签栏回四页签单栏。
 *   2. R3 回归(用户报「选择并排后 tracker/用户标签显示常规/内容且为空」): 合并开启下点
 *      [Tracker&用户] 合并页签 → 列头变 Tracker/用户 且两列有内容(不再渲染旧对列头 + 空列)。
 *   3. 窄视口(<1920): 菜单项置灰(.is-gated), 点击零状态变化(dtToggleMerge 双保险拦截), 四页签原样。
 *   4. W5(计划 26-10-11-2106)起右键模板选择改**密度档**: 合并态右键左列弹常规页签的档位选项、
 *      右列弹内容页签的档位选项(菜单选项集按命中列), 两列各自选择互不影响(各自页签记忆)。
 *   5. 2026-10-10 用户报「合并后右侧空白右键弹左列模板」回归: 右列(内容)通常短于左列, 其下方
 *      空白格区/列间隙不落在任何 .dt-col 元素上 —— 右键仍须归右列(不得回落当前/左列)。
 * 断言口径: 真实手势(右键 click button:'right'), 不借道 vm。
 *
 * !W5(计划 26-10-11-2106)起页签正文只有**一条实现**: Vue 组件(根 `.dt-host`, **不带**
 * data-dt-host —— 那是旧插件挂载锚, 退役后保留不带的纪律只防机械复活)。密度档走描述符:
 *   ·cls 挂组件根(紧凑 = `dd-compact`, CSS 只做密度收紧);
 *   ·结构开关 raw/hint 是模板 v-if **真隐藏**(general 的 `details.drawer-raw`、content 的
 *    `.drawer-toolbar-hint`), 不是 CSS 藏 —— 断言档位生效锚这三样, DOM 可见事实。
 *
 * W2 曾有「经典 Vue / 变体字符串 DOM」双实现, 列表锚点分家(.group-table vs drawer-table);
 * W5 变体整体退役, 该比较只需锚单一实现的表壳: 行容器 .group-table + 行
 * .group-row[data-table="drawer<Tab>"] + cells 渲染器(表头 <aq-table grid>, 拖宽/排序/右键
 * 隐藏/列偏好与主视图同源)。
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

      // gc 双列: 列头 常规/内容; 两列正文都渲染出来(列锚 + 列内 .dt-host)
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
      // (不再是 <table class="drawer-table"><tbody><tr>)。W5 变体退役, 表壳是唯一实现。
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

    test(`宽视口: 右键各列弹各自密度档选择(左常规/右内容) @fast (${skin})`, async ({ page }) => {
      /* 2026-10-10 用户动议「模板选择改为右键选择, 在对应的区域弹右键; 合并时左边弹常规的,
       * 右边弹内容的」; W5(计划 26-10-11-2106)选项集改声明式密度档(经典/紧凑)。右键命中的列
       * 决定菜单操作哪一页签的记忆(左列=general, 右列=content), 两列互不影响。断言口径:
       * 真实手势(右键 click button:'right'), 不借道 vm; 档位生效锚 DOM 可见事实 ——
       *   ·密度类: 紧凑 = 组件根 `.dt-host` 带 `dd-compact`;
       *   ·结构开关: 紧凑 general 真隐藏 `details.drawer-raw`(v-if raw)、
       *     紧凑 content 真隐藏 `.drawer-toolbar-hint`(v-if hint)。 */
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await page.waitForTimeout(300);

      // 开合并 -> gc 双列
      await drawer.locator('.drawer-body').click({ button: 'right' });
      await page.locator('.ctx-menu').locator(MERGE_ITEM).click();
      const split = drawer.locator('.drawer-split');
      await expect(split).toHaveAttribute('data-merge', 'gc', { timeout: 5_000 });

      const menu = page.locator('.ctx-menu');
      const leftCol = split.locator('.dt-col[data-dt-tab="general"]');
      const rightCol = split.locator('.dt-col[data-dt-tab="content"]');
      const leftHost = leftCol.locator('.dt-host');
      const rightHost = rightCol.locator('.dt-host');
      const compactItem = menu.locator('.ctx-item', { hasText: '紧凑' });
      const classicItem = menu.locator('.ctx-item', { hasText: '经典' });

      // 经典是默认档: 两列根都不带 dd-compact, general 的原始键值区在(raw=true), content 提示在
      await expect(leftHost).not.toHaveClass(/dd-compact/);
      await expect(rightHost).not.toHaveClass(/dd-compact/);
      await expect(leftCol.locator('details.drawer-raw')).toBeVisible();
      await expect(rightCol.locator('.drawer-toolbar-hint')).toBeVisible();

      // 左列右键 -> 点「紧凑」: 左列根挂 dd-compact + 原始键值区真隐藏; 右列仍是经典
      await leftCol.click({ button: 'right' });
      await expect(menu).toBeVisible();
      await expect(compactItem).toBeVisible();
      await compactItem.click();
      await expect(leftHost, '左列紧凑档 = 组件根挂 dd-compact').toHaveClass(/dd-compact/, { timeout: 5_000 });
      await expect(leftCol.locator('details.drawer-raw'), '紧凑档结构开关 v-if 真隐藏原始键值区').toHaveCount(0);
      await expect(rightHost).not.toHaveClass(/dd-compact/);
      await expect(rightCol.locator('.drawer-toolbar-hint')).toBeVisible();

      // 2026-10-10 用户报「右侧空白右键弹左列模板」回归: 右列(内容)短于左列(常规), 右列下方
      // 空白格区不属于任何 .dt-col(align-items:start 不撑高) —— 右键该处仍须归右列(内容页签),
      // 不得回落当前/左列。真实手势点右列底缘 + 40px(钳在正文可视底内), 点「紧凑」后判据:
      // content 记忆翻转(右列挂 dd-compact + 提示真隐藏), 左列不受牵连。
      const rightBox = await rightCol.boundingBox();
      const bodyBox = await drawer.locator('.drawer-body').boundingBox();
      const blankY = Math.min(rightBox.y + rightBox.height + 40, bodyBox.y + bodyBox.height - 8);
      await page.mouse.click(rightBox.x + rightBox.width / 2, blankY, { button: 'right' });
      await expect(menu, '右列下方空白右键必须仍弹右列(内容)菜单').toBeVisible();
      await expect(compactItem, '右列空白命中须归内容页签, 不得回落左列').toBeVisible();
      await compactItem.click();
      await expect(rightHost, '右列空白右键选紧凑必须落到 content 记忆').toHaveClass(/dd-compact/, { timeout: 5_000 });
      await expect(rightCol.locator('.drawer-toolbar-hint'), '紧凑档 content 提示 v-if 真隐藏').toHaveCount(0);
      // 左列选择不受右列影响(两列各自记忆)
      await expect(leftHost).toHaveClass(/dd-compact/);

      // 经典回切(反向过渡): 右列右键选回「经典」—— dd-compact 移除 + 提示回来, 正文照常渲染;
      // 左列的紧凑档不受牵连。密度档不再有"换实现"问题(W5 后正文唯一实现), 但列记忆互斥性照钉。
      await rightCol.click({ button: 'right' });
      await expect(menu).toBeVisible();
      await classicItem.first().click();
      await expect(rightHost, '回切经典后右列密度类必须移除').not.toHaveClass(/dd-compact/, { timeout: 5_000 });
      await expect(rightCol.locator('.drawer-toolbar-hint')).toBeVisible();
      await expect(rightCol.locator('.group-row[data-table="drawerFile"]').first()).toBeVisible();
      await expect(leftHost).toHaveClass(/dd-compact/);
      await expect(leftCol.locator('details.drawer-raw')).toHaveCount(0);
    });
  });
}
