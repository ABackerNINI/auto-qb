// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 添加种子「部分受理」时窗口必须消失(2026-10-18 用户报障:
 * 「WEBUI 部分种子添加失败(已存在)时添加窗口不消失」)
 *
 * 背景: qB 对重复种子是**整批里挑着拒**(HTTP 200 + failure_count>0), 于是"一部分加进去、
 * 其余已存在"是常态路径。旧口径把部分受理折叠进 error 回执, 前端 submitAddTorrent 只认
 * r.ok 关窗 ⇒ 明明加进去几个, 窗口赖着不动还报"添加种子失败"。
 * 修法 = 后端三态回执(ok/warn/error, commands.py::_cmd_add_torrents)+ 前端按 r.status 分流。
 *
 * 注入手法(page.route, 与仓库既有的回执/载荷注入同口径):
 *   ① 拦 POST /api/torrents/add —— 命令不进真队列(不会真加种子), 回一个约定 cmd_id;
 *   ② 拦 GET /api/cmd/{cmd_id} —— 供出注定的回执。SSE 侧没有该 cmd_id 的事件,
 *      waitCmd 的轮询路径确定性拿到它(不与事件路径赛跑)。
 * 后端三态回执的语义由单测钉(test_web_admin / test_web_longtail), 本 spec 钉**前端反应**;
 * 且 error(全拒)必须反向留窗 —— 那一份文件/链接原样没进 qB, 留窗才能改完重提。
 * 两个方向都钉: 只钉"warn 关窗"会放过"把 error 也一起关窗"的过度修复。
 */

/** 约定的回执 id(注入用, 与真实 cmd_id 不会相碰) */
const ID_PARTIAL = 'e2e-add-partial';
const ID_ALLFAIL = 'e2e-add-allfail';

/** 与后端 commands.py::_cmd_add_torrents 三态回执同文案(计数段逐字同) */
const RECEIPT_PARTIAL = {
  status: 'warn',
  error: '部分种子未添加(可能已存在): 成功 1 / 失败 1 / 待定 0',
};
const RECEIPT_ALLFAIL = {
  status: 'error',
  error: 'qB 未接受添加: 成功 0 / 失败 1 / 待定 0',
};

/**
 * 注入一对路由: 提交被拦(不入真队列), 回执按给定 id 供出。
 * @param {import('@playwright/test').Page} page
 * @param {string} cmdId
 * @param {{status: string, error: string}} receipt
 */
async function stubAddReceipt(page, cmdId, receipt) {
  await page.route('**/api/torrents/add', (route) => route.fulfill({ json: { queued: true, cmd_id: cmdId } }));
  await page.route(`**/api/cmd/${cmdId}`, (route) => route.fulfill({ json: receipt }));
}

/** 开添加窗口并提交一条 magnet 链接(来源域最轻路径: 无文件读取) */
async function submitOneMagnet(page) {
  await page.click('button.add-btn');
  await expect(page.locator('.add-dialog-mask')).toBeVisible();
  await page.click('.add-dialog-linkbtn'); // 展开链接输入域(DLG-03 默认收起)
  const urlBox = page.locator('.add-dialog-textarea');
  await expect(urlBox).toBeVisible();
  await urlBox.fill('magnet:?xt=urn:btih:e2eaddpartialreceipt');
  await page.click('.add-dialog .modal-actions .bt.primary');
}

for (const skin of SKINS) {
  test.describe(`添加种子部分受理回执 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`部分受理(warn): warn toast 带计数 + 添加窗口关闭 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await stubAddReceipt(page, ID_PARTIAL, RECEIPT_PARTIAL);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      await submitOneMagnet(page);

      // warn 类 toast: 部分失败详情(计数由后端文案带出)+ 列表稍后自动刷新
      const toast = page.locator('.toast-wrap .toast.warn');
      await expect(toast, '部分受理必须给 warn 提示(不是 error)').toBeVisible({ timeout: 10_000 });
      await expect(toast).toContainText('部分种子未添加');
      await expect(toast).toContainText('成功 1 / 失败 1');
      await expect(toast).toContainText('列表稍后自动刷新');
      // 本案报障的关键断言: 窗口消失(v-if="addOpen" 直接移除, 无过渡包装)
      await expect(page.locator('.add-dialog-mask'), '部分受理时添加窗口必须关闭').toHaveCount(0);
    });

    test(`全部被拒(error): error toast + 添加窗口保留(反向防过度修复) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await stubAddReceipt(page, ID_ALLFAIL, RECEIPT_ALLFAIL);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      await submitOneMagnet(page);

      const toast = page.locator('.toast-wrap .toast.error');
      await expect(toast, '全拒必须给 error 提示').toBeVisible({ timeout: 10_000 });
      await expect(toast).toContainText('添加种子失败');
      // 反向: 全拒时那一份链接原样没进 qB, 窗口留在前台等用户改完重提
      await expect(page.locator('.add-dialog-mask'), '全部被拒时添加窗口必须保留').toBeVisible();
    });
  });
}
