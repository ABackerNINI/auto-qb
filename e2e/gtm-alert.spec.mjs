// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst } from './lib/vm.mjs';

/**
 * GTM 当日总量虚高告警的**常驻横幅**(计划 26-11-03-1102 S7c / 验收 T32)。
 *
 * 数据面桩法: 不伪造整份 /api/state, 而是 `route.fetch()` 取真实桩响应后**只改写**
 * `status.traffic.gtm_anomaly` 一个可选键 —— 其余字段(行数据/统计/限速)保持生产形状,
 * 断言只落在横幅本身, 不受桩数据差异干扰。
 *
 * T32 三条判据(逐条对应计划 §11 测试矩阵):
 *   ① T1 注入 -> 横幅常驻可见(短版含 nic/dir/人类可读速率);
 *   ② 点 ×(本机 ack)-> 立即隐藏, localStorage["gtm.spike.ack"] = T1;
 *   ③ 刷新页面 -> 仍隐藏(T1 已被 ack); 换成 T2 -> 自动重显(短版多方向追加 +N);
 *   ④ 降级面: items 为空 -> 整段不渲染, 且速度组/通知入口等既有状态栏元素不受影响。
 *
 * 皮肤口径: 与既有冒烟轨一致, SKINS = prism|atlas(模板与 CSS 都是 shared 单点,
 * 双皮肤覆盖即验"三皮肤/四皮肤共享同一来源"的运行时表现)。
 */
const T1 = '2026-11-03T10:47:28+08:00';
const T2 = '2026-11-03T11:02:15+08:00';
const T3 = '2026-11-03T11:10:00+08:00';

/** 与用户提供的真实 gtm_anomaly 形状逐字一致(字段名/量纲不改)。 */
const ITEM_UP = { nic: '以太网', dir: 'up', cur: 1115700, last: 800, delta: 273400, rate_bps: 58720255996 };
const ITEM_DOWN = { nic: 'Wi-Fi', dir: 'down', cur: 980000, last: 500, delta: 120000, rate_bps: 104857600 };

const spike = (ts, items) => ({
  ts,
  dt_s: 5.0,
  eff_dt_s: 5.0,
  threshold_bps: 1073741824,
  items,
});

/**
 * 只改 traffic.gtm_anomaly 的 /api/state 拦截器。
 * @param {import('@playwright/test').Page} page
 * @param {() => object} current 返回本拍要注入的告警段(可为 null / 缺字段对象, 走降级)
 */
async function injectAnomaly(page, current) {
  await page.route('**/api/state*', async (route) => {
    const resp = await route.fetch();
    let body = null;
    try {
      body = await resp.json();
    } catch (e) {
      body = null;
    }
    if (!body || !body.status) {
      await route.fulfill({ response: resp });
      return;
    }
    body.status.traffic = body.status.traffic || {};
    body.status.traffic.gtm_anomaly = current();
    await route.fulfill({ response: resp, json: body });
  });
}

/** 等页面真的采纳了某个 ts(轮询是异步的, 直接断言 DOM 会赌时长)。 */
const seenTs = (page) => expect.poll(
  () => readInst(page, 'vm.traffic && vm.traffic.gtm_anomaly ? vm.traffic.gtm_anomaly.ts : null'),
  { message: '服务端告警段已随轮询落到 vm.traffic' },
);

for (const skin of SKINS) {
  test.describe(`皮肤 ${skin}(GTM 告警横幅)`, () => {
    installRuntimeErrorGuard(test);

    test(`GTM 告警: 常驻可见 / ack 隐藏 / 刷新保持 / 新 ts 重显 / 空 items 降级 @fast (${skin})`, async ({ page }) => {
      test.setTimeout(120_000);   // 两次整页加载 + 多轮轮询等待, 放宽默认 30s
      let anomaly = spike(T1, [ITEM_UP]);
      await injectAnomaly(page, () => anomaly);

      const banner = page.locator('.sb-gtm-alert');
      const shortText = banner.locator('.sb-gtm-main .val');

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      /* ① 常驻可见: 不依赖 todayTraffic 的 v-if 分支(该桩默认有今日流量, 但判据是元素本身) */
      await expect(banner).toBeVisible({ timeout: 30_000 });
      await expect(shortText).toContainText('以太网 上行');
      await expect(shortText).toContainText('GiB/s');

      /* ② 点 × -> 本机消警(写 localStorage, 不写服务端) */
      await banner.locator('.sb-gtm-ack').click();
      await expect(banner).toHaveCount(0);
      expect(await page.evaluate(() => localStorage.getItem('gtm.spike.ack')), 'ack 键值必须是当前 ts')
        .toBe(T1);

      /* ③ 刷新后仍隐藏:T1 已在 ack 里, 先确认新载荷真的到了再断言(不赌"页面还没加载完") */
      await page.reload({ waitUntil: 'domcontentloaded' });
      await seenTs(page).toBe(T1);
      await expect(banner).toHaveCount(0);

      /* 新异常 ts 不同 -> 自动重显; 多方向 -> 短版追加 +1 */
      anomaly = spike(T2, [ITEM_UP, ITEM_DOWN]);
      await seenTs(page).toBe(T2);
      await expect(banner).toBeVisible();
      await expect(shortText).toContainText('+1');

      /* ④ 降级: items 为空 = 无异常 -> 整段不渲染; 其它状态栏元素照常 */
      anomaly = spike(T3, []);
      await seenTs(page).toBe(T3);
      await expect(banner).toHaveCount(0);
      await expect(page.locator('.sb-speed')).toBeVisible();
      await expect(page.locator('.sb-err')).toBeVisible();
    });
  });
}
