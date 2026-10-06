// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { CMD_RESULT, requireMode } from './lib/mode.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { INST, readInst, withVm } from './lib/vm.mjs';
import { armClick, armPending, readPending } from './lib/probes.mjs';

/**
 * 乐观 UI 全家(S3 批, 计划 26-10-06-0708 §3.3/§04 S3) —— 承接旧脚本 scripts/ui_smoke.cjs
 * 的**块C + 块E + hang 探针**三段。行号为取证时点值(计划 §2.2), 已按 grep 锚点复核
 * (2026-10-06, 删块前; S1/S2 已删块A/F/CTX-03, 行号较计划漂移):
 *
 * 块C grep 锚点: `P0-3 乐观 UI: 右键 → 暂停 → 立刻出现 pending` 起, 至 P0-4 批量合单块止
 * (删块前 L449–766; 计划取证 L588–900 —— 差值即 S1 删块A)。内含: 单行右键暂停链(P0-3)、
 * 补丁先于 POST(慢投递)、值覆盖落回真值、压暗撤下、P0-4 批量合单(60 目标)。
 * 块E grep 锚点: `P0-3 整组乐观(BUG-3)` 起, 至 `BUG-9 辅种页复制磁力` 块止
 * (删块前 L1174–1295; 计划取证 L1400–1515)。内含: 整组乐观、真值事件陈旧快照、BUG-9。
 * hang 探针 grep 锚点: `hang 模式(命令永不回执)的**常驻守阵**` 的 hangChecks 函数
 * (删块前 L162–216; 计划取证 L169–214)+ smokeUi 内 `hang 模式独占一轮` 早退分支(L297–303)。
 *
 * 模式门控(计划 §3.2 D1): ok/error 跑主路径组, hang 只跑兜底三连 —— 与旧脚本
 * 「hang 独占一轮 / 主轮不跑 hangChecks」的互斥关系同构, requireMode 按当前 env 整组跳过。
 *
 * ── 对账映射表(旧断言名 → 新 test 名; 旧块 add() 调用点 ok/error 各 11 处/皮肤, hang 4 处/皮肤) ──
 *  旧 add() 行号(删块前 grep 实测)         旧断言名                                    新去向下落
 *  块C:
 *  L481(ok 模式; error 仅 [info])  P0-3 点击后立即可见 pending(乐观)          → 单行暂停(ok 分支, 记录器 appear)
 *  L499(双模式)                    P0-3 回执(EXPECT_CMD)后不留假状态          → 单行暂停(双模式, poll 至干净 ≤8s)
 *  L553(双模式)                    P0-3 补丁先于 POST(注入 800ms 仍即时)      → 补丁先于 POST(<400ms)
 *  L562(仅 error)                  P0-3 慢投递 + 失败回执后回滚干净           → 补丁先于 POST(error 分支)
 *  L668(双模式, FLOOR=80|0)        P0-3 值覆盖及时落回真值(FLOOR~1000ms)      → 值覆盖/压暗/落回真值
 *  L679(双模式)                    P0-3 压暗在回执后及时撤下(<250ms)          → 同上
 *  L692(ok)/L688(error)            P0-3 落回的是真值(行确为 s-paused) /        → 同上(按 CMD_RESULT 分支)
 *                                  P0-3 失败后落回原状态(非假暂停)
 *  L744(双模式)                    P0-4 批量动作合单为一条请求                 → 批量合单 60 目标
 *  L760(ok)/L755(error)            P0-3 批量乐观覆盖全部目标 /                 → 同上(按 CMD_RESULT 分支)
 *                                  P0-3 批量失败后回滚干净
 *  块E:
 *  L1218(ok)/L1212(error)          P0-3 整组乐观(组行 is-pending) /            → 整组乐观(按 CMD_RESULT 分支)
 *                                  P0-3 整组乐观失败后回滚(组行)
 *  L1266(双模式)                   真值事件后不被陈旧快照打回                  → 真值事件陈旧快照(vm 直调, 旧同款)
 *  L1292(双模式)                   BUG-9 辅种页复制磁力不再恒失败              → BUG-9(clipboard 权限 + toast 轮询)
 *  hang 探针:
 *  L209/L211/L214(hang 独占轮)     P0-3 hang: 无回执立刻可见 / 3s 兜底清除     → hang 兜底三连(1 test 3 断言,
 *                                  / 兜底后落回原状态                            2500~6000ms 窗口逐字保留)
 *  L300(hang 轮收尾总检)           无 console.error / pageerror                → installRuntimeErrorGuard afterEach
 *  另: 旧「右键菜单有暂停项 / 值覆盖…找不到未暂停的行」等 add() 均为**失败兜底分支**
 *  (L452/L471/L612/L613/L1192), 新轨定位器拿不到目标直接红, 兜底分支不再需要。
 *  计数口径: 块C ok/error 各 8 处 + 块E 3 处 = 11 处/皮肤(ok 与 error 同数不同名), hang 轮
 *  3+1(总检)=4 处/皮肤 → 新 7 test/皮肤(ok|error) + 1 test/皮肤(hang)。
 *
 * ── 对账实跑数字(五步对账 §5.1 × ok/error/hang 三模式, 2026-10-06 S3 批实测回填) ──
 *  · 步骤2 旧脚本同参数轮(适配版): 桩 8231+ --torrents 300 --ui both --expect-cmd <mode>,
 *    W4 导出段两块(多选导出/组选中导出)按任务书临时中和(仅工作树, 已随批还原)让块E可达:
 *    - ok 轮:   80 项 78 PASS / 2 FAIL —— 失败仅「顶栏三视图按钮存在」×2, 系 S2 删块F 时
 *      残留的悬空 add(ok=false 恒红, 本机 nav=4 时必触发), 与本批三段无关, 已记录不修;
 *    - error 轮: 80 项 76 PASS / 4 FAIL —— 上两项之外再加「W5 批量限速成功回执 toast」×2,
 *      error 模式存量(W2/W5 段归 S4 批): 成功 toast 在 --cmd-result error 下恒不出现;
 *    - hang 轮: 8 项(hangChecks 3 + 收尾总检 1)× 2 皮肤全 PASS(消失 3057/3077ms, 窗口内)。
 *    对账范围内(块C + 块E)× 2 皮肤: ok 22/22 全 PASS, error 22/22 全 PASS; hang 6/6 全 PASS。
 *  · 步骤1/5 新 spec(双模式轮 + 复跑): ok = 默认档 42 passed / 2 skipped(hang 组 ×2 皮肤,
 *    实测 1.3m); error = 42 passed / 2 skipped(1.3m); hang = 30 passed / 14 skipped(主路径组
 *    ×2 皮肤整组 skip, 实测 1.1m; 兜底三连 9.2s/9.1s)。
 *  · 步骤5 双复跑: 旧脚本(删三段 + 还原中和)ok 轮 34 项 32 PASS / 2 FAIL —— 失败仍仅 W4
 *    每皮肤 1 条存量「冒烟整体执行 — elementHandle.click: Timeout 30000ms」(W4 超时中断该皮肤
 *    后续块, 故 顶栏/设置/HR/列设置 段未执行, 项数 34 = 中和轮 80 - 删块 22 - 中断未达 24),
 *    零新增失败; 新 spec 三模式复跑绿(数字同上); npm run test:e2e:fast 4 passed(10.1s)不变。
 *  · 步骤4: 旧脚本删块C/块E/hang 探针(hangChecks 函数 + 独占轮早退)+ 其专属脚手架
 *    pausableRow / CMD_URL(净 14+/536-); armPending/armClick/readPending 探针三件**保留** ——
 *    W2 限速的 armClick 依赖 armPending 预置的 window.__p 时刻基准(删掉会让 W2 轮 pageerror)。
 *  · 计划外发现(记录不修): S2 multiselect-shows.spec error 分支「前行/集行乐观补丁先贴上」
 *    用 expect.poll 轮 pendingOps>0 —— error 模式补丁+回滚窗口可短于首个采样, 窗口错过即恒红
 *    (实测三次 error 轮: 1 次全绿 / 2 次各红 3 条, 红=multiselect 3 条, 本 spec 14 条全绿)。
 *    本 spec 的 error 分支一律轮**终态**(归零)或用 4ms 采样器, 无此竞态; 修不修走 issue 流程。
 *
 * ── D4 断言翻译守则落地说明(计划 §3.5) ──
 *  · 交互真实手势: 行右键/菜单项点击走 clickRow()/locator.click(clickRow 对冲写法沿用
 *    multiselect-shows.spec —— 宽行居中滚动把行左缘落点滚出裁剪面的 flaky 机理, 见该文件头)。
 *  · evaluate 保留处(均有注释): ①armPending/armClick/readPending(vm 内部时序探针, 第②类);
 *    ②T2/T3/hang 的页面内采样器(旧 __m/__t/__h 原样移植, 第②类); ③T4 注入选中集合 + 清选
 *    (N=60 真实 Ctrl+click 不可行, 选中集合升级链路已由 multiselect-shows 用真实手势在 N=5
 *    验过 —— 注入桩态属第①类); ④T6/T7 直调 vm(旧脚本注释明言"刻意直调, 本条测的是时序",
 *    第②类); ⑤T3 的 vm.refresh() 真值预对齐(第①类注入/复原桩态)。
 *  · 阈值数字逐字保留: 补丁先于 POST 800ms 注入/400ms 预算、值覆盖 80(ok)|0(error)~1000ms、
 *    压暗 <250ms、批量峰值下界 min(picked,60)*0.8、1500ms 请求观察窗、hang 三连
 *    appear<500 / 消失 2500~6000ms / 6.5s 采样窗 —— 这些是回归基准, 不是等待。
 *  · 桩命令泵瞬时回执 ⇒ 压暗窗口只有几十 ms, expect.poll 会整段错过 —— 乐观出现类断言一律
 *    用 armPending 记录器判"曾经出现过"(probes.mjs 的存在理由, S2 同口径)。
 *  · 每 test 独立 context ⇒ 旧脚本跨块的 settle sleep(等 3s 兜底窗口过等)不再需要;
 *    保留的 sleep 均有注释: T1 400ms/T5 900ms(让记录器把瞬时起落采完再读, 旧同值)、
 *    T3 400ms(真值预对齐后的 ver 去抖, 旧同值)、T4/hang 观察窗(断言语义)。
 */

/** 导航页签定位器(tpl/topbar.html `nav.tabs [data-view]`)。 */
const tab = (page, view) => page.locator(`nav.tabs [data-view="${view}"]`);
/** 菜单项定位器(ctx 菜单是 div.ctx-item, 无 role, 按文案取)。 */
const ctxItem = (page, text) => page.locator('.ctx-item', { hasText: text });

/** 命令投递端点谓词(旧 CMD_URL 原样移植; 给「补丁先于 POST」注入人为延迟用)。
 *  !Playwright 路由谓词收到的是 URL 对象而不是字符串, 别直接当 string 用。 */
const CMD_URL = (u) => {
  const s = typeof u === 'string' ? u : String(u);
  return /\/api\/(torrents|groups)\/[^/?]+\/(pause|resume)(\?|$)/.test(s) || s.includes('/api/torrents/bulk');
};

/** 行状态色类(s-paused / s-seeding …), 旧 hangChecks/整组回滚同款。 */
const sCls = (c) => (c || '').split(' ').find((x) => x.startsWith('s-')) || '';

/**
 * 行点击统一入口: 真实鼠标手势 + 落点可验(对冲写法沿用 multiselect-shows.spec, 机理见其文件头:
 * 宽行居中滚动把 {x:8,y:8} 落点滚出裁剪面 ⇒ sticky-head/html 交替拦截 30s —— 这里 5 拍 arrange
 * + elementFromPoint 验落点, 拦截发生时立即带现场报错)。
 *
 * @param {import('@playwright/test').Page} page
 * @param {import('@playwright/test').Locator} row
 * @param {{button?: 'left'|'right', modifiers?: Array<'Control'|'Shift'|'Alt'|'Meta'>}} [opts]
 * @returns {Promise<void>}
 */
async function clickRow(page, row, opts = {}) {
  const { button = 'left', modifiers = [] } = opts;
  let last = null;
  for (let attempt = 0; attempt < 5; attempt++) {
    last = await row.evaluate(async (/** @type {HTMLElement} */ el) => {
      const cont = el.closest('.group-table');
      if (cont && cont.scrollLeft !== 0) cont.scrollLeft = 0;
      const head = document.querySelector('.sticky-head');
      const headBottom = head ? head.getBoundingClientRect().bottom : 0;
      let r = el.getBoundingClientRect();
      if (r.top < headBottom + 8 || r.bottom > window.innerHeight - 8) {
        el.scrollIntoView({ block: 'center', behavior: 'instant' });
        await new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(res)));
        r = el.getBoundingClientRect();
      }
      const x = r.left + 8;
      const y = r.top + 8;
      const hit = document.elementFromPoint(x, y);
      return {
        x, y,
        ok: !!hit && (hit === el || el.contains(hit)),
        hit: hit ? `${hit.tagName}.${String(hit.className && hit.className.baseVal !== undefined ? hit.className.baseVal : hit.className || '')}`.slice(0, 60) : '(null)',
      };
    });
    if (last.ok) break;
  }
  if (!last.ok || !last) {
    throw new Error(`clickRow: 落点验证 5 拍未过(行左缘 8,8 被拦截, 最后拦截者 ${last ? last.hit : '?'})—— ` +
      `这是 smoke.md「点击拦截面随布局漂移」签名, 请带 trace 走 issue 流程, 别加 sleep 硬等`);
  }
  if (modifiers.length) {
    for (const k of modifiers) await page.keyboard.down(k);
  }
  try {
    await page.mouse.click(last.x, last.y, { button });
  } finally {
    for (const k of modifiers) await page.keyboard.up(k);
  }
}

/**
 * 打开首页并等首屏渲染(每 test 独立 context 的公共 arrange 前奏, 与 multiselect-shows 同款)。
 * @param {import('@playwright/test').Page} page
 * @param {string} skin
 */
async function openApp(page, skin) {
  collectRuntimeErrors(page);
  await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
}

/**
 * 找一个"可暂停"的行(未被暂停过的)。找不到就把第一行**恢复**一次再用 —— 一轮会连续暂停
 * 几十个目标(批量 60 个), 后面的用例很容易撞上"窗口里全是已暂停"(旧 pausableRow 同款兜底,
 * 走真实右键手势)。注意: 桩服务是单实例长驻, 暂停的真值跨 test 持续, 本 helper 是必需品。
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} rowSel —— 行选择器(.torrent-row / .group-row[data-table="group"])
 * @param {string} resumeText —— 恢复菜单项文案(开始该种子 / 开始整组)
 * @returns {Promise<import('@playwright/test').Locator|null>}
 */
async function pausableRow(page, rowSel, resumeText) {
  const pick = async () => {
    const rows = page.locator(rowSel);
    const n = await rows.count();
    for (let i = 0; i < n; i++) {
      const cls = (await rows.nth(i).getAttribute('class')) || '';
      if (!cls.includes('s-paused')) return rows.nth(i);
    }
    return null;
  };
  let row = await pick();
  if (row || !resumeText) return row;
  const first = page.locator(rowSel).first();
  await clickRow(page, first, { button: 'right' });
  const resume = ctxItem(page, resumeText);
  await expect(resume.first()).toBeVisible({ timeout: 5_000 });
  await resume.first().click();
  // 等"恢复"的真值落回(旧固定睡 1200ms; 升级为轮询行 class 离开 s-paused, 语义不变)
  await expect.poll(async () => (await first.getAttribute('class')) || '', {
    message: '恢复的真值落回(行离开 s-paused)', timeout: 4_000,
  }).not.toContain('s-paused');
  return pick();
}

/**
 * 乐观态残留读数(旧「回执后不留假状态」的轮询口径): pending 行数 + pendingOps 条数。
 * @param {import('@playwright/test').Page} page
 */
const pendingState = (page) => withVm(page, `return {
  rows: document.querySelectorAll('.torrent-row.is-pending, .group-row.is-pending').length,
  ops: Object.keys(vm.pendingOps || {}).length,
};`);

for (const skin of SKINS) {
  test.describe(`皮肤 ${skin}(块C+E: 乐观 UI)`, () => {
    test.describe('块C+E 主路径(ok/error)', () => {
      /* hang 模式下主轮断言在 40s 命令超时下会拖到十分钟(旧脚本"hang 独占一轮"同款互斥) */
      requireMode(test, { cmdResult: ['ok', 'error'] });
      installRuntimeErrorGuard(test);

      test('P0-3 单行暂停: 乐观 pending 立即可见(ok)/回执后不留假状态(双模式)', async ({ page }) => {
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        const row = await pausableRow(page, '.torrent-row', '开始该种子');
        expect(row, '找到可暂停的种子行(且恢复兜底成功)').toBeTruthy();

        await clickRow(page, /** @type {import('@playwright/test').Locator} */ (row), { button: 'right' });
        const item = ctxItem(page, '暂停该种子');
        await expect(item).toBeVisible({ timeout: 5_000 });
        await armPending(page); // 记录器必须在点击**之前**装好(瞬时窗口, 事后再数恒 0)
        await armClick(page, await item.elementHandle());
        await item.click();

        if (CMD_RESULT === 'ok') {
          await page.waitForTimeout(400); // 旧同值: 让记录器把瞬时起落采完再读
          const p = await readPending(page);
          // 判"曾经出现过"而不是"此刻还有" —— 真值对齐修好后 pending 只活 100~300ms
          expect(p.appear, `点击 → 出现 ${p.appear === null ? '从未出现' : p.appear + 'ms'}`).not.toBeNull();
        }
        // 成功回执后 pending 会一直贴到"真值对齐"(或 3s 兜底) —— 立刻清会出现"先变过去、
        // 下一轮又弹回来"。等到彻底干净再断言"不留假状态"(旧 8s 上限同值)。
        await expect.poll(() => pendingState(page), {
          message: `回执(${CMD_RESULT})后不留假状态`, timeout: 8_000,
        }).toEqual({ rows: 0, ops: 0 });
      });

      test('P0-3 补丁先于 POST(慢投递注入 800ms 仍即时; error 加验失败回滚干净)', async ({ page }) => {
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        const DELAY = 800;
        const BUDGET = 400; // 远小于注入的 800ms、又远高于本地正常的 ~10ms(阈值逐字保留)
        await page.route(CMD_URL, async (route) => {
          await new Promise((r) => setTimeout(r, DELAY));
          await route.continue();
        });
        const target = await pausableRow(page, '.torrent-row', '开始该种子');
        expect(target, '找到未暂停的行').toBeTruthy();

        await clickRow(page, /** @type {import('@playwright/test').Locator} */ (target), { button: 'right' });
        const item = ctxItem(page, '暂停该种子');
        await expect(item).toBeVisible({ timeout: 5_000 });
        // vm 内部时序探针(D4 第②类, 旧 __m 原样移植): MutationObserver 抓 .is-pending 首现
        await page.evaluate(`(() => {
          window.__m = { t0: null, dom: null };
          if (window.__mo2) window.__mo2.disconnect();
          window.__mo2 = new MutationObserver(() => {
            if (window.__m.dom === null && document.querySelector('.is-pending')) window.__m.dom = performance.now();
          });
          window.__mo2.observe(document.body, { subtree: true, attributes: true, attributeFilter: ['class'], childList: true });
        })()`);
        await item.evaluate((el) => el.addEventListener('click', () => {
          window.__m.t0 = performance.now();
        }, { capture: true, once: true })); // t0 钉在菜单项 click 事件, 不含鼠标开销(旧同款; __m 不是
        // armPending 的 __p, 不能用 armClick —— 那依赖 armPending 预置的 window.__p)
        await item.click();
        // lat 为 null(从未出现)时 toBeLessThan 同样不过 ⇒ 轮询自然覆盖"未出现"分支
        // (旧 deadline DELAY+1500 同窗口)
        await expect.poll(() => page.evaluate(`(() => {
          const m = window.__m; return (m.t0 && m.dom) ? Math.round(m.dom - m.t0) : null;
        })()`), {
          message: `点击 → is-pending(阈值 ${BUDGET}ms; POST 注入 ${DELAY}ms)`, timeout: DELAY + 1500,
        }).toBeLessThan(BUDGET);
        await page.unrouteAll({ behavior: 'ignoreErrors' });
        if (CMD_RESULT === 'error') {
          // 补丁提前后"发送失败"必须显式回滚(旧 L562; ok 模式旧脚本仅 [info] 不设断言)
          await expect.poll(() => pendingState(page), {
            message: 'error 模式: 慢投递 + 失败回执后回滚干净', timeout: 8_000,
          }).toEqual({ rows: 0, ops: 0 });
        }
      });

      test('P0-3 值覆盖及时落回真值 + 压暗及时撤下 + 落回真值(ok)/原状态(error)', async ({ page }) => {
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        const BUDGET = 1000;      // 值覆盖释放上界(走满 3s 兜底是它的回归形态)
        const GREY_BUDGET = 250;  // 压暗上界(正常 ~20ms; 退化 ~350ms 必红 —— 阈值逐字保留)
        // error 无"等真值"这回事(失败立即回滚 ~21ms), 套下界会恒红(旧同款)
        const FLOOR = CMD_RESULT === 'error' ? 0 : 80;
        // !挑目标**之前**先与服务端真值对齐一次(旧同款): 前面的用例暂停过的行, 前端要等下一轮
        // 轮询才在 DOM 反映 —— 不对齐会挑到"服务端已 paused"的行 ⇒ pending 瞬间清, 断言恒绿
        // 却什么都没测到。vm.refresh 属注入/复原桩态类 evaluate(D4 第①类)。
        await withVm(page, 'return vm.refresh && vm.refresh();');
        await page.waitForTimeout(400); // 旧同值: 等 ver 去抖 + DOM 落地
        const target = await pausableRow(page, '.torrent-row', '开始该种子');
        expect(target, '找到未暂停的行').toBeTruthy();
        // 以 data-hash 锚定目标行: 2s 整表重渲染会换掉行节点, nth 定位可能漂到别的行
        const targetHash = await (/** @type {import('@playwright/test').Locator} */ (target))
          .getAttribute('data-hash');
        expect(targetHash, '目标行带 data-hash').toBeTruthy();
        const targetRow = page.locator(`.torrent-row[data-hash="${targetHash}"]`);
        const beforeKind = await targetRow.evaluate((el) => [...el.classList].find((c) => c.startsWith('s-')) || '(无)');

        await clickRow(page, /** @type {import('@playwright/test').Locator} */ (target), { button: 'right' });
        const item = ctxItem(page, '暂停该种子');
        await expect(item).toBeVisible({ timeout: 5_000 });
        // vm 内部时序探针(D4 第②类, 旧 __t 原样移植): 压暗走 MutationObserver; 值覆盖
        // (pendingOps 是响应式对象、DOM 上看不见)只能 4ms 定时采样 —— 4ms 远小于 error
        // 回滚 ~21ms, 不至漏采整个起落。
        await page.evaluate(`(() => {
          const vm = ${INST};
          window.__t = { t0: null, dom0: null, clear: null, opsUp: null, opsDown: null };
          if (window.__mo3) window.__mo3.disconnect();
          window.__mo3 = new MutationObserver(() => {
            const m = window.__t;
            if (m.dom0 === null && document.querySelector('.is-pending')) m.dom0 = performance.now();
            if (m.dom0 !== null && m.clear === null && !document.querySelector('.is-pending')) m.clear = performance.now();
          });
          window.__mo3.observe(document.body, { subtree: true, attributes: true, attributeFilter: ['class'], childList: true });
          clearInterval(window.__ti3);
          window.__ti3 = setInterval(() => {
            const m = window.__t;
            const n = Object.keys(vm.pendingOps || {}).length;
            if (m.opsUp === null) { if (n > 0) m.opsUp = performance.now(); return; }
            if (m.opsDown === null && n === 0) m.opsDown = performance.now();
          }, 4);
        })()`);
        await item.evaluate((el) => el.addEventListener('click', () => {
          window.__t.t0 = performance.now();
        }, { capture: true, once: true })); // t0 钉在菜单项 click 事件(旧同款; __t 不是 armPending 的
        // __p, 不能用 armClick —— 那依赖 armPending 预置的 window.__p)
        await item.click();
        const rel = (k) => page.evaluate(`(() => {
          const m = window.__t; return (m.t0 && m[${JSON.stringify(k)}] !== null) ? Math.round(m[${JSON.stringify(k)}] - m.t0) : null;
        })()`);
        // 2. 值覆盖释放(pendingOps 归零): 下界防"拿自己贴的补丁当真值比对"(实测过的坑:
        //    28ms 就清, 断言全绿却什么都没测到); 上界的回归形态 = 走满 3s 兜底。
        await expect.poll(() => rel('opsDown'), {
          message: `点击 → pendingOps 归零(须 ${FLOOR}~${BUDGET}ms)`, timeout: 8_000,
        }).toBeLessThan(BUDGET);
        const opsDown = await rel('opsDown');
        expect(opsDown, `pendingOps 归零 ${opsDown}ms, 早于 ${FLOOR}ms 说明没等真值、只是跟自己的补丁比上了` +
          `(error 模式 = 失败立即回滚)`).toBeGreaterThanOrEqual(FLOOR);
        // 1. 压暗(DOM .is-pending)单独成条: 用户感知的那一半; 上界卡"压暗不随回执结束、
        //    挂到值覆盖释放(~350ms)才消失"的回归形态。
        await expect.poll(() => rel('clear'), {
          message: `点击 → is-pending 消失(须 <${GREY_BUDGET}ms)`, timeout: 8_000,
        }).toBeLessThan(GREY_BUDGET);
        await page.evaluate('(() => { clearInterval(window.__ti3); if (window.__mo3) window.__mo3.disconnect(); })()');
        // 光"pending 消失"不够 —— 回滚也会让它消失。必须落回真值本身: ok 行必须是暂停态
        // (证明清 pending 的是"真值匹配"而不是"补丁撤了退回旧值"); error 必须落回原状态。
        const cls2 = () => targetRow.getAttribute('class');
        if (CMD_RESULT === 'error') {
          const after = (await cls2()) || '';
          expect(after, `行 class: ${after}`).not.toContain('s-paused');
        } else {
          expect(beforeKind, '前置自证: 点击前不是暂停态(否则"真值对齐"是白捡的)').not.toContain('s-paused');
          await expect.poll(async () => (await cls2()) || '', {
            message: '落回的是真值(行确为 s-paused)', timeout: 4_000,
          }).toContain('s-paused');
        }
      });

      test('P0-4 批量合单: 60 目标恰好 1 条 bulk / 0 条逐目标 + 乐观覆盖全部目标(ok)/回滚干净(error)', async ({ page }) => {
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        const N = 60;
        // 注入选中集合(D4 第①类): N=60 的真实 Ctrl+click 不可行; 选中集合的升级/合单链路
        // 已由 multiselect-shows.spec 用真实手势在 N=5 验过, 这里只验合单规模。
        const picked = await withVm(page,
          `vm.selGroups = []; vm.selMembers = vm.filteredTorrents.slice(0, ${N}).map((r) => r.hash); return vm.selMembers.length;`);
        expect(picked, '注入选中集合').toBe(N);
        // 行是窗口化的: 只在**已渲染**的行里挑一个属于选中集合的锚点(菜单才会升级为批量)
        const anchorHash = await withVm(page, `const sel = new Set(vm.selMembers);
          const el = [...document.querySelectorAll('.torrent-row')].find((r) => sel.has(r.getAttribute('data-hash')));
          return el ? el.getAttribute('data-hash') : null;`);
        expect(anchorHash, '渲染窗口内找到选中锚点').toBeTruthy();
        const anchor = page.locator(`.torrent-row[data-hash="${anchorHash}"]`);

        const hits = { bulk: 0, single: 0 };
        const onReq = (/** @type {import('@playwright/test').Request} */ r) => {
          const u = r.url();
          if (u.includes('/api/torrents/bulk')) hits.bulk++;
          else if (/\/api\/torrents\/[^/?]+\/pause(\?|$)/.test(u)) hits.single++;
        };
        page.on('request', onReq);
        await clickRow(page, anchor, { button: 'right' });
        const item = ctxItem(page, '批量暂停');
        await expect(item).toBeVisible({ timeout: 5_000 });
        await armPending(page, '.torrent-row.is-pending, .group-row.is-pending'); // 点击之前装好
        await armClick(page, await item.elementHandle());
        await item.click();
        // 回执是异步流: 先等 bulk 到 1, 再给一个确定的观察窗看"逐目标误发"(旧 1500ms 同值)
        await expect.poll(() => hits.bulk, { message: '批量暂停应恰好 1 条 bulk POST' }).toBe(1);
        await page.waitForTimeout(1500);
        page.off('request', onReq);
        expect(hits.bulk, `选中 ${picked} 个 → bulk ${hits.bulk} 次`).toBe(1);
        expect(hits.single, `bulk 之后的逐目标 pause ${hits.single} 次`).toBe(0);

        const p = await readPending(page);
        if (CMD_RESULT === 'error') {
          // error 回执瞬间回, 乐观窗口在采样前就关了 —— 那不是缺陷, 是采样时机(旧同款改验回滚)
          await expect.poll(() => pendingState(page), {
            message: 'error 模式: 批量失败后回滚干净', timeout: 8_000,
          }).toEqual({ rows: 0, ops: 0 });
        } else {
          // 用**峰值**而不是"此刻的数量": 真值对齐修好后 1500ms 早清干净了(下界 *0.8 逐字保留)
          expect(p.peak, `峰值 pendingOps ${p.peak}(@${p.peakT === null ? '-' : p.peakT + 'ms'}) / 目标 ${picked}`)
            .toBeGreaterThanOrEqual(Math.min(picked, N) * 0.8);
        }
        // 清掉选择, 免得影响后续用例(注入态复原, D4 第①类)
        await withVm(page, 'return vm.clearSelection && vm.clearSelection();');
      });

      test('P0-3 整组乐观(BUG-3): 组行 is-pending(ok)/失败后回滚(error)', async ({ page }) => {
        // 分组视图(旧"先切回分组"的等价 arrange); 走 pausableRow 兜底 —— 前面的用例已暂停
        // 大量目标, 窗口里的组行很容易全是 s-paused(2026-09-19 实测 atlas 因此挂过)。
        await openApp(page, skin);
        const gRow = await pausableRow(page, '.group-row[data-table="group"]', '开始整组');
        expect(gRow, '找到可暂停的组行(且恢复兜底成功)').toBeTruthy();
        const before = (await gRow.getAttribute('class')) || '';

        await clickRow(page, /** @type {import('@playwright/test').Locator} */ (gRow), { button: 'right' });
        const item = ctxItem(page, '暂停整组');
        await expect(item).toBeVisible({ timeout: 5_000 });
        await armPending(page, '.group-row.is-pending'); // 必须在点击**之前**装好
        await armClick(page, await item.elementHandle());
        await item.click();

        if (CMD_RESULT === 'error') {
          await expect.poll(() => pendingState(page), {
            message: 'error 模式: 整组失败回滚(pendingOps 归零)', timeout: 8_000,
          }).toEqual({ rows: 0, ops: 0 });
          const after = (await gRow.getAttribute('class')) || '';
          expect(after, `${before} -> ${after}`).not.toContain('is-pending');
          expect(sCls(after), '回滚后状态色落回点击前(状态色取自 g.status.primary)').toBe(sCls(before));
        } else {
          await page.waitForTimeout(900); // 旧同值: 让记录器把组行 pending 起落采完
          const p = await readPending(page);
          // 判"组行**曾经**出现过 pending"(记录器) —— 组行 pending 只活 100~300ms,
          // 点完再数一次必然是 0(不是回归, 是度量方式失效)
          expect(p.appear, `点击 → 组行出现 pending ${p.appear === null ? '从未出现' : p.appear + 'ms'} / ` +
            `消失 ${p.gone === null ? '-' : p.gone + 'ms'}`).not.toBeNull();
        }
      });

      test('真值事件后不被陈旧快照打回(值覆盖保持到快照同意)', async ({ page }) => {
        await openApp(page, skin);
        // 「真值到达」≠「值覆盖结束」(2026-09-21 用户报「整组暂停后 灰→绿→灰」): 真值走
        // torrents/info 直查, 比自己的 /sync/maindata 快照新 ≤1.5s。若真值事件一到就把
        // pendingOps 删掉, 这 1.5s 内任何一次视图发布都会带着命令前的 kind 打回行色。
        // 刻意直调 vm.applyOptimistic/resolveOptimistic/onTruthEvent(不经右键菜单): 本条测的
        // 是"时序", 菜单与点击时序已由前面用例覆盖 —— vm 内部时序探针(D4 第②类, 旧原样移植)。
        const t = await page.evaluate(`(() => {
          const vm = ${INST};
          // 挑一个"成员状态一致且非暂停"的组(前面的用例已暂停过大量行)
          const g = vm.decoratedGroups.find((x) => x.members.length && x.members.every((m) => m.kind !== "paused"));
          if (!g) return { err: "找不到可暂停的组" };
          const hashes = g.members.map((m) => m.hash);
          const key = g.key;
          const before = vm.decoratedGroups.find((x) => x.key === key).status.primary;
          vm.applyOptimistic(hashes, "pause");
          const afterPatch = vm.decoratedGroups.find((x) => x.key === key).status.primary;
          vm.resolveOptimistic(hashes, true);   // 回执到达(结束压暗, 转入值覆盖)
          const truth = {};
          for (const h of hashes) truth[h] = { kind: "paused" };
          vm.onTruthEvent({ cmd_id: "smoke", truth });   // 真值事件(服务端直查)
          const held = Object.keys(vm.pendingOps || {}).length;
          // 陈旧快照: 服务端这一版仍是命令前的 kind, 且 rid 前进(真机窗口最多 1.5s)
          for (const gg of vm.groups) for (const m of gg.members) if (hashes.includes(m.hash)) m.kind = before;
          vm._snapshotTruth({ groups: vm.groups, singles: [], torrents: [] });   // refresh() 的同一顺序
          vm.reapplyPending();
          const afterStale = vm.decoratedGroups.find((x) => x.key === key).status.primary;
          // 快照追上: 这一版真的带上了 paused -> 覆盖必须收工(不留假状态)
          for (const gg of vm.groups) for (const m of gg.members) if (hashes.includes(m.hash)) m.kind = "paused";
          vm._snapshotTruth({ groups: vm.groups, singles: [], torrents: [] });
          vm.reapplyPending();
          const released = Object.keys(vm.pendingOps || {}).length;
          // 复原: 本条没真发命令, 前后端都没变, 行上的补丁要撤干净(免污染后续断言)
          for (const h of hashes) { vm._forEachRow(h, (r) => { r.kind = before; }); delete vm.pendingOps[h]; }
          return { key, before, afterPatch, held, afterStale, released };
        })()`);
        expect(t.err, `前置: ${t.err || 'ok'}`).toBeUndefined();
        expect(t.afterPatch, `补丁贴上(${t.before} → ${t.afterPatch})`).toBe('paused');
        expect(t.afterStale, '陈旧快照不得打回行色(值覆盖保持)').toBe('paused');
        expect(t.held, `覆盖保持 ${t.held} 条`).toBeGreaterThan(0);
        expect(t.released, '快照同意后覆盖必须收工(不留假状态)').toBe(0);
      });

      test('BUG-9: 辅种页复制磁力不再恒失败', async ({ page }) => {
        // "复制磁力"要真写剪贴板, headless 默认会拒 —— 旧脚本 context 级 permissions 同款
        await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);
        await openApp(page, skin);
        // magnet_uri **只**在种子页的平铺 SEED_ITEM 里, 成员索引(groups/singles)不带该字段
        // ⇒ 修复前在辅种页恒提示"该种子没有 magnet 链接"(与种子是否真有磁力无关)。
        // 断言刻意避开剪贴板实现差异: 只验"不再弹失败提示"; 注入 vm.menu + 直调
        // copyTorrentInfo(菜单开合 DOM 路径已由 menus 批的 CTX-06 覆盖) —— D4 第①/②类。
        const r = await page.evaluate(`(async () => {
          const vm = ${INST};
          const g = vm.groups.find((x) => (x.members || []).length);
          if (!g) return { err: 'no group' };
          const h = g.members[0].hash;
          const idxHasMagnet = 'magnet_uri' in (vm.memberByHash.get(h) || {});
          vm.menu = { visible: true, hash: h, key: null };
          await vm.copyTorrentInfo('magnet');
          return { idxHasMagnet };
        })()`);
        expect(r.err, '辅种页有带成员的组').toBeUndefined();
        expect(r.idxHasMagnet, '前置自证: 索引确不带 magnet_uri(否则本断言空过)').toBe(false);
        const lastToast = () => readInst(page,
          `(() => { const t = (vm.toasts || []).slice(-1)[0]; return t ? t.kind + '|' + t.text : null; })()`);
        await expect.poll(lastToast, { message: '复制磁力应弹出回执 toast(而不是静默)', timeout: 5_000 }).toBeTruthy();
        const toast = /** @type {string} */ (await lastToast());
        expect(toast.split('|').slice(1).join('|'), `toast=${toast}`).not.toBe('该种子没有 magnet 链接');
      });
    });

    test.describe('hang 兜底三连(命令永不回执)', () => {
      /* 只在 hang 轮跑: 判「失败/未知绝不留永久假状态」这条红线在**无回执**场景下还成不成立
       * —— 2026-09-19 之前兜底只 delete pendingOps 不回滚字段值, 命令根本没执行界面却一直
       * 显示已暂停, ok/error 两轮都碰不到这条路径(issue 26-09-19-2141)。 */
      requireMode(test, { cmdResult: 'hang' });
      installRuntimeErrorGuard(test);
      test.setTimeout(60_000); // 6.5s 采样窗 + 恢复兜底 + boot, 30s 默认太紧

      test('P0-3 hang: 无回执立刻可见 pending → 3s 兜底清除(2500~6000ms) → 落回原状态', async ({ page }) => {
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        await page.waitForTimeout(900); // 旧同值: 等首轮轮询/渲染尘埃落定再装采样器
        const row = await pausableRow(page, '.torrent-row', '开始该种子');
        expect(row, '找到可暂停的行(且恢复失败)').toBeTruthy();
        const rowLoc = /** @type {import('@playwright/test').Locator} */ (row);
        const hash = await rowLoc.getAttribute('data-hash');
        expect(hash, '行带 data-hash').toBeTruthy();
        const before = sCls((await rowLoc.getAttribute('class')) || '');

        // vm/DOM 时序探针(D4 第②类, 旧 __h 原样移植): 10ms 采样钉住目标行的 is-pending 与状态色
        await page.evaluate(`(() => {
          const H = ${JSON.stringify(hash)};
          window.__h = { t0: null, rows: [] };
          window.__hi = setInterval(() => {
            const s = window.__h;
            if (s.t0 === null) return;
            const el = document.querySelector('.torrent-row[data-hash="' + H + '"]');
            s.rows.push({
              t: Math.round(performance.now() - s.t0),
              pend: el ? el.className.includes('is-pending') : null,
              cls: el ? ((el.className.split(' ').find((x) => x.startsWith('s-')) || '')) : null,
            });
          }, 10);
        })()`);
        await clickRow(page, rowLoc, { button: 'right' });
        const item = ctxItem(page, '暂停该种子');
        await expect(item).toBeVisible({ timeout: 5_000 });
        await item.evaluate((el) => el.addEventListener('click', () => {
          window.__h.t0 = performance.now();
        }, { capture: true, once: true }));
        await item.click();
        // 兜底 3s + 轮询周期 ⇒ 最长约 5s; 留到 6.5s 保证采到"消失"那一帧(旧同值 —— 这是
        // 采样窗口断言的一部分, 不是可省的等待)
        await page.waitForTimeout(6500);
        const rows = await page.evaluate('(() => { clearInterval(window.__hi); return window.__h.rows; })()');
        const i0 = rows.findIndex((/** @type {{pend: boolean|null}} */ r) => r.pend);
        const appear = i0 >= 0 ? rows[i0].t : null;
        let gone = null;
        if (i0 >= 0) for (let j = i0; j < rows.length; j++) if (!rows[j].pend) { gone = rows[j].t; break; }
        const after = rows.length ? rows[rows.length - 1].cls : null;
        // 三连(阈值逐字保留): 1.乐观立即出现 2.约 3s 兜底清除 3.落回点击前状态色 ——
        // 光"消失"不够(回滚也会消失), 必须证明兜底真的把补丁撤了。
        expect(appear, `点击 → 出现 ${appear === null ? '从未出现' : appear + 'ms'}`).toBeLessThan(500);
        expect(gone, `点击 → 消失 ${gone === null ? '始终未消失' : gone + 'ms'}(须 2500~6000ms)`)
          .toBeGreaterThanOrEqual(2500);
        expect(gone, `点击 → 消失 ${gone === null ? '始终未消失' : gone + 'ms'}(须 2500~6000ms)`)
          .toBeLessThanOrEqual(6000);
        expect(after, `兜底后落回原状态(不留假状态): ${before} -> ${after}`).toBe(before);
      });
    });
  });
}
