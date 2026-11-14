// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';

/**
 * 状态栏键位开关(计划 26-11-14-0041 S5/W2; 前序件 26-11-12-0344 S5 的「键位」文字入口已被取代)。
 *
 * 背景: 状态栏右角「键位」文字钮 → **无文字图标钮**(.sb-btn.sb-kbd-sw)。两态互斥:
 *   开 = body.kbd-persist(全落点常驻显示) / 关 = 仅按住反引号显影(body.kbd-reveal)。
 *   两态共用共享 CSS 同一条显示规则(.aq-kbd 的 opacity/visibility), 切换只写 body class +
 *   本机偏好 localStorage autoqb.ui.kbdPersist(D6), 零 JS 重绘、取数链一行不动(D4)。
 *   钮内仍是状态栏唯一一处 .aq-kbd(串走 kbKeycapOf('help-panel') 现算 = Shift + /), 版式 =
 *   绝对定位角标(不进布局流 => 不挤右角速度组、不改变顶栏药丸宽度, 34px 锁高内不裁)。
 *
 * 断言面(真实手势, 不借道 vm):
 *   1. 键帽现算: 钮内键帽文本 == Shift + /(注册表 help-panel 条目 kbDisplayName 输出);
 *   2. 两态: 默认关 -> 键帽不可见; click -> body.kbd-persist + 键帽可见; 再 click -> 摘下;
 *      关态按住反引号 -> body.kbd-reveal + 键帽显影(keyboard.down/up 真实手势);
 *   3. 刷新保留: reload 后 body.kbd-persist 与键帽可见性一并恢复(D6);
 *   4. 零几何副作用: 顶栏药丸宽度与状态栏右角速度组位置在开关前后不变(W5/S4 验收面);
 *   5. 34px 锁高: 状态栏高度恒 --statusbar-h, 开关钮与键帽角标都在栏内(scrollWidth 不超
 *      clientWidth = overflow:hidden 没裁东西), 速度组未被挤出(§08 风险);
 *   6. 与 Shift+/ 互不干扰: click 开关**不开**帮助浮层; Shift+/ 仍开/关同一浮层(浮层入口
 *      保持原语义, 与键盘链同源未动)。
 */

for (const skin of SKINS) {
  test.describe(`状态栏键位开关 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`两态 + 刷新保留 + 键帽现算 + 零几何副作用 + 34px 不裁 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openApp(page, skin);

      const sb = page.locator('.statusbar');
      const sw = sb.locator('button.sb-kbd-sw');
      await expect(sw).toBeVisible();
      await expect(sw, '开关钮无文字(图标钮), 可达名走 aria-label').toHaveAttribute('aria-label', '键位提示');
      // D11: 模板写原生 title(控件自身功能说明), 运行时由 shared/ui_feedback.js 的 title -> data-aq-tip
      // 单向迁移接管(全站悬浮提示统一口径, 迁移后 DOM 里不再有 title —— 不是本钮的特例)
      await expect(sw, 'D11: title 写控件自身功能说明(运行时归一为 data-aq-tip)')
        .toHaveAttribute('data-aq-tip', '按住 ` 显影 / 点此常驻');
      const kbd = sw.locator('.aq-kbd');
      await expect(kbd, '键帽现算(注册表 help-panel -> Shift + /, I1 不手抄)').toHaveText('Shift + /');
      // 默认关 = 仅按住反引号显影: 键帽在 DOM 但不可见(opacity:0/visibility:hidden)
      await expect(page.locator('body')).not.toHaveClass(/kbd-persist/);
      await expect(kbd).toBeHidden();

      // 基线几何: 顶栏药丸宽度 + 状态栏右角速度组位置(W5 验收: 开关/角标都不许推挤)
      const geoOf = () => page.evaluate(`(() => {
        const sbEl = document.querySelector('.statusbar');
        const addBtn = document.querySelector('.topbar .add-btn');
        const speed = sbEl.querySelector('.sb-speed');
        const swEl = sbEl.querySelector('button.sb-kbd-sw');
        const sbr = sbEl.getBoundingClientRect();
        const swr = swEl.getBoundingClientRect();
        const kbdEl = swEl.querySelector('.aq-kbd');
        const kr = kbdEl.getBoundingClientRect();
        return {
          h: sbr.height,
          sw: sbEl.scrollWidth, cw: sbEl.clientWidth,
          addW: addBtn.getBoundingClientRect().width,
          speedLeft: speed.getBoundingClientRect().left,
          speedRight: speed.getBoundingClientRect().right,
          swTop: swr.top - sbr.top, swBottom: sbr.bottom - swr.bottom,
          kbdTop: kr.top - sbr.top, kbdBottom: sbr.bottom - kr.bottom,
        };
      })()`);
      const before = await geoOf();

      // 开: body.kbd-persist + 全落点键帽可见(状态栏开关钮与顶栏两处同一条显示规则)
      await sw.click();
      await expect(page.locator('body')).toHaveClass(/kbd-persist/);
      await expect(sw).toHaveAttribute('aria-pressed', 'true');
      await expect(kbd).toBeVisible();
      await expect(page.locator('.topbar .add-btn .aq-kbd')).toBeVisible();
      await expect(page.locator('.topbar .col-picker .aq-kbd')).toBeVisible();

      const after = await geoOf();
      expect(after.addW, '顶栏药丸宽度不因键位变化(W5: 角标绝对定位不进布局流)').toBeCloseTo(before.addW, 1);
      expect(after.speedLeft, '状态栏右角速度组位置不因开关键帽变化(§08 不挤压)').toBeCloseTo(before.speedLeft, 1);
      expect(after.speedRight, '速度组右缘不变').toBeCloseTo(before.speedRight, 1);

      // 34px 锁高 + overflow:hidden 不裁角标(键帽角标竖向在栏内, 未被裁)
      expect(after.h, '--statusbar-h 锁高恒 34px(不随开关/键帽增高)').toBeCloseTo(34, 0);
      expect(after.swTop, '开关钮顶缘在栏内').toBeGreaterThanOrEqual(0);
      expect(after.swBottom, '开关钮底缘在栏内').toBeGreaterThanOrEqual(0);
      expect(after.kbdTop, '键帽角标顶缘在栏内(W5 基线内 inset, 不用 top:-6px)').toBeGreaterThanOrEqual(0);
      expect(after.kbdBottom, '键帽角标底缘在栏内(不被 overflow:hidden 裁)').toBeGreaterThanOrEqual(0);
      expect(after.sw, '状态栏层无横向裁切(overflow:hidden 下 scrollWidth 超出 = 有内容被裁)')
        .toBeLessThanOrEqual(after.cw);
      expect(await page.locator('.modal.kb-help').count(), 'click 开关不打开帮助浮层(与 Shift+/ 互不干扰)').toBe(0);

      // 刷新保留(D6: localStorage autoqb.ui.kbdPersist): body class 与键帽可见性一并恢复
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await expect(page.locator('body'), '刷新后开关态保留').toHaveClass(/kbd-persist/);
      await expect(page.locator('.statusbar button.sb-kbd-sw .aq-kbd'), '刷新后常驻键帽仍可见').toBeVisible();

      // 帮助浮层入口原语义: Shift+/ 开, Esc 关(浮层本体与键盘链零改动)
      const help = page.locator('.modal.kb-help');
      await page.keyboard.press('Shift+Slash');
      await expect(help, 'Shift+/ 仍打开帮助浮层').toBeVisible({ timeout: 5_000 });
      await expect(help).toHaveAttribute('aria-label', '键盘快捷键');
      await page.keyboard.press('Escape');
      await expect(help).toHaveCount(0);

      // 关: 再 click -> 摘 kbd-persist, 回到「仅按住反引号显影」
      await page.locator('.statusbar button.sb-kbd-sw').click();
      await expect(page.locator('body')).not.toHaveClass(/kbd-persist/);
      await expect(page.locator('.statusbar button.sb-kbd-sw .aq-kbd')).toBeHidden();
      // 按住反引号 = 显影态(body.kbd-reveal), 松手即隐(S1 链未变)
      await page.keyboard.down('Backquote');
      await expect(page.locator('body')).toHaveClass(/kbd-reveal/);
      await expect(page.locator('.statusbar button.sb-kbd-sw .aq-kbd'), '关态下按住反引号键帽显影').toBeVisible();
      await page.keyboard.up('Backquote');
      await expect(page.locator('body')).not.toHaveClass(/kbd-reveal/);
      await expect(page.locator('.statusbar button.sb-kbd-sw .aq-kbd')).toBeHidden();
    });
  });
}
