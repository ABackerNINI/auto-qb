// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS, TORRENTS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst } from './lib/vm.mjs';

/**
 * 视图与渲染健康(S1 批, 计划 26-10-06-0708 §3.3/§3.5 D3) —— 承接旧单页冒烟脚本(2026-10-06
 * S7 退役, git 历史可查)的**块A**(L288–470, 取证时点值; grep 锚点: `smokeUi(browser, ui)` 起到
 * "轮询间隔按种子量分档"断言止), 并入原 smoke.spec.mjs 的 2 条 @fast(壳文件退役, P4 拍板:
 * 渲染健康断言从此单点)。
 *
 * 块A grep 锚点: `展开态跨视图记忆` / `导航焦点不变式` / `三视图切换(P1-1` /
 * `种子页筛选器必须有数据` / `轮询分档(P1 之后的收尾一步)`。
 *
 * ── 对账映射表(旧断言名 → 新 test 名; 旧脚本 ok 模式主路径块A add() 调用点 13 处, 见下行) ──
 *  旧 add() 行号(取证 26-10-06)  旧断言名                                        新去向下落
 *  L305   分组视图渲染                                          → 渲染健康 @fast(.group-row 可见 = 行数 > 0)
 *  L329   展开态跨视图: 取到组行                                 → 展开态跨视图记忆(arrange 步的 data-key 前置断言)
 *  L336   展开分组: 明细面板出现                                 → 展开态跨视图记忆(.detail 可见 + expandedKey 同步断言)
 *  L341   切到种子视图: 展开态不串台(实时字段清空)                → 展开态跨视图记忆(expect.poll expandedKey → null)
 *  L346   切回辅种视图: 展开的组还在(跨视图记忆)                  → 展开态跨视图记忆(.detail 可见 + expandedKey 还原)
 *  L372   导航焦点: 鼠标点页签持焦且无焦点框                      → 导航焦点(前半段)
 *  L382   导航焦点: 键盘切页后旧页签不残留焦点框(L387 为同名的     → 导航焦点(后半段; 页签缺失分支不再需要 ——
 *         元素不足兜底)                                            Playwright 拿不到定位器会直接红, 语义等价)
 *  L398   切到种子视图有数据                                     → 种子视图(DOM 行 > 0 且 ≤ 数据)
 *  L399   种子总数与桩服务一致(EXPECT_N 给定时)                   → 种子视图(filteredTorrents.length === TORRENTS;
 *                                                                  e2e 轨道 TORRENTS 恒有值, 无旧脚本的缺省分支)
 *  L401   单轮 renderMs 埋点可读                                 → 种子视图
 *  L414   状态栏速度 = 服务端 totals(种子页不回 groups 也要对)     → 状态栏速度 = 服务端 totals
 *  L448   种子页筛选器有数据(计数=种子数)                         → 种子页筛选器有数据(计数=种子数)
 *  L464   轮询间隔按种子量分档(EXPECT_N 给定时)                   → 轮询间隔按种子量分档(e2e 轨道恒验)
 *  L214(删块前终态; 计划块表取证 L1710)                                  → 设置页刷新保持位置(顶层页 +
 *         设置页刷新保持位置(顶层页 + 分区 + 配置已加载)               分区 + 配置已加载)(S7a 补迁:
 *         计划块表遗漏该孤儿断言, S6 报告确认仍留旧脚本收尾段, 块体删块前 L198–225; 收尾清
 *         localStorage / 回辅种页不再需要 —— 每 test 独立 context)
 *  另: 旧收尾总检 L1988「无 console.error / pageerror」(全文件 1 处, 非块A专有) →
 *      installRuntimeErrorGuard afterEach(每条 test 各自把关, e2e/lib/errors.mjs)。
 *  计数口径: 旧块A add() 调用点 13 处 + 孤儿断言 1 处(设置页刷新保持位置, S7a 补迁, 见上表)
 *  (主路径, --torrents 300; 2026-10-06 删块前全量轮实测每皮肤 13 项全 PASS × 2 皮肤) →
 *  新 8 test/皮肤 × 2 皮肤 + 数据契约 2 条, 其中断言 expect 约 25 处 + afterEach 守卫 ——
 *  1:N(合并)成立, 每个旧名都有去向下落。
 *
 * ── D4 断言翻译守则落地说明(计划 §3.5) ──
 *  · 交互全部真实手势: 页签/行/筛选按钮走 locator.click; 旧 vm.toggleExpand 复原、vm.selMembers
 *    注入等 evaluate 在新轨道**不再需要**(每条 test 独立 context, 天然隔离, 无现场要还原)。
 *  · evaluate 保留处均为 vm 内部字段读数(expandedKey / viewMode / filteredTorrents / renderMs /
 *    totalDl / tagOptions / currentPollMs)—— 这些埋点与视图态没有 DOM 之外的取径, 属 D4 允许的
 *    第②类; 各处注释标明。
 *  · 装饰性 waitForTimeout(400/700/300/150…) 全部换成 expect 自动等待 / expect.poll;
 *    唯一保留的 sleep 是渲染健康里「跨一个轮询周期再看错误」的 2000ms —— 那是断言语义本身。
 *  · 阈值/超时数字逐字保留: 15_000(v-cloak/种子行)/30_000(首屏行)/5_000(.detail/弹层)、
 *    轮询分档 1500/2000/3000、300 种子档轮询 2s。
 *  · 整表 2s 重渲染抢点击的坑仍在(smoke.md): 行点击沿用 force:true + 注释, 与旧脚本同款。
 */

/** 导航页签定位器(模板: tpl/topbar.html `nav.tabs [data-view]`, 三个视图三态同页)。 */
const tab = (page, view) => page.locator(`nav.tabs [data-view="${view}"]`);

for (const skin of SKINS) {
  test.describe(`皮肤 ${skin}(块A: 视图与渲染健康)`, () => {
    /* 旧脚本收尾总检「无 console.error / pageerror」的框架化: 组内每条 test 结束时各自把关。
     * 组内每条 test 都必须在开头调 collectRuntimeErrors(page) 挂采集器(挂晚了会漏)。 */
    installRuntimeErrorGuard(test);

    /* 承接 smoke.spec 口径(P4): 渲染健康 + 数据契约打 @fast, 供 `--grep @fast` 日常门禁。 */
    test('渲染健康: Vue 挂载成功、分组行渲染、无运行时错误 @fast', async ({ page }) => {
      const errors = collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });

      /* #app 带 v-cloak + `[v-cloak] { display: none }` ⇒ Vue 不 mount 就整页隐藏, 只剩背景。
       * 断言该属性已被摘掉 = 挂载成功 —— 这是"白屏"与"数据没回来"的分界线。 */
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });

      /* 首屏数据经 /api/state 回来后才有行; 行数 > 0 即旧「分组视图渲染」同口径。 */
      const gRows = page.locator('.group-row');
      await expect(gRows.first()).toBeVisible({ timeout: 30_000 });
      expect(await gRows.count(), '分组视图渲染行数').toBeGreaterThan(0);

      /* 跨过一个轮询周期再看错误: "每轮重渲染才抛"的那类错只有等一轮才现形(轮询 1.5~3s 分档,
       * 300 种子的档位取 2s)。这里必须等, 不是可省的 sleep。 */
      await page.waitForTimeout(2000);

      expect(errors, `运行期错误:\n${errors.join('\n')}`).toEqual([]);
    });

    test('展开态跨视图记忆: 展开分组后切种子页再切回, 展开的组还在', async ({ page }) => {
      collectRuntimeErrors(page);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });

      /* 展开 = "我正盯着这一组"这种临时意图, 切走再切回必须还是那一组。三层缺一不可:
       * 1.切走后实时字段清空(展开态不串台); 2.切回后 expandedKey 还原成同一个组 key;
       * 3.DOM 里 .detail 真渲染出来(值对而面板没画正是要抓的形态)。 */
      const gRow = page.locator('.group-row[data-table="group"]').first();
      await expect(gRow).toBeVisible({ timeout: 30_000 });
      const gKey = await gRow.getAttribute('data-key');
      expect(gKey, '展开态跨视图: 取到组行').toBeTruthy();

      /* force:true —— 页面每 2s 整表重渲染会抢走点击(smoke.md), 旧脚本同款纪律。 */
      await gRow.click({ force: true });
      await expect(page.locator('.detail').first()).toBeVisible({ timeout: 5_000 });
      /* vm 内部字段读数(evaluate 第②类): expandedKey 无 DOM 之外的取径。 */
      expect(await readInst(page, 'vm.expandedKey'), '展开分组: 明细面板出现').toBe(gKey);

      await tab(page, 'torrents').click(); // 切种子页
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await expect.poll(() => readInst(page, 'vm.expandedKey'), {
        message: '切到种子视图: 展开态不串台(实时字段清空)',
      }).toBe(null);

      await tab(page, 'groups').click(); // 切回辅种页
      await expect(page.locator('.detail').first()).toBeVisible({ timeout: 5_000 });
      expect(await readInst(page, 'vm.expandedKey'), '切回辅种视图: 展开的组还在(跨视图记忆)').toBe(gKey);
    });

    test('导航焦点: 键盘切页后旧页签不残留焦点框', async ({ page }) => {
      collectRuntimeErrors(page);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(tab(page, 'shows')).toBeVisible({ timeout: 15_000 });

      /* 鼠标点「追剧」—— 页签持焦但鼠标模态不画 :focus-visible。
       * matches(":focus-visible") 是机制读数, 框是否真画出以 focused(焦点位置)为准。 */
      await tab(page, 'shows').click();
      await expect.poll(async () => page.evaluate(() => {
        const b = document.querySelector('nav.tabs [data-view="shows"]');
        if (!b) return { focused: false, fv: true };
        return { focused: document.activeElement === b, fv: b.matches(':focus-visible') };
      })).toEqual({ focused: true, fv: false });

      /* 键盘切到种子页 —— 复现残留框的关键一步(修法 = goView 后 syncNavFocus 归还焦点)。 */
      await page.keyboard.press('2');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      /* vm 内部字段读数(evaluate 第②类): viewMode。 */
      expect(await readInst(page, 'vm.viewMode'), '键盘切页后视图态').toBe('torrents');
      const stale = await page.evaluate(() =>
        [...document.querySelectorAll('nav.tabs [data-view]')]
          .filter((b) => document.activeElement === b || b.matches(':focus-visible')).length);
      expect(stale, '导航焦点: 键盘切页后旧页签不残留焦点框').toBe(0);
    });

    test('种子视图: 切换有数据、总数与桩一致、renderMs 埋点可读', async ({ page }) => {
      collectRuntimeErrors(page);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      /* P1-1: 只回传当前视图数组 ⇒ 切过去必须仍有数据, 不能被上一轮抹空。 */
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      const tRows = await page.locator('.torrent-row').count();
      /* vm 内部字段读数(evaluate 第②类): filteredTorrents 是窗口化数据源, 行窗口化 ⇒ DOM 行 ≤ 数据。 */
      const tTotal = await readInst(page, 'vm.filteredTorrents.length');
      expect(tRows, `切到种子视图有数据: DOM ${tRows} 行 / 数据 ${tTotal} 条`).toBeGreaterThan(0);
      expect(tRows, 'DOM 行数不超过数据条数(行窗口化)').toBeLessThanOrEqual(tTotal);
      expect(tTotal, '种子总数与桩服务一致').toBe(TORRENTS);

      /* vm 内部埋点(evaluate 第②类): renderMs 只在 vm 上。 */
      const renderMs = await readInst(page, 'vm.renderMs');
      expect(renderMs, `单轮 renderMs 埋点可读(${renderMs}ms)`).toEqual(expect.any(Number));
    });

    test('状态栏速度 = 服务端 totals(种子页不回 groups 也要对)', async ({ page }) => {
      collectRuntimeErrors(page);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      /* issue 26-09-20-1646: 状态栏是跨视图的常驻显示, 旧实现在前端对 groups 求和而种子页不回
       * groups ⇒ 恒 0 或冻结旧值。所以断言写成「等于服务端 status.totals 真值」而不是「≠ 0」。
       * vm 内部字段读数(evaluate 第②类): status.totals / totalDl 的数值口径在 vm 上。 */
      const wantDl = await readInst(page, 'vm.status && vm.status.totals ? vm.status.totals.dlspeed : null');
      expect(wantDl, '桩服务 status.totals.dlspeed 非零(合成种子自带速度)').toBeGreaterThan(0);
      await expect.poll(() => readInst(page, 'vm.totalDl'), {
        message: '状态栏 vm.totalDl == 服务端 totals.dlspeed',
      }).toBe(wantDl);
      const sbText = (await page.locator('.sb-speed .val').first().innerText()).trim();
      expect(sbText, `状态栏 DOM="${sbText}"`).not.toBe('0 B/s');
      expect(sbText, '状态栏 DOM 速度文本非空').not.toBe('');
    });

    test('种子页筛选器有数据(计数=种子数)', async ({ page }) => {
      collectRuntimeErrors(page);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      /* 2026-09-21 用户报「种子页筛选器无数据」: 筛选弹层选项原先遍历 groups 计算, 而种子页按
       * 视图分片不回 groups ⇒ 标签/分类/站点/路径恒空。判据两层缺一不可: 1.选项非空 + 弹层 DOM
       * 真渲染出项 2.计数 = 种子数(只判非空会被"仍按组算"的错误口径蒙过去)。
       * vm 内部字段读数(evaluate 第②类): filterDefs/tagOptions 的计数口径在 vm 上。 */
      /* vm 内部字段读数(evaluate 第②类, 走 readInst 的 INST 单点): filterDefs/tagOptions 的
       * 计数口径只在 vm 上, DOM 只能看到渲染结果。 */
      const opts = await readInst(page, `(() => {
        const tag = vm.tagOptions[0];
        return {
          groups: vm.groups.length, torrents: vm.torrents.length,
          empty: vm.filterDefs.filter((x) => !x.options.length).map((x) => x.kind).join(','),
          first: tag ? tag.value : null,
          count: tag ? tag.count : -1,
          truth: tag ? vm.torrents.filter((r) => (r.tags || []).includes(tag.value)).length : -1,
        };
      })()`);
      expect(opts.empty, `空筛选器 kinds=[${opts.empty}](取数面 groups=${opts.groups}/torrents=${opts.torrents})`).toBe('');
      expect(opts.count, `首个标签 ${opts.first} 计数`).toBe(opts.truth);

      await page.locator('.filter-btn').first().click(); // 标签筛选弹层: 用户看到"暂无数据"的地方
      await expect(page.locator('.pop-menu .pop-item').first()).toBeVisible({ timeout: 5_000 });
      const items = await page.locator('.pop-menu .pop-item').count();
      const emptyTip = await page.locator('.pop-menu .pop-empty').count();
      expect(items, '弹层渲染出选项').toBeGreaterThan(0);
      expect(emptyTip, '弹层无「暂无数据」空提示').toBe(0);
      await page.keyboard.press('Escape'); // 收起弹层
      await expect(page.locator('.pop-menu')).toHaveCount(0);
    });

    test('设置页刷新保持位置(顶层页 + 分区 + 配置已加载)', async ({ page }) => {
      collectRuntimeErrors(page);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      /* 2026-09-25 用户报「设置页刷新会回到种子页」: 顶层 page 与设置分区(hub.view)原本都是
       * **纯内存态** ⇒ F5 必掉回辅种页 + 设置首页, 编辑到一半的位置全丢。走真实手势
       * (点设置 → 进分区 → 刷新)复现用户路径。
       * !断言里必须含 `cfg.schema` 非空 —— 只改初值不改启动路径的写法会让刷新停在
       * 「配置加载失败 + 重试」(设置页配置树是**按需加载**的), 而 page 值看着是对的。 */
      await page.locator('nav.tabs-right button').first().click(); // 顶栏右侧「设置」
      await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
      await page.locator('.hb-grid .hb-card').first().click(); // 进第一个分区(真实手势)

      /* vm 内部字段读数(evaluate 第②类): page/hub.view/cfg.schema 是纯内存态, 无 DOM 之外的
       * 取径; 面包屑分区名走 DOM。 */
      const READ = `({ page: vm.page, hub: vm.hub.view, schema: !!vm.cfg.schema,
        crumb: (document.querySelector('.hb-crumb .cb-now') || {}).textContent || '' })`;
      let s1;
      await expect.poll(async () => {
        s1 = await readInst(page, READ);
        return s1 && s1.schema && s1.hub !== 'hub' && s1.crumb ? 1 : 0;
      }, { message: '进入设置: cfg.schema 已加载且 hub.view 离开设置首页', timeout: 15_000 }).toBe(1);
      expect(s1.page, `进入: 顶层页 = settings(hub=${s1.hub} crumb=${s1.crumb})`).toBe('settings');

      await page.reload({ waitUntil: 'domcontentloaded' });
      /* 刷新后要等鉴权 + 首轮轮询 + 补的那次 cfgLoad(旧脚本 sleep 3500ms), 换 poll 等同一稳定态:
       * 分区与面包屑都还原 + 配置树非空, 三者齐才算位置真的保住。 */
      let s2;
      await expect.poll(async () => {
        s2 = await readInst(page, READ);
        return s2 && s2.schema && s2.hub === s1.hub && s2.crumb === s1.crumb ? 1 : 0;
      }, {
        message: `刷新后: 分区/面包屑还原(hub=${s1.hub} crumb=${s1.crumb})且 cfg.schema 已加载`,
        timeout: 15_000,
      }).toBe(1);
      expect(s2.page, '刷新后: 顶层页仍是 settings').toBe('settings');
      /* 旧脚本收尾的「清位置偏好 + 回辅种页」不再需要 —— 每 test 独立 context(D4), 天然隔离。 */
    });

    test('轮询间隔按种子量分档(≤1000→1500 / 1000~3000→2000 / >3000→3000)', async ({ page }) => {
      collectRuntimeErrors(page);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      /* 等首屏数据到位再断言: basePollMs 在 status.torrents 未知时取中间档 2000,
       * 不等数据落地的话 3000 种子轮(期望也是 2000)会被"未知档"蒙过去。 */
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      /* 档位来自实测单轮 refresh 耗时(1000:143ms / 3000:309ms / 5000:~400ms), 目的是把主线程
       * 占用率压在 ~15%。断言它, 免得"改了半天的渲染优化"被一个写死的 1s 轮询重新拖垮。
       * vm 内部方法读数(evaluate 第②类): currentPollMs 只在 vm 上; 阈值逐字保留。 */
      const want = TORRENTS > 3000 ? 3000 : TORRENTS > 1000 ? 2000 : 1500;
      await expect.poll(() => readInst(page, 'vm.currentPollMs()'), {
        message: `${TORRENTS} 种子 → 轮询 ${want}ms(失败退避翻倍态也算不达标)`,
      }).toBe(want);
    });
  });
}

/* 数据契约(@fast, 承接 smoke.spec 口径): 不经页面, 直接打桩服务接口。 */
test.describe('数据契约(桩供数 @fast)', () => {
  for (const skin of SKINS) {
    test(`[${skin}] 数据契约: status.torrents 与桩服务种子数一致 @fast`, async ({ request }) => {
      const res = await request.get(`${BASE_URL}/api/state`);
      expect(res.ok(), `GET /api/state -> ${res.status()}`).toBeTruthy();

      const body = await res.json();
      /* status.torrents 是"恒回传"标量(不参与按视图裁剪), 用它判桩服务真的在供数据 ——
       * 只判 HTTP 200 会被"旧进程仍在应答"蒙过去。 */
      expect(body.status.torrents).toBe(TORRENTS);
      expect(body.status.groups).toBeGreaterThan(0);
    });
  }
});

/* 几何守卫(2026-10-06, 计划 26-10-06-1009, 随远端 cdacf51a 并入本文件 —— 该 test 原落在已退役的
 * smoke.spec.mjs, 本轨 S1 删壳后按「断言单点」纪律移此承载, 断言逻辑逐字保留):
 * 右对齐列表头文字与值文字必须落在同一竖线上。
 * 为什么需要它: 本轮缺陷的成因是「盒子模型」—— 表头 .h-cell 为容纳拖拽把手多出的 10px
 * 右内边距, 让右对齐表头比数值左偏 11px(明细 10px), 排序时箭头再顶 11px; 而 tests/test_web.py
 * 的近 300 条守阵全是**读文件文本**的静态断言, 原理上看不见盒子模型。故在真浏览器 + 桩服务这层
 * 加一条几何断言(桩服务由 playwright.config.mjs 的 webServer 自动拉起)。
 * 口径: 量**内容盒**右缘之差(盒右缘 − 右内边距), 不量墨迹(值溢出被省略号截断会抖动);
 * 数据行有 1px 侧边框 ⇒ 允许 ±1px。详见 pitfalls/web-ui/header-cell-gutter.md。 */
test.describe('几何守卫(右对齐列表头)', () => {
  for (const skin of SKINS) {
    test(`[${skin}] 几何: 右对齐列表头与值右缘对齐(±1px), 且值格不居中`, async ({ page }) => {
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.group-row', { timeout: 30_000 });
      await page.waitForTimeout(300); /* 等列对齐规则注入 + 首帧布局稳定 */

      const bad = await page.evaluate(() => {
        /* 内容盒右缘 = 盒右缘 − 右内边距 */
        const cRight = (el) => el.getBoundingClientRect().right - parseFloat(getComputedStyle(el).paddingRight);
        const out = [];
        /* 表头网格表 = .group-head(分组/种子/追剧) + .detail-head(组内明细/集明细) */
        for (const head of document.querySelectorAll('.group-head[data-table], .detail-head[data-table]')) {
          const page_ = head.getAttribute('data-table');
          const cells = [...head.children].filter((c) => c.classList.contains('h-cell'));
          if (!cells.length) continue;
          const row = document.querySelector(page_ === 'detail'
            ? '.member-row[data-table="detail"]'
            : `.group-row[data-table="${page_}"]`);
          if (!row) continue;
          const rcells = [...row.children];
          cells.forEach((hc, i) => {
            if (getComputedStyle(hc).textAlign !== 'right') return; /* 只看右对齐列(左/中列无此缺陷) */
            const rc = rcells[i];
            if (!rc) return;
            const d = cRight(rc) - cRight(hc);
            if (Math.abs(d) > 1) out.push({ page: page_, delta: Math.round(d * 100) / 100 });
            if (getComputedStyle(rc).textAlign === 'center') out.push({ page: page_, zeroCentered: true });
          });
        }
        return out;
      });

      expect(bad, `右对齐列错位 / 0 值居中: ${JSON.stringify(bad)}`).toEqual([]);
    });
  }
});
