// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 停靠面板几何稳定(2026-10-07 修「种子详情面板/流量图在搜索/筛选时跳动」) —— 静态守阵
 * (test_webui_static_skins_widget.py::test_frontend_search_pending_no_collapse)钉的是接线存在性; 本 spec 钉**行为**:
 * 静态守阵探不到「调用存在但几何/时机错」的缺陷(dock-panel 坑档 2026-10-04 教训), 必须真浏览器采样。
 *
 * 两个被修缺陷的真机指纹(修复前取证, prism 皮肤 1280x800, 逐帧采样):
 * 1. 搜索待响应窗(防抖 400ms + 请求往返)把列表塌成 0 行 => docH 18582→800(塌到视口高)→1141,
 *    滚动位置被钳回 0(列表中部搜一次整页跳顶), 面板 top 430↔416 反复横跳;
 * 2. 列表被筛短后文档变矮, .drawer-dock 的 sticky 吸底脱锚, 面板跟着内容末尾上浮(视口越高跳越多)。
 *
 * 断言口径: 面板开着逐字输入搜索词, 全程逐帧采样 —— 面板 top 偏差 ≤2px(吸底锚点稳定),
 * 且 docH 任一时刻不塌到视口高 +150px 以内(真结果落袋 docH = 视口高+行数; 待响应塌列表 = 恰视口高)。
 *
 * S0 红验基线(计划 26-11-12-1048 §04 S0; W1/W2 各自独立红绿, D5; 判据 = 位移量/位移事件次数, R6):
 * 1. W1 开-关-再开: 用户复现路径(文档底选被覆盖行开面板 → 关 → 等收场完 → 选附近未被覆盖行 → 再开)
 *    逐帧采样, 断言第二步打开全程 scrollY 与选中行 rect.bottom 零位移。
 *    修复前实测(2026-11-13, prism+atlas 双皮肤): **两皮肤均绿, 未复现红** —— 计划 §02 的 W1 根因
 *    (_drawerAnimTop 跨周期残留被 reveal 消费)被真机判别实验否定: 关后改 drawerHeightPx 再开,
 *    重开后第一帧 animTop 已从残留值(626)重写为新鲜落定顶缘(488), 即 enter 钩子在 nextTick 量测前
 *    必然重写登记; 且 dock 恒 sticky 吸底(866-dockH) + 面板高度恒锁 → 残留值恒等于新鲜顶缘,
 *    "旧顶缘偏小"在该几何下不可构造。真机另捕到判据的**有意越过带**(vBot = 面板顶-8 再 -4 容差,
 *    dock-panel.md:50-51): 行底在面板顶 12px 之内的"未被覆盖"行会按设计被抬 4~16px, 首次打开同样
 *    触发(实测 dy=10.5) —— 用户报障的症状带更可能是它, 不是跨周期残留; 该带属判据语义, W1 的
 *    登记生命周期修复(S1)对它无效, 详见任务报告。
 * 2. W2 收场非文档底: 滚动位远离文档底时关面板, 全程零位移(回归守卫; 修复前后都可能绿, 如实记录)。
 * 3. W2 收场文档底(W2 红验主判据): 贴文档底关面板, leave 钩子逐帧写 dock.style.height → 文档逐帧
 *    变矮 → 浏览器逐帧钳制 scrollY —— 修复前实测位移事件 8~11 次(双皮肤多次运行, D11 判据
 *    允许一次性位移 ≤1), 逐帧序列存逐条断言消息。
 */

/* ==================== S0 三条用例共用小件(判据一律位移量/事件次数, 不用绝对像素阈值) ==================== */

/** 列表落定等待: 渲染行数 + 滚动位两拍全等(拍距 250ms) —— 滚到文档底后等窗口化重渲完成。 */
async function waitListSettled(page) {
  await page.waitForFunction(() => {
    const cur = JSON.stringify([document.querySelectorAll('.torrent-row').length, Math.round(window.scrollY)]);
    if (window.__listSettled === cur) return true;
    window.__listSettled = cur;
    return false;
  }, undefined, { timeout: 10_000, polling: 250 });
}

/** 面板几何落定等待: dock top/height + scrollY 三量两拍全等(拍距 250ms) —— 机制同文件头既有用例
 *  的 __geoSettled(enter 动画 + 详情到手长高 + 让位 scroll 全部停稳才算落定)。 */
async function waitDockSettled(page) {
  await page.waitForFunction(() => {
    const r = document.querySelector('.drawer-dock').getBoundingClientRect();
    const cur = JSON.stringify([Math.round(r.top), Math.round(r.height), Math.round(window.scrollY)]);
    if (window.__geoSettled === cur) return true;
    window.__geoSettled = cur;
    return false;
  }, undefined, { timeout: 10_000, polling: 250 });
}

/** 收场收拢完成等待: dock 高 ≤0.5px(160ms 收场曲线末帧; 面板节点 detach 要到 220ms, 不等它)。 */
async function waitDockCollapsed(page) {
  await page.waitForFunction(
    () => document.querySelector('.drawer-dock').getBoundingClientRect().height <= 0.5,
    undefined, { timeout: 5_000, polling: 30 },
  );
}

/** 挑"会被抽屉覆盖"的行: 全开顶缘(pt)以下 60px 起、中心在状态栏上缘之上(可点)的渲染行里取最深
 *  一行 —— 即用户路径里"列表最下方会被面板盖住"的种子。 */
async function pickCoveredRow(page, pt) {
  return page.evaluate((panelTop) => {
    const sb = document.querySelector('.statusbar');
    const sbTop = sb ? sb.getBoundingClientRect().top : window.innerHeight;
    let best = null;
    for (const r of document.querySelectorAll('.torrent-row')) {
      const b = r.getBoundingClientRect();
      if (b.bottom > panelTop + 60 && (b.top + b.bottom) / 2 < sbTop - 8 && (!best || b.bottom > best.bottom)) {
        best = { hash: r.getAttribute('data-hash'), top: Math.round(b.top), bottom: Math.round(b.bottom) };
      }
    }
    return best;
  }, pt);
}

/** 挑"不会被抽屉覆盖"的行: 行底在全开顶缘(pt)- 16px 之上的渲染行里取最深一行(最靠近面板的)。
 *  16px = 判据有意越过的 8px 呼吸距 + 4px 容差(dock-panel.md:50-51, 该带内的行按设计会被抬)
 *  再加 4px 取整余量 —— 挑行避开这个带, 免得把判据的设计行为误当跨周期缺陷。 */
async function pickUncoveredRow(page, pt) {
  return page.evaluate((panelTop) => {
    const sb = document.querySelector('.statusbar');
    const sbTop = sb ? sb.getBoundingClientRect().top : window.innerHeight;
    let best = null;
    for (const r of document.querySelectorAll('.torrent-row')) {
      const b = r.getBoundingClientRect();
      if (b.bottom < panelTop - 16 && (b.top + b.bottom) / 2 < sbTop - 8 && (!best || b.bottom > best.bottom)) {
        best = { hash: r.getAttribute('data-hash'), top: Math.round(b.top), bottom: Math.round(b.bottom) };
      }
    }
    return best;
  }, pt);
}

/** rAF 逐帧采样器(S0/D11): 每帧记 scrollY / docH / dock(top,h) / 面板 top / 选中行 rect.bottom /
 *  vm._drawerAnimTop; window.scrollBy 调用一并登记(只作诊断, 不参与断言)。
 *  stopGeoSampler 取回 { frames, sb } 并停拍。 */
async function installGeoSampler(page, hash) {
  await page.evaluate((h) => {
    const vm = document.querySelector('#app')._vnode.component.proxy;
    window.__geo = [];
    window.__sb = [];
    if (!window.__sbOrig) {
      window.__sbOrig = window.scrollBy;
      window.scrollBy = function (x, y) {
        window.__sb.push({ y, at: Math.round(performance.now()) });
        return window.__sbOrig.call(window, x, y);
      };
    }
    window.__geoHash = h;
    window.__geoStop = false;
    const tick = () => {
      if (window.__geoStop) return;
      const dock = document.querySelector('.drawer-dock');
      const panel = document.querySelector('.drawer-dock > .drawer');
      const row = window.__geoHash ? document.querySelector(`[data-hash="${window.__geoHash}"]`) : null;
      const dr = dock ? dock.getBoundingClientRect() : null;
      const pr = panel ? panel.getBoundingClientRect() : null;
      const rr = row ? row.getBoundingClientRect() : null;
      window.__geo.push({
        t: Math.round(performance.now()), y: Math.round(window.scrollY),
        docH: document.documentElement.scrollHeight, animTop: vm._drawerAnimTop || 0,
        open: !!vm.drawer.open,
        dockH: dr ? Math.round(dr.height) : null, dockTop: dr ? Math.round(dr.top) : null,
        panelTop: pr ? Math.round(pr.top) : null,
        rowB: rr ? Math.round(rr.bottom) : null,
      });
      if (window.__geo.length < 6000) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, hash);
}

/** 停采样并取回全部帧 + scrollBy 登记表。 */
async function stopGeoSampler(page) {
  return page.evaluate(() => {
    window.__geoStop = true;
    return { frames: window.__geo, sb: window.__sb };
  });
}

/** 位移事件数: 相邻采样帧 scrollY 不相等的次数(D11 口径 —— 逐帧钳制每帧计一次, 一次性位移只计一次)。 */
function scrollEvents(frames) {
  let n = 0;
  for (let i = 1; i < frames.length; i++) if (frames[i].y !== frames[i - 1].y) n++;
  return n;
}

/** 采样帧压缩序列(断言消息用): y 与 dockH 两条, 相邻全等的段折叠成 "值xN"。 */
function frameDigest(frames) {
  const fold = (key) => {
    const out = [];
    for (const f of frames) {
      const v = f[key];
      if (out.length && out[out.length - 1].v === v) out[out.length - 1].n++;
      else out.push({ v, n: 1 });
    }
    return out.map((s) => `${s.v}${s.n > 1 ? `x${s.n}` : ''}`).join(',');
  };
  return `y=[${fold('y')}] dockH=[${fold('dockH')}]`;
}

for (const skin of SKINS) {
  test.describe(`停靠面板几何稳定 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`搜索全程面板 top 不变、文档高不塌 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 种子视图平铺行双击开详情面板
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await page.dblclick('.torrent-row >> nth=0', { force: true }); // force: 整表 2s 重渲染抢点击(smoke.md)
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      // 等面板几何落定(enter 动画 + 详情到手长到 42vh): top/height 连续 250ms 不再变化才算落定,
      // 否则采样把"进场长高"也算进偏差, 与搜索无关的初始 settle 会误红
      await page.waitForFunction(() => {
        const r = document.querySelector('.drawer-dock').getBoundingClientRect();
        const cur = JSON.stringify([Math.round(r.top), Math.round(r.height)]);
        if (window.__geoSettled === cur) return true;
        window.__geoSettled = cur;
        return false;
      }, undefined, { timeout: 10_000, polling: 250 });

      // 逐帧采样贯穿: 输入 → 防抖 → 请求在途 → 落袋换列表
      await page.evaluate(() => {
        window.__geo = [];
        const tick = () => {
          const r = document.querySelector('.drawer-dock').getBoundingClientRect();
          window.__geo.push({ top: Math.round(r.top), docH: document.documentElement.scrollHeight });
          if (window.__geo.length < 1200) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      });

      const input = page.locator('.search-box input');
      await input.click();
      await input.pressSequentially('GROUP7', { delay: 120 }); // 桩数据里 ~5 个命中(短结果, 落袋必缩列表)
      // 等落袋: 列表确实换成短结果(docH 缩小)后, 几何才允许定格
      await expect
        .poll(() => page.evaluate(() => document.documentElement.scrollHeight), { timeout: 10_000 })
        .toBeLessThan(15_000);

      const geo = await page.evaluate(() => { window.__geo = window.__geo || []; return window.__geo; });
      expect(geo.length, '逐帧采样应有足够样本').toBeGreaterThan(30);
      const tops = geo.map((s) => s.top);
      const topSpan = Math.max(...tops) - Math.min(...tops);
      expect(topSpan, `面板 top 全程偏差(实测 ${Math.min(...tops)}~${Math.max(...tops)})`).toBeLessThanOrEqual(2);
      const minDocH = Math.min(...geo.map((s) => s.docH));
      // 塌列表指纹 = 恰视口高(内容撑不起文档); 留 150px 余量把真短结果(视口高 + 数行)与塌列表分开
      expect(minDocH, `文档高不得塌到近视口高(实测最小 ${minDocH}, 视口 ${await page.evaluate(() => innerHeight)})`)
        .toBeGreaterThan(await page.evaluate(() => innerHeight) + 150);
    });

    /* ==================== S0 红验基线(计划 26-11-12-1048 §04 S0) ==================== */

    test(`W1 开-关-再开: 附近未被覆盖的行再开抽屉全程零位移 @fast (${skin})`, async ({ page }) => {
      test.setTimeout(60_000);
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 步骤1(用户路径): 列表滚到底部附近, 选中一个会被抽屉覆盖的行并打开。
      // 行被让位抬起属正常 —— 只记录(scrollY/行位置), 不对第一次打开判红绿。
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await waitListSettled(page);
      const panelTopEst = await page.evaluate(() => {
        const sb = document.querySelector('.statusbar');
        const sbTop = sb ? sb.getBoundingClientRect().top : window.innerHeight;
        return sbTop - Math.round(window.innerHeight * 0.42); // 全开顶缘估算: 状态栏顶 - 42vh
      });
      const cov = await pickCoveredRow(page, panelTopEst);
      expect(cov, `前置: 文档底视口内应有会被抽屉覆盖的行(全开顶缘估算 ${panelTopEst})`).toBeTruthy();
      // position 左缘 {x:8,y:8}: 行宽超出视口(实测 2660px), 中心点会命中溢出的 h-label 等行外元素(smoke.md)
      await page.dblclick(`.torrent-row[data-hash="${cov.hash}"]`, { force: true, position: { x: 8, y: 8 } });
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      await waitDockSettled(page);
      const opened = await page.evaluate((h) => {
        const d = document.querySelector('.drawer-dock').getBoundingClientRect();
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { dockTop: Math.round(d.top), dockH: Math.round(d.height), rowB: Math.round(r.bottom), y: Math.round(window.scrollY) };
      }, cov.hash);

      // 步骤2: 关闭抽屉, 等收场动画结束
      await page.click('.drawer-dock .drawer-close');
      await waitDockCollapsed(page);

      // 步骤3: 选中附近一个不会被抽屉覆盖的行(其行底在抽屉全开顶缘之上, 取最靠近面板的一行)
      const near = await pickUncoveredRow(page, opened.dockTop);
      expect(near, `前置: 收场后视口内应有未被抽屉覆盖的行(全开顶缘 ${opened.dockTop})`).toBeTruthy();
      expect(near.hash, '前置: 第二次选中的应是另一行(附近换目标)').not.toBe(cov.hash);

      // 步骤4: 打开抽屉, rAF 逐帧采样全程。基线显式预读(收场钳制已完成、几何静止)——
      // 不依赖采样器捕到"打开前帧"(重开很快时第一帧就可能已是 open=true, atlas 实测过)。
      const baseline = await page.evaluate((h) => {
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { y: Math.round(window.scrollY), rowB: Math.round(r.bottom) };
      }, near.hash);
      await installGeoSampler(page, near.hash);
      await page.dblclick(`.torrent-row[data-hash="${near.hash}"]`, { force: true, position: { x: 8, y: 8 } });
      // 采样窗口用条件等待收口(与第一次打开同款两拍落定, 不用固定 waitForTimeout): enter 动画 +
      // 三发让位(含 drawer_store.js:394-398 集合落定兑现的那发, 它发生在详情到手时刻)全部停稳才
      // 停拍 —— 固定 900ms 对"详情到手"覆盖不确定, 桩慢(R6 时序差异)会把第三发让位漏采成假绿
      await waitDockSettled(page);
      const { frames, sb } = await stopGeoSampler(page);
      expect(frames.length, '前置: 采样应有足够帧数').toBeGreaterThan(10);

      // 前置: 第二次打开确实发生且面板到过全高(否则断言空转)
      const openedFrames = frames.filter((f) => f.open);
      expect(openedFrames.length, '前置: 采样应覆盖到第二次打开的动画期').toBeGreaterThan(0);
      const maxDockH = Math.max(...openedFrames.map((f) => f.dockH ?? 0));
      expect(maxDockH, `前置: 第二次打开后面板应到过全高(实测峰值 ${maxDockH}, 首开 ${opened.dockH})`)
        .toBeGreaterThanOrEqual(opened.dockH - 4);

      // 断言(修复后应绿): 第二步打开全程 scrollY 与选中行 rect.bottom 零位移。
      // 2026-11-13 修复前实测: prism/atlas 两皮肤均绿(逐帧 y 一字不动, rowB 抖动 ≤1px 取整噪声),
      // 红未能复现的原因与判据越带证据见文件头 S0 节 —— 如实记录, 不放宽也不硬造红。
      const dy = frames.map((f) => f.y - baseline.y);
      const db = frames.map((f) => (f.rowB ?? baseline.rowB) - baseline.rowB);
      expect(Math.max(...dy.map(Math.abs)),
        `第二次打开全程 scrollY 位移量(基线 ${baseline.y}; 序列 ${frameDigest(frames)}; scrollBy 登记 ${JSON.stringify(sb)})`)
        .toBe(0);
      expect(Math.max(...db.map(Math.abs)),
        `第二次打开全程选中行 rect.bottom 位移量(基线 ${baseline.rowB}, 选行 ${JSON.stringify(near)}; scrollBy ${JSON.stringify(sb)})`)
        .toBeLessThanOrEqual(1); // 1px = 行矩形取整噪声(实测逐帧 468→467 一类抖动), 非绝对像素判据
    });

    test(`W2 收场非文档底: 关面板全程零位移(回归守卫) @fast (${skin})`, async ({ page }) => {
      test.setTimeout(60_000);
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 滚到文档中部(远离文档底), 开面板落定 —— 关场时文档变矮但滚动余量足额, 不该发生任何钳制
      await page.evaluate(() => window.scrollTo(0, 3000));
      await waitListSettled(page);
      const row = await page.evaluate(() => {
        const sb = document.querySelector('.statusbar');
        const sbTop = sb ? sb.getBoundingClientRect().top : window.innerHeight;
        // 筛选条 .status-strip sticky 盖住视口顶部(wrap 后实测高 ~150px), 行顶必须在它之下才是可点的
        const strip = document.querySelector('.status-strip');
        const stripBottom = strip ? strip.getBoundingClientRect().bottom : 0;
        for (const r of document.querySelectorAll('.torrent-row')) {
          const b = r.getBoundingClientRect();
          if (b.top > stripBottom + 4 && (b.top + b.bottom) / 2 < sbTop - 8) return r.getAttribute('data-hash');
        }
        return null;
      });
      expect(row, '前置: 文档中部视口内应有可见可点的行').toBeTruthy();
      await page.dblclick(`.torrent-row[data-hash="${row}"]`, { force: true, position: { x: 8, y: 8 } });
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      await waitDockSettled(page);
      const openedH = await page.evaluate(() => Math.round(document.querySelector('.drawer-dock').getBoundingClientRect().height));

      // 采样贯穿 close 全程
      await installGeoSampler(page, row);
      await page.click('.drawer-dock .drawer-close');
      await page.waitForTimeout(700);
      const { frames } = await stopGeoSampler(page);

      // 前置: 收场确实发生了(dock 高从全高收到 0, 文档同步变矮)
      const maxDockH = Math.max(...frames.map((f) => f.dockH ?? 0));
      const lastDockH = frames[frames.length - 1].dockH ?? 0;
      const docHDrop = Math.max(...frames.map((f) => f.docH)) - Math.min(...frames.map((f) => f.docH));
      expect(maxDockH, `前置: 面板应到过全高(实测峰值 ${maxDockH}, 首开 ${openedH})`).toBeGreaterThanOrEqual(openedH - 4);
      expect(lastDockH, `前置: 收场应完成(dock 末帧高 ${lastDockH})`).toBeLessThanOrEqual(2);
      expect(docHDrop, `前置: 文档应随收场变矮(实测落差 ${docHDrop})`).toBeGreaterThanOrEqual(openedH - 4);

      // 断言(修复前后都可能绿 —— 回归守卫): 收场全程零位移
      const events = scrollEvents(frames);
      const firstY = frames[0].y;
      const lastY = frames[frames.length - 1].y;
      expect(events, `收场期 scrollY 位移事件数应为 0(实测 ${events}; 序列 ${frameDigest(frames)})`).toBe(0);
      expect(Math.abs(lastY - firstY), `收场期 scrollY 净位移应为 0(实测 ${firstY} -> ${lastY})`).toBe(0);
    });

    test(`W2 收场文档底: 收场期位移事件 ≤1 不得逐帧反复 @fast (${skin})`, async ({ page }) => {
      test.setTimeout(60_000);
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 文档底开面板(被覆盖行正常让位), 落定后显式滚到文档底吃满停靠槽位 headroom ——
      // 保证收场文档变矮时滚动位必然被钳制(让位只消耗部分余量, 显式滚满使前置确定性成立)
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await waitListSettled(page);
      const panelTopEst = await page.evaluate(() => {
        const sb = document.querySelector('.statusbar');
        const sbTop = sb ? sb.getBoundingClientRect().top : window.innerHeight;
        return sbTop - Math.round(window.innerHeight * 0.42);
      });
      const cov = await pickCoveredRow(page, panelTopEst);
      expect(cov, `前置: 文档底视口内应有会被抽屉覆盖的行(全开顶缘估算 ${panelTopEst})`).toBeTruthy();
      // position 左缘 {x:8,y:8}: 行宽超出视口(实测 2660px), 中心点会命中溢出的 h-label 等行外元素(smoke.md)
      await page.dblclick(`.torrent-row[data-hash="${cov.hash}"]`, { force: true, position: { x: 8, y: 8 } });
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      await waitDockSettled(page);
      const openedH = await page.evaluate(() => Math.round(document.querySelector('.drawer-dock').getBoundingClientRect().height));
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await page.waitForTimeout(150);
      const preDoc = await page.evaluate(() => ({ y: Math.round(window.scrollY), max: document.documentElement.scrollHeight - window.innerHeight }));
      expect(preDoc.y, `前置: 收场前必须贴文档底(实测 y=${preDoc.y}, maxScroll=${preDoc.max})`).toBe(preDoc.max);

      // 采样贯穿 close 全程(leave 钩子逐帧写 dock.style.height → 文档逐帧变矮 → 浏览器逐帧钳制)
      await installGeoSampler(page, cov.hash);
      await page.click('.drawer-dock .drawer-close');
      await page.waitForTimeout(700);
      const { frames } = await stopGeoSampler(page);

      // 前置: 收场确实发生了
      const maxDockH = Math.max(...frames.map((f) => f.dockH ?? 0));
      const lastDockH = frames[frames.length - 1].dockH ?? 0;
      const docHDrop = Math.max(...frames.map((f) => f.docH)) - Math.min(...frames.map((f) => f.docH));
      expect(maxDockH, `前置: 面板应到过全高(实测峰值 ${maxDockH}, 首开 ${openedH})`).toBeGreaterThanOrEqual(openedH - 4);
      expect(lastDockH, `前置: 收场应完成(dock 末帧高 ${lastDockH})`).toBeLessThanOrEqual(2);
      expect(docHDrop, `前置: 文档应随收场变矮(实测落差 ${docHDrop})`).toBeGreaterThanOrEqual(openedH - 4);

      // 断言(D11, 修复前应红): 允许一次性位移, 但位移事件计数 ≤1 —— 逐帧钳制 = 每帧一个事件。
      // 2026-11-13 修复前实测: 双皮肤 10~11 次(scrollY 逐帧阶梯下降), 红。
      const events = scrollEvents(frames);
      expect(events, `收场期 scrollY 位移事件数(D11 判据 ≤1; 实测 ${events}; 序列 ${frameDigest(frames)})`)
        .toBeLessThanOrEqual(1);
    });
  });
}
