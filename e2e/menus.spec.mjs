// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { CMD_RESULT, requireMode } from './lib/mode.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst } from './lib/vm.mjs';
import { armClick, armPending, readPending } from './lib/probes.mjs';

/**
 * 菜单族 + W5-off fail-closed(S4 批, 计划 26-10-06-0708 §3.3/§04 S4) —— 承接旧单页冒烟脚本
 * (S7 退役, git 历史可查)的**块D 其余**(CTX-03 段已随 S2 迁走)+ **W5-off 精简轮**。
 * 行号为取证时点值(计划 §2.2), 已按 grep 锚点复核(2026-10-06, 删块前):
 *
 * W2 限速 grep 锚点: `W2 批量限速/移动(计划 26-10-02-1955)` 起, 至收尾清选择止
 * (删块前 L371–459; 计划取证 L1019–1070)。内含: 批量菜单两项 / W5 四项齐 / 限速载荷形状
 * (留空方向不提交) / W5 限速成功回执 toast。
 * W3 跳检 grep 锚点: `W3 批量跳检(计划 26-10-02-1955)` 起, 至收尾清选择止
 * (删块前 L462–583; 计划取证 L1114–1192)。内含: 单选/批量菜单跳检项 / 确认框取消不提交 /
 * 确认后恰好 1 条 bulk(action=skip_check)。
 * W4 导出 grep 锚点: `W4 多选导出(计划 26-10-02-1955, D1 拍板 = 前端循环逐个触发下载)` 起,
 * 至 `W4 组选中场景` 块收尾止(删块前 L586–699; 计划取证 L1235–1311)。内含: 批量菜单导出项 /
 * 多选逐个请求(数 == 选中展开数) / W5 导出成功回执 toast / 组选中展开为整组成员。
 * CTX-04/05/06 grep 锚点: `CTX-04 / CTX-05 / CTX-06 —— 右键**次级菜单**的三条` 起,
 * 至 Escape 收尾止(删块前 L702–768; 计划取证 L1338–1383)。内含: 唯一次级入口(更多操作) /
 * 复制族并入 / 悬停父项时子面板图标仍是语义色 / 移出父项后子面板收起。
 * W5-off grep 锚点: `跳检菜单旗标「关」态精简轮(W5 汇总, 计划 26-10-02-1955)` 的
 * skipCheckOffChecks 函数(删块前 L132–190)+ smokeUi 内 `SKIP_CHECK === "off"` 早退分支
 * (删块前 L216–223; 计划取证 L233–271)。
 *
 * 模式门控(计划 §3.2 D1): 与旧脚本同构 —— 主路径组只在 skip-check **on** 跑(那些断言假定
 * flags 开, 关态下 W3「菜单含跳检项」会假红, 旧脚本 off 轮同款早退互斥); W5-off 精简组只在
 * **off** 跑, requireMode 按当前 env 整组跳过, skip 消息带当前值。另: W3 确认链限 ok|error
 * (确认钮靠预检回执解锁, hang 下预检不回执永不解锁, 见映射表 L572 行注)。
 *
 * ── 对账映射表(旧断言名 → 新 test 名) ──
 *  on 轮(块D 其余, 旧 add() 16 处/皮肤 → 新 7 test/皮肤):
 *  旧 add() 行号(删块前 grep 实测)  旧断言名                                       新去向下落
 *  L399  W2 批量菜单含限速/移动两项                                 → W2/W5 多选菜单: 两项 + 四项齐
 *  L404  W5 多选菜单四项齐(限速/移动/跳检/导出)                     → 同上(1:N 合并, 同一菜单快照)
 *  L437  W2 批量限速载荷形状(留空方向不提交)                        → W2 批量限速: 载荷形状 + toast
 *  L450  W5 批量限速成功回执 toast                                  → 同上 test 的 ok 分支 —— 旧 error
 *          轮该项恒红系存量假红(成功 toast 在 --cmd-result error 下不存在,
 *          S3 对账实测), 新轨修掉: 该断言只在 CMD_RESULT==='ok' 跑
 *  L494  W3 单选菜单含跳检项(flags 开)                              → W3 跳检菜单项: 单选 + 批量
 *  L507  W3 批量菜单含跳检项(flags 开)                              → 同上(1:N 合并)
 *  L535  W3 跳检确认框取消不提交                                    → W3 跳检确认链: 取消 / 确认提交
 *  L572  W3 跳检确认后提交 bulk(action=skip_check)                  → 同上(1:N 合并) —— S7 矩阵
 *          hang 轮实测该 test 需限 ok|error(确认钮靠预检回执解锁, hang 下
 *          永不解锁 ⇒ click 超时), 已补 requireMode 门控(2026-10-06)
 *  L615  W4 批量菜单含导出项                                        → W4 多选导出(arrange 步菜单断言)
 *  L632  W4 多选导出逐个请求(数 == 选中展开数)                      → 同上(升级为 poll 到 N)
 *  L645  W5 导出成功回执 toast                                      → 同上 test 尾段 —— exportMulti 走
 *          裸 fetch 不经命令泵, ok/error 两模式都出 toast(旧 error 轮实测
 *          本来就绿), 故**不**按模式门控, 与旧存量行为一致
 *  L691  W4 组选中导出展开为整组成员                                → W4 组选中导出(selHashSet 全量展开)
 *  L726  CTX-06 一级只有一个次级菜单入口(更多操作)                  → CTX-04/05/06 次级菜单四合一
 *  L735  CTX-06 复制族并入「更多操作」                              → 同上
 *  L753  CTX-04 悬停父项时子面板图标仍是语义色(不变灰)             → 同上
 *  L763  CTX-05 移出父项后子面板收起                                → 同上
 *  L781  顶栏三视图按钮存在                                          → **不迁移**: S2 删块F 残留的悬空
 *          add(ok=false 恒红, 计划内清除项), 本批随删块一并删除
 *  旧「页面上没有 .torrent-row 可右键」兜底分支(L718)不迁移 —— 新轨定位器拿不到行直接红。
 *  off 轮(W5-off 精简组, 旧 add() 4 处/皮肤 → 新 3 test/皮肤 + 守卫):
 *  L146  W5 off: flags 取到 skip_check_menu=false(fail-closed)      → W5 off: flags=false
 *  L158  W5 off: 单选/多选菜单无跳检项(无行兜底, 恒 false 分支)     → 不迁移(同上理由)
 *  L164  W5 off: 单选菜单不渲染跳检项(限速仍在)                     → W5 off: 单选菜单
 *  L184  W5 off: 多选菜单不渲染跳检项(限速/移动/导出照常)           → W5 off: 多选菜单
 *  L220  无 console.error / pageerror(off 轮收尾总检)               → installRuntimeErrorGuard
 *  旧多选注入(vm.selMembers = …)在旧块里是取"已知选中集合"的手段; 新轨一律真实 Ctrl+click
 *  (D4 守则: 有真实 UI 路径的交互不借道 vm), 选中集合用 readInst 读数自证(第②类)。
 *
 * ── 对账实跑数字(五步对账 §5.1 × on/off 双轮, 2026-10-06 S4 批实测回填) ──
 *  · 步骤1 新 spec: 默认(on) commands run dev.e2e 全量 56 passed / 8 skipped(1.2m; 本 spec
 *    14 passed + off 组 6 skipped + hang 组 2 skipped, skip 消息可读); off 轮
 *    E2E_SKIP_CHECK=off commands run dev.e2e 全量 48 passed / 16 skipped(54.3s; 本 spec
 *    off 组 6 passed + on 组 14 skipped)。本 spec 单文件首跑 23.2s(14 passed / 6 skipped)。
 *  · 步骤2 旧脚本同参数轮(适配版): 桩 8232(off)/8233(on)/8234(error) --torrents 300 --ui both。
 *    两处临时对账脚手架(仅工作树, 已随删段一并消失, grep「临时对账脚手架」零残留):
 *    ①W4 导出段两块中和(存量 elementHandle.click 30s 超时会中断该皮肤整段, 让其后段可达);
 *    ②W2 的 armClick 依赖块C 的 armPending 预置 window.__p, S3 删块C 后前置消失 ⇒ 点击时
 *    pageerror「Cannot set properties of undefined (setting 't0')」污染收尾总检(此前被 W4
 *    超时掩盖), 适配按块C 原样预置 __p:
 *    - on 轮:  58 项 56 PASS / 2 FAIL —— 失败仅「顶栏三视图按钮存在」×2(S2 删块残留的悬空
 *      add, ok=false 恒红, 本批计划内删除); 对账范围内块D 其余 12 断言名 ×2 皮肤全 PASS。
 *    - off 轮: 8 项(--skip-check off 精简轮)全 PASS。
 *    - error 轮: 58 项 54 PASS / 4 FAIL —— 上两项之外「W5 批量限速成功回执 toast」×2 恒红
 *      (存量假红: 成功 toast 在 --cmd-result error 下不存在; 对照组: W4 导出 toast 走裸
 *      fetch 不经命令泵, error 下本来就绿)。新轨据此把限速 toast 断言门控到 ok 模式
 *      (修掉旧假红), 导出 toast 不门控(与旧存量行为一致)。
 *  · 步骤3 对账映射: 见上表 —— on 16 旧名/皮肤 → 7 test/皮肤(1:N 合并, 每个旧名有去向下落),
 *    off 4 旧名/皮肤 → 3 test/皮肤 + installRuntimeErrorGuard; 悬空 add 不迁移(删除)。
 *  · 步骤4 删旧块(与本 spec 同 commit): 旧脚本删块D 其余段 + W5-off 轮
 *    (skipCheckOffChecks + 早退分支 + SKIP_CHECK 参数/头注释)+ 探针三件退役
 *    (armPending/armClick/readPending, 零调用方)+ 悬空 add 一行, 净 28+/504-, node --check 过。
 *  · 步骤5 双复跑: 旧脚本(删段后, 同桩 8233)on 轮 32 项 0 FAIL —— 失败不增反清零: 任务书
 *    预期「仍仅 W4 存量 2 项」随 W4 段删除不再适用, 原 W4 存量超时/悬空 add/armClick
 *    pageerror 三类失败全部随所删段离开; 余下段(块B/设置/HR/列设置)在中和轮已证全绿。
 *    新 spec on/off 复跑绿(数字同步骤1); E2E_CMD_RESULT=error 抽验本 spec 14 passed /
 *    6 skipped(23.4s, 无恒红); npm run test:e2e:fast 4 passed(7.6s)不变。
 *  · 计划外发现(记录不修, 修不修走 issue 流程): ui_feedback.js 的 _menuPos(event, w=214,
 *    h=222) 以常量 h=222 估算菜单高度做视口钳位, 批量菜单 ~10 项实测 361px —— 行在视口
 *    下部时右键, 菜单底部溢出视口, 下方项(移动/标签分类/导出/批量删除)真实点击不可达
 *    (Playwright "outside of the viewport" 108 次重试耗尽; stub 150 组行占满文档时下部行
 *    滚不上来, 无 arrange 可解)。旧脚本 W4-组选中块的存量 elementHandle.click 超时使该
 *    问题从未暴露。本 spec 用「挑视口上部行」的 arrange 对冲(W4 组选中用例)。
 *
 * ── D4 断言翻译守则落地说明(计划 §3.5) ──
 *  · 交互真实手势: 页签/菜单项/对话框按钮走 locator.click; 行点击(左键/修饰键/右键)走
 *    clickRow() 的 page.mouse —— 对冲写法沿用 multiselect-shows.spec(宽行居中滚动把行左缘
 *    落点滚出裁剪面的 flaky 机理与 5 拍 arrange, 见该文件头)。
 *  · evaluate 保留处(均有注释): ①readInst 读 vm 内部字段(selMembers/selGroups/selHashSet/
 *    decoratedGroups/toasts —— 无 DOM 之外的取径, 第②类); ②CTX-04 色探针在页面内比对
 *    var(--teal)/var(--fg-muted) 的 computed 解析值(对照 smoke.md Dark Reader 纪律: 颜色
 *    断言读自定义属性的解析结果, 不读裸 computed 背景); ③W2 的 armPending+armClick 按
 *    旧 W2 用法原样移植(第②类时序探针; 旧脚本本段只钉 t0 不消费 —— 限速走 bulk 合单
 *    无乐观贴片, 保持同口径不新增断言)。
 *  · 阈值/语义性 sleep 逐字保留: CTX-05 移出后等 450ms 再看(收起延迟 ~180ms, 等待即断言);
 *    W2/W4 toast 轮询上限 5s(旧 deadline 同值); W3 取消后 600ms 零 POST 观察窗(旧 400ms
 *    同款语义, 略放余量)、确认后 poll 到 1 再加 500ms 观察窗看"无误发"(旧 1200ms 等回执
 *    同语义); W5-off flags 轮询 10s(旧 waitForFunction 同值)。
 *  · 每 test 独立 context ⇒ 旧脚本跨块 settle sleep(等 3s 兜底窗口过/清选择/关弹层)不再需要。
 */

/** 导航页签定位器(tpl/topbar.html `nav.tabs [data-view]`)。 */
const tab = (page, view) => page.locator(`nav.tabs [data-view="${view}"]`);
/** 菜单项定位器(ctx 菜单是 div.ctx-item, 无 role, 按文案取)。 */
const ctxItem = (page, text) => page.locator('.ctx-item', { hasText: text });

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
  /* 修饰键走 keyboard.down/up 包夹 mouse.click(page.mouse.click 的 options 没有 modifiers,
   * 裸传会被静默忽略 —— multiselect-shows.spec 首跑实测), 仍是 CDP 输入管线的真实手势。 */
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
 * 打开首页并等首屏渲染(每 test 独立 context 的公共 arrange 前奏, 与既有 spec 同款)。
 * @param {import('@playwright/test').Page} page
 * @param {string} skin
 */
async function openApp(page, skin) {
  collectRuntimeErrors(page);
  await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
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

/**
 * Ctrl+click 选中前 N 个已渲染行(行窗口化 ~26 行, 300 种子下前 N 行恒在窗口内),
 * 返回选中集合权威读数(vm.selMembers, evaluate 第②类)。
 * @param {import('@playwright/test').Page} page
 * @param {number} n
 * @returns {Promise<string[]>}
 */
async function pickRows(page, n) {
  const rows = page.locator('.torrent-row');
  for (let i = 0; i < n; i++) {
    await clickRow(page, rows.nth(i), { modifiers: ['Control'] });
  }
  const picked = await readInst(page, 'vm.selMembers.slice()');
  expect(picked, `Ctrl+click ${n} 行后选中集合(selMembers)`).toHaveLength(n);
  return /** @type {string[]} */ (picked);
}

/** bulk POST 计数 + 末条载荷捕获(W2/W3 载荷形状断言共用口径)。 */
const bulkTap = (/** @type {import('@playwright/test').Page} */ page) => {
  const hits = { n: 0, body: /** @type {string|null} */ (null) };
  const onReq = (/** @type {import('@playwright/test').Request} */ r) => {
    if (r.url().includes('/api/torrents/bulk')) { hits.n++; hits.body = r.postData(); }
  };
  page.on('request', onReq);
  return { hits, off: () => page.off('request', onReq) };
};

/** /export 请求计数(W4 逐个导出口径, 旧 onReq 同款)。 */
const exportTap = (/** @type {import('@playwright/test').Page} */ page) => {
  const hits = { n: 0 };
  const onReq = (/** @type {import('@playwright/test').Request} */ r) => {
    if (/\/api\/torrents\/[^/?]+\/export(\?|$)/.test(r.url())) hits.n++;
  };
  page.on('request', onReq);
  return { hits, off: () => page.off('request', onReq) };
};

for (const skin of SKINS) {
  test.describe(`皮肤 ${skin}(块D: 菜单族 + W5-off)`, () => {
    test.describe('块D 主路径(W2/W3/W4/CTX, skip-check on)', () => {
      /* 与旧脚本 off 轮早退同款互斥: 主路径断言假定 flags 开, 关态下 W3 会假红 */
      requireMode(test, { skipCheck: 'on' });
      installRuntimeErrorGuard(test);

      test('W2/W5 多选菜单: 含限速/移动两项 + 四项齐(限速/移动/跳检/导出)', async ({ page }) => {
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        const N = 3;
        await pickRows(page, N);
        await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
        const texts = await openMenuTexts(page);
        // W2: 批量菜单含限速/移动两项(排序从宽, 只要求同时出现 —— 旧同口径)
        expect(texts.some((t) => t.includes('限速…')) && texts.some((t) => t.includes('移动…')),
          `批量菜单: ${texts.slice(0, 8).join(' / ')}`).toBe(true);
        // W5 汇总: 四项齐 —— 专抓"加了新项挤掉旧项"这类汇总遗漏(旧收录口径同款)
        expect(['限速…', '移动…', '跳检…', '导出 .torrent'].every((k) => texts.some((t) => t.includes(k))),
          `四项齐: ${texts.join(' / ')}`).toBe(true);
        await page.keyboard.press('Escape');
      });

      test('W2 批量限速: 载荷形状(留空方向不提交) + 成功回执 toast(仅 ok 模式)', async ({ page }) => {
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        const N = 3;
        const picked = await pickRows(page, N);
        await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
        const item = ctxItem(page, '限速…');
        await expect(item).toBeVisible({ timeout: 5_000 });
        const { hits, off } = bulkTap(page);
        // 旧 W2 用法原样移植(第②类时序探针): armClick 依赖 armPending 预置的 window.__p;
        // 旧脚本本段只钉 t0 不消费时序(限速走 bulk 合单、无乐观贴片), 同口径不新增断言。
        await armPending(page);
        await armClick(page, await item.elementHandle());
        await item.click();
        await expect(page.locator('.modal')).toBeVisible({ timeout: 5_000 });
        const inputs = page.locator('.modal-fields input');
        expect(await inputs.count(), '限速对话框双输入(上传/下载)').toBe(2);
        await inputs.nth(0).fill('1024'); // 上传 1024 KiB/s; 下载留空 = 不提交该项(D3)
        await page.locator('.modal-actions .bt.primary').click();
        await expect.poll(() => hits.n, { message: '批量限速应发出恰好 1 条 bulk POST', timeout: 8_000 }).toBe(1);
        await page.waitForTimeout(500); // 观察窗: 确认没有第二条(旧 W3 同款"恰好 1 条"语义)
        off();
        expect(hits.n, `选中 ${N} 个 → bulk ${hits.n} 条`).toBe(1);
        const posted = JSON.parse(/** @type {string} */ (hits.body));
        expect(posted.action, `载荷: ${JSON.stringify(posted).slice(0, 140)}`).toBe('limits');
        expect(posted.up_limit, '上传 1024 KiB/s → 1024*1024 bytes/s').toBe(1024 * 1024);
        expect('dl_limit' in posted, '留空方向不提交(dl_limit 键不出现)').toBe(false);
        expect([...posted.hashes].sort(), 'hashes 覆盖整个选中集合').toEqual([...picked].sort());

        if (CMD_RESULT === 'ok') {
          // 成功回执 toast 只在 ok 模式断言 —— error 桩下 waitCmd 回错误, 成功 toast 不存在
          // (旧 error 轮该项恒红系存量假红, S3 对账实测; 新轨按"该断言只该在 ok 模式跑"修掉)
          await expect.poll(async () => {
            const ts = await readInst(page, "(vm.toasts || []).map((t) => t.kind + '|' + t.text)");
            return (ts || []).includes(`ok|已执行: 批量限速(${N} 个目标)`);
          }, { message: `W5 成功回执 toast「已执行: 批量限速(${N} 个目标)」`, timeout: 5_000 }).toBe(true);
        }
        await readPending(page); // 收口: 清掉 armPending 的 10ms 采样器(与本 test 装的记录器配对)
      });

      test('W3 跳检菜单项(flags 开): 单选菜单 + 批量菜单都含跳检', async ({ page }) => {
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        const N = 3;
        await pickRows(page, N); // 先选中(后面批量菜单要用), 单选菜单右键未选中行不受影响
        // 单选: 右键未选中行(= 单目标菜单); 之后再右键选中锚点会整份替换菜单, 不会串台(旧同序)
        await clickRow(page, page.locator('.torrent-row').nth(N + 3), { button: 'right' });
        let texts = await openMenuTexts(page);
        expect(texts.some((t) => t.includes('跳检…')), `单选菜单: ${texts.slice(0, 10).join(' / ')}`).toBe(true);
        // 批量: 右键选中锚点(重新校验之后、限速/移动之前, 从宽只要求出现 —— 旧同口径)
        await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
        texts = await openMenuTexts(page);
        expect(texts.some((t) => t.includes('跳检…')), `批量菜单: ${texts.slice(0, 9).join(' / ')}`).toBe(true);
        await page.keyboard.press('Escape');
      });

      test('W3 跳检确认链: 取消不提交 / 确认恰好 1 条 bulk(action=skip_check)(ok|error 模式)', async ({ page }) => {
        // hang 模式整条跳过(S7 矩阵轮 2026-10-06 实测补, 基线 26-10-06-1425): 确认按钮由
        // S4 跳检预检回执解锁(:disabled="modal.okDisabled", tpl/popovers.html), hang 下预检
        // 永不回执 ⇒ 按钮恒 disabled ⇒ click 必 30s 超时; error 模式预检有回执照常解锁
        // (矩阵 error 轮实测 0 failed), 故按 W2 toast「仅 ok 模式」同款口径限 ok|error。
        requireMode(test, { cmdResult: ['ok', 'error'] });
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        const N = 3;
        await pickRows(page, N);
        const { hits, off } = bulkTap(page);
        // 1. 取消: 点「跳检…」→ danger 确认框 → 点「取消」→ 零 bulk POST
        await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
        await ctxItem(page, '跳检…').click();
        await expect(page.locator('.modal')).toBeVisible({ timeout: 5_000 });
        await expect(page.locator('.modal-title')).toContainText('批量跳检');
        await page.locator('.modal-actions .bt.ghost').click(); // 取消
        await page.waitForTimeout(600); // 旧 400ms 同款观察窗: 取消后不该有 POST
        expect(hits.n, `取消后 bulk POST ${hits.n} 条`).toBe(0);
        // 选择未清(取消不提交也不清选) —— 旧脚本按 selMembers 现找锚点的同款自证
        expect(await readInst(page, 'vm.selMembers.length'), '取消后选择保持').toBe(N);
        // 2. 确认: 再走一遍 → 点「跳检」(danger-solid) → 恰好 1 条 bulk(action=skip_check)
        await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
        await ctxItem(page, '跳检…').click();
        await expect(page.locator('.modal')).toBeVisible({ timeout: 5_000 });
        await page.locator('.modal-actions .bt.danger-solid').click();
        await expect.poll(() => hits.n, { message: '确认后应恰好 1 条 bulk POST', timeout: 8_000 }).toBe(1);
        await page.waitForTimeout(500); // 观察窗: 确认没有误发第二条(旧 1200ms 等回执同语义)
        off();
        expect(hits.n, `确认后 bulk POST ${hits.n} 条`).toBe(1);
        const posted = JSON.parse(/** @type {string} */ (hits.body));
        expect(posted.action, `载荷: ${JSON.stringify(posted).slice(0, 140)}`).toBe('skip_check');
        expect(posted.hashes, '目标 = 选中集合').toHaveLength(N);
      });

      test('W4 多选导出: 逐个请求(数 == 选中展开数) + 成功回执 toast', async ({ page }) => {
        test.setTimeout(60_000); // 串行逐个 fetch, 组大时慢(旧 1.2s 等待的框架化等价)
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        const N = 3;
        await pickRows(page, N);
        await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
        const texts = await openMenuTexts(page);
        expect(texts.some((t) => t.includes('导出 .torrent')), `批量菜单: ${texts.slice(0, 11).join(' / ')}`).toBe(true);
        const { hits, off } = exportTap(page);
        await ctxItem(page, '导出 .torrent').click();
        // 串行也全都会发: poll 到 N(旧固定等 1200ms 后断言 == N 的框架化等价)
        await expect.poll(() => hits.n, { message: `导出应对选中 ${N} 个逐个发请求(无 bulk 合单)`, timeout: 10_000 }).toBe(N);
        off();
        expect(hits.n, `选中 ${N} 个 → 导出请求 ${hits.n} 个(期望 ${N})`).toBe(N);
        // exportMulti 走裸 fetch 不经命令泵, ok/error 两模式都出成功 toast(旧 error 轮本来就绿)
        await expect.poll(async () => {
          const ts = await readInst(page, "(vm.toasts || []).map((t) => t.kind + '|' + t.text)");
          return (ts || []).includes(`ok|已导出 ${N} 个 .torrent`);
        }, { message: `W5 导出成功回执 toast「已导出 ${N} 个 .torrent」`, timeout: 5_000 }).toBe(true);
      });

      test('W4 组选中导出: 展开为整组成员(selHashSet 全量, 请求数 == 成员数)', async ({ page }) => {
        test.setTimeout(60_000); // 整组成员串行导出, 组大时慢
        await openApp(page, skin); // 默认分组视图
        const gRows = page.locator('.group-row[data-table="group"]');
        await expect(gRows.first()).toBeVisible({ timeout: 30_000 });
        // 反挑两个**已渲染且在视口上部**的实体组(行窗口化, 不假设排序; 只选 1 组时
        // _ctxMulti 的"范围一致"判定会降级单目标菜单 —— 旧注释同款, 必须选 2 组)。
        // 上部带的理由: 批量菜单 ~10 项(实测 361px)高于 _menuPos 定位用的 h=222 常量估算
        // (ui_feedback.js), 行在视口下部时菜单底部溢出视口、下方菜单项(移动/标签分类/导出/
        // 批量删除)真实点击不可达 —— 首轮实测 "outside of the viewport" 108 次重试耗尽;
        // 且 stub 数据 150 组行占满文档, 下部行滚不上来(文档到底)。该产品侧钳位问题走
        // issue 流程, 这里用"挑上部行"的 arrange 对冲(与 clickRow 内部滚动同类,
        // multiselect-shows 头注口径), 右键点 ~y150 处菜单整份在屏内。
        const keys = await readInst(page, `(() => {
          const ok = new Set(vm.decoratedGroups
            .filter((g) => !g.virtual && (g.members || []).length).map((g) => g.key));
          const head = document.querySelector('.sticky-head');
          const min = (head ? head.getBoundingClientRect().bottom : 0) + 12;
          const out = [];
          for (const el of document.querySelectorAll('.group-row[data-table="group"]')) {
            const k = el.getAttribute('data-key');
            const r = el.getBoundingClientRect();
            if (ok.has(k) && r.top >= min && r.bottom <= 500) { out.push(k); if (out.length >= 2) break; }
          }
          return out;
        })()`);
        expect(keys, '视口上部找到两个可选的实体组').toHaveLength(2);
        const pickedRows = /** @type {string[]} */ (keys)
          .map((k) => page.locator(`.group-row[data-table="group"][data-key="${k}"]`));
        for (const r of pickedRows) {
          await clickRow(page, r, { modifiers: ['Control'] });
        }
        expect(await readInst(page, 'vm.selGroups.length'), 'Ctrl+click 两组后 selGroups').toBe(2);
        const ginfo = await readInst(page, `(() => {
          const sel = new Set(vm.selGroups);
          const gs = vm.decoratedGroups.filter((g) => sel.has(g.key));
          return { members: gs.reduce((n, g) => n + (g.members || []).length, 0), expanded: vm.selHashSet.size };
        })()`);
        expect(ginfo.expanded, `selHashSet 全量展开(${ginfo.expanded}) == 成员数(${ginfo.members})`)
          .toBe(ginfo.members);
        // 右键**选中**的组行(右键未选中组行会降级单目标菜单, 导出数就不对)
        await clickRow(page, pickedRows[0], { button: 'right' });
        const item = ctxItem(page, '导出 .torrent');
        await expect(item).toBeVisible({ timeout: 5_000 });
        const { hits, off } = exportTap(page);
        await item.click();
        await expect.poll(() => hits.n, {
          message: `组选中导出应展开为整组成员(${ginfo.members} 个请求)`, timeout: 15_000,
        }).toBe(ginfo.expanded);
        off();
        expect(hits.n, `2 组 ${ginfo.members} 成员 → 导出请求 ${hits.n} 个`).toBe(ginfo.expanded);
      });

      test('CTX-04/05/06 次级菜单: 唯一入口(更多操作) / 复制族并入 / 悬停语义色不变灰 / 移出收起', async ({ page }) => {
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
        await expect(page.locator('.ctx-menu')).toBeVisible({ timeout: 5_000 });
        // CTX-06: 一级只允许一个次级菜单入口(复制族曾单列第二个子面板)
        const subs = page.locator('.ctx-menu > .ctx-item.has-sub');
        expect(await subs.count(), '一级 has-sub 恰好 1 个').toBe(1);
        await expect(subs.first()).toContainText('更多操作');
        // 展开子面板(hover 父项 —— 与用户路径一致)
        await subs.first().hover();
        await expect(page.locator('.ctx-sub')).toBeVisible({ timeout: 3_000 });
        const panel = ((await page.locator('.ctx-sub').textContent()) || '').replace(/\s+/g, ' ');
        for (const t of ['复制名称', '复制哈希', '复制 magnet']) {
          expect(panel, `复制族并入「更多操作」面板: ${panel.slice(0, 90)}`).toContain(t);
        }
        // CTX-04: `.ctx-item:hover .ico` 是后代选择器, 而 .ctx-sub 是父项的 DOM 后代 ⇒ hover
        // 父项会把整个子面板图标刷成 --fg-muted(修之前的恒红形态)。判据: 悬停父项时子面板
        // 首项图标(.ico-queue)的 computed color 仍是语义色(--teal)。页面内比对 var() 的解析值
        // (smoke.md Dark Reader 纪律: 颜色断言读自定义属性解析结果; evaluate 第②类读数)。
        const probe = await page.evaluate(`(() => {
          const el = document.querySelector(".ctx-sub .ico-queue");
          if (!el) return null;
          const mk = (v) => { const s = document.createElement("span"); s.style.color = v; document.body.appendChild(s); return s; };
          const muted = mk("var(--fg-muted)"), teal = mk("var(--teal)");
          const out = {
            icon: getComputedStyle(el).color,
            muted: getComputedStyle(muted).color,
            teal: getComputedStyle(teal).color,
          };
          muted.remove(); teal.remove();
          return out;
        })()`);
        expect(probe, '子面板没展开, 读不到图标').toBeTruthy();
        expect(/** @type {{icon: string, teal: string, muted: string}} */ (probe).icon,
          `图标 ${probe && probe.icon} / 语义色(--teal) ${probe && probe.teal} / 灰(--fg-muted) ${probe && probe.muted}`)
          .toBe(/** @type {{icon: string, teal: string}} */ (probe).teal);
        expect(/** @type {{icon: string, muted: string}} */ (probe).icon).not.toBe(/** @type {{muted: string}} */ (probe).muted);
        // CTX-05: 只有 mouseenter 展开、没有任何收起 ⇒ 子面板会一直挂在屏幕上(修前形态)。
        // hover 到另一个一级项 → 450ms 后 .ctx-sub 必须为 0(收起延迟 ~180ms, 等 450ms 是断言语义)
        await page.locator('.ctx-menu > .ctx-item').first().hover();
        await page.waitForTimeout(450);
        await expect(page.locator('.ctx-sub')).toHaveCount(0);
        await page.keyboard.press('Escape'); // 收尾关菜单
        await expect(page.locator('.ctx-menu')).toHaveCount(0);
      });
    });

    test.describe('W5 off: fail-closed 门控精简组(skip-check off)', () => {
      /* 桩 --skip-check-menu off 起盘, 走真实 /api/webui/flags -> state.flags -> v-if 链。
       * 与旧脚本 off 轮同构: 只验门控, 主路径那些"菜单含跳检项"断言在关态下会假红故整组跳过。
       * 后端 gate 的 403 双态由 pytest 兜底(test_web.py), 这里只管前端渲染面。 */
      requireMode(test, { skipCheck: 'off' });
      installRuntimeErrorGuard(test);

      test('W5 off: flags 取到 skip_check_menu=false(fail-closed)', async ({ page }) => {
        await openApp(page, skin);
        // 必须是**布尔 false**(不是"没取到"的 undefined 形态 —— v-if 对 undefined 也隐藏,
        // 那是端点断链另一档故障, 会被误判成门控生效; 旧注释同款)
        await expect.poll(() => readInst(page, 'vm.flags ? vm.flags.skip_check_menu : null'), {
          message: 'flags.skip_check_menu 应为布尔 false(fail-closed)', timeout: 10_000,
        }).toBe(false);
      });

      test('W5 off: 单选菜单不渲染跳检项(限速仍在)', async ({ page }) => {
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        // 单选: 不选中任何行直接右键
        await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
        const texts = await openMenuTexts(page);
        expect(texts.some((t) => t.includes('限速…')), `单选菜单: ${texts.slice(0, 10).join(' / ')}`).toBe(true);
        expect(texts.some((t) => t.includes('跳检…')), '关态单选菜单不得渲染跳检项').toBe(false);
        await page.keyboard.press('Escape');
      });

      test('W5 off: 多选菜单不渲染跳检项(限速/移动/导出照常)', async ({ page }) => {
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        await pickRows(page, 3); // 门控只藏高危项: 多选菜单其余三项必须照常
        await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
        const texts = await openMenuTexts(page);
        expect(['限速…', '移动…', '导出 .torrent'].every((k) => texts.some((t) => t.includes(k))),
          `多选菜单: ${texts.slice(0, 11).join(' / ')}`).toBe(true);
        expect(texts.some((t) => t.includes('跳检…')), '关态多选菜单不得渲染跳检项').toBe(false);
        await page.keyboard.press('Escape');
      });
    });
  });
}
