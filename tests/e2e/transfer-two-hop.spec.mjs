// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { readInst, withVm } from './lib/vm.mjs';

/**
 * S2-b / 双跳时序(计划 26-11-27-0530): transfer 受理段 POST 返回后本地渲染,
 * 终态回执到达才结算三件套; 已结算行不得被后到的受理段渲染降级回「后台验证中」。
 * 判定主体在 node 电池真跑(test_transfer_flow_confirm.py), 本 spec 在真浏览器双皮肤
 * (SKINS: prism/atlas, 模板与 CSS 是 shared 单点)验两段可见与幂等的 DOM 侧观感。
 * 注入只走 withVm 第 1 类(桩 POST/waitCmd/setRowIcon 控制两跳时序), 不真发 qB 请求。
 */
for (const skin of SKINS) {
  test.describe(`转移两段回执 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`受理段先到 / 终态后到 / 已结算不降级 @fast (${skin})`, async ({ page }) => {
      await openApp(page, skin);

      // 桩两跳: POST 立即回 cmd_id -> 受理段 pending「后台验证中」可见;
      // waitCmd 挂起等 __tfResolve -> 终态回执才结算。setRowIcon 落内存探针。
      await withVm(page, `
        vm.__tfIcons = {}; vm.__tfLog = []; vm.__tfSettled = null;
        const origApi = vm.api.bind(vm);
        vm.api = async (path, opt) => {
          if (path === '/api/transfer/run') {
            vm.__tfPosted = JSON.parse(opt.body);
            return { cmd_id: 'c-e2e' };
          }
          return origApi(path, opt);
        };
        vm.setRowIcon = (h, kind, msg) => {
          vm.__tfIcons[h] = { kind, msg }; vm.__tfLog.push([h, kind, msg]);
        };
        vm._runningToast = () => ({ tid: -1 });
        vm._finishToast = () => {};
        vm._settleRunningToast = () => Promise.resolve();
        vm.transferTargetsReload = () => Promise.resolve();
        vm.clearSelection = () => {};
        const origSettle = vm._transferSettleIcon.bind(vm);
        vm._transferSettleIcon = (settled, h, k, r) => {
          vm.__tfSettled = settled; return origSettle(settled, h, k, r);
        };
        vm.__tfResolve = null;
        vm.waitCmd = () => new Promise((r) => {
          vm.__tfResolve = () => r({ ok: true, truth: { results: [
            { hash: 'ee01', '状态': '成功', '原因': '' },
          ] } });
        });
        vm._transferRunning = false;
        vm.__tfRun = vm._transferExec('副种机', '副种机', ['ee01'], [], false);
      `);

      // 第一跳: POST 已回, 受理段 pending + 「后台验证中」可见, 尚未结算
      await expect.poll(() => readInst(page, "vm.__tfIcons.ee01 && vm.__tfIcons.ee01.msg")).toBe('后台验证中');
      expect(await readInst(page, "vm.__tfIcons.ee01.kind")).toBe('pending');
      expect(await readInst(page, "vm.__tfSettled")).toBe(null);

      // 第二跳: 放终态回执 -> 三件套结算(行内 ok / toast ok / 目标缓存刷新)
      await withVm(page, `vm.__tfResolve(); return true;`);
      await readInst(page, `vm.__tfRun.then(() => true)`);
      expect(await readInst(page, "vm.__tfIcons.ee01.kind")).toBe('ok');
      expect(await readInst(page, "vm.__tfLog.length")).toBe(2);

      // 双跳竞态: 终态已记账后, 后到的受理段渲染不得降级已结算行
      await withVm(page, `vm._transferRenderAccepted(['ee01'], vm.__tfSettled, 40000); return true;`);
      expect(await readInst(page, "vm.__tfIcons.ee01.kind")).toBe('ok');
      expect(await readInst(page, "vm.__tfLog.length")).toBe(2);
    });
  });
}
