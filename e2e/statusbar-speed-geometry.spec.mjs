// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS_ALL } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { withVm } from './lib/vm.mjs';

/**
 * 状态栏速度组逐帧几何(计划 26-11-16-0130 S3/D12/D14)。
 *
 * 背景: fmtSpeed 单位串随量级变化("0 B/s" 5 字符 -> "1023.99 KiB/s" 13 字符), .lim 另有
 * 不限 / — / 数值三形态; .sb-spd 是 flex: 0 0 auto, .sb-speed 右缘钉死 => 数值宽变 = 整组
 * 左缘平移(用户报"速度数值变化时周边 UI 跳动")。修复 = shared 层 .val/.lim 各 13ch 定宽
 * (.val 右对齐 / .lim 左对齐), 窄屏 @media(max-width: 900px)把 .lim 退 4ch。
 *
 * 断言面(静态守阵 _scan_statusbar_speed_width 钉 CSS 事实面, 本 spec 钉真浏览器几何 ——
 * 静态断言兜不住布局, 见 pitfalls/web-ui/progress-bar.md):
 *   1. 宽视口(1440, 桌面默认): 变异全程(速度四档 + 限速三态 + 未读徽标两位数)逐帧采样
 *      (rAF + 4ms 双路, dt-live-update 同款量具), .sb-speed 与两枚 .sb-spd 的 .val/.lim 及
 *      .sb-sep 左右缘偏移 <=1px —— 含 flux 360ms numRoll 补间中间帧; .sb-err 右缘不动
 *      (徽标变宽只能向左挤 spacer, D14 零改动的几何前提), 左缘允许左移不许右移;
 *   2. 窄视口(800, 覆盖 @media max-width: 900px): 只保 .sb-speed 右缘不动 —— .lim 窄屏只设
 *      4ch 下限, 长限速值仍会撑开并把组内元素一起左推, 窄屏契约不承诺组内零位移(R2);
 *   3. 34px 锁高两态不变; 状态栏无横向裁切(overflow:hidden 下 scrollWidth > clientWidth
 *      = 有内容被裁);
 *   4. 覆盖性自证: 采样帧里必须真实出现过四个速度形 / 三个限速形 / 徽标 42 —— 防
 *      注入被真实轮询冲掉后变异序列空转、测试无病呻吟地绿。
 *
 * 注入走 withVm(e2e/lib/vm.mjs:49-51, 计划 S3 允许的形态一): 页内直写 vm.status / vm.statsServer / vm._errUnread;
 * 真实轮询会把桩值周期性写回 —— 几何不变量对任意文本成立(不受影响), 覆盖性靠页内 80ms
 * 心跳重放当前步注入兜住(被冲掉下一拍即恢复, 4ms 采样必捕捉)。步序调度全在页内
 * setTimeout, 外层零固定睡等(flaky 守卫第 2 类要拦的调用字面不在此注释复述 —— 它按行
 * 文本连注释一起计); 纯几何探针, 零 route 改写。
 */

/** 页内执行: 装探针(4ms 采样 + rAF 双路)并按步序注入变异; 返回后轮询 window.__sbGeo.done。
 *  注入经 withVm(e2e/lib/vm.mjs 取根实例唯一直径, D4 第 1 类 evaluate), vm 由其绑定。 */
async function runSpeedSequence(page) {
  await withVm(page, `
    const K = 1024;
    const P = (window.__sbGeo = { s: [], done: false });
    const sb = document.querySelector('.statusbar');
    const setSpeed = (v) => {
      vm.status = Object.assign({}, vm.status, { totals: { dlspeed: v, upspeed: v } });
    };
    const setLimits = (v) => {
      vm.statsServer = Object.assign({}, vm.statsServer, { dl_rate_limit: v, up_rate_limit: v });
    };
    /* 步序(毫秒): 基线稳定窗 -> 速度四档("0 B/s" / "1023.99 KiB/s" / "1.00 MiB/s" /
     * "9999.99 GiB/s") + 限速三态("不限" / "—" / "1023.99 KiB/s") + 徽标两位数 -> 收尾;
     * 每步 500ms 窗覆盖 flux numRoll 360ms 补间的中间帧。 */
    const steps = [
      [600, () => setSpeed(0)],
      [1100, () => setLimits(0)],
      [1600, () => setSpeed(1023.99 * K)],
      [2100, () => setLimits(null)],
      [2600, () => setSpeed(K * K)],
      [3100, () => setSpeed(9999.99 * K * K * K)],
      [3600, () => setLimits(1023.99 * K)],
      [4100, () => { vm._errUnread = 42; }],
      [5100, () => { P.done = true; }],
    ];
    let last = null;
    /* 心跳重放当前步注入: 真实轮询把桩值写回后, 下一拍即恢复 —— 几何不变量不受影响,
     * 覆盖性不丢(每形至少存活 80ms 减轮询竞窗, 4ms 采样必捕捉)。 */
    const beat = setInterval(() => { if (last) last(); }, 80);
    for (const [t, fn] of steps) setTimeout(() => { last = fn; fn(); }, t);
    setTimeout(() => clearInterval(beat), 5200);
    const rec = () => {
      const rect = (sel) => {
        const e = sb.querySelector(sel);
        if (!e) return null;
        const r = e.getBoundingClientRect();
        return { l: r.left, r: r.right, h: r.height };
      };
      const txt = (sel) => { const e = sb.querySelector(sel); return e ? e.textContent : null; };
      P.s.push({
        spd: rect('.sb-speed'), sep: rect('.sb-sep'), err: rect('.sb-err'),
        vd: rect('.spd-down .val'), ld: rect('.spd-down .lim'),
        vu: rect('.spd-up .val'), lu: rect('.spd-up .lim'),
        tvd: txt('.spd-down .val'), tld: txt('.spd-down .lim'), tb: txt('.sb-err-badge'),
        sw: sb.scrollWidth, cw: sb.clientWidth,
      });
    };
    const iv = setInterval(rec, 4);
    const raf = () => { rec(); if (!P.done) requestAnimationFrame(raf); };
    raf();
    P.stop = () => clearInterval(iv);
  `);
  await expect.poll(() => page.evaluate(() => window.__sbGeo && window.__sbGeo.done), {
    message: '页内变异序列跑完(步序 ~5.2s)',
    timeout: 20_000,
  }).toBe(true);
}

/** 汇总采样帧: 各元素左右缘相对基线帧的最大偏移 + 文本形并集 + 裁切面。 */
async function collectDeviation(page) {
  return page.evaluate(() => {
    const P = window.__sbGeo;
    P.stop();
    const s = P.s;
    const b = s[0];
    const mx = (key) => {
      if (!b[key]) return null;
      let l = 0, r = 0;
      for (const x of s) {
        if (!x[key]) continue;
        l = Math.max(l, Math.abs(x[key].l - b[key].l));
        r = Math.max(r, Math.abs(x[key].r - b[key].r));
      }
      return { l, r };
    };
    const texts = (key) => [...new Set(s.map((x) => x[key]).filter(Boolean))];
    /* .sb-err 左缘漂移只取向右的方向量(徽标变宽只许向左挤 spacer, D14) */
    const errLeftRight = Math.max(0, ...s.filter((x) => x.err && b.err).map((x) => x.err.l - b.err.l));
    return {
      n: s.length,
      spd: mx('spd'), sep: mx('sep'), vd: mx('vd'), ld: mx('ld'), vu: mx('vu'), lu: mx('lu'),
      errR: mx('err') ? mx('err').r : null,
      errLeftRight,
      baseH: b.spd ? b.spd.h : null,
      clip: s.some((x) => x.sw > x.cw),
      vals: texts('tvd'), lims: texts('tld'), badge42: s.some((x) => x.tb === '42'),
    };
  });
}

for (const skin of SKINS_ALL) {
  test.describe(`状态栏速度组逐帧几何 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`速度四档/限速三态/徽标 全程定宽恒定 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openApp(page, skin);
      await expect(page.locator('.statusbar .sb-speed')).toBeVisible();

      // ---- 宽视口(1440 桌面默认): 全程逐帧零位移(容差 1px, 含 flux 补间中间帧) ----
      await runSpeedSequence(page);
      const d = await collectDeviation(page);
      expect(d.n, '采样帧数(4ms x rAF 双路, ~5.2s 窗)').toBeGreaterThan(400);
      for (const [key, label] of [
        ['spd', '.sb-speed'], ['sep', '.sb-sep'],
        ['vd', '下载 .val'], ['ld', '下载 .lim'], ['vu', '上传 .val'], ['lu', '上传 .lim'],
      ]) {
        expect(d[key].l, `${label} 左缘全程偏移 <=1px(定宽槽冻结整组左缘)`).toBeLessThanOrEqual(1);
        expect(d[key].r, `${label} 右缘全程偏移 <=1px`).toBeLessThanOrEqual(1);
      }
      expect(d.errR, '.sb-err 右缘不动(被速度组左缘钉住, D14)').toBeLessThanOrEqual(1);
      expect(d.errLeftRight, '.sb-err 左缘不许右移(徽标变宽只能向左挤 spacer)').toBeLessThanOrEqual(1);
      expect(d.baseH, '34px 锁高不随速度/限速/徽标变化').toBeGreaterThanOrEqual(33);
      expect(d.baseH, '34px 锁高不随速度/限速/徽标变化').toBeLessThanOrEqual(35);
      expect(d.clip, '状态栏无横向裁切(overflow:hidden 下 scrollWidth>clientWidth = 有内容被裁)').toBe(false);
      // 覆盖性自证: 变异形必须真实出现在采样帧里(防轮询冲掉注入后空转变绿)
      for (const shape of ['0 B/s', '1023.99 KiB/s', '1.00 MiB/s', '9999.99 GiB/s']) {
        expect(d.vals, `速度形「${shape}」必须真实出现过(覆盖性自证)`).toContain(shape);
      }
      for (const shape of ['不限', '—', '1023.99 KiB/s']) {
        expect(d.lims, `限速形「${shape}」必须真实出现过(覆盖性自证)`).toContain(shape);
      }
      expect(d.badge42, '未读徽标 42(两位数)必须真实出现过').toBe(true);

      // ---- 窄视口(800, 覆盖 @media max-width: 900px): 契约只保 .sb-speed 右缘不动 ----
      await page.setViewportSize({ width: 800, height: 900 });
      await expect.poll(
        () => page.evaluate(() => {
          const el = document.querySelector('.statusbar');
          return el ? el.getBoundingClientRect().width : 0;
        }),
        { message: '视口缩窄后状态栏按 800px 重排', timeout: 5_000 },
      ).toBeGreaterThan(790);
      await runSpeedSequence(page);
      const dn = await collectDeviation(page);
      expect(dn.n, '窄屏采样帧数').toBeGreaterThan(400);
      expect(dn.spd.r, '窄屏 .sb-speed 右缘不动(容器右内边距钉死, R1 契约)').toBeLessThanOrEqual(1);
      expect(dn.baseH, '窄屏 34px 锁高不变').toBeGreaterThanOrEqual(33);
      expect(dn.baseH, '窄屏 34px 锁高不变').toBeLessThanOrEqual(35);
      expect(dn.clip, '窄屏无新增横向裁切').toBe(false);
      // 窄屏不承诺组内零位移(.lim 只设 4ch 下限, 长限速值撑开会把组内元素一起左推 —— R2)
    });
  });
}
