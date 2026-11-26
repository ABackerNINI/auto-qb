// @ts-check
import { expect } from '@playwright/test';

/**
 * 死类守阵(pitfalls/web-ui/esc-attr-quote-dead-class):
 * 字符串 DOM 层若把「整段属性文本」(如 ` class="x"`)当插值传进 dtHtml, esc 会把引号转成
 * &quot;, HTML 解析还原成**类名里的引号字符** —— 元素 class 实际值带引号, 按类名写的 CSS
 * 全线静默失效(零报错)。本守阵在渲染后的 DOM 上做坑档判别: 全文档任何元素的 class 值
 * 不得含 `"` 字符。经典(Vue :class)与变体(dtHtml 字符串)两态都查 —— Vue 侧若有人照抄
 * 旧 DOM 逐字节等价把引号拼回 :class 也一样红。
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} label 场景标注(进失败消息)
 */
export async function expectNoDeadClass(page, label) {
  const hits = await page.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll('[class]')) {
      const cls = el.getAttribute('class') || '';
      if (cls.includes('"')) {
        out.push(`<${el.tagName.toLowerCase()}${el.getAttribute('data-dt-host') ? ` data-dt-host="${el.getAttribute('data-dt-host')}"` : ''}> class=${JSON.stringify(cls.slice(0, 96))}`);
      }
    }
    return out;
  });
  expect(hits, `${label}: 不得出现「类名含引号」的死类(坑档 esc-attr-quote-dead-class —— 出现即该元素的 CSS 修饰全线静默失效)`).toEqual([]);
}
