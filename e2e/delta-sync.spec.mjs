// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst, withVm } from './lib/vm.mjs';

/**
 * S4 增量合并冒烟(plan 26-10-07-0414 S4) —— 前端默认带 delta=1 后, /api/state 的更新轮
 * 可能回增量载荷(full=false + delta/removed 桶), refresh() 经 polling.js applyStateRows
 * 行级合并。本文件只做**冒烟**(内容等价由 S5 镜子兜底):
 *   1. 真实手势(右键暂停)触发的真值轮**确实是增量轮**(full=false)且渲染正确(行变真值态);
 *   2. applyStateRows 行级语义的页面内直测(D4 第①类注入桩态): upsert 替换/追加 + removed
 *      剔除 + 未脏行对象引用恒等(DoD 的 === 断言)+ 数组新实例 + lastRid 置空走 full 恢复;
 *   3. 分组视图整组暂停: 组桶(groups)经增量轮渲染正确。
 *   4. S7 装饰记忆化(plan 26-10-07-0414): decorate.js decoratedGroups 的 WeakMap 层 ——
 *      未脏组行的装饰结果引用恒等(= 未重算的直接证据, 页内 === 断言), 脏行 miss 重算且
 *      装饰结果与无记忆化逐字段一致、键集形状不变(computed 静默白屏坑的形状红线)。
 * 桩服务(scripts/ui_harness.py)的命令泵只真改 pause/resume 状态(见 _apply_truth), 删除
 * 不落合成数据 ⇒ removed 路径在这里走注入桩态直测, 不走 UI 删除(真删除会减少共享桩的
 * 种子总数, 打破 views.spec 的 `filteredTorrents.length === TORRENTS` 精确断言)。
 *
 * 探针说明(armDeltaProbe): 包装 vm.applyStateRows 记录每轮 {full, rid, delta 桶键} ——
 * vm 方法直调/包装属 D4 守则第②类(vm 内部行为没有 DOM 之外的取径, optimistic.spec T6/T7
 * 同款先例); 交互本身(右键 → 菜单 → 暂停)一律真实手势。
 *
 * 为什么「行变色」不能单独当增量渲染判据: 乐观补丁(P0-3)在点击后立刻就把行 kind 改成
 * paused(视觉同色), 真值轮的合并渲染必须另找判据 —— 用「pendingOps 已清(真值对齐)+
 * 行 kind 仍是真值态」表示合并链走完, 再叠探针的 full=false 轮佐证。
 */

/** 导航页签定位器(tpl/topbar.html `nav.tabs [data-view]`)。 */
const tab = (page, view) => page.locator(`nav.tabs [data-view="${view}"]`);
/** 菜单项定位器(ctx 菜单是 div.ctx-item, 无 role, 按文案取)。 */
const ctxItem = (page, text) => page.locator('.ctx-item', { hasText: text });

/**
 * 打开首页并等首屏渲染(每 test 独立 context 的公共 arrange 前奏, 与 optimistic.spec 同款)。
 * @param {import('@playwright/test').Page} page
 * @param {string} skin
 */
async function openApp(page, skin) {
  collectRuntimeErrors(page);
  await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
}

/** 进种子视图并等行渲染(perf.spec gotoTorrents 同款)。 */
async function gotoTorrents(page, skin) {
  await openApp(page, skin);
  await tab(page, 'torrents').click();
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
}

/**
 * 行点击统一入口(对冲写法照搬 optimistic.spec 的 clickRow —— 宽行居中滚动把 {x:8,y:8}
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
      const head = document.querySelector('.sticky-head');
      const headBottom = head ? head.getBoundingClientRect().bottom : 0;
      let r = el.getBoundingClientRect();
      if (r.top < headBottom + 8 || r.bottom > window.innerHeight - 8) {
        el.scrollIntoView({ block: 'center', behavior: 'instant' });
        await new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(res)));
        r = el.getBoundingClientRect();
      }
      const x = r.left + 8;
      const y = r.top + 8;
      const hit = document.elementFromPoint(x, y);
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
 * 给 vm.applyStateRows 装记录器(见文件头探针说明), 之后每一轮合并都会被记进 window.__d。
 * @param {import('@playwright/test').Page} page
 */
async function armDeltaProbe(page) {
  await withVm(page, `
    window.__d = window.__d || { rounds: [] };
    if (!vm.__origApplyStateRows) {
      vm.__origApplyStateRows = vm.applyStateRows;
      vm.applyStateRows = function (p) {
        window.__d.rounds.push({
          full: p.full === undefined ? null : p.full,
          rid: typeof p.rid === 'number' ? p.rid : null,
          buckets: p.full === false ? Object.keys(p.delta || {}).sort().join(',') : null,
        });
        return vm.__origApplyStateRows.call(vm, p);
      };
    }
    return window.__d.rounds.length;
  `);
}

/** 读探针记录的合并轮清单。 */
async function deltaRounds(page) {
  return (await readInst(page, '(window.__d && window.__d.rounds) || []')) || [];
}

for (const skin of SKINS) {
  test.describe(`皮肤 ${skin}(S4: 增量合并冒烟)`, () => {
    installRuntimeErrorGuard(test);

    test('真实暂停手势触发增量轮(full=false)且真值渲染正确 + 未脏行引用恒等', async ({ page }) => {
      await gotoTorrents(page, skin);
      await armDeltaProbe(page);

      /* 挑一个未暂停的行当目标(长驻桩跨 test 状态, optimistic.spec pausableRow 同款挑选) */
      const rows = page.locator('.torrent-row');
      const n = await rows.count();
      let target = null;
      for (let i = 0; i < n; i++) {
        const cls = (await rows.nth(i).getAttribute('class')) || '';
        if (!cls.includes('s-paused')) { target = rows.nth(i); break; }
      }
      expect(target, '存在未暂停的行').toBeTruthy();
      const targetHash = await target.getAttribute('data-hash');
      /* 旁观者 = 数据里第一个非目标行: 只当「未脏行引用恒等」的见证, 不参与任何操作(vm 探针, 第②类) */
      expect(await withVm(page, `
        window.__bystander = vm.torrents.find((r) => r.hash !== ${JSON.stringify(targetHash)});
        return !!window.__bystander;
      `)).toBe(true);
      const roundsBefore = (await deltaRounds(page)).length;

      await clickRow(page, target, { button: 'right' });
      await ctxItem(page, '暂停该种子').first().click();

      /* 真值对齐判据: 该行已不在 pendingOps(真值已到并清账)且行 kind 停在真值态 'paused'
       * (回执/3s 兜底路径不会同时满足这两条 —— 兜底是回滚成暂停前的 kind)。
       * 轮询 ≤1.5s + 桩真值延迟 0.12s, 8s 窗口足够。 */
      await expect.poll(async () => await readInst(page, `
        (() => { const row = vm.torrents.find((r) => r.hash === ${JSON.stringify(targetHash)});
                 return row && !vm.pendingOps[${JSON.stringify(targetHash)}] ? row.kind : null; })()
      `), {
        message: '暂停真值经合并落行(行 kind=paused 且 pending 已清账)',
        timeout: 8_000,
      }).toBe('paused');

      /* 这一轮确实是增量轮(full=false)且带 torrents 桶; lastRid 恒 = 最后收到的 rid */
      const rounds = await deltaRounds(page);
      const deltaOnes = rounds.slice(roundsBefore).filter((r) => r.full === false);
      expect(deltaOnes.length, '暂停后的更新轮至少有一次增量轮(full=false)').toBeGreaterThan(0);
      expect(deltaOnes.some((r) => (r.buckets || '').includes('torrents')), '增量轮带 torrents 桶').toBe(true);
      expect(typeof (await readInst(page, 'vm.lastRid')), 'lastRid 更新为数字').toBe('number');
      /* DoD: 未脏行对象引用原样保留(vm.torrents 里仍是同一个对象) */
      expect(await readInst(page, 'vm.torrents.includes(window.__bystander)'),
        '未脏行引用恒等(=== 同一对象)').toBe(true);
    });

    test('applyStateRows 行级语义直测: upsert 替换/追加 + removed 剔除 + 数组新实例 + 置空走 full 恢复', async ({ page }) => {
      await gotoTorrents(page, skin);  // 种子视图: vm.torrents 才有数据(view=group 的全量不含 torrents)
      await armDeltaProbe(page);
      /* 注入桩态直调合并入口(D4 第①类): 构造合成 delta 载荷(替换/追加/删除/未脏见证)。
       * 身份断言用 marker 字段而不是 `===`: vm 读出的行是响应式代理, 载荷行是裸对象 ——
       * 「合并后该行只剩载荷实例」由「只有载荷实例带 marker」等价表达(未脏行见证走
       * includes, Vue 对数组 includes 做了 toRaw 回退, 代理与裸对象都能命中)。 */
      const r = await withVm(page, `
        const t0 = vm.torrents[0];    // 种子桶替换对象
        const t1 = vm.torrents[1];    // 种子桶删除对象
        const keep = vm.torrents[2];  // 种子桶未脏见证
        const upT = JSON.parse(JSON.stringify(t0)); upT.progress = (upT.progress || 0) + 0.5; upT.__s4probe = 'upT';
        const newT = JSON.parse(JSON.stringify(t0)); newT.hash = 'f'.repeat(40); newT.__s4probe = 'newT';
        const g0 = vm.groups[0];      // 组桶替换对象
        const gKeep = vm.groups[1] || null;  // 组桶未脏见证(组数不足两行时跳过)
        const upG = JSON.parse(JSON.stringify(g0)); upG.name = (upG.name || '') + '*'; upG.__s4probe = 'upG';
        const arrT = vm.torrents, arrG = vm.groups, arrS = vm.singles;
        vm.applyStateRows({
          rid: (typeof vm.lastRid === 'number' ? vm.lastRid : 0) + 1, updated: true, full: false,
          delta: { torrents: [upT, newT], groups: [upG] },
          removed: { torrents: [t1.hash], groups: [], singles: [], shows: [] },
        });
        return {
          torrentNewArr: vm.torrents !== arrT,
          groupNewArr: vm.groups !== arrG,
          singlesUntouched: vm.singles === arrS,  // 桶键不存在: 原引用不动(不 || [] 清空)
          upserted: (vm.torrents.find((x) => x.hash === t0.hash) || {}).__s4probe === 'upT',
          appended: vm.torrents.some((x) => x.hash === newT.hash),
          removedGone: !vm.torrents.some((x) => x.hash === t1.hash),
          keepRef: vm.torrents.includes(keep),
          t1RefGone: !vm.torrents.includes(t1),
          groupUpserted: (vm.groups.find((x) => x.key === g0.key) || {}).__s4probe === 'upG',
          groupKeepRef: gKeep ? vm.groups.includes(gKeep) : null,
          membersCarried: Array.isArray(upG.members) && upG.members.length === g0.members.length,  // R8: members 随整行原样携带
        };
      `);
      for (const [k, v] of Object.entries(r)) {
        if (v !== null) expect(v, `applyStateRows 行级语义: ${k}`).toBe(true);
      }
      /* 收尾(页内还原 + 顺带冒烟「lastRid 置空 ⇒ 恒全量」路径, 切视图同款):
       * 先踢一次 refresh(只踢一次 —— 在轮询循环里反复踢会堆叠请求链), 再轮询读探针。 */
      await withVm(page, `(vm.lastRid = null, void vm.refresh(), true)`);
      await expect.poll(async () => await readInst(page, `
        (window.__d.rounds[window.__d.rounds.length - 1] || {}).full
      `), { message: 'lastRid 置空后下一轮为全量(full=true)', timeout: 8_000 }).toBe(true);
      expect(await readInst(page, `vm.torrents.some((x) => x.hash === ${JSON.stringify('f'.repeat(40))})`),
        '全量轮后注入的合成行被服务端真值覆盖').toBe(false);
    });

    test('分组视图整组暂停: 组桶(groups)经增量轮渲染正确', async ({ page }) => {
      await openApp(page, skin);  // 默认落在分组视图
      await armDeltaProbe(page);
      const rows = page.locator('.group-row[data-table="group"]');
      await expect(rows.first()).toBeVisible({ timeout: 15_000 });
      /* 挑一个非暂停的组(行状态色 = 组内成员聚合, 桩跨 test 状态同款挑选) */
      const n = await rows.count();
      let target = null;
      for (let i = 0; i < n; i++) {
        const cls = (await rows.nth(i).getAttribute('class')) || '';
        if (!cls.includes('s-paused')) { target = rows.nth(i); break; }
      }
      expect(target, '存在非暂停的组行').toBeTruthy();
      const groupKey = await target.getAttribute('data-key');
      const roundsBefore = (await deltaRounds(page)).length;

      await clickRow(page, target, { button: 'right' });
      await ctxItem(page, '暂停整组').first().click();

      /* 组行真值对齐: 组内成员 pending 清账 + 行状态色停在真值聚合档(乐观期也会变 paused 色,
       * 所以同样以 pendingOps 清账为准 —— 成员 hash 从 pendingOps 消失即真值轮已合并)。
       * !读 vm.decoratedGroups: status 是 decorate.js 的 computed 派生字段, 不在原始组行上。 */
      await expect.poll(async () => await readInst(page, `
        (() => { const g = vm.decoratedGroups.find((x) => x.key === ${JSON.stringify(groupKey)});
                 if (!g) return null;
                 const pending = (g.members || []).some((m) => vm.pendingOps[m.hash]);
                 return pending ? null : g.status.primary; })()
      `), {
        message: '整组暂停真值落回(组行状态=paused 且成员 pending 清账)',
        timeout: 8_000,
      }).toBe('paused');
      const rounds = await deltaRounds(page);
      const deltaOnes = rounds.slice(roundsBefore).filter((r) => r.full === false);
      expect(deltaOnes.length, '整组暂停后的更新轮至少有一次增量轮').toBeGreaterThan(0);
      expect(deltaOnes.some((r) => (r.buckets || '').includes('groups')), '增量轮带 groups 桶(view=group 裁剪)').toBe(true);
    });

    test('S7 装饰记忆化: 未脏组行装饰结果引用恒等(未重算) + 脏行重算且与无记忆化逐字段一致', async ({ page }) => {
      await openApp(page, skin);  // 默认落在分组视图, vm.groups 有数据
      /* 单次页内事务(D4 第①类注入 + 第②类读数, S4 直测同款; 一笔完成免轮询竞态):
       * 引用比较必须在页内做 —— withVm 返回值过结构化克隆, 出页面即失对象身份。
       * 步骤: ①快照各行装饰结果引用 → ②注入合成 delta(第 0 组脏=整行新对象, 第 1 组未脏
       * = 引用原样, applyStateRows 的既有口径) → ③对**合并后**的每组用 vm 自带同源纯方法
       * (_aggStatus/_commonTags/_commonCategory)做无记忆化现算, 与缓存结果逐字段比 + 键集
       * 形状比(原行键 + 5 个派生键, 无多余/缺失) → ④返回全部断言。 */
      const r = await withVm(page, `
        const snap = { deco: {}, arr: vm.decoratedGroups };
        for (const d of snap.arr) snap.deco[d.key] = d;
        if (vm.groups.length < 2) return { skip: 'groups 不足两行' };

        const g0 = vm.groups[0];                       // 脏组: 整行替换对象
        const keepKey = vm.groups[1].key;              // 未脏见证组
        const upG = JSON.parse(JSON.stringify(g0));
        upG.name = (upG.name || '') + '*';
        vm.applyStateRows({
          rid: (typeof vm.lastRid === 'number' ? vm.lastRid : 0) + 1, updated: true, full: false,
          delta: { groups: [upG] },
          removed: { torrents: [], singles: [], groups: [], shows: [] },
        });

        // 无记忆化现算(纯函数口径与 decorate.js 逐字一致, 复用 vm 注入的同源方法)
        const ADDED = ['save_path', 'status', 'commonTags', 'commonCategory', 'sizeMismatch'];
        const fresh = {};
        for (const g of vm.groups) {
          fresh[g.key] = {
            save_path: (g.members[0] && g.members[0].save_path) || '',
            status: vm._aggStatus(g.members),
            commonTags: vm._commonTags(g.members),
            commonCategory: vm._commonCategory(g.members),
            sizeMismatch: new Set(g.members.map((m) => m.size)).size > 1,
          };
        }
        let mismatch = null;
        for (const d of vm.decoratedGroups) {
          const raw = vm.groups.find((x) => x.key === d.key);
          const f = fresh[d.key];
          const rawKeys = new Set(Object.keys(raw));
          const shapeOk = Object.keys(d).length === rawKeys.size + ADDED.length &&
            ADDED.every((k) => k in d) &&
            Object.keys(d).every((k) => rawKeys.has(k) || ADDED.includes(k));
          const fieldOk = d.save_path === f.save_path &&
            JSON.stringify(d.status) === JSON.stringify(f.status) &&
            JSON.stringify(d.commonTags) === JSON.stringify(f.commonTags) &&
            JSON.stringify(d.commonCategory) === JSON.stringify(f.commonCategory) &&
            d.sizeMismatch === f.sizeMismatch;
          if (!shapeOk) { mismatch = { key: d.key, why: '键集形状漂移' }; break; }
          if (!fieldOk) { mismatch = { key: d.key, why: '字段与无记忆化现算不一致' }; break; }
        }
        return {
          mismatch,
          arrNew: vm.decoratedGroups !== snap.arr,
          witnessRefSame: vm.decoratedGroups.find((x) => x.key === keepKey) === snap.deco[keepKey],
          dirtyRefNew: vm.decoratedGroups.find((x) => x.key === g0.key) !== snap.deco[g0.key],
          dirtyRenamed: (vm.decoratedGroups.find((x) => x.key === g0.key) || {}).name === upG.name,
        };
      `);
      if (r.skip) test.skip(true, r.skip);
      expect(r.mismatch, '装饰结果与无记忆化逐字段一致 + 键集形状不变').toBeNull();
      expect(r.arrNew, 'groups 变化触发 computed 重算(数组新实例, 消费方照常感知)').toBe(true);
      expect(r.witnessRefSame, '未脏组行装饰结果引用恒等(WeakMap 命中 = 未重算的直接证据)').toBe(true);
      expect(r.dirtyRefNew, '脏组行装饰结果为新对象(WeakMap miss 重算)').toBe(true);
      expect(r.dirtyRenamed, '脏行装饰内容反映新行(名称带 *)').toBe(true);

      /* 收尾: 踢一次全量刷新, 让注入的合成组被服务端真值覆盖(共享桩还原, S4 直测同款) */
      await withVm(page, `(vm.lastRid = null, void vm.refresh(), true)`);
      await expect.poll(async () => await readInst(page, `
        vm.groups.some((x) => (x.name || '').endsWith('*'))
      `), { message: '全量轮后注入的合成组被真值覆盖', timeout: 8_000 }).toBe(false);
    });
  });
}
