// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { readInst } from './lib/vm.mjs';

/**
 * 设置页 · 规则分区 · 条件组合树编辑器的注入回归(坑档 mixin-ce-inject-break 的第二现场钉面)。
 *
 * 背景(2026-11-11 用户报障): 全局 mixin(CONFIG_EDITOR)给**每个**组件都挂 provide(){ce:this},
 * 条件树宿主组件 aq-cond-node / aq-choose-block 此前缺 `inject:["ce"]` + provide 透传 —— 内嵌
 * hub-field 注入到中间实例(mixin data 新建的 cfg 副本, tree=null): 条件叶子列表「＋ 添加」抛
 * TypeError 被吞(按钮"无反应")、「?」说明浮窗开不出来、叶子字段读值恒显默认值/编辑写坏副本
 * 全丢。机理与 traffic-card 的 aq-fold 事故同款(pitfalls/web-ui/mixin-ce-inject-break.md)。
 *
 * 断言面(按坑档守阵教训: 必须钉**非缺省态**与**写路径往返**, 默认态断言对注入断裂恒真零鉴别力):
 *   1) 建规则集 + 规则(真实手势, 全程只动客户端草稿树不落盘 —— 不污染桩的临时 config.yml);
 *   2) 条件叶子写路径: 根级选「路径」(列表型) -> 点叶子「＋ 添加」出输入行 -> 输入值 ->
 *      vm 草稿树断言 path == [值](写坏副本时树恒空, 该红);
 *   3) 「?」说明浮窗: 点叶子行 ? -> .hb-pop.on 可见 -> 再点同钮关闭(toggle);
 *   4) choose 第二现场: 分支(choose) -> when 树加「标签」叶子 -> then 加「添加标签」动作 ->
 *      vm 草稿树断言 choose.then[0] 是规范形 {type, params, on_error}; 再点 then 动作卡列表
 *      「＋ 添加」+ 填值(aq-choose-block **自身** ce 链的写路径, 与 2/3 步 aq-cond-node 现场
 *      互相独立 —— 单回退任一组件各有红灯, 见坑档守阵判据)。
 * 运行期错误把关走 installRuntimeErrorGuard(修复前「＋ 添加」的 TypeError 在此必红)。
 * vm 探针口径(lib/vm.mjs D4 守则): 草稿树与 helpKey 是 vm 内部状态、无 DOM 取径(草稿不落盘),
 * 属第 2 类探针; 其余交互一律真实手势。
 */
test.describe('设置页 · 规则条件组合树编辑器(ce 注入回归)', () => {
  installRuntimeErrorGuard(test);

  /** 建规则集 + 规则(对话框真实手势); 规则集名直接带 _rules 后缀(输入框会自动补, 带了不重复)。 */
  async function createRule(page, group, rule) {
    await page.getByRole('button', { name: '＋ 新增规则集' }).click();
    await page.locator('.modal-input').fill(group);
    await page.locator('.modal-actions button', { hasText: '添加' }).click();
    await expect(page.getByRole('button', { name: '＋ 新增规则', exact: true })).toBeVisible();
    await page.getByRole('button', { name: '＋ 新增规则', exact: true }).click();
    await page.locator('.modal-input').fill(rule);
    await page.locator('.modal-actions button', { hasText: '添加' }).click();
    await expect(page.locator('.hb-rule-hd', { hasText: rule })).toBeVisible({ timeout: 15_000 });
  }

  /** 读规则集草稿树(vm 内部探针, 第 2 类): 草稿只存在客户端 cfg 树, 无 DOM/服务端取径。 */
  const rulesDraft = (page, group) =>
    readInst(page, `(vm.cfg.tree && vm.cfg.tree.config ? JSON.parse(JSON.stringify(vm.cfg.tree.config[${JSON.stringify(group)}] || null)) : null)`);

  for (const skin of SKINS) {
    test(`[${skin}] 叶子列表写路径往返 + ? 浮窗 + choose 第二现场 @fast`, async ({ page }) => {
      const group = 'e2e_inject_rules';
      const rule = 'cond_regress';

      await openApp(page, skin);
      await page.locator('nav.tabs-right button').first().click();
      await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
      /* 「规则」卡按标题取: 卡 desc 含「自动化规则」, 裸 hasText 会命中其它卡(bt-backup 同款纪律) */
      await page.locator('.hb-card')
        .filter({ has: page.locator('.hb-card-t', { hasText: '规则' }) })
        .filter({ hasNot: page.locator('.hb-card-t', { hasText: '自动化' }) })
        .click();
      await expect(page.getByRole('button', { name: '＋ 新增规则集' })).toBeVisible({ timeout: 15_000 });

      await createRule(page, group, rule);

      /* 2) 条件叶子写路径: 根级「添加条件」选「路径」(列表型 spec_kind=list) -> 叶子卡出现 */
      const rootSel = page.locator('select.hb-select', { hasText: '添加条件' }).first();
      await rootSel.selectOption({ label: '路径' });
      const leaf = page.locator('.hb-cond-node .hb-step').first();
      await expect(leaf).toBeVisible({ timeout: 15_000 });

      /* 叶子「＋ 添加」(列表控件): 修复前点击抛 TypeError(console.error)且树不写 -> 双红 */
      await leaf.locator('.hb-list button', { hasText: '添加' }).click();
      const rowInput = leaf.locator('.hb-list .hb-input').first();
      await expect(rowInput).toBeVisible({ timeout: 15_000 });
      await rowInput.fill('/data/movies');

      const draft = await rulesDraft(page, group);
      expect(draft?.[rule]?.conditions?.all?.[0]?.path, '叶子列表写路径往返(写坏副本时树恒空)')
        .toEqual(['/data/movies']);

      /* 3) 「?」说明浮窗: 打开(.hb-pop.on) -> helpKey 命中叶子路径 -> 再点关闭 */
      const ask = leaf.locator('.hb-ask');
      await ask.click();
      const pop = page.locator('.hb-pop.on');
      await expect(pop).toBeVisible({ timeout: 15_000 });
      const helpKey = await readInst(page, 'vm.hub.helpKey');
      expect(helpKey, '? 浮窗的 helpKey 指向叶子路径(坏副本上恒空串)').toBe(
        `config.${group}.${rule}.conditions.all.0.path`);
      await ask.click();
      await expect(pop).not.toBeVisible({ timeout: 15_000 });

      /* 4) choose 第二现场(then 里也嵌 hub-field): 加分支 -> when 加「标签」叶子 -> then 加「添加标签」 */
      await page.getByRole('button', { name: '＋ 分支(choose)' }).click();
      const choose = page.locator('.hb-choose').first();
      await expect(choose).toBeVisible({ timeout: 15_000 });
      await choose.locator('select.hb-select', { hasText: '添加条件' }).first()
        .selectOption({ label: '标签' });
      await expect(choose.locator('.hb-cond-node .hb-step').first()).toBeVisible({ timeout: 15_000 });
      await choose.locator('select.hb-select', { hasText: '添加动作' }).first()
        .selectOption({ label: '添加标签' });

      /* ce 介面写路径(守阵判据, 见头注): then 动作卡(add_tags 是列表型)的 spec 控件
       * 直接渲染在 aq-choose-block 自身模板里(rule-tree.html:103), 它的「＋ 添加」走
       * listAdd -> this.ce.cfgItemAdd —— 回退 aq-choose-block 透传时此步坏副本上抛
       * TypeError(console 守卫红)且草稿树不写(下方 params 断言红), 与第 2/3 步
       * (aq-cond-node 现场)互相独立, 单回退任一组件各有红灯。 */
      const thenCard = choose.locator('.hb-branch-then .hb-step').first();
      await expect(thenCard).toBeVisible({ timeout: 15_000 });
      await thenCard.locator('.hb-list button', { hasText: '添加' }).click();
      await thenCard.locator('.hb-list .hb-input').first().fill('e2e-tag');

      const draft2 = await rulesDraft(page, group);
      const then0 = draft2?.[rule]?.actions?.[0]?.choose?.[0]?.then?.[0];
      expect(then0?.type, 'choose then 动作写树(规范形)').toBe('add_tags');
      expect(then0?.on_error?.policy, 'choose then 动作缺省 on_error 注入').toBe('stop');
      expect(then0?.params, 'then 动作卡列表写路径往返(aq-choose-block 自身 ce 链)')
        .toEqual(['e2e-tag']);
    });
  }
});
