// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 必显列(吸左首格)悬停同帧守阵(2026-10-20 修「必显列鼠标滑过时背景与其它列不一致, 短暂后恢复一致」)
 *
 * **报障面 = 三个主表 × 每个皮肤**(辅种 / 种子 / 追剧; 必显列 = locked 的首列, 也是吸左首格)。
 * **根因**: 行板 `.group-row` 有 `transition: background var(--dur)`(160ms), 吸左首格此前没有过渡
 * ⇒ 滑过瞬间首格已 snap 到 `--bg-hover`, 其余列还在从 `--bg-row` 渐入; 160ms 内行内是一条比其它
 * 列更亮的竖带, 过渡结束又"恢复一致"(用户描述的现象逐字对应)。移出方向同理反号。
 * **修法**: 三皮肤 views.css 的 `.group-row > :first-child` 补同源时长/缓动的 `background-color`
 * 过渡(声明式契约由 test_webui_static_skins.py::test_frontend_pinned_first_cell_hover_transition_parity
 * 静态钉住; 本 spec 钉**行为**: 静态守阵看不出两边是否真的逐帧同步)。
 *
 * 三段断言(每段都能独立抓回退):
 *   A. 声明面: 行板与首格**各自**的 background(-color) 过渡时长逐字相等, 且都是非零 —— 只改一边
 *      (例如把行板调成 280ms、首格留 160ms)会重新错拍, 静态守阵只管"读的是 --dur"管不到这类改法;
 *   B. 逐帧面: 滑入与移出两个方向各采 ~32 帧, 首格与行板的 backgroundColor 逐帧逐通道差 ≤ 2
 *      (修复前实测 14 / 18, 远在阈外; 阈值取 2 是给计算样式的整数取整留余量);
 *   C. 稳态面: 悬停保持后两者同色, 且与悬停前的行板基色不同 —— 防"两边都不变"这种空过(悬停根本没触发)。
 *
 * 采样放在页面内用 rAF 跑(pointer 由 Playwright 真手势触发, 之后立即回页面逐帧读数):
 * 过渡窗口只有 160ms, 从 Node 侧逐次 evaluate 读会漏帧(坑档 testing/playwright-teardown 之外的
 * 另一类时序坑: 读数本身要贴帧)。
 */

const VIEWS = [
  { view: 'groups', table: 'group', label: '辅种表' },
  { view: 'torrents', table: 'torrent', label: '种子表' },
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

/**
 * 把指针真放进某一行(行宽可超出视口 ⇒ 取行中心并钳进视口; 首行可能被吸顶列头/状态栏压住 ⇒
 * 逐行试到 `:hover` 成立为止, 探不到就红 —— 宁可失败也不要在没悬停的样本上"验通过")。
 */
async function hoverRow(page, table) {
  const rows = page.locator(ROW_SEL(table));
  const n = Math.min(await rows.count(), 8);
  for (let i = 0; i < n; i++) {
    const box = await rows.nth(i).boundingBox();
    if (!box || box.height < 8) continue;
    const x = Math.min(box.x + box.width / 2, 1400);
    const y = Math.min(Math.max(box.y + box.height / 2, 8), 880);
    await page.mouse.move(x, y);
    const hit = await page.evaluate(
      ({ sel, idx }) => !!document.querySelectorAll(sel)[idx]?.matches(':hover'),
      { sel: ROW_SEL(table), idx: i },
    );
    if (hit) return { box, x, y };
  }
  return null;
}

/** 行板与首格的过渡声明(计算值, 不是源码)。 */
function readTransition(page, table) {
  return page.evaluate((sel) => {
    const row = document.querySelector(sel);
    const cell = row?.children?.[0];
    if (!row || !cell) return null;
    const pick = (el) => {
      const cs = getComputedStyle(el);
      return { prop: cs.transitionProperty, dur: cs.transitionDuration, ease: cs.transitionTimingFunction };
    };
    return { row: pick(row), cell: pick(cell) };
  }, ROW_SEL(table));
}

/** 按属性取对应那一档的时长(属性名可能是 background 简写, 也可能是 background-color 长写)。 */
function bgDuration({ prop, dur }) {
  const props = String(prop).split(',').map((s) => s.trim());
  const durs = String(dur).split(',').map((s) => s.trim());
  const i = props.findIndex((p) => p === 'background-color' || p === 'background');
  if (i < 0) return null;
  return durs[Math.min(i, durs.length - 1)];
}

/** 逐帧采样: 500ms 内每帧读一次首格与行板的 backgroundColor, 返回逐帧逐通道最大差。 */
function traceColors(page, table) {
  return page.evaluate(
    (sel) => new Promise((resolve) => {
      const row = document.querySelector(sel);
      const cell = row?.children?.[0];
      const parse = (s) => (s.match(/[\d.]+/g) || []).map(Number);
      const frames = [];
      const t0 = performance.now();
      const tick = () => {
        const fb = getComputedStyle(cell).backgroundColor;
        const rb = getComputedStyle(row).backgroundColor;
        const fa = parse(fb);
        const ra = parse(rb);
        let d = 0;
        for (let i = 0; i < 3; i++) d = Math.max(d, Math.abs((fa[i] || 0) - (ra[i] || 0)));
        frames.push({ d, f: fb, r: rb });
        if (performance.now() - t0 < 500) requestAnimationFrame(tick);
        else resolve(frames);
      };
      tick();
    }),
    ROW_SEL(table),
  );
}

const maxDelta = (frames) => frames.reduce((m, f) => Math.max(m, f.d), 0);
const worst = (frames) => {
  const m = maxDelta(frames);
  return frames.find((f) => f.d === m) || { d: 0, f: '', r: '' };
};

for (const skin of SKINS) {
  test.describe(`必显列悬停同帧 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    for (const v of VIEWS) {
      test(`${v.label}: 首格与行板悬停逐帧同步(滑入/移出) @fast (${skin})`, async ({ page }) => {
        collectRuntimeErrors(page);
        await openView(page, skin, v.view);

        // A. 声明面: 两边 background 过渡时长相等且非零(只改一边即红)
        const tr = await readTransition(page, v.table);
        expect(tr, `${v.label} 取不到行板/首格(结构变了?)`).not.toBeNull();
        const rowDur = bgDuration(tr.row);
        const cellDur = bgDuration(tr.cell);
        expect(rowDur, `${v.label} 行板过渡不含 background(时长基准丢了?)`).not.toBeNull();
        expect(cellDur, `${v.label} 必显列首格缺 background 过渡 —— 行板渐变 160ms 而首格瞬切, ` +
          '滑过/移出瞬间行内现竖带(2026-10-20 报障)').not.toBeNull();
        expect(cellDur, `${v.label} 首格过渡时长(${cellDur}) != 行板(${rowDur}) —— 两边错拍仍会闪竖带`)
          .toBe(rowDur);
        expect(parseFloat(cellDur), `${v.label} 首格过渡时长为 0(等于没有过渡)`).toBeGreaterThan(0);

        // C(前置): 悬停前基色 —— 用来证 C 段不是"两边都没变"
        const base = await traceColors(page, v.table);
        const baseColor = base[base.length - 1].r;

        // B. 滑入: 真实指针进到行内, 立刻回页面逐帧采样
        const hit = await hoverRow(page, v.table);
        expect(hit, `${v.label} 指针没能落进任何行(吸顶列头/状态栏遮挡?) —— 不能在无悬停样本上判绿`)
          .not.toBeNull();
        const inFrames = await traceColors(page, v.table);
        const inWorst = worst(inFrames);
        expect(inFrames.length, `${v.label} 滑入采样帧太少(${inFrames.length}), 过渡窗口没被观察到`).toBeGreaterThan(8);
        expect(maxDelta(inFrames), `${v.label} 滑入: 必显列与行板逐帧不同色 —— 最差一帧首格 ${inWorst.f} ` +
          `vs 行板 ${inWorst.r}(差 ${inWorst.d}); 修复前实测 14/18, 阈值 2`)
          .toBeLessThanOrEqual(2);

        // C. 稳态: 悬停保持后同色, 且确实变过色(悬停生效应验)
        const settled = inFrames[inFrames.length - 1];
        expect(settled.f, `${v.label} 悬停稳态: 首格 ${settled.f} != 行板 ${settled.r}`).toBe(settled.r);
        expect(settled.r, `${v.label} 悬停没有改变行板底色(${settled.r}) —— 采样时指针已离开行内?`)
          .not.toBe(baseColor);

        // B(反向). 移出: 指针移到列表之外, 同样逐帧采
        await page.mouse.move(Math.min(hit.box.x + hit.box.width / 2, 1400), 8);
        const outFrames = await traceColors(page, v.table);
        const outWorst = worst(outFrames);
        expect(outFrames.length, `${v.label} 移出采样帧太少(${outFrames.length})`).toBeGreaterThan(8);
        expect(maxDelta(outFrames), `${v.label} 移出: 必显列与行板逐帧不同色 —— 最差一帧首格 ${outWorst.f} ` +
          `vs 行板 ${outWorst.r}(差 ${outWorst.d})`)
          .toBeLessThanOrEqual(2);
        const back = outFrames[outFrames.length - 1];
        expect(back.f, `${v.label} 移出稳态: 首格 ${back.f} != 行板 ${back.r}`).toBe(back.r);
      });
    }
  });
}
