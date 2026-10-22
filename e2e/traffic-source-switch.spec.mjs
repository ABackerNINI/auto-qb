// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';

/**
 * 「流量与限速 → 数据来源」总开关的 ce 注入链守阵 —— issue 26-10-22-0435 回归栅。
 *
 * 事故(2026-10-22, 用户报障「关闭工具后界面仍显示启用、切换无法保存、重启无效」):
 * 回归点 6ad07b6a 把折叠段头从普通 div 换成 <aq-fold> 组件后, 插槽里的 <hub-field>
 * 注入到了 **aq-fold 组件实例** —— 全局 mixin(CONFIG_EDITOR)给每个组件都挂了
 * provide(){ce:this} 与 data() 的空 cfg 树(tree=null), 而 aq-fold 没把注入到的 ce
 * 透传下去:
 *   · 读: 磁盘 traffic_source.enabled="false", 开关恒显「启用」还带「默认」徽标(回落
 *     schema 默认 true); 卡头摘要/依赖提示条走 $root.tmSourceOff() 读**根**树, 显示
 *     「来源已关闭」—— 开关与横幅自相矛盾, 即用户看到的「GET /api/config 里 false、
 *     界面里启用」;
 *   · 写: 拨动写进那个空树(cfgSetPath 在 tree=null 上 TypeError), 根树不脏、
 *     「保存并应用」永不出现、磁盘不动(重启无效)。
 * 修复(ctl_bits.js 的 AQ_FOLD_COMPONENT 补 inject+provide 透传, 与 aq-traffic-card /
 * CE_FIELD_BASE 同范式)后, 本 spec 钉读路径与写路径两条, 断裂时任一条必红。
 *
 * 为什么既有守卫没拦住: views.spec「三区同屏」那条只断言「启用」勾选反映 **schema 缺省
 * true** —— 与注入断裂后的回落值同形, 恒真(假信心); 本 spec 钉**非缺省态**(磁盘 false)
 * 与**写路径往返**, 才是断裂时真的会红的判据。
 *
 * 第二现场(「规则卡」那条 describe): 同一个 <aq-fold> 也包着规则卡「触发与节奏」段的
 * hub-field(settings.html:237), 断裂时段内字段同样只显 schema 默认值 —— 同机制不同调用面,
 * 一并钉住, 免得下次只在流量卡这一处修。(通用分区块的 object 段不走 aq-fold —— 那是
 * settings-detail.html 的平铺块, 本就不经注入链, 无第二现场之虞。)
 *
 * 桩口径(ctx-custom.spec 同款纪律): 不写 harness 共享的 config.yml(同轮其它 spec 会读到),
 * 用 page.route 把 /api/config 的 GET/PUT 拦下来造一份"磁盘" —— GET 可注入键值(模拟用户
 * 手改配置后重启), PUT 记下载荷并回放(闭环 cfgSave 保存后的重拉)。掩码/版本章/往返语义
 * 原样保留: 拦的只是"写到哪", 不是"怎么走"。
 */

/** 来源区总开关行(data-hb-key = hubKey(path) = 路径点分, config_editor 单点) */
const ENABLED_ROW = '.hb-row[data-hb-key="config.traffic_source.enabled"]';

/**
 * "磁盘"模拟器: 拦 /api/config 的 GET/PUT。
 *   · GET: 首次取真树后把 inject 的键值对点分路径写进去(此后恒回放同一份, reload 也看到);
 *   · PUT: 记下载荷进 puts, 并把它当"已落盘"回放(cfgSave 保存后会重拉一次树)。
 * @param {import('@playwright/test').Page} page
 * @param {Record<string, string>} inject —— 点分路径 -> 值(字符串: 磁盘树是 YAML 全字符串口径)
 * @returns {Promise<{puts: any[]}>} PUT 载荷列表(写路径断言读它)
 */
async function stubDisk(page, inject) {
  /** @type {any[]} */
  const puts = [];
  /** @type {any} */
  let disk = null;
  await page.route('**/api/config', async (route) => {
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON();
      puts.push(body);
      disk = body.tree;
      return route.fulfill({ json: { applied: true, changes: [], restart_required: [] } });
    }
    const json = await (await route.fetch()).json();
    if (!disk) {
      disk = json.tree;
      disk.config = disk.config || {};
      for (const [path, value] of Object.entries(inject || {})) {
        const segs = path.split('.');
        let node = disk;
        for (const s of segs.slice(0, -1)) {
          if (node[s] === null || typeof node[s] !== 'object') node[s] = {};
          node = node[s];
        }
        node[segs[segs.length - 1]] = value;
      }
    }
    return route.fulfill({ json: Object.assign({}, json, { tree: disk }) });
  });
  return { puts };
}

/** 进设置 → 指定分区卡, 等配置树加载完(actbar 回同步态 = schema+tree 都到了) */
async function enterHubCard(page, skin, cardText) {
  await openApp(page, skin);
  await page.locator('nav.tabs-right button').first().click(); // 顶栏右侧「设置」
  await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
  await page.locator('.hb-card', { hasText: cardText }).first().click();
  await expect(page.locator('.hb-actbar')).toContainText('已与磁盘同步', { timeout: 20_000 });
}

test.describe('流量与限速 · 数据来源开关(aq-fold ce 透传守阵 · 读/写)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 读路径: 磁盘 enabled=false → 开关显关闭、无默认徽标、与摘要同判, 刷新后仍关闭 @fast`, async ({ page }) => {
      /* 字符串 "false" 而非布尔 false: 磁盘树是 YAML BaseLoader 全字符串口径(GET 响应即如此),
         注入值必须与真磁盘同构, 否则测的是另一种树 */
      await stubDisk(page, { 'config.traffic_source.enabled': 'false' });
      await enterHubCard(page, skin, '流量与限速');

      /* 读路径主断言: 磁盘说 false, 开关就必须是关闭态 —— 注入断裂时这里恒显「启用」
         +「默认」徽标(回落 schema 默认), 而下面两条根树读数显示「已关闭」, 自相矛盾现形 */
      const row = page.locator(ENABLED_ROW);
      await expect(row, '来源区找不到 traffic_source.enabled 行(折叠段没展开?)').toBeVisible({ timeout: 10_000 });
      await expect(row.locator('.hb-switch input[type=checkbox]')).not.toBeChecked();
      await expect(row.locator('.hb-sw-text')).toHaveText('关闭');
      await expect(row.locator('.hb-lb .hb-badge'),
        '磁盘上明明有值却被打上「默认」徽标 —— 回落 schema 默认值的签名').toHaveCount(0);

      /* 自相矛盾不再现: 卡头摘要与依赖提示条走根树, 现在必须与开关同判「已关闭」 */
      await expect(page.locator('.hb-tl-sum')).toHaveText('来源已关闭');
      await expect(page.locator('.hb-tl-dep')).toContainText('流量来源已关闭');

      /* 「重启无效」症状: 刷新页面(整棵配置树重拉)后仍是关闭态。
         hub.view 持久化在 localStorage, 刷新后多半直接落回流量卡; 万一被复位到卡片总览,
         补一次点卡(与 ctx-custom.spec 同款兜底, 不把"回得去"写死在断言里) */
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect.poll(async () => {
        if (await page.locator(ENABLED_ROW).isVisible().catch(() => false)) return 'card';
        if (await page.locator('.hb-grid .hb-card').first().isVisible().catch(() => false)) return 'grid';
        return '';
      }, { message: '刷新后: 设置页未还原(既没回流量卡也没回卡片总览)', timeout: 20_000 }).not.toBe('');
      if (!(await page.locator(ENABLED_ROW).isVisible().catch(() => false))) {
        await page.locator('.hb-card', { hasText: '流量与限速' }).first().click();
      }
      await expect(page.locator('.hb-actbar')).toContainText('已与磁盘同步', { timeout: 20_000 });
      await expect(page.locator(ENABLED_ROW).locator('.hb-sw-text')).toHaveText('关闭');
      await expect(page.locator(ENABLED_ROW).locator('.hb-switch input[type=checkbox]')).not.toBeChecked();
    });

    test(`[${skin}] 写路径: 拨动开关 → 脏标记出现 → 保存并应用 → PUT 载荷 enabled=false → 保存后仍关闭 @fast`, async ({ page }) => {
      /* 不注入: 桩配置里没有 traffic_source 段, enabled 缺省 true ⇒ 开关初态「启用」,
         这正是要拨动的那一格 */
      const stub = await stubDisk(page, {});
      await enterHubCard(page, skin, '流量与限速');

      const row = page.locator(ENABLED_ROW);
      await expect(row).toBeVisible({ timeout: 10_000 });
      const track = row.locator('.hb-sw-track'); // input 是 0x0 opacity:0(见 console_hub.css), 可点的是轨道
      await expect(row.locator('.hb-switch input[type=checkbox]')).toBeChecked();
      await expect(row.locator('.hb-sw-text')).toHaveText('启用');

      /* 拨动: 注入断裂时这一击写进的是 aq-fold 实例的空树(cfgSetPath 在 tree=null 上
         TypeError), 根树不脏 ⇒ 下面两条恒不过; 开关还会被回落值当场复位 */
      await track.click();
      await expect(page.locator('.hb-actbar')).toContainText('有改动还没保存');
      await expect(row.locator('.hb-switch input[type=checkbox]'),
        '拨动后开关被回落值复位 —— 写入没进根树的签名').not.toBeChecked();

      await page.locator('.hb-actbar .hb-btn.primary').click();
      await expect.poll(() => stub.puts.length, { message: 'PUT /api/config 未发出', timeout: 15_000 }).toBeGreaterThan(0);
      expect(stub.puts[0].tree.config.traffic_source.enabled,
        'PUT 载荷里没有 enabled=false —— 拨动没写进根树').toBe('false');

      /* 保存后重拉的树回放 enabled=false: 开关仍是关闭态, actbar 回同步态 */
      await expect(page.locator('.hb-actbar')).toContainText('已与磁盘同步', { timeout: 15_000 });
      await expect(row.locator('.hb-switch input[type=checkbox]')).not.toBeChecked();
    });
  }
});

/* 第二现场: 规则卡「触发与节奏」折叠段(settings.html:237)把 hub-field 包在同一个
 * <aq-fold> 里, 断裂时段内字段同样只显 schema 默认值。这里用枚举字段「执行一次」
 * (schema 默认 "never")钉一次: 磁盘显式 "daily" ⇒ 下拉必须显 daily; 断裂时回落
 * 默认 "never"。规则集经 route 桩注入(桩配置里没有规则, 见上方桩口径)。 */
test.describe('设置页 · 规则卡「触发与节奏」(aq-fold ce 透传守阵 · 第二现场)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 规则卡 meta 段: 磁盘 execute_once=daily → 段内下拉显 daily @fast`, async ({ page }) => {
      await stubDisk(page, { 'config.demo_rules.demo.execute_once': 'daily' });
      await openApp(page, skin);
      await page.locator('nav.tabs-right button').first().click();
      await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
      /* 按卡标题精确取: 「规则」二字也出现在站点/HR 卡的描述里, hasText 会多命中 */
      await page.locator('.hb-card', { has: page.locator('.hb-card-t', { hasText: /^规则$/ }) }).first().click();
      await expect(page.locator('.hb-actbar')).toContainText('已与磁盘同步', { timeout: 20_000 });

      /* 进分区即自动选中首个规则集(hubGo 的 rules 分支); 规则卡与折叠段头随之渲染 */
      const ruleCard = page.locator('.hb-rule', { hasText: 'demo' });
      await expect(ruleCard).toBeVisible({ timeout: 10_000 });
      const fold = ruleCard.locator('.hb-blk-hd.hb-sub-toggle', { hasText: '触发与节奏' });
      await expect(fold).toBeVisible({ timeout: 10_000 });
      await fold.locator('.bh-t').click(); // 段默认折叠, 先进段(与设置页 group 段同口径)
      await expect(fold).toHaveAttribute('aria-expanded', 'true');

      /* 段内枚举行: 磁盘 "daily" ⇒ select 值 daily(枚举选项文案即原值, 无翻译层);
         断裂时回落 schema 默认 "never" ⇒ 值 never, 这里必红 */
      const row = page.locator('.hb-row[data-hb-key="config.demo_rules.demo.execute_once"]');
      await expect(row).toBeVisible({ timeout: 10_000 });
      await expect(row.locator('.hb-select')).toHaveValue('daily');
    });
  }
});
