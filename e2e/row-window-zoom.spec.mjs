// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 行窗口化 zoom!=1 分数布局守阵(issue 26-11-14-0844, 2026-11-14 修)。
 *
 * 缺陷: html zoom != 1(分数布局)下贴文档底后, 行窗口化渲染窗整体错位 —— 渲染行落在视口
 * 上方约 (1-z)×视觉总高(flux 实测 ~1900px, 全部行不可见), 底部空白独占视口; scrollBy ±1
 * 后窗口 1:1 跟随但错位不自愈。根因(坐标空间实测, Chrome, html{zoom:0.9}): 窗口化几何输入
 * (scrollY / innerHeight / getBoundingClientRect 一族)全部按**视觉空间**报数, 而占位件
 * style.height 是**布局空间** —— 前缀和(视觉)直接写进 style 会再被 zoom 缩一遍, pad 恒短
 * (1-z) 倍。修法 = _rowWindow 的两个 pad 出口按有效缩放(容器 gBR.height / computed used 高
 * 比值实测, _winZoomOf)除以 z 换算成布局 px; _winSigExtra 加根缩放令牌(zoom 切换后 _winTop 重量)。
 *
 * 用例(次序钉死 = 先 zoom 后贴底 —— 用户真实流是「缩放是页面态, 随后滚到底」, 也是修复前
 * flux 必红的次序; T8 的「先贴底再 zoom」次序是为绕开本缺陷钉死的, 本用例补上反向面):
 * 1. zoom 0.9 + 贴文档底落定: 视口内可见行 >= 5(修复前 flux = 0; prism/atlas 修复前存在
 *    两态平衡、此判据可能不红, flux 是判别皮肤 —— 与 T8 flux 跳过口径互为镜像)。
 * 2. 末行可达: 最深一行 rect 与视口相交(padBottom=0 落底, 修复前整体在视口上方)。
 * 3. scrollBy ±1 微滚两次再贴底, 可见行数不塌(issue 指纹「±1 后不自愈」的回归面)。
 *
 * 皮肤面: prism/atlas(SKINS)+ flux(判别皮肤); console 不进(主表行窗口化四皮肤同构,
 * 双档 + 判别档足以钉住, 全局 SKINS 扩面会翻倍运行时长 —— 同 drawer-dock-stability 口径)。
 */
const ZOOM_SKINS = [...SKINS, 'flux'];

/** 列表落定等待: 渲染行数 + 滚动位两拍全等(拍距 250ms) —— 滚到文档底后等窗口化重渲完成。 */
async function waitListSettled(page) {
  await page.waitForFunction(() => {
    const cur = JSON.stringify([document.querySelectorAll('.torrent-row').length, Math.round(window.scrollY)]);
    if (window.__listSettled === cur) return true;
    window.__listSettled = cur;
    return false;
  }, undefined, { timeout: 10_000, polling: 250 });
}

/** 视口内可见行采样: rect 与 [0, innerHeight] 相交的渲染行数 + 最深一行几何。 */
async function sampleVisible(page) {
  return page.evaluate(() => {
    const vh = window.innerHeight;
    const rows = [...document.querySelectorAll('.torrent-row')];
    let visible = 0;
    for (const r of rows) {
      const b = r.getBoundingClientRect();
      if (b.bottom > 0 && b.top < vh) visible++;
    }
    const last = rows[rows.length - 1];
    const lb = last ? last.getBoundingClientRect() : null;
    return { rendered: rows.length, visible,
      lastTop: lb ? Math.round(lb.top) : null, lastBottom: lb ? Math.round(lb.bottom) : null };
  });
}

installRuntimeErrorGuard(test);

for (const skin of ZOOM_SKINS) {
  test(`zoom 0.9 贴文档底: 视口内可见行 >= 5 + 末行可达 + 微滚不塌 @fast (${skin})`, async ({ page }) => {
    test.setTimeout(90_000);
    collectRuntimeErrors(page);

    await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
    await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
    await page.click('nav.tabs [data-view="torrents"]');
    await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

    // 步骤1: 先应用缩放(用户真实流: 缩放是页面态) -> 再贴文档底 + 落定。修复前 flux 在这个
    // 次序下渲染行整体落在视口上方(全部不可见), 见文件头。
    // !贴底必须循环到真 maxScroll: zoom 后首贴时 pad 还是旧换算(文档偏短, scrollTo 被钳到
    // 偏小的 max), 落定后 pad 按 1/z 换算撑高文档, scrollY 不再在底 —— 逐轮重贴到
    // scrollY >= maxScroll-2 才算贴住(与 T8「重贴 + 重落定」同机理)。
    await page.evaluate(() => { document.documentElement.style.zoom = '0.9'; });
    for (let i = 0; i < 4; i++) {
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await waitListSettled(page);
      const atBottom = await page.evaluate(
        () => window.scrollY >= document.documentElement.scrollHeight - window.innerHeight - 2);
      if (atBottom) break;
    }
    const atBottom = await page.evaluate(
      () => window.scrollY >= document.documentElement.scrollHeight - window.innerHeight - 2);
    expect(atBottom, `前置: 贴底应收敛到真 maxScroll(scrollY ${JSON.stringify(await page.evaluate(() => [Math.round(window.scrollY), document.documentElement.scrollHeight, window.innerHeight]))})`).toBe(true);

    // 断言1: 视口内可见行 >= 5(健康态 ~20 行, 5 留足余量; 修复前 flux = 0)。
    const s1 = await sampleVisible(page);
    expect(s1.visible, `贴文档底视口内可见行数(rendered ${s1.rendered})`).toBeGreaterThanOrEqual(5);
    // 断言2: 末行可达 —— 最深一行 rect 与视口相交(padBottom=0 落底; 修复前行整体在视口上方)。
    expect(s1.lastTop, `末行 rect.top(应 < innerHeight)`).toBeLessThan(await page.evaluate(() => window.innerHeight));
    expect(s1.lastBottom, `末行 rect.bottom(应 > 0)`).toBeGreaterThan(0);

    // 断言3: scrollBy ±1 微滚两次(issue 指纹「±1 后窗口跟随但不自愈」的回归面) —— 每次落定
    // 后可见行数都不得塌。
    await page.evaluate(() => window.scrollBy(0, -1));
    await waitListSettled(page);
    const s2 = await sampleVisible(page);
    expect(s2.visible, `scrollBy(0,-1) 落定后可见行数`).toBeGreaterThanOrEqual(5);
    await page.evaluate(() => window.scrollBy(0, 1));
    await waitListSettled(page);
    const s3 = await sampleVisible(page);
    expect(s3.visible, `scrollBy(0,+1) 回贴底后可见行数`).toBeGreaterThanOrEqual(5);
  });
}
