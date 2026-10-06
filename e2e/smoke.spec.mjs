// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS, TORRENTS } from './harness.mjs';
import { collectRuntimeErrors } from './lib/errors.mjs';

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
 * (错误采集器已提为 e2e/lib/errors.mjs 单点 —— S0 基建, 计划 26-10-06-0708; 断言逻辑零变化。) */

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

    /* 几何守卫(2026-10-06, 计划 26-10-06-1009): 右对齐列表头文字与值文字必须落在同一竖线上。
     * 为什么需要它: 本轮缺陷的成因是「盒子模型」—— 表头 .h-cell 为容纳拖拽把手多出的 10px
     * 右内边距, 让右对齐表头比数值左偏 11px(明细 10px), 排序时箭头再顶 11px; 而 tests/test_web.py
     * 的近 300 条守阵全是**读文件文本**的静态断言, 原理上看不见盒子模型。故在真浏览器 + 桩服务这层
     * 加一条几何断言(桩服务由 playwright.config.mjs 的 webServer 自动拉起)。
     * 口径: 量**内容盒**右缘之差(盒右缘 − 右内边距), 不量墨迹(值溢出被省略号截断会抖动);
     * 数据行有 1px 侧边框 ⇒ 允许 ±1px。详见 pitfalls/web-ui/header-cell-gutter.md。 */
    test('几何: 右对齐列表头与值右缘对齐(±1px), 且值格不居中', async ({ page }) => {
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.group-row', { timeout: 30_000 });
      await page.waitForTimeout(300); /* 等列对齐规则注入 + 首帧布局稳定 */

      const bad = await page.evaluate(() => {
        /* 内容盒右缘 = 盒右缘 − 右内边距 */
        const cRight = (el) => el.getBoundingClientRect().right - parseFloat(getComputedStyle(el).paddingRight);
        const out = [];
        /* 表头网格表 = .group-head(分组/种子/追剧) + .detail-head(组内明细/集明细) */
        for (const head of document.querySelectorAll('.group-head[data-table], .detail-head[data-table]')) {
          const page_ = head.getAttribute('data-table');
          const cells = [...head.children].filter((c) => c.classList.contains('h-cell'));
          if (!cells.length) continue;
          const row = document.querySelector(page_ === 'detail'
            ? '.member-row[data-table="detail"]'
            : `.group-row[data-table="${page_}"]`);
          if (!row) continue;
          const rcells = [...row.children];
          cells.forEach((hc, i) => {
            if (getComputedStyle(hc).textAlign !== 'right') return; /* 只看右对齐列(左/中列无此缺陷) */
            const rc = rcells[i];
            if (!rc) return;
            const d = cRight(rc) - cRight(hc);
            if (Math.abs(d) > 1) out.push({ page: page_, delta: Math.round(d * 100) / 100 });
            if (getComputedStyle(rc).textAlign === 'center') out.push({ page: page_, zeroCentered: true });
          });
        }
        return out;
      });

      expect(bad, `右对齐列错位 / 0 值居中: ${JSON.stringify(bad)}`).toEqual([]);
    });
  });
}
