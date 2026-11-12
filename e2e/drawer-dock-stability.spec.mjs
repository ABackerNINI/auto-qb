// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * S-A 扩展(2026-11-13): 本 spec 的用例矩阵扩成三皮肤(prism/atlas/flux) —— flux 是 S-A 首开
 * 遮挡竞速的当事皮肤, 既有 W1 守卫/W2 两用例/S-C 两用例一并扩到 flux 跑(任务口径「优先把
 * SKINS 扩成三皮肤」)。全局 SKINS(harness.mjs 冒烟预算单点, 53 个 spec 共用)不动, 只本 spec
 * 局部扩 —— 全局翻三皮肤会让整套 e2e 运行时长翻倍以上, 超出本任务预算。
 */
const DOCK_SKINS = [...SKINS, 'flux'];

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
 *
 * S-C 判据越过带收紧(2026-11-13 用户拍板「未被覆盖的行绝对不动」, 替代已取消的 S1): 上面的 W1
 * 红验未复现的原因即本判据的**有意越过带** —— 旧触发界 rect.bottom > vBot - 4(vBot = 面板顶 - 8)
 * 把行底落在 (面板顶-12, 面板顶] 的未覆盖行也按公式抬 4~16px。收紧后触发界 = 单点 + 界源分支补差
 * (_kbViewBottomPad: 面板分支 +8 呼吸距补偿 → 界 = 面板顶实缘; 状态栏/整窗分支 +0 精确边 → 关闭
 * 路径遮 1~8px 的行照旧让位, 不外溢过紧): 行底 <= 面板顶的行在首开/再开全程零位移; 位移公式不动,
 * 真覆盖行(行底 > 面板顶)仍让位到公式终值 vBot - 8 = 面板顶 - 16(修复前后都必须绿)。用例:
 * 4. S-C 越过带: 滚动相位对齐把行底精确送到带中央(面板顶 - 6), 首开与「关→再开」两个场景
 *    全程零位移; 修复前预期红(实测被抬 4~16px)。
 * 5. S-C 反向守卫: 真被覆盖的行(最深 + 最浅边界探针)仍被让位到公式终值 —— 最深行钉公式全程
 *    无钳制, 最浅行(面板顶 + 3 对齐)直接贴触发界边界, 拦「结构性过紧到中浅覆盖行漏让」。
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

/** 任意两列压缩序列(S-A 遮挡时序用): 同 fold 机制, 列名带进标签。 */
function pairDigest(frames, keyA, keyB) {
  const fold = (key) => {
    const out = [];
    for (const f of frames) {
      const v = f[key];
      if (out.length && out[out.length - 1].v === v) out[out.length - 1].n++;
      else out.push({ v, n: 1 });
    }
    return out.map((s) => `${s.v}${s.n > 1 ? `x${s.n}` : ''}`).join(',');
  };
  return `${keyA}=[${fold(keyA)}] ${keyB}=[${fold(keyB)}]`;
}

for (const skin of DOCK_SKINS) {
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

    /* ==================== S-C 判据越过带收紧(2026-11-13 用户拍板「未被覆盖的行绝对不动」) ==================== */

    test(`S-C 越过带: 带内未覆盖行首开与再开全程零位移 @fast (${skin})`, async ({ page }) => {
      test.setTimeout(90_000);
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 距文档底 600px 滚动(预留收场 headroom: 关面板文档变矮 ~面板全高, scrollY 不得被钳制挪动
      // 行位 —— 钳制是 W2 文档底用例的取证口径, 不混入本判据; 600 > 面板全高 + 呼吸距, 对齐增量
      // (<= 半行)吃不完)。
      await page.evaluate(() => {
        window.scrollTo(0, document.documentElement.scrollHeight - window.innerHeight - 600);
      });
      await waitListSettled(page);

      // 滚动相位对齐: 挑最深一个行底 <= 全开顶缘估算的行, scrollBy 精确送到带中央(顶缘 - 6)。
      // 顶缘估算 = 状态栏顶 - 42vh(W1 用例同式; dock sticky bottom = --statusbar-h + 面板高恒锁
      // 42vh, 估算对实值的偏差只有取整级 ±1px, ±5px 内带判据不受扰)。越过带 = (面板顶-12, 面板顶]:
      // 旧触发界 vBot - 4(vBot = 面板顶 - 8)的触发范围, 带内行肉眼未被覆盖(行底 <= 面板顶)。
      const aligned = await page.evaluate(() => {
        const sb = document.querySelector('.statusbar');
        const sbTop = sb ? sb.getBoundingClientRect().top : window.innerHeight;
        const panelTopEst = sbTop - Math.round(window.innerHeight * 0.42);
        let best = null;
        for (const r of document.querySelectorAll('.torrent-row')) {
          const b = r.getBoundingClientRect();
          if (b.bottom <= panelTopEst && (b.top + b.bottom) / 2 < sbTop - 8 && (!best || b.bottom > best.bottom)) {
            best = { hash: r.getAttribute('data-hash'), bottom: b.bottom };
          }
        }
        if (!best) return null;
        // 下滚把行往上搬(scrollY 增大 = 内容上移): 行底要从 best.bottom 移到 panelTopEst - 6(更下方),
        // 滚动量 = 当前 - 目标(负值 = 上滚, 行随内容下移进带)。红验第一轮曾写反成 目标-当前,
        // 行被滚出带下方 21px, 前置断言当场拦下 —— 带对齐的符号口径以此为准。
        window.scrollBy(0, Math.round(best.bottom - (panelTopEst - 6)));
        return best.hash;
      });
      expect(aligned, '前置: 视口内应有行底不越过全开顶缘的行(带对齐原料)').toBeTruthy();
      await waitListSettled(page);

      // 场景1(首开): 基线预读 -> 采样 -> 双击带内行 -> 落定(三发让位全部停稳)。
      const band = await page.evaluate((h) => {
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { y: Math.round(window.scrollY), rowB: r.bottom };
      }, aligned);
      await installGeoSampler(page, aligned);
      await page.dblclick(`.torrent-row[data-hash="${aligned}"]`, { force: true, position: { x: 8, y: 8 } });
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      await waitDockSettled(page);
      const first = await stopGeoSampler(page);
      const panelGeo = await page.evaluate(() => {
        const p = document.querySelector('.drawer-dock > .drawer').getBoundingClientRect();
        return { top: p.top, h: p.height };
      });

      // 前置: 面板到过全高; 行底(打开前实测)确实落在越过带内 —— 对面板顶**实值**判, 估算偏差
      // 超过 ±5px 在此显形(测试无效), 不静默放过。
      const maxDockH1 = Math.max(...first.frames.filter((f) => f.open).map((f) => f.dockH ?? 0));
      expect(maxDockH1, `前置: 首开面板应到过全高(实测峰值 ${maxDockH1}, 落定 ${Math.round(panelGeo.h)})`)
        .toBeGreaterThanOrEqual(Math.round(panelGeo.h) - 4);
      expect(band.rowB, `前置: 对齐后行底 ${band.rowB.toFixed(1)} 应在越过带 (${panelGeo.top - 12}, ${panelGeo.top}] 内(面板顶实值)`)
        .toBeGreaterThan(panelGeo.top - 12 - 1);
      expect(band.rowB, `前置: 对齐后行底 ${band.rowB.toFixed(1)} 不得真被覆盖(应 <= 面板顶实值 ${panelGeo.top.toFixed(1)})`)
        .toBeLessThanOrEqual(panelGeo.top + 1);

      // 断言(修复后应绿, 修复前红: 带内行被抬 4~16px): 首开全程 scrollY 与行 rect.bottom 零位移。
      const dy1 = first.frames.map((f) => f.y - band.y);
      const db1 = first.frames.map((f) => (f.rowB ?? band.rowB) - band.rowB);
      expect(Math.max(...dy1.map(Math.abs)),
        `首开全程 scrollY 位移量(基线 ${band.y}; 序列 ${frameDigest(first.frames)}; scrollBy 登记 ${JSON.stringify(first.sb)})`)
        .toBe(0);
      expect(Math.max(...db1.map(Math.abs)),
        `首开全程行 rect.bottom 位移量(基线 ${band.rowB.toFixed(1)}; scrollBy ${JSON.stringify(first.sb)})`)
        .toBeLessThanOrEqual(1);

      // 场景2(再开, 用户症状路径): 关 -> 等收场 -> 同一带内行再开。先证收场没挪行位(headroom
      // 足额无钳制), 再开断言同一套零位移。
      await page.click('.drawer-dock .drawer-close');
      await waitDockCollapsed(page);
      const reopened = await page.evaluate((h) => {
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { y: Math.round(window.scrollY), rowB: r.bottom };
      }, aligned);
      expect(Math.abs(reopened.rowB - band.rowB),
        `收场不得挪动带内行位(行底 ${band.rowB.toFixed(1)} -> ${reopened.rowB.toFixed(1)}; 收场期钳制即此处红)`)
        .toBeLessThanOrEqual(1);
      expect(reopened.rowB, `前置: 再开前带判据应仍成立(行底 ${reopened.rowB.toFixed(1)} vs 面板顶 ${panelGeo.top.toFixed(1)})`)
        .toBeGreaterThan(panelGeo.top - 12 - 1);
      await installGeoSampler(page, aligned);
      await page.dblclick(`.torrent-row[data-hash="${aligned}"]`, { force: true, position: { x: 8, y: 8 } });
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      await waitDockSettled(page);
      const second = await stopGeoSampler(page);
      expect(second.frames.length, '前置: 采样应有足够帧数').toBeGreaterThan(10);
      const dy2 = second.frames.map((f) => f.y - reopened.y);
      const db2 = second.frames.map((f) => (f.rowB ?? reopened.rowB) - reopened.rowB);
      expect(Math.max(...dy2.map(Math.abs)),
        `再开全程 scrollY 位移量(基线 ${reopened.y}; 序列 ${frameDigest(second.frames)}; scrollBy 登记 ${JSON.stringify(second.sb)})`)
        .toBe(0);
      expect(Math.max(...db2.map(Math.abs)),
        `再开全程行 rect.bottom 位移量(基线 ${reopened.rowB.toFixed(1)}; scrollBy ${JSON.stringify(second.sb)})`)
        .toBeLessThanOrEqual(1);
    });

    test(`S-C 反向守卫: 真被覆盖的行(最深+最浅边界探针)仍让位到公式终值 @fast (${skin})`, async ({ page }) => {
      test.setTimeout(90_000);
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 双探针(防过紧): 探针1 = 最深被覆盖行(覆盖深达 ~42vh-16px)钉「公式全程 + 无文档底钳制」;
      // 探针2 = 最浅被覆盖行(行底刚过面板顶 + 补差)直接贴新触发界边界 —— 只探最深行拦不住
      // 「触发界结构性过紧到中浅覆盖行漏让」(如把面板分支补差误做成 +16, 最深行仍会让位)。
      // 距文档底 600px(下滚余量足额, 让位 scrollBy 不被文档底钳制 —— 文档底钳制是已修缺陷的
      // 取证口径, 不混入本判据)。挑最深一个行底越过全开顶缘估算 + 8 且可点(中心在状态栏上缘
      // 之上)的行 = 真被面板覆盖的行。
      await page.evaluate(() => {
        window.scrollTo(0, document.documentElement.scrollHeight - window.innerHeight - 600);
      });
      await waitListSettled(page);
      const covered = await page.evaluate(() => {
        const sb = document.querySelector('.statusbar');
        const sbTop = sb ? sb.getBoundingClientRect().top : window.innerHeight;
        const panelTopEst = sbTop - Math.round(window.innerHeight * 0.42);
        let best = null;
        for (const r of document.querySelectorAll('.torrent-row')) {
          const b = r.getBoundingClientRect();
          if (b.bottom > panelTopEst + 8 && b.bottom < sbTop - 8 && (!best || b.bottom > best.bottom)) {
            best = { hash: r.getAttribute('data-hash'), bottom: b.bottom };
          }
        }
        return best;
      });
      expect(covered, '前置: 视口内应有真被面板覆盖的行(行底越过全开顶缘 + 8)').toBeTruthy();

      const base = await page.evaluate((h) => {
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { y: Math.round(window.scrollY), rowB: r.bottom };
      }, covered.hash);
      await installGeoSampler(page, covered.hash);
      await page.dblclick(`.torrent-row[data-hash="${covered.hash}"]`, { force: true, position: { x: 8, y: 8 } });
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      await waitDockSettled(page);
      const run = await stopGeoSampler(page);
      const after = await page.evaluate((h) => {
        const p = document.querySelector('.drawer-dock > .drawer').getBoundingClientRect();
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { panelTop: p.top, panelH: p.height, rowB: r.bottom, y: Math.round(window.scrollY) };
      }, covered.hash);

      // 前置: 行底真被覆盖(越过面板顶实值 + 4px 裕量), 且面板到过全高
      expect(base.rowB, `前置: 行底 ${base.rowB.toFixed(1)} 应真被覆盖(> 面板顶实值 ${after.panelTop.toFixed(1)} + 4)`)
        .toBeGreaterThan(after.panelTop + 4);
      const maxDockH = Math.max(...run.frames.filter((f) => f.open).map((f) => f.dockH ?? 0));
      expect(maxDockH, `前置: 面板应到过全高(实测峰值 ${maxDockH}, 落定 ${Math.round(after.panelH)})`)
        .toBeGreaterThanOrEqual(Math.round(after.panelH) - 4);

      // 断言(修复前后都必须绿 —— 判据收紧只动触发界, 位移公式不动): 行确实被让位, 且终值落在
      // 公式落点 vBot - 8 = 面板顶 - 16(呼吸距 8 + 落点裕量 8)。
      expect(after.rowB - base.rowB,
        `真覆盖行必须被让位(行底 ${base.rowB.toFixed(1)} -> ${after.rowB.toFixed(1)}; scrollBy ${JSON.stringify(run.sb)})`)
        .toBeLessThan(0);
      expect(Math.abs(after.rowB - (after.panelTop - 16)),
        `让位终值应落在公式落点 vBot - 8 = 面板顶 - 16(实测 ${after.rowB.toFixed(1)} vs ${(after.panelTop - 16).toFixed(1)})`)
        .toBeLessThanOrEqual(2);

      // ---- 探针2: 最浅被覆盖行, 贴触发界边界 ----
      // 关面板收场后, 把最深一个未覆盖行精确滚到面板顶 + 3(行底刚过新触发界 —— 面板分支补差
      // +8 后触发界 = 面板顶实缘, 覆盖 3px)。触发界若结构性过紧 >= 8px, 该行不再让位即当场红;
      // 正确判据下它必须仍被让位到公式终值(旧口径对真覆盖行无差别让位, 修复前后都绿)。
      await page.click('.drawer-dock .drawer-close');
      await waitDockCollapsed(page);
      const shallowHash = await page.evaluate((pt) => {
        let best = null;
        for (const r of document.querySelectorAll('.torrent-row')) {
          const b = r.getBoundingClientRect();
          if (b.bottom <= pt && (!best || b.bottom > best.bottom)) {
            best = { hash: r.getAttribute('data-hash'), bottom: b.bottom };
          }
        }
        if (!best) return null;
        // 下滚把行往上搬(scrollY 增大 = 内容上移): 行底要从 best.bottom(<= 面板顶)移到
        // pt + 3(更下方), 滚动量 = 当前 - 目标(负 = 上滚, 行随内容下移进覆盖区)。
        window.scrollBy(0, Math.round(best.bottom - (pt + 3)));
        return best.hash;
      }, after.panelTop);
      expect(shallowHash, '前置: 收场后视口内应有未覆盖行可作边界探针').toBeTruthy();
      await waitListSettled(page);
      const base2 = await page.evaluate((h) => {
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { y: Math.round(window.scrollY), rowB: r.bottom };
      }, shallowHash);
      // 前置: 行底确实刚过触发界(面板顶 + 3 对齐, 取整/亚像素余量内; 且覆盖 <= 8px ——
      // 恰是「补差若误做成 +16 就不再让位」的判别区间)
      expect(base2.rowB, `前置: 边界探针行底 ${base2.rowB.toFixed(1)} 应刚过面板顶 ${after.panelTop.toFixed(1)}`)
        .toBeGreaterThan(after.panelTop + 1);
      expect(base2.rowB, `前置: 边界探针行底 ${base2.rowB.toFixed(1)} 覆盖应 <= 8px(浅覆盖判别区间)`)
        .toBeLessThanOrEqual(after.panelTop + 8);
      await installGeoSampler(page, shallowHash);
      await page.dblclick(`.torrent-row[data-hash="${shallowHash}"]`, { force: true, position: { x: 8, y: 8 } });
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      await waitDockSettled(page);
      const run2 = await stopGeoSampler(page);
      const after2 = await page.evaluate((h) => {
        const p = document.querySelector('.drawer-dock > .drawer').getBoundingClientRect();
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { panelTop: p.top, rowB: r.bottom };
      }, shallowHash);
      // 前置: 重开后面板几何与探针1一致(高度恒锁), 对齐目标才可信
      expect(Math.abs(after2.panelTop - after.panelTop), '前置: 重开面板顶应与探针1一致(高度恒锁)')
        .toBeLessThanOrEqual(1);
      // 断言(修复前后都必须绿): 浅覆盖行仍被让位到公式终值 —— 触发界边界行为与旧行为无差别
      expect(after2.rowB - base2.rowB,
        `边界探针行必须仍被让位(行底 ${base2.rowB.toFixed(1)} -> ${after2.rowB.toFixed(1)}; scrollBy ${JSON.stringify(run2.sb)})`)
        .toBeLessThan(0);
      expect(Math.abs(after2.rowB - (after2.panelTop - 16)),
        `边界探针让位终值应落在公式落点 vBot - 8 = 面板顶 - 16(实测 ${after2.rowB.toFixed(1)} vs ${(after2.panelTop - 16).toFixed(1)})`)
        .toBeLessThanOrEqual(2);
    });

    /* ==================== S-A flux 首开遮挡竞速(2026-11-13 用户报「种子先被面板遮挡、之后才上移」) ====================
     * 定因(取证报告 S-A): flux 独有形态 = 入场 translateY(100%) 300ms 整幅上滑(dialogs.css,
     * 令牌 --fx-dur-panel) x html.fx-glide { scroll-behavior: smooth }(fx-mount.css, 开门窗口内
     * 所有程序化滚动变平滑动画) x 四个滚动写入者互相重启(openTorrentDrawer 开场 / _drawerDone
     * 集合落定兑现 / drawerAfterEnterHook 补发 / state.js flux 开门落定回执重入) —— 每次新
     * scrollBy 取消上一个平滑滚动从中途重启, 合成 490ms+ 爬行; 抽屉 300ms 就升完了, 行还在
     * 半路 = 先被盖后探出。prism/atlas 无 fx-glide(瞬时传输), 同用例是对照组(应绿)。
     *
     * 确定性化: 默认高 42vh(378px)时是否被盖是竞速抛硬币; 拖高记忆 620px(addInitScript 注入
     * localStorage —— initialDrawerHeight 在应用 created 读一次, 必须先于应用 boot)加大行程,
     * 被盖窗口变宽, 竞速变确定性。滚动相位对齐: 距文档底 900px 停车(让位 scrollBy 余量足额,
     * 开场那发不被文档底钳制 —— 文档底路径要等槽位长高才有余量, 是另一条时序), 挑行底落在
     * (全开顶缘 + 60, 全开顶缘 + 550] 的真覆盖行(覆盖深 60~550px —— 红验迭代中从 400 放宽,
     * 缘由: 400 档红验红在断言2(同步滞后), 断言1 未红 —— 面板顶扫过行底与平滑爬行追平几乎
     * 同时; 加深覆盖把被盖窗口拉宽, 550 档红验仍落断言2(爬行尾部+回执修正 ~180ms), 两档结论
     * 一致; 550 上限保证开场让位 Δ <= 566 < 900 停车余量, 开场那发不被文档底钳制)。
     *
     * 断言口径(全部位移量/时间差, 无绝对像素阈值; R6 不放宽):
     * 1. 开门全程(面板在场每一帧)选中行行底不越过面板顶实缘(行底 - 面板顶 <= 1px 取整噪声)。
     *    注: 任务书原文写「rect.bottom >= 面板 top」—— 视口坐标 y 越小越靠上, 「不被遮」的
     *    几何语义是行底 <= 面板顶, 按几何语义落地(任务书不等号方向与坐标语义相反, 属笔误)。
     * 2. 滚动落定不晚于面板升完(允许 ~3 帧余量 50ms): 最后一次 scrollY 变化帧时间 <= 面板顶
     *    首次到达终值帧时间 + 50ms —— 同步感判据(修复前平滑爬行 490ms+ 越过面板升起完成时刻)。
     */
    test(`S-A 首开遮挡: 开门全程选中行不被面板遮 + 滚动落定不晚于面板升完 @fast (${skin})`, async ({ page }) => {
      test.setTimeout(90_000);
      collectRuntimeErrors(page);

      // 620px 拖拽高度记忆: 应用 boot 前注入 localStorage(W3 高度记忆跨会话生效的既有键)
      await page.addInitScript(() => {
        try { localStorage.setItem('autoqb.ui.drawerHeight', '620'); } catch { /* 隐私模式等: 用例走默认高, 前置会拦 */ }
      });
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 距文档底 900px 停车(开场让位 scrollBy 的下滚余量足额, 不被文档底钳制)
      await page.evaluate(() => {
        window.scrollTo(0, document.documentElement.scrollHeight - window.innerHeight - 900);
      });
      await waitListSettled(page);
      const panelTopEst = await page.evaluate(() => {
        const sb = document.querySelector('.statusbar');
        const sbTop = sb ? sb.getBoundingClientRect().top : window.innerHeight;
        return sbTop - 620;  // 620px 拖高记忆的全开顶缘估算(同 W1 的 42vh 式, 高度换 620)
      });
      // 挑真覆盖行: 行底在 (顶缘估算 + 60, 顶缘估算 + 550] 内取最深一行(覆盖深 60~550px:
      // 覆盖越深面板顶越早扫过行底、平滑爬行追平越晚 = 遮挡窗口越宽越确定; 550 上限保证开场
      // 让位 Δ <= 566 < 900 停车余量, 不被文档底钳制); 中心须在状态栏上缘之上才可点(与
      // pickCoveredRow 同约束)。
      const cov = await page.evaluate((pt) => {
        const sb = document.querySelector('.statusbar');
        const sbTop = sb ? sb.getBoundingClientRect().top : window.innerHeight;
        let best = null;
        for (const r of document.querySelectorAll('.torrent-row')) {
          const b = r.getBoundingClientRect();
          if (b.bottom > pt + 60 && b.bottom <= pt + 550 && (b.top + b.bottom) / 2 < sbTop - 8
              && (!best || b.bottom > best.bottom)) {
            best = { hash: r.getAttribute('data-hash'), top: Math.round(b.top), bottom: Math.round(b.bottom) };
          }
        }
        return best;
      }, panelTopEst);
      expect(cov, `前置: 视口内应有覆盖深 60~550px 的真覆盖行(620px 全开顶缘估算 ${panelTopEst})`).toBeTruthy();
      expect(cov.bottom, `前置: 选中行应真被 620px 面板覆盖(行底 ${cov.bottom} > 顶缘估算 ${panelTopEst})`)
        .toBeGreaterThan(panelTopEst + 8);

      // 基线预读 -> 采样 -> 双击开面板(首开, 此前面板从未打开过) -> 条件等待落定
      const baseline = await page.evaluate((h) => {
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { y: Math.round(window.scrollY), rowB: Math.round(r.bottom) };
      }, cov.hash);
      await installGeoSampler(page, cov.hash);
      await page.dblclick(`.torrent-row[data-hash="${cov.hash}"]`, { force: true, position: { x: 8, y: 8 } });
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      await waitDockSettled(page);
      const { frames, sb: scrollLog } = await stopGeoSampler(page);
      expect(frames.length, '前置: 采样应有足够帧数').toBeGreaterThan(10);

      // 前置: 面板到过 620px 全高且顶缘到位(高度记忆生效的判据; 峰值对估算给 4px 取整余量)
      const openedFrames = frames.filter((f) => f.open && f.panelTop != null);
      expect(openedFrames.length, '前置: 采样应覆盖到开门动画期(面板在场)').toBeGreaterThan(5);
      const maxDockH = Math.max(...frames.filter((f) => f.open).map((f) => f.dockH ?? 0));
      expect(maxDockH, `前置: 面板应到过 620px 全高(实测峰值 ${maxDockH} —— 高度记忆未生效或入场被截断)`).toBeGreaterThanOrEqual(616);
      const finalPanelTop = openedFrames[openedFrames.length - 1].panelTop;
      // 前置: 落定后行应已被让位到公式落点(面板顶 - 16) —— 真覆盖行按判据必须让位(S-C 反向
      // 守卫同口径); 本前置不成立说明挑行/几何漂了, 断言无效。
      const lastRowB = frames[frames.length - 1].rowB;
      expect(lastRowB - finalPanelTop,
        `前置: 落定后行底 ${lastRowB} 应已被让位到面板顶 ${finalPanelTop} - 16 公式落点(偏差 ${lastRowB - finalPanelTop - (-16)})`)
        .toBeLessThanOrEqual(-14);

      // 断言1(核心, 修复前红): 开门全程行底不越过面板顶实缘 —— 遮挡深度 = 行底 - 面板顶
      // (视口坐标, >0 = 行底被面板顶盖住)。1px = 行/面板矩形取整噪声, 非绝对像素判据。
      let worst = 0;
      let worstAt = 0;
      for (const f of openedFrames) {
        const d = f.rowB - f.panelTop;
        if (d > worst) { worst = d; worstAt = f.t; }
      }
      expect(worst,
        `开门全程最大遮挡深度(行底-面板顶, 实测峰值 ${worst}px @${worstAt}ms; 时序 ${pairDigest(openedFrames, 'rowB', 'panelTop')}; scrollBy 登记 ${JSON.stringify(scrollLog)})`)
        .toBeLessThanOrEqual(1);

      // 断言2(修复前红): 滚动落定不晚于面板升完(允许 3 帧余量 50ms) —— 同步感。
      const panelDoneT = (openedFrames.find((f) => f.panelTop <= finalPanelTop + 1)
        ?? openedFrames[openedFrames.length - 1]).t;
      let lastScrollT = -1;
      for (let i = 1; i < frames.length; i++) if (frames[i].y !== frames[i - 1].y) lastScrollT = frames[i].t;
      expect(lastScrollT,
        `最后一次 scrollY 变化帧(${lastScrollT}ms)不得晚于面板顶首次到终值帧(${panelDoneT}ms)+50ms —— 滚动与抽屉上升的同步感(修复前平滑爬行越过面板升起完成时刻; 开门时序 rowB基线=${baseline.rowB} ${pairDigest(openedFrames, 'rowB', 'panelTop')}; scrollBy 登记 ${JSON.stringify(scrollLog)})`)
        .toBeLessThanOrEqual(panelDoneT + 50);
    });
  });
}
