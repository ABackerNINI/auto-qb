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
 *
 * T6 边距生命周期(2026-11-13 缺陷甲+乙, 用户拍板本轮修掉): drawerEnterHook 起拍两行
 * height=0/marginTop=0 使文档在 enter 起拍帧缩短 8px(呼吸距被 JS 清零)—— 关闭态贴文档底
 * (gap<8)时 scrollY 被钳 (8-gap) px, 全部行视口下移, 行底 (面板顶-(8-gap), 面板顶] 的未覆盖行
 * 被推进触发带, writer #1(_kbRevealRow)误发 reveal。Chromium 在文档长回同帧恢复 scrollY(钳制窗
 * 密闭, 误发恒落 0, 净 0)—— Gecko 无此恢复, 钳制永久, writer #2(~30ms 后, 余量充足)判据仍真、
 * 全额落地 -> 未覆盖行被拉到面板顶-16, 净上移 8~16px(Firefox 真机 20/20 确定性复现)。缺陷乙:
 * leave 末帧 marginTop=0 + afterLeave 缴回 CSS 8px 无滚动补偿 -> 文档两段式变化(->0 再 ->8), 贴
 * 文档底时闭合稳态 scrollY 比关闭前低 8px, 行位随之低 8px —— W1「重开零位移」基线取关闭后, 对它
 * 盲区。修复 = margin-top 生命周期整体退出 JS(dock.style.marginTop 全程零写入), 高度插值口径改为
 * 「槽位总占位 = margin(CSS 恒 8) + height」-> enter 全程文档单调不减、leave 全程单调降到关闭态
 * 总占位, 钳制在所有浏览器结构性消失。可观测面(Chromium): 甲的 scrollY 症状不可观测(同帧恢复),
 * 但 docH 的 -8 凹陷可观测(取证实测 19781->19773); 乙的 -8 残差落在行位上可观测。用例:
 * 6. T6 红验1: reopen 全程 docH >= 闭合态基线(修复前红: 起拍凹陷 -8)。
 * 7. T6 红验2: 两循环闭合稳态行位稳定(vs 开关循环前的闭合基线; 修复前红: 首轮关闭钳制 -8 残差,
 *    行位 +8; 修复前两循环之间因钳制落点饱和而相等 —— 残差是首轮一次性落地, 对「循环间比较」盲,
 *    故锚点取循环前的闭合基线)。
 * 8. T6 回归守卫: reopen 全程 scrollY 零位移(Chromium 修复前后恒绿 —— 修复前钳制窗密闭; 修复后
 *    结构性消失, 防回退), 不作红验。
 *
 * T7 上界(顶界)触发带收紧(2026-11-14 用户拍板「未被覆盖的行绝对不动」顶界方向): S-C 只收了下界,
 * flux 独有 writer #4(开门落定回执 -> _kbScrollRowIntoView)的上界分支旧触发界 rect.top < vTop + 4
 * 把「行顶距吸顶列头底实缘 0~4px」的未覆盖行也按公式下移(位移 ∈ (-9, -5], 探针实测 4~12px)。
 * 修复 = 补差单点 _kbViewTopPad(吸顶列头分支 -1 补偿 vTop 内建 +1(列头吸顶落位 top =
 * calc(--head-h - 1px) 防透缝)回到列头底实缘; 列头不在/未吸顶 +0 精确边), 位移公式不动。用例
 * (flux 专属 —— writer #4 只在 flux 挂, prism/atlas 开门路径无上界触发面, 键盘跟随面归
 * kbd-scroll-band.spec.mjs):
 * 9. T7 顶界带: 列头下 2px 未覆盖行开门(writer#4 重入)全程行顶/scrollY 零位移; 修复前预期红
 *    (实测被下移 ~7px)。
 * 10. T7 反向守卫: 真被列头遮住的行(覆盖 10px)走门仍让位到公式终值 vTop + 8 = 列头底 + 9
 *     (修复前后都必须绿)。
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

/** 闭合收尾完成等待: 面板节点出 DOM(leave 过渡终了 Vue 摘除, afterLeave 钩子同任务已跑完)。
 *  T6 闭合稳态基线(docH/行位)必须在它之后读 —— waitDockCollapsed 只等到收场末帧, 比 afterLeave
 *  早 ~60ms, 边距恢复(旧口径)发生在那段间隙里, 在那里读会把两段式文档的中间态当闭合基线。 */
async function waitDrawerGone(page) {
  await page.waitForFunction(
    () => !document.querySelector('.drawer-dock > .drawer'),
    undefined, { timeout: 5_000, polling: 30 },
  );
}

/** T6 文档底(gap 0)挑未被覆盖的参照行: 滚到文档底 -> 落定 -> 按全开顶缘估算挑最深未覆盖行。
 *  参照行未覆盖: 开/关全程无让位滚动, scrollY 的任何变化只可能来自文档高变化的钳制 ——
 *  判据对「边距生命周期」纯净。 */
async function pickRefAtBottom(page) {
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await waitListSettled(page);
  const panelTopEst = await page.evaluate(() => {
    const sb = document.querySelector('.statusbar');
    const sbTop = sb ? sb.getBoundingClientRect().top : window.innerHeight;
    return sbTop - Math.round(window.innerHeight * 0.42); // 全开顶缘估算: 状态栏顶 - 42vh(W1 同式)
  });
  const ref = await pickUncoveredRow(page, panelTopEst);
  expect(ref, `前置: 文档底视口内应有未被抽屉覆盖的行(全开顶缘估算 ${panelTopEst})`).toBeTruthy();
  return ref;
}

/** T6 闭合稳态读数: { y, rowB, docH }(参照行行底视口坐标 + scrollY + 文档高)。 */
async function measureClosed(page, hash) {
  return page.evaluate((h) => {
    const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
    return { y: Math.round(window.scrollY), rowB: Math.round(r.bottom), docH: document.documentElement.scrollHeight };
  }, hash);
}

/** T6 开面板(双击参照行; position 左缘 {x:8,y:8}: 行宽超出视口, 中心点会命中溢出的行外元素 ——
 *  smoke.md, 既有用例同口径)。 */
async function openRefDrawer(page, hash) {
  await page.dblclick(`.torrent-row[data-hash="${hash}"]`, { force: true, position: { x: 8, y: 8 } });
  await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
}

/** T6 关面板并等闭合收尾完成(面板出 DOM = afterLeave 已跑完)。 */
async function closeRefDrawer(page) {
  await page.click('.drawer-dock .drawer-close');
  await waitDrawerGone(page);
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
        rowT: rr ? Math.round(rr.top) : null,  // T7 上界(顶界)判据用: 行顶位移(下界用例只看 rowB, 加列无扰)
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

    /* ==================== T7 上界(顶界)触发带收紧(2026-11-14 用户拍板「未被覆盖的行绝对不动」顶界方向) ====================
     * 下界方向已由 S-C 收紧(触发界 = 界源实缘, _kbViewBottomPad 单点); 上界方向还有一处漏网:
     * flux 独有 writer #4(state.js drawerVisible -> AQB_FX_MOUNT.dock 落定回执 -> _kbScrollRowIntoView)
     * 重入时, 其上界分支(旧触发界 rect.top < vTop + 4, vTop = _kbViewTop = 顶栏 + 吸顶列头高)把
     * 「行顶距吸顶列头底实缘 0~4px」的**未覆盖**行也按公式下移(位移 = rect.top - vTop - 8 ∈
     * (-9, -5], 16 场景探针实测 4~12px)—— 行顶在列头之下 = 未被列头/面板覆盖, 按拍板语义必须
     * 零位移。修复(与 S-C 同法): 触发界收紧到界源实缘 —— 补差单点 _kbViewTopPad(吸顶列头分支
     * -1 补偿 vTop 内建 +1: 列头吸顶落位 top = calc(--head-h - 1px) 防透缝, 单点返回值 = 列头底
     * 实缘 + 1; 列头不在 DOM/未吸顶分支 +0 精确边, 界源 = 顶栏), 位移公式逐字不动, 真被列头
     * 遮住的行仍按公式让位到 vTop + 8。
     * 两用例 flux 专属: writer #4 只在 flux 挂(AQB_FX_MOUNT 仅 flux shell 注册), prism/atlas 无
     * 此写入者 = 开门路径无上界触发面(上界的键盘跟随面由 kbd-scroll-band.spec.mjs 覆盖)。
     */

    test(`T7 顶界带: 列头下 2px 未覆盖行开门落定回执重入全程零位移 @fast (${skin})`, async ({ page }) => {
      test.skip(skin !== 'flux', 'writer#4(开门落定回执重入)flux 独有; 其余皮肤无此写入者');
      test.setTimeout(90_000);
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 先深滚进列表中部(列头吸顶恒成立 —— 吸顶前滚动连列头一起搬, 行顶-列头底相对量不动,
      // 对齐无从谈起; 首轮红验实证: 不深滚对齐残差 17px), 再挑视口中部一个行顶在列头底 40px
      // 以下的行, scrollBy 精确送到列头底实缘 + 2(未覆盖: 行顶在列头之下; 且在旧触发带内 ——
      // vTop = 列头底实缘 + 1, 行顶 = 列头底 + 2 即 vTop + 1 < vTop + 4, 旧判据必触发; 修复后
      // 判据 = 列头底实缘, 不触发)。+2 档对亚像素安全: Math.round 对齐误差 ±0.5px 内, 既不会
      // 把行顶推到列头之上(误成真覆盖), 也不会推出 vTop + 4(红验不红)。
      // 滚动量 = 当前 - 目标(下滚把行往上搬, S-C 同式)。
      await page.evaluate(() => window.scrollTo(0, Math.round(document.documentElement.scrollHeight / 2)));
      await waitListSettled(page);
      const aligned = await page.evaluate(() => {
        const hb = document.querySelector('.group-head').getBoundingClientRect().bottom;
        let best = null;
        for (const r of document.querySelectorAll('.torrent-row')) {
          const b = r.getBoundingClientRect();
          if (b.top > hb + 40 && b.bottom < window.innerHeight - 40) {
            best = { hash: r.getAttribute('data-hash'), top: b.top };
            break;
          }
        }
        if (!best) return null;
        window.scrollBy(0, Math.round(best.top - (hb + 2)));
        return best.hash;
      });
      expect(aligned, '前置: 视口内应有行顶在列头底 40px 以下的行(带对齐原料)').toBeTruthy();
      await waitListSettled(page);

      const band = await page.evaluate((h) => {
        const head = document.querySelector('.group-head');
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { y: Math.round(window.scrollY), rowT: r.top, hb: head.getBoundingClientRect().bottom };
      }, aligned);
      // 前置: 行顶确实落在列头底实缘之下 0~4px(未被列头覆盖 + 旧触发带内 —— 对列头底**实值**判)
      expect(band.rowT - band.hb, `前置: 对齐后行顶 - 列头底 = ${(band.rowT - band.hb).toFixed(1)} 应在 (0, 4] 内(未覆盖且旧判据必触发)`)
        .toBeGreaterThan(0);
      expect(band.rowT - band.hb, `前置: 对齐后行顶 - 列头底 = ${(band.rowT - band.hb).toFixed(1)} 应 <= 4(旧触发带内)`)
        .toBeLessThanOrEqual(4);

      await installGeoSampler(page, aligned);
      await page.dblclick(`.torrent-row[data-hash="${aligned}"]`, { force: true, position: { x: 8, y: 8 } });
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      // writer#4 在面板入场落定回执(transitionend + 宏任务)后 ~10ms 发 —— 不加 waitForTimeout
      // (flaky 守阵禁新增): waitDockSettled 的判稳对要求 dock 高 + scrollY 连续两拍(拍距 250ms)
      // 全等, 而 writer#4 恒在高度收敛后 ~15ms 内发且其位移必打破 scrollY 全等 —— 判稳对在
      // writer#4 之前结构上不可能凑齐, 落定返回时回执重入必已被采样覆盖。
      await waitDockSettled(page);
      const run = await stopGeoSampler(page);

      // 断言(修复后绿, 修复前红: writer#4 上界分支把行下移 ~7px): 全程行顶与 scrollY 零位移。
      const dt = run.frames.map((f) => (f.rowT ?? band.rowT) - band.rowT);
      const dy = run.frames.map((f) => f.y - band.y);
      expect(Math.max(...dy.map(Math.abs)),
        `开门全程 scrollY 位移量(基线 ${band.y}; 序列 ${frameDigest(run.frames)}; scrollBy 登记 ${JSON.stringify(run.sb)})`)
        .toBe(0);
      expect(Math.max(...dt.map(Math.abs)),
        `开门全程行顶位移量(基线 ${band.rowT.toFixed(1)}; scrollBy ${JSON.stringify(run.sb)})`)
        .toBeLessThanOrEqual(1);
    });

    test(`T7 反向守卫: 真被吸顶列头遮住的行走门仍让位到上界公式终值 vTop + 8 @fast (${skin})`, async ({ page }) => {
      test.skip(skin !== 'flux', 'writer#4(开门落定回执重入)flux 独有; 其余皮肤无此写入者');
      test.setTimeout(90_000);
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 对齐: 先深滚进列表中部(列头吸顶恒成立, 缘由同上例), 再把行顶送到列头底实缘 - 10(真被
      // 列头遮 10px)。点击点必须落在列头之下(行顶被盖, y=8 会点在列头上被 z-index 拦截), 按行高
      // 取行下半部一个安全偏移: 点视口 y = 行顶 + clickY > 列头底 且仍在行盒内(clickY <= 行高 - 8)。
      await page.evaluate(() => window.scrollTo(0, Math.round(document.documentElement.scrollHeight / 2)));
      await waitListSettled(page);
      const aligned = await page.evaluate(() => {
        const hb = document.querySelector('.group-head').getBoundingClientRect().bottom;
        let best = null;
        for (const r of document.querySelectorAll('.torrent-row')) {
          const b = r.getBoundingClientRect();
          if (b.top > hb + 40 && b.bottom < window.innerHeight - 40) {
            best = { hash: r.getAttribute('data-hash'), top: b.top, h: b.height };
            break;
          }
        }
        if (!best) return null;
        window.scrollBy(0, Math.round(best.top - (hb - 10)));
        return { hash: best.hash, clickY: Math.max(12, Math.min(Math.round(best.h) - 8, 30)) };
      });
      expect(aligned, '前置: 视口内应有行顶在列头底 40px 以下的行(带对齐原料)').toBeTruthy();
      await waitListSettled(page);

      const base = await page.evaluate((h) => {
        const head = document.querySelector('.group-head');
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { y: Math.round(window.scrollY), rowT: r.top, hb: head.getBoundingClientRect().bottom };
      }, aligned.hash);
      // 前置: 行顶真被列头盖住(覆盖 >= 4px 裕量 —— 贴 1px 边的行属触发界边界探针域, 不混入本守卫)
      expect(base.hb - base.rowT, `前置: 对齐后行顶 ${base.rowT.toFixed(1)} 应真被列头盖住(列头底 ${base.hb.toFixed(1)}, 覆盖 >= 4px)`)
        .toBeGreaterThanOrEqual(4);

      await installGeoSampler(page, aligned.hash);
      await page.dblclick(`.torrent-row[data-hash="${aligned.hash}"]`, { force: true, position: { x: 8, y: aligned.clickY } });
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      await waitDockSettled(page);  // writer#4 覆盖性: 判稳对结构上不可能早于回执重入(上例注)
      const run = await stopGeoSampler(page);
      const after = await page.evaluate((h) => {
        const head = document.querySelector('.group-head');
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { rowT: r.top, hb: head.getBoundingClientRect().bottom };
      }, aligned.hash);

      // 断言(修复前后都必须绿 —— 判据收紧只动触发界, 位移公式不动): 行被下移让位, 终值落在
      // 公式落点 vTop + 8 = 列头底实缘 + 9(vTop = 列头底 + 1 内建偏移)。
      expect(after.rowT - base.rowT,
        `真覆盖行必须被让位(行顶 ${base.rowT.toFixed(1)} -> ${after.rowT.toFixed(1)}; scrollBy ${JSON.stringify(run.sb)})`)
        .toBeGreaterThan(0);
      expect(Math.abs(after.rowT - (after.hb + 9)),
        `让位终值应落在公式落点 vTop + 8 = 列头底 + 9(实测 ${after.rowT.toFixed(1)} vs ${(after.hb + 9).toFixed(1)})`)
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
      // T8(2026-11-14)起根滚动器禁锚(html overflow-anchor: none): settle 期窗口化 pad 重算的
      // 文档高变化不再被浏览器锚补隐性补偿(一段式停车实测余量被 pad 重算吃成 0, 开场让位被钳,
      // 面板上升先于行上移 = S-A 症状在对照皮肤复发) —— 停车改两段式: 落定后按**落定文档高**
      // 再停一次, 余量对锚补开关不依赖(T8 前后都必须 >= 让位上限 566)。
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

    /* ==================== T6 边距生命周期(缺陷甲+乙, 2026-11-13 用户拍板本轮修掉) ====================
     * 红验两用例(修复前红 / 修复后绿) + 一条回归守卫(修复前后都绿, 不作红验)。判据全部位移量/差值,
     * 无绝对像素阈值; 场景恒为文档底(gap 0) + 未覆盖参照行(开/关全程无让位滚动, scrollY 的任何
     * 变化只可能来自文档高变化的钳制)。 */

    test(`T6 红验1: reopen 全程 docH >= 闭合态基线(enter 起拍清边距凹陷 -8) @fast (${skin})`, async ({ page }) => {
      test.setTimeout(90_000);
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      const ref = await pickRefAtBottom(page);
      await openRefDrawer(page, ref.hash);
      await waitDockSettled(page);
      await closeRefDrawer(page);
      const closed = await measureClosed(page, ref.hash);

      // reopen 全程 rAF 采样: 起拍帧的 docH 是判据 —— 采样器 tick 先于追赶循环首帧注册,
      // 必然读到处在起拍态的文档高(修复前 = 基线 - 8: 起拍清边距把文档压短 8px, 取证实测
      // 19781->19773; 修复后起拍只压 height, 总占位 = margin(CSS 恒 8) + 0 = 关闭态, 文档零变化)。
      await installGeoSampler(page, ref.hash);
      await openRefDrawer(page, ref.hash);
      await waitDockSettled(page);
      const { frames } = await stopGeoSampler(page);
      expect(frames.length, '前置: 采样应有足够帧数').toBeGreaterThan(10);
      const openedH = await page.evaluate(() => Math.round(document.querySelector('.drawer-dock').getBoundingClientRect().height));
      const maxDockH = Math.max(...frames.filter((f) => f.open).map((f) => f.dockH ?? 0));
      expect(maxDockH, `前置: reopen 后面板应到过全高(实测峰值 ${maxDockH}, 落定 ${openedH})`).toBeGreaterThanOrEqual(openedH - 4);

      const minDocH = Math.min(...frames.map((f) => f.docH));
      expect(minDocH,
        `reopen 全程 docH 最小值(实测 ${minDocH})不得低于闭合态基线 ${closed.docH} —— enter 起拍清边距使文档凹陷 -8px` +
        `(修复前实测 ${closed.docH - 8}; docH/dockH 序列 ${pairDigest(frames, 'docH', 'dockH')})`)
        .toBeGreaterThanOrEqual(closed.docH);
    });

    test(`T6 红验2: 两循环闭合稳态行位稳定(边距两段式 -8 残差) @fast (${skin})`, async ({ page }) => {
      test.setTimeout(120_000);
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 开关循环前的闭合基线(锚点): 贴文档底、面板从未开过
      const ref = await pickRefAtBottom(page);
      const pristine = await measureClosed(page, ref.hash);

      // 两个完整开关循环(同一未覆盖行), 各轮闭合收尾完成(面板出 DOM)后测闭合稳态
      await openRefDrawer(page, ref.hash);
      await waitDockSettled(page);
      await closeRefDrawer(page);
      const closed1 = await measureClosed(page, ref.hash);
      await openRefDrawer(page, ref.hash);
      await waitDockSettled(page);
      await closeRefDrawer(page);
      const closed2 = await measureClosed(page, ref.hash);

      // 断言(修复后应绿, 修复前红): 闭合稳态行底与循环前闭合基线差 <=1px(取整噪声)。修复前红:
      // 贴文档底(gap 0)关闭, 末帧清边距使文档比闭合稳态多缩 8px -> scrollY 被多钳 8, 闭合稳态
      // 行位比基线低 8px(afterLeave 缴回 8 只还文档高不还 scrollY —— 残差留在行位上, 首轮一次性
      // 落地; 两循环之间因钳制落点饱和而相等, 故锚点必须取循环前基线, 循环间比较对首轮残差盲)。
      const db1 = closed1.rowB - pristine.rowB;
      const db2 = closed2.rowB - pristine.rowB;
      expect(Math.abs(db1),
        `循环1 闭合稳态行底位移量(基线 ${pristine.rowB} -> ${closed1.rowB}, 实测 ${db1}; y ${pristine.y}->${closed1.y}, ` +
        `docH ${pristine.docH}->${closed1.docH}) —— 闭合收尾不得挪动未覆盖行位(边距两段式 ->0 再 ->8 的钳制落点残差)`)
        .toBeLessThanOrEqual(1);
      expect(Math.abs(db2),
        `循环2 闭合稳态行底位移量(基线 ${pristine.rowB} -> ${closed2.rowB}, 实测 ${db2}; 循环1 后 ${closed1.rowB}; ` +
        `y ${closed1.y}->${closed2.y}, docH ${closed1.docH}->${closed2.docH})`)
        .toBeLessThanOrEqual(1);
    });

    test(`T6 回归守卫: reopen 全程 scrollY 零位移(Chromium 修复前后恒绿, 防回退) @fast (${skin})`, async ({ page }) => {
      test.setTimeout(90_000);
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      const ref = await pickRefAtBottom(page);
      await openRefDrawer(page, ref.hash);
      await waitDockSettled(page);
      await closeRefDrawer(page);
      const baseline = await measureClosed(page, ref.hash);

      // 基线显式预读后采样 reopen 全程: 修复前 Chromium 起拍钳制窗密闭(同帧恢复, 误发恒落 0)
      // 恒绿; Gecko 的钳制在 e2e(Chromium)不可观测, 由边距退出 JS 的结构性修复消除 —— 本用例
      // 只防回退, 不作红验(与 W1 再开零位移同谱系, 参照行换未覆盖行 + 场景钉死文档底)。
      await installGeoSampler(page, ref.hash);
      await openRefDrawer(page, ref.hash);
      await waitDockSettled(page);
      const { frames, sb } = await stopGeoSampler(page);
      expect(frames.length, '前置: 采样应有足够帧数').toBeGreaterThan(10);
      const openedH = await page.evaluate(() => Math.round(document.querySelector('.drawer-dock').getBoundingClientRect().height));
      const maxDockH = Math.max(...frames.filter((f) => f.open).map((f) => f.dockH ?? 0));
      expect(maxDockH, `前置: reopen 后面板应到过全高(实测峰值 ${maxDockH}, 落定 ${openedH})`).toBeGreaterThanOrEqual(openedH - 4);

      const dy = frames.map((f) => f.y - baseline.y);
      const db = frames.map((f) => (f.rowB ?? baseline.rowB) - baseline.rowB);
      expect(Math.max(...dy.map(Math.abs)),
        `reopen 全程 scrollY 位移量(基线 ${baseline.y}; 序列 ${frameDigest(frames)}; scrollBy 登记 ${JSON.stringify(sb)})`)
        .toBe(0);
      expect(Math.max(...db.map(Math.abs)),
        `reopen 全程参照行 rect.bottom 位移量(基线 ${baseline.rowB}; scrollBy ${JSON.stringify(sb)})`)
        .toBeLessThanOrEqual(1); // 1px = 行矩形取整噪声(W1 同口径), 非绝对像素判据
    });

    /* ==================== T8 根滚动器 CSS scroll anchoring(2026-11-14 用户真机 BUG) ====================
     * 定因(只读取证 + 本任务红验探针复现): 文档底贴满(scrollY == maxScroll)时点行开抽屉, 停靠
     * 槽位(.drawer-dock, 流内 sticky)enter 逐帧生长被 Chromium 根滚动器的 CSS scroll anchoring
     * 锚补 —— scrollY 无 JS 调用地同帧自动 +dock 首帧生长(真机取证 +286 = 42vh x 首帧缓动 0.45;
     * 本环境 1440x900 实测 +12~+287(量级随时序浮动, 恒非零), 选中行被推出视口顶, 上界分支拉回后仍净上移。
     * 复现的**必要条件是缩放 != 100%**(用户真机条件): zoom=1 的整数布局下锚补恒不触发(红验
     * 探针 ~200 次零复现, 如实口径), html 设 zoom 0.9(分数布局)后 prism/atlas 100% 确定性复现。
     * 流程次序钉死: 先贴底(整型布局下窗口化渲染窗落位) -> 再应用 zoom -> 再贴底(zoom 改变
     * 文档总高, 必须重贴 + 重落定) —— 这个次序下修复前后视口内都有可点行(先 zoom 后贴底的
     * 次序在修复后窗口化平衡态翻转, 视口内无行, 前置不可构造 —— 计划外发现, 见任务报告)。
     * 指纹三件套: scrollY 跳变 == dock 同帧生长量、window.scrollBy 登记空表(零 JS 滚动)、
     * 逐帧采样捕获 —— 三者齐备才能单独指认浏览器锚补。
     * 修复 = 四皮肤 dialogs.css 的 .drawer-dock 定义同段加 html { overflow-anchor: none; }(根
     * 滚动器禁锚) —— 项目几何全部自管(reveal/让位/T6 续缴/T7 上界都是显式滚动管理), 锚补只与
     * 之互相干扰, 与「滚动位宁可不动也不猜」同口径。方案矩阵: .drawer-dock 子树禁锚无效是规范
     * 语义本身(锚点候选在子树外、sticky 即 excluded subtree), 故取 html 根级。
     * 继承语义: overflow-anchor 不可继承(computed 实测内层滚动器仍 auto), 规范明文后代滚动盒
     * 自行恢复自身锚定 —— html 根级禁锚只禁根滚动器, 内层滚动器 CSS 锚定不受影响; 抽屉内层的
     * 滚动稳定另由 JS 自管(anchFill 锚保活 = 锚元素身份保持, 非 CSS scroll anchoring; 窗口化
     * 显式 scrollTop), e2e dt-live-update #8/#9 族钉该面不受波及(修复后复验 14/14)。
     * flux 已解跳(2026-11-14, issue 26-11-14-0844 修): flux 的行窗口化在 zoom != 1 下窗口错位
     * —— 全部渲染行落在视口上方(底 pad 独占视口), 前置不可构造; 已入池并修(columns_grid.js
     * _rowWindow pad 按有效缩放 1/z 换算成布局 px, e2e/row-window-zoom.spec.mjs 钉该面), 本用例
     * flux 档回归。机制为浏览器级, prism/atlas 双皮肤此前已确证。
     */
    test(`T8 根锚补: 缩放 0.9 + 文档底首开抽屉全程行视口位置零位移 @fast (${skin})`, async ({ page }) => {
      test.setTimeout(90_000);
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 步骤1: 先贴底(整型布局下窗口化渲染窗落位) -> 应用用户真实缩放条件(zoom 0.9 = 分数
      // 布局) -> zoom 后先按新布局落定一次, 再重新贴底 + 落定(zoom 改变文档总高, scrollY 必须
      // 重新钳到新 maxScroll)。次序依据见上方 T8 节注释 —— 先 zoom 后贴底的次序在修复后无可点行
      // (窗口化平衡态翻转)。
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await waitListSettled(page);
      await page.evaluate(() => { document.documentElement.style.zoom = '0.9'; });
      await waitListSettled(page);
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await waitListSettled(page);

      // 步骤2: 邻近行 = 行底距全开顶缘估算 >= 200px 的最深一行(余量充足 —— 让位三发与 flux 回执
      // 重入的判据对它一律不触发, 打开全程的 scrollY 变化只可能来自浏览器, 判据纯净; zoom 0.9
      // 下真实面板比 42vh 估算矮, 该约束对真实几何只严不松)。
      const near = await page.evaluate(() => {
        const sb = document.querySelector('.statusbar');
        const sbTop = sb ? sb.getBoundingClientRect().top : window.innerHeight;
        const pt = sbTop - Math.round(window.innerHeight * 0.42);
        let best = null;
        for (const r of document.querySelectorAll('.torrent-row')) {
          const b = r.getBoundingClientRect();
          if (b.bottom <= pt - 200 && b.top > 4
              && (b.top + b.bottom) / 2 < sbTop - 8 && (!best || b.bottom > best.bottom)) {
            best = { hash: r.getAttribute('data-hash'), top: Math.round(b.top), bottom: Math.round(b.bottom) };
          }
        }
        return best;
      });
      expect(near, '前置: 文档底视口内应有行底距全开顶缘 >= 200px 的可点行(邻近行选行原料)').toBeTruthy();

      // 步骤3: 基线显式预读 -> 采样 -> 开抽屉 -> 落定。zoom 改变点击坐标语义, 用 JS 派发 dblclick
      // (Vue @dblclick 响应; Playwright 定位点击在 zoom 下会撞上窗口化换帧的元素 detach)。
      const baseline = await page.evaluate((h) => {
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { y: Math.round(window.scrollY), rowT: Math.round(r.top), rowB: Math.round(r.bottom) };
      }, near.hash);
      await installGeoSampler(page, near.hash);
      await page.evaluate((h) => {
        const el = document.querySelector(`.torrent-row[data-hash="${h}"]`);
        for (const type of ['click', 'click', 'dblclick']) {
          el.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window,
            clientX: 20, clientY: el.getBoundingClientRect().top + 10 }));
        }
      }, near.hash);
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      await waitDockSettled(page);
      const { frames, sb } = await stopGeoSampler(page);
      expect(frames.length, '前置: 采样应有足够帧数').toBeGreaterThan(10);

      // 前置: 打开确实发生且面板到过全高; 让位链对该行全程未触发(scrollBy 空表 = 零 JS 滚动 ——
      // 位移只能来自浏览器, 这正是本判据能单独指认锚补的前提)。
      const openedFrames = frames.filter((f) => f.open);
      expect(openedFrames.length, '前置: 采样应覆盖到打开的动画期').toBeGreaterThan(0);
      const openedH = await page.evaluate(() => Math.round(document.querySelector('.drawer-dock').getBoundingClientRect().height));
      const maxDockH = Math.max(...openedFrames.map((f) => f.dockH ?? 0));
      expect(maxDockH, `前置: 打开后面板应到过全高(实测峰值 ${maxDockH}, 落定 ${openedH})`)
        .toBeGreaterThanOrEqual(openedH - 4);
      expect(sb.length, `前置: 全程不得有 JS 滚动(scrollBy 登记 ${JSON.stringify(sb)})`).toBe(0);

      // 断言(修复后绿, 修复前红: 根滚动器锚补使 scrollY 无 JS 调用地同帧 +dock 首帧生长, 行被
      // 推出视口顶): 全程 scrollY 与行 rect.top/rect.bottom 零位移(1px = 行矩形取整噪声)。
      const dy = frames.map((f) => f.y - baseline.y);
      const dt = frames.map((f) => (f.rowT ?? baseline.rowT) - baseline.rowT);
      const db = frames.map((f) => (f.rowB ?? baseline.rowB) - baseline.rowB);
      expect(Math.max(...dy.map(Math.abs)),
        `打开全程 scrollY 位移量(基线 ${baseline.y}; 序列 ${frameDigest(frames)}; scrollBy 登记 ${JSON.stringify(sb)})`)
        .toBe(0);
      expect(Math.max(...dt.map(Math.abs)),
        `打开全程选中行 rect.top 位移量(基线 ${baseline.rowT}, 选行 ${JSON.stringify(near)}; 修复前锚补会把行推出视口顶)`)
        .toBeLessThanOrEqual(1);
      expect(Math.max(...db.map(Math.abs)),
        `打开全程选中行 rect.bottom 位移量(基线 ${baseline.rowB}, 选行 ${JSON.stringify(near)})`)
        .toBeLessThanOrEqual(1);
    });

    test(`T8 反向守卫: 最后种子(真覆盖行)让位链照常落到面板顶-16 @fast (${skin})`, async ({ page }) => {
      test.setTimeout(90_000);
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      // 用户路径步骤1单独钉: 文档底点最后的可点种子行(真覆盖行), 让位链(开场发 + 落定补发 +
      // T6 截断续缴)必须照常把行送到公式落点 vBot - 8 = 面板顶 - 16 —— 禁锚只摘浏览器的锚补,
      // 不碰 JS 让位链(修复前后都必须绿)。
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await waitListSettled(page);
      const panelTopEst = await page.evaluate(() => {
        const sb = document.querySelector('.statusbar');
        const sbTop = sb ? sb.getBoundingClientRect().top : window.innerHeight;
        return sbTop - Math.round(window.innerHeight * 0.42);
      });
      const cov = await pickCoveredRow(page, panelTopEst);
      expect(cov, `前置: 文档底视口内应有可点且被抽屉覆盖的行(全开顶缘估算 ${panelTopEst})`).toBeTruthy();
      await installGeoSampler(page, cov.hash);
      await page.dblclick(`.torrent-row[data-hash="${cov.hash}"]`, { force: true, position: { x: 8, y: 8 } });
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      await waitDockSettled(page);
      const { sb } = await stopGeoSampler(page);
      const after = await page.evaluate((h) => {
        const p = document.querySelector('.drawer-dock > .drawer').getBoundingClientRect();
        const r = document.querySelector(`[data-hash="${h}"]`).getBoundingClientRect();
        return { panelTop: p.top, panelH: p.height, rowB: r.bottom, y: Math.round(window.scrollY) };
      }, cov.hash);

      // 前置: 面板到过全高 + 让位链确实发起过(scrollBy 登记非空 —— 文档底打开首发改写被钳,
      // 调用本身仍发生; T6 续缴在槽位长高后补齐)
      expect(after.panelH, '前置: 面板应到过全高(42vh)').toBeGreaterThanOrEqual(
        await page.evaluate(() => Math.round(window.innerHeight * 0.42)) - 4);
      expect(sb.length, `前置: 让位链应发起过 scrollBy(登记 ${JSON.stringify(sb)})`).toBeGreaterThanOrEqual(1);

      // 断言(修复前后都必须绿): 行被让位到公式落点 vBot - 8 = 面板顶 - 16(S-C 反向守卫同口径)。
      expect(after.rowB - cov.bottom,
        `真覆盖行必须被让位(行底 ${cov.bottom} -> ${after.rowB.toFixed(1)}; scrollBy 登记 ${JSON.stringify(sb)})`)
        .toBeLessThan(0);
      expect(Math.abs(after.rowB - (after.panelTop - 16)),
        `让位终值应落在公式落点 vBot - 8 = 面板顶 - 16(实测 ${after.rowB.toFixed(1)} vs ${(after.panelTop - 16).toFixed(1)}; scrollBy ${JSON.stringify(sb)})`)
        .toBeLessThanOrEqual(2);
    });
  });
}
