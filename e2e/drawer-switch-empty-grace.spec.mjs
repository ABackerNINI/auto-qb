// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 抽屉三列表(peers/trackers/files)软切换空态守卫(2026-10-13 用户报障「种子详情用户页切换种子时
 * 『暂无已连接用户』闪烁」+ 用户要求 trackers/files 同族一并修)。
 *
 * 病根(见 drawer-switch-flicker.md 第九次形态): 软切换(FX-29)本意「保留旧数据撑几何 + 遮罩防串显」,
 * 但换目标后 qB 对新种子的**首个**列表响应常为瞬时**空**(连接/状态未就绪), 空响应直接落袋会覆盖
 * 旧数据渲染成一帧空态, 下一拍(5s)真实数据到达再顶回表格 = 用户所报「闪一下」。修法 =
 * 换目标窗口内**首个空响应视为「未就绪」**(不落袋/不掀罩/1s 后快速重拉一次, 仍空才接受),
 * 三列表共用单点 `drawer_store.js::_drawerGraceHold`。
 *
 * 为什么另立本 spec(不并入各页签的既有 spec): 该缺陷是**跨三列表的同一条数据落袋语义**问题 ——
 * 桩服务对每个种子**恒有**数据(peers 1~7 对端 / trackers 多条 / files 两文件), 既有全部用例又都是
 * `dblclick nth=0` **单次打开**(无"切换种子"用例) ⇒ 「切换 + 首拍空」这条真机路径此前在 e2e 里
 * 零覆盖。本 spec 用 route 让**切换目标**的首个列表响应返空(其余走桩), 逐帧 rAF 采样空态文案,
 * 三页签各钉一条; 静态接线由 test_webui_static_dom_panel.py::test_drawer_list_switch_empty_grace_wiring 钉住。
 */

/** 三页签: 标签 / 端点段 / 经典空态文案 / 经典行锚(data-table)。 */
const TABS = [
  { tab: 'peers', label: '用户', api: 'peers', empty: '暂无已连接用户', rowTable: 'drawerPeer' },
  { tab: 'trackers', label: 'Tracker', api: 'trackers', empty: '暂无 tracker', rowTable: 'drawerTracker' },
  { tab: 'content', label: '内容', api: 'files', empty: '无文件列表', rowTable: 'drawerFile' },
];

for (const skin of SKINS) {
  test.describe(`抽屉三列表切换种子空态守卫 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    for (const t of TABS) {
      test(`${t.label}: 切换种子首个空 ${t.api} 响应不得闪现空态 @fast (${skin})`, async ({ page }) => {
        collectRuntimeErrors(page);
        // 切换目标的**首个**列表响应返回空(模拟真机换种子后 qB 状态未就绪); 其余(初开/重拉/轮询)走桩。
        const seen = /** @type {Record<string, number>} */ ({});
        await page.route(`**/api/torrents/*/${t.api}**`, (route) => {
          const m = route.request().url().match(new RegExp(`torrents/([0-9a-fA-F]+)/${t.api}`));
          const h = m ? m[1] : '';
          seen[h] = (seen[h] || 0) + 1;
          const isSwitchTarget = Object.keys(seen).length > 1;
          if (isSwitchTarget && seen[h] === 1) {
            // peers 是 qB sync 整包(dict), trackers/files 是数组 —— 与真机同形
            const body = t.api === 'peers'
              ? { rid: 0, full_update: true, peers: {}, peers_removed: {} }
              : [];
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
          }
          return route.continue();
        });

        await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
        await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
        await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
        await page.click('nav.tabs [data-view="torrents"]');
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

        await page.dblclick('.torrent-row >> nth=0', { force: true });
        const drawer = page.locator('.drawer-dock > .drawer');
        await expect(drawer).toBeVisible({ timeout: 5_000 });
        await drawer.locator('.drawer-tabs button', { hasText: t.label }).click();
        await expect(drawer.locator(`.group-row[data-table="${t.rowTable}"]`).first())
          .toBeVisible({ timeout: 5_000 });

        // 逐帧(rAF)采样: 换目标全程抽屉内不得出现本页签的空态文案(经典 .empty 与变体 .dt0X-empty 同文本)
        await page.evaluate((txt) => {
          const el = document.querySelector('.drawer-dock > .drawer');
          /** @type {any} */ (window).__emptyFrames = 0;
          let stop = false;
          /** @type {any} */ (window).__stopSample = () => { stop = true; };
          const tick = () => {
            if (stop) return;
            if (el && (el.textContent || '').indexOf(txt) >= 0)
              /** @type {any} */ (window).__emptyFrames++;
            requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        }, t.empty);

        await page.dblclick('.torrent-row >> nth=1', { force: true });   // 软切换换目标
        await page.waitForTimeout(2500);                                  // 覆盖首拍空(0ms) + 宽限重拉(1s)
        const emptyFrames = await page.evaluate(() => {
          /** @type {any} */ (window).__stopSample();
          return /** @type {any} */ (window).__emptyFrames;
        });
        expect(emptyFrames, `换种子期间不得出现「${t.empty}」空态`).toBe(0);

        // 宽限重拉拿到真实数据 ⇒ 列表就位(不得永久停在加载态)
        await expect(drawer.locator(`.group-row[data-table="${t.rowTable}"]`).first())
          .toBeVisible({ timeout: 10_000 });
      });
    }
  });
}
