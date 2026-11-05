// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 主表横滚指示条的行为面守阵(计划 26-11-01-0553 S5; 实现 = shared/hscroll.css + shared/columns.js)。
 *
 * **钉的是什么**: 原生横条被彻底隐藏后, 底部胶囊(300x5, hover 7)是唯一的横向可达入口 ——
 * ①窄窗下列真的溢出时原生条**不占条槽**(否则每行底部白丢 10px 且胶囊与条槽叠在一起); ②隐藏条槽后
 * 仍能横滚; ③指针伸到内容区底部 24px 热区带内胶囊才淡入(常态零痕迹); ④拖胶囊真的改 `scrollLeft`,
 * 且**表头跟着同步**(R2: 拖动是程序化写 scrollLeft, 只信"scroll 事件会触发"的推断不够);
 * ⑤宽窗无溢出时热区内也不出现; ⑥召唤范围(纵向不含状态栏 / 横向只认胶囊邻域 / Shift+滚轮也召唤)。
 *
 * **为什么静态守阵(S4, tests/test_webui_static_skins.py)不够**: 那条只能读源码文本 —— 它看得出
 * `display: none` 在不在、link 挂没挂, 但看不出**几何是否真的生效**: `::-webkit-scrollbar{display:none}`
 * 被更高特异性的规则压掉、`scrollbar-width` 拼错、`.hscroll-pill` 被别的 `opacity` 规则覆盖、
 * `syncHeadScroll` 尾部那行 `_hscrollSync` 被删但静态锚点仍在 —— 这四类都只在真浏览器里有结果。
 * 静态守阵管"写了没有", 本 spec 管"生效没有", 两层缺一不可(D9 双验)。
 *
 * **覆盖切分(不 ×2 皮肤 ×3 视图 ×5 断言全排列, 那只是把同一单点重复验 6 遍)**:
 *   · 无条槽 / 仍可横滚 / 热区淡入 —— 三视图全跑。这三条的成本只有一次页面加载, 而"溢出 → 建 DOM →
 *     淡入"在三个视图上走的是**三条不同的模板分支**(groups/torrents/shows 各自的 .group-table 与 ref),
 *     值得各验一次。
 *   · 拖动 + 表头同步 —— 只跑辅种表。三视图共用**同一份** `syncHeadScroll` 与同一个胶囊单例
 *     (columns.js 里没有按 page 分支的实现), 换视图再验一遍等于验同一个单点, 只是多花一次加载。
 *   · 宽窗负例 —— 只跑辅种表一次(同上: 无溢出路径在 `_hscrollSync` 里也是单点早退)。
 *   · 召唤范围(不含状态栏 / 横向只认胶囊邻域 / Shift+滚轮) —— 只跑辅种表一次。三条判据全在
 *     `_hscrollBand` / `_hscrollInPillSpan` / `_hscrollWheel` 三个单点里, 与视图无关。
 * 皮肤仍走 SKINS 双跑: 胶囊外观与 `--statusbar-h` 是三皮肤各自声明的, 热区 y 由实测状态栏高算出,
 * 换皮肤能抓到"某皮肤状态栏更高 → 热区带错位"。console 皮肤不在 e2e 覆盖内(既有全局口径), 其一致性
 * 由静态守阵覆盖, 故不动 SKINS。
 *
 * **窗口取值是实测定的, 不是猜的**: 窄窗 1000×700(仓库既有 NARROW 口径)下三视图都确认溢出;
 * 宽窗必须宽过辅种表可见列的 `minmax` 最小宽之和(默认隐藏 amount_left 后约 2074px), 故取 2400×900
 * —— 1600/2000 仍会溢出, 会让负例变成"什么都没验"的空过。两个方向都把"已确认溢出/未溢出"写成
 * **显式前置断言**: 视口漂了(列模型加列、媒体查询改行宽)会红在这里, 而不是静默退化成空过。
 *
 * **实测环境注意(本 spec 的红绿双验结论)**: 本仓库的 headless Chromium 用 **overlay 滚动条** ——
 * `offsetHeight - clientHeight` 在"原生条可见"时实测同样是 0, 故计划 S5 ① 的那条几何断言在当前环境
 * 永远不会红(换成经典滚动条的环境才有效)。真正的非空过证据是紧随其后的计算样式断言
 * (`::-webkit-scrollbar` 的 computed `display` / `scrollbar-width`): 删掉 hscroll.css 的隐藏规则
 * 会立刻变 `inline` / `thin`, 实测红绿双验过。
 */

const VIEWS = [
  { view: 'groups', label: '辅种表' },
  { view: 'torrents', label: '种子表' },
  { view: 'shows', label: '追剧表' },
];

/** 窄窗: 列宽和远超视口, 三视图都溢出(实测见文件头)。 */
const NARROW = { width: 1000, height: 700 };
/** 宽窗: 必须宽过辅种表可见列最小宽之和(~2074px), 否则负例无效。 */
const WIDE = { width: 2400, height: 900 };

const TABLE = '.group-table';
const headSel = (table) => `.group-head[data-table="${table}"]`;

/**
 * 负条件观察窗(观察程序参数, 非条件等待): 「危险触发已给到(热区 mousemove / ResizeObserver
 * 回调)但不该有痕迹」没法用 expect.poll 表达 —— 首拍即中会提前通过, 窗必须真实流逝才给
 * 「RO 回调 / 淡出过渡 / 定时器抖动」留出暴露时长, 窗后读胶囊状态断言。走 Node 侧 setTimeout
 * (不占页面时钟); e2e setTimeout 审计口径: 观察/业务延迟语义, 保留并注释。
 * @param {number} ms
 */
const observeWindow = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** 打开某个主表页签并等首行出来(与 main-table-pinned-hover.spec.mjs 同一范式)。 */
async function openView(page, skin, view) {
  await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
  await page.click(`nav.tabs [data-view="${view}"]`);
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
  await expect(page.locator(TABLE)).toBeVisible();
}

/** 主表容器的横滚几何。offsetHeight - clientHeight = 横向条槽高度(经典滚动条下, 隐藏失败时是 10px)。 */
function readGeo(page) {
  return page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    return {
      sw: el.scrollWidth,
      cw: el.clientWidth,
      oh: el.offsetHeight,
      ch: el.clientHeight,
      // 该元素上"画不画原生条"的**计算值**(不是源码文本): 证明 hide 规则真的命中这个元素
      scrollbarWidth: getComputedStyle(el).scrollbarWidth,
      webkitBarDisplay: getComputedStyle(el, '::-webkit-scrollbar').display,
    };
  }, TABLE);
}

/** 胶囊状态: 是否存在 / 是否 .on / 计算后的 opacity(过渡中的中间值也读得到)。 */
function pillState(page) {
  return page.evaluate(() => {
    const p = document.querySelector('.hscroll-pill');
    if (!p) return { exists: false, on: false, opacity: 0 };
    return { exists: true, on: p.classList.contains('on'), opacity: parseFloat(getComputedStyle(p).opacity) };
  });
}

/**
 * 底部热区的一个落点 —— 页面内实测, 不写死数字: 视口中央 x, 状态栏上缘再往上 12px。
 * 同时把热区公式的三个输入一起带回来, 供调用方自检(公式错位时红在自检上, 而不是"移过去了但没触发"
 * 这种看起来像实现缺陷的假象)。
 */
function hotSpot(page) {
  return page.evaluate(() => {
    const bar = document.querySelector('.statusbar');
    const sbH = bar ? bar.getBoundingClientRect().height : 0;
    const ih = window.innerHeight;
    return {
      x: Math.round(window.innerWidth / 2),
      y: Math.round(ih - sbH - 12),
      ih,
      sbH,
      bandTop: ih - sbH - 24,  // 热区上界(columns.js: clientY >= innerHeight - 状态栏高 - 24)
    };
  });
}

/** 表头与容器的横滚同步三件套: scrollLeft / 表头**内联** --head-pin-x / 容器 is-hscrolled 打标。 */
function readSync(page, table) {
  return page.evaluate(({ tableSel, head }) => {
    const el = document.querySelector(tableSel);
    const h = document.querySelector(head);
    return {
      x: el ? el.scrollLeft : -1,
      pin: h ? h.style.getPropertyValue('--head-pin-x').trim() : null,
      cls: el ? el.classList.contains('is-hscrolled') : false,
    };
  }, { tableSel: TABLE, head: headSel(table) });
}

for (const skin of SKINS) {
  test.describe(`主表横滚指示条 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    /* ---------- 1. 无条槽 + 仍可横滚 + 热区淡入(三视图) ----------
     * 各段独立: ①/①'条槽(几何 + 计算样式) ②可滚(能力) ③淡入(触发链)。
     * 删掉 hscroll.css 的隐藏规则只红 ①'; 把 .group-table 的 overflow-x 改成 hidden 只红 ②;
     * 删掉 _hscrollBind/_hscrollHot 只红 ③。 */
    for (const v of VIEWS) {
      test(`无条槽 + 可横滚 + 热区淡入: ${v.label} @fast (${skin})`, async ({ page }) => {
        collectRuntimeErrors(page);
        await page.setViewportSize(NARROW);
        await openView(page, skin, v.view);

        // 前置: 列确实溢出(不溢出则本用例验不到任何东西)
        const geo = await readGeo(page);
        expect(geo, `${v.label} 取不到 ${TABLE}(结构变了?)`).not.toBeNull();
        expect(geo.sw, `${v.label} 窄窗前置: 列未溢出(${geo.sw} <= ${geo.cw}) —— 本用例验不到任何东西, ` +
          '视口还要更窄(或列模型变窄了)').toBeGreaterThan(geo.cw);

        // ① 无条槽(几何面, 计划 S5 的验收口径): offsetHeight - clientHeight 就是横向条槽高,
        //    经典滚动条下隐藏失败时是全局 ::-webkit-scrollbar 的 10px。
        //    ⚠ 本 headless Chromium 用的是 **overlay 滚动条**: 不占条槽 ⇒ 这条差值在"有原生条"时
        //    实测也是 0(单独验过), 单靠它在当前环境永远不会红。故紧接着补 ①' 作为同一件事的
        //    非空过证据(否则这条就只是安慰剂 —— 留着是因为换成经典滚动条的环境/浏览器时它才是有牙齿的)。
        expect(geo.oh - geo.ch, `${v.label} 原生横条仍占条槽: offsetHeight(${geo.oh}) - clientHeight(${geo.ch}) ` +
          `= ${geo.oh - geo.ch}px(应为 0; 10 = 全局 ::-webkit-scrollbar 高度, 说明隐藏规则没生效)`).toBe(0);

        // ①' hide 规则真的命中这个元素(计算值, 不是源码文本): 静态守阵只能证明"文件里有这行",
        //    证明不了它没被更高特异性的规则压掉、也证明不了本皮肤真的链到了 hscroll.css。
        expect(geo.webkitBarDisplay, `${v.label} .group-table 的原生条仍在绘制(::-webkit-scrollbar 计算 display=` +
          `${geo.webkitBarDisplay}, 应为 none)`).toBe('none');
        expect(geo.scrollbarWidth, `${v.label} scrollbar-width 计算值=${geo.scrollbarWidth}(应为 none)`).toBe('none');

        // ② 仍可横滚: 隐藏的是"条", 不是"能力"(单独再断一次 —— 别让它被上面的前置断言吞掉)
        expect(geo.sw, `${v.label} 隐藏条槽后失去横滚能力: scrollWidth(${geo.sw}) <= clientWidth(${geo.cw})`)
          .toBeGreaterThan(geo.cw);

        // ③ 热区淡入。先确认热区外零痕迹(胶囊可能压根不存在 —— 它是溢出判定后才惰性建的 DOM)
        const hot = await hotSpot(page);
        expect(hot.sbH, `${v.label} 量不到 .statusbar 高度(${hot.sbH}) —— 热区公式失效, 落点无意义`)
          .toBeGreaterThan(0);
        expect(hot.y, `${v.label} 自检: 落点 y=${hot.y} 不在热区带内[${hot.bandTop}, ${hot.ih - hot.sbH})`)
          .toBeGreaterThanOrEqual(hot.bandTop);
        expect(hot.y, `${v.label} 自检: 落点 y=${hot.y} 落进状态栏(${hot.ih - hot.sbH} 起)`).toBeLessThan(hot.ih - hot.sbH);

        await page.mouse.move(hot.x, Math.round(hot.ih / 2));
        const idle = await pillState(page);
        expect(idle.exists && idle.opacity > 0.01, `${v.label} 指针还在页面中部, 胶囊就已可见` +
          `(exists=${idle.exists}, opacity=${idle.opacity}) —— 热区纪律破了`).toBe(false);

        await page.mouse.move(hot.x, hot.y, { steps: 4 });
        await page.waitForSelector('.hscroll-pill', { state: 'attached', timeout: 5_000 });
        // 淡入 150ms: 轮询等收敛, 不用固定 sleep
        await expect.poll(async () => (await pillState(page)).opacity, {
          message: `${v.label} 指针进入底部热区后胶囊没淡入(opacity 应 > 0.9)`,
          timeout: 5_000,
        }).toBeGreaterThan(0.9);
        expect((await pillState(page)).on, `${v.label} 胶囊可见却缺 .on class(pointer-events 仍为 none, 拖不动)`)
          .toBe(true);
      });
    }

    /* ---------- 2. 拖动真的横滚 + 表头同步(仅辅种表) ----------
     * R2 的正面证据: 拖动改的是 scrollLeft(不是手工调 syncHeadScroll), 表头位移/--head-pin-x/打标
     * 必须由 scroll 事件链路自己跟上。三条一起断: 只红一条说明是链路某一段断了, 不是"整体没动"。 */
    test(`拖动胶囊真的横滚且表头同步: 辅种表 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(NARROW);
      await openView(page, skin, 'groups');

      const geo = await readGeo(page);
      expect(geo.sw, '窄窗前置: 列未溢出 —— 拖动用例无从验起').toBeGreaterThan(geo.cw);

      // 先把胶囊召唤出来(热区内才 pointer-events: auto; 不可见时 mouse.down 根本落不到它身上)
      const hot = await hotSpot(page);
      await page.mouse.move(hot.x, Math.round(hot.ih / 2));
      await page.mouse.move(hot.x, hot.y, { steps: 4 });
      await expect.poll(async () => (await pillState(page)).on, {
        message: '胶囊没有进入 .on(热区没触发或该视图无溢出)',
        timeout: 5_000,
      }).toBe(true);

      const before = (await readSync(page, 'group')).x;

      // 落在滑块上按下(落在轨道其余位置会先跳转 —— 那样测到的就不是"拖"了)
      const thumb = await page.evaluate(() => {
        const t = document.querySelector('.hscroll-pill > i');
        if (!t) return null;
        const r = t.getBoundingClientRect();
        return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
      });
      expect(thumb, '胶囊里没有滑块 <i>(DOM 契约: <div class="hscroll-pill"><i></i></div>)').not.toBeNull();
      await page.mouse.move(thumb.x, thumb.y);
      await page.mouse.down();
      await page.mouse.move(thumb.x + 50, thumb.y, { steps: 8 });
      await page.mouse.up();

      // 程序化写 scrollLeft 触发的 scroll 事件是异步派发的: 轮询等同步链跑完
      await expect.poll(async () => {
        const s = await readSync(page, 'group');
        return Math.abs(parseFloat(s.pin) - s.x) < 1 && s.cls;
      }, {
        message: '拖动后表头没跟上: --head-pin-x 与容器 scrollLeft 不等, 或容器缺 is-hscrolled',
        timeout: 5_000,
      }).toBe(true);

      const after = await readSync(page, 'group');
      expect(after.x, `拖动 50px 后 scrollLeft 没变(${before} -> ${after.x}) —— 胶囊拖不动`).toBeGreaterThan(before);
      expect(after.cls, 'scrollLeft > 0 但容器没打 is-hscrolled(首列吸左落影不出现)').toBe(true);
      // 阈值 1px 不是放宽: 拖动算出的 scrollLeft 是小数, 内联串可能被取整; 真不同步的差值在百 px 量级
      expect(Math.abs(parseFloat(after.pin) - after.x), `表头 --head-pin-x(${after.pin}) 与 scrollLeft(${after.x}) 不同步`)
        .toBeLessThan(1);
    });

    /* ---------- 3. 宽窗负例(仅辅种表) ----------
     * D10: 常态下不给任何"可横滚"提示。负例最怕空过, 故 ①把"确实不溢出"写成前置 ②注入一次性
     * mousemove 计数, 证明热区事件真的到过 document(否则"没出现"只是因为指针压根没动)。 */
    test(`宽窗无溢出: 热区内也不出现指示条 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await openView(page, skin, 'groups');

      const geo = await readGeo(page);
      expect(geo.sw, `宽窗前置: 仍溢出(${geo.sw} > ${geo.cw}) —— 本负例无效, 请把视口再调宽`).toBe(geo.cw);

      // 有效性探针: 计数器只证明"热区 mousemove 到过 document", 不改被测状态
      await page.evaluate(() => {
        window.__hscrollProbe = 0;
        document.addEventListener('mousemove', () => { window.__hscrollProbe += 1; }, { passive: true });
      });
      const hot = await hotSpot(page);
      await page.mouse.move(hot.x, Math.round(hot.ih / 2));
      await page.mouse.move(hot.x, hot.y, { steps: 4 });
      expect(await page.evaluate(() => window.__hscrollProbe),
        '负例有效性: 热区 mousemove 没到过 document, 本用例是空过').toBeGreaterThan(0);

      // ResizeObserver 回调与淡出都是异步的, 给一个合帧 + 过渡窗口再断言"没有痕迹"
      // (负条件观察窗, 见 observeWindow 注)
      await observeWindow(300);
      const st = await pillState(page);
      expect(st.on, `宽窗热区内胶囊被点亮了(无横向余量却给"可横滚"提示, D10)`).toBe(false);
      expect(st.opacity, `宽窗热区内胶囊 opacity=${st.opacity}(应为 0)`).toBe(0);
      expect(st.exists && st.opacity > 0.01, `宽窗下出现了可见胶囊(exists=${st.exists}, opacity=${st.opacity})`).toBe(false);
    });

    /* ---------- 4. 召唤范围 + Shift+滚轮(2026-11-01 用户验收后补) ----------
     * 三条都是**用户当场指出的**行为, 静态守阵一条也抓不到(全是运行时几何/事件判据):
     *   a. 纵向带**不含状态栏** —— 初版只写下界 `clientY >= innerHeight - 状态栏高 - 24`, 少了上界,
     *      于是状态栏那 34px 也落在带内; 状态栏是常用控件区(铃铛/速度/限速), 移过去不该召唤胶囊。
     *   b. 横向**不是全屏宽** —— 初版只判 clientY, 鼠标扫过底部右侧的速度/限速区也会召唤;
     *      现在只认胶囊本身的邻域(胶囊宽 + 左右各 40px)。
     *   c. **Shift+滚轮 / 触控板双指横滚时亮出**, 停手 1.5s 自落 —— 这类用户不需要伸到热区,
     *      但横滚时同样缺位置反馈。
     * 只跑辅种表: 三条判据都在 columns.js 的单点里(_hscrollBand / _hscrollInPillSpan / _hscrollWheel),
     * 与视图无关; 换视图只是多花一次加载。 */
    test(`召唤范围: 不含状态栏 / 不限全屏宽 / Shift+滚轮 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(NARROW);
      await openView(page, skin, 'groups');

      const geo = await readGeo(page);
      expect(geo.sw, `前置: 列未溢出(${geo.sw} <= ${geo.cw}) —— 本用例验不到召唤行为`).toBeGreaterThan(geo.cw);

      const hot = await hotSpot(page);
      const sbCenterY = Math.round(hot.ih - hot.sbH / 2);   // 状态栏正中
      const midY = Math.round(hot.ih / 2);                  // 内容区中部(离带很远)

      // 基线: 指针在内容区中部 -> 不出现(证明下面的"不出现"不是因为它压根没亮过)
      await page.mouse.move(hot.x, midY);
      await observeWindow(300); // 负条件观察窗, 见 observeWindow 注
      expect((await pillState(page)).on, '前置: 指针在内容区中部却亮了胶囊').toBe(false);

      // a. 状态栏本身不召唤
      await page.mouse.move(hot.x, sbCenterY);
      await observeWindow(350); // 负条件观察窗, 见 observeWindow 注
      expect((await pillState(page)).on,
        `指针在状态栏(y=${sbCenterY})却亮了胶囊 —— 热区带把状态栏也算进去了(应只到状态栏上缘为止)`).toBe(false);

      // b. 带内但横向远离胶囊(视口左缘)也不召唤
      await page.mouse.move(20, hot.y);
      await observeWindow(350); // 负条件观察窗, 见 observeWindow 注
      expect((await pillState(page)).on,
        `指针在热区带内但 x=20(远离居中的胶囊)却亮了胶囊 —— 横向判据退化成全屏宽`).toBe(false);

      // b'. 回到胶囊正上方 -> 该出现(证明 a/b 的"没出现"不是因为整条链坏了)
      await page.mouse.move(hot.x, hot.y, { steps: 4 });
      await expect.poll(async () => (await pillState(page)).on, {
        message: `指针移到胶囊正上方(y=${hot.y})仍不亮 —— 热区判据被改坏了(或横向窗口太窄)`,
        timeout: 4_000,
      }).toBe(true);

      // c. Shift+滚轮: 先把指针移出热区(否则 hot 会一直兜着), 再横滚
      await page.mouse.move(hot.x, midY);
      // 旧 300ms 睡等「移出热区后该落」→ poll 等 .on 摘除, 上限同值(300ms 内必须落, 收紧即断言;
      // 移出前它是亮着的, poll 不会首拍提前通过)
      await expect.poll(async () => (await pillState(page)).on, {
        message: '前置: 指针已移出热区却仍亮着(300ms 内未落)', timeout: 300,
      }).toBe(false);

      await page.keyboard.down('Shift');
      await page.mouse.wheel(0, 200);   // Shift+纵向滚轮 = 浏览器原生横滚
      await page.keyboard.up('Shift');
      await expect.poll(async () => (await pillState(page)).on, {
        message: 'Shift+滚轮后胶囊没亮 —— 横滚时没有任何位置反馈',
        timeout: 2_000,
      }).toBe(true);

      // 停手 1.5s 后自落(留 300ms 给 200ms 淡出过渡 + 定时器抖动)
      await expect.poll(async () => (await pillState(page)).on, {
        message: 'Shift+滚轮停手 1.5s 后胶囊没落下 —— 停留定时器没生效, 它会一直挂在屏上',
        timeout: 4_000,
      }).toBe(false);
    });
  });
}
