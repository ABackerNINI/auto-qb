// @ts-check
/**
 * RM04-15 浏览器侧取证: 四皮肤行高 / 浮窗定位与滚动 / Esc 退栈 / 组行入口。
 *
 * 契约(全部经环境变量):
 *   RM_UI_BASE         http://127.0.0.1:<web_port>
 *   RM_UI_GROUP_A      已发起迁移的组名(组行/种子行带 rel-badge)
 *   RM_UI_GROUP_A_SAVE 搬移成员所在组行的保存路径片段(搬移完成后源/目标分成两组, 用路径消歧)
 *   RM_UI_GROUP_A_SRC  源组(未搬移成员)的保存路径片段(可选: 组行入口对照取证)
 *   RM_UI_NONMOVER     未搬移成员 hash(可选: 源组徽标的预期目标)
 *   RM_UI_GROUP_B      未迁移的对照组名(无徽标)
 *   RM_UI_MOVER        组内搬移成员 hash(组行徽标 -> drawer/chain 的预期目标)
 *   RM_UI_CHAIN_HASH   人工多层 junction 链所在种子的 hash(长链滚动取证用)
 *   RM_UI_OUT          截图输出目录
 * 输出: 最后一行 `UI_RESULT {json}`; 任一步失败退出码 1。
 *
 * 纪律: 只读写临时产品实例(副实例 qB), 不触碰用户数据; 截图落 RM_UI_OUT(gitignored .work)。
 */
import { chromium } from 'playwright';
import fs from 'node:fs';

const base = (process.env.RM_UI_BASE || '').replace(/\/$/, '');
const groupA = process.env.RM_UI_GROUP_A || '';
const groupASave = process.env.RM_UI_GROUP_A_SAVE || '';
const groupB = process.env.RM_UI_GROUP_B || '';
const mover = process.env.RM_UI_MOVER || '';
const chainHash = process.env.RM_UI_CHAIN_HASH || '';
const outDir = process.env.RM_UI_OUT || '';

if (!base || !groupA || !groupB || !mover || !chainHash || !outDir) {
  console.error('RM_UI_BASE / GROUP_A / GROUP_B / MOVER / CHAIN_HASH / OUT 必须给齐');
  process.exit(2);
}
fs.mkdirSync(outDir, { recursive: true });

const SKINS = ['prism', 'atlas', 'flux', 'console'];
const VW = 1680;
const VH = 1000;
const out = { skins: {}, placement: {}, groupEntry: {}, chainRequests: [], steps: [], pageErrors: [], ok: false };
const step = (name, extra) => out.steps.push({ name, ...(extra || {}) });

/** 以根实例 Proxy 受控调用(与 UI 同一实例; 只用于读取证状态与打开/关闭浮窗) */
async function vmEval(page, bodyString, arg) {
  return page.evaluate(
    ([body, a]) => {
      const root = document.querySelector('#app');
      const app = root && root.__vue_app__;
      const inst = app && (app._instance || (app._container && app._container._vnode && app._container._vnode.component));
      const vm = inst && inst.proxy;
      if (!vm) throw new Error('取不到 Vue 根实例: app=' + (app ? Object.keys(app).join(',') : 'none'));
      const f = new Function('vm', 'a', 'return (' + body + ')(vm, a)');
      return f(vm, a);
    },
    [bodyString, arg],
  );
}

function rowSelector(name) {
  return new RegExp('^' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '$');
}

/**
 * 组行定位: 搬移完成后源/目标 save_path 不同 -> 同名组会拆成两行,
 * 必须再用保存路径片段消歧; savePart 为空时退回「同名第一行」。
 */
function rowOfGroup(page, name, savePart) {
  let rows = page
    .locator('.group-row[data-table="group"]')
    .filter({ has: page.locator('.g-name-text', { hasText: rowSelector(name) }) });
  if (savePart) rows = rows.filter({ has: page.locator('.g-save-path', { hasText: savePart }) });
  return rows.first();
}

function rowsOfTorrent(page, name) {
  return page
    .locator('.group-row.torrent-row[data-hash]')
    .filter({ has: page.locator('.g-name-text', { hasText: rowSelector(name) }) });
}

async function gotoSkin(page, skin) {
  await page.goto(`${base}/${skin}/`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await page.waitForFunction(
    ([a, b]) => {
      const names = [...document.querySelectorAll('.group-row[data-table="group"] .g-name-text')].map((e) => e.textContent.trim());
      return names.includes(a) && names.includes(b);
    },
    [groupA, groupB],
    { timeout: 30_000 },
  );
}

async function closeAll(page) {
  await vmEval(page, `(vm) => {
    if (vm.relChain && vm.relChain.open) vm.relChainClose(false);
    if (vm.drawer && vm.drawer.open) {
      if (typeof vm.closeDrawer === 'function') vm.closeDrawer();
      else vm.drawer.open = false;
    }
  }`);
  await page.waitForTimeout(150);
}

async function measureRow(page, rowLocator, label) {
  const badge = rowLocator.locator('.rel-badge');
  const badgeCount = await badge.count();
  const rowBox = await rowLocator.boundingBox();
  const cellBox = await rowLocator.locator('.g-save-path').first().boundingBox();
  let badgeBox = null;
  if (badgeCount) badgeBox = await badge.first().boundingBox();
  const metrics = await rowLocator.evaluate((row) => {
    const cell = row.querySelector('.g-save-path');
    const body = cell && cell.querySelector('.sp-body');
    const cs = cell ? getComputedStyle(cell) : null;
    return {
      whiteSpace: cs ? cs.whiteSpace : '',
      cellTextScrollW: body ? body.scrollWidth : 0,
      cellClientW: body ? body.clientWidth : 0,
    };
  });
  const rowH = rowBox ? Math.round(rowBox.height) : 0;
  const inRow = !!(badgeBox && rowBox && badgeBox.y >= rowBox.y - 0.5 && badgeBox.y + badgeBox.height <= rowBox.y + rowBox.height + 0.5);
  const inCell = !!(badgeBox && cellBox && badgeBox.x >= cellBox.x - 1 && badgeBox.x + badgeBox.width <= cellBox.x + cellBox.width + 1);
  return {
    label, rowH, badgeCount,
    badgeH: badgeBox ? Math.round(badgeBox.height) : 0,
    badgeBox, rowBox, cellBox, inRow, inCell, ...metrics,
  };
}

async function openChain(page, locator) {
  const before = out.chainRequests.length;
  // 先把锚点滚进视口并等滚动事件落地: 否则 Playwright click 的自动滚动会在浮窗打开后
  // 再派发一次 scroll, 被「滚动关闭」监听立刻关掉(实测会表现为 open=false 且无 .relc-pop)。
  await locator.scrollIntoViewIfNeeded();
  await page.waitForTimeout(200);
  await locator.click();
  try {
    await page.locator('.relc-pop').waitFor({ state: 'visible', timeout: 15_000 });
  } catch (err) {
    let dbg = null;
    let state = null;
    try {
      dbg = await page.evaluate(() => {
        const pop = document.querySelector('.relc-pop');
        return {
          pop: !!pop,
          cls: pop ? pop.className : '',
          display: pop ? getComputedStyle(pop).display : '',
          visibility: pop ? getComputedStyle(pop).visibility : '',
          html: pop ? pop.outerHTML.slice(0, 240) : '',
        };
      });
    } catch (e) {
      dbg = { error: String(e) };
    }
    try {
      state = await vmEval(page, `(vm) => ({
        open: !!vm.relChain.open, hash: vm.relChain.hash || '',
        anchor: !!vm.relChain.anchor, drawerHash: vm.drawer.hash || '',
      })`);
    } catch (e) {
      state = { error: String(e) };
    }
    throw new Error('浮窗未出现: ' + JSON.stringify({
      dbg, state, pageErrors, chainRequests: out.chainRequests.slice(before),
    }));
  }
  await page.waitForFunction(
    () => {
      const pop = document.querySelector('.relc-pop');
      return pop && !document.querySelector('.relc-state.is-loading') && pop.querySelectorAll('.relc-node').length > 0;
    },
    null,
    { timeout: 15_000 },
  );
  return out.chainRequests.slice(before);
}

async function popInfo(page) {
  return page.evaluate(() => {
    const pop = document.querySelector('.relc-pop');
    if (!pop) return null;
    const r = pop.getBoundingClientRect();
    const cs = getComputedStyle(pop);
    return {
      left: Math.round(r.left), top: Math.round(r.top), right: Math.round(r.right), bottom: Math.round(r.bottom),
      width: Math.round(r.width), height: Math.round(r.height),
      clientH: pop.clientHeight, scrollH: pop.scrollHeight,
      scrollable: pop.scrollHeight > pop.clientHeight + 1,
      bg: cs.backgroundColor, vw: window.innerWidth, vh: window.innerHeight,
      nodes: pop.querySelectorAll('.relc-node').length,
      types: [...pop.querySelectorAll('.relc-type')].map((e) => e.textContent.trim()),
      statuses: [...pop.querySelectorAll('.relc-status')].map((e) => e.textContent.trim()),
      auto: pop.querySelectorAll('.relc-auto').length,
      manual: pop.querySelectorAll('.relc-manual').length,
    };
  });
}

/** 在已打开的浮窗上做一次「外层容器滚动」: 找到列表最近的横/纵可滚祖先, 滚动一次并回报是否关闭 */
async function scrollOuter(page) {
  await page.evaluate(() => {
    const row = [...document.querySelectorAll('.group-row[data-table="group"]')][0];
    let el = row && row.parentElement;
    while (el && el !== document.body) {
      const cs = getComputedStyle(el);
      if ((el.scrollWidth > el.clientWidth + 2 && /(auto|scroll)/.test(cs.overflowX)) ||
          (el.scrollHeight > el.clientHeight + 2 && /(auto|scroll)/.test(cs.overflowY))) {
        el.dataset.rmScrollProbe = '1';
        el.dataset.rmScrollAxis = el.scrollWidth > el.clientWidth + 2 ? 'x' : 'y';
        return;
      }
      el = el.parentElement;
    }
  });
  const axis = await page.evaluate(
    () => document.querySelector('[data-rm-scroll-probe="1"]')?.dataset.rmScrollAxis || '',
  );
  const before = await page.evaluate(() => {
    const el = document.querySelector('[data-rm-scroll-probe="1"]');
    return el ? { left: el.scrollLeft, top: el.scrollTop, sw: el.scrollWidth, sh: el.scrollHeight,
                  cw: el.clientWidth, ch: el.clientHeight } : null;
  });
  await page.evaluate((ax) => {
    const el = document.querySelector('[data-rm-scroll-probe="1"]');
    if (!el) return;
    if (ax === 'x') {
      const max = Math.max(0, el.scrollWidth - el.clientWidth);
      el.scrollLeft = el.scrollLeft >= max - 8 ? Math.max(0, el.scrollLeft - 120) : el.scrollLeft + 120;
    } else {
      const max = Math.max(0, el.scrollHeight - el.clientHeight);
      el.scrollTop = el.scrollTop >= max - 8 ? Math.max(0, el.scrollTop - 120) : el.scrollTop + 120;
    }
  }, axis);
  await page.waitForTimeout(300);
  const after = await page.evaluate(() => {
    const el = document.querySelector('[data-rm-scroll-probe="1"]');
    return el ? { left: el.scrollLeft, top: el.scrollTop } : null;
  });
  const closed = !(await vmEval(page, `(vm) => !!vm.relChain.open`));
  await page.evaluate(() => document.querySelector('[data-rm-scroll-probe="1"]')?.removeAttribute('data-rm-scroll-probe'));
  return { axis, before, after, closed };
}

const pageErrors = [];
const browser = await chromium.launch({ headless: true });
try {
  const ctx = await browser.newContext({ viewport: { width: VW, height: VH } });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => pageErrors.push(String(e)));
  page.on('console', (msg) => {
    if (msg.type() === 'error') pageErrors.push('console: ' + msg.text());
  });
  page.on('request', (req) => {
    if (req.method() !== 'GET') return;
    const u = req.url();
    if (!u.includes('/api/relocate/chain')) return;
    const q = new URL(u).searchParams.get('hash') || '';
    out.chainRequests.push({ hash: q, url: u.replace(base, '') });
  });

  // ---- 1) 四皮肤: 组行 / 种子行 行高、徽标几何、截图、浮窗底色
  for (const skin of SKINS) {
    await gotoSkin(page, skin);
    await closeAll(page);
    const rowA = rowOfGroup(page, groupA, groupASave);
    const rowB = rowOfGroup(page, groupB);
    await rowA.scrollIntoViewIfNeeded();
    const mA = await measureRow(page, rowA, `${skin}-groupA`);
    const mB = await measureRow(page, rowB, `${skin}-groupB`);
    const shotGroup = `${outDir}/group-${skin}.png`;
    await page.screenshot({ path: shotGroup });

    await page.locator('button[data-view="torrents"]').click();
    await page.waitForFunction(
      (n) => [...document.querySelectorAll('.group-row.torrent-row[data-hash] .g-name-text')].some((e) => e.textContent.trim() === n),
      groupA,
      { timeout: 20_000 },
    );
    const trA = rowsOfTorrent(page, groupA).first();
    const trB = rowsOfTorrent(page, groupB).first();
    await trA.scrollIntoViewIfNeeded();
    const mTA = await measureRow(page, trA, `${skin}-torrentA`);
    const mTB = await measureRow(page, trB, `${skin}-torrentB`);
    const shotTor = `${outDir}/torrent-${skin}.png`;
    await page.screenshot({ path: shotTor });
    await page.locator('button[data-view="groups"]').click();
    await page.waitForTimeout(250);

    await closeAll(page);
    const reqs = await openChain(page, rowOfGroup(page, groupA, groupASave).locator('.rel-badge').first());
    const pop = await popInfo(page);
    out.skins[skin] = {
      rows: { groupA: mA, groupB: mB, torrentA: mTA, torrentB: mTB },
      popBg: pop.bg, shotGroup, shotTor, chainReqs: reqs.map((r) => r.hash),
    };
    await closeAll(page);
    step('skin-measured', { skin, groupAH: mA.rowH, groupBH: mB.rowH, torrentAH: mTA.rowH, torrentBH: mTB.rowH, popBg: pop.bg });
  }

  // ---- 2) 浮窗定位 / 长链滚动 / 滚动关闭(prism)
  await gotoSkin(page, 'prism');
  await page.setViewportSize({ width: VW, height: VH });
  await closeAll(page);
  // 页面滚动档: 行数少时 body 本身不滚, 补一个流内占位块让 window.scrollBy 可真实触发
  await page.evaluate(() => {
    const d = document.createElement('div');
    d.id = 'rm-scroll-spacer';
    d.style.height = '1800px';
    d.style.width = '1px';
    document.body.appendChild(d);
  });
  await page.waitForTimeout(150);

  // 2a) 竖向翻转: 真实列表纵向不可滚(表格容器是横向滚), 用 fixed 锚点贴视口下沿 ——
  //     锚点距底 40px, 浮窗默认向下放必然越界, 只能翻到锚点上方(考的是 place 的翻转分支)
  await page.evaluate(() => {
    document.querySelector('#rm-synth-anchor')?.remove();
    const el = document.createElement('button');
    el.id = 'rm-synth-anchor';
    el.style.position = 'fixed';
    el.style.left = '300px';
    el.style.top = 'calc(100vh - 40px)';
    el.style.width = '200px';
    el.style.height = '24px';
    el.style.zIndex = '9999';
    el.textContent = 'anchor';
    document.body.appendChild(el);
  });
  await page.waitForTimeout(100);
  const anchorBox = await page.locator('#rm-synth-anchor').boundingBox();
  if (!anchorBox) throw new Error('合成锚点不可见(boundingBox=null)');
  await vmEval(
    page,
    `(vm, a) => { const el = document.querySelector('#rm-synth-anchor'); vm.relChainOpen(a, el); }`,
    mover,
  );
  await page.locator('.relc-pop').waitFor({ state: 'visible', timeout: 15_000 });
  await page.waitForFunction(
    () => {
      const pop = document.querySelector('.relc-pop');
      return pop && !document.querySelector('.relc-state.is-loading') && pop.querySelectorAll('.relc-node').length > 0;
    },
    null,
    { timeout: 15_000 },
  );
  const pFlip = await popInfo(page);
  const anchorBottom = Math.round(anchorBox.y + anchorBox.height);
  const flipAbove = pFlip.top < Math.round(anchorBox.y) && pFlip.bottom <= anchorBottom;
  const flipInView = pFlip.top >= 0 && pFlip.bottom <= pFlip.vh;
  out.placement.bottomFlip = { anchor: anchorBox, pop: pFlip, flipAbove, flipInView, syntheticAnchor: true };
  step('bottom-flip', { anchorTop: Math.round(anchorBox.y), popTop: pFlip.top, popBottom: pFlip.bottom, flipAbove, flipInView });
  await vmEval(page, `(vm) => vm.relChainClose(false)`);
  await page.waitForTimeout(150);
  await page.evaluate(() => document.querySelector('#rm-synth-anchor')?.remove());

  // 2b) 横向夹取: 真实链路浮窗, 锚点用贴左/贴右的临时可聚焦按钮(位置由真实布局函数计算)
  for (const side of ['left', 'right']) {
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(150);
    await page.evaluate((s) => {
      const el = document.createElement('button');
      el.id = 'rm-synth-anchor';
      el.style.position = 'fixed';
      el.style.top = '300px';
      el.style.width = '300px';
      el.style.height = '24px';
      el.style.zIndex = '9999';
      el.textContent = 'anchor';
      if (s === 'left') el.style.left = '0px';
      else el.style.left = 'calc(100vw - 300px)';
      document.body.appendChild(el);
    }, side);
    await vmEval(
      page,
      `(vm, a) => {
        const el = document.querySelector('#rm-synth-anchor');
        vm.relChainOpen(a, el);
      }`,
      mover,
    );
    await page.locator('.relc-pop').waitFor({ state: 'visible', timeout: 10_000 });
    await page.waitForFunction(
      () => {
        const pop = document.querySelector('.relc-pop');
        return pop && !document.querySelector('.relc-state.is-loading') && pop.querySelectorAll('.relc-node').length > 0;
      },
      null,
      { timeout: 10_000 },
    );
    const pi = await popInfo(page);
    const clampLeft = pi.left === 8;
    const clampRight = pi.right === pi.vw - 8;
    out.placement[`clamp_${side}`] = { pop: pi, anchorSide: side, clampLeft, clampRight, inside: pi.left >= 0 && pi.right <= pi.vw };
    step(`clamp-${side}`, { left: pi.left, right: pi.right, vw: pi.vw, clampLeft, clampRight });
    await vmEval(page, `(vm) => vm.relChainClose(false)`);
    await page.waitForTimeout(150);
    await page.evaluate(() => document.querySelector('#rm-synth-anchor')?.remove());
  }

  // 2c) 滚动关闭: 表格容器滚动 / 页面滚动(能滚才判, 不伪造)
  const badgeA = rowOfGroup(page, groupA, groupASave).locator('.rel-badge').first();
  await closeAll(page);
  await openChain(page, badgeA);
  out.placement.scrollCloseTable = await scrollOuter(page);
  step('scroll-close-table', out.placement.scrollCloseTable);
  await closeAll(page);

  // 2c-2) 页面滚动: 先记录 window 是否真的能滚, 能滚才把「关闭」当判据
  await openChain(page, badgeA);
  const pageBeforeY = await page.evaluate(() => window.scrollY);
  await page.evaluate(() => window.scrollBy(0, 160));
  await page.waitForTimeout(300);
  const pageAfterY = await page.evaluate(() => window.scrollY);
  const pageScrollable = Math.abs(pageAfterY - pageBeforeY) > 1;
  const pageClosed = !(await vmEval(page, `(vm) => !!vm.relChain.open`));
  out.placement.scrollClosePage = { beforeY: pageBeforeY, afterY: pageAfterY, scrollable: pageScrollable, closed: pageClosed };
  step('scroll-close-page', out.placement.scrollClosePage);
  await closeAll(page);

  // 2d) 长链: 浮窗内部可滚动(内部滚动不关浮窗), 页面滚动仍关闭
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(200);
  await vmEval(
    page,
    `(vm, a) => {
      const el = document.querySelector('.group-row[data-table="group"] .g-save-path') || document.body;
      vm.relChainOpen(a, el);
    }`,
    chainHash,
  );
  await page.locator('.relc-pop').waitFor({ state: 'visible', timeout: 15_000 });
  await page.waitForFunction(
    () => {
      const pop = document.querySelector('.relc-pop');
      return pop && !document.querySelector('.relc-state.is-loading') && pop.querySelectorAll('.relc-node').length >= 6;
    },
    null,
    { timeout: 20_000 },
  );
  const longPop = await popInfo(page);
  const longShot = `${outDir}/long-chain.png`;
  await page.screenshot({ path: longShot });
  await page.evaluate(() => {
    const pop = document.querySelector('.relc-pop');
    pop.scrollTop = 120;
  });
  await page.waitForTimeout(300);
  const stillOpen = await vmEval(page, `(vm) => !!vm.relChain.open`);
  const scrolled = await page.evaluate(() => document.querySelector('.relc-pop')?.scrollTop || 0);
  out.placement.longChain = { pop: longPop, scrollable: longPop.scrollable, stillOpenAfterInnerScroll: stillOpen, innerScrollTop: scrolled, shot: longShot };
  step('long-chain', { nodes: longPop.nodes, scrollable: longPop.scrollable, stillOpen, scrolled });
  out.placement.longChain.closedByOuterScroll = (await scrollOuter(page)).closed;
  await closeAll(page);
  await page.evaluate(() => document.querySelector('#rm-scroll-spacer')?.remove());

  // ---- 3) 组行徽标 -> drawer(hash=搬移成员) -> Esc 退栈 -> 详情段「路径链」入口基准
  await gotoSkin(page, 'prism');
  await page.setViewportSize({ width: VW, height: VH });
  await closeAll(page);
  const reqsEntry = await openChain(page, rowOfGroup(page, groupA, groupASave).locator('.rel-badge').first());
  const state1 = await vmEval(page, `(vm) => ({ drawerOpen: !!vm.drawer.open, drawerHash: vm.drawer.hash || '', chainHash: vm.relChain.hash || '' })`);
  // P1-2 详情「迁移」段真渲染取证: 默认变体(dt01)按 data-sec 分组, 行 = .dt01-cell(.dt01-k/.dt01-vv)
  // 详情请求与路径链请求独立, 先等迁移段真正渲染出来再读(否则 relRows=null 会偶发误红)
  await page.waitForSelector('.dt01-sec[data-sec="迁移"] .dt01-cell', { timeout: 10_000 });
  const relRows = await page.evaluate(() => {
    const sec = document.querySelector('.dt01-sec[data-sec="迁移"]');
    if (!sec) return null;
    return [...sec.querySelectorAll('.dt01-cell')].map((c) => ({
      label: (c.querySelector('.dt01-k')?.textContent || '').trim(),
      value: (c.querySelector('.dt01-vv')?.textContent || '').trim(),
    }));
  });
  const relShot = `${outDir}/drawer-relocate.png`;
  await page.locator('.drawer').first().screenshot({ path: relShot });
  out.drawerRelocate = { rows: relRows, shot: relShot, drawerHash: state1.drawerHash };
  step('drawer-relocate', { rows: relRows ? relRows.length : 0 });
  await page.keyboard.press('Escape');
  await page.waitForTimeout(250);
  const afterEsc1 = await vmEval(page, `(vm) => ({
    chainOpen: !!vm.relChain.open,
    drawerOpen: !!vm.drawer.open,
    focusClass: document.activeElement ? String(document.activeElement.className || '') : '',
    focusIsBadge: !!(document.activeElement && document.activeElement.classList && document.activeElement.classList.contains('rel-badge')),
  })`);
  const drawerEntry = page.locator('[data-act="chain"]:visible').first();
  await drawerEntry.waitFor({ state: 'visible', timeout: 10_000 });
  // 详情新增「设置时间」行后路径链入口可能落到抽屉滚动区之外: 先滚到位再点击。
  // 若让 click 自己滚, 滚动事件会在 relChainOpen 之后立刻把浮窗关掉(全局滚动关闭)。
  await drawerEntry.scrollIntoViewIfNeeded();
  await page.waitForTimeout(350);
  const beforeDrawerReq = out.chainRequests.length;
  await drawerEntry.click();
  await page.locator('.relc-pop').waitFor({ state: 'visible', timeout: 10_000 });
  await page.waitForTimeout(500);
  const afterDrawerClick = await vmEval(page, `(vm) => ({ chainHash: vm.relChain.hash || '', drawerHash: vm.drawer.hash || '' })`);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(250);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  const afterEsc2 = await vmEval(page, `(vm) => ({ chainOpen: !!vm.relChain.open, drawerOpen: !!vm.drawer.open })`);
  out.groupEntry = {
    expectedMover: mover,
    badgeClick: { ...state1, chainReqs: reqsEntry.map((r) => r.hash) },
    afterEsc1,
    drawerEntryClick: { ...afterDrawerClick, newReqs: out.chainRequests.slice(beforeDrawerReq).map((r) => r.hash) },
    afterEsc2,
  };
  step('group-entry', out.groupEntry);
  await closeAll(page);

  if (pageErrors.length) throw new Error('页面运行期异常: ' + pageErrors.join(' | '));
  out.ok = true;
} catch (e) {
  out.error = String((e && e.message) || e);
  out.pageErrors = pageErrors;
} finally {
  await browser.close();
}
console.log('UI_RESULT ' + JSON.stringify(out));
process.exit(out.ok ? 0 : 1);
