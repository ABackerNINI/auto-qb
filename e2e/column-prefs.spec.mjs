// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst } from './lib/vm.mjs';

/**
 * 列设置守阵(S6 批, 计划 26-10-06-0708 §3.3/§04 S6; 源头计划 26-09-21-1551 §7.2 双轨模型守阵
 * 与 issue 26-09-20-1800 多标签同步) —— 承接旧脚本 scripts/ui_smoke.cjs 的**块H**。
 * 行号为取证时点值(计划 §2.2), 已按 grep 锚点复核(2026-10-06, 删块前; S1–S5 已删块A/F/C/E/D/B/G,
 * 行号较计划漂移: 计划取证 L1795–1985 → 删块前现 L235–399):
 *
 * 块H grep 锚点: `列设置多标签页同步(issue 26-09-20-1800)` 起, 至 `列设置·v4→v5迁移` 块收尾止
 * (删块前 L235–399; 计划取证 L1795–1985)。内含 5 个旧 add() 名(+5 失败兜底):
 * 列设置多标签页互不覆盖 / 列设置·异视口双窗互不吞+F3 / 列设置·全自动页不落px /
 * 列设置·隐藏列宽度保留 / 列设置·v4→v5迁移。专属脚手架(colHide/dragCol/colState/clearCols,
 * 删块前 L263–284)只供本块, 随块一并退役 —— 新轨等价物见本文件 helpers。
 *
 * ── 对账映射表(旧断言名 → 新 test 名; 旧块 add() 调用点 5 名 × 2 处 = 10 处, ok 模式主路径 5 处/皮肤) ──
 *  旧 add() 行号(删块前 grep 实测)   旧断言名                                 新去向下落
 *  L257  列设置多标签页互不覆盖        → 列设置多标签页互不覆盖(双标签各改一列, storage 事件合流)。
 *          旧判据 hidden.group.length >= 2 自 2026-09-28 hide 默认隐藏播种起**恒真**(播种 4 键),
 *          升级为「两个改动键(uploaded/total_size)都在」—— issue 26-09-20-1800 的本意(谁也不吞谁)。
 *  L317  列设置·异视口双窗互不吞+F3    → 异视口双窗互不吞+F3(1 test 3 断言 —— 共享同一次双窗编排,
 *          拆开要重演"两窗五步"): okMerge(A 采纳 B) / okF3(F3 补漏采纳) / okReload(刷新仍在)。
 *          okMerge/okReload 条件逐字保留; okF3 的 `h.group.length >= 2` 同样被播种恒真,
 *          升级为「含 A 刚隐藏的 uploaded 键」—— F3(visibilitychange 回到可见补采纳)的实际语义。
 *  L336  列设置·全自动页不落px         → 全自动页不落px(意图动作后 pages.torrent.w === null, 逐字保留)
 *  L366  列设置·隐藏列宽度保留         → 隐藏列宽度保留(隐藏→再拖宽→重新显示, 该列 px 原样回来)
 *  L395  列设置·v4→v5迁移              → v4→v5 迁移(1 test 2 断言 —— 共享同一次 v4 注入):
 *          okLoad(固化页宽度保留/隐序保留/非固化页 w=null) + okV5(首次意图动作落 v5)。
 *  L260/L322/L339/L369/L398(catch 兜底)  → **不迁移**: 失败兜底分支, 新轨断言/定位器拿不到目标
 *          直接红, 语义等价(与 S5 批 hr-history 的兜底处置同款)。
 *  另: 旧收尾总检「无 console.error / pageerror」→ installRuntimeErrorGuard afterEach; 多 page
 *  用例(多标签/双窗)对**第二页面**单独挂采集器并在测试体内显式断言 —— afterEach 只接得到 fixture 页。
 *  计数口径: 块H add() 5 处/皮肤(实跑; 兜底 5 处仅失败时出现) → 新 5 test/皮肤 × 2 皮肤,
 *  每个旧名都有去向下落。
 *
 * ── 对账实跑数字(五步对账 §5.1, 2026-10-06 S6 批实测回填) ──
 *  · 步骤1 新 spec: dev.e2e 单跑本文件 10 passed(19.4s); 全量 76 passed / 10 skipped / 0 failed
 *    (2.7m; S5 收口基线 66 passed / 2.4m —— 增量即本批 10 test, 时长 +0.3m 远低于旧脚本同口径
 *    1.5× 阈值, 计划 §6 R3 只记不优化)。
 *  · 步骤2 旧脚本同参数轮(删块前): 桩 8236(`--torrents 300`, 其余默认; READY 判据 = harness
 *    日志首行 + curl 页面 200) + `node scripts/ui_smoke.cjs --base http://127.0.0.1:8236
 *    --torrents 300 --ui both` = 14 项 0 FAIL(36.5s), 无存量失败; 对账范围内块H 5 断言名 ×
 *    2 皮肤全 PASS(实测: 多标签 hidden.group 含 uploaded+total_size; 守阵3 key=upspeed
 *    前=88px 后=88px; 守阵4 load wg.uploaded=300px / hg=[category] / wt=null)。
 *  · 步骤3 对账映射: 见上表 —— 块H 5 旧名/皮肤 → 5 test/皮肤, 每个旧名有去向下落; catch 兜底
 *    5 处不迁移(新轨断言失败即红)。两处判据升级(多标签 hidden 集合 / F3 采纳键)与理由见映射表注。
 *  · 步骤4 删旧块(与本 spec 同 commit): ui_smoke.cjs 删块H 段(删块前 L235–399)+ 专属脚手架
 *    colHide/dragCol/colState/clearCols, 原位留指路注释; `node --check` 过。
 *  · 步骤5 双复跑: 旧脚本 4 项 0 FAIL(14→4, 恰降 10 = 5 名 × 2 皮肤); dev.e2e 全量复跑
 *    76 passed / 10 skipped / 0 failed(2.7m)。`npm run test:e2e:fast` 4 passed(7.7s)与本批前一致。
 *  · Windows 收尾: stub(TaskStop)杀净后 netstat 现查 8137/8236 均无 LISTENING、tasklist 无
 *    python 孤儿进程; dev.e2e 侧由 e2e/global-teardown.mjs 兜底(日志见「收尾兜底」行)。
 *
 * ── D4 断言翻译守则落地说明(计划 §3.5) ──
 *  · 多标签/多视口(计划 D4 专条): 每条 test 独立 context(localStorage 天然隔离), test 内
 *    `page.context().newPage()` 开第二页(同 context ⇒ 共享存储, storage 事件照常跨页);
 *    视口用 `setViewportSize` 摆(窗 A 1600×900 / 窗 B 1000×700, 与旧脚本逐字同值)。
 *    顺序敏感组用 `test.describe.serial` 显式声明 —— 各 test 独立 context 后本已互不依赖,
 *    仍按旧脚本块内顺序排列并声明 serial, 保持与旧流水可对照的固定执行序。
 *  · 旧脚本"clearCols + reload 重置列存储"的舞蹈**整段省去**: 每 test 新 context 存储本就为空,
 *    这是 D4 明言的独立 context 红利(干净, 不带上一块的现场)。
 *  · 交互全部真实手势: 隐藏/显示列走 col-menu 真点击(旧脚本守阵 2/3/4 直调 vm.toggleColumn,
 *    有真实 UI 路径 ⇒ 一律换手势); 菜单项定位用「分区标题 + 项文案」(旧脚本按全菜单
 *    .col-menu-item 全局下标取项 —— 空存储下 items[3]=总上传 / items[5]=总大小 / 种子页段
 *    items=大小, 新轨定位语义相同且不随分区内容漂移)。拖宽手势 mouse.move/down/up **逐字照搬**
 *    (含 +5 起手 / +60px 步进 6)。
 *  · evaluate 保留处(均为 D4 允许的两类): ①守阵 1 的 F3 visibilitychange 模拟 —— 标签冻结/恢复
 *    是浏览器行为, 无真实 UI 路径(旧脚本同款); ②守阵 4 的 v4 载荷注入 —— 桩态注入; ③vm 内部
 *    字段读数(colW/colHidden/_visibleCols/groupColumns) —— 列意图态没有 DOM 之外的取径。
 *  · 装饰性 waitForTimeout(400/600/500/300/200) 全部换成 expect / expect.poll 显式等待:
 *    跨标签 storage 事件传播(旧 600ms)→ poll 等对方 vm 采纳了具体键; Escape 收弹层(旧 200ms)→
 *    poll vm.colMenuOpen === false(不用 toHaveCount(0): pop 过渡挂在 rAF 上, 后台页可能不停走完,
 *    vm 态才是真信号); 拖宽落定(旧 300ms)→ poll colW.group 非空。语义不变, 不再赌时长。
 *  · !守阵 3 的**取键时序坑**(注释随迁, 见 test 体内): 被隐藏列的 key 必须在隐藏**前**从
 *    _visibleCols 取 —— 隐藏后取 colHidden[0] 拿到的是 hide 播种的默认隐藏列(从未有过意图宽度),
 *    它"读不回 px"是双轨模型的正确行为, 不是回归(用例 26-09-30-0602 的前=undefined 后=92px 即此)。
 */

/** 分区标题 → 该区列项(文案定位, 见头部 D4 说明; 分区标题单点在 topbar.html: l10nGroup="辅种")。 */
const colItem = (page, section, label) => page.locator(
  `xpath=//div[contains(@class,"col-menu-title")][normalize-space()="${section}"]`
  + `/following-sibling::div[contains(@class,"col-menu-item")][normalize-space()="${label}"]`).first();

/** 等首屏分组行(旧脚本 waitForFunction('.group-row') 同口径, 30s 逐字保留)。 */
const rowsReady = (page) => expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

/**
 * 打开列选择器弹层(真实手势: 顶栏「列」按钮, 旧脚本同款选择器)。
 */
async function openColMenu(pg) {
  await pg.locator('.col-picker button.table-tool').click();
  await expect(pg.locator('.col-menu .col-menu-item').first()).toBeVisible({ timeout: 5_000 });
}

/**
 * 菜单里切换某列显隐(真实手势), 等勾选态翻转(旧 waitForTimeout(400) 的显式化)再 Escape 收起
 * (旧 200ms → poll vm.colMenuOpen, 见头部 D4 说明)。
 *
 * @param {import('@playwright/test').Page} pg
 * @param {string} section 分区标题(辅种表 / 明细表 / 种子页 / 追剧视图)
 * @param {string} label 列文案(如 总上传)
 * @param {boolean} toHidden true=隐藏该列, false=重新显示
 */
async function colToggle(pg, section, label, toHidden) {
  await openColMenu(pg);
  const item = colItem(pg, section, label);
  await item.click();
  await expect(item, `「${section}/${label}」勾选态翻转`).toHaveAttribute(
    'aria-pressed', toHidden ? 'false' : 'true');
  await pg.keyboard.press('Escape');
  await expect.poll(() => readInst(pg, 'vm.colMenuOpen'), { message: 'Escape 收起列菜单' }).toBe(false);
}

/**
 * 拖宽手势(旧脚本 dragCol 逐字照搬: 第 2 列 resizer, +5 起手 / +60px / steps 6),
 * 末尾旧 waitForTimeout(300) 换成 poll 等固化落地 —— 固化页 colW.group 非空是后续断言的前提。
 */
async function dragCol(pg) {
  const h = pg.locator('.group-head .h-cell:nth-child(2) .resizer');
  const bb = await h.boundingBox();
  await pg.mouse.move(bb.x + 5, bb.y + bb.height / 2);
  await pg.mouse.down();
  await pg.mouse.move(bb.x + 65, bb.y + bb.height / 2, { steps: 6 });
  await pg.mouse.up();
  await expect.poll(() => readInst(pg, 'vm.colW.group ? Object.keys(vm.colW.group).length : 0'), {
    message: '拖宽后 colW.group 已固化(意图宽度非空)',
  }).toBeGreaterThan(0);
}

/** vm 意图态读数(evaluate 第②类: 列意图态没有 DOM 之外的取径)。 */
const colState = (pg) => readInst(pg, '({ w: vm.colW, h: vm.colHidden })');

for (const skin of SKINS) {
  test.describe.serial(`皮肤 ${skin}(块H: 列设置守阵)`, () => {
    /* 旧脚本收尾总检「无 console.error / pageerror」的框架化(与块A 同款, e2e/lib/errors.mjs);
     * 多 page 用例对第二页面另有测试体内显式断言(见各 test 的 errors2)。 */
    installRuntimeErrorGuard(test);

    test('列设置多标签页互不覆盖: 双标签各改一列, storage 事件合流谁也不吞谁', async ({ page }) => {
      test.setTimeout(90_000);   // 两次整页加载 + 跨页传播等待, 放宽默认 30s
      const errors = collectRuntimeErrors(page);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await rowsReady(page);

      /* 标签 2 = 同 context 的第二页(共享 localStorage, storage 事件照常跨页)。
       * 判据前提(issue 26-09-20-1800): 标签 2 必须在**标签 1 改动之前**就已加载 —— 否则读到的是
       * 最新存储, 验不出"旧快照整份写回吞掉别人改动"。这里先等标签 2 行渲染完再动标签 1。 */
      const tab2 = await page.context().newPage();
      const errors2 = collectRuntimeErrors(tab2);
      await tab2.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await rowsReady(tab2);

      await colToggle(page, '辅种表', '总上传', true);   // 标签 1 先改(旧 items[3] = uploaded)
      /* 旧 waitForTimeout(600)「等 storage 事件把改动推给标签 2」→ poll 显式等标签 2 采纳。 */
      await expect.poll(
        () => readInst(tab2, `(vm.colHidden.group || []).includes('uploaded')`),
        { message: '标签 2 经 storage 事件采纳标签 1 的改动' },
      ).toBe(true);
      await colToggle(tab2, '辅种表', '总大小', true);   // 标签 2 再改(旧 items[5] = total_size)

      /* 旧判据 length >= 2 被播种恒真, 升级为「两个改动键都在」(见头部映射表)。 */
      await expect.poll(
        () => readInst(page, '(vm.colHidden.group || []).slice()'),
        { message: '标签 1 的 hidden.group 同时含两标签的改动' },
      ).toEqual(expect.arrayContaining(['uploaded', 'total_size']));

      await tab2.close();
      expect(errors2, `标签 2 运行期错误:\n${errors2.join('\n')}`).toEqual([]);
      expect(errors, `运行期错误:\n${errors.join('\n')}`).toEqual([]);
    });

    test('列设置·异视口双窗互不吞+F3(1600 拖宽固化 / 1000 隐藏列, 互相采纳)', async ({ page }) => {
      test.setTimeout(120_000);   // 三次整页加载 + 两窗编排, 放宽默认 30s
      const errors = collectRuntimeErrors(page);
      // 窗 A 1600×900(fixture 页摆视口; 旧脚本 pa 同值)
      await page.setViewportSize({ width: 1600, height: 900 });
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await rowsReady(page);
      // 窗 B 1000×700(旧脚本 pb 同值; 旧模型此处 B 算出的 px 会写进存储, A 刷新即被改写)
      const pb = await page.context().newPage();
      const errors2 = collectRuntimeErrors(pb);
      await pb.setViewportSize({ width: 1000, height: 700 });
      await pb.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await rowsReady(pb);

      await dragCol(page);   // A 拖宽 -> group 固化(colW 非空)
      await colToggle(pb, '辅种表', '总大小', true);   // B(更窄窗口)隐藏一列
      /* 旧 waitForTimeout(600)「等 storage 事件把 B 的改动推给 A」→ poll 等采纳。 */
      await expect.poll(
        () => readInst(page, `(vm.colHidden.group || []).includes('total_size')`),
        { message: 'A 经 storage 事件采纳 B 的改动' },
      ).toBe(true);
      const ra = await colState(page);
      const okMerge = Object.keys(ra.w.group || {}).length > 0 && (ra.h.group || []).length >= 1;
      expect(okMerge, `A 采纳 B 后意图态(条件逐字保留): ${JSON.stringify(ra)}`).toBe(true);

      await colToggle(page, '辅种表', '总上传', true);   // A 再改一次(旧 items[3] = uploaded)

      /* F3 补漏: 模拟 B 被冻结后恢复可见(hidden -> visible 各派发一次) —— evaluate 保留:
       * 标签冻结/恢复是浏览器行为, 无真实 UI 路径(旧脚本同款, D4 第①类桩态注入)。 */
      await pb.evaluate(`Object.defineProperty(document, "hidden", { value: true, configurable: true });
        document.dispatchEvent(new Event("visibilitychange"));
        Object.defineProperty(document, "hidden", { value: false, configurable: true });
        document.dispatchEvent(new Event("visibilitychange"));`);
      /* 旧 waitForTimeout(500) → poll 等 B 采纳 A 的改动。旧条件 h.group.length >= 2 被播种恒真,
       * 升级为「含 A 刚隐藏的 uploaded」—— F3 补采纳的实际语义(见头部映射表)。 */
      await expect.poll(
        () => readInst(pb, `(vm.colHidden.group || []).includes('uploaded')`),
        { message: 'F3 补漏: B 恢复可见后采纳 A 的改动' },
      ).toBe(true);
      const rb = await colState(pb);
      const okF3 = (rb.h.group || []).length >= 2;   // 旧条件逐字保留(升级判据已在上一行 poll)
      expect(okF3, `F3 后 B 意图态: ${JSON.stringify(rb)}`).toBe(true);

      await page.reload({ waitUntil: 'domcontentloaded' });   // 刷新后两者都必须还在
      await rowsReady(page);
      const ra2 = await colState(page);
      const okReload = Object.keys(ra2.w.group || {}).length > 0 && (ra2.h.group || []).length >= 2;
      expect(okReload, `A 刷新后意图态(条件逐字保留): ${JSON.stringify(ra2)}`).toBe(true);

      await pb.close();
      expect(errors2, `窗 B 运行期错误:\n${errors2.join('\n')}`).toEqual([]);
      expect(errors, `运行期错误:\n${errors.join('\n')}`).toEqual([]);
    });

    test('列设置·全自动页不落px(种子页意图动作后 pages.torrent.w 必须是 null)', async ({ page }) => {
      const errors = collectRuntimeErrors(page);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await rowsReady(page);

      /* 旧脚本 vm.toggleColumn("torrent","size") 直调 —— 有真实 UI 路径(col-menu「种子页」分区),
       * 按 D4 换真实手势。断言对象是**存储形状**, 与走菜单还是 vm 无关。 */
      await colToggle(page, '种子页', '大小', true);

      /* 双轨模型铁律的行为面: 全自动页(未拖宽固化)的派生 px 绝不落盘 —— 意图动作后 w 必须是 null
       * ("派生值没有资格落盘", columns.js persistPage 唯一写入口)。 */
      const blob = JSON.parse(await page.evaluate(`localStorage.getItem("autoqb_cols_v5") || "{}"`));
      const tw = blob.pages && blob.pages.torrent ? blob.pages.torrent.w : undefined;
      expect(tw, `pages.torrent.w = ${JSON.stringify(tw)}`).toBe(null);

      /* 旧脚本在此还原显隐(toggle 回来) —— 新轨每 test 独立 context, 无现场要还原(D4 明言), 省去。 */
      expect(errors, `运行期错误:\n${errors.join('\n')}`).toEqual([]);
    });

    test('列设置·隐藏列宽度保留(隐藏→再拖宽→重新显示, 该列 px 原样回来)', async ({ page }) => {
      const errors = collectRuntimeErrors(page);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await rowsReady(page);
      await dragCol(page);   // 固化 group(全可见列拿到意图宽度)
      const s1 = await colState(page);

      /* !取键时序坑(注释随迁): 被隐藏列的 key 必须在隐藏**前**从 _visibleCols 取 —— 2026-09-28
       * 辅种扩列给列定义加了 hide:true 默认隐藏列后, colHidden.group 里常驻 amount_left 等默认
       * 隐藏键, 隐藏后取 colHidden[0] 拿到的是从未有过意图宽度的默认隐藏列(固化只固化**可见列**),
       * 它"读不回 px"是双轨模型的正确行为(显示时由 toggleColumn 按 templateMinPx 合成), 不是
       * 回归 —— 用例 26-09-30-0602 的 前=undefined 后=92px 即此。断言的对象应是"被本用例隐藏的
       * 那一列"。 */
      const k = await readInst(page, 'vm._visibleCols("group")[2].key');
      /* 隐藏该列走真实手势(旧 vm.toggleColumn): 菜单项 = groupColumns(列定义序, 空存储无自定义序
       * 时与 _visibleCols 同源)里同 key 的文案。 */
      const label = await readInst(
        page, `(vm.groupColumns.find((c) => c.key === ${JSON.stringify(k)}) || {}).label`);
      expect(label, `列 ${k} 的菜单文案`).toBeTruthy();
      await colToggle(page, '辅种表', label, true);
      const s2 = await colState(page);

      await dragCol(page);   // 再拖宽(旧模型此处抹掉隐藏列 px)
      await colToggle(page, '辅种表', label, false);   // 重新显示
      const s3 = await colState(page);
      const okKeep = !!(k && s2.h.group && s2.h.group.includes(k) && s1.w.group && s1.w.group[k]
        && s3.w.group && s3.w.group[k] === s1.w.group[k]);
      expect(okKeep, `key=${k} 前=${JSON.stringify(s1.w.group && s1.w.group[k])}`
        + ` 后=${JSON.stringify(s3.w.group && s3.w.group[k])}`).toBe(true);
      expect(errors, `运行期错误:\n${errors.join('\n')}`).toEqual([]);
    });

    test('列设置·v4→v5迁移(固化页宽度保留 / 非固化页污染 px 清零 / 隐序保留 / 首次意图落 v5)', async ({ page }) => {
      const errors = collectRuntimeErrors(page);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await rowsReady(page);
      /* 注入 v4 旧载荷(桩态注入, D4 第①类 evaluate; 旧脚本同款逐字)。新 context 无 v5 残留,
       * removeItem 保留只为与旧脚本逐字同款(幂等)。 */
      await page.evaluate(() => {
        localStorage.removeItem("autoqb_cols_v5");
        localStorage.setItem("autoqb_cols_v4", JSON.stringify({
          widths: { group: { uploaded: "300px" }, torrent: { name: "222px" } },
          hidden: { group: ["category"] },
          manual: { group: true, torrent: false },
          order: {},
        }));
      });
      await page.reload({ waitUntil: 'domcontentloaded' });
      await rowsReady(page);

      /* 迁移语义(内存迁移, app.js migrateLegacyToV5): 固化页(manual=true)宽度保留,
       * 非固化页(torrent manual=false)的历史污染 px 清零, hidden 原样带过。 */
      const m1 = await readInst(page, '({ wg: vm.colW.group || null, hg: vm.colHidden.group || [], wt: vm.colW.torrent || null })');
      const okLoad = !!(m1.wg && m1.wg.uploaded === '300px' && (m1.hg || []).includes('category') && !m1.wt);
      expect(okLoad, `v4 载入语义: ${JSON.stringify(m1)}`).toBe(true);

      /* 一次意图动作 -> 落 v5(真实手势: 菜单「总大小」, 旧 vm.toggleColumn("group","total_size"))。 */
      await colToggle(page, '辅种表', '总大小', true);

      const blob = JSON.parse(await page.evaluate(`localStorage.getItem("autoqb_cols_v5") || "{}"`));
      const g = blob.pages && blob.pages.group;
      const okV5 = !!(blob.v === 5 && g && g.w && g.w.uploaded === '300px'
        && (g.hidden || []).includes('category')
        && (!blob.pages.torrent || blob.pages.torrent.w === null));
      expect(okV5, `意图动作后存储落 v5: load=${JSON.stringify(m1)} blob=${JSON.stringify(blob)}`).toBe(true);
      expect(errors, `运行期错误:\n${errors.join('\n')}`).toEqual([]);
    });
  });
}
