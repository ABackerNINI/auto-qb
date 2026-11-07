// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';

/**
 * 设置页 · 「自动化」分区 · 「整组迁移」块的 BT_backup 路径表编辑器(S5, 计划 26-11-07-0708)。
 *
 * 背景(计划 §02/§04): config.bt_backup 键全链在(schema/models/loaders/validate)但 hidden=True,
 * 通用编辑树不渲染(cfgFlatten 单点跳过) —— S2 起由 <aq-bt-backup-editor>(shared/bt_backup_editor.js
 * + tpl/bt-backup-editor.html)接管, 挂在 settings-detail.html config.relocate 块尾。此前 e2e 30+
 * spec 没有任何设置页专项浏览器级断言(计划 §02 点名的结构性空档), 本文件补上这一层。
 *
 * 断言面(计划 §04/S5 验收行 + 任务提示补充):
 *   1) 编辑器渲染在「整组迁移」块内(组件接管渲染);
 *   2) 初始空表 = 「功能未启用」空态文案(桩种子 config 无 bt_backup 键 = 未配置);
 *   3) 增行(host:port + 路径) -> 全局保存(PUT /api/config) -> 重载回读值仍在;
 *   4) S3 新口径关键词在场: 「下线窗口」「可直接再迁」「fastresume」(块头 help, schema
 *      groups.py 单点透传 —— 取短词, 不押易改写的长句);
 *   5) 旧口径退场: 「setLocation 收尾」「拒绝再迁」不再出现在设置页 DOM(textContent 口径,
 *      连隐藏残留一起抓);
 *   6) 撞键拒绝: 第二行键改成与第一行相同 -> 只 toast 不写树, 输入框回到该行树真值
 *      (bbSetKey 撞键分支的回弹机制, 键序与保存载荷不受键入脏文本影响)。
 *
 * 桩口径(ctx-custom.spec.mjs 同款): 不往 harness 的真实 config.yml 写 —— 那是同轮其它 spec
 * 共用的临时文件, 改了会互相污染。page.route 把 /api/config 的 PUT 拦下来, 记下载荷当"已落盘",
 * GET 时把 bt_backup 注回树 —— 这正是真后端的往返语义(除了不真写盘), 重载后的回读断言由此成立。
 * 运行期错误把关走 installRuntimeErrorGuard afterEach(openApp 挂采集器在 goto 之前, 全程覆盖)。
 */
test.describe('设置页 · 整组迁移 BT_backup 路径表(S5)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 编辑器在迁移块内: 空态 -> 增行保存 -> 重载回读, 新口径在场旧口径退场`, async ({ page }) => {
      /** 服务端"已落盘"的 bt_backup 映射: PUT 收下的就是它, GET 幂等回放(往返语义见文件头)。 */
      /** @type {Record<string, string> | null} */
      let btBackup = null;
      /** @type {any} */
      let saved = null;

      await page.route('**/api/config', async (route) => {
        if (route.request().method() !== 'PUT') {
          /* 读树: 真实响应 + 把"已落盘"的 bt_backup 注回去(cfgSave 保存后会重拉一次树) */
          const res = await route.fetch();
          const json = await res.json();
          if (btBackup && json && json.tree && json.tree.config) {
            json.tree.config.bt_backup = { ...btBackup };
          }
          return route.fulfill({ json });
        }
        saved = route.request().postDataJSON();
        btBackup = (saved && saved.tree && saved.tree.config && saved.tree.config.bt_backup) || null;
        return route.fulfill({ json: { changes: ['config.bt_backup'], restart_required: [] } });
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

      /* 3) 初始空表 = 「功能未启用」空态(模板 bt-backup-editor.html 实际文案)。 */
      await expect(ed).toContainText('fastresume 收尾功能整体未启用');

      /* 4) S3 新口径关键词在场(块头 help .bh-n, schema groups.py:435-437 单点透传)。 */
      await expect(blk.locator('.bh-n')).toContainText('下线窗口');
      await expect(blk.locator('.bh-n')).toContainText('可直接再迁');
      await expect(blk.locator('.bh-n')).toContainText('fastresume');

      /* 5) 旧口径退场: 收尾机制换 fastresume 双键改写后, 这两个词不许再出现在设置页
         (body textContent 口径 —— x-template/隐藏残留也在 DOM 里, 一起抓)。 */
      await expect(page.locator('body')).not.toContainText('setLocation 收尾');
      await expect(page.locator('body')).not.toContainText('拒绝再迁');

      /* 6) 增行 -> 填 host:port + 路径 -> 全局 actbar「保存并应用」(cfgSave, PUT 整树)。 */
      const actbar = page.locator('.hb-actbar');
      await expect(actbar).toContainText('已与磁盘同步', { timeout: 20_000 });
      await ed.getByRole('button', { name: '+ 新增实例' }).click();
      await ed.getByPlaceholder('host:port').fill('127.0.0.1:8080');
      await ed.getByPlaceholder('该实例的 BT_backup 目录路径').fill('D:/qb/BT_backup');
      await expect(actbar).toContainText('有改动还没保存');

      await actbar.locator('.hb-btn.primary').click();
      await expect.poll(() => saved, { message: 'PUT /api/config 未发出', timeout: 15_000 }).not.toBeNull();
      expect(saved.tree.config.bt_backup, '映射写回形状: host:port -> 路径(整对象替换)')
        .toEqual({ '127.0.0.1:8080': 'D:/qb/BT_backup' });
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
      await expect(ed2.getByPlaceholder('host:port')).toHaveValue('127.0.0.1:8080');
      await expect(ed2.getByPlaceholder('该实例的 BT_backup 目录路径')).toHaveValue('D:/qb/BT_backup');
      /* 有条目后空态退场 */
      await expect(ed2).not.toContainText('fastresume 收尾功能整体未启用');
    });

    test(`[${skin}] 撞键拒绝: 只 toast 不写树, 输入框回弹该行树真值`, async ({ page }) => {
      /** 预置两条实例: 拒绝路径要有"已存在的同名键"可撞, 第二行改名撞第一行。 */
      let btBackup = { '127.0.0.1:8080': 'D:/qb/BT_backup', '127.0.0.1:8081': 'D:/qb/BT_backup2' };
      /** @type {any} */
      let saved = null;

      await page.route('**/api/config', async (route) => {
        if (route.request().method() !== 'PUT') {
          const res = await route.fetch();
          const json = await res.json();
          if (btBackup && json && json.tree && json.tree.config) {
            json.tree.config.bt_backup = { ...btBackup };
          }
          return route.fulfill({ json });
        }
        saved = route.request().postDataJSON();
        btBackup = (saved && saved.tree && saved.tree.config && saved.tree.config.bt_backup) || null;
        return route.fulfill({ json: { changes: ['config.bt_backup'], restart_required: [] } });
      });

      await openApp(page, skin);

      await page.locator('nav.tabs-right button').first().click();
      await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
      await page.locator('.hb-card')
        .filter({ has: page.locator('.hb-card-t', { hasText: '自动化' }) })
        .click();

      const ed = page.locator('.hb-blk')
        .filter({ has: page.locator('.bh-t', { hasText: '整组迁移' }) }).last()
        .locator('.bt-bk');
      await expect(ed).toBeVisible({ timeout: 15_000 });

      const keys = ed.getByPlaceholder('host:port');
      await expect(keys).toHaveCount(2, { timeout: 15_000 });
      await expect(keys.nth(0)).toHaveValue('127.0.0.1:8080');
      await expect(keys.nth(1)).toHaveValue('127.0.0.1:8081');

      /* 第二行键入第一行的 host:port -> 撞键: toast 说明 + 树不动(拒绝写入)。 */
      await keys.nth(1).fill('127.0.0.1:8080');
      const toast = page.locator('.toast-wrap .toast.timeout');
      await expect(toast, '撞键必须给 toast 说明').toBeVisible({ timeout: 10_000 });
      await expect(toast).toContainText('实例地址重复');

      /* 回弹: 输入框回到该行树真值(8081), 不是用户刚键入的撞键文本(8080)。 */
      await expect(keys.nth(1)).toHaveValue('127.0.0.1:8081');

      /* 树真值未被动过: 后续正常改路径保存, 载荷里键序与两条键都原样。 */
      await ed.getByPlaceholder('该实例的 BT_backup 目录路径').nth(1).fill('D:/qb/BT_backup2b');
      const actbar = page.locator('.hb-actbar');
      await actbar.locator('.hb-btn.primary').click();
      await expect.poll(() => saved, { message: 'PUT /api/config 未发出', timeout: 15_000 }).not.toBeNull();
      expect(saved.tree.config.bt_backup, '撞键脏文本不得泄漏进保存载荷')
        .toEqual({ '127.0.0.1:8080': 'D:/qb/BT_backup', '127.0.0.1:8081': 'D:/qb/BT_backup2b' });
    });
  }
});
