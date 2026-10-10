// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * dt07「四卡仪表」/ dt08「五区分组」peers 列表 列头×行 列对齐守阵(2026-10-10 用户报障回归) ——
 *
 * 症状: qB 不回 peers.files 渐进字段时(真机常态), 「进度」列起后续所有列头与行内容错位。
 * 根因: 表头在无 files 时已切 9 列网格(.dt07-head.nofiles / .dt08-gcols.nofiles), 而行
 * rowHtml 从未补 nofiles 类 —— 行仍走 10 列模板却只渲染 9 格, 两个网格里 1fr 列(「正在取」)
 * 各算各的宽(头部 1fr 多吞末列 44/46px + 1 个 gap 的份额), 其后所有列整体错开 50+px。
 * 修复 = 行 cls 与表头同进退补 nofiles。
 *
 * 断言口径: page.route 桩掉 /api/torrents/{hash}/peers(与 drawer-peers-sticky-flush.spec
 * 同款手法) —— 无 files 版钉 9 列对齐(报障路径), 含 files 版钉 10 列对齐(渐进字段在位时不回归);
 * 逐列量 列头格 与 每一行同名次格 的视口左缘(±1px), 格数不齐即红(错位的结构签名)。
 * dt08 按组量(每组自带 .dt08-gcols 列头), 折叠组跳过(display:none 格 rect 恒 0 不可量)。
 * 手法同族: drawer-peers-sticky-flush.spec(桩 peers + addInitScript 预选模板 + 双击开抽屉)。
 */

/** 合成 peer 列表。withFiles=false 覆盖报障路径(qB 不回 files); true 覆盖 10 列路径。
 *  速度键是 qB 原始的 dl_speed / up_speed(前端 _drawerNormPeers 落袋适配, 同族 spec 口径)。 */
function makePeers(withFiles) {
  const flagsPool = ['U D', 'D E', 'u', 'U D K', 'D']; // take/feed/choke 三桶可见, idle(K) 默认折叠
  const out = [];
  for (let i = 0; i < 12; i++) {
    const p = {
      ip: `${10 + (i % 200)}.${(i * 7) % 256}.${(i * 13) % 256}.${(i * 29) % 256}`,
      port: 30000 + i,
      client: `qBittorrent 5.${i % 5}.${i % 3}`,
      flags: flagsPool[i % flagsPool.length],
      progress: (i % 10) / 10,
      dl_speed: (i % 4) * 125000,
      up_speed: (i % 3) * 250000,
      relevance: 0.5 + (i % 50) / 100,
      country_code: ['CN', 'US', 'DE'][i % 3],
      connection: ['UV', 'UT', 'IU'][i % 3],
    };
    if (withFiles) p.files = `Some.Show.S01E${String(1 + (i % 9)).padStart(2, '0')}.mkv`;
    out.push(p);
  }
  return out;
}

const VARIANTS = [
  { id: '07', label: '四卡仪表', wrap: '.dt07-wrap' },
  { id: '08', label: '五区分组', wrap: '.dt08-wrap' },
];

/** 列对齐探针(页面内量测): 逐列比较 列头格 与 每行同名次格 的视口左缘(±1px)。
 *  dt07 = 单列头(.dt07-head); dt08 = 每个未折叠组各带列头(.dt08-gcols), 折叠组跳过 ——
 *  折叠组 rows 是 display:none, 格 rect 恒 0, 量了必假红。 */
function probeFn(id) {
  return `(() => {
    const cellLefts = (el) => [...el.children].map((c) => Math.round(c.getBoundingClientRect().left * 10) / 10);
    const cmp = (head, rows, tag) => {
      const hc = cellLefts(head);
      for (const r of rows) {
        const rc = cellLefts(r);
        if (rc.length !== hc.length) return { fail: 'count', tag, head: hc.length, row: rc.length };
        for (let i = 0; i < hc.length; i++) {
          if (Math.abs(rc[i] - hc[i]) > 1) return { fail: 'x', tag, col: i, head: hc[i], row: rc[i] };
        }
      }
      return { ok: true, cols: hc.length, rows: rows.length };
    };
    if ('${id}' === '07') {
      const head = document.querySelector('.drawer .dt07-head');
      if (!head) return { fail: 'no-head' };
      return cmp(head, [...document.querySelectorAll('.drawer .dt07-list > .dt07-r')], 'dt07');
    }
    const groups = [...document.querySelectorAll('.drawer .dt08-grp:not(.folded)')];
    if (!groups.length) return { fail: 'no-group' };
    for (const g of groups) {
      const head = g.querySelector(':scope .dt08-gcols');
      const rows = [...g.querySelectorAll(':scope .dt08-rows > .dt08-r')];
      if (!head) return { fail: 'no-gcols', tag: g.getAttribute('data-grp') };
      const out = cmp(head, rows, g.getAttribute('data-grp'));
      if (!out.ok) return out;
    }
    return { ok: true, groups: groups.length, cols: groups[0].querySelector('.dt08-gcols').children.length };
  })()`;
}

for (const skin of SKINS) {
  test.describe(`详情抽屉 dt07/08 peers 列对齐 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    /* 报障路径: qB 不回 files —— 表头 9 列(nofiles), 行修复前仍走 10 列网格 ⇒ 「进度」起错位 */
    for (const v of VARIANTS) {
      test(`dt${v.id} ${v.label} 无 files(9 列): 列头与每行列左缘对齐 @fast (${skin})`, async ({ page }) => {
        collectRuntimeErrors(page);

        await page.route('**/api/torrents/*/peers', (route) =>
          route.fulfill({ contentType: 'application/json', body: JSON.stringify({ peers: makePeers(false) }) }));
        // 预选变体(addInitScript 必须赶在 app.js 读 localStorage 之前, 同 sticky-flush spec)
        await page.addInitScript(
          (id) => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ peers: id })),
          v.id,
        );

        await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
        await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
        await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

        // 种子视图平铺行双击开详情抽屉(整表 2s 重渲染抢点击 ⇒ force, 同族 spec 口径)
        await page.click('nav.tabs [data-view="torrents"]');
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        await page.dblclick('.torrent-row >> nth=0', { force: true });
        const drawer = page.locator('.drawer-dock > .drawer');
        await expect(drawer).toBeVisible({ timeout: 5_000 });
        await drawer.locator('.drawer-tabs button', { hasText: '用户' }).click();

        await expect(drawer.locator(v.wrap)).toBeVisible({ timeout: 5_000 });
        const res = /** @type {any} */ (await page.evaluate(probeFn(v.id)));

        expect(res.fail, `列对齐探针: ${JSON.stringify(res)}`).toBeUndefined();
        expect(res.cols, `无 files 时应为 9 列(nofiles 网格), 实际 ${res.cols}`).toBe(9);
      });
    }

    /* 渐进字段在位路径: peers 带 files —— 表头/行都是 10 列, 防修复把 10 列路径改坏 */
    test(`dt07 四卡仪表 有 files(10 列): 列头与每行列左缘对齐 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.route('**/api/torrents/*/peers', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify({ peers: makePeers(true) }) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ peers: '07' })));

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await page.dblclick('.torrent-row >> nth=0', { force: true });
      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 5_000 });
      await drawer.locator('.drawer-tabs button', { hasText: '用户' }).click();

      await expect(drawer.locator('.dt07-wrap')).toBeVisible({ timeout: 5_000 });
      // 「正在取」列头在位 = hasFiles 路径真的走到了(桩数据被前端消费, 不止是 route 生效)
      await expect(drawer.locator('.dt07-head', { hasText: '正在取' })).toBeVisible({ timeout: 5_000 });

      const res = /** @type {any} */ (await page.evaluate(probeFn('07')));
      expect(res.fail, `列对齐探针: ${JSON.stringify(res)}`).toBeUndefined();
      expect(res.cols, `有 files 时应为 10 列, 实际 ${res.cols}`).toBe(10);
    });
  });
}
