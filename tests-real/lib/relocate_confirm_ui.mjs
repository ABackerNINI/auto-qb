// @ts-check
/**
 * RM04-14 浏览器侧断言/取证脚本(由 tests-real Python 用例在真实产品实例起来后调起)。
 *
 * 契约: 环境变量 RM_UI_BASE(http://127.0.0.1:<web_port>) / RM_UI_GROUP(组行文案, 即种子名) /
 *       RM_UI_DST(目标保存路径) / RM_UI_MODE(cancel|confirm) / RM_UI_SKIN(默认 prism)。
 *       最后一行 stdout = `UI_RESULT {json}`; 失败退出码 1。
 *
 * 两条路径都从真实 Web UI 的「右键组行 -> 设定位置 -> 填路径 -> 设定位置」走:
 *   cancel  : 提交 -> 确认框(7 要素) -> 点「取消」-> 原框带原路径重开 -> 请求数不增;
 *   confirm : 提交 -> 确认框 -> 点「确认迁移」-> 第二条 POST 带 confirm=true -> 「已执行」toast。
 * 回执不用 SSE 抢时序: POST 响应里拿 cmd_id, 结束时在页面上下文 fetch /api/cmd/<id> 取终态。
 */
import { chromium } from 'playwright';

const base = (process.env.RM_UI_BASE || '').replace(/\/$/, '');
const group = process.env.RM_UI_GROUP || '';
const dst = process.env.RM_UI_DST || '';
const mode = process.env.RM_UI_MODE || 'confirm';
const skin = process.env.RM_UI_SKIN || 'prism';

if (!base || !group || !dst) {
  console.error('RM_UI_BASE / RM_UI_GROUP / RM_UI_DST 必须给齐');
  process.exit(2);
}

const out = {
  mode,
  group,
  dst,
  requests: [],
  cmdIds: [],
  receipts: [],
  toasts: [],
  confirmText: '',
  cancelPath: '',
  moveDialogClosed: false,
  steps: [],
  ok: false,
};

const step = (name, extra) => {
  out.steps.push({ name, ...(extra || {}) });
};

/** 行右键: 复刻 e2e/lib/gestures.mjs 的拦截面钳位(宽行居中滚动会把落点滚出裁剪面)。 */
async function rightClickRow(page, row) {
  const guard = await page.evaluate(() =>
    [...document.querySelectorAll('.sticky-head')].reduce((m, h) => Math.max(m, h.getBoundingClientRect().bottom), 0),
  );
  for (let attempt = 0; attempt < 3; attempt++) {
    const box = await row.boundingBox();
    if (!box) throw new Error('组行不可见(无 boundingBox)');
    if (box.y < guard + 8 || box.y + box.height > (await page.evaluate(() => window.innerHeight)) - 8) {
      await row.scrollIntoViewIfNeeded();
      await page.waitForTimeout(80);
    }
    const vh = await page.evaluate(() => window.innerHeight);
    const y = Math.max(box.y + Math.min(12, box.height / 2), guard + 10);
    if (y > vh - 10) continue;
    const x = box.x + Math.min(60, box.width / 4);
    await page.mouse.click(x, y, { button: 'right' });
    return;
  }
  throw new Error('组行落点三次都被拦截面/视口吃掉');
}

/** 打开「设定位置」框并填目标路径。 */
async function openMove(page) {
  const row = page.locator('.group-row', { hasText: group }).first();
  await row.waitFor({ state: 'visible', timeout: 30_000 });
  await rightClickRow(page, row);
  const item = page.locator('.ctx-item', { hasText: '设定位置' }).first();
  await item.waitFor({ state: 'visible', timeout: 8_000 });
  await item.click();
  const dlg = page.locator('.modal.move-dialog');
  await dlg.waitFor({ state: 'visible', timeout: 8_000 });
  await dlg.locator('#move-path').fill(dst);
  step('move-dialog-open', { path: dst });
  return dlg;
}

/** 提交(首投 / 确认后重发都走这里)。 */
async function submit(page, dlg) {
  const btn = dlg.locator('button.bt.primary');
  for (let i = 0; i < 60; i++) {
    if (await btn.isEnabled()) break;
    await page.waitForTimeout(100);
  }
  await btn.click();
}

async function waitConfirm(page) {
  const modal = page.locator('.modal', { hasText: '需确认: 迁移方式' }).first();
  await modal.waitFor({ state: 'visible', timeout: 25_000 });
  return modal;
}

/** 页面上下文直取命令终态(避开 SSE 与轮询抢时序)。 */
async function fetchReceipts(page) {
  for (const id of out.cmdIds) {
    const r = await page.evaluate(
      async (u) => {
        const x = await fetch(u, { cache: 'no-store' });
        return await x.json();
      },
      `${base}/api/cmd/${encodeURIComponent(id)}`,
    );
    out.receipts.push(r);
  }
}

const REQUIRED_LABELS = ['迁移形态', '来源', '目标', '未来种子', '原因', '提示'];

async function runCancel(page) {
  const dlg = await openMove(page);
  await submit(page, dlg);
  const modal = await waitConfirm(page);
  out.confirmText = await modal.innerText();
  step('confirm-shown', { requests: out.requests.length });
  for (const label of REQUIRED_LABELS) {
    if (!out.confirmText.includes(label)) throw new Error(`确认框缺要素: ${label}`);
  }
  if (out.requests.length !== 1) throw new Error(`首投请求数应为 1, 实际 ${out.requests.length}`);
  if (out.requests[0].body.confirm) throw new Error('首投不应带 confirm');
  // 提交后不能出现「已执行」
  if (await page.locator('.toast.ok', { hasText: '已执行' }).count()) {
    throw new Error('confirm 未确认却出现「已执行」成功提示');
  }
  step('no-ok-toast-before-confirm');
  // 取消 -> 原框带原路径重开
  await modal.locator('button.bt.ghost', { hasText: '取消' }).click();
  await modal.waitFor({ state: 'hidden', timeout: 8_000 });
  const reopened = page.locator('.modal.move-dialog');
  await reopened.waitFor({ state: 'visible', timeout: 8_000 });
  out.cancelPath = await reopened.locator('#move-path').inputValue();
  if (out.cancelPath !== dst) throw new Error(`取消后原框路径未还原: ${out.cancelPath}`);
  if (out.requests.length !== 1) throw new Error(`取消后不应重发, 实际请求数 ${out.requests.length}`);
  step('cancel-reopened-with-path', { path: out.cancelPath, requests: out.requests.length });
  // 用框自带「取消」收层(避免依赖 Esc 实现)
  await reopened.locator('button.bt.ghost', { hasText: '取消' }).click();
  await reopened.waitFor({ state: 'hidden', timeout: 8_000 });
  out.moveDialogClosed = true;
}

async function runConfirm(page) {
  const dlg = await openMove(page);
  await submit(page, dlg);
  const modal = await waitConfirm(page);
  out.confirmText = await modal.innerText();
  step('confirm-shown', { requests: out.requests.length });
  for (const label of REQUIRED_LABELS) {
    if (!out.confirmText.includes(label)) throw new Error(`确认框缺要素: ${label}`);
  }
  if (out.requests.length !== 1) throw new Error(`首投请求数应为 1, 实际 ${out.requests.length}`);
  if (out.requests[0].body.confirm) throw new Error('首投不应带 confirm');
  if (await page.locator('.toast.ok', { hasText: '已执行' }).count()) {
    throw new Error('confirm 未确认却出现「已执行」成功提示');
  }
  step('no-ok-toast-before-confirm');
  await modal.locator('button.bt.primary', { hasText: '确认迁移' }).click();
  await modal.waitFor({ state: 'hidden', timeout: 8_000 });

  // 第二条 POST 必须带 confirm=true
  const second = await (async () => {
    for (let i = 0; i < 200; i++) {
      if (out.requests.length >= 2) return out.requests[1];
      await page.waitForTimeout(100);
    }
    throw new Error(`确认后未重发(请求数 ${out.requests.length})`);
  })();
  if (second.body.confirm !== true) throw new Error(`重发未带 confirm=true: ${JSON.stringify(second.body)}`);
  if (String(second.body.location) !== dst) throw new Error(`重发目标不一致: ${second.body.location}`);
  step('resent-with-confirm', { path: second.path });

  // 真实回执的成功 toast: 「已执行」+「已发起 1 项」
  const okToast = await (async () => {
    for (let i = 0; i < 120; i++) {
      const t = page.locator('.toast.ok', { hasText: '已执行' }).first();
      if (await t.count()) {
        const txt = await t.innerText();
        if (txt.includes('已发起')) return txt;
      }
      await page.waitForTimeout(100);
    }
    throw new Error('确认后未见「已执行」成功提示');
  })();
  out.toasts.push(okToast);
  if (!/已发起\s*1\s*项/.test(okToast)) throw new Error(`成功提示未按真实回执计数: ${okToast}`);
  step('ok-toast-with-receipt-count', { text: okToast });
  if (await page.locator('.modal.move-dialog').isVisible().catch(() => false)) {
    throw new Error('成功后移动框仍未关闭');
  }
  out.moveDialogClosed = true;
}

const browser = await chromium.launch({ headless: true });
const pageErrors = [];
try {
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } });
  page.on('pageerror', (e) => pageErrors.push(String(e)));
  page.on('request', (req) => {
    if (req.method() !== 'POST' || !req.url().includes('/api/torrents/')) return;
    let body = null;
    try {
      body = JSON.parse(req.postData() || 'null');
    } catch {
      /* 非 JSON 载荷(如上传)不记 */
    }
    if (body && body.location) out.requests.push({ path: req.url().replace(base, ''), body });
  });
  page.on('response', async (resp) => {
    if (resp.request().method() !== 'POST' || !resp.url().includes('/api/torrents/')) return;
    try {
      const j = await resp.json();
      if (j && j.cmd_id) out.cmdIds.push(j.cmd_id);
    } catch {
      /* 非 JSON 响应不记 */
    }
  });

  await page.goto(`${base}/${skin}/`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await page.locator('.group-row', { hasText: group }).first().waitFor({ state: 'visible', timeout: 30_000 });
  step('page-ready', { url: `${base}/${skin}/` });

  if (mode === 'cancel') await runCancel(page);
  else await runConfirm(page);

  await fetchReceipts(page);
  if (pageErrors.length) throw new Error(`页面运行期异常: ${pageErrors.join(' | ')}`);
  out.ok = true;
} catch (e) {
  out.error = String(e && e.message ? e.message : e);
  out.pageErrors = pageErrors;
} finally {
  await browser.close();
}

out.toastAll = out.toasts;
console.log('UI_RESULT ' + JSON.stringify(out));
process.exit(out.ok ? 0 : 1);
