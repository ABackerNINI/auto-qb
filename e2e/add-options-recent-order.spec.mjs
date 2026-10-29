// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS, TORRENTS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 添加种子三候选「最近使用」排序(2026-10-09) —— 桩服务数据面的 @fast 真浏览器覆盖。
 *
 * 为什么需要它: 桩服务的 `FakeClient` 分类定义恒 `{}`、标签集合恒空 ⇒ `/api/categories` 与
 * `/api/tags` 在冒烟里永远回空, 添加窗口的分类/标签下拉**永远**是空态; 保存路径候选则在旧组键
 * `(name, ())` 下被全库种子名污染。于是「最近使用排序」这条渲染路径从未被真浏览器覆盖过 ——
 * 与 drawer peers / trackers 两条同病(默认桩恒空 ⇒ 只有空态分支被测到)。桩已补数据面:
 * `_inject_add_options`(分类/标签) + 合成种子每对独立 `save_path` + 组键改真机口径
 * `(save_path, ())`。本 spec 钉住它不再回退。
 *
 * 期望序**从桩的同源公式现算**(不硬编码, `E2E_TORRENTS` 变档自动跟着变), 公式见
 * `scripts/ui_harness.py::_make_torrents` —— 改桩的合成数据必须同步这里, 否则本 spec 会红
 * (这是**特性**: 数据面与断言同源才有意义)。
 */

/* 桩的确定性数据(与 _make_torrents 同源):
 *   added_on  = 1700000000 + i * 37            (i 越大越新)
 *   category  = ["", "Movies", "TV", "Anime"][i % 4]
 *   tags      = ["HHan", "seed-3D", "low-ratio"] 里第 k 位为 (i >> k) & 1 的那些
 *   save_path = `R:\Downloads\Set{i // 2:03d}`(组对 2k / 2k+1 共用一条) */
const CATEGORY_POOL = ['', 'Movies', 'TV', 'Anime'];
const TAG_POOL = ['HHan', 'seed-3D', 'low-ratio'];

/** 最近使用降序 -> 同时间按字母序(与前端 `_addOrderByRecent` 同义) */
function expectedOrder(valuesOf) {
  const latest = new Map();
  for (let i = 0; i < TORRENTS; i += 1) {
    for (const v of valuesOf(i)) if (v) latest.set(v, i);
  }
  return [...latest.keys()].sort((a, b) => latest.get(b) - latest.get(a) || a.localeCompare(b));
}

const EXPECT_CATS = expectedOrder((i) => [CATEGORY_POOL[i % 4]]);
/* 站点标签(HHan 来自 tracker.tags)会被后端 `exclude_auto=1` 滤掉 —— 这正是要覆盖的真实链路 */
const EXPECT_TAGS = expectedOrder((i) => TAG_POOL.filter((_, k) => (i >> k) & 1)).filter((t) => t !== 'HHan');
/* 保存路径: 组对共用一条, 组内最大 added_on 落在奇数号(i = 2k+1) ⇒ 组号越大越新;
 * 后端 `path_normalize` 把反斜杠转成正斜杠。只比**头部 3 条** —— 排序对不对看头部即知。 */
const LAST_GROUP = Math.floor((TORRENTS - 1) / 2);
const EXPECT_PATH_HEAD = [LAST_GROUP, LAST_GROUP - 1, LAST_GROUP - 2]
  .map((k) => `R:/Downloads/Set${String(k).padStart(3, '0')}`);

/** 读候选面板里的值文本(cat/tag/path 三处结构一致: `.pop-item` > `.pop-value`) */
async function optionValues(pop) {
  const texts = await pop.locator('.pop-item .pop-value').allTextContents();
  return texts.map((s) => s.trim());
}

for (const skin of SKINS) {
  test.describe(`添加种子三候选「最近使用」排序 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`分类/标签/路径候选按最近使用排序 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 顶栏「添加种子」入口(仅 groups 页) -> 开窗
      await page.click('button.add-btn');
      const catInput = page.locator('#ad-category');
      await expect(catInput).toBeVisible({ timeout: 5_000 });

      // 分类: 点输入框即开候选面板(`loadAddOptions` 是异步拉取, 用 expect 等候选落袋)
      const catPop = page.locator('.add-dialog-field:has(#ad-category) .pop-menu.add-pop');
      await catInput.click();
      await expect(catPop.locator('.pop-item').first()).toBeVisible({ timeout: 10_000 });
      const gotCats = await optionValues(catPop);
      expect(gotCats, `分类候选序(期望最近使用降序 ${EXPECT_CATS.join(' > ')})`).toEqual(EXPECT_CATS);

      // 标签: 点标签输入框(三浮层互斥单点会自动收掉分类面板)
      const tagPop = page.locator('.add-dialog-field:has(#ad-tags) .pop-menu.add-pop');
      await page.locator('#ad-tags').click();
      await expect(tagPop.locator('.pop-item').first()).toBeVisible({ timeout: 10_000 });
      const gotTags = await optionValues(tagPop);
      expect(gotTags, '标签候选序(站点标签已由 exclude_auto=1 滤除)').toEqual(EXPECT_TAGS);

      // 保存路径: 头部 3 条 = 最新三组的路径(路径候选量大, 只钉头部)
      const pathPop = page.locator('.add-dialog-field:has(#ad-save-path) .pop-menu.add-pop');
      await page.locator('#ad-save-path').click();
      await expect(pathPop.locator('.pop-item').first()).toBeVisible({ timeout: 10_000 });
      const gotPaths = await optionValues(pathPop);
      expect(gotPaths.slice(0, 3), '保存路径候选头部(最近使用降序)').toEqual(EXPECT_PATH_HEAD);

      // —— 面板内**非交互区**点了不许收起面板(2026-10-29 六修, 用户报「点面板头面板就收了」)。
      //    焦点纪律挂在共享模板的面板**根**上(@mousedown.prevent), 只给 .pop-head 打补丁会漏掉
      //    空态文案这一段 —— 故用真能产出空列表的下拉(分类按输入过滤)再验一次: 修复前 mousedown
      //    把焦点从输入框抢走 → @focusout → 40ms 合帧收层 = 面板"点一下就消失"。
      await page.keyboard.press('Escape');  // 先收路径面板: 它朝下展开, 正盖着下面的分类输入框
      await expect(pathPop).toBeHidden();
      await page.locator('#ad-category').click();  // 三浮层互斥: 开分类即收掉别家面板
      await expect(catPop.locator('.pop-item').first()).toBeVisible({ timeout: 5_000 });
      await catInput.fill('zzz-无此分类');
      const emptyTip = catPop.locator('.pop-empty');
      await expect(emptyTip).toBeVisible({ timeout: 5_000 });
      await emptyTip.click();
      await page.waitForTimeout(300);  // > 40ms 合帧窗, 定时器该响的都响完了
      await expect(catPop, '点空态文案不得收起面板(面板内非交互区抢焦点 = 同一类缺陷)').toBeVisible();
    });
  });
}
