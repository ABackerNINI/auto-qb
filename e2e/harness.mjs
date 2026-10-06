/**
 * e2e 桩服务参数的**单点定义** —— playwright.config.mjs(负责起服务)、各 spec(负责断言)
 * 与 e2e/lib/mode.mjs(负责模式门控)都从这里读, 免得端口/种子数/模式在两处各写一份然后悄悄漂移。
 *
 * 桩服务本体是 scripts/ui_harness.py: 真 `auto_qb.webui.create_app` + 真 QbManager + FakeClient
 * + 合成种子(端点/鉴权/静态挂载全是生产代码, 只有数据是人造的)。它是**长驻**进程
 * (uvicorn.run 阻塞), 正好交给 Playwright 的 webServer 托管 —— 不要指望它自己返回。
 *
 * 模式矩阵走 env 参数化(计划 26-10-06-0708 §3.2 D1): E2E_CMD_RESULT / E2E_SKIP_CHECK /
 * E2E_HR_SCENE / E2E_TORRENTS, 参数名与 ui_harness.py 的 CLI(--cmd-result / --skip-check-menu /
 * --hr-scene / --torrents)一一对应。默认档 = ok/on/on/300(旧冒烟轨默认轮口径, 沿用不改);
 * 模式轮是**串行人跑**(env 组合决定桩形态, 每轮独立起桩), 不是并行实例。
 *
 * S7 终态(2026-10-06): 旧单页冒烟脚本已退役, e2e/ 是 WEB UI 浏览器断言的**全量单点**;
 * 「每次改前端」门禁 = `npm run test:e2e:fast`(@fast 子集), 全量矩阵轮的六行命令见
 * .commands/dev/config.toml 的 dev.e2e note(串行人跑, 每轮独立起桩)。
 */

/**
 * 端口**刻意避开 8099**: 那是人工冒烟的惯用值, 多 clone 工作区下极易被别的会话残留 harness 占用
 * —— memory-bank/pitfalls/testing/smoke.md 已记 3 次复发, 其中一次是"复用了别 clone 的服务,
 * 12 项探针在旧代码上照样通过"的假信心。撞上端口时宁可失败, 也不要静默验错对象。
 * 模式轮也**不改端口**: 串行人跑, 换端口反而破坏「撞残留服务宁可失败」的既有纪律。
 */
export const PORT = 8137;
export const BASE_URL = `http://127.0.0.1:${PORT}`;

/* ------------------------------------------------------------------ *
 * 模式矩阵: 默认值 + env 覆盖(计划 26-10-06-0708 §3.2 示意, 逐字落地) *
 * ------------------------------------------------------------------ */

/** 命令泵回执形态 —— 对应 ui_harness.py `--cmd-result`(ok | error | hang)。 */
export const CMD_RESULT = process.env.E2E_CMD_RESULT || 'ok';

/** 跳检菜单旗标桩值 —— 对应 ui_harness.py `--skip-check-menu`(on | off)。 */
export const SKIP_CHECK = process.env.E2E_SKIP_CHECK || 'on';

/** HR 在线核实桩场景 —— 对应 ui_harness.py `--hr-scene`(on | empty | off)。 */
export const HR_SCENE = process.env.E2E_HR_SCENE || 'on';

/** 合成种子总数 —— 与 ui_harness.py 的 `--torrents` 同值, 供数据契约/轮询分档断言使用。 */
export const TORRENTS = Number(process.env.E2E_TORRENTS || 300);

/** 三个模式维度的合法取值(与 ui_harness.py 的 argparse choices 逐字对齐)。 */
const MODE_CHOICES = {
  CMD_RESULT: ['ok', 'error', 'hang'],
  SKIP_CHECK: ['on', 'off'],
  HR_SCENE: ['on', 'empty', 'off'],
};

/**
 * 矩阵合法性自检 —— 非法值 fail fast(module load 即抛, config 加载阶段就拦下,
 * 不会等到 webServer 起不来才给一句 argparse 报错)。mode.mjs 也调它: 单点在这里。
 */
export function assertModesValid() {
  const bad = [];
  if (!MODE_CHOICES.CMD_RESULT.includes(CMD_RESULT))
    bad.push(`E2E_CMD_RESULT=${CMD_RESULT}(允许: ${MODE_CHOICES.CMD_RESULT.join('|')})`);
  if (!MODE_CHOICES.SKIP_CHECK.includes(SKIP_CHECK))
    bad.push(`E2E_SKIP_CHECK=${SKIP_CHECK}(允许: ${MODE_CHOICES.SKIP_CHECK.join('|')})`);
  if (!MODE_CHOICES.HR_SCENE.includes(HR_SCENE))
    bad.push(`E2E_HR_SCENE=${HR_SCENE}(允许: ${MODE_CHOICES.HR_SCENE.join('|')})`);
  if (!Number.isInteger(TORRENTS) || TORRENTS <= 0)
    bad.push(`E2E_TORRENTS=${process.env.E2E_TORRENTS}(须为正整数)`);
  if (bad.length)
    throw new Error(`[e2e] 模式矩阵 env 非法:\n  - ${bad.join('\n  - ')}`);
}

assertModesValid();

/** 参与冒烟的皮肤(双皮肤都跑是旧冒烟轨以来的既定口径), `console` 不在其中, 只认 prism|atlas。 */
export const SKINS = ['prism', 'atlas'];

/**
 * 起桩服务的命令。用 `uv run` —— 与 .commands/dev/config.toml 的 dev.harness 保持**同一条口径**
 * (裸 `python` 会缺 qbittorrentapi, 别改成系统 python)。
 * 非默认参数才传: 命令首行即"本轮是什么模式"的可见证据(E2E_CMD_RESULT=error ⇒ 带 `--cmd-result error`)。
 *
 * WARN 收尾依赖(踩过, 见 memory-bank/pitfalls/testing/playwright-teardown.md):
 * Playwright 停 webServer 时等的是子进程的 `'close'` 事件, 而 Node 的 `'close'` 要求**所有
 * stdio 管道都关闭**。Windows 上它用 `spawnSync('taskkill ...')`(带管道 stdio) —— 本机 node 的
 * `spawnSync` 遇管道 stdio 必 EBUSY, 失败被静默吞掉 => 桩服务没死 => 命令永不退出、8137 残留。
 * 现由 `e2e/global-teardown.mjs`(配置里的 `globalTeardown`)在 Playwright 动手之前用**异步**
 * taskkill 先杀掉进程树兜底; 非 Windows 走 `process.kill(-pid, SIGKILL)` 本来就没问题。
 */
export const HARNESS_CMD = [
  'uv run python scripts/ui_harness.py',
  `--torrents ${TORRENTS}`,
  `--port ${PORT}`,
  CMD_RESULT !== 'ok' ? `--cmd-result ${CMD_RESULT}` : '',
  SKIP_CHECK !== 'on' ? '--skip-check-menu off' : '',
  HR_SCENE !== 'on' ? `--hr-scene ${HR_SCENE}` : '',
].filter(Boolean).join(' ');

/**
 * 就绪探测 URL —— 用**页面**而不是 `/api/` 下的接口: 只探接口会被"旧进程仍在服务旧代码"蒙过去
 * (旧进程可能页面 404 但 /api 仍 200), 这是 smoke.md 里记的判据。
 */
export const READY_URL = `${BASE_URL}/${SKINS[0]}/`;
