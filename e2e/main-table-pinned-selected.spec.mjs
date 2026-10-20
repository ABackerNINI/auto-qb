// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 选中行必显列(吸左首格)与行板**同底**守阵(2026-10-20 修「选中的行必显列背景与其它列不一致」)
 *
 * **报障面** = 三个主表 × 每个皮肤(辅种 / 种子 / 追剧; 必显列 = locked 的首列, 也是吸左首格)。
 * **根因**: `.group-row.selected { background: var(--sel-bg) }` 把行底**替换**成半透明 tint(而不是叠在
 * 行底上) ⇒ 行板实际露出的是页底 `--bg`, 而首格镜像按 `var(--bg-row)` 合成(坑档
 * pitfalls/web-ui/frozen-column.md ②⑥ 的按面重锚口径) —— 两侧承光底分家, 选中行名称列成了整列
 * 异色竖带。真浏览器逐像素实测: atlas Δ9/255、prism Δ5/255, 未选中行 Δ0。
 * **修法**: 行底不被状态替换 —— `linear-gradient(tint, tint), var(--bg-row)`, 与首格同一个合成表达式
 * ⇒ 两侧计算背景逐字节相等(声明式契约由
 * test_webui_static_skins.py::test_frontend_pinned_first_cell_selected_row_keeps_base 静态钉住;
 * 本 spec 钉**行为**: 声明看着对、实际被后置规则/继承打回半透明的形态静态看不出来)。
 *
 * 三段断言(每段都能独立抓回退):
 *   A. 结构面: 选中行(真手势 Ctrl+click)真的带 `selected`, 且行板背景**不透明** —— 行底一旦退回
 *      rgba, 页底就会透上来(这正是修复前的形态, 行板 backgroundColor 是 rgba(…, .18));
 *   B. 同底面: 行板与首格的 backgroundColor / backgroundImage **逐字相等**(不是"差 ≤ N"的阈值判据 ——
 *      两边现在是同一个合成表达式, 任何不等都说明有一侧被改写成另一个基色);
 *   C. 悬停面: 选中行被指针压住时仍逐字相等(选中态压过悬停态, 位序写反会让悬停期首格露出一条竖带)。
 *
 * 半选(partial)与全选共用同一条规则体(静态守阵对两个选择器都钉了末层 `--bg-row`), 行为等价, 不再重复采样。
 *
 * **展开态**(2026-10-20 用户「group 一同修」同轮收): `.group-row.expanded { background: var(--bg-sunken) }`
 * 是同一类缺陷 —— 半透明下沉底替换行底, 行板承光层变页底 `--bg` 而首格按 `--bg-row` 合成(展开行
 * atlas Δ5/255、prism Δ2/255)。可展开面只有辅种表/追剧表(种子表是平铺行), 同样钉行板不透明 +
 * 行板与首格逐字相等(含悬停); console 独享的 `.group-row.expanded:hover` 由静态守阵钉。
 */

const VIEWS = [
  { view: 'groups', table: 'group', label: '辅种表' },
  { view: 'torrents', table: 'torrent', label: '种子表' },
  { view: 'shows', table: 'show', label: '追剧表' },
];

/** 可展开的主表(种子表是平铺行, 无展开态)。 */
const EXPANDABLE = [
  { view: 'groups', table: 'group', label: '辅种表' },
  { view: 'shows', table: 'show', label: '追剧表' },
];

const ROW_SEL = (table) => `.group-table .group-row[data-table="${table}"]`;

/** 打开某个主表页签并等首行出来。 */
async function openView(page, skin, view) {
  await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
  await page.click(`nav.tabs [data-view="${view}"]`);
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
}

/** 真手势 Ctrl+click 一个**尚未选中**的行, 返回它的下标(已选中的行不选 —— 拉它一下反而会取消选择)。 */
async function selectUnselectedRow(page, table) {
  const rows = page.locator(ROW_SEL(table));
  const n = Math.min(await rows.count(), 8);
  for (let i = 0; i < n; i++) {
    const pre = await page.evaluate(
      ({ sel, idx }) => document.querySelectorAll(sel)[idx]?.classList.contains('selected') === true,
      { sel: ROW_SEL(table), idx: i },
    );
    if (pre) continue;
    const box = await rows.nth(i).boundingBox();
    if (!box || box.height < 8) continue;
    const x = Math.min(box.x + 8, 1400);
    const y = Math.min(Math.max(box.y + box.height / 2, 8), 880);
    await page.mouse.move(5, 5);
    await page.keyboard.down('Control');
    try {
      await page.mouse.click(x, y);
    } finally {
      await page.keyboard.up('Control');
    }
    const ok = await page.evaluate(
      ({ sel, idx }) => document.querySelectorAll(sel)[idx]?.classList.contains('selected') === true,
      { sel: ROW_SEL(table), idx: i },
    );
    if (ok) return { idx: i, x, y };
  }
  return null;
}

/** 把指针真放进某个已选中行(选中后顶栏摘要会出现、行会移位 ⇒ 每次重测行盒; 吸顶表头可遮挡 ⇒ 逐拍试)。 */
async function hoverRowIdx(page, table, idx) {
  const row = page.locator(ROW_SEL(table)).nth(idx);
  for (let attempt = 0; attempt < 3; attempt++) {
    const box = await row.boundingBox();
    if (!box || box.height < 8) return null;
    const x = Math.min(box.x + box.width / 2, 1400);
    const y = Math.min(Math.max(box.y + box.height / 2, 8), 880);
    await page.mouse.move(x, y);
    const hit = await page.evaluate(
      ({ sel, idx }) => document.querySelectorAll(sel)[idx]?.matches(':hover') === true,
      { sel: ROW_SEL(table), idx },
    );
    if (hit) return { x, y };
  }
  return null;
}

/** 展开一个未选中行, 返回其下标(合成 click 走 Vue 的 @click 处理器; 行首格有交互后裔时真鼠标会踩偏)。 */
async function expandUnselectedRow(page, table) {
  const idx = await page.evaluate((sel) => {
    const rows = [...document.querySelectorAll(sel)];
    return rows.findIndex((r) => !r.classList.contains('selected') && !r.classList.contains('expanded') &&
      r.getBoundingClientRect().height > 8);
  }, ROW_SEL(table));
  if (idx < 0) return null;
  await page.evaluate(({ sel, idx }) => {
    const row = document.querySelectorAll(sel)[idx];
    row.scrollIntoView({ block: 'center', behavior: 'instant' });
    (row.querySelector('.g-name') || row.children[0]).click();
  }, { sel: ROW_SEL(table), idx });
  await page.waitForTimeout(400);
  const ok = await page.evaluate(
    ({ sel, idx }) => document.querySelectorAll(sel)[idx]?.classList.contains('expanded') === true,
    { sel: ROW_SEL(table), idx },
  );
  return ok ? idx : null;
}

/** 行板与首格的计算背景(颜色层 + image 层)。 */
function readBgs(page, table, idx) {
  return page.evaluate(({ sel, idx }) => {
    const row = document.querySelectorAll(sel)[idx];
    const cell = row?.children?.[0];
    if (!row || !cell) return null;
    const pick = (el) => {
      const cs = getComputedStyle(el);
      return { color: cs.backgroundColor, image: cs.backgroundImage };
    };
    return { row: pick(row), cell: pick(cell) };
  }, { sel: ROW_SEL(table), idx });
}

const alphaOf = (color) => {
  const nums = String(color).match(/[\d.]+/g) || [];
  return nums.length >= 4 ? Number(nums[3]) : 1;
};

for (const skin of SKINS) {
  test.describe(`必显列同底 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    for (const v of VIEWS) {
      test(`${v.label}: 选中行行板与首格同底(含悬停) @fast (${skin})`, async ({ page }) => {
        collectRuntimeErrors(page);
        await openView(page, skin, v.view);

        // A. 真手势选中 + 行板必须不透明
        const hit = await selectUnselectedRow(page, v.table);
        expect(hit, `${v.label} Ctrl+click 没能选中任何行(吸顶表头/状态栏遮挡?) —— 不能在未选中样本上判绿`)
          .not.toBeNull();
        await page.mouse.move(5, 5);
        const picked = await readBgs(page, v.table, hit.idx);
        expect(picked, `${v.label} 取不到行板/首格(结构变了?)`).not.toBeNull();
        expect(alphaOf(picked.row.color), `${v.label} 选中行的行板 backgroundColor 是半透明 ` +
          `(${picked.row.color}) —— tint 替换了行底, 页底透上来; 必须「同色 linear-gradient 叠 --bg-row」`)
          .toBe(1);

        // B. 同底面: 逐字相等
        expect(picked.row.color, `${v.label} 选中行: 行板 backgroundColor ${picked.row.color} != ` +
          `首格 ${picked.cell.color} —— 必显列成了异色竖带`).toBe(picked.cell.color);
        expect(picked.row.image, `${v.label} 选中行: 行板 backgroundImage 与首格不同(source: ` +
          `行板 ${picked.row.image} / 首格 ${picked.cell.image})`).toBe(picked.cell.image);

        // C. 悬停面: 选中行被压住时仍同底
        const over = await hoverRowIdx(page, v.table, hit.idx);
        expect(over, `${v.label} 指针未能落在选中行内(吸顶表头/状态栏遮挡?) —— 悬停面不可判`).not.toBeNull();
        await page.waitForTimeout(300);
        const hov = await readBgs(page, v.table, hit.idx);
        expect(hov.row.color, `${v.label} 悬停选中行: 行板 ${hov.row.color} != 首格 ${hov.cell.color}`)
          .toBe(hov.cell.color);
        expect(hov.row.image, `${v.label} 悬停选中行: backgroundImage 行板 ${hov.row.image} != ` +
          `首格 ${hov.cell.image}`).toBe(hov.cell.image);
      });
    }

    /* 展开态(下沉底)与选中态是同一类缺陷: `background: var(--bg-sunken)` 把行底替换掉 ⇒ 行板承光层
     * 变页底 --bg, 首格却按 --bg-row 合成。实测展开行 atlas Δ5/255、prism Δ2/255(2026-10-20 用户
     * 「group 一同修」本轮收掉); 选中态用例管不到这个状态 —— 展开但未选中的行是另一条行板规则。 */
    for (const v of EXPANDABLE) {
      test(`${v.label}: 展开行行板与首格同底(含悬停) @fast (${skin})`, async ({ page }) => {
        collectRuntimeErrors(page);
        await openView(page, skin, v.view);

        const idx = await expandUnselectedRow(page, v.table);
        expect(idx, `${v.label} 没能展开任何行 —— 不能在无展开样本上判绿`).not.toBeNull();
        await page.mouse.move(5, 5);
        const bac = await readBgs(page, v.table, idx);
        expect(bac, `${v.label} 取不到行板/首格(结构变了?)`).not.toBeNull();
        expect(alphaOf(bac.row.color), `${v.label} 展开行的行板 backgroundColor 是半透明(${bac.row.color}) ` +
          '—— 下沉底替换了行底, 页底透上来; 必须「同色 linear-gradient 叠 --bg-row」').toBe(1);
        expect(bac.row.color, `${v.label} 展开行: 行板 backgroundColor ${bac.row.color} != ` +
          `首格 ${bac.cell.color} —— 必显列成了异色竖带`).toBe(bac.cell.color);
        expect(bac.row.image, `${v.label} 展开行: 行板 backgroundImage 与首格不同(source: ` +
          `行板 ${bac.row.image} / 首格 ${bac.cell.image})`).toBe(bac.cell.image);

        const over = await hoverRowIdx(page, v.table, idx);
        expect(over, `${v.label} 指针未能落在展开行内(吸顶表头/状态栏遮挡?) —— 悬停面不可判`).not.toBeNull();
        await page.waitForTimeout(300);
        const hov = await readBgs(page, v.table, idx);
        expect(hov.row.color, `${v.label} 悬停展开行: 行板 ${hov.row.color} != 首格 ${hov.cell.color}`)
          .toBe(hov.cell.color);
        expect(hov.row.image, `${v.label} 悬停展开行: backgroundImage 行板 ${hov.row.image} != ` +
          `首格 ${hov.cell.image}`).toBe(hov.cell.image);
      });
    }
  });
}
