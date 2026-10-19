// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst } from './lib/vm.mjs';
import { tab, ctxItem, clickRow, openApp } from './lib/gestures.mjs';

/**
 * 站点问题改色表达与 chip 图标收口(计划 26-10-19-2206 S4) —— 真浏览器断言。
 *
 * 通道分工: 站点问题(缺配置 / tracker 报错)走**颜色**, 命令结果走**图标**且固定放站点名之后。
 * 静态守阵 `test_frontend_site_alert_icon_wiring` 只能钉"样式齐备 / 模板只有一个槽 / 映射单点";
 * 本 spec 钉**真浏览器算出来的东西**:
 *   1. 缺配置 chip 的 computed 底色 == --warn-soft 且底边 dashed(D4 非颜色通道),
 *      tracker 报错 == --error-soft, 两者不相等(R4 橙红可分);
 *   2. tooltip 挂整块 chip(data-aq-tip 为后端文案 / 报错原文), 站点问题零图标;
 *   3. 命令结果图标是 chip 的最后一个子元素(位置恒定) + 变色 chip 内图标继承前景色(R1);
 *   4. 搜索命中时站点问题底色仍胜出, 命中改 inset 描边(D6);
 *   5. 明细行站点文本同语义染色 + 同款 tooltip(D9)。
 *
 * 桩数据(scripts/ui_harness.py --site-alert on, 默认开):
 *   · 种子倒数第 4: tracker_conf=None + 真实 tracker URL -> site_alert=no_site_conf
 *   · 种子倒数第 3: tracker_health_msg 非空           -> site_alert=tracker_error
 *   两者同属最后一组 ⇒ 组行的两个 chip 上能**同时**看到两种告警。
 *
 * 命令结果: 命令泵对 reannounce 回执带 truth.results(与后端 check_pending 同形),
 * 其中 site_alert=tracker_error 的行判"拒绝" —— 于是"3 个目标、1 个被拒"可复现。
 */

const NO_CONF_TITLE = '站点未在配置中';
const TRACKER_MSG = '由本地系统中止网络连接。';
/* 命令结果图标寿命(计划 D7): 成功 10s / 失败 180s —— 用例只验 until 差值(真等 180s 没有意义) */
const OK_MS = 10_000;
const ERR_MS = 180_000;

/** 读皮肤令牌(各皮肤 :root / 棱镜主题选择器上的自定义属性, 在 documentElement 上求值) */
const token = (page, name) => page.evaluate(
  (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim(), name);

/** 颜色字符串 -> 分量数组; 支持 rgb()/rgba() 与 #rgb/#rrggbb(令牌可能是 hex, 计算值恒是 rgb)。 */
const parseRgb = (s) => {
  const str = String(s || '').trim();
  const m = str.match(/rgba?\(([^)]+)\)/);
  if (m) {
    const p = m[1].split(',').map((x) => parseFloat(x));
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  }
  const h = str.match(/^#([0-9a-f]{3,8})$/i);
  if (h) {
    let x = h[1];
    if (x.length === 3 || x.length === 4) x = x.split('').map((c) => c + c).join('');
    return {
      r: parseInt(x.slice(0, 2), 16),
      g: parseInt(x.slice(2, 4), 16),
      b: parseInt(x.slice(4, 6), 16),
      a: x.length >= 8 ? parseInt(x.slice(6, 8), 16) / 255 : 1,
    };
  }
  return null;
};

/** 两个颜色是否同值(容差 1/255 + 2% alpha: 计算值四舍五入差异不该让断言飘) */
const sameColor = (a, b) => !!a && !!b
  && Math.abs(a.r - b.r) <= 1 && Math.abs(a.g - b.g) <= 1 && Math.abs(a.b - b.b) <= 1
  && Math.abs(a.a - b.a) <= 0.02;

for (const skin of SKINS) {
  test.describe(`站点问题改色表达 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`站点问题走颜色: 缺配置橙底+虚线 / 报错红底, tooltip 挂整块 chip @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openApp(page, skin); // 默认分组视图: 组行 = 每成员一个 chip

      const noConf = page.locator('.site-chip.sa-no-conf');
      const tracker = page.locator('.site-chip.sa-tracker');
      await expect(noConf.first(), '缺站点配置的 chip 应染橙底').toBeVisible({ timeout: 30_000 });
      await expect(tracker.first(), 'tracker 报错的 chip 应染红底').toBeVisible({ timeout: 15_000 });

      // ① 底色 == 皮肤令牌(不是散写色值): 缺配置 --warn-soft / 报错 --error-soft
      const [warnSoft, errorSoft] = [
        parseRgb(await token(page, '--warn-soft')),
        parseRgb(await token(page, '--error-soft')),
      ];
      const bgNoConf = parseRgb(await noConf.first().evaluate((el) => getComputedStyle(el).backgroundColor));
      const bgTracker = parseRgb(await tracker.first().evaluate((el) => getComputedStyle(el).backgroundColor));
      expect(sameColor(bgNoConf, warnSoft), `缺配置 chip 底色应 == --warn-soft(实际 ${JSON.stringify(bgNoConf)})`).toBe(true);
      expect(sameColor(bgTracker, errorSoft), `报错 chip 底色应 == --error-soft(实际 ${JSON.stringify(bgTracker)})`).toBe(true);
      expect(sameColor(bgNoConf, bgTracker), 'R4: 橙底与红底必须可区分(同值即两态撞脸)').toBe(false);

      // ② D4 非颜色通道: 缺配置恒带虚线下边框(灰度/色盲下与实底红可区分), 报错不带
      expect(await noConf.first().evaluate((el) => getComputedStyle(el).borderBottomStyle),
        '缺配置 chip 必须带虚线下边框(D4 非颜色通道)').toBe('dashed');
      expect(await tracker.first().evaluate((el) => getComputedStyle(el).borderBottomStyle),
        '报错 chip 不该有虚线底边(那是缺配置的专属通道)').not.toBe('dashed');

      // ③ 站点问题零图标 + tooltip 挂整块 chip(不再是 11px 图标可触发)
      expect(await noConf.first().locator('svg').count(), '站点问题不再走图标(改走底色)').toBe(0);
      expect(await tracker.first().locator('svg').count(), '站点问题不再走图标(改走底色)').toBe(0);
      // title 在落 DOM 时被 ui_feedback.js 迁成 data-aq-tip(原生气泡退役), 断言后者
      await expect(noConf.first()).toHaveAttribute('data-aq-tip', NO_CONF_TITLE);
      await expect(tracker.first()).toHaveAttribute('data-aq-tip', TRACKER_MSG);
      // 读屏通道(D4): aria-label 带上站点名与原因
      await expect(noConf.first()).toHaveAttribute('aria-label', new RegExp(NO_CONF_TITLE));
      await expect(tracker.first()).toHaveAttribute('aria-label', new RegExp(TRACKER_MSG));

      // 同一组行里两种告警并存(同组两个 chip 各染各的色)
      const row = page.locator('.group-row[data-table="group"]').filter({ has: tracker.first() }).first();
      await expect(row.locator('.site-chip.sa-no-conf')).toHaveCount(1);
      await expect(row.locator('.site-chip.sa-tracker')).toHaveCount(1);

      // 种子页平铺行同一口径(三处站点 cell 都接了新类)
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await expect(page.locator('.torrent-row .site-chip.sa-no-conf').first()).toBeVisible({ timeout: 15_000 });
      await expect(page.locator('.torrent-row .site-chip.sa-tracker').first())
        .toHaveAttribute('data-aq-tip', TRACKER_MSG);
      expect(await page.locator('.site-chip .sa').count(), '旧图标槽 .sa 必须零残留').toBe(0);
    });

    test(`命令结果图标: 位置恒定在站点名之后 + 变色 chip 继承前景色 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openApp(page, skin);
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 桩把两态注在**末尾两个**种子上(added_on 最大 = 默认序最前), 行窗口化下必然被渲染。
      // 健康目标刻意排除带 site_alert 的行 —— 下面要验"正常 chip 仍保留语义色"。
      const picked = /** @type {string[]} */ (await readInst(page, `(() => {
        const rows = vm.visibleTorrents || [];
        const active = rows.filter((r) => r.kind === 'seeding' || r.kind === 'downloading');
        const bad = active.find((r) => r.site_alert === 'tracker_error');
        if (!bad) return [];
        const others = active.filter((r) => r.hash !== bad.hash && !r.site_alert).slice(0, 2);
        return [bad.hash, ...others.map((r) => r.hash)];
      })()`));
      expect(picked.length, '窗口内应能挑到 1 个报错目标 + 2 个健康活跃目标').toBe(3);
      const [badHash] = picked;

      for (const h of picked) {
        await clickRow(page, page.locator(`.torrent-row[data-hash="${h}"]`), { modifiers: ['Control'] });
      }
      expect(await readInst(page, 'vm.selMembers.length'), 'Ctrl+click 选中 3 行').toBe(3);

      // 右键选中行 -> 批量菜单 -> 强制重新汇报(真实手势)
      await clickRow(page, page.locator(`.torrent-row[data-hash="${badHash}"]`), { button: 'right' });
      await ctxItem(page, '强制重新汇报').click();

      // 逐目标结果落到行上: 失败 1 行(红叉) / 成功 2 行(绿勾)
      const errIcon = page.locator('.site-chip .sx.sx-error');
      const okIcon = page.locator('.site-chip .sx.sx-ok');
      await expect(errIcon, '失败行出现红叉').toHaveCount(1, { timeout: 30_000 });
      await expect(okIcon, '其余两行出现绿勾').toHaveCount(2, { timeout: 15_000 });
      await expect(page.locator(`.torrent-row[data-hash="${badHash}"] .site-chip .sx-error`)).toHaveCount(1);

      // 位置恒定(D1): 图标必须是 chip 的**最后一个**子元素(站点名之后), 且每 chip 最多一个
      const shape = await page.locator(`.torrent-row[data-hash="${badHash}"] .site-chip`).evaluate((el) => {
        const kids = [...el.children];
        return {
          last: kids.length ? kids[kids.length - 1].tagName.toLowerCase() : '',
          svgs: el.querySelectorAll('svg').length,
        };
      });
      expect(shape.last, '命令结果图标必须排在站点名之后(chip 最后一个子元素)').toBe('svg');
      expect(shape.svgs, '每 chip 最多一个图标(站点问题已改走颜色)').toBe(1);

      // R1: 变色 chip(报错红底)内图标继承前景色 —— 写死的语义色在红底上会糊掉
      const badColors = await page.locator(`.torrent-row[data-hash="${badHash}"] .site-chip`).evaluate((el) => ({
        chip: getComputedStyle(el).color,
        svg: getComputedStyle(/** @type {Element} */ (el.querySelector('svg'))).color,
      }));
      expect(badColors.svg, 'R1: 变色 chip 内的图标必须走 currentColor(与 chip 前景同色)').toBe(badColors.chip);

      // 反向: 健康 chip 的语义色不被 currentColor 吞掉(否则失败红叉会变成种子状态的绿字)
      const okHash = picked.find((h) => h !== badHash) || '';
      const okSvg = await page.locator(`.torrent-row[data-hash="${okHash}"] .site-chip .sx`).evaluate(
        (el) => getComputedStyle(el).color);
      expect(sameColor(parseRgb(okSvg), parseRgb(await token(page, '--green'))),
        `健康 chip 的成功图标应保持 --green(实际 ${okSvg})`).toBe(true);

      // 寿命按 D7: 成功 10s / 失败 180s(读 until 差值, 不真等 180s)
      const spans = await readInst(page, `(() => {
        const out = {};
        for (const [h, v] of Object.entries(vm.alertIcons)) out[h] = { kind: v.kind, ms: v.until - Date.now() };
        return out;
      })()`);
      expect(Object.keys(spans).sort()).toEqual([...picked].sort());
      expect(spans[badHash].kind, '被拒目标是 error').toBe('error');
      expect(spans[badHash].ms, `失败图标寿命应≈${ERR_MS}ms`).toBeGreaterThan(ERR_MS - 15_000);
      for (const h of picked) {
        if (h === badHash) continue;
        expect(spans[h].kind, '健康目标是 ok').toBe('ok');
        expect(spans[h].ms, `成功图标寿命应≈${OK_MS}ms`).toBeGreaterThan(0);
        expect(spans[h].ms).toBeLessThanOrEqual(OK_MS);
      }

      // 聚合 toast 文案与改动前逐字一致(成功/失败/未确认三桶 + 首条原因)
      const toasts = await readInst(page, 'vm.toasts.map((t) => t.text).join("\\n")');
      expect(toasts).toContain('强制重新汇报: 成功 2, 失败 1, 未确认 0');
      expect(toasts).toContain('失败: tracker 未接受汇报(not working)');
    });

    test(`搜索命中让出底色: 站点问题仍占填充, 命中改 inset 描边 (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openApp(page, skin);

      // 缺配置那颗种子的站点名(桩里是 tracker.unknown-site.net) —— 用它搜, 命中面收窄到该行
      const site = /** @type {string} */ (await readInst(page, `(() => {
        for (const g of (vm.groups || [])) {
          for (const m of (g.members || [])) if (m.site_alert === 'no_site_conf') return m.site || '';
        }
        return '';
      })()`));
      expect(site, '桩里应有 no_site_conf 成员(否则本用例无从命中)').not.toBe('');

      await page.locator('.topbar input[placeholder="搜索种子或文件名..."]').fill(site);
      const hit = page.locator('.site-chip.sa-no-conf.search-hit').first();
      await expect(hit, '搜索命中后缺配置 chip 应同时带 search-hit 与 sa-no-conf').toBeVisible({ timeout: 15_000 });

      const shot = await hit.evaluate((el) => {
        const s = getComputedStyle(el);
        return { bg: s.backgroundColor, shadow: s.boxShadow };
      });
      // D6: 底色仍由站点问题决定(命中不再用 accent 柔底占住填充)
      expect(sameColor(parseRgb(shot.bg), parseRgb(await token(page, '--warn-soft'))),
        `命中态下站点问题底色必须胜出(实际 ${shot.bg})`).toBe(true);
      expect(shot.shadow, '命中态应改用 inset 描边(两个信号都不丢)').toContain('inset');
    });

    test(`明细行同语义: .m-site 染文字色 + 同款 tooltip (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openApp(page, skin);

      // 展开含问题成员的组(用站点名把目标组搜出来, 再点名称格展开 —— 点 chip 会走筛选)
      const site = /** @type {string} */ (await readInst(page, `(() => {
        for (const g of (vm.groups || [])) {
          for (const m of (g.members || [])) if (m.site_alert === 'no_site_conf') return m.site || '';
        }
        return '';
      })()`));
      await page.locator('.topbar input[placeholder="搜索种子或文件名..."]').fill(site);
      const grp = page.locator('.group-row[data-table="group"]').filter({ has: page.locator('.site-chip.sa-no-conf') }).first();
      await expect(grp).toBeVisible({ timeout: 15_000 });
      await grp.locator('.g-name').click({ force: true });

      const noConf = page.locator('.member-row .m-site.sa-no-conf').first();
      const tracker = page.locator('.member-row .m-site.sa-tracker').first();
      await expect(noConf, '明细行站点文本应染缺配置色').toBeVisible({ timeout: 10_000 });
      await expect(noConf).toHaveAttribute('data-aq-tip', NO_CONF_TITLE);
      const col = await noConf.evaluate((el) => getComputedStyle(el).color);
      expect(sameColor(parseRgb(col), parseRgb(await token(page, '--warn'))),
        `明细行缺配置文本色应 == --warn(实际 ${col})`).toBe(true);

      // 报错成员同组(桩口径): 明细行同样染红 + 带报错原文
      await expect(tracker, '明细行站点文本应染报错色').toBeVisible({ timeout: 10_000 });
      await expect(tracker).toHaveAttribute('data-aq-tip', TRACKER_MSG);
      const colT = await tracker.evaluate((el) => getComputedStyle(el).color);
      expect(sameColor(parseRgb(colT), parseRgb(await token(page, '--error'))),
        `明细行报错文本色应 == --error(实际 ${colT})`).toBe(true);
    });
  });
}
