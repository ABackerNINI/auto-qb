// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS_ALL } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import zlib from 'zlib';

/**
 * 必显列(吸左首格)悬停底色一致性 —— 行为守阵全矩阵(2026-11-11)
 *
 * **背景**: 「主表下载状态种子固定列名称列 hover 背景与其它列不一致」用户多次报障。历史逐轮
 * 修因各不相同(frozen-column.md 06/07/08/09/10 各条 + 26-10-30 row_lang flat/wave 重构 issue 26-10-30-0818
 * + 26-11-03 flux fx D4-1 hover 渐亮让位退役), 结构性根因 = 名称列与行板是**两个承载物**,
 * 「底色表达式逐字相同 + 过渡同源 --dur」不变量靠每个绘制面(4 皮肤 × flat/wave × 状态 × 主题 ×
 * fx 预设)各自手写维持, 每新增一个绘制面就重新引入一次分家风险。
 * **既有守阵的盲区**(本 spec 堵的点): 静态守阵(test_webui_static_skins_table.py, 四皮肤)只钉
 * 声明形态; 行为守阵 main-table-pinned-hover.spec.mjs 只跑 SKINS(prism+atlas) × 默认 flat ×
 * 通用行 —— 26-11-03 flux fx 复发恰好落在行为盲区。本 spec 把行为面扩到:
 *   · 全四皮肤(SKINS_ALL) × 行语言(flat 全四 + wave 双皮肤: row_lang.css 皮肤无关, 取两个
 *     令牌不同的皮肤抽样);
 *   · 状态行(s-downloading/s-seeding/s-checking/s-paused/s-other, 用户报障面 = 下载态);
 *   · 组合态(选中+hover 真手势 / search-hit+hover 注入类 / 展开行 hover, 辅种表);
 *   · 两种量法: 过渡窗口逐帧 backgroundColor 采样(过渡错拍) + **稳态截图像素地面真值**
 *     (隐藏行内文字后整行只剩底色, 名称格 vs 相邻格同 y 逐通道差 ≤ 2 —— 表示法无关, 渐层/
 *     半透明/扫层伪元素全部按最终可见像素对齐, 不重蹈 0818「计算值表示分家」与探针漏
 *     background-image 层的覆辙)。
 *
 * 对账: 本 spec 是 main-table-pinned-hover.spec.mjs(通用行, 三表×双皮肤)与
 * dt-table-face-bg.spec.mjs(抽屉八面)之外的第三块拼图 —— 主表 × 状态/组合态 × 全皮肤 × 双行语言。
 */

const ST_STATES = ['downloading', 'seeding', 'checking', 'paused', 'other'];
/** wave 行语言规则在 shared/row_lang.css 单点、皮肤无关 —— 取两个令牌体系不同的皮肤抽样即可。 */
const WAVE_SKINS = ['prism', 'flux'];
/** 展开行 hover 用辅种表(点击行 = 展开开关的既定手势面)。 */
const GROUPS_VIEW = 'groups';

/** 打开某皮肤某页签(先写行语言偏好再进页面, rowlang.js 首帧同步读)。 */
async function openView(page, skin, view, rowlang) {
  // 钉深色: theme.js 无存储时跟随 prefers-color-scheme(prism LIGHT_DEFAULT=frost) —— 不钉则
  // prism 上下文落 frost, row_lang.css 被 :not([data-theme="frost"]) 整体排除, wave 抽样假覆盖。
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
  await page.evaluate((k) => localStorage.setItem('autoqb.ui.rowlang', k), rowlang);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
  await page.click(`nav.tabs [data-view="${view}"]`);
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
}

/** 隐藏行内文字/芯片(visibility 不改布局), 整行只剩底色 —— 像素地面真值的前提。 */
async function hideRowContent(page) {
  await page.addStyleTag({
    content: `.group-row > * > *, .group-row > * > * > * { visibility: hidden !important; }`,
  });
}

/** 找一条可悬停的指定状态行(逐行试 :hover 真命中, 探不到返回 null —— 宁红勿假绿)。 */
async function hoverableStateRow(page, stateCls) {
  const sel = `.group-row[data-table="torrent"].${stateCls}`;
  const n = await page.locator(sel).count();
  for (let i = 0; i < Math.min(n, 14); i++) {
    const box = await page.locator(sel).nth(i).boundingBox();
    if (!box || box.height < 8 || box.y < 60 || box.y > 900) continue;
    const x = Math.max(Math.min(box.x + Math.min(box.width * 0.6, 900), 1580), box.x + 400);
    const y = Math.min(Math.max(box.y + box.height / 2, 8), 880);
    await page.mouse.move(5, 5);
    await page.mouse.move(x, y);
    const hit = await page.evaluate(
      ({ sel, idx }) => !!document.querySelectorAll(sel)[idx]?.matches(':hover'),
      { sel, idx: i },
    );
    if (hit) return { sel, idx: i, box, x, y };
  }
  return null;
}

/** 逐帧采样(500ms): 指定行的首格 vs 行板 backgroundColor 逐帧逐通道最大差。 */
function traceColorsAt(page, rowSel, idx) {
  return page.evaluate(
    ({ rowSel, idx }) => new Promise((resolve) => {
      const row = document.querySelectorAll(rowSel)[idx];
      const cell = row?.children?.[0];
      if (!row || !cell) { resolve([]); return; }
      const parse = (s) => (s.match(/[\d.]+/g) || []).map(Number);
      const frames = [];
      const t0 = performance.now();
      const tick = () => {
        const fa = parse(getComputedStyle(cell).backgroundColor);
        const ra = parse(getComputedStyle(row).backgroundColor);
        let d = 0;
        for (let i = 0; i < 3; i++) d = Math.max(d, Math.abs((fa[i] || 0) - (ra[i] || 0)));
        frames.push({ d, f: getComputedStyle(cell).backgroundColor, r: getComputedStyle(row).backgroundColor });
        if (performance.now() - t0 < 500) requestAnimationFrame(tick);
        else resolve(frames);
      };
      requestAnimationFrame(tick);
    }),
    { rowSel, idx },
  );
}

/* ---- PNG 解码(无依赖) + 取样 ---- */
function decodePng(buf) {
  const b = Buffer.from(buf);
  let off = 8, w = 0, h = 0, colorType = 0;
  const idat = [];
  while (off < b.length) {
    const len = b.readUInt32BE(off);
    const type = b.toString('ascii', off + 4, off + 8);
    const data = b.subarray(off + 8, off + 8 + len);
    if (type === 'IHDR') { w = data.readUInt32BE(0); h = data.readUInt32BE(4); colorType = data[9]; }
    else if (type === 'IDAT') idat.push(data);
    off += 12 + len;
    if (type === 'IEND') break;
  }
  const ch = colorType === 6 ? 4 : 3;
  const raw = zlib.inflateSync(Buffer.concat(idat));
  const stride = w * ch;
  const out = Buffer.alloc(h * stride);
  let p = 0;
  for (let y = 0; y < h; y++) {
    const ft = raw[p++];
    const src = raw.subarray(p, p + stride); p += stride;
    const prev = y > 0 ? out.subarray((y - 1) * stride, y * stride) : null;
    const cur = out.subarray(y * stride, (y + 1) * stride);
    for (let x = 0; x < stride; x++) {
      const a = x >= ch ? cur[x - ch] : 0;
      const bb = prev ? prev[x] : 0;
      const c = x >= ch && prev ? prev[x - ch] : 0;
      let v = src[x];
      if (ft === 1) v = (v + a) & 255;
      else if (ft === 2) v = (v + bb) & 255;
      else if (ft === 3) v = (v + ((a + bb) >> 1)) & 255;
      else if (ft === 4) {
        const pp = (a + bb - c) | 0;
        const pa = Math.abs(pp - a), pb = Math.abs(pp - bb), pc = Math.abs(pp - c);
        v = (v + (pa <= pb && pa <= pc ? a : pb <= pc ? bb : c)) & 255;
      }
      cur[x] = v;
    }
  }
  return { w, h, ch, data: out };
}
const px = (img, x, y) => {
  const i = (y * img.w + x) * img.ch;
  return [img.data[i], img.data[i + 1], img.data[i + 2]];
};
const chanDiff = (p1, p2) => Math.max(Math.abs(p1[0] - p2[0]), Math.abs(p1[1] - p2[1]), Math.abs(p1[2] - p2[2]));

/**
 * 稳态像素对比: 名称格内部取样带 vs 相邻格同 y 取样带(避开边缘 4px 与列分界), 逐 y 逐通道差。
 * 文字已隐藏 ⇒ 格内只剩底色, 任何一点都是纯背景。返回最大差与两侧样本(断言消息用)。
 */
async function steadyPixelDiff(page, rowSel, idx) {
  const rects = await page.evaluate(
    ({ rowSel, idx }) => {
      const row = document.querySelectorAll(rowSel)[idx];
      if (!row || !row.children[0] || !row.children[1]) return null;
      const r = (el) => { const b = el.getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height }; };
      return { c0: r(row.children[0]), c1: r(row.children[1]), dpr: window.devicePixelRatio || 1 };
    },
    { rowSel, idx },
  );
  if (!rects) return null;
  const img = decodePng(await page.screenshot());
  const s = rects.dpr;
  const ys = [0.3, 0.5, 0.7].map((f) => Math.round((rects.c0.y + rects.c0.h * f) * s));
  const nameX = Math.round((rects.c0.x + rects.c0.w - 10) * s);
  const sibX = Math.round((rects.c1.x + 12) * s);
  let maxD = 0, pair = null;
  for (const y of ys) {
    const d = chanDiff(px(img, nameX, y), px(img, sibX, y));
    if (d > maxD) { maxD = d; pair = [px(img, nameX, y), px(img, sibX, y)]; }
  }
  return { maxD, pair, namePx: px(img, nameX, ys[1]), sibPx: px(img, sibX, ys[1]) };
}

/* ---- 矩阵 ---- */
const CONTEXTS = [];
for (const skin of SKINS_ALL) CONTEXTS.push({ skin, rowlang: 'flat' });
for (const skin of WAVE_SKINS) CONTEXTS.push({ skin, rowlang: 'wave' });

for (const { skin, rowlang } of CONTEXTS) {
  const tag = `${skin}/${rowlang}`;

  test.describe(`必显列悬停全矩阵 ${tag}`, () => {
    installRuntimeErrorGuard(test);

    test(`种子表状态行: 悬停逐帧同步 + 稳态像素同底 @fast (${tag})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openView(page, skin, 'torrents', rowlang);
      await hideRowContent(page);

      let probed = 0;
      for (const st of ST_STATES) {
        const hit = await hoverableStateRow(page, `s-${st}`);
        if (!hit) continue; // 桩内无该状态行(如 s-error)—— 矩阵按实有状态覆盖
        probed += 1;

        // (1) 过渡窗口逐帧(滑入/移出): 仅 flat —— flat 下行板/首格底色同源 --dur 逐帧必须同步。
        //    wave 下此断言**不成立**(设计如此): 行板透明/斑马 tint 半透明、首格不透明 var(--bg),
        //    backgroundColor 表示本就不同, 可见色一致由 (2) 的像素地面真值承担; hover 高亮唯一
        //    来源是扫层(行 ::after z3 均匀覆盖), 不动两侧底色。
        // 滑入采样: 500ms 逐帧本身就是确定性 settle(覆盖 160ms 过渡 / wave 300ms 扫层), 不用 waitForTimeout
        await page.mouse.move(hit.x, hit.y);
        const inFrames = await traceColorsAt(page, hit.sel, hit.idx);
        if (rowlang === 'flat') {
          const inWorst = inFrames.reduce((m, f) => (f.d > m.d ? f : m), { d: 0, f: '', r: '' });
          expect(inFrames.length, `${tag} s-${st} 滑入采样帧太少`).toBeGreaterThan(8);
          expect(inWorst.d, `${tag} s-${st} 滑入: 首格 ${inWorst.f} vs 行板 ${inWorst.r} 逐帧错拍(差 ${inWorst.d})`)
            .toBeLessThanOrEqual(2);
        }

        // (2) 悬停稳态像素地面真值: 名称格 == 相邻格(可见底色, 表示法无关; wave 的扫层覆盖也在此验)
        const steady = await steadyPixelDiff(page, hit.sel, hit.idx);
        expect(steady, `${tag} s-${st} 取不到首格/相邻格矩形`).not.toBeNull();
        expect(steady.maxD, `${tag} s-${st} 悬停稳态: 名称格 ${steady.namePx} vs 相邻格 ${steady.sibPx} ` +
          `可见底色差 ${steady.maxD} —— 名称列竖带(用户报障面)`)
          .toBeLessThanOrEqual(2);

        // (3) 移出: 移出过渡采样(500ms = settle)+ 稳态像素
        await page.mouse.move(5, 5);
        await traceColorsAt(page, hit.sel, hit.idx);
        const back = await steadyPixelDiff(page, hit.sel, hit.idx);
        expect(back.maxD, `${tag} s-${st} 移出稳态: 名称格 ${back.namePx} vs 相邻格 ${back.sibPx} 差 ${back.maxD}`)
          .toBeLessThanOrEqual(2);
      }
      expect(probed, `${tag} 桩内一条可悬停状态行都没有 —— 矩阵空转即红`).toBeGreaterThan(0);
      expect(
        await page.evaluate(() => !!document.querySelector('.group-row[data-table="torrent"].s-downloading')),
        `${tag} 桩内必须有下载态行(用户报障面必须被覆盖)`,
      ).toBe(true);
    });

    test(`选中行悬停保持选中底(真手势 Ctrl+click) @fast (${tag})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openView(page, skin, 'torrents', rowlang);
      await hideRowContent(page);
      const hit = await hoverableStateRow(page, 's-downloading');
      expect(hit, `${tag} 找不到可悬停的下载态行`).not.toBeNull();
      await page.keyboard.down('Control');
      await page.mouse.click(hit.x, hit.y);
      await page.keyboard.up('Control');
      const sel = await page.evaluate(({ sel, idx }) => !!document.querySelectorAll(sel)[idx]?.classList.contains('selected'), { sel: hit.sel, idx: hit.idx });
      expect(sel, `${tag} Ctrl+click 未产生选中(手势/选择面变了?)`).toBe(true);
      await traceColorsAt(page, hit.sel, hit.idx); // 500ms settle(选中态切换)
      const steady = await steadyPixelDiff(page, hit.sel, hit.idx);
      expect(steady.maxD, `${tag} 选中行悬停: 名称格 ${steady.namePx} vs 相邻格 ${steady.sibPx} 差 ${steady.maxD} ` +
        `(坑档 frozen-column 10 口径: 选中态两侧必须同底)`).toBeLessThanOrEqual(2);
      // 复原(不污染后续用例的行序观感)
      await page.keyboard.down('Control');
      await page.mouse.click(hit.x, hit.y);
      await page.keyboard.up('Control');
    });

    test(`search-hit 行悬停保持命中底 @fast (${tag})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openView(page, skin, 'torrents', rowlang);
      await hideRowContent(page);
      // 类注入: 量 CSS 规则对面(行板命中渐层 vs 首格命中渐层镜像), 不依赖搜索链路。
      // 注 rows[0] 与 rows[1] 两条: wave 下斑马按数据行序奇偶打标(n%2===1 恒 zebra), 单注一条
      // 会在 flux/wave 恒命中 .search-hit.rl-zebra, 非斑马双层(flat/wave 行板+首格基础对)零覆盖。
      await page.evaluate(() => {
        const rows = document.querySelectorAll('.group-row[data-table="torrent"]');
        rows[0]?.classList.add('search-hit');
        rows[1]?.classList.add('search-hit');
      });
      // 阈值 3: 行板/首格渐层停靠点已收紧为固定 220px(2026-11-11 用户拍板, 口径单点在
      // row_lang.css flat 段注释) —— 两侧同一绝对几何, 逐像素一致; 残余差只有行 padding(14px)
      // 相位差那一项(14/220 斜率差, 折算 <=2 通道值), 阈值给取整余量取 3。旧百分比停靠点
      // (46%)时代边界实测 Δ20-28 —— 那条路已被静态守阵(test_webui_static_skins_table)钉死,
      // 这里是行为面回归线。
      const hitSel = '.group-row[data-table="torrent"].search-hit';
      let hitProbed = 0;
      for (let k = 0; k < 2; k++) {
        if ((await page.locator(hitSel).count()) <= k) break;
        const box = await page.locator(hitSel).nth(k).boundingBox();
        if (!box || box.height < 8 || box.y < 60 || box.y > 900) continue;
        const x = Math.max(Math.min(box.x + Math.min(box.width * 0.6, 900), 1580), box.x + 400);
        const y = Math.min(Math.max(box.y + box.height / 2, 8), 880);
        await page.mouse.move(5, 5);
        await page.mouse.move(x, y);
        expect(await page.evaluate(
          (k) => !!document.querySelectorAll('.group-row[data-table="torrent"].search-hit')[k]?.matches(':hover'), k,
        ), `${tag} search-hit 第${k}条不可悬停`).toBe(true);
        hitProbed += 1;
        // zebra 标注取实测(wave 下 n%2===1 打标; flat 恒无) —— 硬编码 k===1 在 flat 失败时会引向
        // 不存在的斑马规则(复评轮 minor)
        const isZebra = await page.evaluate(
          (k) => !!document.querySelectorAll('.group-row[data-table="torrent"].search-hit')[k]?.classList.contains('rl-zebra'), k,
        );
        await traceColorsAt(page, hitSel, k); // 500ms settle(悬停手势已在行上)
        const steady = await steadyPixelDiff(page, hitSel, k);
        expect(steady, `${tag} search-hit 第${k}条取不到首格/相邻格矩形`).not.toBeNull();
        expect(steady.maxD, `${tag} search-hit 第${k}条(zebra=${isZebra})悬停: 名称格 ${steady.namePx} vs 相邻格 ${steady.sibPx} 差 ${steady.maxD} ` +
          `(停靠点定案 220px 后应逐像素一致; 超限 = 渐层镜像几何分家回潮)`).toBeLessThanOrEqual(3);
      }
      expect(hitProbed, `${tag} search-hit 注入行全部不可悬停`).toBeGreaterThan(0);
    });

    test(`辅种表展开行悬停保持下沉底 @fast (${tag})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openView(page, skin, GROUPS_VIEW, rowlang);
      await hideRowContent(page);
      const sel = '.group-row[data-table="group"]';
      const box = await page.locator(sel).first().boundingBox();
      expect(box, `${tag} 辅种表无行`).not.toBeNull();
      const x = Math.max(Math.min(box.x + Math.min(box.width * 0.6, 900), 1580), box.x + 400);
      const y = Math.min(Math.max(box.y + box.height / 2, 8), 880);
      await page.mouse.click(x, y); // 点行 = 展开
      const expanded = await page.evaluate(() => !!document.querySelector('.group-row[data-table="group"].expanded'));
      expect(expanded, `${tag} 点击辅种行未展开(展开手势变了?)`).toBe(true);
      await page.mouse.move(x, y);
      await traceColorsAt(page, sel, 0); // 500ms settle
      const steady = await steadyPixelDiff(page, sel, 0);
      expect(steady.maxD, `${tag} 展开行悬停: 名称格 ${steady.namePx} vs 相邻格 ${steady.sibPx} 差 ${steady.maxD} ` +
        `(坑档 frozen-column 10 同族口径: 下沉底两侧同表达式)`).toBeLessThanOrEqual(2);
    });
  });
}
