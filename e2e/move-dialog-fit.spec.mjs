// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { clickRow, ctxItem, openApp } from './lib/gestures.mjs';

/**
 * 设定位置对话框守阵 —— 几何(2026-10-19 首修) + 提交语义与过渡(2026-10-29 二修)。
 *
 * 缺陷机理(首修): 保存路径组合框是本表单的**最后一项**, 而下拉朝下开(`.add-pop { top: calc(100% + 4px) }`)
 * ⇒ 整条菜单必然伸到 `.add-dialog-body`(overflow-y:auto 滚动容器)底沿之外: ①被 body 裁掉,
 * 伸出部分还把 body 的 scrollHeight 撑大(实测 123→383); ②`_fitAddPop` 的净空算式量的是「输入行 →
 * body 可见底沿」, 行贴底沿时净空为负, `avail > 0` 门恒不生效 ⇒ 限高兜底也失效。修法 = 根元素按
 * movePathMenu 挂 `.pop-open` + 三皮肤 body 预留 padding-bottom 272px。
 *
 * 二修(2026-10-29 用户报「点下拉框中的选项就触发移动」+「窗口太小, 点下拉框高度跳变」):
 * ①**点选只回填**: 移动只由「设定位置」按钮或手输回车发起(moveApplyPath 不再调 submitMoveDialog);
 * ②**窗口基线 360px**: 收层态原实测 243px(一句说明 + 一个输入框 = 小个子), 三皮肤 min-height 抬到
 *    `min(360px, calc(100vh - 120px))`, 动作条 margin-top:auto 钉底;
 * ③**高度走过渡**: 预留改 `transition: padding-bottom 200ms`(原先 0↔272 硬切 = 一次开/收跳 272px),
 *    高度 360→515 平滑长高、收层平滑回落;
 * ④**打开不自动展开**: 只聚焦(openMoveDialog 置 moveSuppressOpen), 点输入框/方向键才展开 ——
 *    否则「第一眼」是开层态, 一按 Esc 就塌回小窗口, 跳变被放大成两次。
 *
 * 三修(2026-10-29 用户报「点下拉框, 下拉框出现后自动弹回」): 二修把增长交给了 padding 过渡, 但遮罩是
 * `align-items:center` —— 增高上下对半扩, 输入行连同刚展开的面板整体**上移 77px**(360→515 的一半),
 * 面板正好顶到光标底下: 光标原位置落在候选行上, 再点一下就命中候选/面板头 = 面板"自动弹回"。
 * 修法 = 遮罩挂 .move-dialog-mask 改 flex-start + margin-top 复刻收层态居中偏移 ⇒ **增长只朝下**。
 * 故断言口径补一条几何不变量: 开层前后**输入行的屏坐标不得移动**(面板顶必须在输入框原位置之下)。
 *
 * 四修(2026-10-29 用户报「下拉框出现时弹窗有一瞬间出现滚动条」): 预留 padding 是**过渡**的, 面板却是
 * 瞬间挂载的 ⇒ 开层头 ~110ms 面板(256px)伸出 body 的 padding 盒(实测溢出 256→173→108→…→0), 而
 * body 是 `overflow-y:auto` 的滚动容器 ⇒ 闪一条滚动条, 并把内容横向挤一个滚动条宽。开层期溢出的
 * 只有那段预留空白(真内容在输入行上方)⇒ 面板在 DOM 期间 `overflow:hidden`。故断言补一条: **开层
 * 全过程逐帧 body 必须 overflowY=hidden 且零滚动条占位**(无头 Chromium 是覆盖式滚动条, 占位宽恒 0,
 * 所以判据看计算值而不是宽度)。
 *
 * 五修(2026-10-29 用户报「下拉框消失时弹窗仍会有一瞬间出现滚动条」): 收层时面板**并不立刻离场** ——
 * `<transition name="pop">` 的淡出(--dur-fast ~120ms)期间它仍在 DOM 里、高度仍是 256px, 而 `.pop-open`
 * 已摘(overflow 回到 auto)、padding 在 200ms 里往回缩 ⇒ 头 ~140ms 溢出涨到 254px(实测)= 又闪一次。
 * 开关改跟「面板是否存在」走(`:has(.add-pop)`), 开层/离场两段一起覆盖 ⇒ 收层全过程也要逐帧断言。
 *
 * 六修(2026-10-29 用户报「点面板头面板就收了」, 排查三修时顺带发现的独立缺陷): 面板里除候选行之外还有
 * **非交互区** —— `.pop-head`(「选择保存位置 N」标题+计数)与 `.pop-empty`(空态文案)。它们点了什么都不该
 * 发生, 但 mousedown 的默认动作把焦点从输入框抢走 → `@focusout` → `movePathBlurClose` 的 40ms 合帧定时器
 * 收层 = 面板"点一下就消失"(光标本来就在候选行正上方, 误触概率极高)。修法 = 焦点纪律挂在共享模板的
 * **面板根**(`@mousedown.prevent`), 一处覆盖全部非交互子元素; 只给 `.pop-head` 打补丁会让空态那处复发
 * (红验证实测: 收窄版下本文件的"点头不收"仍绿, 空态断言在 add-options-recent-order 里才抓到)。
 *
 * 七修(2026-10-29, 排查「无焦点点击弹回」时复现到的真实缺陷): 按下与抬起落在**不同元素**时, `click` 的
 * target 是两者的**公共祖先**(`.add-input-row` / 面板 / 整行), 那一路没有 `@click.stop`, 于是冒泡到
 * lifecycle 的 window 收层名单 ⇒ `movePathMenu = false` = 面板点一下就关。无焦点时最易踩: 面板是在
 * **按住期间**才挂载的(@focus → 开层), DOM 在按下与抬起之间变化, 抬起落点被改写的机会就在那一段;
 * 两皮肤输入行屏位差 2px + 面板入场 `drop-in` 从 translateY(-4px) 起(面板顶 = 输入框底 +4), 入场头
 * ~120ms 面板顶正好压在输入框下沿那 1~2px 上 —— 这就是"prism 正常 atlas 异常"这类皮肤差异的来源。
 * 修法 = 组件根 `.add-input-row` 挂 `@click.stop`(落点在本组合框内部的一切点击都不再冒泡)。
 *
 * 八修(2026-10-29 用户报「选中新路径后再次点击下拉框, 弹窗里的元素从上往下滑动出现一次; 输入框无文字时
 * 正常」): `_hiScroll` 用 `el.scrollIntoView({block:'nearest'})` 把高亮项滚进视野 —— 但 scrollIntoView 会
 * 把**所有可滚祖先**一起滚, 而 `.add-dialog-body` 正是 overflow-y 容器, 开层过渡期它的 scrollHeight 比
 * clientHeight 大 166px ⇒ 整段说明文案被滚走再弹回(实测 body.scrollTop `0 → 166 → 83 → 18 → 0`,
 * 文案 top `352 → 186 → 269 → 334`)。输入框为空时 `hi = -1`、没有 `[data-hi="1"]`, 所以只有"已选中过
 * 路径"才看得见。修法 = 手动差值调 scrollTop, 且**只动菜单内部**那层(到菜单根即止)。
 *
 * 断言口径(量 containment 不量位移 —— 居中弹窗增高时上下对半扩, 量推下量只有真实增量一半,
 * 见 pitfalls/web-ui/dialog-measure):
 *   ①打开即收层态: 下拉未展开、高度 ≥ 基线 360、body 零滚动(overflowY 仍 auto)、空路径按钮置灰;
 *   ②点输入框展开: ResizeObserver 采样到**严格介于基线与终值之间的中间高度**(证明是过渡不是瞬跳),
 *     终值增量 > 120px, 下拉完整落在框内、列表未被限高截断、前 6 项真实可点; **输入行屏坐标不动**;
 *     逐帧无滚动条(overflowY 恒 hidden / 占位宽恒 0);
 *   ③Esc 收层: 高度平滑回落到基线(±8px), body 仍零滚动且**离场全过程无滚动条**, 收完回到 auto;
 *   ④点选候选: 对话框仍在 + 输入框回填 + **零写请求**; 点「设定位置」才发一次写请求并关窗;
 *   ⑤同一屏幕点连点两次: 面板仍在、输入框未被回填(三修回归门);
 *   ⑥点面板头: 面板仍在、输入框未被改写, 且面板没被"冻住"(随后点候选仍能回填并收起);
 *   ⑦按下与抬起落在不同元素(行内留白 / 候选行): 面板仍在、输入框未被回填; 而**真点到组件外**
 *     (上方文案)仍必须收层 —— 防 `@click.stop` 挂得过宽把"点空白收层"一起废掉;
 *   ⑧选中候选后再点下拉: 逐帧 `body.scrollTop` 恒 0、说明文案屏坐标极差 ≤2px; 且高亮项仍在列表
 *     可视区内(反向守门: 滚动跟随不许被"修死")。
 */

/**
 * 等对话框子树内全部 CSS 动画/过渡跑完再量几何 —— .modal 的 modal-in 带 scale(.985),
 * 量在动画进行中会把 rect 压小(实测关态宽 856 vs 稳态 860)。
 * @param {import('@playwright/test').Locator} loc
 */
const settleAnim = (/** @type {import('@playwright/test').Locator} */ loc) =>
  loc.evaluate((el) => Promise.all(el.getAnimations({ subtree: true }).map((a) => a.finished.catch(() => {}))));

/** 量当前几何: 高度/滚动/下拉包含性/前 6 项可点/按钮禁用态。 */
const geom = (page) => page.evaluate(() => {
  const d = document.querySelector('.modal.move-dialog');
  const body = d.querySelector('.add-dialog-body');
  const row = d.querySelector('.add-input-row');
  const pop = d.querySelector('.pop-menu.add-pop');
  const list = d.querySelector('.add-pop-list');
  const items = list ? [...list.querySelectorAll('.pop-item')] : [];
  const db = body.getBoundingClientRect();
  const rb = row.getBoundingClientRect();
  const btn = d.querySelector('.modal-actions .bt.primary');
  const input = d.querySelector('#move-path');
  // 前 6 项中心点命中: 旧缺陷态第 3 项起被 .modal-actions / 遮罩盖住(elementFromPoint 落空)
  const hits = items.slice(0, 6).map((el) => {
    const b = el.getBoundingClientRect();
    const at = document.elementFromPoint(Math.round(b.left + b.width / 2), Math.round(b.top + b.height / 2));
    return { isItem: !!at && (at === el || el.contains(at)) };
  });
  return {
    w: Math.round(d.getBoundingClientRect().width),
    h: Math.round(d.getBoundingClientRect().height),
    dlgTop: Math.round(d.getBoundingClientRect().top),
    rowTop: Math.round(rb.top),  // 开层前后必须不动(三修: 增长只朝下, 不许把面板顶到光标底下)
    inputBottom: Math.round(input.getBoundingClientRect().bottom),
    popTop: pop ? Math.round(pop.getBoundingClientRect().top) : null,
    vh: window.innerHeight,
    popOpen: !!pop,
    popBelowBody: list ? Math.round(list.closest('.add-pop').getBoundingClientRect().bottom - db.bottom) : null,
    bodyScroll: body.scrollHeight - body.clientHeight,
    bodyOverflowY: getComputedStyle(body).overflowY,
    bodyGutter: body.offsetWidth - body.clientWidth,  // 滚动条占位宽(经典滚动条平台才有非 0)
    modalScroll: d.scrollHeight - d.clientHeight,
    listH: list ? Math.round(list.getBoundingClientRect().height) : 0,
    itemCount: items.length,
    rowBottomGap: Math.round(db.bottom - rb.bottom),  // 开层后行底到 body 底沿的预留量
    btnDisabled: !!(btn && btn.disabled),
    inputValue: input ? input.value : "",
    hits,
  };
});

/** 挂 ResizeObserver 采样对话框高度序列(过渡的中间态只能这样抓, 事后量只有终值)。 */
const samplerOn = (page) => page.evaluate(() => {
  const d = document.querySelector('.modal.move-dialog');
  const arr = [];
  window.__moveH = arr;
  const ro = new ResizeObserver(() => arr.push(Math.round(d.getBoundingClientRect().height)));
  ro.observe(d);
  window.__moveRO = ro;
});

const samplerOff = (page) => page.evaluate(() => {
  const ro = window.__moveRO;
  if (ro) ro.disconnect();
  return window.__moveH || [];
});

/**
 * 逐帧采样 body 的滚动条状态(四修/五修): 面板在 padding 过渡与离场淡出期间都留在 DOM 里, 而 body 是
 * overflow-y:auto 的滚动容器 ⇒ 会闪滚动条(并横向挤一个滚动条宽)。判据口径 = **面板在 DOM 的那一段**:
 * 只记面板存在的帧(离场后 body 回到 auto 是正确状态, 不该混进来); 无头 Chromium 是覆盖式滚动条,
 * offsetWidth-clientWidth 恒 0, 所以判据看计算值 overflowY, 不看占位宽。
 */
const sbSamplerOn = (page) => page.evaluate(() => {
  const body = document.querySelector('.modal.move-dialog .add-dialog-body');
  const arr = [];
  window.__moveSb = arr;
  const t0 = performance.now();
  const tick = () => {
    if (document.querySelector('.modal.move-dialog .pop-menu.add-pop')) {
      arr.push([getComputedStyle(body).overflowY, body.offsetWidth - body.clientWidth]);
    }
    if (performance.now() - t0 < 700) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
});

const sbSamplerOff = (page) => page.evaluate(() => window.__moveSb || []);

/**
 * 逐帧采样「对话框内容有没有被滚动」(八修): body.scrollTop 必须恒 0, 说明文案的屏坐标必须不动。
 * 症状是"选中过路径后再点下拉, 弹窗文案从上往下滑一次" —— 根因 _hiScroll 用 scrollIntoView,
 * 把 .add-dialog-body 这个祖先滚动容器也一起滚了。
 */
const scrollSamplerOn = (page) => page.evaluate(() => {
  const d = document.querySelector('.modal.move-dialog');
  const body = d.querySelector('.add-dialog-body');
  const note = d.querySelector('.move-note');
  const arr = [];
  window.__moveScroll = arr;
  const t0 = performance.now();
  const tick = () => {
    arr.push([Math.round(body.scrollTop), Math.round(note.getBoundingClientRect().top)]);
    if (performance.now() - t0 < 900) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
});

const scrollSamplerOff = (page) => page.evaluate(() => window.__moveScroll || []);

/** 高亮项是否真的落在列表可视区内(证明滚动跟随没被"修死") */
const hiVisible = (page) => page.evaluate(() => {
  const d = document.querySelector('.modal.move-dialog');
  const hi = d.querySelector('.pop-menu.add-pop [data-hi="1"]');
  const list = d.querySelector('.add-pop-list');
  const box = list || d.querySelector('.pop-menu.add-pop');
  if (!hi || !box) return { ok: false, why: hi ? 'no box' : 'no hi' };
  const hb = hi.getBoundingClientRect();
  const bb = box.getBoundingClientRect();
  return { ok: hb.top >= bb.top - 1 && hb.bottom <= bb.bottom + 1, hi: [Math.round(hb.top), Math.round(hb.bottom)], box: [Math.round(bb.top), Math.round(bb.bottom)] };
});

for (const skin of SKINS) {
  test.describe(`设定位置对话框 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`收层态基线 360 · 点输入框才展开 · 高度走过渡不跳变 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await openApp(page, skin);
      await clickRow(page, page.locator('.group-row').first(), { button: 'right' });
      await expect(page.locator('.ctx-menu')).toBeVisible();
      await ctxItem(page, '设定位置').click();

      const dlg = page.locator('.modal.move-dialog');
      const pop = dlg.locator('.pop-menu.add-pop');
      await expect(dlg).toBeVisible();
      await settleAnim(dlg);

      // —— ① 打开即收层态(2026-10-29 二修): 不自动展开 + 基线 360 + 空路径按钮置灰
      const closed0 = await geom(page);
      expect(closed0.popOpen, '打开对话框不应自动展开下拉(否则第一眼开层态, 一按 Esc 就塌 = 跳变)').toBe(false);
      expect(closed0.w, '设定位置对话框宽度(860 宽档, 与添加种子同宽)').toBe(860);
      expect(closed0.h, '收层态基线 360px(原实测 243px = 用户报的「窗口太小」)').toBeGreaterThanOrEqual(358);
      expect(closed0.bodyScroll, '收层态 body 无滚动').toBeLessThanOrEqual(0);
      expect(closed0.bodyOverflowY, '收层态 body 仍可滚(矮视口兜底, 四修只关开层期)').toBe('auto');
      expect(closed0.btnDisabled, '空路径时「设定位置」按钮应置灰(按钮是唯一鼠标提交路径)').toBe(true);

      // —— ② 点输入框展开: 高度必须是**过渡**过来的(采到中间态), 终值含 272 预留
      await samplerOn(page);
      await sbSamplerOn(page);  // 四修: 逐帧记 body 滚动条状态(过渡期面板伸出 body = 闪滚动条)
      await page.locator('#move-path').click();
      await expect(pop.locator('.pop-item').first()).toBeVisible({ timeout: 10_000 });
      await page.waitForTimeout(450);  // 过渡 200ms + settle 重测 240ms
      await settleAnim(dlg);

      const open = await geom(page);
      const samples = await samplerOff(page);
      const sbFrames = await sbSamplerOff(page);
      const mids = samples.filter((h) => h > closed0.h + 8 && h < open.h - 8);
      expect(open.popOpen, '点输入框后下拉应展开').toBe(true);
      expect(mids.length, '高度必须经过渡到达(采样到中间态); 一步到位 = 跳变回归').toBeGreaterThan(0);
      expect(open.h - closed0.h, '开层增量应≈预留 272(基线 360 → 515)').toBeGreaterThan(120);
      expect(open.popBelowBody, '下拉底缘不得超出 body 客户区底沿').toBeLessThanOrEqual(0);
      expect(open.bodyScroll, '开层后 body 无新增滚动').toBeLessThanOrEqual(0);
      expect(open.modalScroll, '开层后 modal 自身无新增滚动').toBeLessThanOrEqual(0);
      expect(open.listH, '列表未被限高截断(≤210 证明 settle 后净空算式无需兜底)').toBeLessThanOrEqual(211);
      expect(open.itemCount, '桩 300 种子应给出足量候选(足够溢出 210px 列表)').toBeGreaterThan(20);
      expect(open.rowBottomGap, '开层后输入行下方应有预留空间(≈272px)').toBeGreaterThan(200);
      // 四修: 开层全过程(含 padding 过渡的那 ~110ms)body 不得出现滚动条
      expect(sbFrames.length, '滚动条采样帧数为 0(采样器没挂上?)').toBeGreaterThan(0);
      const sbBad = sbFrames.filter(([oy, gut]) => oy !== 'hidden' || gut !== 0);
      expect(sbBad, '开层全过程 body 必须 overflow:hidden 且零滚动条占位(用户报的「一瞬间出现滚动条」)')
        .toEqual([]);
      // 三修几何不变量: 增长只朝下 —— 输入行(以及面板)不许随开层上移, 否则面板顶到光标底下
      expect(Math.abs(open.rowTop - closed0.rowTop), '开层后输入行屏坐标不得移动(增长只朝下)').toBeLessThanOrEqual(2);
      expect(Math.abs(open.dlgTop - closed0.dlgTop), '开层后对话框上缘不得移动').toBeLessThanOrEqual(2);
      expect(open.popTop, '下拉面板不得盖住输入框(修复前顶到光标底下, 再点一下即"自动弹回")')
        .toBeGreaterThanOrEqual(closed0.inputBottom);
      expect(open.dlgTop + open.h, '开层后对话框下缘不得溢出视口').toBeLessThanOrEqual(open.vh);
      for (const [i, h] of open.hits.entries()) {
        expect(h.isItem, `下拉第 ${i} 项应真实可点(不被动作条/遮罩盖住)`).toBe(true);
      }

      // —— ③ Esc 只收下拉不关对话框: 高度平滑回落到基线; 收层全过程同样不得出现滚动条(五修)
      await sbSamplerOn(page);  // 面板离场淡出期间仍在 DOM 里撑高度, 而 .pop-open 已摘
      await page.keyboard.press('Escape');
      await expect(pop).toBeHidden();
      await page.waitForTimeout(350);
      await settleAnim(dlg);
      const sbClose = await sbSamplerOff(page);
      const closed1 = await geom(page);
      expect(sbClose.length, '收层期滚动条采样帧数为 0(采样器没挂上?)').toBeGreaterThan(0);
      expect(sbClose.filter(([oy, gut]) => oy !== 'hidden' || gut !== 0),
        '收层全过程 body 必须 overflow:hidden(面板离场淡出期间它仍在 DOM 里, 用户报的「消失时仍闪滚动条」)')
        .toEqual([]);
      expect(Math.abs(closed1.h - closed0.h), '收层后高度应回到基线(±8px)').toBeLessThanOrEqual(8);
      expect(closed1.w, '收层后宽度不变').toBe(860);
      expect(closed1.bodyScroll, '收层后 body 无新增滚动').toBeLessThanOrEqual(0);
      expect(closed1.bodyOverflowY, '收层后面板已离场, body 回到 auto(矮视口兜底滚动)').toBe('auto');
    });

    test(`点选候选只回填 · 点「设定位置」才移动 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      // 写请求计数: 单种子/单组/多选都落在 /api/torrents/bulk(action=location); 回执走 cmd 轮询
      let writes = 0;
      await page.route('**/api/torrents/bulk', async (route) => {
        writes += 1;
        await route.fulfill({ json: { cmd_id: 'e2e-move-cmd' } });
      });
      await page.route('**/api/cmd/e2e-move-cmd', (route) => route.fulfill({ json: { status: 'ok' } }));

      await openApp(page, skin);
      await clickRow(page, page.locator('.group-row').first(), { button: 'right' });
      await expect(page.locator('.ctx-menu')).toBeVisible();
      await ctxItem(page, '设定位置').click();

      const dlg = page.locator('.modal.move-dialog');
      const pop = dlg.locator('.pop-menu.add-pop');
      await expect(dlg).toBeVisible();
      await page.locator('#move-path').click();
      const first = pop.locator('.pop-item').first();
      await expect(first).toBeVisible({ timeout: 10_000 });
      const picked = (await first.innerText()).trim();

      // —— 点选候选 = 只回填 + 收面板, 不移动(2026-10-29 报障「点选项就触发移动」)
      await first.click();
      await expect(pop).toBeHidden();
      await expect(dlg).toBeVisible();
      const afterPick = await geom(page);
      expect(afterPick.inputValue, '点选候选应把路径回填到输入框').toBe(picked);
      expect(writes, '点选候选不得发写请求(移动只由按钮/回车发起)').toBe(0);
      expect(afterPick.btnDisabled, '有路径后按钮应可用').toBe(false);

      // —— 点「设定位置」才真正移动
      await dlg.locator('.modal-actions .bt.primary').click();
      await expect.poll(() => writes, { timeout: 10_000 }).toBe(1);
      await expect(dlg).toBeHidden();
    });

    test(`同一屏幕点连点两次 · 面板不弹回 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await openApp(page, skin);
      await clickRow(page, page.locator('.group-row').first(), { button: 'right' });
      await expect(page.locator('.ctx-menu')).toBeVisible();
      await ctxItem(page, '设定位置').click();

      const dlg = page.locator('.modal.move-dialog');
      const pop = dlg.locator('.pop-menu.add-pop');
      await expect(dlg).toBeVisible();
      await page.waitForTimeout(700);

      // 真人手感: 按下/抬起隔 150ms(合成零延迟点击测不出按压时序竞态)
      const box = await page.locator('#move-path').boundingBox();
      if (!box) throw new Error('#move-path 没有 boundingBox');
      const cx = Math.round(box.x + box.width / 2);
      const cy = Math.round(box.y + box.height / 2);
      await page.mouse.move(cx, cy);
      await page.mouse.down();
      await page.waitForTimeout(150);
      await page.mouse.up();
      await expect(pop.locator('.pop-item').first()).toBeVisible({ timeout: 10_000 });
      await page.waitForTimeout(450);  // 过渡 200ms + settle 240ms 全跑完

      // —— 同一屏幕坐标再点一次: 修复前面板已顶到光标底下, 这一下命中候选行 = 面板"自动弹回"
      await page.mouse.down();
      await page.waitForTimeout(150);
      await page.mouse.up();
      await page.waitForTimeout(400);

      await expect(pop, '同一位置连点两次后面板必须还在(用户报的「出现后自动弹回」)').toBeVisible();
      expect(await page.locator('#move-path').inputValue(), '第二次点击不得回填候选').toBe('');
      expect((await geom(page)).inputValue, '第二次点击不得改写路径').toBe('');
    });

    test(`点面板头/空态不收起 · 面板内非交互区不抢焦点 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await openApp(page, skin);
      await clickRow(page, page.locator('.group-row').first(), { button: 'right' });
      await expect(page.locator('.ctx-menu')).toBeVisible();
      await ctxItem(page, '设定位置').click();

      const dlg = page.locator('.modal.move-dialog');
      const pop = dlg.locator('.pop-menu.add-pop');
      await expect(dlg).toBeVisible();
      await page.locator('#move-path').click();
      const head = pop.locator('.pop-head');
      await expect(head).toBeVisible({ timeout: 10_000 });
      await page.waitForTimeout(450);

      // —— 六修: 面板头「选择保存位置 N」是**纯展示区**, 点它什么都不该发生。修复前 mousedown 的
      //    默认动作把焦点从输入框抢走 → @focusout → movePathBlurClose 的 40ms 合帧定时器收层
      //    = 面板"点一下就消失"(光标本来就在候选行上方, 误触概率极高)
      await head.click();
      await page.waitForTimeout(300);  // > 40ms 合帧窗, 定时器该响的都响完了
      await expect(pop, '点面板头不得收起面板(非交互区抢焦点 → focusout → 合帧收层)').toBeVisible();
      expect(await page.locator('#move-path').inputValue(), '点面板头不得改写路径').toBe('');
      // 点完头面板仍是"活着"的: 候选照常可点(修复成"点了头顺手把面板冻住"也算坏)
      await pop.locator('.pop-item').nth(1).click();
      await expect(pop).toBeHidden();
      expect(await page.locator('#move-path').inputValue(), '点头之后候选仍须可点选回填').not.toBe('');
    });

    test(`按下与抬起落在不同元素 · 面板不收起 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await openApp(page, skin);
      await clickRow(page, page.locator('.group-row').first(), { button: 'right' });
      await expect(page.locator('.ctx-menu')).toBeVisible();
      await ctxItem(page, '设定位置').click();

      const dlg = page.locator('.modal.move-dialog');
      const pop = dlg.locator('.pop-menu.add-pop');
      await expect(dlg).toBeVisible();
      await page.waitForTimeout(700);

      const inputBox = await page.locator('#move-path').boundingBox();
      if (!inputBox) throw new Error('#move-path 没有 boundingBox');
      const cx = Math.round(inputBox.x + inputBox.width / 2);
      const cy = Math.round(inputBox.y + inputBox.height / 2);

      /** 无焦点按下 -> 按住 140ms(面板在这段里挂载) -> 抬到 (tx,ty) */
      const downThenUpAt = async (tx, ty) => {
        await page.mouse.move(cx, cy);
        await page.mouse.down();
        await page.waitForTimeout(140);
        await page.mouse.move(tx, ty, { steps: 4 });
        await page.mouse.up();
        await page.waitForTimeout(400);
      };

      // —— 变体 A: 抬到输入框下方 6px(行内留白 / 面板顶)。click 的 target 变成公共祖先
      //    `.add-input-row` —— 修复前它没有 @click.stop, 事件冒泡到 lifecycle 的 window 收层名单
      //    ⇒ 面板"点一下就消失"(七修, 排查「无焦点点击弹回」时复现)
      await page.locator('.move-note').click();  // 先失焦: 面板在按住期间才挂载, 落点才可能被改写
      await page.waitForTimeout(300);
      await downThenUpAt(cx, Math.round(inputBox.y + inputBox.height + 6));
      await expect(pop, '按下在输入框、抬到行内留白不得收起面板(click 目标 = 公共祖先 = 冒泡到 window 收层)')
        .toBeVisible();
      expect(await page.locator('#move-path').inputValue(), '这一路不得回填路径').toBe('');

      // —— 变体 B: 抬到候选行上(面板内部)。onPick 走 mousedown, 这一路只 mousemove/mouseup ⇒ 不得回填
      await downThenUpAt(cx, Math.round(inputBox.y + inputBox.height + 80));
      await expect(pop, '按下在输入框、抬到候选行不得收起面板(同上: 公共祖先 = .add-input-row)').toBeVisible();
      expect(await page.locator('#move-path').inputValue(), '抬到候选行不得回填(onPick 走 mousedown)').toBe('');

      // —— 反向守门: 真点到组件外(上方说明文案)仍必须收层 —— 防 @click.stop 挂得过宽
      await page.locator('.move-note').click();
      await expect(pop, '点组件外仍须收层(@click.stop 只许挡住组件内部的点击)').toBeHidden();
    });

    test(`选中候选后再点下拉 · 弹窗文案不滑动 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await openApp(page, skin);
      await clickRow(page, page.locator('.group-row').first(), { button: 'right' });
      await expect(page.locator('.ctx-menu')).toBeVisible();
      await ctxItem(page, '设定位置').click();

      const dlg = page.locator('.modal.move-dialog');
      const pop = dlg.locator('.pop-menu.add-pop');
      await expect(dlg).toBeVisible();

      // 先选中一条候选(路径回填, 面板收起) —— 用户报的正是"选中过新路径之后"再点下拉
      await page.locator('#move-path').click();
      await expect(pop.locator('.pop-item').first()).toBeVisible({ timeout: 10_000 });
      await page.waitForTimeout(450);
      await pop.locator('.pop-item').nth(4).click();
      await expect(pop).toBeHidden();
      const picked = await page.locator('#move-path').inputValue();
      expect(picked, '第 5 条候选应回填到输入框').not.toBe('');
      await page.waitForTimeout(400);

      // —— 八修: 再点下拉。修复前 _hiScroll 用 scrollIntoView, 把 .add-dialog-body(祖先滚动容器)
      //    也一起滚了 ⇒ body.scrollTop 0→166→83→18→0, 说明文案 top 352→186→269→334 = 用户看到的
      //    「元素从上往下滑动一次」。空输入时 hi=-1、没有 [data-hi="1"], 所以只有这条路才复现。
      await scrollSamplerOn(page);
      await page.locator('#move-path').click();
      await expect(pop).toBeVisible({ timeout: 5_000 });
      await page.waitForTimeout(1000);
      const frames = await scrollSamplerOff(page);
      expect(frames.length, '滚动采样帧数为 0(采样器没挂上?)').toBeGreaterThan(0);
      expect(frames.filter(([st]) => st !== 0).map(([st]) => st),
        '开层全过程 .add-dialog-body 的 scrollTop 必须恒 0(祖先容器被滚动 = 弹窗文案滑动)').toEqual([]);
      const tops = frames.map(([, t]) => t);
      const spread = Math.max(...tops) - Math.min(...tops);
      expect(spread, `说明文案屏坐标不得移动(实测极差 ${spread}px; 修复前 166px)`)
        .toBeLessThanOrEqual(2);

      // —— 反向守门: 滚动跟随不能"修死" —— 已选中那条候选必须仍在列表可视区内(高亮项可见)
      const hi = await hiVisible(page);
      expect(hi.ok, `高亮项必须在列表可视区内(滚动跟随仍生效): ${JSON.stringify(hi)}`).toBe(true);
    });
  });
}
