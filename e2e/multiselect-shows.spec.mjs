// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { CMD_RESULT } from './lib/mode.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst } from './lib/vm.mjs';
import { armClick, armPending, readPending } from './lib/probes.mjs';

/**
 * 多选右键 + 追剧视图(S2 批, 计划 26-10-06-0708 §3.3/§04 S2) —— 承接旧脚本 scripts/ui_smoke.cjs
 * 的**块D·CTX-03 段**与**块F**(存量 flaky 所在块, 计划 §2.4: 追剧集行 Ctrl+click 落点被
 * sticky-head/header.topbar 交替拦截)。行号为取证时点值, 已按 grep 锚点复核(2026-10-06, 删块前):
 *
 * 块D·CTX-03 段 grep 锚点: `CTX-03 多选右键 = 对**整个选中集合**生效` 起,
 * 至 `CTX-03 批量乐观覆盖整个选中集合` 止(旧脚本现 L777–851; 计划取证 L940–983 —— 差值即 S1 删块A)。
 * 块F grep 锚点: `await nav[2].click();  // 追剧` 起, 至 `BUG-8 刷新后追剧页不空白` 块止
 * (旧脚本现 L1376–1545; 计划取证 L1517–1720)。
 *
 * ── 对账映射表(旧断言名 → 新 test 名; 旧块 add() 调用点 12 处, ok 模式主路径) ──
 *  旧 add() 行号(删块前 grep 实测)  旧断言名                                          新去向下落
 *  L808   CTX-03 选中行右键 -> 批量菜单                                → CTX-03: 选中行右键升级批量菜单
 *  L811   CTX-03 未选中行右键 -> 仍是单目标菜单                        → CTX-03: 未选中行右键仍是单目标菜单
 *  L835   CTX-03 批量菜单动作合单为一条 bulk                           → CTX-03: 批量暂停合单为一条 bulk(数请求)
 *  L843/L846(按 EXPECT_CMD 分流)                                        → 同上 test 内按 CMD_RESULT 分支:
 *         CTX-03 批量菜单失败后回滚干净 / CTX-03 批量乐观覆盖整个选中集合    error=回滚干净 / ok=乐观峰值覆盖 5 目标
 *  L1380  切到追剧视图有剧行                                           → 前行乐观(折叠态)(arrange 步 .show-row 行数断言)
 *  L1414/L1422(按 EXPECT_CMD 分流)                                      → 前行乐观(折叠态)内按 CMD_RESULT 分支:
 *         P0-3 前行乐观(失败不留假状态) / P0-3 前行乐观(剧行 is-pending)     error=不留假状态 / ok=记录器 1.5s 内出现过
 *  L1438  展开剧后有集行                                               → 集行乐观(arrange 步 .ep-row 行数断言)
 *  L1456/L1460(按 EXPECT_CMD 分流)                                      → 集行乐观内按 CMD_RESULT 分支:
 *         P0-3 整集乐观失败后回滚(集行) / P0-3 整集乐观(集行 is-pending)     error=回滚干净 / ok=记录器抓 is-pending 出现
 *  L1491  CTX-03 追剧视图: 选中多集右键 -> 批量菜单(兜底分支 L1493 同名)  → CTX-03 追剧: Ctrl 选中两集右键 -> 批量菜单
 *  L1501  切回分组视图有数据                                           → CTX-03 辅种: Ctrl 选中两组右键 -> 批量菜单
 *         (arrange 步 .group-row[data-table="group"] 行数断言 —— 旧脚本该断言只是块F 的导航落点检查)
 *  L1517/L1521(主路径/组行不足兜底, 同名)                                → CTX-03 辅种: Ctrl 选中两组右键 -> 批量菜单
 *         CTX-03 辅种视图: 选中多组右键 -> 批量菜单                          (组行不足在新轨直接红, 兜底分支不再需要)
 *  L1542  BUG-8 刷新后追剧页不空白                                     → BUG-8: 刷新后停在追剧页不空白
 *  计数口径: 旧块D·CTX-03 段 add() 4 处 + 块F add() 8 处 = 12 处(ok 模式主路径; error 模式下
 *  L843/L1414/L1456 三处换名仍 12 处) → 新 6 test/皮肤 × 2 皮肤, 1:N(合并)成立,
 *  每个旧名都有去向下落。旧收尾总检「无 console.error/pageerror」由 installRuntimeErrorGuard
 *  afterEach 承接(与块A 同款, e2e/lib/errors.mjs)。
 *
 * ── 对账实跑数字(五步对账 §5.1, 2026-10-06 S2 批实测回填) ──
 *  · 步骤2 旧脚本同参数轮(适配版): 桩 8231 --torrents 300 --ui both, W4 导出段两块
 *    (L1069–1131 多选导出 / L1133–1182 组选中导出)按任务书 2.a 临时中和后块F+CTX-03 段可达:
 *    全轮 102 项 0 失败(中和生效打印 [skip] × 4 = 双皮肤 × 两段); 对账范围内 12 个旧断言名
 *    × 2 皮肤 = 24 项全 PASS。块F 自身存量 flaky(「CTX-03 追剧视图」的集行 Ctrl+click)
 *    本轮**未复现**(双皮肤均绿, 与 smoke.md「间歇性」口径一致; 新轨侧机理已另行 trace 归因,
 *    见下节)。另跑 HEAD 版旧脚本同桩对照轮: 58 项 56 PASS / 2 FAIL, 失败仅 W4 导出段
 *    每皮肤 1 条「冒烟整体执行 — elementHandle.click: Timeout 30000ms exceeded」
 *    (中断点 = W4 组选中导出的 anchor 右键; 任务书引用的前批基线 84 项/82 PASS 数字在今日
 *    桩状态下 HEAD 也未能复现, 但**失败签名逐字一致**, 对账以同桩 HEAD 对照为准)。
 *  · 步骤1 新 spec: commands run dev.e2e 全量双皮肤 28 passed / 0 failed(本 spec 12 +
 *    views.spec 16), 实测 47s; 本 spec 单文件首跑 22.8s(12 passed)。
 *  · 步骤5 双复跑: 旧脚本(删两段 + 还原中和)50 项 48 PASS / 2 FAIL —— 失败仍仅 W4 每皮肤
 *    1 条「冒烟整体执行」, 与同桩 HEAD 对照(58/56/2)差值恰为已删 CTX-03 段 8 项, 零新增失败;
 *    新 spec 复跑 dev.e2e 28 passed / 0 failed(46.7s); npm run test:e2e:fast 4 passed(8.7s)。
 *  · 步骤3 映射自检: 旧 12 add() → 新 6 test/皮肤; 其中 3 个旧名按模式分流进同 test 的
 *    CMD_RESULT 分支(e2e 轨道模式由 env 决定, 一次运行只有一种回执形态, 不设恒红/恒真分支)。
 *
 * ── 存量 flaky 的 trace 归因(S2 交底, 修不修走 issue 流程) ──
 *  迁移首轮本 spec 曾在同一签名上红过(atlas 辅种组行右键, prism 追剧集行同族):
 *  `sticky-head`/`header.topbar`/`html` 交替拦截点击, 30s 耗尽 —— 与 smoke.md 记录的旧脚本
 *  存量 flaky 逐字同签名。--trace on 抓到机理(旧轨拿不到的时序证据, 首次):
 *  组行/集行/种子行(约 2038px)**宽于**滚动容器(约 1416px); 当动作恰与 2s 整表重渲染相撞、
 *  Chromium 的 scrollIntoViewIfNeeded 判定元素"不可见"时, 对宽于容器的元素做**居中滚动**,
 *  容器 scrollLeft 被顶到 ~(2038-1416)/2 ≈ 311px —— 行左缘落点 {x:8,y:8} 随之被滚出裁剪面,
 *  此后每次重试都重新居中, 点永远落在 html/表头上, 30s 耗尽。「间歇性」= 只在动作与重渲染
 *  相撞时触发; 旧脚本手工轮 rarely 相撞所以时红时绿。
 *  本 spec 的对冲是**测试 arrange**(非产品修复): clickRow() 先把容器横向滚回 0、把行滚到
 *  sticky 头之外的视口中部, 再从行盒现算落点并用 elementFromPoint 验落点真在行上, 然后
 *  page.mouse 点击(真实受信输入事件) —— 落点纪律(行左缘 8,8)原样保留, 且拦截发生时
 *  立即带现场报错而不是 30s 静默重试。产品侧要不要做"窗口化行宽收窄/点击落点自愈",
 *  走 issue 流程另行拍板。
 *
 * ── D4 断言翻译守则落地说明(计划 §3.5) ──
 *  · 交互真实手势: 页签/菜单项走 locator.click; 行点击(左键/修饰键/右键)走 clickRow() 的
 *    page.mouse —— 同为受信输入事件(与 locator.click 同一输入管线), 且落点可验可断言。
 *  · evaluate 保留处(均有注释): ①armPending/readPending(vm 内部时序探针, 第②类,
 *    lib/probes.mjs); ②readInst 读 vm 内部字段(selMembers/selGroups/pendingOps/viewMode/
 *    memberByHash.size —— 无 DOM 之外的取径, 第②类); ③clickRow 的滚动 arrange 与落点验证
 *    —— 滚动位置是测试环境状态而非被测行为(上面的 flaky 归因), 属"注入/复原测试态"的
 *    引申, 特此注明接受评审。
 *  · 等待语义: 旧「等乐观回落 3400/900/600ms」类 settle sleep 在"每 test 独立 context +
 *    armPending 每次新装"下不再需要跨段隔离, 相应删除; 保留的时序数字: 前行 is-pending
 *    须在 1500ms 内出现(旧 waitForFunction 同值)、批量动作后 1500ms 请求观察窗(旧同值 ——
 *    断言"逐目标误发为 0"需要确定观察窗, 不是装饰性 sleep)。
 *  · 阈值数字逐字保留: 1500(前行 pending 窗口)、乐观峰值下界 min(picked, N)、1500(请求窗)。
 *  · 桩命令泵瞬时回执 ⇒ 压暗窗口只有几十 ms, expect.poll 的 100ms 轮询会整段错过
 *    (旧脚本此处靠 rAF 频率的 waitForFunction 才采到) —— 前行/集行两处一律用记录器
 *    (armPending)判"曾经出现过", 这正是 probes.mjs 的存在理由。
 */

/** 导航页签定位器(与 views.spec 同款: tpl/topbar.html `nav.tabs [data-view]`)。 */
const tab = (page, view) => page.locator(`nav.tabs [data-view="${view}"]`);
/** 行左缘落点(smoke.md 落点纪律单点: 行本体在行盒内的偏移, 避开 .site-chip 等交互后代)。 */
const ROW_POINT = { x: 8, y: 8 };
/** 菜单项定位器(ctx 菜单是 div.ctx-item, 无 role, 按文案取)。 */
const ctxItem = (page, text) => page.locator('.ctx-item', { hasText: text });

/**
 * 行点击统一入口: 真实鼠标手势 + 落点可验(机理与取舍见文件头「存量 flaky 的 trace 归因」)。
 *
 * @param {import('@playwright/test').Page} page
 * @param {import('@playwright/test').Locator} row —— 目标行 locator(.torrent-row / .show-row /
 *        .group-row.ep-row / .group-row[data-table="group"])。
 * @param {{button?: 'left'|'right', modifiers?: Array<'Control'|'Shift'|'Alt'|'Meta'>}} [opts]
 * @returns {Promise<void>}
 */
async function clickRow(page, row, opts = {}) {
  const { button = 'left', modifiers = [] } = opts;
  /* 对冲 arrange + 落点验证, 最多 5 拍(每拍重排一次, 抗 2s 重渲染相撞)。
   * 全部在同一帧序列里完成: 滚动 arrange → 双 rAF 落定 → 量行盒 → elementFromPoint 验落点。 */
  let last = null;
  for (let attempt = 0; attempt < 5; attempt++) {
    last = await row.evaluate(async (/** @type {HTMLElement} */ el) => {
      const cont = el.closest('.group-table');
      if (cont && cont.scrollLeft !== 0) cont.scrollLeft = 0; // 居中滚动残留回零(见文件头机理)
      const head = document.querySelector('.sticky-head');
      const headBottom = head ? head.getBoundingClientRect().bottom : 0;
      let r = el.getBoundingClientRect();
      if (r.top < headBottom + 8 || r.bottom > window.innerHeight - 8) {
        el.scrollIntoView({ block: 'center', behavior: 'instant' }); // 让位 sticky 头, 停在视口中部
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
  /* 修饰键走 keyboard.down/up 包夹 mouse.click: page.mouse.click 的 options 里**没有**
   * modifiers(那是 locator.click 的选项), 裸传会被静默忽略 ⇒ 修饰键多选变成普通点击
   * (首跑实测: selGroups=0)。keyboard 状态与鼠标事件同属 CDP 输入管线, 仍是真实手势。 */
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
 * 打开首页并等首屏渲染(每 test 独立 context 的公共 arrange 前奏)。
 * @param {import('@playwright/test').Page} page
 * @param {string} skin
 */
async function openApp(page, skin) {
  collectRuntimeErrors(page);
  await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
  // 首屏数据经 /api/state 回来后才有行 —— 与 views.spec 渲染健康同口径的 boot 判据
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
}

/**
 * 断言右键菜单已打开, 返回菜单项文本数组(供"含什么/不含什么"两类断言共用)。
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<string[]>}
 */
async function openMenuTexts(page) {
  await expect(page.locator('.ctx-menu')).toBeVisible({ timeout: 5_000 });
  const texts = await page.locator('.ctx-item').allInnerTexts();
  return texts.map((t) => t.trim());
}

for (const skin of SKINS) {
  test.describe(`皮肤 ${skin}(块F + D·CTX-03: 多选与追剧)`, () => {
    installRuntimeErrorGuard(test);

    test('CTX-03: 选中行右键升级批量菜单 / 未选中行仍是单目标 / 批量暂停合单为一条 bulk', async ({ page }) => {
      await openApp(page, skin);
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 选中前 5 个**已渲染**行(行窗口化 ~26 行, 300 种子下前 5 行恒在窗口内)。
      // 真实 Ctrl+click(selection.js onTorrentClick -> toggleMemberSel), 落点纪律见文件头。
      const N = 5;
      const rows = page.locator('.torrent-row');
      for (let i = 0; i < N; i++) {
        await clickRow(page, rows.nth(i), { modifiers: ['Control'] });
      }
      // vm 内部字段读数(evaluate 第②类): 选中集合权威在 selMembers, DOM 只渲染 selected 类。
      const picked = await readInst(page, 'vm.selMembers.length');
      expect(picked, `Ctrl+click ${N} 行后选中数`).toBe(N);

      // 1. 菜单文案: 右键选中行 -> 批量菜单(CTX-03 选中行右键 -> 批量菜单, 旧 L808)
      await clickRow(page, rows.nth(0), { button: 'right' });
      let texts = await openMenuTexts(page);
      expect(texts.some((t) => t.includes('批量暂停')), `选中行右键菜单: ${texts.slice(0, 6).join(' / ')}`).toBe(true);

      // 2. 右键未选中行 -> 仍是单目标菜单(CTX-03 未选中行右键 -> 仍是单目标菜单, 旧 L811)
      await clickRow(page, rows.nth(N + 3), { button: 'right' }); // 再右键整份替换菜单, 不必先关
      texts = await openMenuTexts(page);
      expect(texts.some((t) => t.includes('暂停该种子')), `未选中行右键菜单: ${texts.slice(0, 6).join(' / ')}`).toBe(true);
      expect(texts.some((t) => t.includes('批量')), '未选中行菜单不出现批量项').toBe(false);

      // 3. 实际投递: 右键选中行 -> 点「批量暂停」-> 恰好 1 条 bulk / 0 条逐目标(旧 L835)
      const hits = { bulk: 0, single: 0 };
      const onReq = (/** @type {import('@playwright/test').Request} */ r) => {
        const u = r.url();
        if (u.includes('/api/torrents/bulk')) hits.bulk++;
        else if (/\/api\/torrents\/[^/?]+\/pause(\?|$)/.test(u)) hits.single++;
      };
      page.on('request', onReq);
      await clickRow(page, rows.nth(0), { button: 'right' });
      const item = ctxItem(page, '批量暂停');
      await expect(item).toBeVisible({ timeout: 5_000 });
      await armPending(page, '.torrent-row.is-pending, .group-row.is-pending'); // 点击**之前**装好
      await armClick(page, await item.elementHandle());
      await item.click();
      // 回执是异步流: 先等 bulk 到 1, 再给一个确定的观察窗看"逐目标误发"(旧脚本同位 1500ms)
      await expect.poll(() => hits.bulk, { message: '批量暂停应恰好 1 条 bulk POST' }).toBe(1);
      await page.waitForTimeout(1500);
      page.off('request', onReq);
      expect(hits.single, `bulk ${hits.bulk} 条之后的逐目标 pause 数`).toBe(0);

      // 4. 乐观覆盖/回滚按模式分流(旧 L846 ok / L843 error; e2e 模式由 E2E_CMD_RESULT 决定)
      const p = await readPending(page);
      if (CMD_RESULT === 'error') {
        await expect.poll(() => readInst(page, 'Object.keys(vm.pendingOps || {}).length'), {
          message: 'error 模式: pendingOps 归零(回滚)',
        }).toBe(0);
        const pendRows = await page.locator('.torrent-row.is-pending, .group-row.is-pending').count();
        expect(pendRows, 'error 模式: 残留 pending 行').toBe(0);
      } else {
        expect(p.peak, `乐观峰值 pendingOps ${p.peak} / 选中 ${picked}`).toBeGreaterThanOrEqual(Math.min(picked, N));
      }
      await page.keyboard.press('Escape'); // 收尾关菜单
      await expect(page.locator('.ctx-menu')).toHaveCount(0);
    });

    test('前行乐观(折叠态): 右键暂停整剧, 前行 1.5s 内出现 is-pending', async ({ page }) => {
      await openApp(page, skin);
      await tab(page, 'shows').click();
      // 切到追剧视图有剧行(旧 L1380: 原"epRows >= 0"恒真是 BUG-8 的教训, 这里行数必须 > 0)
      const sRows = page.locator('.show-row');
      await expect(sRows.first()).toBeVisible({ timeout: 15_000 });
      const showRowCount = await sRows.count();
      expect(showRowCount, `追剧视图剧行数(${showRowCount} 行)`).toBeGreaterThan(0);

      // 前行默认**折叠**, 集行根本不渲染 ⇒ 前行是折叠态下唯一能显示"在飞"的元素(BUG-3 教训)。
      // 必须在折叠态断言, 展开后的集行用例覆盖不到这一层。
      const sRow = sRows.first();
      const before = await sRow.getAttribute('class');
      await clickRow(page, sRow, { button: 'right' });
      const item = ctxItem(page, '暂停整剧');
      await expect(item).toBeVisible({ timeout: 5_000 });
      // 桩命令泵瞬时回执 ⇒ 压暗窗口只有几十 ms, expect.poll 的 100ms 间隔会整段错过
      // (旧脚本此处用 rAF 频率的 waitForFunction 才采到)。改用记录器: 点击**之前**装好,
      // 事后问"它**曾经**出现过吗" —— probes.mjs 的存在理由(见其头注释)。
      await armPending(page, '.show-row.is-pending');
      await armClick(page, await item.elementHandle());
      await item.click();

      if (CMD_RESULT === 'error') {
        // 失败路径: 补丁同步贴上(pendingOps > 0)→ 等回执回来归零(旧 waitForFunction 同语义),
        // 再断言类上不留 is-pending。若先断言 class 会"还没贴上就通过", 是假绿。
        await expect.poll(() => readInst(page, 'Object.keys(vm.pendingOps || {}).length'), {
          message: 'error 模式: 前行乐观补丁先贴上', timeout: 4_000,
        }).toBeGreaterThan(0);
        await expect.poll(() => readInst(page, 'Object.keys(vm.pendingOps || {}).length'), {
          message: 'error 模式: pendingOps 归零(回滚)', timeout: 4_000,
        }).toBe(0);
        const after = (await sRows.first().getAttribute('class')) || '';
        expect(after, `前行 class ${before} -> ${after}`).not.toContain('is-pending');
      } else {
        // 成功路径: 前行折叠态出现 is-pending。1.5s 窗口逐字保留(旧 waitForFunction 同值,
        // "轮询 1.5s 内出现") —— 记录器抓瞬时窗口, 这里卡上界防"补丁迟到成另一个 bug"。
        const p = await readPending(page);
        expect(p.appear, `点击 → 前行出现 pending ${p.appear === null ? '从未出现' : p.appear + 'ms'}(须 ≤1500ms)`)
          .toBeLessThanOrEqual(1_500);
        expect(p.appear, '前行折叠态出现 is-pending(旧 L1422 同口径)').not.toBeNull();
      }
    });

    test('集行乐观: 展开剧后有集行, 右键暂停整集, 集行 is-pending / error 回滚', async ({ page }) => {
      await openApp(page, skin);
      await tab(page, 'shows').click();
      await expect(page.locator('.show-row').first()).toBeVisible({ timeout: 15_000 });
      // 展开剧 -> 出集行(普通点击 = toggleShow 展开, selection.js onShowClick)
      await clickRow(page, page.locator('.show-row').first());
      const epRows = page.locator('.group-row.ep-row');
      await expect(epRows.first()).toBeVisible({ timeout: 8_000 });
      // 展开剧后有集行(旧 L1438)
      const epCount = await epRows.count();
      expect(epCount, `展开剧后集行数(${epCount} 集)`).toBeGreaterThan(0);

      // 集行状态色来自后端标量拷贝 e.state, 整集此前点了没有即时反馈(BUG-3) ——
      // 断言集行在回执前就带上 is-pending(armPending 记录器在点击**之前**装好)。
      const ep0 = epRows.first();
      const before = await ep0.getAttribute('class');
      await clickRow(page, ep0, { button: 'right' });
      // 菜单项按可用文案取: 暂停整集 / 暂停整剧(scope 决定文案, 与旧脚本同一匹配序)
      const item = ctxItem(page, '暂停整集').or(ctxItem(page, '暂停整剧'));
      await expect(item.first()).toBeVisible({ timeout: 5_000 });
      await armPending(page, '.group-row.ep-row.is-pending');
      await armClick(page, await item.first().elementHandle());
      await item.first().click();

      if (CMD_RESULT === 'error') {
        // 两段式(同前行 error 分支): 先证补丁真贴上, 再等回滚归零, 最后对 class —— 免得假绿
        await expect.poll(() => readInst(page, 'Object.keys(vm.pendingOps || {}).length'), {
          message: 'error 模式: 集行乐观补丁先贴上', timeout: 4_000,
        }).toBeGreaterThan(0);
        await expect.poll(() => readInst(page, 'Object.keys(vm.pendingOps || {}).length'), {
          message: 'error 模式: pendingOps 归零(回滚)', timeout: 4_000,
        }).toBe(0);
        const after = (await ep0.getAttribute('class')) || '';
        const beforeKind = ((before || '').split(' ').find((c) => c.startsWith('s-')) || '');
        const afterKind = ((after || '').split(' ').find((c) => c.startsWith('s-')) || '');
        expect(after, `集行 class ${before} -> ${after}`).not.toContain('is-pending');
        expect(afterKind, '回滚后状态色落回点击前').toBe(beforeKind);
      } else {
        // 判"曾经出现过"(记录器), 不判"此刻还有" —— pending 只活 100~300ms, 事后采样恒 0
        const p = await readPending(page);
        expect(p.appear, `点击 → 集行出现 pending ${p.appear === null ? '从未出现' : p.appear + 'ms'}`).not.toBeNull();
      }
    });

    test('CTX-03 追剧: Ctrl 选中两集右键 -> 批量菜单(存量 flaky 观测位)', async ({ page }) => {
      await openApp(page, skin);
      await tab(page, 'shows').click();
      await expect(page.locator('.show-row').first()).toBeVisible({ timeout: 15_000 });
      await clickRow(page, page.locator('.show-row').first()); // 展开剧出集行
      const epRows = page.locator('.group-row.ep-row');
      await expect(epRows.first()).toBeVisible({ timeout: 8_000 });
      expect(await epRows.count(), '集行至少 2 行(多选前提)').toBeGreaterThanOrEqual(2);

      // ⚠存量 flaky 所在位置(计划 §2.4 / pitfalls/testing/smoke.md): 集行 Ctrl+click 的落点
      // 被 sticky-head/header.topbar 交替拦截。机理已由本批 trace 归因(宽行居中滚动, 见文件头),
      // 对冲在 clickRow 的 arrange 里 —— 若这里仍红, 是对冲失效的新形态, 带 trace 走 issue。
      await clickRow(page, epRows.nth(0), { modifiers: ['Control'] });
      await clickRow(page, epRows.nth(1), { modifiers: ['Control'] });
      // vm 内部字段读数(evaluate 第②类): 两集的成员 hash 都进 selMembers(单元 = 整集全部版本)
      const selN = await readInst(page, 'vm.selMembers.length');
      expect(selN, `Ctrl+click 两集后 selMembers=${selN}(两集成员均入选)`).toBeGreaterThan(0);

      await clickRow(page, epRows.nth(0), { button: 'right' });
      const texts = await openMenuTexts(page);
      expect(texts.some((t) => t.includes('批量暂停')), `多选右键菜单: ${texts.slice(0, 5).join(' / ')}`).toBe(true);
      expect(texts.some((t) => t.includes('暂停整集')), '多选时不再出现单集目标项').toBe(false);
      await page.keyboard.press('Escape');
      await expect(page.locator('.ctx-menu')).toHaveCount(0);
    });

    test('CTX-03 辅种: Ctrl 选中两组右键 -> 批量菜单(切回分组视图有数据为 arrange 前置)', async ({ page }) => {
      await openApp(page, skin); // 默认落在分组视图 —— 旧"切回分组视图有数据"(L1501)的等价 arrange
      const gRows = page.locator('.group-row[data-table="group"]');
      await expect(gRows.first()).toBeVisible({ timeout: 30_000 });
      expect(await gRows.count(), '分组视图有数据(组行 > 0)').toBeGreaterThan(0);

      // 真实修饰键路径(selection.js onGroupClick -> toggleGroupSel); 落点理由见文件头
      await clickRow(page, gRows.nth(0), { modifiers: ['Control'] });
      await clickRow(page, gRows.nth(1), { modifiers: ['Control'] });
      const selN = await readInst(page, 'vm.selGroups.length');
      expect(selN, `Ctrl+click 两组后 selGroups=${selN}`).toBe(2);

      await clickRow(page, gRows.nth(0), { button: 'right' });
      const texts = await openMenuTexts(page);
      expect(texts.some((t) => t.includes('批量暂停')), `多组右键菜单: ${texts.slice(0, 5).join(' / ')}`).toBe(true);
      expect(texts.some((t) => t.includes('暂停整组')), '多选时不再出现单组目标项').toBe(false);
      await page.keyboard.press('Escape');
      await expect(page.locator('.ctx-menu')).toHaveCount(0);
    });

    test('BUG-8: 刷新后停在追剧页不空白(视图偏好持久化 x 按视图回传)', async ({ page }) => {
      // 视图偏好是持久化的(localStorage): 预置 autoqb.ui.view=shows 后刷新, 追剧页必须有行 ——
      // P1-1 按视图回传若只回 shows 而成员索引没跟上, 0 行且 rid 已记 ⇒ 自己不会恢复(BUG-8)。
      // addInitScript 在 app.js 读 localStorage 之前写入(smoke.md: 注入脚本必须赶在读之前)。
      collectRuntimeErrors(page);
      await page.addInitScript(() => localStorage.setItem('autoqb.ui.view', 'shows'));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      // 等挂载再读 vm: readInst 在 Vue mount 前会抛(_vnode 未定义), 轮询必须从挂载后起跑
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });

      // 旧脚本 reload 后固定睡 3500ms 再读; 新轨升级为轮询(语义不变: 等鉴权 + 首轮轮询落地),
      // 视图态与行数两层缺一不可: viewMode 真停在 shows 且 DOM 真渲染出剧行。
      await expect.poll(() => readInst(page, 'vm.viewMode'), {
        message: '刷新后 viewMode 停在 shows(偏好持久化)', timeout: 15_000,
      }).toBe('shows');
      await expect(page.locator('.show-row').first()).toBeVisible({ timeout: 15_000 });
      const rows = await page.locator('.show-row').count();
      expect(rows, `追剧页行数(${rows} 行)`).toBeGreaterThan(0);
      // vm 内部字段读数(evaluate 第②类): memberByHash 索引规模 —— 0 行的根因探针(索引空 ⇒ 行空)
      const idx = await readInst(page, 'vm.memberByHash.size');
      expect(idx, `成员索引规模 memberByHash.size=${idx}(为 0 即 P1-1 按视图回传又犯了)`).toBeGreaterThan(0);
    });
  });
}
