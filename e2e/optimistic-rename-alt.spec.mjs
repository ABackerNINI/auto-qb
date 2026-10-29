// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { CMD_RESULT, requireMode } from './lib/mode.mjs';
void CMD_RESULT; // 模式四元组随 lib/mode 单点走(本组只跑 ok 档, 门控见 requireMode)
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { withVm } from './lib/vm.mjs';
import { clickRow, ctxItemById, openApp, tab } from './lib/gestures.mjs';

/**
 * 乐观 UI 扩面 e2e 两条(计划 26-10-30-0610 §04 S5 / 决策 D9) —— 贴 26-10-06 计划
 * (26-10-06-0708)落好的既有矩阵与 lib 四件, 与单测四态(tests/test_webui_optimistic_rename_alt.py)
 * 分工: 单测在 node 里钉四态逻辑, 本文件在真浏览器里钉**用户可见帧**级的两条主路径:
 *
 *   1. 改名(commit 5ac63a7e): 确认对话框 -> 行上新名当帧可见(applyOptimisticPatch 先于
 *      POST) -> 轮询/快照 name 对齐后仍保持新名, 不弹回旧名。
 *   2. 乌龟按钮(commit e6ef9344): 点击 -> 高亮当帧翻转(altOverride 预翻转) -> 轮询确认
 *      (statsServer 对账清除)后保持, 不弹回; tooltip(sbAltTitle 经 title->data-aq-tip
 *      单向迁移落 DOM, ui_feedback.js)同一显示单点同步跟随。
 *
 * 「弹回」是**可见帧**级别的事(乐观值被轮询旧值打回再重贴, 中间可能闪一帧), 事后单点读数
 * 会漏 —— 故两条都用 10ms 页面内采样器(仿 optimistic.spec hang 探针 __h 同款, D4 第2类
 * vm/DOM 时序探针)记录全窗起落, 收口后对采样序列断言「一旦翻过去就不再翻回来」。
 *
 * 模式门控: 只跑默认档 E2E_CMD_RESULT=ok —— 两条都断言「确认后保持」, error 轮(失败回滚)
 * 与 hang 轮(3s 兜底回滚)的对应面已由单测四态覆盖, 不在本组重复(requireMode 整组 skip)。
 *
 * 桩真值落地(本批随行加的测试夹具, scripts/ui_harness.py::_apply_truth): rename_torrent /
 * speed_alt_toggle 两命令原先只回 ok 不落真值, 「快照确认后不弹回」在桩上不可达; 现按
 * pause/resume 同款纪律把真值落到合成数据(rename 经 store._apply 增量 patch 走生产推导 /
 * alt 直改 store.server_state, 随 /api/state status.server 回传)。
 *
 * ── 测试计划(计划 26-10-30-0610 §04 S5, 每条 test 一行) ──
 * - 改名立即可见不弹回: 确认 -> 新名 400ms 内上行(阈值同 optimistic.spec「补丁先于 POST」
 *   预算) -> op 注册 -> 快照对齐收口(pendingOps 清除且 < 7.5s, 走满 8s 兜底即红) -> 采样全窗
 *   无弹回帧 -> 收尾把行名改回原名(长驻桩共享实例, 合成名是追剧聚合的输入, 不还原会污染
 *   后续 spec)。
 * - 乌龟按钮立即翻转不弹回: 前置自证初始熄灭 -> 点击 -> 高亮 400ms 内翻转 -> 轮询确认
 *   (altOverride 清除且 sbAltOn 保持 true) -> 采样全窗无弹回帧 + tooltip 同步 -> 收尾点回
 *   主速度并等确认(prism -> atlas 串行跑同一桩, 备用态残留会带偏下一皮肤的前置自证)。
 *
 * 阈值口径: 400ms(乐观贴上是 POST 之前的同步动作, 与 optimistic.spec BUDGET 同值);
 * 7.5s(快照对齐收口上界 —— TRUTH_HOLD_MS=8s 兜底之前; 收口实测 ~2-3s = 回执 0.12s 真值
 * 落地 + 1.5-2s 轮询节拍); 这些是回归基准, 不是等待。
 */

/** 乐观贴上/预翻转的可见上界(optimistic.spec「补丁先于 POST」同款预算)。 */
const APPEAR_BUDGET = 400;
/** 快照对齐收口上界 —— 必须 < TRUTH_HOLD_MS(8s): 走满兜底收口 = 「确认后不弹回」没测到。 */
const SETTLE_BUDGET = 7_500;
/** 轮询确认上界(确认延迟 = 距下个 sync 节拍 ≤1.5s + 收尾余量)。 */
const CONFIRM_BUDGET = 10_000;

/**
 * 装 10ms 页面内采样器(D4 第2类): 自 t0 起每 10ms 记一条 reader(page) 的读数。
 * @param {import('@playwright/test').Page} page
 * @param {string} windowName —— 采样器挂 window 的键(各 test 独立 context, 不互扰)。
 * @param {string} readerExpr —— 页面内表达式, 返回本拍读数(JSON 可序列化)。
 */
async function armSampler(page, windowName, readerExpr) {
  await page.evaluate(`(() => {
    const W = ${JSON.stringify(windowName)};
    window[W] = { t0: null, rows: [] };
    clearInterval(window[W + 'i']);
    window[W + 'i'] = setInterval(() => {
      const s = window[W];
      if (s.t0 === null) return;
      s.rows.push({ t: Math.round(performance.now() - s.t0), v: (${readerExpr}) });
    }, 10);
  })()`);
}

/** 读采样器全窗(并停掉定时器)。 */
async function readSampler(page, windowName) {
  return page.evaluate(`(() => {
    const W = ${JSON.stringify(windowName)};
    clearInterval(window[W + 'i']);
    const s = window[W];
    return s && s.t0 ? s.rows : [];
  })()`);
}

for (const skin of SKINS) {
  test.describe(`乐观 UI 扩面 ${skin}(计划 26-10-30-0610 S5)`, () => {
    /* 两条都断言「确认后保持」—— error(回滚)/hang(3s 兜底)轮的对应面由单测四态覆盖 */
    requireMode(test, { cmdResult: 'ok' });
    installRuntimeErrorGuard(test);

    test('S5-e2e 改名: 确认后行上新名立即可见, 快照对齐后保持不弹回', async ({ page }) => {
      await openApp(page, skin);
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      const row = page.locator('.torrent-row').first();
      const hash = await row.getAttribute('data-hash');
      expect(hash, '行带 data-hash').toBeTruthy();
      const oldName = await row.locator('.g-name-text').textContent();
      expect(oldName, '前置自证: 行上有名字').toBeTruthy();
      // 以 data-hash 锚定目标行: 整表重渲染会换掉行节点, first() 定位可能漂到别的行
      // (optimistic.spec T3 同款)
      const rowLoc = page.locator(`.torrent-row[data-hash="${hash}"]`);
      const nameText = rowLoc.locator('.g-name-text');
      const newName = `${oldName} E2E-RENAMED`;

      await armSampler(
        page, '__rn',
        `(document.querySelector('.torrent-row[data-hash="${hash}"] .g-name-text') || {}).textContent || null`,
      );

      await clickRow(page, rowLoc, { button: 'right' });
      const item = ctxItemById(page, 'rename');
      await expect(item).toBeVisible({ timeout: 5_000 });
      await item.click();
      const dlg = page.locator('.modal.rename-dialog');
      await expect(dlg).toBeVisible();
      await dlg.locator('.modal-field input').fill(newName);
      // t0 钉在确认按钮的 click 事件(捕获阶段, armClick 同款: 不含鼠标开销) —— 乐观补丁
      // 在这条链路里同步贴上, 采样出的「新名首现时刻」就是纯前端侧的当帧数字。
      const okBtn = dlg.locator('.modal-actions .bt.primary');
      await okBtn.evaluate((el) => el.addEventListener('click', () => {
        window.__rn.t0 = performance.now();
      }, { capture: true, once: true }));
      await okBtn.click();

      // 1. 立即可见: 新名在 APPEAR_BUDGET 内上过行(补丁先于 POST)
      await expect.poll(() => page.evaluate(`(() => {
        const hit = window.__rn.rows.find((r) => r.v === ${JSON.stringify(newName)});
        return hit ? hit.t : null;
      })()`), {
        message: `确认 -> 行上新名可见(阈值 ${APPEAR_BUDGET}ms; null = 从未出现)`,
        timeout: APPEAR_BUDGET + 1_500,
      }).toBeLessThan(APPEAR_BUDGET);

      // 2. op 已注册(贴上)—— 收口 poll 的首采样若抢在注册前会空过, 先证存在再等清除
      await expect.poll(() => withVm(page, `return !!vm.pendingOps[${JSON.stringify(hash)}];`), {
        message: '确认 -> rename 乐观 op 已注册', timeout: 2_000,
      }).toBe(true);

      // 3. 快照对齐收口: pendingOps 清除且在 8s 兜底之前 —— 走满兜底收口说明「确认后
      //    保持」的值覆盖链断了(和失败回滚一个观感), 正是本条要抓的回归
      await expect.poll(() => withVm(page, `return !vm.pendingOps[${JSON.stringify(hash)}];`), {
        message: `快照 name 对齐收口(<${SETTLE_BUDGET}ms; 走满 8s 兜底即红)`,
        timeout: SETTLE_BUDGET,
      }).toBe(true);

      // 4. 不弹回: 采样全窗里新名一旦上过行就不再出现别的行名(弹回是可见帧, 10ms 采样必中)
      const rows = await readSampler(page, '__rn');
      const i0 = rows.findIndex((/** @type {{v: string|null}} */ r) => r.v === newName);
      expect(i0, '采样窗内新名确曾上过行').toBeGreaterThanOrEqual(0);
      const bounce = rows.slice(i0).find((/** @type {{v: string|null}} */ r) => r.v !== newName);
      expect(bounce, `新名上行后不得再变(弹回帧 t=${bounce ? bounce.t : '-'}ms, name=${bounce ? JSON.stringify(bounce.v) : '-'})`)
        .toBeUndefined();

      // 5. 收尾: 改回原名 —— 长驻桩共享实例, 合成名是追剧聚合(shows 视图)的输入, 不还原
      //    会污染后续 spec; 走同一条真实手势链路, 顺带复验乐观补丁可重复。
      await clickRow(page, rowLoc, { button: 'right' });
      const item2 = ctxItemById(page, 'rename');
      await expect(item2).toBeVisible({ timeout: 5_000 });
      await item2.click();
      const dlg2 = page.locator('.modal.rename-dialog');
      await expect(dlg2).toBeVisible();
      await dlg2.locator('.modal-field input').fill(oldName);
      await dlg2.locator('.modal-actions .bt.primary').click();
      await expect.poll(async () => (await nameText.textContent()) || '', {
        message: '收尾: 行名还原成原名(桩保真)', timeout: SETTLE_BUDGET,
      }).toBe(oldName);
    });

    test('S5-e2e 乌龟: 点击高亮当帧翻转, 轮询确认后保持不弹回', async ({ page }) => {
      await openApp(page, skin);
      const btn = page.locator('.sb-alt');
      await expect(btn).toBeVisible();
      // 前置自证: 桩 fresh 起 store.server_state 为空 -> sbAltOn 恒 false(主速度)。
      // 若本前置红了, 先查是不是上一皮肤的收尾没把备用态点回去(长驻桩共享实例)。
      // title 读 data-aq-tip 而非 title: 全局悬浮提示把原生 title 单向迁走
      // (ui_feedback.js capture, DOM 里从此不存在 title), data-aq-tip 才是 DOM 真值。
      expect(await btn.evaluate((el) => el.classList.contains('on')), '前置: 初始乌龟熄灭(主速度)').toBe(false);
      await expect.poll(() => btn.getAttribute('data-aq-tip'), {
        message: '前置: 初始 tooltip 按主速度措辞', timeout: 5_000,
      }).toBe('主速度生效中 · 点击切换到备用速度(qB 乌龟)');

      await armSampler(page, '__alt', `!!(document.querySelector('.sb-alt') && document.querySelector('.sb-alt').classList.contains('on'))`);

      // t0 钉在按钮 click 事件(armClick 同款); 预翻转在 POST 之前同步贴上
      await btn.evaluate((el) => el.addEventListener('click', () => {
        window.__alt.t0 = performance.now();
      }, { capture: true, once: true }));
      await btn.click();

      // 1. 立即翻转: 高亮在 APPEAR_BUDGET 内点亮(预翻转 = 点击当帧, 0ms 级)
      await expect.poll(() => page.evaluate(`(() => {
        const hit = window.__alt.rows.find((r) => r.v);
        return hit ? hit.t : null;
      })()`), {
        message: `点击 -> 高亮翻转(阈值 ${APPEAR_BUDGET}ms; null = 从未点亮)`,
        timeout: APPEAR_BUDGET + 1_500,
      }).toBeLessThan(APPEAR_BUDGET);

      // 2. 轮询确认: server 真值带回一致 -> altOverride 清除且显示保持备用速度(对账单点 =
      //    polling.js statsServer 赋值处的 _altOverrideReconcile)
      await expect.poll(() => withVm(page, 'return vm.altOverride === null && !!vm.sbAltOn;'), {
        message: '轮询确认: altOverride 清除且显示保持备用速度', timeout: CONFIRM_BUDGET,
      }).toBe(true);

      // 3. 不弹回: 采样全窗里高亮一旦点亮就不再熄灭(熄灭帧 = 弹回) + title 同一显示单点
      const rows = await readSampler(page, '__alt');
      const i0 = rows.findIndex((/** @type {{v: boolean}} */ r) => r.v);
      expect(i0, '采样窗内高亮确曾点亮').toBeGreaterThanOrEqual(0);
      const bounce = rows.slice(i0).find((/** @type {{v: boolean}} */ r) => !r.v);
      expect(bounce, `高亮点亮后不得再熄灭(弹回帧 t=${bounce ? bounce.t : '-'}ms)`).toBeUndefined();
      await expect.poll(() => btn.getAttribute('data-aq-tip'), {
        message: '确认后 tooltip 同步(备用措辞; title 单向迁移见前置注释)', timeout: 5_000,
      }).toBe('备用速度生效中 · 点击切回主速度');

      // 4. 收尾: 点回主速度并等轮询确认 —— prism -> atlas 串行跑同一桩, 备用态残留会
      //    带偏下一皮肤的前置自证(见上)。
      await btn.click();
      await expect.poll(() => withVm(page, 'return vm.altOverride === null && !vm.sbAltOn;'), {
        message: '收尾: 切回主速度并经轮询确认(桩保真)', timeout: CONFIRM_BUDGET,
      }).toBe(true);
    });
  });
}
