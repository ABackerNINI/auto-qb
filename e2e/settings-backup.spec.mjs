// @ts-check
import { expect, test } from '@playwright/test';
import fs from 'node:fs';
import { SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { installRouteCleanup } from './lib/route-cleanup.mjs';

/* 收尾竞态兜底(issue 26-11-13-0234): 本文件的 route 桩/观测回调(fallback/fulfill)在用例
 * 收尾统一卸载, 与 settings-bt-backup.spec.mjs 同款。 */
installRouteCleanup(test);

/**
 * 设置页 · actbar「导出配置 / 导入配置」双钮(计划 26-11-14-0624 S3, D3/D6/D7/D10/D12)。
 *
 * 端点口径: 导出全真(GET /api/backup/export 真响应真下载); 导入真 POST(真后端整份
 * 应用, 用 route.fallback **观测**请求体不拦截)。桩的 config.yml 钉在 mkdtemp 临时目录
 * (scripts/ui_harness.py: mgr.config_path = <tmp>/config.yml), 真写盘不落仓库根 ——
 * 生产红线不沾边。round-trip 里「改一处」的 PUT /api/config 拦桩只记账**不落盘**
 * (ctx-custom / settings-bt-backup 同款口径: 桩 config.yml 是同轮其它 spec 共用的临时
 * 文件); 导入写回的均为原 bundle 或带注释标记的原样副本, 磁盘终态 = 原样, 零净污染。
 *
 * 桩前提: harness 已把 gtm 指针发现(agent.pointer_dir 单点)重定向进桩私有临时目录
 * (gtm-pointer, scripts/ui_harness.py _isolate_gtm_discovery, issue 26-11-18-0308)——
 * 宿主 endpoint.json 不可见 -> 宿主 gtm 工具在不在跑都一样: 导出 bundle.gtm === null
 * (离线导出形态), 导入确认框里 gtm 勾选灰显(缺段不可勾) —— 这正是 D6「缺段灰显」
 * 的真值场景。
 *
 * 断言面(D3 / D6 三闸 / D10 / D12):
 *   导出: cfgDirty 提示不阻断 + download 捕获合法 bundle + ui_prefs 前端并入且与页面
 *         localStorage 逐字对账(D3 采集面) + Content-Disposition 文件名戳;
 *   导入: round-trip(内存改 bundle -> 导入真落盘(re-export 见标记注释) -> 导入原 bundle
 *         还原 -> 磁盘终态原样) + POST 请求体无 ui_prefs 且 sections 只含勾选段(D3 前端
 *         出口) + 缺段灰显(is-gated 真禁勾) + 结果 dialog -> reload;
 *   脏态: cfgDirty 先弹「未保存改动将丢失」确认, 确认后闸 2 正常弹; 取消无 POST(D12);
 *   apply: 未登记键/非字符串值 -> warn toast 且不写回; 已登记字符串键写回; 缺键保持
 *         本机值(D8/R5);
 *   失败: 422 聚合文本 -> 「导入失败」dialog 逐行展示 + 不 reload + 本机偏好一字未动;
 *         全不勾选 -> warn 且无 POST。
 *
 * 改动落点选 bt_backup 输入框(整组迁移块, 与 settings-bt-backup.spec.mjs 同款定位):
 * 它是纯路径标量、schema 可回写, round-trip 断言干净。
 */

/** 进设置页「自动化」分区并等 actbar 就绪(导航惯例同 settings-bt-backup.spec.mjs)。 */
async function openSettings(page, skin) {
  await openApp(page, skin);
  await page.locator('nav.tabs-right button').first().click();
  await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
  await page.locator('.hb-card')
    .filter({ has: page.locator('.hb-card-t', { hasText: '自动化' }) })
    .click();
  const actbar = page.locator('.hb-actbar');
  await expect(actbar).toContainText('已与磁盘同步', { timeout: 20_000 });
  return actbar;
}

/** 整组迁移块的 bt_backup 输入框(纯路径标量, round-trip 的改动落点)。 */
function btBackupInput(page) {
  return page.locator('.hb-blk')
    .filter({ has: page.locator('.bh-t', { hasText: '整组迁移' }) }).last()
    .locator('.bt-bk input');
}

/** 真 GET /api/backup/export -> download 捕获 -> 返回解析后的 bundle。 */
async function exportBundle(page, actbar) {
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    actbar.getByRole('button', { name: '导出配置' }).click(),
  ]);
  expect(download.suggestedFilename(), 'Content-Disposition 文件名戳(§03)')
    .toMatch(/^auto-qb-backup-\d{8}-\d{6}\.json$/);
  return JSON.parse(await fs.promises.readFile(await download.path(), 'utf8'));
}

/** 导入闸1 的文件投入: 动态 input 的程序化 click 会开文件选择器 —— 用 Playwright 的
 * filechooser 事件接住并把(可内存改造的)bundle 喂进去, 等价于用户在系统对话框里选中文件。 */
async function feedViaFileChooser(page, click, bundle) {
  const [chooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    click(),
  ]);
  await chooser.setFiles({
    name: 'auto-qb-backup-test.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(bundle, null, 2), 'utf8'),
  });
}

/** 观测 POST /api/backup/import 请求体(route.fallback 放行真网络, 只记账不拦截)。 */
async function observeImport(page) {
  const bodies = [];
  await page.route('**/api/backup/import', async (route) => {
    bodies.push(route.request().postDataJSON());
    return route.fallback();
  });
  return bodies;
}

test.describe('设置页 · 配置备份导出/导入(S3)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 导出: 脏态提示不阻断 + 合法 bundle + ui_prefs 与本机 localStorage 逐字对账 @fast`, async ({ page }) => {
      const actbar = await openSettings(page, skin);
      const input = btBackupInput(page);
      await expect(input).toBeVisible({ timeout: 15_000 });

      /* D3 采集面对账锚点: 先落两个已知 PREF_KEYS 值, 导出后逐字比对(bundle ui_prefs
       * 段 = 前端 collect() 读 localStorage, 服务端响应不含该段)。 */
      await page.evaluate(() => {
        localStorage.setItem('autoqb.ui.theme', 'ocean');
        localStorage.setItem('autoqb.ui.kbdPersist', '0');
      });

      /* D12: 先做一处改动(不保存) -> 导出仍照常走, 且提示「未保存改动不含在内」不阻断 */
      await input.fill('D:/qb/backup-export-dirty-check');
      await expect(actbar).toContainText('有改动还没保存');

      const bundle = await exportBundle(page, actbar);

      /* bundle 形状(§03): format/bundle_version/created_at/app_version + 三服务端段 */
      expect(bundle.format).toBe('auto-qb-config-bundle');
      expect(bundle.bundle_version).toBe(1);
      expect(typeof bundle.created_at).toBe('string');
      expect(String(bundle.app_version).length).toBeGreaterThan(0);
      expect(typeof bundle.config_yaml).toBe('string');
      expect(bundle.config_yaml.trim().length).toBeGreaterThan(0);
      expect(bundle.webui_keys).toMatchObject({
        schema_version: 1,
        template: expect.any(String),
        overrides: expect.any(Object),
      });
      /* 桩前提: gtm 指针发现已重定向进桩私有目录(_isolate_gtm_discovery) -> 宿主
       * endpoint.json 不可见 -> 离线导出形态(D9 该段 null), 与宿主是否真跑 gtm 无关 */
      expect(bundle.gtm).toBeNull();
      /* D3: ui_prefs 段在且与页面 localStorage 逐字相等 */
      expect(bundle.ui_prefs && typeof bundle.ui_prefs === 'object' && !Array.isArray(bundle.ui_prefs)).toBe(true);
      expect(bundle.ui_prefs['autoqb.ui.theme']).toBe('ocean');
      expect(bundle.ui_prefs['autoqb.ui.kbdPersist']).toBe('0');

      /* 脏态提示在场(不阻断的证据: download 已发生) */
      await expect(page.locator('.toast-wrap .toast.warn').first()).toContainText('未保存改动不含在内');

      /* 现场还原: 放弃改动(cfgDiscard 自带确认框), 不把脏态带出本用例 */
      await actbar.getByRole('button', { name: '放弃改动' }).click();
      await page.locator('.modal-actions').getByRole('button', { name: '放弃修改' }).click();
      await expect(actbar).toContainText('已与磁盘同步', { timeout: 15_000 });
    });

    test(`[${skin}] 导入 round-trip: 内存改 bundle 真落盘 -> 导原 bundle 还原; POST 体无 ui_prefs; 缺段灰显 @fast`, async ({ page }) => {
      /* PUT /api/config 拦桩只记账不落盘(共用 tmp config.yml 的污染口径见文件头);
       * GET 放行真盘(cfgSave 的 fresh 回读走真数据)。 */
      let savedPayload = null;
      await page.route('**/api/config', async (route) => {
        if (route.request().method() === 'PUT') {
          savedPayload = route.request().postDataJSON();
          return route.fulfill({ json: { changes: ['config.relocate.bt_backup'], restart_required: [] } });
        }
        return route.fallback();
      });
      const importBodies = await observeImport(page);

      const actbar = await openSettings(page, skin);
      const input = btBackupInput(page);
      await expect(input).toBeVisible({ timeout: 15_000 });
      const original = await input.inputValue();

      /* 0) 基准 bundle(改动前导出, 真 GET /api/backup/export) */
      const bundle = await exportBundle(page, actbar);
      /* 评审 #5 判别力: 内存改 bundle(config_yaml 追加一行注释标记 —— ruamel round-trip
       * 保注释, 导入即随原文落盘) -> 导入 -> re-export 断言标记真在盘上(导出恒读磁盘)。 */
      const MARKER = 'aqb-e2e-import-marker';
      const mutated = { ...bundle, config_yaml: bundle.config_yaml + `\n# ${MARKER}\n` };

      /* 1) 改一处 -> PUT 桩记账「已保存」(不落盘), actbar 回同步态 */
      await input.fill('D:/qb/backup-roundtrip-modified');
      await expect(actbar).toContainText('有改动还没保存');
      await actbar.locator('.hb-btn.primary').click();
      await expect.poll(() => savedPayload, { message: 'PUT /api/config 未发出', timeout: 15_000 }).not.toBeNull();
      await expect(actbar).toContainText('已与磁盘同步', { timeout: 15_000 });
      /* 桩口径生效: 修改值只在树/桩账上, 真盘仍原样(fresh GET 放行真盘) */
      await expect(input).toHaveValue(original);

      /* 2) 导入改标记的 bundle -> 闸2 确认框: 摘要行 + 机器路径提示行(D10) + 缺段灰显 */
      await feedViaFileChooser(page, () => actbar.getByRole('button', { name: '导入配置' }).click(), mutated);
      const modal = page.locator('.modal');
      await expect(modal).toBeVisible({ timeout: 10_000 });
      /* cfg 已「保存」后导入, 不应再弹脏态闸(D12: 那道闸只在 cfgDirty 时出现) */
      await expect(modal).not.toContainText('未保存的改动将丢失');
      await expect(modal).toContainText('bundle 版本');
      await expect(modal).toContainText('机器相关路径');
      /* gtm 段离线导出为 null(指针发现已隔离, 与宿主 gtm 无关) -> 灰显不可勾
       * (opt-pill.is-gated 真禁点击, 三层一致口径) */
      const pills = modal.locator('.opt-pill');
      await expect(pills).toHaveCount(3);
      const gated = pills.filter({ hasText: 'gtm' });
      await expect(gated).toHaveClass(/is-gated/);
      await expect(gated).toHaveAttribute('aria-disabled', 'true');
      /* 可用段默认全勾, 确认 */
      await modal.locator('.modal-actions').getByRole('button', { name: '导入', exact: true }).click();

      /* 3) 结果 dialog: applied 报告 -> 确认 -> reload */
      await expect(modal).toContainText('导入完成');
      await expect(modal).toContainText('已应用');
      await modal.locator('.modal-actions').getByRole('button', { name: '刷新页面' }).click();

      /* 4) reload 后回设置页(位置持久化, bt-backup spec 同款), 断言真写盘(re-export 见标记) */
      await expect(btBackupInput(page)).toBeVisible({ timeout: 30_000 });
      const onDisk = await exportBundle(page, page.locator('.hb-actbar'));
      expect(onDisk.config_yaml, '评审 #5: 导入的标记注释必须真落盘(导出恒读磁盘)')
        .toContain(MARKER);

      /* 5) D3 前端出口: POST 请求体无 ui_prefs 键, sections 只含勾选段(gtm 灰显未被发) */
      expect(importBodies.length).toBe(1);
      expect(importBodies[0]).not.toHaveProperty('ui_prefs');
      expect(Object.keys(importBodies[0].sections).sort()).toEqual(['config_yaml', 'webui_keys']);
      expect(importBodies[0].bundle_version).toBe(1);

      /* 6) 导原 bundle 还原 -> reload -> re-export 断言标记已不在盘上(磁盘终态 = 原样) */
      await feedViaFileChooser(page, () => page.locator('.hb-actbar').getByRole('button', { name: '导入配置' }).click(), bundle);
      await expect(modal).toBeVisible({ timeout: 10_000 });
      await modal.locator('.modal-actions').getByRole('button', { name: '导入', exact: true }).click();
      await expect(modal).toContainText('导入完成', { timeout: 10_000 });
      await modal.locator('.modal-actions').getByRole('button', { name: '刷新页面' }).click();
      const input2 = btBackupInput(page);
      await expect(input2).toBeVisible({ timeout: 30_000 });
      await expect(input2).toHaveValue(original);
      await expect(page.locator('.hb-actbar')).toContainText('已与磁盘同步', { timeout: 20_000 });
      const restored = await exportBundle(page, page.locator('.hb-actbar'));
      expect(restored.config_yaml).not.toContain(MARKER);
    });

    test(`[${skin}] D12 脏态闸: 未保存改动先弹「将丢失」确认 -> 确认后闸 2 正常弹; 取消无 POST @fast`, async ({ page }) => {
      const actbar = await openSettings(page, skin);
      const input = btBackupInput(page);
      await expect(input).toBeVisible({ timeout: 15_000 });
      const bundle = await exportBundle(page, actbar);  // 干净态先取基准 bundle
      const importBodies = await observeImport(page);

      /* fill 改动不保存 -> cfgDirty */
      await input.fill('D:/qb/backup-dirty-import-check');
      await expect(actbar).toContainText('有改动还没保存');

      /* 点导入 -> 脏态确认框(D12)在场 */
      await feedViaFileChooser(page, () => actbar.getByRole('button', { name: '导入配置' }).click(), bundle);
      const modal = page.locator('.modal');
      await expect(modal).toBeVisible({ timeout: 10_000 });
      await expect(modal).toContainText('未保存的改动将丢失');

      /* 确认「放弃改动并继续」-> cfgLoad 回磁盘态 -> 闸 2 勾选确认框正常弹出 */
      await modal.locator('.modal-actions').getByRole('button', { name: '放弃改动并继续' }).click();
      await expect(modal).toContainText('bundle 版本', { timeout: 10_000 });
      await expect(actbar).toContainText('已与磁盘同步');

      /* 取消路径: 闸 2 点取消 -> 中止, 无 POST 发出 */
      await modal.locator('.modal-actions').getByRole('button', { name: '取消' }).click();
      await expect(modal).toHaveCount(0);
      expect(importBodies.length, '取消路径不得发出 POST /api/backup/import').toBe(0);
    });

    test(`[${skin}] apply 分支: 未登记键/非字符串值 warn 不写回; 已登记键写回; 缺键保持本机值 @fast`, async ({ page }) => {
      const actbar = await openSettings(page, skin);
      await expect(btBackupInput(page)).toBeVisible({ timeout: 15_000 });
      const bundle = await exportBundle(page, actbar);
      const importBodies = await observeImport(page);

      /* 本机基线: theme/rowlang 预置(bundle 不含/含非字符串值), kbdPersist 预置 0 等
       * bundle 覆盖成 1 —— 三支分别钉「缺键保持」「忽略不写回」「已登记写回」。 */
      await page.evaluate(() => {
        localStorage.setItem('autoqb.ui.theme', 'ocean');
        localStorage.setItem('autoqb.ui.rowlang', 'flat');
        localStorage.setItem('autoqb.ui.kbdPersist', '0');
      });
      const mutated = {
        ...bundle,
        ui_prefs: {
          'autoqb.ui.kbdPersist': '1',       // 已登记字符串 -> 写回
          'autoqb.unknown.pref': 'x',         // 未登记 -> 忽略 + warn
          'autoqb.ui.rowlang': 42,            // 已登记但非字符串 -> 忽略 + warn, 本机 'flat' 不动
          // theme 故意缺键 -> 保持本机 'ocean'
        },
      };

      /* 只勾 webui_keys(够发出一次真 POST; 该段内容与磁盘同源, 零净污染) */
      await feedViaFileChooser(page, () => actbar.getByRole('button', { name: '导入配置' }).click(), mutated);
      const modal = page.locator('.modal');
      await expect(modal).toBeVisible({ timeout: 10_000 });
      await modal.locator('.opt-pill').filter({ hasText: '主配置' }).click();
      await modal.locator('.modal-actions').getByRole('button', { name: '导入', exact: true }).click();

      /* POST 成功后: 未登记/非字符串键的 warn toast + 已登记键照常写回 + 缺键保持本机值 */
      await expect(modal).toContainText('导入完成', { timeout: 10_000 });
      const warn = page.locator('.toast-wrap .toast.warn', { hasText: '偏好部分未导入' }).first();
      await expect(warn).toContainText('autoqb.unknown.pref');
      await expect(warn).toContainText('autoqb.ui.rowlang');
      const prefs = await page.evaluate(() => ({
        theme: localStorage.getItem('autoqb.ui.theme'),
        rowlang: localStorage.getItem('autoqb.ui.rowlang'),
        kbdPersist: localStorage.getItem('autoqb.ui.kbdPersist'),
      }));
      expect(prefs.kbdPersist, '已登记字符串键必须写回').toBe('1');
      expect(prefs.theme, 'bundle 缺键 -> 本机值保持').toBe('ocean');
      expect(prefs.rowlang, '非字符串值 -> 忽略不写回, 本机值保持').toBe('flat');
      /* D3 出口: POST 体无 ui_prefs, sections 只含勾选的 webui_keys */
      expect(importBodies.length).toBe(1);
      expect(importBodies[0]).not.toHaveProperty('ui_prefs');
      expect(Object.keys(importBodies[0].sections)).toEqual(['webui_keys']);
      /* 收尾: 刷新页面(reload 使偏好落定), 不留悬空结果 dialog */
      await modal.locator('.modal-actions').getByRole('button', { name: '刷新页面' }).click();
      await expect(btBackupInput(page)).toBeVisible({ timeout: 30_000 });
    });

    test(`[${skin}] 导入闸1: 非 bundle JSON(format 不符)直接报错, confirm 不弹出 @fast`, async ({ page }) => {
      const actbar = await openSettings(page, skin);
      await expect(btBackupInput(page)).toBeVisible({ timeout: 15_000 });

      /* shape 闸(D6): format 字段不符直接 toast 报错, 不进确认框 */
      await feedViaFileChooser(
        page,
        () => actbar.getByRole('button', { name: '导入配置' }).click(),
        { format: 'something-else', hello: 1 },
      );
      await expect(page.locator('.toast-wrap .toast.error').first()).toContainText('format 字段不符');
      await expect(page.locator('.modal')).toHaveCount(0);
    });
  }
});

  /* 失败路径单独一组、不装公共运行期错误守阵: 422 桩会触发 Chromium 网络层的
   * console.error("Failed to load resource: ... 422") —— 那是测试注入的已知噪音而非页面
   * 运行期错误; 本组改用手工断言「pageerror 为零 + console.error 恰好只有这条噪音」,
   * 比全量静默更强(422 之外再多一条 console.error 也会红)。 */
  test.describe('设置页 · 配置备份导入失败路径(S3, 422 桩面)', () => {
    for (const skin of SKINS) {
      test(`[${skin}] 422 聚合文本整段展示且不 reload、本机零改动; 全不勾选 warn 无 POST @fast`, async ({ page }) => {
        const runtimeErrors = collectRuntimeErrors(page);  // 必须在 goto 前挂监听
        const actbar = await openSettings(page, skin);
        await expect(btBackupInput(page)).toBeVisible({ timeout: 15_000 });
        /* 「本机偏好一字未动」断言要有判别力(复评 minor): kbdPersist 预置必须在 exportBundle
         * **之前** —— 让 bundle.ui_prefs 真带上 kbdPersist='0'; 导出后再把本机改成 '1'。
         * 422 失败后断言本机仍 '1': apply 一旦被回归挪回 POST 之前, bundle 里的 '0' 就会
         * 写回而红 —— 缺键语义(评审原断言)守不住这个拍板回归面。 */
        await page.evaluate(() => { localStorage.setItem('autoqb.ui.kbdPersist', '0'); });
        const bundle = await exportBundle(page, actbar);
        expect(bundle.ui_prefs['autoqb.ui.kbdPersist'], '前置自证: bundle 必须真带上 kbdPersist=0').toBe('0');
        await page.evaluate(() => { localStorage.setItem('autoqb.ui.kbdPersist', '1'); });
        /* reload 探针: 一旦 location.reload() 发生, 内存标记消失 */
        await page.evaluate(() => { window.__aqbNoReloadProbe = 1; });

        /* POST 桩: 422 聚合多行 detail(routes/backup.py _r1_message 同形态) */
        let postCount = 0;
        await page.route('**/api/backup/import', async (route) => {
          postCount += 1;
          return route.fulfill({
            status: 422,
            json: { detail: 'config_yaml: 掩码值无法还原为本机现值, 共 2 处:\n  [1] web.passwords 第 3 条\n  [2] transfer targets 第 2 项' },
          });
        });

        await feedViaFileChooser(page, () => actbar.getByRole('button', { name: '导入配置' }).click(), bundle);
        const modal = page.locator('.modal');
        await expect(modal).toBeVisible({ timeout: 10_000 });
        await modal.locator('.modal-actions').getByRole('button', { name: '导入', exact: true }).click();

        /* 失败 dialog: 标题 + 聚合多行逐行展示 + 「一字未改」文案(ui_prefs 移到 POST 成功后,
         * 失败路径本机偏好同样零改动 —— 文案对双侧保真) */
        await expect(modal).toContainText('导入失败', { timeout: 10_000 });
        await expect(modal).toContainText('一字未改');
        await expect(modal).toContainText('掩码值无法还原为本机现值');
        await expect(modal).toContainText('web.passwords 第 3 条');
        await expect(modal).toContainText('transfer targets 第 2 项');

        /* 不 reload + 本机偏好一字未动 */
        await modal.locator('.modal-actions').getByRole('button', { name: '知道了' }).click();
        await expect(modal).toHaveCount(0);
        expect(await page.evaluate(() => window.__aqbNoReloadProbe), '失败路径不得 reload').toBe(1);
        /* 本机仍是导出后手改的 '1': bundle 里带的 '0' 没有写回 —— apply 移位拍板的判别断言 */
        expect(await page.evaluate(() => localStorage.getItem('autoqb.ui.kbdPersist')), '422 失败后本机偏好一字未动(bundle 的 0 未写回)').toBe('1');
        expect(postCount).toBe(1);

        /* 全不勾选分支: 再开一次, 两可用段全部退勾 -> warn 且无第二次 POST */
        await feedViaFileChooser(page, () => page.locator('.hb-actbar').getByRole('button', { name: '导入配置' }).click(), bundle);
        await expect(modal).toBeVisible({ timeout: 10_000 });
        const pills = modal.locator('.opt-pill');
        await pills.filter({ hasText: '主配置' }).click();
        await pills.filter({ hasText: '快捷键' }).click();
        await modal.locator('.modal-actions').getByRole('button', { name: '导入', exact: true }).click();
        await expect(page.locator('.toast-wrap .toast.warn', { hasText: '未勾选任何要应用的段' }).first()).toBeVisible();
        await expect(modal).toHaveCount(0);
        expect(postCount, '全不勾选不得发出 POST').toBe(1);

        /* 运行期错误面手工把关: pageerror 为零; console.error 只许 422 桩那一条网络噪音 */
        const pageErrors = runtimeErrors.filter((t) => t.startsWith('pageerror:'));
        expect(pageErrors, `无页面运行期错误:\n${pageErrors.join('\n')}`).toEqual([]);
        const noise = runtimeErrors.filter((t) => t.includes('Failed to load resource') && t.includes('422'));
        expect(noise, '422 桩的已知网络层 console.error 恰一条').toHaveLength(1);
        expect(runtimeErrors.length, '除 422 桩噪音外零 console.error/pageerror').toBe(noise.length);
      });
    }
  });
