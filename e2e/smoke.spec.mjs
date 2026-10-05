// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS, TORRENTS } from './harness.mjs';

/**
 * WEB UI 冒烟(最小集) —— 每次改前端都该过一遍的那几条。
 *
 * 为什么这一层不可省: `tests/test_web.py` 的 296 条守阵是**读文件文本**的静态断言, 有一整类
 * 故障它原理上就看不见 —— "pytest 全绿 + node --check 全绿 + 界面废掉":
 *   · Vue Options API 的四类静默白屏(computed 当函数 / 带参 computed / 三者同名 / 裸调跨模块 methods)
 *     → pitfalls/web-ui/vue-reactivity.md
 *   · JS 块注释里出现"星号斜杠"会把注释提前砍断, 尾巴落成代码态 → 页面首次执行该文件才
 *     ReferenceError 整站白屏 → pitfalls/web-ui/js-comment-terminator.md
 *     (!本文件自身就踩过一次: 在注释正文里写出该符号组合, 于是注释在第 12 行被截断,
 *      Playwright 报 `Invalid left-hand side in postfix operation` + "No tests found"。)
 *   · CSS 注释同族: 规则被浏览器静默丢弃, 无任何报错 → pitfalls/web-ui/css-comment-terminator.md
 * 本文件只钉住"页面到底活没活 + 数据对不对"; 交互时序 / 几何 / 数值那四类深水区走 ui_smoke.cjs。
 *
 * 桩服务由 playwright.config.mjs 的 webServer 自动拉起(真 create_app + 合成种子), 无需手工起。
 */

/**
 * 采集本页的运行时错误。
 * Dark Reader 这类**企业策略强装**的扩展即使 `--disable-extensions` + 全新 profile 也会注入并报错
 * (pitfalls/testing/smoke.md), 故按来源过滤 chrome-extension —— 否则本断言在本机会恒红。
 */
function collectRuntimeErrors(page) {
  const errors = [];
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() !== 'error') return;
    if ((m.location()?.url || '').startsWith('chrome-extension://')) return;
    const text = m.text();
    if (text.includes('chrome-extension://')) return;
    errors.push(`console.error: ${text}`);
  });
  return errors;
}

for (const skin of SKINS) {
  test.describe(`皮肤 ${skin}`, () => {
    test('首屏渲染健康: Vue 挂载成功、分组行渲染、无运行时错误', async ({ page }) => {
      const errors = collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });

      /* #app 带 v-cloak + `[v-cloak] { display: none }` ⇒ Vue 不 mount 就整页隐藏, 只剩背景。
       * 断言该属性**已被摘掉** = 挂载成功 —— 这是"白屏"与"数据没回来"的分界线。
       * (骨架在但某块区域空 = 模板表达式错误, 那要真机看页面, 静态判不出来。) */
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });

      /* 首屏数据经 /api/state 回来后才有行。.group-row 是 ui_smoke.cjs 的第一条断言, 同一口径。 */
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      /* 跨过一个轮询周期再看错误: "每轮重渲染才抛"的那类错只有等一轮才现形(轮询 1.5~3s 分档,
       * 300 种子的档位取 2s)。这里必须等, 不是可省的 sleep。 */
      await page.waitForTimeout(2000);

      expect(errors, `运行期错误:\n${errors.join('\n')}`).toEqual([]);
    });

    test('数据契约: status.torrents 与桩服务种子数一致', async ({ request }) => {
      const res = await request.get(`${BASE_URL}/api/state`);
      expect(res.ok(), `GET /api/state -> ${res.status()}`).toBeTruthy();

      const body = await res.json();
      /* status.torrents 是"恒回传"标量(不参与按视图裁剪), 用它判桩服务真的在供数据 ——
       * 只判 HTTP 200 会被"旧进程仍在应答"蒙过去。 */
      expect(body.status.torrents).toBe(TORRENTS);
      expect(body.status.groups).toBeGreaterThan(0);
    });
  });
}
