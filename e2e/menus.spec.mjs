// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { CMD_RESULT, requireMode } from './lib/mode.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst } from './lib/vm.mjs';
import { tab, ctxItem, clickRow, openApp, openMenuTexts, pickRows, bulkTap } from './lib/gestures.mjs';
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
 *  · CTX-fit(**非旧脚本迁入**, 本 spec 新增): 视口下部行开批量菜单 → 菜单盒整体落在视口内 +
 *    底部项真实可点 —— issue 26-10-06-1717 的回归断言(计划外发现的正式修复轮补)。
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
 *    → **2026-10-06 已修**(issue 26-10-06-1717): _menuPos 只留"光标处初值", 新增
 *    ui_feedback.js::_menuFit 在开层 watcher 里按**实测** offsetWidth/Height 重钳位
 *    (state.js 的 menu/headMenu/filePrio 三个 watcher 单点)。本 spec 的 CTX-fit test
 *    是它的回归断言(挑**下部行**, 与 W4 的对冲方向相反)。
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

/** /export 请求计数(W4 逐个导出口径, 旧 onReq 同款)。 */
const exportTap = (/** @type {import('@playwright/test').Page} */ page) => {
  const hits = { n: 0 };
  const onReq = (/** @type {import('@playwright/test').Request} */ r) => {
    if (/\/api\/torrents\/[^/?]+\/export(\?|$)/.test(r.url())) hits.n++;
  };
  page.on('request', onReq);
  return { hits, off: () => page.off('request', onReq) };
};

/**
 * reannounce 命令 POST 计数 + 目标 token 采集(块E「非活跃禁汇报」的行为层实证: 置灰项被点也不得
 * 发请求; 混选用例还要看"打到谁身上", 故连 URL 里的目标一起收)。
 * token 取 `/api/torrents/{token}/reannounce` 段: 投递收敛后组目标会展开为逐成员 hash(仅活跃的
 * 在列), 故正常路径 token 就是 40 位 hash —— 断言"非活跃行的 hash 不在其中"才落得住。
 */
const reannounceTap = (/** @type {import('@playwright/test').Page} */ page) => {
  const hits = { n: 0, targets: /** @type {string[]} */ ([]) };
  const onReq = (/** @type {import('@playwright/test').Request} */ r) => {
    if (r.method() !== 'POST' || !/\/reannounce(\?|$)/.test(r.url())) return;
    hits.n++;
    const m = /\/api\/(?:torrents|groups)\/([^/?]+)\/reannounce/.exec(r.url());
    if (m) hits.targets.push(decodeURIComponent(m[1]));
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
        // 上部带的由来: 取证时批量菜单 ~10 项实测 393px 高于 _menuPos 定位用的 h=222 常量估算,
        // 行在视口下部时菜单底部溢出视口、下方菜单项真实点击不可达("outside of the viewport"
        // 108 次重试耗尽), 且 stub 150 组行占满文档、下部行滚不上来。该产品侧钳位问题已于
        // 2026-10-06 修复(issue 26-10-06-1717: ui_feedback.js::_menuFit 按实测高度重钳位,
        // 回归断言 = 本 spec 的 CTX-fit test); 这里保留"挑上部行"只是让本用例少一层依赖。
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

      test('CTX-fit 视口下部行的批量菜单整份落在视口内(底部项可点)', async ({ page }) => {
        /* 回归(issue 26-10-06-1717): 钳位用常量 h=222 估算菜单高度, 批量菜单实测 ~361px ⇒
         * 锚点落在视口下部时菜单底越过下缘, 底部项(标签分类/导出/批量删除)真实点击不可达
         * (Playwright "element is outside of the viewport" 重试到超时)。修后按**实测高度**
         * 重钳位; 这里故意挑视口最下 220px 带内的行 —— 锚点 y 越低越容易溢出, 修复前必红。
         * 判据 = 几何(菜单盒整体在视口内) + 真实手势(点底部最后一项, 走 locator.click 不绕 vm)。 */
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        // 反挑**最靠下的两个**完整可见行: clickRow 对界内行不做居中滚动, 故锚点 y 可控
        // (与 W4 组选中导出那段"挑上部行"的对冲方向相反, 正是本回归的触发几何)。
        // 从末行倒着取, 行高不齐(带 H&R 的行多一行, 三皮肤 ~44/65px)也能稳定拿到底部行。
        const band = await readInst(page, `(() => {
          const out = [];
          const rows = [...document.querySelectorAll('.torrent-row')];
          for (let i = rows.length - 1; i >= 0; i--) {
            const r = rows[i].getBoundingClientRect();
            if (r.top >= window.innerHeight * 0.5 && r.bottom <= window.innerHeight - 8) {
              out.push(i);
              if (out.length >= 2) break;
            }
          }
          return out;
        })()`);
        expect(band, '视口下半带内找到两个完整可见的可右键行').toHaveLength(2);
        const picked = band.map((/** @type {number} */ i) => page.locator('.torrent-row').nth(i));
        for (const r of picked) {
          await clickRow(page, r, { modifiers: ['Control'] });
        }
        expect(await readInst(page, 'vm.selMembers.length'), 'Ctrl+click 两行后选中集合').toBe(2);
        await clickRow(page, picked[0], { button: 'right' });
        const menu = page.locator('.ctx-menu');
        await expect(menu).toBeVisible({ timeout: 5_000 });
        const vp = /** @type {{width: number, height: number}} */ (page.viewportSize());
        const b = /** @type {{x: number, y: number, width: number, height: number}} */ (await menu.boundingBox());
        expect(b, '菜单盒量不到').toBeTruthy();
        expect(Math.round(b.y + b.height),
          `菜单底 ${Math.round(b.y + b.height)} 应 ≤ 视口高 - 8(${vp.height - 8}) —— 溢出即底部项点不到`)
          .toBeLessThanOrEqual(vp.height - 8 + 1);
        expect(Math.round(b.x + b.width), `菜单右缘 ${Math.round(b.x + b.width)} 应 ≤ 视口宽 - 8`)
          .toBeLessThanOrEqual(vp.width - 8 + 1);
        // 底部最后一项走真实点击: 溢出时这里报 "outside of the viewport" 直到超时(修复前的签名)
        await ctxItem(page, '批量删除…').click();
        await expect(page.locator('.modal')).toBeVisible({ timeout: 5_000 });
        await page.keyboard.press('Escape'); // 收掉确认框(本用例只验可达性, 不提交)
        await expect(page.locator('.modal')).toHaveCount(0);
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
       * 后端 gate 的 403 双态由 pytest 兜底(tests/test_web_auth.py), 这里只管前端渲染面。 */
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

    /* 块E: 强制汇报可用性(qB 口径) —— 非活跃种子(暂停/停止·排队·校验中·错误/文件丢失)的
     * 「强制汇报」必须置灰不可用, 活跃种子照常。判据单点 = `decorate.js::reannounceMenuGate`
     * (qB commit `aa189a7` 关闭 issue #12080: isPaused/isChecking/isQueued 时置灰)。
     * 行状态用**真实 DOM 类**选(`.torrent-row` 的 `s-<kind>` 由模板绑定, 桩状态池按 8 循环
     * ⇒ 首屏窗口内恒有 s-paused 与 s-seeding/s-downloading 两种), 不借 vm 造数据;
     * 三层断言 = 置灰类 + title 给原因 + **真实点击零 reannounce 请求**(行为层闸门才是
     * "不可点"的实证 —— 置灰只改样式, 光看类名验不出绕行路径被堵住)。 */
    test.describe('块E: 强制汇报可用性(qB 口径)', () => {
      installRuntimeErrorGuard(test);

      /* @fast: 「改前端必跑」门禁(harness.mjs 头部口径)—— 本条是本专题行为层绕行路径的回归断言 */
      test('非活跃种子置灰且零请求 / 活跃种子可用 @fast', async ({ page }) => {
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        const pausedRow = page.locator('.torrent-row.s-paused').first();
        const activeRow = page.locator('.torrent-row.s-seeding, .torrent-row.s-downloading').first();
        expect(await pausedRow.count(), '首屏窗口内应有 s-paused 行(桩状态池含 pausedUP/pausedDL)').toBeGreaterThan(0);
        expect(await activeRow.count(), '首屏窗口内应有活跃行').toBeGreaterThan(0);

        await clickRow(page, pausedRow, { button: 'right' });
        const item = ctxItem(page, '强制汇报');
        await expect(item).toBeVisible({ timeout: 5_000 });
        await expect(item, '非活跃种子的强制汇报项应置灰(is-gated)').toHaveClass(/is-gated/);
        /* 原因提示读 **data-aq-tip**: 全站悬浮提示由 ui_feedback 的拦截层把 title **单向迁移**成
         * data-aq-tip 并删掉原属性(原生气泡断供式, 见其文件头) —— 页面上 `title` 早已不存在,
         * 真浏览器里只能读迁移后的落点。 */
        const tip = (await item.getAttribute('data-aq-tip')) || (await item.getAttribute('title'));
        expect(tip, '置灰项提示应给出原因(data-aq-tip)').toMatch(/无法强制汇报/);
        const { hits, off } = reannounceTap(page);
        await item.click();          // 置灰项仍可被点(样式拦显示), 行为层必须拦住
        await page.waitForTimeout(700); // 观察窗: 越过点击 -> 投递的短窗
        off();
        expect(hits.n, '非活跃种子点击强制汇报不得发出任何 reannounce 请求').toBe(0);
        await expect.poll(async () => {
          const ts = await readInst(page, "(vm.toasts || []).map((t) => t.kind + '|' + t.text)");
          return (ts || []).some((x) => x.startsWith('error|') && x.includes('无法强制汇报'));
        }, { message: '置灰项被点击后应有一条 error toast 说明原因', timeout: 5_000 }).toBe(true);

        // 活跃态对照: 同一菜单项不得置灰(判据只在非活跃目标上生效)
        await page.keyboard.press('Escape');
        await expect(page.locator('.ctx-menu')).toHaveCount(0);
        await clickRow(page, activeRow, { button: 'right' });
        const actItem = ctxItem(page, '强制汇报');
        await expect(actItem).toBeVisible({ timeout: 5_000 });
        expect(String(await actItem.getAttribute('class')), '活跃种子的强制汇报项不得置灰').not.toMatch(/is-gated/);
        await page.keyboard.press('Escape');
      });

      /* 混选(1 活跃 + 1 非活跃): 菜单按 qB 口径**放行**(oneCanForceReannounce = 任一活跃即可用),
       * 但投递必须收敛为活跃子集 —— 非活跃目标发出去 qB 引擎(libtorrent)只会静默空转, 而我们的
       * tracker 确认层会为它白等 item deadline(最长 600s)后落「未确认」, 把一次干净的成功报成
       * 部分失败(2026-10-10 投递收敛, 机理见 pitfalls/web-ui/reannounce-inactive-gate.md)。
       * 断言按 **hash** 落(不数请求条数): 选中行可能同属一组而被展开为整组成员, 条数会随分组变,
       * 但"非活跃那个没被投递"这条在任何分组形态下都必须成立。 */
      test('混选放行但只汇报活跃目标 @fast', async ({ page }) => {
        await openApp(page, skin);
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        const pausedRow = page.locator('.torrent-row.s-paused').first();
        const activeRow = page.locator('.torrent-row.s-seeding, .torrent-row.s-downloading').first();
        expect(await pausedRow.count(), '首屏窗口内应有 s-paused 行').toBeGreaterThan(0);
        expect(await activeRow.count(), '首屏窗口内应有活跃行').toBeGreaterThan(0);
        const pausedHash = await pausedRow.getAttribute('data-hash');
        const activeHash = await activeRow.getAttribute('data-hash');
        expect(pausedHash && activeHash && pausedHash !== activeHash, '两个目标必须是不同种子').toBe(true);

        await clickRow(page, pausedRow, { modifiers: ['Control'] });
        await clickRow(page, activeRow, { modifiers: ['Control'] });
        expect(await readInst(page, '(vm.selMembers || []).length'), '混选应选中 2 个种子').toBe(2);

        await clickRow(page, activeRow, { button: 'right' });
        const item = ctxItem(page, '强制汇报');
        await expect(item).toBeVisible({ timeout: 5_000 });
        expect(String(await item.getAttribute('class')), '混选含活跃目标 -> 按 qB 口径放行(不得置灰)')
          .not.toMatch(/is-gated/);

        const { hits, off } = reannounceTap(page);
        await item.click();
        await page.waitForTimeout(1200); // 观察窗: 越过点击 -> 投递的短窗
        off();
        expect(hits.targets, '活跃目标必须被投递').toContain(activeHash);
        expect(hits.targets, '非活跃目标不得被投递(混选时必须收敛掉)').not.toContain(pausedHash);
        await expect.poll(async () => {
          const ts = await readInst(page, "(vm.toasts || []).map((t) => t.text)");
          return (ts || []).some((x) => x.includes('跳过 1 个非活跃'));
        }, { message: '回执应体现被跳过的非活跃目标数(用户要看得懂"选了 2 个为什么只汇报了 1 个")',
          timeout: 8_000 }).toBe(true);
      });
    });
  });
}
