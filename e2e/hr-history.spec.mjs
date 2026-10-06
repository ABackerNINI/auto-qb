// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { requireMode } from './lib/mode.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * HR 拉取历史表③(S5 批, 计划 26-10-06-0708 §3.3/§04 S5; 源头计划 26-10-04-0312 S5) ——
 * 承接旧单页冒烟脚本(S7 退役, git 历史可查)的**块G**。行号为取证时点值(计划 §2.2), 已按 grep 锚点复核
 * (2026-10-06, 删块前; S1–S4 已删块A/F/C/E/D, 行号较计划漂移):
 *
 * 块G grep 锚点: `HR 拉取历史表③(计划 26-10-04-0312 S5): 桩 --hr-scene on(默认)起盘` 起,
 * 至该 `if (HR_SCENE === "on")` 块收尾止(删块前 L344–410; 计划取证 L1725–1790)。
 * 内含 4 个旧 add() 名(+1 失败兜底): HR表③: 首次展开懒加载, 五形态行齐 / HR表③: 五档徽章各一
 * 且 result_tone 类落上 / HR表③: 仅看异常本地过滤生效(defer+通道不可用) / HR表③: 行展开明细
 * 子行可见(完成行三档) / (兜底) HR表③: 桩走查断言组。
 *
 * 模式门控(计划 §3.2 D1): 与旧脚本同构 —— 整组只在 hr-scene **on** 跑(行数断言在 empty/off
 * 场景不成立: 桩 --hr-scene empty/off 下行集为空/未启用), requireMode 按当前 env 整组跳过,
 * skip 消息带当前值(计划 §6 R2 防静默少跑)。
 *
 * ── 对账映射表(旧断言名 → 新 test 名; 旧块 add() 调用点 4 处/皮肤) ──
 *  旧 add() 行号(删块前 grep 实测)      旧断言名                                        新去向下落
 *  L370  HR表③: 首次展开懒加载, 五形态行齐                              → 首次展开懒加载 + 五形态徽章
 *                                                                (1 test 2 断言: 行数 5 与徽章档位同属
 *                                                                 "首次展开渲染正确"这一时刻的观察)
 *  L380  HR表③: 五档徽章各一且 result_tone 类落上                      → 同上
 *  L388  HR表③: 仅看异常本地过滤生效(defer+通道不可用)                 → 仅看异常过滤 + 行展开明细
 *                                                                (1 test 2 断言: 共享同一 arrange, 过滤
 *                                                                 复原与行展开是同一现场里的连续动作)
 *  L395  HR表③: 行展开明细子行可见(完成行三档)                         → 同上
 *  L404  HR表③: 桩走查断言组(catch 兜底, ok=false)                     → **不迁移**: 失败兜底分支, 新轨
 *                                                                定位器/断言拿不到目标直接红
 *  另: 旧收尾总检「无 console.error / pageerror」→ installRuntimeErrorGuard afterEach。
 *  计数口径: 块G add() 4 处/皮肤(实跑; 兜底 1 处仅失败时出现) → 新 2 test/皮肤 ——
 *  1:N(合并)成立, 每个旧名都有去向下落。
 *
 * ── 对账实跑数字(五步对账 §5.1, 2026-10-06 S5 批实测回填) ──
 *  · 步骤1 新 spec: commands run dev.e2e 全量 66 passed / 10 skipped / 0 failed(2.4m)。
 *  · 步骤2 旧脚本同参数轮: 桩 8235(--torrents 300, --hr-scene on 默认), 旧脚本
 *    --base http://127.0.0.1:8235 --torrents 300 --ui both = 32 项 0 FAIL(1m26s), 无存量失败;
 *    对账范围内块G 4 断言名 × 2 皮肤全 PASS(实测: 5 行 / 五档徽章各 1 / 仅看异常后 2 行 /
 *    明细子行文案「A 考察中 · 有效 · 3 页 / 96 行 · 全深度翻完…」逐字命中)。
 *  · 步骤3 对账映射: 见上表 —— 块G 4 旧名/皮肤 → 2 test/皮肤, 1:N(合并)成立, 每个旧名有
 *    去向下落; catch 兜底 add 不迁移(新轨断言失败即红, 语义等价)。
 *  · 步骤4 删旧块(与本 spec 同 commit): 旧脚本删块G 段 + `--hr-scene` 参数与头注释两处
 *    (与块B 段同批, 见 perf.spec.mjs 头的删段数字)。
 *  · 步骤5 双复跑: 旧脚本(删段后, 同桩 8235)14 项 0 FAIL(37.9s) —— 32−(块B 5 + 块G 4)×2 皮肤
 *    = 14, 项数下降恰对应两块, 零残余失败; 新 spec 复跑绿(66 passed / 10 skipped / 0 failed,
 *    2.4m); E2E_HR_SCENE=empty 抽验(dev.e2e 全量)62 passed / 14 skipped(1.3m) —— 本组 4 test
 *    整组 skip, skip 消息可读: 「模式不匹配, 整组跳过 —— 当前 E2E_HR_SCENE=empty, 本组要求 on」
 *    (e2e/lib/mode.mjs requireMode 注入, 其余组全绿)。
 *  · 时长: 见 perf.spec.mjs 头(R3 监控口径)。
 *
 * ── D4 断言翻译守则落地说明(计划 §3.5) ──
 *  · 交互全部真实手势(对旧块 vm 直调的升级, 均有真实 UI 路径): 进 HR 分区 = 点设置页 hub 的
 *    「HR 在线核实」卡片(旧 vm.hubGo("hr_check")); 站点状态全屏弹层 = 点分区头部「展开」钮
 *    (旧 vm.hrsToggle()); 表③ 首次展开 = 点「拉取历史」summary(旧点 details 元素本体, 收敛到
 *    summary —— 原生 details 只有 summary 命中才触发 @toggle); 仅看异常 = 点 chip(旧同款真实
 *    点击, 只是取元素方式从 evaluate 换成 locator); 行展开 = 点首行(旧同款)。
 *  · 旧块收尾的 vm.hrsCollapse()/vm.hubBack()/localStorage 清理**不再需要** —— 每 test 独立
 *    context, 现场天然隔离(同 views.spec 口径)。
 *  · 旧「仅看异常后 vm.hrsHist.badOnly = false 复原」的 vm 注入改为**再点一次 chip**(真实手势,
 *    同一 toggle 的关向); 复原后行数回 5 的确认并入行展开 test 的前置 expect。
 *  · 阈值/桩文案逐字保留: 五形态行齐 = 5 行、五档徽章 ok|warn|dim|err|blue 各一、仅看异常后
 *    2 行、明细子行文案「A 考察中」「3 页 / 96 行」—— 桩数据契约, 改了就是桩或渲染变了。
 *  · 无保留 sleep: 旧块的 waitForTimeout(250/200/800) 全是等本地过滤/弹层渲染的装饰性等待,
 *    expect 自动等待 / toHaveCount 覆盖同语义。
 */

/** 进设置页 → HR 分区 → 开站点状态全屏弹层 → 首次展开表③(懒加载) → 等行渲染。
 *  块G 所有用例的共同 arrange(旧脚本真实手势链, vm 直调已全部换成 locator 手势)。 */
async function openHrHistoryTable(page, skin) {
  collectRuntimeErrors(page);
  await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

  await page.locator('nav.tabs-right button').click(); // 顶栏右侧「设置」(旧同款真实手势)
  await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
  // 进 HR 分区: 点 hub 卡片(旧 vm.hubGo("hr_check") 的真实手势等价)
  await page.locator('.hb-card', { hasText: 'HR 在线核实' }).click();

  // 站点状态全屏弹层: 分区块头部唯一展开钮(旧 vm.hrsToggle() 的真实手势等价; scope 到
  // 「站点状态」块头, 排除顶栏/其它分区的 aria-expanded 同名钮)
  await page
    .locator('.hb-blk-hd', { hasText: '站点状态' })
    .locator('button[aria-expanded="false"]', { hasText: '展开' })
    .click();
  await expect(page.locator('.hr-full-modal')).toBeVisible({ timeout: 10_000 });

  // 表③ = 弹层里 summary 带「拉取历史」的 details(表② 同类但文案不同); 真实点开 summary,
  // @toggle -> hrsHistOnToggle -> 首次 fetch /api/hr/history(limit=300) —— 懒加载链路本体
  await page.locator('.hr-full-modal details.hrs-diag summary', { hasText: '拉取历史' }).click();
  await expect(page.locator('.hr-full-modal .hr-hist-row').first()).toBeVisible({ timeout: 10_000 });
}

for (const skin of SKINS) {
  test.describe(`皮肤 ${skin}(块G: HR 拉取历史表③)`, () => {
    /* 整组只在 hr-scene on 跑(桩 --hr-scene empty/off 下行集为空/未启用, 行数断言不成立)。 */
    requireMode(test, { hrScene: 'on' });
    installRuntimeErrorGuard(test);

    test('HR表③: 首次展开懒加载, 五形态行齐; 五档徽章各一且 result_tone 类落上', async ({ page }) => {
      await openHrHistoryTable(page, skin);
      const rows = page.locator('.hr-full-modal .hr-hist-row');
      /* 首次展开懒加载: 点 summary 前行不存在(上面的 arrange 里 toBeVisible 已验出现),
       * 这里钉行数 —— 桩 on 场景五形态各一行, 恰好 5。 */
      await expect(rows, 'HR表③: 首次展开懒加载, 五形态行齐(恰好 5 行)').toHaveCount(5);

      /* 五档徽章各一: 徽章类 hr-hres-<tone> 落上(桩契约: ok|warn|dim|err|blue 各 1)。 */
      for (const tone of ['ok', 'warn', 'dim', 'err', 'blue']) {
        await expect(
          page.locator('.hr-full-modal .hr-hist-row .hr-hres.hr-hres-' + tone),
          `HR表③: 五档徽章各一且 result_tone 类落上(hr-hres-${tone})`,
        ).toHaveCount(1);
      }
    });

    test('HR表③: 仅看异常本地过滤生效(defer+通道不可用) + 行展开明细子行可见(完成行三档)', async ({ page }) => {
      await openHrHistoryTable(page, skin);
      const rows = page.locator('.hr-full-modal .hr-hist-row');
      await expect(rows).toHaveCount(5);

      // 仅看异常: 点 chip(纯前端本地过滤, 不回后端 —— 旧同款真实点击, locator 化)
      await page.locator('.hr-full-modal .hr-chip', { hasText: '仅看异常' }).click();
      /* 桩契约: 异常行恰 2 条(defer + 通道不可用)。旧块 250ms 后读数, expect 自动等待覆盖同语义。 */
      await expect(rows, 'HR表③: 仅看异常本地过滤生效(defer+通道不可用, 恰 2 行)').toHaveCount(2);

      // 复原全量行集: 再点一次 chip(旧 vm.hrsHist.badOnly = false 注入的真实手势等价)
      await page.locator('.hr-full-modal .hr-chip', { hasText: '仅看异常' }).click();
      await expect(rows).toHaveCount(5);

      // 行点击 -> hrsHistToggleRow -> 明细子行(桩契约文案逐字保留: 完成行三档「A 考察中」「3 页 / 96 行」)
      await rows.first().click();
      const sub = page.locator('.hr-full-modal .hr-hist-sub');
      await expect(sub).toBeVisible({ timeout: 5_000 });
      const subText = (await sub.innerText()).trim();
      expect(subText, `HR表③: 行展开明细子行可见(完成行三档), 实得 "${subText.slice(0, 70)}"`)
        .toContain('A 考察中');
      expect(subText, '明细子行波次文案(3 页 / 96 行)').toContain('3 页 / 96 行');
    });
  });
}
