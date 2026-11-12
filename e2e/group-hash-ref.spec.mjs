// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS, TORRENTS } from './harness.mjs';
import { requireMode } from './lib/mode.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst, withVm } from './lib/vm.mjs';
import { armClick, armPending } from './lib/probes.mjs';

/**
 * P-02 二期协议形状 e2e(联合计划 26-11-11-0630 §04 S4) —— S1 后端组行 hash 引用式 +
 * S2 前端 ingestion 物化接缝落定后的**线级形状钉与端到端缝面**, 四条用例各钉一个面:
 *
 *   1. 线级形状钉: 拦页面真实收到的 /api/state 响应(轮询轮全量 + delta 轮; test 4 另把 delta
 *      轮钉到暂停真值轮上), 断言每个组行 members 是**40 位 hash 字符串数组**(后端
 *      views_group._build_group_row 的 P-02 二期契约; 服务端单测/镜子守阵之外, 这里钉的是
 *      "真机线上到底发的什么形状")。覆盖面如实: 登录快照轮(auth.js bootstrap 的独立物化
 *      调用点)在本轨**不可达** —— e2e 桩恒免鉴权(ui_harness skip_local_verify, 无登录表单
 *      就没有 bootstrap), 该缝的覆盖落点 = 节点电池静态钉(poll_auth_lifecycle 电池钉
 *      「物化调用先于 this.groups 赋值」), 不在本 spec 声称。
 *      同时断言页面渲染正常: vm 侧组行 members 已被 S2 接缝全部物化回成员行对象
 *      (缺项防御会保留 hash 串 —— 桩数据恒可解析, 全 hash 串 = 物化破)。
 *   2. 明细渲染: 组行展开 -> 成员行渲染, data-hash 集合与**线级 hash 数组**逐一对上
 *      (wire hash 数组 -> DOM 成员行, 物化缝端到端); 成员行的 状态/进度/速度 文本与
 *      平铺面(vm.torrents = SEED_ITEM)经同一渲染管线(fmtSpeedOrDash/progPct/stateText)
 *      的期望值逐格一致; 平铺面 DOM 同格再对一遍(首组成员 = 种子页窗口顶部两行;
 *      前提收窄: 仅全库归组 wire.singles 空档才跑, 大库档 singles 占满窗口顶部, 见段注);
 *      vm 层加钉物化产物的浅拷贝不变式(组员行与平铺行是独立对象 —— 乐观链 prev 采集
 *      「同 hash 多命中各为独立对象」的前提, polling.js 物化注释的契约)。
 *   3. 筛选计数: 五筛选器族(状态/标签/分类/站点/路径, filters.js 文件头口径)在 hash
 *      引用式组行下计数正确 —— 期望值从**线级载荷**(request 直打 /api/state?view=group,
 *      与前端 ingestion 无关的独立数据面)现算:
 *        - 状态分布(distSegments) = **种子数口径**(逐成员 bump, 含 singles), 组/种子两视图同数;
 *        - 标签/分类/站点/路径 = 组视图按**组数**(_facetPick 组内去重后计数)、种子页按
 *          **种子数**两套口径分别比对; 路径的期望值复用 vm._pathPositions 同源谓词
 *          (位置集单点, plan 26-11-07-2344 R3 D17 —— spec 内不复刻它的实现, 只喂线级行);
 *        - 另以真实点击开标签筛选弹层, 钉 .pop-item 计数徽标的 DOM 渲染。
 *   4. 乐观补丁: 组内成员(明细行)右键暂停/恢复 —— 乐观 is-pending 即时出现(记录器口径,
 *      瞬时窗口) + 真值落地收敛(pendingOps 清账 + 行 kind 停在真值)。收敛判据里同时钉
 *      「增量轮整行 upsert 后组行 members 仍是物化对象形」: 暂停成员必使同代组行脏
 *      (runtime_views drain_delta 成员脏 ⇒ 组脏), delta 轮重组的新组行要再次经物化缝
 *      还原成员行 —— 这一步若破了, 该成员在明细表会退化成 hash 串(判据返回 null 恒红)。
 *
 * 模式门控: 1-3 是纯数据/渲染面(命令泵三形态下 /api/state 行为不变), 不加门控三模式全跑;
 * 4 的判据前提是**命令成功且真值真的变了**(桩 --cmd-result error/hang 下真值不动,
 * 8s 轮询必超时, smoke.md「某种模式下恒红」反例), 与 delta-sync.spec 同口径 requireMode 限 ok。
 *
 * D4 断言翻译守则(计划 26-10-06-0708 §3.5)评估:
 *   · 交互全部真实手势(展开点 .g-name / 右键成员行 / 菜单项点击 / 顶栏筛选按钮);
 *   · evaluate 保留处: 1) 「组行 hash -> 成员值」的期望值面要把线级行喂给 vm._pathPositions,
 *     该谓词只在页面里, 期望值必须页内现算(第2类读数, optimistic.spec「vm 内部行为没有
 *     DOM 之外的取径」同款理由); 2) 浅拷贝不变式的 === 比较必须页内做(结构化克隆出页面
 *     即失对象身份, delta-sync.spec S7 直测同款注释); 3) armPending/armClick 是 vm 时序
 *     探针(probes.mjs 既有口径); 4) DOM 批量读格文本走单次 evaluate(逐格 locator 读会
 *     各自带一次协议往返, 无语义差异)。
 *   · 「首组行 = 种子页窗口顶部两行」的对应关系来自**桩数据自己的排序事实**(added_on
 *     严格递增 + 组键按 i//2 配对 + 组级 added_on 取成员最大), 不是对前端排序实现的假设:
 *     用它免掉种子页 300 行窗口化下按 hash 找行的滚动循环, 期望值仍从线级载荷独立现算。
 */

/** 40 位小写十六进制 hash(P-02 二期组行 members 的元素契约)。 */
const HASH_RE = /^[0-9a-f]{40}$/;

/** 导航页签定位器(tpl/topbar.html `nav.tabs [data-view]`)。 */
const tab = (page, view) => page.locator(`nav.tabs [data-view="${view}"]`);
/** 菜单项定位器(按注册表 id, 模板 `:data-item="it.id"`): 单种子菜单 pause/resume 四支同名, 只能按 id 点。 */
const ctxItemById = (page, id) => page.locator(`.ctx-item[data-item="${id}"]`);

/**
 * 一份 /api/state 载荷里的组行清单: 全量轮在顶层 groups; delta 轮在 delta.groups;
 * 「版本未变」轮两者皆无(空数组, 不参与形状断言)。
 * @param {any} b
 * @returns {any[]}
 */
const groupRowsOf = (b) => {
  if (b && Array.isArray(b.groups)) return b.groups;
  if (b && b.delta && Array.isArray(b.delta.groups)) return b.delta.groups;
  return [];
};

/**
 * 打开首页并等首屏渲染(每 test 独立 context 的公共 arrange 前奏, 与 delta-sync.spec 同款)。
 * @param {import('@playwright/test').Page} page
 * @param {string} skin
 */
async function openApp(page, skin) {
  collectRuntimeErrors(page);
  await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
}

/**
 * 行点击统一入口(对冲写法照搬 delta-sync.spec 的 clickRow —— 宽行居中滚动把 {x:8,y:8}
 * 落点滚出裁剪面的 flaky 机理见该文件头; 5 拍 arrange + elementFromPoint 验落点)。
 * @param {import('@playwright/test').Page} page
 * @param {import('@playwright/test').Locator} row
 * @param {{button?: 'left'|'right'}} [opts]
 */
async function clickRow(page, row, opts = {}) {
  const { button = 'left' } = opts;
  let last = null;
  for (let attempt = 0; attempt < 5; attempt++) {
    last = await row.evaluate(async (/** @type {HTMLElement} */ el) => {
      const cont = el.closest('.group-table');
      if (cont && cont.scrollLeft !== 0) cont.scrollLeft = 0;
      /* 拦截面 = **所有** .sticky-head 下沿的最大值(顶栏条与表头各有其一, 只取头一个会低估) */
      const guard = [...document.querySelectorAll('.sticky-head')]
        .reduce((m, h) => Math.max(m, h.getBoundingClientRect().bottom), 0);
      const vh = window.innerHeight;
      const pad = 8;    // 落点纪律同款余量(行左缘 8,8)
      let r = el.getBoundingClientRect();
      const tall = r.height > vh - guard - pad * 2;
      if (r.top < guard + pad || r.bottom > vh - pad) {
        el.scrollIntoView({ block: tall ? 'start' : 'center', behavior: 'instant' });
        await new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(res)));
        r = el.getBoundingClientRect();
      }
      const lo = Math.max(r.top + pad, guard + pad);
      const hi = Math.min(r.bottom - pad, vh - pad);
      const y = lo <= hi ? lo : NaN;   // 可落区为空 ⇒ 本拍作废, 交给下一拍重排
      const x = r.left + pad;
      const hit = Number.isFinite(y) ? document.elementFromPoint(x, y) : null;
      return {
        x, y,
        ok: !!hit && (hit === el || el.contains(hit)),
        hit: hit ? `${hit.tagName}.${String(hit.className && hit.className.baseVal !== undefined ? hit.className.baseVal : hit.className || '')}`.slice(0, 60) : '(null)',
      };
    });
    if (last.ok) break;
  }
  if (!last.ok || !last) {
    throw new Error(`clickRow: 落点验证 5 拍未过(最后拦截者 ${last ? last.hit : '?'}) —— smoke.md「点击拦截面随布局漂移」签名`);
  }
  await page.mouse.click(last.x, last.y, { button });
}

/**
 * 拉一份线级真值(与前端 ingestion 无关的独立数据面, views.spec 数据契约同款直打):
 * view=group 按 VIEW_ARRAYS 回 groups+singles+torrents —— 组行 members 在这里是
 * **服务端发出去的原始形状**, 是 S4 四条用例的期望值锚。数组语义: torrents = flat_view
 * 全量平铺(组员 + 未归组都在内, 每 hash 恰一次), singles 只是它的未归组子集 ——
 * 期望值面一律只吃 torrents, 不再 concat singles(那会把 singles 计双)。
 * @param {import('@playwright/test').APIRequestContext} request
 */
async function fetchWire(request) {
  const res = await request.get(`${baseUrl()}/api/state?view=group`);
  expect(res.ok(), `GET /api/state?view=group -> ${res.status()}`).toBeTruthy();
  const body = await res.json();
  expect(Array.isArray(body.groups) && body.groups.length, '线级载荷有非空 groups').toBeTruthy();
  expect(Array.isArray(body.torrents) && body.torrents.length, '线级载荷有非空 torrents(索引源)').toBeTruthy();
  return body;
}

/**
 * 计数 map 等值断言: 期望(线级现算)逐值等于 vm 选项(_facetOptions 产物)。
 * @param {Array<{value: string, count: number}>} got
 * @param {Map<string, number>} want
 * @param {string} label 断言消息前缀
 */
function expectCountsEqual(got, want, label) {
  const gotMap = new Map(got.map((o) => [o.value, o.count]));
  expect(got.length, `${label}: 选项数(vm=${got.length} / 线级=${want.size})`).toBe(want.size);
  for (const [v, c] of want) {
    expect(gotMap.get(v), `${label}: 值 "${v}" 计数(vm=${gotMap.get(v)} / 线级=${c})`).toBe(c);
  }
}

for (const skin of SKINS) {
  test.describe(`皮肤 ${skin}(P-02 二期 S4: 协议形状)`, () => {
    installRuntimeErrorGuard(test);

    test('线级形状钉: /api/state 组行 members 为 hash 字符串数组, 页面经物化正常渲染 @fast', async ({ page }) => {
      /* 被动旁听页面真实收到的 /api/state(轮询/登录快照/delta 全部途径), 不干预响应 ——
       * 形状钉要钉的是"线上到底发了什么", 不是"改写后的什么"(改写式拦截先例见 gtm-alert.spec)。 */
      const bodies = /** @type {any[]} */ ([]);
      const onResp = (/** @type {import('@playwright/test').Response} */ res) => {
        if (!/\/api\/state(\?|$)/.test(res.url())) return;
        res.json().then((j) => { if (j && typeof j === 'object') bodies.push(j); }).catch(() => {});
      };
      page.on('response', onResp);

      await openApp(page, skin);

      // 等至少一轮**带组行**的载荷落袋(boot 后首轮即全量; expect.poll 免赌轮询节拍)
      await expect.poll(() => bodies.some((b) => groupRowsOf(b).length > 0), {
        message: '至少收到一轮带组行的 /api/state 载荷', timeout: 20_000,
      }).toBe(true);

      // 线级形状: 每份载荷的每个组行 members 都是 40 位 hash 字符串数组(全量轮 + delta 轮一并钉)
      let checked = 0;
      for (const b of bodies) {
        for (const g of groupRowsOf(b)) {
          expect(Array.isArray(g.members), `组行 ${g.key} members 必须是数组(实际 ${typeof g.members})`).toBe(true);
          expect(g.members.length, `组行 ${g.key} members 非空(P-02 一期空组不建行)`).toBeGreaterThan(0);
          for (const h of g.members) {
            expect(typeof h === 'string' && HASH_RE.test(h),
              `组行 ${g.key} members 元素必须是 40 位 hash 串(实际 ${JSON.stringify(h)})`).toBe(true);
          }
          checked += 1;
        }
      }
      expect(checked, '已断言的线级组行数(带组行的载荷至少一轮)').toBeGreaterThan(0);

      // 页面渲染正常: vm 侧组行 members 已全部物化回成员行对象 —— 缺项防御会保留 hash 串,
      // 桩数据恒可解析(索引源 = singles ∪ torrents, VIEW_ARRAYS 连带), 全对象 = 物化缝活着
      expect(await readInst(page, `vm.groups.length > 0 && vm.groups.every((g) =>
        Array.isArray(g.members) && g.members.length > 0 &&
        g.members.every((m) => m && typeof m === 'object' && typeof m.hash === 'string'))`),
        'vm 侧组行 members 全部物化为成员行对象(hash 串残留 = 物化缺项)').toBe(true);
      expect(await page.locator('.group-row').count(), '组行渲染非空').toBeGreaterThan(0);
    });

    test('明细渲染: 组行展开成员行与线级 hash 数组逐一对上, 数据与平铺面一致 @fast', async ({ page, request }) => {
      await openApp(page, skin);
      const wire = await fetchWire(request);

      // 首组行(added_on 降序首组) = 种子页同口径排序的最前两行(桩数据排序事实, 见文件头注),
      // 其成员在种子页窗口顶部必然已渲染 —— 平铺面 DOM 对照免滚动循环。
      const firstKey = await page.locator('.group-row').first().getAttribute('data-key');
      expect(firstKey, '首组行带 data-key').toBeTruthy();
      const wg = wire.groups.find((g) => g.key === /** @type {string} */ (firstKey));
      expect(wg, 'DOM 首组行在线级载荷中有同 key 行').toBeTruthy();

      // 展开(点名称格, 行中心落在站点/标签挂件上会走筛选 —— drawer-groups-shows 同款)
      await page.locator(`.group-row[data-key="${firstKey}"] .g-name`).click({ force: true });
      const memberRows = page.locator('.member-row');
      await expect(memberRows.first()).toBeVisible({ timeout: 10_000 });

      const n = await memberRows.count();
      expect(n, `成员行数 = 线级组行 count(${wg.count})`).toBe(wg.count);

      // 物化缝端到端: 线级 hash 数组 -> DOM 成员行 data-hash 集合逐一对应
      const domHashes = await memberRows.evaluateAll((els) =>
        els.map((e) => e.getAttribute('data-hash') || '').sort());
      expect(domHashes, '明细行 data-hash 集合 == 线级 members hash 集合').toEqual([...wg.members].sort());
      for (const h of domHashes) {
        expect(h, '明细行 data-hash 是 40 位 hash').toMatch(HASH_RE);
      }

      // vm 层缝面: 物化成员行与平铺面(vm.torrents)逐字段一致 + 浅拷贝不变式(独立对象;
      // === 必须页内做 —— 结构化克隆出页面即失对象身份, delta-sync.spec S7 直测同款)
      const seam = await withVm(page, `
        const g = vm.groups.find((x) => x.key === ${JSON.stringify(firstKey)});
        if (!g) return { err: '组不在 vm.groups' };
        const out = { allObj: true, fieldDiff: null, aliasFree: true };
        const FIELDS = ['name', 'kind', 'dlspeed', 'upspeed', 'progress', 'size', 'category', 'site'];
        for (const m of g.members) {
          if (!m || typeof m !== 'object') { out.allObj = false; continue; }
          const f = vm.torrents.find((t) => t.hash === m.hash);
          if (!f) { out.fieldDiff = m.hash + ': 平铺面无此 hash'; break; }
          for (const k of FIELDS) {
            if (JSON.stringify(m[k]) !== JSON.stringify(f[k])) {
              out.fieldDiff = m.hash + '.' + k + ': 组内 ' + JSON.stringify(m[k]) + ' != 平铺 ' + JSON.stringify(f[k]);
              break;
            }
          }
          if (out.fieldDiff) break;
          if (m === f) out.aliasFree = false;   // 组员行与平铺行必须是独立对象(乐观链 prev 采集不变式)
        }
        return out;
      `);
      expect(seam.err, `前置: ${seam.err || 'ok'}`).toBeUndefined();
      expect(seam.allObj, '组行 members 全为成员行对象').toBe(true);
      expect(seam.fieldDiff, '物化成员行与平铺面逐字段一致').toBeNull();
      expect(seam.aliasFree, '组员行与平铺行是独立对象(浅拷贝不变式)').toBe(true);

      // DOM 逐格: 成员行的 状态/进度/下载/上传 文本 == 平铺面数据经同一渲染管线的期望值
      // (速度格无专名类, 按可见列序取下标 —— 值格按可见列序直挂行下, colAlignCss 同款几何)
      const cellIdx = await withVm(page, `return {
        d: vm.visibleDetailCols.findIndex((c) => c.key === 'dlspeed'),
        u: vm.visibleDetailCols.findIndex((c) => c.key === 'upspeed'),
      };`);
      expect(cellIdx.d, '明细表有 dlspeed 列').toBeGreaterThanOrEqual(0);
      expect(cellIdx.u, '明细表有 upspeed 列').toBeGreaterThanOrEqual(0);
      const got = await page.evaluate(`(() => {
        const D = ${JSON.stringify(cellIdx)};
        return [...document.querySelectorAll('.member-row')].map((el) => ({
          hash: el.getAttribute('data-hash'),
          cls: el.className,
          state: (el.querySelector('.m-state .state-text') || {}).innerText ? el.querySelector('.m-state .state-text').innerText.trim() : null,
          pct: (el.querySelector('.m-progress .val') || {}).innerText ? el.querySelector('.m-progress .val').innerText.trim() : null,
          dl: el.children[D.d] ? el.children[D.d].innerText.trim() : null,
          up: el.children[D.u] ? el.children[D.u].innerText.trim() : null,
        }));
      })()`);
      const want = await withVm(page, `
        return ${JSON.stringify(domHashes)}.map((h) => {
          const f = vm.torrents.find((t) => t.hash === h);
          return { hash: h, kind: f.kind, state: vm.stateText(f), pct: vm.progPct(f.progress).toFixed(1) + '%',
                   dl: vm.fmtSpeedOrDash(f.dlspeed), up: vm.fmtSpeedOrDash(f.upspeed) };
        });
      `);
      for (const w of want) {
        const g = got.find((x) => x.hash === w.hash);
        expect(g, `成员行 ${w.hash} 已渲染`).toBeTruthy();
        expect(g.state, `成员行 ${w.hash} 状态文本 == 平铺面渲染值`).toBe(w.state);
        expect(g.pct, `成员行 ${w.hash} 进度文本 == 平铺面渲染值`).toBe(w.pct);
        expect(g.dl, `成员行 ${w.hash} 下载速度 == 平铺面渲染值`).toBe(w.dl);
        expect(g.up, `成员行 ${w.hash} 上传速度 == 平铺面渲染值`).toBe(w.up);
        expect(g.cls.split(/\s+/), `成员行 ${w.hash} 行类含平铺面 kind(${w.kind})`).toContain(w.kind);
      }

      // 平铺面 DOM 对照: 同 hash 的种子行(added_on 降序 = 窗口顶部)状态/进度/下载速度与明细行同值。
      // 前提收窄(major 修复): 「首组行成员 = 种子页窗口顶部两行」的窗口顶部可见性只在**全库归组**
      // (wire.singles 空)时成立 —— 默认 300 档桩前 150 对两两归组恰好吃满全库, 首组(added_on 最大的
      // 末对)成员就是种子页最前两行; --torrents 3000 档只归前 200 对, 其余落单 singles 的 added_on
      // 比首组成员大, 占满 rowWin 窗口顶部, 首组成员沉到窗口外(窗口化不渲染), 可见性断言必红。
      // singles 非空时跳过本段 —— 不改成滚动检索找行: 那会给大库轮引入负载型 flake(smoke.md 忌讳)。
      if ((wire.singles || []).length === 0) {
        await tab(page, 'torrents').click();
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        const tIdx = await withVm(page, `return vm.visibleTorrentCols.findIndex((c) => c.key === 'dlspeed');`);
        expect(tIdx, '种子页有 dlspeed 列').toBeGreaterThanOrEqual(0);
        for (const h of wg.members) {
          const trow = page.locator(`.torrent-row[data-hash="${h}"]`);
          await expect(trow, `种子页窗口顶部可见成员 ${h} 的平铺行`).toBeVisible();
          const tCell = await trow.evaluate((/** @type {HTMLElement} */ el, i) => ({
            state: (el.querySelector('.state-text') || {}).innerText ? el.querySelector('.state-text').innerText.trim() : null,
            pct: (el.querySelector('.m-progress .val') || {}).innerText ? el.querySelector('.m-progress .val').innerText.trim() : null,
            dl: el.children[i] ? el.children[i].innerText.trim() : null,
          }), tIdx);
          const mCell = got.find((x) => x.hash === h);
          expect(tCell.state, `平铺行 ${h} 状态文本 == 明细行`).toBe(mCell.state);
          expect(tCell.pct, `平铺行 ${h} 进度文本 == 明细行`).toBe(mCell.pct);
          expect(tCell.dl, `平铺行 ${h} 下载速度 == 明细行`).toBe(mCell.dl);
        }
      } else {
        // singles 非空档(--torrents 3000 矩阵轮): 平铺窗口顶部对照段按前提收窄跳过(见上注)。
        expect(wire.singles.length, '非全库归组档: 跳过窗口顶部对照段的前提成立').toBeGreaterThan(0);
      }
    });

    test('筛选计数: 五筛选器族在 hash 引用式组行下计数正确(组数/种子数两口径) @fast', async ({ page, request }) => {
      await openApp(page, skin);
      const wire = await fetchWire(request);

      // 期望值面: 线级载荷的**瘦行**(计数消费的字段) + 组行 hash 映射喂进页内现算 ——
      // 路径位置集必须复用 vm._pathPositions 同源谓词(26-11-07-2344 R3 D17, 禁止 spec 复刻);
      // 值抽取 mirror filters.js::_facetPick(tag 展开 / category、site 真值才计)。
      // 瘦行源**只取 wire.torrents**: flat_view 是全库平铺(组员 + 未归组都在内, 每 hash 恰
      // 一次), singles 只是它的未归组子集 —— 旧写法 concat(singles) 把 singles 计双(桩
      // --torrents 3000 档只归前 200 对, singles=2600), kindCounts/memberTotal 结构红。
      const exp = await withVm(page, `
        const slim = ${JSON.stringify(wire.torrents.map((t) => ({
          hash: t.hash, kind: t.kind, tags: t.tags || [], category: t.category || '',
          site: t.site || '', save_path: t.save_path || '', relocate: t.relocate || null,
        })))};
        const byHash = new Map(slim.map((r) => [r.hash, r]));
        const gHashes = ${JSON.stringify(wire.groups.map((g) => [g.key, g.members]))};
        const pick = (r, kind) => {
          if (kind === 'tag') return r.tags || [];
          if (kind === 'category') return r.category ? [r.category] : [];
          if (kind === 'site') return r.site ? [r.site] : [];
          return vm._pathPositions(r);   // 路径: 同源谓词, 不复刻
        };
        // 选项计数(带行内去重, mirror _facetOptions + _facetPick 的 row.members || [row]):
        // rowList 元素 = 组(成员行数组, 组内去重后计一组)或单行(种子页), 归一后逐成员取值
        const optOf = (kind, rowList) => {
          const counts = new Map();
          for (const row of rowList) {
            const members = Array.isArray(row) ? row : [row];
            const seen = new Set();
            for (const r of members) {
              for (const v of pick(r, kind)) {
                if (seen.has(v)) continue;
                seen.add(v);
                counts.set(v, (counts.get(v) || 0) + 1);
              }
            }
          }
          return counts;
        };
        // 组视图行 = 线级组行(经 hash 引用还原成员); 种子页行 = 平铺行自身
        const groupRows = gHashes.map(([, hs]) => hs.map((h) => byHash.get(h)).filter(Boolean));
        const kindCounts = {};
        for (const r of slim) kindCounts[r.kind] = (kindCounts[r.kind] || 0) + 1;
        const FAM = ['tag', 'category', 'site', 'path'];
        const pack = (m) => [...m.entries()].map(([value, count]) => ({ value, count }));
        return {
          group: Object.fromEntries(FAM.map((k) => [k, pack(optOf(k, groupRows))])),
          seed: Object.fromEntries(FAM.map((k) => [k, pack(optOf(k, slim))])),
          kindCounts,
          memberTotal: slim.length,
        };
      `);
      // 前置自证: 线级组行的成员 hash 全部可在平铺面解析(期望值计算的数据前提 ——
      // 页内现算对未解析 hash 是静默 filter(Boolean) 塌缩, 必须在这里显式拦下;
      // 解析源同上 = wire.torrents 全量平铺, 每 hash 恰一次)
      const flatByHash = new Map(wire.torrents.map((t) => [t.hash, t]));
      const unresolved = wire.groups.reduce(
        (acc, g) => acc + g.members.filter((h) => !flatByHash.has(h)).length, 0);
      expect(unresolved, '线级组行成员 hash 全部可在平铺面解析(flat_view 全量平铺)').toBe(0);

      // 组视图口径: 四 facet 族 = 含该值的**组数**; 状态分布 = **种子数**(逐成员)
      const vmGroup = await withVm(page, `return {
        tag: vm.tagOptions, category: vm.categoryOptions, site: vm.siteOptions, path: vm.pathOptions,
        dist: vm.distSegments.map((s) => ({ kind: s.kind, count: s.count })),
      };`);
      expectCountsEqual(vmGroup.tag, new Map(exp.group.tag.map((o) => [o.value, o.count])), '组视图 标签');
      expectCountsEqual(vmGroup.category, new Map(exp.group.category.map((o) => [o.value, o.count])), '组视图 分类');
      expectCountsEqual(vmGroup.site, new Map(exp.group.site.map((o) => [o.value, o.count])), '组视图 站点');
      expectCountsEqual(vmGroup.path, new Map(exp.group.path.map((o) => [o.value, o.count])), '组视图 路径');
      const kindSum = Object.values(exp.kindCounts).reduce((a, b) => a + b, 0);
      expect(kindSum, '状态分布合计 = 种子数口径(逐成员, 含 singles)').toBe(exp.memberTotal);
      expect(kindSum, '状态分布合计 = 桩种子总数').toBe(TORRENTS);
      for (const s of vmGroup.dist) {
        expect(s.count, `组视图 状态 ${s.kind} 计数 = 线级逐成员计数`).toBe(exp.kindCounts[s.kind] || 0);
      }

      // 状态图例 chips 的 DOM 渲染(组视图常显): 文本 = kindText + 计数
      await expect(page.locator('.dist-legend .dist-chip').first(),
        '状态图例 chips 已随首屏渲染').toBeVisible({ timeout: 10_000 });
      const chips = await page.evaluate(`(() => [...document.querySelectorAll('.dist-legend .dist-chip')].map((el) => {
        const t = el.innerText.replace(/\\s+/g, ' ').trim();
        const m = t.match(/^(.*) (\\d+)$/);
        return m ? [m[1], Number(m[2])] : [t, null];
      }))()`);
      const wantChips = await withVm(page,
        `return vm.distSegments.map((s) => [vm.kindText(s.kind), s.count]);`);
      expect(chips, '状态图例 chips 文本/计数 == distSegments').toEqual(wantChips);

      // 标签筛选弹层真实点击: .pop-item 的 值/计数 徽标 == tagOptions(选项计数进 DOM 的那一跳)
      const tagPop = page.locator('.filter-pop', { has: page.locator('.filter-btn', { hasText: '标签' }) });
      await tagPop.locator('.filter-btn').click();
      const popItems = tagPop.locator('.pop-menu .pop-item');
      await expect(popItems.first()).toBeVisible({ timeout: 5_000 });
      const domTag = await popItems.evaluateAll((els) => els.map((e) => [
        (e.querySelector('.pop-value') || {}).innerText ? e.querySelector('.pop-value').innerText.trim() : '',
        Number(((e.querySelector('.pop-count') || {}).innerText || '').trim()) || 0,
      ]));
      expect(domTag, '标签弹层 DOM 项 == tagOptions(值, 计数)').toEqual(
        vmGroup.tag.map((o) => [o.value, o.count]));
      await tagPop.locator('.filter-btn').click();  // 再点同钮收起

      // 种子页口径: 四 facet 族 = 含该值的**种子数**(facetRows = torrents 平铺行)
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      const vmSeed = await withVm(page, `return {
        tag: vm.tagOptions, category: vm.categoryOptions, site: vm.siteOptions, path: vm.pathOptions,
        dist: vm.distSegments.map((s) => ({ kind: s.kind, count: s.count })),
      };`);
      expectCountsEqual(vmSeed.tag, new Map(exp.seed.tag.map((o) => [o.value, o.count])), '种子页 标签');
      expectCountsEqual(vmSeed.category, new Map(exp.seed.category.map((o) => [o.value, o.count])), '种子页 分类');
      expectCountsEqual(vmSeed.site, new Map(exp.seed.site.map((o) => [o.value, o.count])), '种子页 站点');
      expectCountsEqual(vmSeed.path, new Map(exp.seed.path.map((o) => [o.value, o.count])), '种子页 路径');
      // 状态分布在两视图同数(同一批成员, 不同取数路径: 组成员物化行 vs 平铺行)
      expect(vmSeed.dist, '种子页状态分布 == 组视图状态分布(种子数口径)').toEqual(vmGroup.dist);
    });

    test('乐观补丁: 组内成员暂停/恢复 UI 即时变化 + 真值落地收敛(ok 模式)', async ({ page }) => {
      // 真值面依赖命令成功(见文件头模式门控注), error/hang 轮结构恒红
      requireMode(test, { cmdResult: 'ok' });
      // 被动旁听(同 test 1 形状钉的写法): 暂停/恢复真值轮必然走 delta(命令真值 bump 版本),
      // 把「delta 轮一并钉」落到本用例必然出现的轮次 —— 监听器独立 res.json() 解析, 页面侧
      // 物化是就地改写载荷行对象, 不影响这里拿到的服务端原始形状。
      const bodies = /** @type {any[]} */ ([]);
      const onResp = (/** @type {import('@playwright/test').Response} */ res) => {
        if (!/\/api\/state(\?|$)/.test(res.url())) return;
        res.json().then((j) => { if (j && typeof j === 'object') bodies.push(j); }).catch(() => {});
      };
      page.on('response', onResp);
      await openApp(page, skin);

      // 挑组: 第一个含非暂停成员的组(长驻桩跨 test 状态, optimistic/delta-sync 同款挑选;
      // 物化对象形前置自证 —— hash 串槽不能当操作目标)
      const t = await withVm(page, `
        const g = vm.groups.find((x) => x.members.some((m) => m && typeof m === 'object' && m.kind !== 'paused'));
        if (!g) return { err: '没有含非暂停成员的组' };
        const m = g.members.find((m) => m && typeof m === 'object' && m.kind !== 'paused');
        return { key: g.key, hash: m.hash, beforeKind: m.kind };
      `);
      expect(t.err, `前置: ${t.err || 'ok'}`).toBeUndefined();

      // 展开该组 -> 成员行可见(明细表数据源 = 物化缝, 乐观操作打在成员行上)
      await page.locator(`.group-row[data-key="${t.key}"] .g-name`).click({ force: true });
      const mrow = page.locator(`.member-row[data-hash="${t.hash}"]`);
      await expect(mrow).toBeVisible({ timeout: 10_000 });

      // 右键成员行 -> 单种子菜单 -> 停止(真实手势; 记录器必须在点击之前装好 —— 瞬时窗口)
      await clickRow(page, mrow, { button: 'right' });
      const item = ctxItemById(page, 'pause');
      await expect(item).toBeVisible({ timeout: 5_000 });
      await armPending(page, `.member-row[data-hash="${t.hash}"].is-pending`);
      await armClick(page, await item.elementHandle());
      await item.click();

      // 乐观即时: 成员行 is-pending 曾经出现(桩命令瞬时回执, 事后再数恒 0 —— 记录器口径)
      await expect.poll(() => page.evaluate('window.__p ? window.__p.appear : null'), {
        message: '点击 -> 记录器采到成员行 is-pending 出现(瞬时窗口)', timeout: 8_000,
      }).not.toBe(null);
      // 乐观补丁同时把行 kind 打到 paused(明细行类 = m.kind, 即时变化)
      await expect.poll(async () => (await mrow.getAttribute('class')) || '', {
        message: '乐观补丁即时把成员行打到暂停态(行类含 paused)', timeout: 2_000,
      }).toContain('paused');

      // 真值收敛: pendingOps 清账 + 行 kind 停在真值 + 增量轮重组的组行仍是物化对象形
      // + 拷贝源新鲜度档(major 修复): 组员拷贝上「补丁不触字段」的 state 必须等于线级真值。
      //   判别机理: 乐观补丁只写 kind(commands_optimistic.js 的 pause/resume patch 都只有
      //   {kind}), state 不在补丁键里; 而桩的真值变更(pause -> _PAUSED_STATE="pausedDL")恰恰
      //   改的就是 state —— 「downloading 与 paused 真值行可区分」且「本地旧行值 != 线级真值」
      //   在桩里成立(被选成员 kind != paused, 其 state 必不在 {pausedDL, pausedUP}, 与真值行
      //   的 pausedDL 必异; progress/added_on 等其余补丁不触字段在静态桩里真值前后同值, 判别
      //   不了拷贝源)。对照源 = vm.torrents 平铺行: delta 轮脏行整行替换直推 upsert 行对象
      //   本体(applyStateRows applyRows), 即线级真值的页内驻留。桶序正确(torrents/singles
      //   合并先于组行物化)时组员拷贝 = {...新鲜行}, state 必等; 回归(物化挪到 torrents 合并
      //   前)时拷贝源 = 本地旧行, state 停旧值 -> m.state !== f.state 恒成立 -> 判据恒 null ->
      //   poll 超时红。恢复段同档: 恢复真值行 state(uploading/downloading)异于回弹前 pausedDL。
      const converged = `(() => {
        const g = vm.groups.find((x) => x.key === ${JSON.stringify(t.key)});
        const m = g && g.members.find((x) => x.hash === ${JSON.stringify(t.hash)});
        if (!m || typeof m !== 'object') return null;   // 重组后退化成 hash 串 = 物化破(判据恒红)
        if (vm.pendingOps[${JSON.stringify(t.hash)}]) return null;   // 真值未落(乐观值不算数)
        const f = (vm.torrents || []).find((x) => x.hash === ${JSON.stringify(t.hash)});
        if (!f) return null;                            // 平铺真值行未合并(真值未落) -> 继续等
        if (m.state !== f.state) return null;           // 新鲜度档: 拷贝源=本地旧行(桶序回归) -> 恒红
        return m.kind;
      })()`;
      await expect.poll(async () => readInst(page, converged), {
        message: '暂停真值落地(组行 members 仍物化 + pending 清账 + 拷贝源新鲜(state==平铺真值行) + kind=paused)',
        timeout: 8_000,
      }).toBe('paused');

      // delta 轮形状钉(major 修复配套): 暂停真值轮必然带非空 delta.groups(成员脏 => 同代组脏,
      // runtime_views.py drain_delta 不变式) —— 每个组行 members 仍是 40 位 hash 数组, 与全量轮
      // 同契约(test 1 的形状钉由此落到本用例必然出现的 delta 轮上)。
      const deltaGroups = () => bodies.flatMap((b) =>
        (b && b.full === false && b.delta && Array.isArray(b.delta.groups)) ? b.delta.groups : []);
      await expect.poll(() => deltaGroups().length, {
        message: '暂停真值轮的 delta 组行已落袋(成员脏=>同代组脏, 必然出现)', timeout: 10_000,
      }).toBeGreaterThan(0);
      for (const g of deltaGroups()) {
        expect(Array.isArray(g.members), `delta 组行 ${g.key} members 必须是数组(实际 ${typeof g.members})`).toBe(true);
        for (const h of g.members) {
          expect(typeof h === 'string' && HASH_RE.test(h),
            `delta 组行 ${g.key} members 元素必须是 40 位 hash 串(实际 ${JSON.stringify(h)})`).toBe(true);
        }
      }

      // 恢复(启动): 反向同链 —— 收敛回非暂停真值, 行类随真值离开 paused(判据含同一新鲜度档)
      await clickRow(page, mrow, { button: 'right' });
      const resume = ctxItemById(page, 'resume');
      await expect(resume).toBeVisible({ timeout: 5_000 });
      await resume.click();
      await expect.poll(async () => readInst(page, converged), {
        message: '恢复真值落地(组行 members 仍物化 + pending 清账 + 拷贝源新鲜)', timeout: 8_000,
      }).toBeTruthy();
      const afterKind = /** @type {string} */ (await readInst(page, converged));
      expect(afterKind, '恢复后行 kind 回到非暂停真值').not.toBe('paused');
      expect((await mrow.getAttribute('class')) || '', '成员行类离开 paused').not.toContain('paused');
      expect(await readInst(page, 'Object.keys(vm.pendingOps || {}).length'),
        '收尾不留假状态(pendingOps 清零)').toBe(0);
    });
  });
}
