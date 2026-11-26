// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS_ALL } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { INST } from './lib/vm.mjs';

/**
 * 双排 A→B 行高恒等守阵(2026-11-19 行高恒等修正) ——
 *
 * 最初设计判据: **双排路径不得使行高变化**(整组迁移武装该行变高、终态回落再缩回的"行高跳变"
 * 即用户报的现象)。v2 落地时 pair 块(2×14.3px@11px/1.3 + 2px gap = 30.59px)超出主表行内容盒
 * (14px/21.7px 行盒 → 基线 42.69px)8.9px, 双排行 51.59 vs 单排 42.69; 修法 = has-relpair
 * 单元格 `margin: -5px 0` 吃进上下 padding(margin-box 20.59px ≤ 内容盒), 行高与单排逐像素相等。
 *
 * 钉法 = **同一行 A/B 两腿逐行差分**: B 腿经 vm 注入把当前可见行全部造成 pair(组级 moving 同
 * src/dst → pair; 成员级 src/dst 双非空 → pair), A 腿清注入回单排, 按 data-key/data-hash 对齐
 * 断言两腿行高逐行相等。不走路由改写翻腿 —— 增量轮询在版本未变时**不回传行**(polling.js 响应体
 * 趋零), app 永远吃不到"去掉标注的全量行", 翻腿恒空转(实测 15s 不清零); vm 注入则存活于
 * delta 轮询之间(实测跨 3+ 周期不冲), 且属 lib/vm.mjs D4 守则允许的「注入/复原桩态」类。
 * B 腿守"注入数 == 可见行数"(防轮询冲掉部分注入的假绿)。
 *
 * 组行与种子行(torrent 分支)同一条 CSS 规则(.g-save-path.has-relpair), 两页分别钉 ——
 * 行内容盒构成不同(组行 21.69px / 种子行 22.05px 驱动), 负 margin 方案对两者都须成立。
 * 四皮肤 SKINS_ALL(几何一致性只读测量口径)。静态面钉在
 * test_webui_relocate_visibility.py::test_p1_pair_cell_margin_keeps_row_height_constant。
 */

const TOL = 0.5; // 行高对比容差(px, 亚像素取整)

/** 组级 pair job(state=moving 同 src/dst → relocateView mode='pair')。 */
const GROUP_JOB = {
  state: 'moving', phase: 'moving', pending: 1, total: 1, job_ids: ['job-pair-height'], mover: false,
  src: 'R:\\Downloads\\Set000', dst: ['R:\\Downloads\\Relocated'],
  alias_kind: '', alias_count: 0, created_at: 1, armed_at: 1, updated_at: 1, origin: 'web', reason: '',
  resume_pending_count: 0, resume_pending_hashes: [], resume_retries: 0, resume_exhausted: false,
};
/** 成员级 pair job(种子行: src/dst 双非空 → pair; dst 是字符串)。 */
const MEMBER_JOB = {
  state: 'moving', phase: 'moving', job_id: 'job-pair-height', mover: false,
  src: 'R:\\Downloads\\Set000', dst: 'R:\\Downloads\\Relocated',
  alias_kind: '', alias_count: 0, created_at: 1, armed_at: 1, updated_at: 1, origin: 'web', reason: '',
  resume_pending_count: 0, resume_pending_hashes: [], resume_retries: 0, resume_exhausted: false,
};

for (const skin of SKINS_ALL) {
  test.describe(`双排 A→B 行高恒等 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`同行 pair 态 vs 单排态 逐行相等(组行+种子行) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize({ width: 1600, height: 900 });

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.rl-scope .group-row').first()).toBeVisible({ timeout: 30_000 });
      // 量齐就位(首访量轮 settle, relocate-key-change-pad 同款 poll): 行高实测态就位后
      // 行窗口化切片稳定 —— 此前是全量渲染, 行集在量轮前后会变, 两腿行集对齐会假红。
      await expect.poll(
        () => page.evaluate(`(async () => { const vm = ${INST}; return vm._winMeasured.group; })()`),
        { timeout: 30_000, message: '首访量齐全量轮 settle(行高实测态就位, 行集稳定)' },
      ).toBe(true);

      /**
       * 行高表: 可见行逐行 {key: {h, pair}}。kind='group' 量组行(data-key), 'torrent' 量种子行
       * (data-hash, data-table="torrent")。
       */
      const heightMap = (kind) => page.evaluate(([kindArg]) => {
        const px = (v) => Math.round(v * 100) / 100;
        const sel = kindArg === 'torrent' ? '.rl-scope .group-row[data-table="torrent"]' : '.rl-scope .group-row';
        const out = {};
        for (const row of document.querySelectorAll(sel)) {
          const key = row.getAttribute(kindArg === 'torrent' ? 'data-hash' : 'data-key');
          if (!key) continue;
          const h = row.getBoundingClientRect().height;
          if (h > 0) out[key] = { h: px(h), pair: !!row.querySelector('.rel-pair') };
        }
        return out;
      }, [kind]);

      /**
       * vm 注入/清桩: 对**当前可见行**的行对象批量写 relocate(kind='torrent' 按hash写 vm.torrents,
       * 否则按 key 写 vm.groups)。返回注入行数 —— 必须等于可见行数, 少一个就是轮询冲掉了注入。
       */
      const setRelocate = (kind, jobOrNull) => page.evaluate(([kindArg, job]) => {
        const vm = document.querySelector('#app')._vnode.component.proxy;
        const sel = kindArg === 'torrent' ? '.rl-scope .group-row[data-table="torrent"]' : '.rl-scope .group-row';
        const keys = new Set(
          [...document.querySelectorAll(sel)]
            .map((r) => r.getAttribute(kindArg === 'torrent' ? 'data-hash' : 'data-key'))
            .filter(Boolean),
        );
        let n = 0;
        const rows = kindArg === 'torrent' ? vm.torrents || [] : vm.groups || [];
        const idOf = (r) => (kindArg === 'torrent' ? r.hash : r.key);
        for (const r of rows) if (keys.has(idOf(r))) { r.relocate = job ? { ...job } : null; n += 1; }
        return n;
      }, [kind, jobOrNull]);

      const pairCount = (kind) => page.evaluate(([kindArg]) => {
        const sel = kindArg === 'torrent'
          ? '.rl-scope .group-row[data-table="torrent"] .rel-pair'
          : '.rl-scope .group-row .rel-pair';
        return document.querySelectorAll(sel).length;
      }, [kind]);

      /** 一面(页内一类行)的完整 A/B 对比。 */
      const assertPairHeightConstant = async (kind, label) => {
        // A 腿: harness 原始态。桩自灌的 5 个 job 让组页本就有 2 个真 pair 组({t0 moving,t1 armed}
        // 与 {t2 failed,t3 done} —— 组级聚合 group_relocate 按 _PRIORITY 取最高态且单 job_id 不出
        // mixed)—— 不做"零 pair"强前提, 改按行状态分类: 只对「A 单排 → B 双排」的行判行高恒等,
        // A 即 pair 的行显式排除(排除数上报, 不静默)。
        const a = await heightMap(kind);
        const keysA = Object.keys(a).sort();
        expect(keysA.length, `${label}: A 腿可见行数 > 0`).toBeGreaterThan(0);

        // B 腿: 全量注入 pair, 守注入覆盖 + pair 真渲染
        const injected = await setRelocate(kind, kind === 'torrent' ? MEMBER_JOB : GROUP_JOB);
        expect(injected, `${label}: vm 注入数应 == 可见行数(少即轮询冲掉注入, B 腿假绿)`).toBe(keysA.length);
        await expect.poll(() => pairCount(kind), { timeout: 10_000, message: `${label}: 注入后 pair 行应全量渲染` })
          .toBe(keysA.length);
        const b = await heightMap(kind);

        // 复原(不留注入态给后续轮询/其它断言面)
        await setRelocate(kind, null);
        await expect.poll(() => pairCount(kind), { timeout: 10_000, message: `${label}: 清注入后 pair 应清零` }).toBe(0);

        // 逐行相等断言: 两腿键集必须一致(行变高的回归态会让窗口切片移位 —— 键集不等按漂移归因报红, 不抛 TypeError)
        const keysB = Object.keys(b).sort();
        expect(keysB, `${label}: B 腿可见行集应与 A 腿完全一致(不一致 = 行集在两腿间漂移)`).toEqual(keysA);
        // 判定集 = 本守阵要守的迁移路径: A 单排 → B 双排(整组迁移武装该行)。A 即 pair 的行
        // (harness 自灌)不进判定, 排除面如实留痕; 判定集为空 = 守阵零判别, 直接红。
        const judged = keysA.filter((k) => !a[k].pair);
        const excluded = keysA.length - judged.length;
        expect(judged.length, `${label}: 「A 单排→B 双排」判定行数 > 0(A 即 pair 排除 ${excluded} 行; 全排除 = 零判别)`).toBeGreaterThan(0);
        const drifted = judged
          .filter((k) => Math.abs(b[k].h - a[k].h) > TOL)
          .map((k) => ({ key: k.slice(0, 14), pair: b[k].h, plain: a[k].h }));
        expect(drifted, `${label}: 双排行高必须与单排逐行相等(±${TOL}px): ${JSON.stringify(drifted.slice(0, 5))}`).toEqual([]);
      };

      await assertPairHeightConstant('group', `组行(${skin})`);

      // 种子页同阵: torrent 分支, 同一条 CSS 规则另一行模型(切页会翻 _winMeasured, 等量齐再量;
      // 切页走真实手势 —— D4 守则: 凡有真实 UI 路径的交互一律 locator 手势, relocate-pair-filter 同款)
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.rl-scope .group-row[data-table="torrent"]').first()).toBeVisible({ timeout: 15_000 });
      await expect.poll(
        () => page.evaluate(`(async () => { const vm = ${INST}; return vm._winMeasured.torrent; })()`),
        { timeout: 30_000, message: '种子页量齐全量轮 settle(行集稳定)' },
      ).toBe(true);
      await assertPairHeightConstant('torrent', `种子行(${skin})`);
    });
  });
}
