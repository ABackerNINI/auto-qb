// @ts-check
/**
 * e2e 共享手势库(计划 26-10-10-2001 S5 随参数化矩阵抽取) —— menus.spec.mjs 的本地辅助
 * **原样上移**(逐字保留, 含注释), 供 trigger-scope.spec.mjs 与 menus.spec.mjs 复用。
 * 上移理由: clickRow 这类 50 行精密函数(5 拍落点验证 + 修饰键 CDP 包夹)复制两份必漂移。
 * 断言口径与 D4 守则不变 —— 见 vm.mjs / probes.mjs 头注。
 */
import { expect } from '@playwright/test';
import { BASE_URL } from '../harness.mjs';
import { collectRuntimeErrors } from './errors.mjs';
import { readInst } from './vm.mjs';

/** 导航页签定位器(tpl/topbar.html `nav.tabs [data-view]`)。 */
export const tab = (page, view) => page.locator(`nav.tabs [data-view="${view}"]`);
/** 菜单项定位器(ctx 菜单是 div.ctx-item, 无 role, 按文案取)。 */
export const ctxItem = (page, text) => page.locator('.ctx-item', { hasText: text });

/**
 * 菜单项定位器(按注册表 id) —— 计划 26-10-20-0145 之后的**点击挂点**。
 * 四支菜单的 启动/停止/删除 文案已统一成「动词 + 灰色 N 个种子」, 同一 id(resume/pause/delete)
 * 在四支上都叫同一个词 —— 按文案点会分不清点了哪支, 也没有"唯一可见文案"可依赖。模板给每项绑了
 * `:data-item="it.id"`(registry id), 这里按它取; 分支与目标数另用 ctxMenuScope() 断言。
 * @param {import('@playwright/test').Page} page
 * @param {string} id —— 注册表 item id(resume / pause / delete / recheck / open-path …)
 */
export const ctxItemById = (page, id) => page.locator(`.ctx-item[data-item="${id}"]`);

/**
 * 当前行右键菜单的**作用域挂点**读值(计划 26-10-20-0145 D9): 容器上的 data-kind(四支分支名,
 * 与注册表 CTX_BRANCHES 同词: multi/episode/member/group)与 data-count(目标种子总数)。
 * 文案统一后四支可见文案趋同, scope 契约必须挂属性 —— 这里就是那个挂点的唯一读口。
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<{kind: string|null, count: number}>}
 */
export async function ctxMenuScope(page) {
  const menu = page.locator('.ctx-menu[data-kind]').first();
  await expect(menu).toBeVisible({ timeout: 5_000 });
  const kind = await menu.getAttribute('data-kind');
  const count = Number(await menu.getAttribute('data-count'));
  return { kind, count };
}

/**
 * 行点击统一入口: 真实鼠标手势 + 落点可验(对冲写法沿用 multiselect-shows.spec, 机理见其文件头:
 * 宽行居中滚动把 {x:8,y:8} 落点滚出裁剪面 ⇒ sticky-head/html 交替拦截 30s —— 这里 5 拍 arrange
 * + elementFromPoint 验落点, 拦截发生时立即带现场报错)。
 *
 * @param {import('@playwright/test').Page} page
 * @param {import('@playwright/test').Locator} row
 * @param {{button?: 'left'|'right', modifiers?: Array<'Control'|'Shift'|'Alt'|'Meta'>, point?: {x: number, y: number}}} [opts]
 *        point = 相对行盒的落点偏移, 默认行左缘 {x:8,y:8}。**成员行例外**: 其第一格就是
 *        .m-site(带 @click.stop 走筛选, kbd-members.spec 文件头同款纪律), 左缘落点会踩筛
 *        选 ⇒ 成员行调用方传第二格(.m-state, 无交互后代)偏移。
 * @returns {Promise<void>}
 */
export async function clickRow(page, row, opts = {}) {
  const { button = 'left', modifiers = [], point = { x: 8, y: 8 } } = opts;
  let last = null;
  for (let attempt = 0; attempt < 5; attempt++) {
    last = await row.evaluate(async (/** @type {HTMLElement} */ el, /** @type {{x: number, y: number}} */ pt) => {
      const cont = el.closest('.group-table');
      if (cont && cont.scrollLeft !== 0) cont.scrollLeft = 0;
      /* 拦截面 = **所有** .sticky-head 下沿的最大值(文档里不止一个: 顶栏条与表头各有其一) ——
       * 只取 querySelector 的头一个会低估拦截面, 落点被表头吃掉后 5 拍都不自愈。 */
      const guard = [...document.querySelectorAll('.sticky-head')]
        .reduce((m, h) => Math.max(m, h.getBoundingClientRect().bottom), 0);
      const vh = window.innerHeight;
      const pad = 8;    // 落点纪律同款余量(行左缘 8,8)
      let r = el.getBoundingClientRect();
      /* 行高于"可用视口"时, 居中滚动会把行顶推到视口**上方** ⇒ 落点 y 为负 ⇒ elementFromPoint
       * 恒回 null, 5 拍全部空转(issue 26-10-18-2226: 3000 种子下每集 ~142 个版本把集行的
       * .g-sites 格堆到 1198px ⇒ 行高 1220px > 900px 视口 ⇒ 居中后 r.top = -160)。
       * 这种行改用 start 对齐(行顶贴滚动口顶), 落点再钳进"行盒 ∩ (视口 - 拦截面)"。 */
      const tall = r.height > vh - guard - pad * 2;
      if (r.top < guard + pad || r.bottom > vh - pad) {
        el.scrollIntoView({ block: tall ? 'start' : 'center', behavior: 'instant' });
        await new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(res)));
        r = el.getBoundingClientRect();
      }
      const lo = Math.max(r.top + pad, guard + pad);
      const hi = Math.min(r.bottom - pad, vh - pad);
      const y = lo <= hi ? lo : NaN;   // 可落区为空 ⇒ 本拍作废, 交给下一拍重排
      const x = r.left + pt.x;        // 水平偏移可覆盖(成员行避让第一格 .m-site), 垂直仍走拦截面钳位
      const hit = Number.isFinite(y) ? document.elementFromPoint(x, y) : null;
      return {
        x, y,
        ok: !!hit && (hit === el || el.contains(hit)),
        hit: hit ? `${hit.tagName}.${String(hit.className && hit.className.baseVal !== undefined ? hit.className.baseVal : hit.className || '')}`.slice(0, 60) : '(null)',
      };
    }, point);
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
export async function openApp(page, skin) {
  collectRuntimeErrors(page);
  await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
}

/**
 * 断言右键菜单已打开, 返回菜单项文本数组(供"含什么/不含什么"两类断言共用)。
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<string[]>}
 */
export async function openMenuTexts(page) {
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
export async function pickRows(page, n) {
  const rows = page.locator('.torrent-row');
  for (let i = 0; i < n; i++) {
    await clickRow(page, rows.nth(i), { modifiers: ['Control'] });
  }
  const picked = await readInst(page, 'vm.selMembers.slice()');
  expect(picked, `Ctrl+click ${n} 行后选中集合(selMembers)`).toHaveLength(n);
  return /** @type {string[]} */ (picked);
}

/** bulk POST 计数 + 末条载荷捕获(载荷形状断言共用口径)。 */
export const bulkTap = (/** @type {import('@playwright/test').Page} */ page) => {
  const hits = { n: 0, body: /** @type {string|null} */ (null) };
  const onReq = (/** @type {import('@playwright/test').Request} */ r) => {
    if (r.url().includes('/api/torrents/bulk')) { hits.n++; hits.body = r.postData(); }
  };
  page.on('request', onReq);
  return { hits, off: () => page.off('request', onReq) };
};

/** 单目标组路径 POST 计数(捕获 `/api/groups/{key}/{action}` 的 key 与 action)。 */
export const groupActionTap = (/** @type {import('@playwright/test').Page} */ page) => {
  const hits = { n: 0, key: '', action: '' };
  const onReq = (/** @type {import('@playwright/test').Request} */ r) => {
    if (r.method() !== 'POST') return;
    const m = /\/api\/groups\/([^/?]+)\/([a-z_]+)(\?|$)/.exec(r.url());
    if (m) { hits.n++; hits.key = decodeURIComponent(m[1]); hits.action = m[2]; }
  };
  page.on('request', onReq);
  return { hits, off: () => page.off('request', onReq) };
};

/** 单目标种子路径 POST 计数(捕获 `/api/torrents/{hash}/{action}` 的 hash 与 action)。 */
export const torrentActionTap = (/** @type {import('@playwright/test').Page} */ page) => {
  const hits = { n: 0, hash: '', action: '' };
  const onReq = (/** @type {import('@playwright/test').Request} */ r) => {
    if (r.method() !== 'POST') return;
    const m = /\/api\/torrents\/([^/?]+)\/([a-z_]+)(\?|$)/.exec(r.url());
    if (m) { hits.n++; hits.hash = decodeURIComponent(m[1]); hits.action = m[2]; }
  };
  page.on('request', onReq);
  return { hits, off: () => page.off('request', onReq) };
};
