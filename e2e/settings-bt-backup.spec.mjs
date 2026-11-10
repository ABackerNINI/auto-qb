// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';

/**
 * 设置页 · 「自动化」分区 · 「整组迁移」块的 BT_backup 编辑器(S4 重写, 计划 26-11-11-0259;
 * 前身 = 26-11-07-0708 S5 的键值表编辑器 spec, 旧表已随 relocate.bt_backup 标量收编退役)。
 *
 * 背景(计划 §3.1 主线 3 / §3.2 五态): 编辑器 = 单路径输入 + 「自动探测」按钮 + 证据展示区。
 * relocate.bt_backup 在 schema 打 hidden(S4, 组件接管渲染, 不然通用行与本编辑器同键双输入框),
 * 编辑直接落在 cfg.tree.config.relocate.bt_backup 草稿上, 保存走全局 cfgSave(PUT /api/config)。
 * D3 读法2: 按钮是探测唯一入口(POST /api/relocate/bt_backup_probe, 无 body); D5: 歧义不猜,
 * 配置一字不动。五态前端行为(§3.2 表)是 T8a 真机验收面 —— 本 spec 钉其中浏览器可断言的三支:
 *   hit    -> 回填草稿(不自动保存) + 证据区展示; 用户点保存才落盘(审计轨迹);
 *             消歧 hit(多候选合格 + 恰一 hash 命中, probe.verdict 的 len(matched_paths)==1 形态)
 *             回填 hash 命中的候选 —— 命中者不在扫描序首位时, 取首个 qualified 会回填错路径;
 *   ambiguous -> 只列全部候选明细, 草稿一字不动(输入框保持空, actbar 不出现脏态)。
 *   (miss / unusable-sqlite / manual-set 三支的判定与文案单点在 BB_VERDICT_TEXT + 端点,
 *    静态接线由 tests/test_bt_backup_editor.py 守, 不在此重复桩形。)
 *
 * 断言面:
 *   1) 编辑器渲染在「整组迁移」块内(组件接管渲染, 块内无通用 bt_backup 行 —— hidden 生效);
 *   2) 初始空态 = 「留空 = 未启用」placeholder + 说明文案(草稿无 relocate.bt_backup 键);
 *   3) 手填路径 -> 全局保存(PUT /api/config) -> 重载回读值仍在(树形状: config.relocate.bt_backup);
 *   4) 探测 hit: 按钮回填草稿 -> actbar 出现脏态(未保存) -> 手动保存才发 PUT(审计轨迹);
 *   5) 探测 ambiguous: 证据区列出全部候选明细, 输入框与配置零改动(D5 拒不猜测);
 *   6) S3 新口径关键词在场 + 旧口径退场(块头 help, schema groups.py 单点透传);
 *   7) hit 两处分流: 消歧形态回填 hash 命中候选(非首个 qualified); 草稿已有值未回填时主行
 *      话术不声称「已回填」(bbProbe.filled 分流, 不诱导保存)。
 *
 * 桩口径(ctx-custom.spec.mjs 同款): 不往 harness 的真实 config.yml 写 —— 那是同轮其它 spec
 * 共用的临时文件, 改了会互相污染。page.route 把 /api/config 的 PUT 拦下来, 记下载荷当"已落盘",
 * GET 时把 bt_backup 注回树 —— 这正是真后端的往返语义(除了不真写盘), 重载后的回读断言由此成立。
 * 探测端点同样 page.route 拦下回合成响应(端点真实现的单测在 test_webui_relocate_chain.py,
 * 这里只验前端消费面)。运行期错误把关走 installRuntimeErrorGuard(afterEach openApp 挂采集器
 * 在 goto 之前, 全程覆盖)。
 */

/** hit 态合成响应(形状 = POST /api/relocate/bt_backup_probe 真实响应: ProbeResult 证据 + verdict)。 */
const PROBE_HIT = {
  reason: '恰一个合格候选: hash 自证通过(v1 sha1 交集 1)',
  candidates: [
    {
      path: 'C:/Users/u/AppData/Local/qBittorrent/BT_backup',
      origin: 'default-profile', suffix: '',
      qualified: true, qualification_reason: 'fastresume x3', fastresume_count: 3, has_queue: false,
      hash_matched: true, matched_ids: ['a'.repeat(40)],
    },
  ],
  notes: ['后缀枚举(来源: 配置目录): 无 _<name> 变体'],
  verdict: 'hit', online: true, manual_set: false, storage_type: 'Legacy',
};

/** ambiguous 态合成响应: 双候选合格且 hash 同中, 拒不猜测。 */
const PROBE_AMBIGUOUS = {
  reason: '多候选合格且 hash 自证不能消歧(2 候选 hash 命中)',
  candidates: [
    {
      path: 'C:/Users/u/AppData/Local/qBittorrent/BT_backup',
      origin: 'default-profile', suffix: '',
      qualified: true, qualification_reason: 'fastresume x3', fastresume_count: 3, has_queue: false,
      hash_matched: true, matched_ids: ['a'.repeat(40)],
    },
    {
      path: 'C:/Users/u/AppData/Local/qBittorrent_data/BT_backup',
      origin: 'portable', suffix: '_lab',
      qualified: true, qualification_reason: 'fastresume x2 + queue', fastresume_count: 2, has_queue: true,
      hash_matched: true, matched_ids: ['a'.repeat(40)],
    },
  ],
  notes: ['后缀枚举(来源: 配置目录): _lab 变体'],
  verdict: 'ambiguous', online: true, manual_set: false, storage_type: 'Legacy',
};

/** hit 消歧形态合成响应(probe.verdict: 多候选合格 + 恰一 hash 命中 = hit, reason 照后端措辞):
 *  hash 命中者排在候选序第二位 —— 回填必须选中它, 取首个 qualified 会回填候选一(hash 未命中)
 *  的错误路径, 用户保存即落盘错误 BT_backup 路径。 */
const PROBE_HIT_DISAMBIGUATED = {
  reason: '2 个候选合格, hash 自证消歧命中唯一: C:/qb/portable/profile/qBittorrent/data/BT_backup',
  candidates: [
    {
      path: 'C:/Users/u/AppData/Local/qBittorrent/BT_backup',
      origin: 'default-profile', suffix: '',
      qualified: true, qualification_reason: 'fastresume x2', fastresume_count: 2, has_queue: false,
      hash_matched: false, matched_ids: [],
    },
    {
      path: 'C:/qb/portable/profile/qBittorrent/data/BT_backup',
      origin: 'portable', suffix: '',
      qualified: true, qualification_reason: 'fastresume x3 + queue', fastresume_count: 3, has_queue: true,
      hash_matched: true, matched_ids: ['b'.repeat(40)],
    },
  ],
  notes: ['后缀枚举(来源: 配置目录): _lab 变体'],
  verdict: 'hit', online: true, manual_set: false, storage_type: 'Legacy',
};

test.describe('设置页 · 整组迁移 BT_backup 编辑器(S4)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 编辑器在迁移块内: 空态 -> 手填保存 -> 重载回读, 新口径在场旧口径退场`, async ({ page }) => {
      /** 服务端"已落盘"的 bt_backup 标量: PUT 收下的就是它, GET 幂等回放(往返语义见文件头)。 */
      let btBackup = null;
      /** @type {any} */
      let saved = null;

      await page.route('**/api/config', async (route) => {
        if (route.request().method() !== 'PUT') {
          /* 读树: 真实响应 + 把"已落盘"的 bt_backup 注回 relocate 段(cfgSave 保存后会重拉一次树) */
          const res = await route.fetch();
          const json = await res.json();
          if (btBackup !== null && json && json.tree && json.tree.config) {
            json.tree.config.relocate = { ...(json.tree.config.relocate || {}), bt_backup: btBackup };
          }
          return route.fulfill({ json });
        }
        saved = route.request().postDataJSON();
        btBackup = (saved && saved.tree && saved.tree.config && saved.tree.config.relocate
          && saved.tree.config.relocate.bt_backup) || '';
        return route.fulfill({ json: { changes: ['config.relocate.bt_backup'], restart_required: [] } });
      });

      await openApp(page, skin);

      /* 1) 进设置 -> 「自动化」分区(maintenance)。卡头按 .hb-card-t 标题取: 「规则」卡的 desc
         里有「自动化规则」, 裸 hasText 会双命中。 */
      await page.locator('nav.tabs-right button').first().click();
      await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
      await page.locator('.hb-card')
        .filter({ has: page.locator('.hb-card-t', { hasText: '自动化' }) })
        .click();

      /* 2) 编辑器渲染在「整组迁移」块内(挂载点 settings-detail.html: b.key === 'config.relocate'
         的块尾; 按语义标题取块, 不按位置序)。 */
      const blk = page.locator('.hb-blk')
        .filter({ has: page.locator('.bh-t', { hasText: '整组迁移' }) }).last();
      const ed = blk.locator('.bt-bk');
      await expect(ed).toBeVisible({ timeout: 15_000 });

      /* 2b) hidden 接管生效: 块内没有通用「BT_backup 目录」行(hub-field 的 hb-lb 标签), 本
         编辑器是同键唯一输入面 —— 出现两个 = schema hidden 被摘, 双输入框回归。 */
      await expect(blk.locator('.hb-lb', { hasText: 'BT_backup' })).toHaveCount(0);

      /* 3) 初始空态 = 「留空 = 未启用」placeholder + 说明文案(草稿无 relocate.bt_backup 键)。 */
      const input = ed.getByPlaceholder('留空 = 未启用, 可点自动探测');
      await expect(input).toBeVisible();
      await expect(input).toHaveValue('');
      await expect(ed).toContainText('留空 = fastresume 收尾未启用');

      /* 4) S3 新口径关键词在场(块头 help .bh-n, schema groups.py 单点透传)。 */
      await expect(blk.locator('.bh-n')).toContainText('下线窗口');
      await expect(blk.locator('.bh-n')).toContainText('可直接再迁');
      await expect(blk.locator('.bh-n')).toContainText('fastresume');

      /* 5) 旧口径退场: 收尾机制换 fastresume 双键改写后, 这两个词不许再出现在设置页
         (body textContent 口径 —— x-template/隐藏残留也在 DOM 里, 一起抓)。 */
      await expect(page.locator('body')).not.toContainText('setLocation 收尾');
      await expect(page.locator('body')).not.toContainText('拒绝再迁');

      /* 6) 手填路径 -> 全局 actbar「保存并应用」(cfgSave, PUT 整树)。 */
      const actbar = page.locator('.hb-actbar');
      await expect(actbar).toContainText('已与磁盘同步', { timeout: 20_000 });
      await input.fill('D:/qb/BT_backup');
      await expect(actbar).toContainText('有改动还没保存');

      await actbar.locator('.hb-btn.primary').click();
      await expect.poll(() => saved, { message: 'PUT /api/config 未发出', timeout: 15_000 }).not.toBeNull();
      expect(saved.tree.config.relocate.bt_backup, '标量写回形状: relocate.bt_backup 单路径')
        .toBe('D:/qb/BT_backup');
      /* 保存成功回执: fresh GET 注回了同值 -> 树==基线, 脏态清掉(这条同时证明保存链走完)。 */
      await expect(actbar).toContainText('已与磁盘同步', { timeout: 15_000 });

      /* 7) 回读: 重载后值仍在(编辑草稿不另存, 磁盘值经 GET 注回 = 真后端往返语义)。
         位置持久化是既有产品行为(views.spec「设置页刷新保持位置」钉过): 重载后直接落回
         自动化分区, 编辑器可见即 cfg 树已回来; 到不了就是持久化/恢复链坏了, 该红。 */
      await page.reload({ waitUntil: 'domcontentloaded' });
      const ed2 = page.locator('.hb-blk')
        .filter({ has: page.locator('.bh-t', { hasText: '整组迁移' }) }).last()
        .locator('.bt-bk');
      await expect(ed2).toBeVisible({ timeout: 20_000 });
      await expect(ed2.getByPlaceholder('留空 = 未启用, 可点自动探测')).toHaveValue('D:/qb/BT_backup');
    });

    test(`[${skin}] 探测 hit: 回填草稿不落盘, 手动保存才发 PUT(审计轨迹)`, async ({ page }) => {
      let btBackup = null;
      /** @type {any} */
      let saved = null;

      await page.route('**/api/config', async (route) => {
        if (route.request().method() !== 'PUT') {
          const res = await route.fetch();
          const json = await res.json();
          if (btBackup !== null && json && json.tree && json.tree.config) {
            json.tree.config.relocate = { ...(json.tree.config.relocate || {}), bt_backup: btBackup };
          }
          return route.fulfill({ json });
        }
        saved = route.request().postDataJSON();
        btBackup = (saved && saved.tree && saved.tree.config && saved.tree.config.relocate
          && saved.tree.config.relocate.bt_backup) || '';
        return route.fulfill({ json: { changes: ['config.relocate.bt_backup'], restart_required: [] } });
      });
      await page.route('**/api/relocate/bt_backup_probe', (route) => route.fulfill({ json: PROBE_HIT }));

      await openApp(page, skin);

      await page.locator('nav.tabs-right button').first().click();
      await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
      await page.locator('.hb-card')
        .filter({ has: page.locator('.hb-card-t', { hasText: '自动化' }) })
        .click();

      const actbar = page.locator('.hb-actbar');
      await expect(actbar).toContainText('已与磁盘同步', { timeout: 20_000 });
      const ed = page.locator('.hb-blk')
        .filter({ has: page.locator('.bh-t', { hasText: '整组迁移' }) }).last()
        .locator('.bt-bk');
      const input = ed.getByPlaceholder('留空 = 未启用, 可点自动探测');
      await expect(input).toHaveValue('');

      /* 点「自动探测」-> hit: 输入框回填草稿 + 证据区给候选明细; actbar 出现脏态 =
         探测没有替用户落盘(端点零配置写 + 前端只写草稿), 保存链在用户手里(审计轨迹)。 */
      await ed.getByRole('button', { name: '自动探测' }).click();
      await expect(input).toHaveValue(PROBE_HIT.candidates[0].path);
      const ev = ed.locator('.bt-bk-ev');
      await expect(ev).toContainText('已探测到 BT_backup 目录');
      await expect(ev).toContainText(PROBE_HIT.candidates[0].path);
      await expect(ev).toContainText('hash 自证命中');
      await expect(actbar).toContainText('有改动还没保存');

      /* 手动保存 -> PUT 载荷里就是回填的路径(探测结果经草稿进盘, 无第二条写路径)。 */
      await actbar.locator('.hb-btn.primary').click();
      await expect.poll(() => saved, { message: 'PUT /api/config 未发出', timeout: 15_000 }).not.toBeNull();
      expect(saved.tree.config.relocate.bt_backup).toBe(PROBE_HIT.candidates[0].path);
      await expect(actbar).toContainText('已与磁盘同步', { timeout: 15_000 });

      /* 第二轮探测(草稿已有值): 保守默认 = 不覆盖用户草稿, 证据区明示「未覆盖」。主行话术按
         filled 分流: 未回填的 hit 主行不再声称「已回填」—— 与实际行为一致, 不诱导保存。
         (桩仍回同一 hit; 输入框值不变即草稿零写入 —— 探测不静默丢用户输入。) */
      await ed.getByRole('button', { name: '自动探测' }).click();
      await expect(ev).toContainText('草稿已有值, 探测结果未覆盖');
      await expect(ev).not.toContainText('已回填');
      await expect(input).toHaveValue(PROBE_HIT.candidates[0].path);
    });

    test(`[${skin}] 探测 hit 消歧形态: 多候选合格恰一 hash 命中, 回填 hash 命中者(非首个 qualified)`, async ({ page }) => {
      let btBackup = null;
      /** @type {any} */
      let saved = null;

      await page.route('**/api/config', async (route) => {
        if (route.request().method() !== 'PUT') {
          const res = await route.fetch();
          const json = await res.json();
          if (btBackup !== null && json && json.tree && json.tree.config) {
            json.tree.config.relocate = { ...(json.tree.config.relocate || {}), bt_backup: btBackup };
          }
          return route.fulfill({ json });
        }
        saved = route.request().postDataJSON();
        btBackup = (saved && saved.tree && saved.tree.config && saved.tree.config.relocate
          && saved.tree.config.relocate.bt_backup) || '';
        return route.fulfill({ json: { changes: ['config.relocate.bt_backup'], restart_required: [] } });
      });
      await page.route('**/api/relocate/bt_backup_probe', (route) => route.fulfill({ json: PROBE_HIT_DISAMBIGUATED }));

      await openApp(page, skin);

      await page.locator('nav.tabs-right button').first().click();
      await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
      await page.locator('.hb-card')
        .filter({ has: page.locator('.hb-card-t', { hasText: '自动化' }) })
        .click();

      const actbar = page.locator('.hb-actbar');
      await expect(actbar).toContainText('已与磁盘同步', { timeout: 20_000 });
      const ed = page.locator('.hb-blk')
        .filter({ has: page.locator('.bh-t', { hasText: '整组迁移' }) }).last()
        .locator('.bt-bk');
      const input = ed.getByPlaceholder('留空 = 未启用, 可点自动探测');
      await expect(input).toHaveValue('');

      /* 消歧 hit: hash 命中者排在候选序第二位 —— 回填必须选中它, 而非首个合格候选(取首个
         qualified 会把 hash 未命中的候选一路径回填, 用户保存即落盘错误 BT_backup 路径)。 */
      const hitPath = PROBE_HIT_DISAMBIGUATED.candidates[1].path;
      await ed.getByRole('button', { name: '自动探测' }).click();
      await expect(input).toHaveValue(hitPath);
      const ev = ed.locator('.bt-bk-ev');
      await expect(ev).toContainText('消歧');
      await expect(ev).toContainText(hitPath);
      await expect(actbar).toContainText('有改动还没保存');

      /* 保存载荷里就是 hash 命中候选的路径(消歧结果经草稿进盘, hash 未命中的错误候选不得进盘)。 */
      await actbar.locator('.hb-btn.primary').click();
      await expect.poll(() => saved, { message: 'PUT /api/config 未发出', timeout: 15_000 }).not.toBeNull();
      expect(saved.tree.config.relocate.bt_backup).toBe(hitPath);
      await expect(actbar).toContainText('已与磁盘同步', { timeout: 15_000 });
    });

    test(`[${skin}] 探测 ambiguous: 证据区列全部候选, 草稿一字不动(D5 拒不猜测)`, async ({ page }) => {
      /** @type {any} */
      let saved = null;

      await page.route('**/api/config', async (route) => {
        if (route.request().method() !== 'PUT') {
          const res = await route.fetch();
          return route.fulfill({ json: await res.json() });
        }
        saved = route.request().postDataJSON();
        return route.fulfill({ json: { changes: [], restart_required: [] } });
      });
      await page.route('**/api/relocate/bt_backup_probe', (route) => route.fulfill({ json: PROBE_AMBIGUOUS }));

      await openApp(page, skin);

      await page.locator('nav.tabs-right button').first().click();
      await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
      await page.locator('.hb-card')
        .filter({ has: page.locator('.hb-card-t', { hasText: '自动化' }) })
        .click();

      const actbar = page.locator('.hb-actbar');
      await expect(actbar).toContainText('已与磁盘同步', { timeout: 20_000 });
      const ed = page.locator('.hb-blk')
        .filter({ has: page.locator('.bh-t', { hasText: '整组迁移' }) }).last()
        .locator('.bt-bk');
      const input = ed.getByPlaceholder('留空 = 未启用, 可点自动探测');
      await expect(input).toHaveValue('');

      /* ambiguous: 证据区列全部候选明细 + 拒不猜测话术; 输入框保持空 = 配置一字不动,
         actbar 保持同步态 = 无草稿写入(也就不会有 PUT 发出)。 */
      await ed.getByRole('button', { name: '自动探测' }).click();
      const ev = ed.locator('.bt-bk-ev');
      await expect(ev).toContainText('无法消歧');
      for (const c of PROBE_AMBIGUOUS.candidates) {
        await expect(ev).toContainText(c.path);
      }
      await expect(input).toHaveValue('');
      await expect(actbar).toContainText('已与磁盘同步');
      expect(saved, 'ambiguous 态不得发出 PUT(配置一字不动)').toBeNull();
    });
  }
});
