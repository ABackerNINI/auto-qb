import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { collectRuntimeErrors } from './lib/errors.mjs';

/**
 * W6a 抽屉文件优先级乐观写补丁(计划 26-11-02-0351 §06 拍板 = 实施):
 * 千文件内容表下三条路径 + 可见延迟对照实测。
 *
 * 桩口径:
 *  · GET /api/torrents/{hash}/files —— 1000 文件(dt11 单层目录 D), 状态由 filesState 持有,
 *    POST 成功时同步改写(模拟 qB 已落库), 失败/超时不改(模拟服务端没生效)。
 *  · POST files/priority —— 拦下不入真队列, 按场景回约定 cmd_id。
 *  · GET /api/cmd/{id} —— 成功/失败回既定回执; 超时恒 pending(waitCmd 10s 后走超时出口)。
 * 回执故意延迟 100/300ms: 让「乐观值先渲染」与「回执后回滚/收敛」两个窗口都可观测,
 * 同时让对照组(_editPost 旧路径)的可见延迟接近真实往返量级(非零测量)。
 *
 * 量具: 同一页面同一 1000 行抽屉, t0 = 动作发起(JS 调用)那一刻, rAF 逐帧重查
 * 目标行徽章文本, 首次变到目标文案即停 —— 对照组 = _editPost(旧路径: 回执后静默重拉),
 * 候选组 = setFilePriority(乐观写)。两组都打印实测 ms, 候选必须显著更短。
 */

const WIDE = { width: 2560, height: 1200 };
const TABLE = 'drawerContentV11';
const BADGE = '.dt11-pbadge';
const CMD_OK = 'e2e-prio-ok';
const CMD_FAIL = 'e2e-prio-fail';
const CMD_TIMEOUT = 'e2e-prio-timeout';

function makeFilesK(n = 1000) {
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push({
      name: `D/f${String(i).padStart(4, '0')} - file.mkv`,
      size: 1_000_000 + i * 999,
      progress: (i % 4) / 4,
      priority: 1,
      availability: i % 5 === 0 ? undefined : 0.3 + (i % 7) / 10,
    });
  }
  return out;
}

/** 目标行徽章文本(每帧重查: 换帧可能替换元素, 持引用会读到陈旧节点)。 */
async function badgeText(page, idx) {
  return page.evaluate(({ table, badge, idx }) => {
    const rows = document.querySelectorAll(`.group-row[data-table="${table}"]`);
    const tag = `f${String(idx).padStart(4, '0')}`;
    for (const r of rows) {
      if ((r.textContent || '').includes(tag)) {
        const b = r.querySelector(badge);
        return b ? (b.textContent || '').trim() : '';
      }
    }
    return '';
  }, { table: TABLE, badge: BADGE, idx });
}

/**
 * 量一次可见延迟: 发起动作后逐帧采样徽章文本, 首次到达目标文案返回 ms。
 * mode=control 走旧路径 _editPost(回执后静默重拉); mode=optimistic 走 W6a 通道。
 */
async function measureVisible(page, { mode, idx, target = '最高', limitMs = 5000 }) {
  return page.evaluate(async ({ mode, idx, target, limitMs, table, badge }) => {
    const el = document.querySelector('#app');
    const vm = el && el._vnode && el._vnode.component ? el._vnode.component.proxy : null;
    if (!vm) return -1;
    const t0 = performance.now();
    if (mode === 'optimistic') vm.setFilePriority(7, [idx]);
    else vm._editPost(vm.drawer.hash, 'files/priority', { indices: [idx], priority: 7 }, 'x');
    return await new Promise((resolve) => {
      const check = () => {
        const rows = document.querySelectorAll(`.group-row[data-table="${table}"]`);
        const tag = `f${String(idx).padStart(4, '0')}`;
        let text = '';
        for (const r of rows) {
          if ((r.textContent || '').includes(tag)) {
            const b = r.querySelector(badge);
            text = b ? (b.textContent || '').trim() : '';
            break;
          }
        }
        if (text === target) resolve(Math.round(performance.now() - t0));
        else if (performance.now() - t0 > limitMs) resolve(-1);
        else requestAnimationFrame(check);
      };
      requestAnimationFrame(check);
    });
  }, { mode, idx, target, limitMs, table: TABLE, badge: BADGE });
}

/** 观察「乐观值出现 -> 回滚到原值」两段: 返回 first(ms) / back(ms)。 */
async function measureRollback(page, { idx, target = '最高', origin = '正常', limitMs = 15000 }) {
  return page.evaluate(async ({ idx, target, origin, limitMs, table, badge }) => {
    const el = document.querySelector('#app');
    const vm = el && el._vnode && el._vnode.component ? el._vnode.component.proxy : null;
    const t0 = performance.now();
    vm.setFilePriority(7, [idx]);
    const read = () => {
      const rows = document.querySelectorAll(`.group-row[data-table="${table}"]`);
      const tag = `f${String(idx).padStart(4, '0')}`;
      for (const r of rows) {
        if ((r.textContent || '').includes(tag)) {
          const b = r.querySelector(badge);
          return b ? (b.textContent || '').trim() : '';
        }
      }
      return '';
    };
    let firstAt = -1;
    return await new Promise((resolve) => {
      const check = () => {
        const text = read();
        const now = performance.now() - t0;
        if (text === target && firstAt < 0) firstAt = now;
        if (firstAt >= 0 && text === origin) return resolve({ first: Math.round(firstAt), back: Math.round(now - firstAt) });
        if (now > limitMs) return resolve({ first: Math.round(firstAt), back: -1 });
        requestAnimationFrame(check);
      };
      requestAnimationFrame(check);
    });
  }, { idx, target, origin, limitMs, table: TABLE, badge: BADGE });
}

/** 开页 -> torrents -> 双击首行 -> 内容页签 -> dt11 千行锚。 */
async function openK(page, skin, filesState) {
  await page.setViewportSize(WIDE);
  await page.addInitScript(() =>
    localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
  await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();
  const anchor = drawer.locator(`[data-dt-table-anchor="${TABLE}"]`);
  await expect(anchor.locator(`.group-row[data-table="${TABLE}"]`).first()).toBeVisible({ timeout: 10_000 });
  return { drawer, anchor };
}

/** 注册 files 桩 + priority 桩 + 回执桩; 返回占位数组(供断言服务端真值)。 */
async function stubPriority(page, filesState, { receipt, delayMs = 0 }) {
  await page.route('**/api/torrents/*/files', (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify(filesState) }));
  await page.route('**/api/torrents/*/files/priority', async (route) => {
    const body = route.request().postDataJSON();
    if (receipt === 'ok') {
      for (const i of body.indices) filesState[i] = { ...filesState[i], priority: body.priority };
    }
    const id = receipt === 'ok' ? CMD_OK : receipt === 'fail' ? CMD_FAIL : CMD_TIMEOUT;
    await route.fulfill({ json: { queued: true, cmd_id: id } });
  });
  await page.route(`**/api/cmd/${CMD_OK}`, async (route) => {
    if (delayMs) await new Promise((r) => setTimeout(r, delayMs));
    await route.fulfill({ json: { status: 'ok' } });
  });
  await page.route(`**/api/cmd/${CMD_FAIL}`, async (route) => {
    if (delayMs) await new Promise((r) => setTimeout(r, delayMs));
    await route.fulfill({ json: { status: 'error', error: '桩服务注入的失败(qB 拒绝)' } });
  });
  await page.route(`**/api/cmd/${CMD_TIMEOUT}`, (route) => route.fulfill({ json: { status: 'pending' } }));
  return filesState;
}

for (const skin of SKINS) {
  test.describe(`W6a 抽屉文件优先级乐观写 ${skin}`, () => {

    test(`成功路径: 乐观写先于 POST, 可见延迟对照旧路径显著缩短 @fast (${skin})`, async ({ page }) => {
      test.setTimeout(90_000);
      collectRuntimeErrors(page);
      const filesState = makeFilesK();
      await stubPriority(page, filesState, { receipt: 'ok', delayMs: 100 });
      await openK(page, skin, filesState);

      // 对照组(旧路径 _editPost: 等回执 + 静默重拉): idx 0
      const control = await measureVisible(page, { mode: 'control', idx: 0 });
      expect(control, `对照组可见延迟应可测(实测 ${control}ms)`).toBeGreaterThan(0);
      await page.waitForTimeout(400); // 等旧路径重拉落定, 再量候选组

      // 候选组(W6a 乐观写): idx 1
      const candidate = await measureVisible(page, { mode: 'optimistic', idx: 1 });
      expect(candidate, `乐观路径应可测(实测 ${candidate}ms)`).toBeGreaterThanOrEqual(0);
      expect(candidate, `乐观可见延迟应显著短于旧路径(实测 候选 ${candidate}ms vs 对照 ${control}ms)`)
        .toBeLessThan(control);
      expect(candidate, `乐观路径应在 2 帧内可见(实测 ${candidate}ms)`).toBeLessThan(60);
      expect(await badgeText(page, 0), '对照组最终徽章 == 最高').toBe('最高');
      expect(await badgeText(page, 1), '候选组徽章 == 最高').toBe('最高');
      console.log(`      [W6a 成功 ${skin}] 可见延迟 候选=${candidate}ms 对照=${control}ms (1000 files, 回执延迟 100ms)`);
    });

    test(`失败回滚: 乐观值出现 -> 回执 error 回滚到原值且与服务端真值一致 @fast (${skin})`, async ({ page }) => {
      test.setTimeout(60_000);
      collectRuntimeErrors(page);
      const filesState = makeFilesK();
      await stubPriority(page, filesState, { receipt: 'fail', delayMs: 300 });
      await openK(page, skin, filesState);

      const r = await measureRollback(page, { idx: 2 });
      expect(r.first, `失败路径的乐观值必须先出现(实测 first=${r.first}ms)`).toBeGreaterThanOrEqual(0);
      expect(r.back, `回执 error 后必须回滚到原值(实测 back=${r.back}ms)`).toBeGreaterThan(0);
      expect(await badgeText(page, 2), '回滚后徽章 == 正常').toBe('正常');
      expect(filesState[2].priority, '服务端真值仍是 1(失败未落库)').toBe(1);
      console.log(`      [W6a 失败回滚 ${skin}] 乐观可见=${r.first}ms 回滚=${r.back}ms (回执延迟 300ms)`);
    });

    test(`超时回滚: 10s 无回执 -> 回滚到原值(不把假值留在界面上) (${skin})`, async ({ page }) => {
      test.setTimeout(60_000);
      collectRuntimeErrors(page);
      const filesState = makeFilesK();
      await stubPriority(page, filesState, { receipt: 'timeout' });
      await openK(page, skin, filesState);

      const r = await measureRollback(page, { idx: 3, limitMs: 20_000 });
      expect(r.first, `超时路径的乐观值必须先出现(实测 first=${r.first}ms)`).toBeGreaterThanOrEqual(0);
      expect(r.back, `等待超时后必须回滚(实测 back=${r.back}ms)`).toBeGreaterThan(9_000);
      expect(await badgeText(page, 3), '超时回滚后徽章 == 正常').toBe('正常');
      expect(filesState[3].priority, '超时未落库, 服务端真值仍是 1').toBe(1);
      console.log(`      [W6a 超时回滚 ${skin}] 乐观可见=${r.first}ms 超时回滚=${r.back}ms (waitCmd 10s)`);
    });
  });
}
