// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { readInst, withVm } from './lib/vm.mjs';

/**
 * S1-b/S1-c(计划 26-11-27-0530): errlog 事件落袋 -> 通知面板可见。
 * SSE 监听注册/坏帧忽略/去重乱序/对账的判定在 node 电池真跑
 * (test_webui_static_r4_poll_auth_lifecycle.py); 本 spec 在真浏览器验落袋后的
 * 徽标 + 面板 DOM。双皮肤口径取 SKINS(prism/atlas, 模板与 CSS 是 shared 单点)。
 * 注入只走 withVm 第 1 类(桩一条事件载荷), 开面板是真手势点击 .sb-err。
 */
for (const skin of SKINS) {
  test.describe(`通知面板 errlog 落袋 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`错误日志事件入历史 / 未读徽标 / 面板可见 @fast (${skin})`, async ({ page }) => {
      await openApp(page, skin);
      const entry = 'S1-b e2e 通知';
      await withVm(page, `vm.onErrlogEvent({seq: 9100, level: "ERROR", msg: "${entry}"});`);

      // 面板关闭: 新条目计未读, 入口徽标亮起
      expect(await readInst(page, 'vm._errUnread')).toBeGreaterThan(0);
      await expect(page.locator('.sb-err-badge')).toBeVisible();

      // 真手势开面板: 条目可见, 打开后未读清零(state.js watcher)
      await page.locator('.sb-err').click();
      await expect(page.locator('.err-panel')).toBeVisible();
      await expect(page.locator('.err-panel')).toContainText(entry);
      await expect.poll(() => readInst(page, 'vm._errUnread')).toBe(0);
    });
  });
}
