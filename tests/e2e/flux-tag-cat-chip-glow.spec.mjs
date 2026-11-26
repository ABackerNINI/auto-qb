// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS_ALL } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * flux 分类/标签 chip hover 辉光绘制层(计划 26-11-12-1012 S3 e2e 部分, D7)
 *
 * **报障面**: tag-chip / cat-chip 的 hover 辉光被直接父容器 .g-tags/.m-tags/.g-cat/.m-cat 的
 * overflow:hidden(components.css:340-341)裁掉 —— 坑档 clip-path-clips-outer-glow.md 的姊妹
 * 机理, 但裁剪点不在控件本体、在**祖先**。S1(fx-mount.css 文件尾「祖先裁剪放行」段)用
 * overflow:clip + overflow-clip-margin:16px 放行; S2 把 H&R 状态竖线(tag-chip.hr-pending /
 * .hr-done 的 inset 2px 0 0)从本体 box-shadow 迁到 ::before, hover 不再被共用辉光规则吃掉。
 *
 * 本 spec 一篇一件事, 三个 test 各钉一面:
 *   1. S1 computed: 四个容器 overflow === 'clip' 且 overflowClipMargin === '16px'
 *      (组行 .g-* 与展开成员行 .m-*; 16px = 12px blur + 3px spread + 1px 余量, 计划 S1 验收)。
 *   2. S1 像素: hover 辉光真的越过容器裁剪边界 —— 同页 A/B 自比(R8/O5: 不写绝对 RGB 常量,
 *      容器 swiftshader 软渲染 + DPI/抗锯齿差异下绝对阈值脆弱): 放行态截图 vs 往页面注入
 *      overflow:hidden !important(= 红验 1 的回退形态)再截, 容器 border box 外 1-4px 采样带
 *      逐带均值差; 摘掉注入复原再截, 与放行态对齐(注入无残留 + hover 未丢的自证)。
 *   3. S2: H&R 竖线 hover 前后持续可见 —— computed(::before boxShadow 含 2px 左缘 inset
 *      竖线, 基线与 hover 双态; Chrome 序列化后置 inset, 见 hasInsetLine 注)+ 像素
 *      (左缘竖线列 vs 本体内参考列的逐通道差, 同 chip 自比);
 *      本体 hover 的 boxShadow 仍逐字等于 site-chip 的共用 --fx-glow-stack 值。
 *
 * 为什么必须像素: 祖先 overflow 裁剪不改变任何 computed 值(子元素 box-shadow 原样),
 * computed 断言抓不到「辉光被裁」这层(坑档原话: 静态检查与样式值全对也发现不了); 反过来
 * computed 红也不证明辉光真出来了(overflow-clip-margin 不生效的内核差异, R5/O1)。
 *
 * flux 不在 e2e 默认 SKINS(['prism','atlas'], harness.mjs:102) —— 本 spec 显式取 SKINS_ALL
 * 里的 flux(不改 SKINS 默认值, R12), 手法对齐 flux-site-chip-shape-glow.spec.mjs。
 *
 * **hr chip 只在成员行**(计划 S2 的 .tag-chip.hr-* 断言面): 组载荷 members 是 **hash 字符串
 * 数组**(views_group.py, P-02 二期起明细经 memberByHash 还原), 组行模板
 * tagClass(t, g.members[0]) 拿到的是 hash 串 => 组行 tag-chip 永远不带 hr-pending/hr-done
 * (既存展示层死角, 与本计划无关, 只在此记录)。带状态类的 chip 渲染在辅种页(groups 视图)
 * 展开明细的成员行里 —— 本 spec 的 S2 面走 groups 视图逐组展开扫描。
 *
 * **数据面**(桩增量, scripts/ui_harness.py): 桩默认 hr.add_tag / add_tag_for_satisfied 恒空串
 * => tagClass(decorate.js)打不出 hr-pending/hr-done。桩把两档 HR 输出标签统一指到位 3 池名
 * hr-e2e(_make_torrents): done(i%3!=0)种子全部触发 HR(dlsratio 0.7), 做种达标线 84h((i%400)h)
 * => i%400<84 未达标(pending)/ >=84 已达标(done), 同名标签按成员态分别打出 hr-pending /
 * hr-done。带状态 chip 的成员只落在位 3 组(i%16>=8): 表尾首个 pending = Set004(i=8),
 * 表头首个 done = Set149(i=298)。标签名进 auto_managed_tag_rules 精确集 => 添加窗口候选
 * (/api/tags?exclude_auto=1)把它与站点标签同款滤除, add-options-recent-order 的期望序不受影响。
 * 红验 2 = 删 fx-mount.css 的 S2 迁层规则(smoke.md:104 红绿双验纪律)。
 */

/* 本 spec 只对 flux 有意义: 四个容器类在四皮肤共用 CSS 里都是 overflow:hidden, 但放行规则
 * 带 html[data-fx-preset] 前缀只作用 flux, 三旧皮肤既无 fx-mount.css 也没有该属性。 */
const FLUX = SKINS_ALL.filter((skin) => skin === 'flux');

/** 打开 flux 种子页(三种 chip 都在平铺行的列里: site/category/tags)。 */
async function openTorrents(page) {
  await page.goto(`${baseUrl()}/flux/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.group-row.torrent-row').first()).toBeVisible({ timeout: 30_000 });
}

/**
 * 把指针真放进某个 chip 并等 hover boxShadow 稳态(手法对齐 flux-site-chip-shape-glow.spec.mjs
 * 的 hoverChip: 逐个试到 :hover 真命中; 连续三拍全等、拍距 150ms, 静默 >= 300ms > box-shadow
 * 过渡 --dur-fast glass 140ms, 不用固定睡等赌过渡走完)。wantIdx 给定时只试该下标(pickChip
 * 已选好样本), 否则从前 12 个里逐个试。命中返回 { cls, shadow, before }, 探不到返回 null ——
 * 宁可失败也不要在没悬停的样本上验通过。before 一并带回(S2 断言 hover 态 ::before 用)。
 */
async function hoverChip(page, sel, wantIdx = null) {
  const chips = page.locator(sel);
  const total = await chips.count();
  const lo = wantIdx !== null ? wantIdx : 0;
  const hi = wantIdx !== null ? wantIdx + 1 : Math.min(total, 12);
  for (let i = lo; i < hi; i++) {
    const chip = chips.nth(i);
    await chip.scrollIntoViewIfNeeded().catch(() => {});
    const box = await chip.boundingBox();
    if (!box || box.height < 4 || box.width < 4) continue;
    const x = Math.min(Math.max(box.x + box.width / 2, 8), 1432);
    const y = Math.min(Math.max(box.y + box.height / 2, 8), 892);
    if (x !== box.x + box.width / 2 || y !== box.y + box.height / 2) continue; // 钳到视口外 = 没滚进来, 换下一个
    await page.mouse.move(x, y);
    const hit = await page.evaluate(
      ({ sel, idx }) => !!document.querySelectorAll(sel)[idx]?.matches(':hover'),
      { sel, idx: i },
    );
    if (!hit) continue;
    const readShadow = () => page.evaluate(
      ({ sel, idx }) => {
        const el = document.querySelectorAll(sel)[idx];
        return {
          cls: el.className,
          shadow: getComputedStyle(el).boxShadow,
          before: getComputedStyle(el, '::before').boxShadow,
        };
      },
      { sel, idx: i },
    );
    const seq = [];
    await expect.poll(async () => {
      seq.push(await readShadow());
      if (seq.length > 3) seq.shift();
      return seq.length === 3 && seq[0].shadow === seq[1].shadow && seq[1].shadow === seq[2].shadow;
    }, { timeout: 5_000, intervals: [150] }).toBe(true);
    return seq[seq.length - 1];
  }
  return null;
}

/** 切到辅种页(groups 视图): .m-tags/.m-cat(展开成员行)与带 HR 状态类的 tag-chip 都在这里
 * (种子页展开态会被清掉, views.spec 跨视图记忆用例即钉此事)。 */
async function gotoGroupsView(page) {
  await page.click('nav.tabs [data-view="groups"]');
  await expect(page.locator('.group-row[data-table="group"]').first()).toBeVisible({ timeout: 30_000 });
}

/**
 * 展开第 idx 个组行(程序化 click 走 Vue 的 @click 处理器, 打 .g-name 避开 chip 的
 * @click.stop 筛选; 手法对齐 main-table-pinned-selected.spec.mjs 的 expandUnselectedRow)。
 * 旧 400ms 睡等改 poll expanded 类; 2s 整表重渲染会抢走点击(smoke.md:104) => 失败重试一次。
 */
async function expandGroupRow(page, idx) {
  for (let attempt = 0; attempt < 2; attempt++) {
    await page.evaluate((i) => {
      const row = document.querySelectorAll('.group-row[data-table="group"]')[i];
      row.scrollIntoView({ block: 'center', behavior: 'instant' });
      (row.querySelector('.g-name') || row.children[0]).click();
    }, idx);
    try {
      await expect.poll(
        () => page.evaluate(
          (i) => document.querySelectorAll('.group-row[data-table="group"]')[i]?.classList.contains('expanded') === true,
          idx,
        ),
        { timeout: 3_000, message: `组行 #${idx} 展开点击未落上(expanded 类未出现)` },
      ).toBe(true);
      return true;
    } catch {
      if (attempt === 1) return false;
    }
  }
  return false;
}

/**
 * 逐组展开扫描, 直到展开明细里出现目标 chip(成员行才有 HR 状态类, 见文件头)。
 * 组列表默认按 added_on **降序**(桩 added_on = 1700000000 + i*37 => Set149 在顶、Set000 在底;
 * e2e 页面快照实测), 而 pending 态成员只存在于做种达标线(i<84)即**表尾** —— fromEnd=true
 * 从表尾往前扫(pending), false 从表头往后扫(done 态集中在表头)。返回命中的组下标,
 * 扫满 maxGroups 未命中返回 -1(调用方红)。展开是单键互斥(expandedKey), 点下一组自动
 * 收上一组, 不会累积。
 */
async function expandUntilChip(page, chipSel, maxGroups, fromEnd = false) {
  const total = await page.locator('.group-row[data-table="group"]').count();
  for (let k = 0; k < Math.min(total, maxGroups); k++) {
    const i = fromEnd ? total - 1 - k : k;
    if (!(await expandGroupRow(page, i))) continue;
    if ((await page.locator(`.member-row ${chipSel}`).count()) > 0) return i;
  }
  return -1;
}

/* ---------------- S1 像素采样(放行 vs 同页 hidden 基线) ---------------- */

/** 上下贴缘余量上限(CSS px): 超过 = chip 辉光够不着容器边界, 相对判据失效, 宁红勿假绿。 */
const CONTACT_MAX_PX = 6;
/** 左带采样要求 chip 贴左缘(flex 行首 chip 恒贴左, slackLeft ≈ 0)的余量上限。 */
const LEFT_SLACK_MAX_PX = 5;

/**
 * 选一枚「贴容器上下缘」的采样 chip: 逐候选(scrollIntoView 物化窗口行后)读 chip 与直接父
 * 容器(g-tags/g-cat 格)的视口矩形, 取 min(slackTop, slackBottom) 最小者; 左带并行记一个
 * 「同时贴左缘」的次优(flex 换行时贴上缘的未必是行首)。选完回中重滚再量一次 —— 迭代期的
 * scrollIntoViewIfNeeded 落点不保证复现, 以最终矩形为准。找不到合格样本返回 chosen=null
 * (几何漂了/列宽变了), diag 带最后候选数据供断言消息。
 */
async function pickChip(page, kind) {
  const sel = `.group-row .${kind}:not(.f-on)`;
  const n = Math.min(await page.locator(sel).count(), 40);
  const measure = async (idx) => {
    const chip = page.locator(sel).nth(idx);
    return chip.evaluate((el) => {
      const cont = el.parentElement;
      if (!cont) return null;
      const c = el.getBoundingClientRect();
      const t = cont.getBoundingClientRect();
      return {
        chip: { x: c.x, y: c.y, w: c.width, h: c.height },
        cont: { x: t.x, y: t.y, w: t.width, h: t.height },
        vw: innerWidth, vh: innerHeight, dpr: window.devicePixelRatio || 1,
        cls: el.className,
      };
    });
  };
  const annotate = (r, idx) => {
    const slackTop = r.chip.y - r.cont.y;
    const slackBottom = r.cont.y + r.cont.h - (r.chip.y + r.chip.h);
    const slackLeft = r.chip.x - r.cont.x;
    const slackRight = r.cont.x + r.cont.w - (r.chip.x + r.chip.w);
    return { sel, idx, ...r, slackTop, slackBottom, slackLeft, slackRight, vert: Math.min(slackTop, slackBottom) };
  };
  const inViewport = (r) =>
    r.cont.y >= 6 && r.cont.y + r.cont.h <= r.vh - 6 && r.cont.x >= 6 && r.cont.x + r.cont.w <= r.vw - 6;
  let best = null;
  let bestLeft = null;
  let last = null;
  for (let i = 0; i < n; i++) {
    const chip = page.locator(sel).nth(i);
    await chip.scrollIntoViewIfNeeded().catch(() => {});
    const raw = await measure(i);
    if (!raw || raw.chip.w < 8 || raw.chip.h < 8 || !inViewport(raw)) continue;
    const cand = annotate(raw, i);
    last = cand;
    if (!best || cand.vert < best.vert) best = cand;
    if (cand.slackLeft <= LEFT_SLACK_MAX_PX && (!bestLeft || cand.vert < bestLeft.vert)) bestLeft = cand;
    if (bestLeft && bestLeft.vert <= 1) break; // 贴到 1px 内已是最优, 不再滚
  }
  let chosen = best;
  let leftUsable = false;
  if (bestLeft && bestLeft.vert <= CONTACT_MAX_PX) {
    chosen = bestLeft;
    leftUsable = true;
  }
  if (!chosen || chosen.vert > CONTACT_MAX_PX) {
    return { chosen: null, leftUsable: false, diag: last ? JSON.stringify(last) : `候选数=${n}` };
  }
  // 回中重滚 + 终量(以最终矩形为准; 终量后护栏再不过 = 判据面失效, 交由调用方红)
  await page.evaluate(({ sel, idx }) => {
    const el = document.querySelectorAll(sel)[idx];
    el.scrollIntoView({ block: 'center', behavior: 'instant' });
  }, { sel: chosen.sel, idx: chosen.idx });
  const fin = await measure(chosen.idx);
  const ok = fin && fin.chip.w >= 8 && fin.chip.h >= 8 && inViewport(fin);
  if (!ok) return { chosen: null, leftUsable: false, diag: `终量失败 ${JSON.stringify(fin)}` };
  return { chosen: annotate(fin, chosen.idx), leftUsable, diag: '' };
}

/**
 * 容器 border box 外 1-4px 采样带(设备像素): 上下带沿 chip 宽度铺开、左右带沿 chip 高度
 * 铺开。只采 border box 之外 —— overflow 的裁剪边界(padding box)不会超出 border box,
 * hidden 基线下带上每个点必然被裁, 放行态下被 16px 外扩放行。
 */
function bandPoints(p, side) {
  const { chip, cont, dpr, vw, vh } = p;
  const pts = [];
  const put = (x, y) => {
    const px = Math.round(x * dpr);
    const py = Math.round(y * dpr);
    if (px >= 0 && py >= 0 && px < Math.round(vw * dpr) && py < Math.round(vh * dpr)) pts.push([px, py]);
  };
  const x0 = Math.max(chip.x + 3, cont.x + 1);
  const x1 = Math.min(chip.x + chip.w - 3, cont.x + cont.w - 1);
  const y0 = Math.max(chip.y + 3, cont.y + 1);
  const y1 = Math.min(chip.y + chip.h - 3, cont.y + cont.h - 1);
  for (let k = 1; k <= 4; k++) {
    if (side === 'top') for (let x = x0; x <= x1; x += 4) put(x, cont.y - k);
    if (side === 'bottom') for (let x = x0; x <= x1; x += 4) put(x, cont.y + cont.h + k);
    if (side === 'left') for (let y = y0; y <= y1; y += 3) put(cont.x - k, y);
    if (side === 'right') for (let y = y0; y <= y1; y += 3) put(cont.x + cont.w + k, y);
  }
  return pts;
}

/** 红验 1 形态的页内注入(= fx-mount.css 放行规则退回 hidden 的同款几何): !important 压过
 * 链尾级联; 用完即摘, 摘后与放行态重截对齐(注入无残留的自证)。 */
const CLIP_REVERT_CSS =
  'html[data-fx-preset] .g-tags, html[data-fx-preset] .m-tags,' +
  'html[data-fx-preset] .g-cat, html[data-fx-preset] .m-cat' +
  '{ overflow: hidden !important; overflow-clip-margin: 0px !important; }';

/**
 * 截图并在 page.evaluate 内解码采样(page.screenshot -> Image -> canvas.getImageData,
 * 计划 S3 钉的采样路径): 每条带返回平均 RGB 与点数。一次截图一次 evaluate, 所有带一次取数。
 */
async function shootAndSample(page, bands) {
  const b64 = (await page.screenshot()).toString('base64');
  return page.evaluate(async ({ b64, bands }) => {
    const img = new Image();
    img.src = 'data:image/png;base64,' + b64;
    await img.decode();
    const cv = document.createElement('canvas');
    cv.width = img.naturalWidth;
    cv.height = img.naturalHeight;
    const ctx = cv.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(img, 0, 0);
    const out = {};
    for (const [side, pts] of Object.entries(bands)) {
      let r = 0, g = 0, b = 0, n = 0;
      for (const [x, y] of pts) {
        if (x >= cv.width || y >= cv.height) continue;
        const d = ctx.getImageData(x, y, 1, 1).data;
        r += d[0]; g += d[1]; b += d[2]; n++;
      }
      out[side] = n ? { mean: [r / n, g / n, b / n], n } : null;
    }
    return out;
  }, { b64, bands });
}

/** 采样带均值标量(0-255)。 */
const lum = (s) => (s.mean[0] + s.mean[1] + s.mean[2]) / 3;
const fmt = (s) => (s ? `rgb(${s.mean.map((v) => v.toFixed(1)).join('/')}) n=${s.n}` : 'null');

/* ---------------- S2 左缘竖线像素 ---------------- */

/**
 * 竖线 computed 形态(::before boxShadow = inset 2px 0 0 var(--hr-*)): Chrome 序列化把
 * `inset 2px 0 0` 规整成 `rgb(r, g, b) 2px 0px 0px 0px inset`(inset 后置 + 补 px, 同
 * flux-site-chip-shape-glow.spec.mjs 头注记过的序列化坑), 两种形态都认 —— 归一化去空白后
 * 双向匹配, 规则本体(2px 左缘 inset 竖线)漂移即 false。
 */
function hasInsetLine(shadow) {
  const s = String(shadow).replace(/\s+/g, '');
  return s.includes('2px0px0px0pxinset') || s.includes('inset2px00');
}

/**
 * 左缘竖线强度: 截图后页内解码, 竖线列(chipLeft+2, 2px inset 线芯, 避开 1px border)对
 * 本体内参考列(chipLeft+6, 7px 内边距中段、文字之前)逐 y 逐通道差取均值 —— 同 chip 自比,
 * 差值只来自竖线色(--hr-pending/-done)与 soft 底色的色距。S2 回退形态(迁层规则被删)下
 * hover 把本体竖线吃掉, 两列同底色, 差值塌到噪声级。hover 态随截图一并复核(常态基线也有
 * 竖线, hover 丢了会假绿)。
 */
async function lineStrength(page, sel, idx) {
  const geo = await page.evaluate(
    ({ sel, idx }) => {
      const el = document.querySelectorAll(sel)[idx];
      const b = el.getBoundingClientRect();
      return { x: b.x, y: b.y, w: b.width, h: b.height, dpr: window.devicePixelRatio || 1 };
    },
    { sel, idx },
  );
  const b64 = (await page.screenshot()).toString('base64');
  return page.evaluate(async ({ b64, geo, sel, idx }) => {
    const img = new Image();
    img.src = 'data:image/png;base64,' + b64;
    await img.decode();
    const cv = document.createElement('canvas');
    cv.width = img.naturalWidth;
    cv.height = img.naturalHeight;
    const ctx = cv.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(img, 0, 0);
    const s = geo.dpr;
    const lineX = Math.round((geo.x + 2) * s);
    const refX = Math.round((geo.x + 6) * s);
    const yA = Math.round((geo.y + 4) * s);
    const yB = Math.round((geo.y + geo.h - 4) * s);
    let sum = 0, n = 0, worst = 0;
    for (let y = yA; y <= yB; y++) {
      const a = ctx.getImageData(lineX, y, 1, 1).data;
      const b = ctx.getImageData(refX, y, 1, 1).data;
      const d = Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]), Math.abs(a[2] - b[2]));
      sum += d; n++;
      if (d > worst) worst = d;
    }
    const hoverOk = !!document.querySelectorAll(sel)[idx]?.matches(':hover');
    return { diff: n ? sum / n : 0, worst, n, hoverOk };
  }, { b64, geo, sel, idx });
}

/* ---------------- 用例 ---------------- */

for (const skin of FLUX) {
  test.describe(`flux tag/cat chip 辉光绘制层 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`主判据: 四个 chip 容器 overflow=clip 且 overflow-clip-margin=16px @fast (${skin})`, async ({ page }) => {
      test.setTimeout(120_000); // 双视图 + 展开明细, 容器软渲染下放宽
      collectRuntimeErrors(page);
      await openTorrents(page);

      // 组行 .g-tags/.g-cat(xtpl-cells.html:71/86): 抽样前 24 行, computed 逐格断言
      const CONTAINER_SAMPLE = 24;
      const rows = await page.evaluate((cap) => {
        const pick = (sel) => [...document.querySelectorAll(sel)].slice(0, cap).map((el) => {
          const cs = getComputedStyle(el);
          return { sel, cls: el.className, overflow: cs.overflow, margin: cs.overflowClipMargin };
        });
        return [...pick('.group-row .g-tags'), ...pick('.group-row .g-cat')];
      }, CONTAINER_SAMPLE);
      for (const sel of ['.group-row .g-tags', '.group-row .g-cat']) {
        expect(rows.filter((r) => r.sel === sel).length,
          `${sel} 零样本(标签/分类列被移出默认列集?)`).toBeGreaterThan(0);
      }
      for (const r of rows) {
        expect(r.overflow, `${r.sel} computed overflow=${r.overflow} —— S1 祖先裁剪放行被退回 ` +
          'hidden(裁掉 hover 辉光, 用户报障回归; 计划 26-11-12-1012 S1 验收)')
          .toBe('clip');
        expect(r.margin, `${r.sel} computed overflowClipMargin=${r.margin} —— 外扩余量丢了, ` +
          '辉光(最大层 0 0 12px 3px)没有 16px 让路空间(计划 S1 验收)')
          .toBe('16px');
      }

      // 成员行 .m-tags/.m-cat(xtpl.html:281/287, 辅种页展开明细才有): 切 groups 视图展开
      // 首个组行后同款断言(种子页无展开态, 见 gotoGroupsView 注)
      await gotoGroupsView(page);
      const expanded = await expandGroupRow(page, 0);
      expect(expanded, '首个组行展开未落上(渲染链变了?)').toBe(true);
      const mrows = await page.evaluate(() => {
        const pick = (sel) => [...document.querySelectorAll(sel)].map((el) => {
          const cs = getComputedStyle(el);
          return { sel, cls: el.className, overflow: cs.overflow, margin: cs.overflowClipMargin };
        });
        return [...pick('.member-row .m-tags'), ...pick('.member-row .m-cat')];
      });
      expect(mrows.length, '展开后没有 .m-tags/.m-cat(成员行渲染链变了?)').toBeGreaterThan(0);
      for (const r of mrows) {
        expect(r.overflow, `${r.sel} computed overflow=${r.overflow} —— 成员行容器未跟上 S1 放行`)
          .toBe('clip');
        expect(r.margin, `${r.sel} computed overflowClipMargin=${r.margin} —— 成员行容器未跟上 S1 放行`)
          .toBe('16px');
      }
    });

    test(`像素判据: tag/cat chip hover 辉光越过容器裁剪边界(放行 vs 同页 hidden 基线) @fast (${skin})`, async ({ page }) => {
      test.setTimeout(90_000); // 本 spec 唯一真跑截图的用例(2 kinds × pickChip 扫描 + hover 稳态轮询 + 3 次截图 + 页内 PNG 解码逐点 getImageData), 容器软渲染下放宽
      collectRuntimeErrors(page);
      await openTorrents(page);

      /** 放行 - hidden 的每带均值差下限(同页同态自比, 噪声级 ≈0; 实测校准见交付报告留痕)。 */
      const EPS_GLOW = 10;
      /** 复原态与放行态的最大漂移(同态重截, 应为渲染噪声级)。 */
      const NOISE_MAX = 4;

      for (const kind of ['tag-chip', 'cat-chip']) {
        const picked = await pickChip(page, kind);
        expect(picked.chosen, `.${kind} 找不到贴容器上下缘的采样 chip(行高/列宽几何漂了, ` +
          `相对判据失效; 最后候选: ${picked.diag})`).not.toBeNull();
        const p = picked.chosen;

        const bands = {
          top: bandPoints(p, 'top'),
          bottom: bandPoints(p, 'bottom'),
          left: picked.leftUsable ? bandPoints(p, 'left') : [],
          right: bandPoints(p, 'right'),
        };
        const hit = await hoverChip(page, p.sel, p.idx);
        expect(hit, `.${kind} 指针没能落进选中的 chip(idx=${p.idx}) —— 不能在无悬停样本上判绿`)
          .not.toBeNull();
        const ship = await shootAndSample(page, bands);
        for (const [side, s] of Object.entries(ship)) {
          if (bands[side].length) {
            expect(s, `.${kind} ${side} 带采样点全落截图外(视口护栏失守?)`).not.toBeNull();
          }
        }
        const hoverOk = await page.evaluate(
          ({ sel, idx }) => document.querySelectorAll(sel)[idx]?.matches(':hover') === true,
          { sel: p.sel, idx: p.idx },
        );
        expect(hoverOk, `.${kind} 截图时 hover 已丢(整表重渲染顶掉指针态?) —— 放行态样本不可信`)
          .toBe(true);

        const style = await page.addStyleTag({ content: CLIP_REVERT_CSS });
        const clip = await shootAndSample(page, bands);
        await style.evaluate((el) => el.remove());
        const rest = await shootAndSample(page, bands);

        for (const side of ['top', 'bottom', 'left', 'right']) {
          if (!bands[side].length) continue;
          const s = lum(ship[side]);
          const c = lum(clip[side]);
          const r2 = lum(rest[side]);
          // 左带只在 chip 贴左缘时断言(已由 leftUsable 保证); 右带只在 chip 同时贴右缘时
          // 断言 —— 多 chip 行的中间 chip 辉光落在容器内不裁, 那是几何而不是回归。
          const asserted = side === 'top' || side === 'bottom' ||
            (side === 'left' && picked.leftUsable) || (side === 'right' && p.slackRight <= 2);
          if (asserted) {
            expect(s - c, `.${kind} ${side} 带辉光差 ship-clip=${(s - c).toFixed(1)} ` +
              `(ship ${fmt(ship[side])} vs clip ${fmt(clip[side])}) —— hover 辉光没有越过容器边界, ` +
              '祖先裁剪放行(S1)失效或被退回 hidden(计划 26-11-12-1012 红验 1 形态)')
              .toBeGreaterThan(EPS_GLOW);
          }
          expect(Math.abs(r2 - s), `.${kind} ${side} 带复原态漂移 |rest-ship|=${Math.abs(r2 - s).toFixed(1)} ` +
            `(rest ${fmt(rest[side])} vs ship ${fmt(ship[side])}) —— 注入摘除后没回到放行态 ` +
            '(注入残留/hover 丢失/渲染不稳), 像素判据不可信')
            .toBeLessThanOrEqual(NOISE_MAX);
        }
      }
    });

    test(`S2: H&R 竖线 hover 前后持续可见(::before 迁层) + 本体辉光仍走共用 stack @fast (${skin})`, async ({ page }) => {
      test.setTimeout(180_000); // done 态表头 idx 0 即命中(Set149), 逐组展开的行程面在 pending(fromEnd 第 5 组), 两态扫描 + hover + 截图, 容器软渲染下放宽
      collectRuntimeErrors(page);
      await openTorrents(page);

      /** 左缘竖线列对本体参考列的逐通道差下限(同 chip 自比; 实测校准见交付报告留痕)。 */
      const EPS_LINE = 40;

      // 对账基准: 种子页先悬停一枚 site-chip, 取三种 chip 共用的 --fx-glow-stack hover 值
      // (preset 级配方, 换视图不变)。
      const site = await hoverChip(page, '.group-row .site-chip:not(.f-on)');
      expect(site, 'site-chip 没能悬停').not.toBeNull();
      expect(site.shadow, 'site-chip hover boxShadow 为 none —— 辉光规则整条丢失').not.toBe('none');

      // hr chip 只在辅种页展开明细的成员行(文件头注): 逐组展开扫描两种状态
      await gotoGroupsView(page);
      for (const [cls, label, cap, fromEnd] of [['hr-pending', '未达标', 10, true], ['hr-done', '已达标', 60, false]]) {
        const hit0 = await expandUntilChip(page, `.tag-chip.${cls}`, cap, fromEnd);
        expect(hit0, `扫描 ${cap} 个组没找到带 .tag-chip.${cls} 的成员行 —— 桩没供出 ${label} 态 ` +
          'chip(scripts/ui_harness.py 的 HR 状态标签注入被删? 或组排序/HR 达标线漂了)').toBeGreaterThanOrEqual(0);

        const sel = `.member-row .tag-chip.${cls}`;
        // hover 前基线: 竖线已迁 ::before(S2), 常态可见
        const base = await page.locator(sel).first().evaluate((el) => ({
          cls: el.className,
          before: getComputedStyle(el, '::before').boxShadow,
        }));
        expect(hasInsetLine(base.before), `${sel} 基线 ::before 无竖线(${base.before}, ${base.cls}) —— ` +
          'S2 迁层规则丢失, 常态竖线退回本体 box-shadow(计划 26-11-12-1012 S2 验收)')
          .toBe(true);

        const hit = await hoverChip(page, sel, 0);
        expect(hit, `${sel} 指针没能落进 chip`).not.toBeNull();
        expect(hasInsetLine(hit.before), `${sel} hover 态 ::before 竖线丢失(${hit.before}) —— hover 辉光规则 ` +
          '整体替换 box-shadow 时迁层载体没了, 竖线在 hover 态消失(计划 S2 验收)')
          .toBe(true);
        expect(hit.shadow, `${sel} hover 本体 boxShadow 与 site-chip 的共用 stack 不等 —— ` +
          '三种 chip 应同消费一条 --fx-glow-stack(计划 S2 验收)')
          .toBe(site.shadow);

        const line = await lineStrength(page, sel, 0);
        expect(line.hoverOk, `${sel} 截图时 hover 已丢 —— 竖线像素可能取自常态(常态也有线), 判据失效`)
          .toBe(true);
        expect(line.diff, `${sel} 左缘竖线强度 diff=${line.diff.toFixed(1)}(worst=${line.worst}, ` +
          `n=${line.n}) —— hover 态竖线列与本体参考列同色, 迁层竖线在 hover 态归零 ` +
          '(计划 S2 像素判据; 红验 2 = 删 fx-mount.css 的 S2 迁层规则)')
          .toBeGreaterThan(EPS_LINE);
      }
    });
  });
}
