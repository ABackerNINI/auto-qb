/**
 * 设置页 bt_backup 编辑器视觉实测截图脚本(计划 26-11-07-0708 S6 验收动作, dev-only, **不是测试**)。
 *
 * 用途: 对 ui_harness 桩服务做真浏览器目检截图留证, 断言面与 e2e/settings-bt-backup.spec.mjs
 * 同口径(编辑器在「整组迁移」块内渲染+空态 / 增行 host:port+路径 保存回读 / S3 新口径 help
 * 在场 / 旧口径文案与退役键 finalize_timeout 退场), 差别只在产出: 每皮肤 5 张元素截图落
 * memory-bank/testing/baselines/attachments/, 断言结果打 stdout —— pytest「测试计划」不含本文件
 * (e2e 断言守阵由 settings-bt-backup.spec.mjs 承载, 本脚本只做验收截图, 不新增 pytest 用例)。
 *
 * 用法(桩服务自行起停, 端口由 OS 分配):
 *   uv run python scripts/ui_harness.py                # 启动行含 [harness] http://127.0.0.1:<port>/
 *   node scripts/ui_harness_settings_shots.mjs --port <实端口>
 * 可选: --out <目录>(默认 memory-bank/testing/baselines/attachments)
 *       --stem <文件名前缀>(默认 26-11-07-bt-backup)
 * 退出码: 断言全过 0; 任何 FAIL/ERROR 1(截图尽力而为, 已到达阶段的照常落盘)。
 *
 * 保存往返不写真桩配置盘: page.route 拦截 /api/config, PUT 收下载荷当「已落盘」、GET 注回 ——
 * 与 e2e/settings-bt-backup.spec.mjs 同口径(真后端往返语义, 只差不落盘)。
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, '..');

const argv = process.argv.slice(2);
function argOf(flag, fallback) {
  const i = argv.indexOf(flag);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
}
const port = argOf('--port', '');
if (!port) {
  console.error('NEXT: 先起桩(uv run python scripts/ui_harness.py), 再以 --port <启动行实端口> 重跑');
  process.exit(2);
}
const outDir = resolve(repo, argOf('--out', 'memory-bank/testing/baselines/attachments'));
const stem = argOf('--stem', '26-11-07-bt-backup');
const base = `http://127.0.0.1:${port}`;
const SKINS = ['prism', 'atlas'];
const ROW = { host: '127.0.0.1:8080', path: 'D:/qb/BT_backup' };

const failures = [];
function check(name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  -- ' + detail : ''}`);
  if (!ok) failures.push(name);
}
function flowError(name, err) {
  console.log(`ERROR ${name}: ${err && err.message ? err.message : err}`);
  failures.push(name);
}
/** filter+hasText 轮询等 actbar 状态词出现(spec 的 toContainText 口径)。 */
async function waitState(page, text, timeout) {
  await page.locator('.hb-actbar').filter({ hasText: text }).first().waitFor({ timeout });
}

mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();

for (const skin of SKINS) {
  const file = (n) => join(outDir, `${stem}-${skin}-${n}.png`);
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await ctx.newPage();

  let btBackup = null;
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

  try {
    await page.goto(`${base}/${skin}/`, { waitUntil: 'domcontentloaded' });
    await page.locator('.group-row').first().waitFor({ timeout: 30000 });

    // 进设置 -> 「自动化」分区(与 spec 同款选择器; 卡头按 .hb-card-t 标题取避免「自动化规则」双命中)
    await page.locator('nav.tabs-right button').first().click();
    await page.locator('.hb-grid .hb-card').first().waitFor({ timeout: 20000 });
    const card = page.locator('.hb-card')
      .filter({ has: page.locator('.hb-card-t', { hasText: '自动化' }) })
      .first();
    await card.click();

    const blk = page.locator('.hb-blk')
      .filter({ has: page.locator('.bh-t', { hasText: '整组迁移' }) }).last();
    const ed = blk.locator('.bt-bk');
    await ed.waitFor({ timeout: 15000 });

    // (1) 编辑器渲染在整组迁移块内 + 空态文案
    check(`[${skin}] editor rendered in relocate block`, true);
    const emptyText = await ed.innerText();
    check(
      `[${skin}] empty state text present`,
      emptyText.includes('fastresume 收尾功能整体未启用'),
      emptyText.slice(0, 50),
    );

    // (3) S3 新口径 help(块头 .bh-n, schema groups.py 单点透传)
    const help = (await blk.locator('.bh-n').innerText()).trim();
    check(`[${skin}] help has 下线窗口`, help.includes('下线窗口'), help.slice(0, 60));
    check(`[${skin}] help has 可直接再迁`, help.includes('可直接再迁'));
    check(`[${skin}] help has fastresume`, help.includes('fastresume'));

    // (4) 旧口径文案 + 退役键 finalize_timeout 全部退场(body textContent 口径, 连 x-template 一起抓)
    const bodyText = await page.locator('body').textContent();
    check(`[${skin}] old wording「setLocation 收尾」absent`, !bodyText.includes('setLocation 收尾'));
    check(`[${skin}] old wording「拒绝再迁」absent`, !bodyText.includes('拒绝再迁'));
    check(`[${skin}] retired key finalize_timeout absent`, !bodyText.includes('finalize_timeout'));

    // 截图 01/02/03: 维护视图全景(块滚入视口后拍视口) / 编辑器块特写(空态) / 块头 help 特写。
    // !01 不拍卡片元素: 点卡进详情后 settings.html 的 hb-grid 卡片网格已被 v-else 切走(不可见),
    //   元素截图会等可见性到超时 —— 拍视口既留页面语境又避开该坑。
    await blk.scrollIntoViewIfNeeded();
    await page.screenshot({ path: file('01-maintenance-view') });
    await blk.screenshot({ path: file('02-editor-empty') });
    await blk.locator('.bh-n').screenshot({ path: file('03-relocate-help') });

    // (2) 增行(host:port + 路径) -> 全局保存 -> 重载回读
    await waitState(page, '已与磁盘同步', 20000);
    await ed.getByRole('button', { name: '+ 新增实例' }).click();
    await ed.getByPlaceholder('host:port').fill(ROW.host);
    await ed.getByPlaceholder('该实例的 BT_backup 目录路径').fill(ROW.path);
    await waitState(page, '有改动还没保存', 10000);
    await blk.screenshot({ path: file('04-row-added') });

    await page.locator('.hb-actbar').locator('.hb-btn.primary').click();
    const deadline = Date.now() + 15000;
    while (saved === null && Date.now() < deadline) await page.waitForTimeout(200);
    const payload = saved && saved.tree && saved.tree.config ? saved.tree.config.bt_backup : null;
    check(
      `[${skin}] PUT payload bt_backup == {host:port: path}`,
      JSON.stringify(payload) === JSON.stringify({ [ROW.host]: ROW.path }),
      JSON.stringify(payload),
    );
    await waitState(page, '已与磁盘同步', 15000);

    await page.reload({ waitUntil: 'domcontentloaded' });
    const blk2 = page.locator('.hb-blk')
      .filter({ has: page.locator('.bh-t', { hasText: '整组迁移' }) }).last();
    const ed2 = blk2.locator('.bt-bk');
    await ed2.waitFor({ timeout: 20000 });
    check(
      `[${skin}] readback host:port after reload`,
      (await ed2.getByPlaceholder('host:port').inputValue()) === ROW.host,
    );
    check(
      `[${skin}] readback path after reload`,
      (await ed2.getByPlaceholder('该实例的 BT_backup 目录路径').inputValue()) === ROW.path,
    );
    const emptyGone = !((await ed2.innerText()).includes('fastresume 收尾功能整体未启用'));
    check(`[${skin}] empty state gone once a row exists`, emptyGone);
    await blk2.screenshot({ path: file('05-reload-readback') });
  } catch (e) {
    flowError(`[${skin}] flow`, e);
  } finally {
    await ctx.close();
  }
}

await browser.close();
if (failures.length) {
  console.log(`\nRESULT: ${failures.length} failed -> ${failures.join(' | ')}`);
  process.exit(1);
}
console.log('\nRESULT: all checks passed');
