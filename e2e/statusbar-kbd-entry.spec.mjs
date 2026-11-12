// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';

/**
 * 状态栏「键位」帮助入口(计划 26-11-12-0344 S5)。
 *
 * 背景: Shift+/ 帮助浮层此前零按钮入口(不知道 Shift+/ 存在就永远发现不了), S5 在状态栏
 * 加「键位」文字钮(.sb-btn, 与「完整统计」同款) + Shift+/ 键帽(.aq-kbd, 串走 kbKeycapOf
 * -> kbKeycapById -> kbShortcutDisplay 现算, id 引用注册表 help-panel)。
 *
 * 断言面:
 *   1. 键帽现算: 入口钮键帽文本 == Shift + /(注册表 help-panel 条目 kbDisplayName 输出,
 *      非模板手抄);
 *   2. click 开/关与 Shift+/ 行为一致: click 分派 = help-panel 同链 _kbToggleKbHelp(注册表
 *      run 同一 toggle 方法) —— click 打开的就是 Shift+/ 的同一浮层(.modal.kb-help); 浮层
 *      开着时 Shift+/ 仍可键盘自切换关(KB_SELF_TOGGLE_OVERLAY 本体不动, 纯显示层反证面);
 *      Esc/再 click 走既有开合链幂等可复用;
 *   3. 34px 锁高无溢出(计划 §07「状态栏溢出」对策的实测面): 状态栏高度恒 --statusbar-h
 *      (34px); 入口钮垂直在栏内; 状态栏层无横向裁切(overflow:hidden 之下 scrollWidth 超出
 *      clientWidth 即有内容被裁); 右角速度组未被挤出(spacer 先吸收入口增宽)。
 *
 * 注: 浮层开着时 modal-mask(z-index 130) 盖住状态栏, 「再 click 关」物理不可达 —— 鼠标关走
 * Esc/x/遮罩(既有 D8 口径零改动), 键盘关走 Shift+/ 自切换, 本 spec 两路都断言。
 * 断言口径: 真实手势(keyboard.press / click), 不借道 vm; 几何读 DOM getBoundingClientRect。
 */

for (const skin of SKINS) {
  test.describe(`状态栏键位帮助入口 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`键帽现算 + click 开关浮层与 Shift+/ 同链 + 34px 锁高无溢出 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openApp(page, skin);

      // 入口钮: .sb-btn 同款文字钮, 键帽串现算(注册表 help-panel -> Shift + /)
      const entry = page.locator('.statusbar button.sb-btn', { hasText: '键位' });
      await expect(entry).toBeVisible();
      await expect(entry.locator('.aq-kbd')).toHaveText('Shift + /');

      // 34px 锁高(计划 §07 对策实测面): 高度/按钮栏内/无横向裁切/速度组未被挤出
      const geo = /** @type {{h:number, sw:number, cw:number, btnTop:number, btnBottom:number, spacerW:number, speedOut:number}} */ (
        await page.evaluate(`(() => {
        const sb = document.querySelector('.statusbar');
        const btn = [...sb.querySelectorAll('button.sb-btn')].find((b) => b.textContent.includes('键位'));
        const sbr = sb.getBoundingClientRect();
        const br = btn.getBoundingClientRect();
        return {
          h: sbr.height,
          sw: sb.scrollWidth, cw: sb.clientWidth,
          btnTop: br.top - sbr.top, btnBottom: sbr.bottom - br.bottom,
          spacerW: sb.querySelector('.sb-spacer').getBoundingClientRect().width,
          speedOut: Math.max(0, sb.querySelector('.sb-speed').getBoundingClientRect().right - sbr.right),
        };
      })()`)
      );
      expect(geo.h, '--statusbar-h 锁高恒 34px(不随入口钮增高)').toBeCloseTo(34, 0);
      expect(geo.btnTop, '入口钮顶缘在栏内(34px 锁高内无溢出)').toBeGreaterThanOrEqual(0);
      expect(geo.btnBottom, '入口钮底缘在栏内(34px 锁高内无溢出)').toBeGreaterThanOrEqual(0);
      expect(geo.sw, '状态栏层无横向裁切(overflow:hidden 下 scrollWidth 超出 = 有内容被裁)')
        .toBeLessThanOrEqual(geo.cw);
      expect(geo.speedOut, '右角速度组未被挤出(spacer 先吸收入口增宽)').toBe(0);

      // click 开: 打开的就是 Shift+/ 的同一浮层(D8: 内容/布局零改动, 这里只断外壳锚)
      await entry.click();
      const help = page.locator('.modal.kb-help');
      await expect(help, 'click 必须打开 Shift+/ 帮助浮层').toBeVisible({ timeout: 5_000 });
      await expect(help).toHaveAttribute('aria-label', '键盘快捷键');

      // Esc 关(浮层既有退栈链) -> 再 click 开(入口幂等可复用)
      await page.keyboard.press('Escape');
      await expect(help).toHaveCount(0);
      await entry.click();
      await expect(help).toBeVisible({ timeout: 5_000 });

      // 与 Shift+/ 行为一致的反证面: 浮层开着时 Shift+/ 仍键盘自切换关(KB_SELF_TOGGLE_OVERLAY
      // 本体未被入口钮改动 —— 纯显示层); 关掉后 click 可再开。
      await page.keyboard.press('Shift+Slash');
      await expect(help, 'Shift+/ 自切换关(键盘链与 click 同链未变)').toHaveCount(0, { timeout: 5_000 });
      await entry.click();
      await expect(help).toBeVisible({ timeout: 5_000 });
      await page.keyboard.press('Escape');
      await expect(help).toHaveCount(0);
    });
  });
}
