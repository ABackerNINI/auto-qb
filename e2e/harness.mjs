/**
 * e2e 桩服务参数的**单点定义** —— playwright.config.mjs(负责起服务)与 smoke.spec.mjs(负责断言)
 * 都从这里读, 免得端口/种子数在两处各写一份然后悄悄漂移。
 *
 * 桩服务本体是 scripts/ui_harness.py: 真 `auto_qb.webui.create_app` + 真 QbManager + FakeClient
 * + 合成种子(端点/鉴权/静态挂载全是生产代码, 只有数据是人造的)。它是**长驻**进程
 * (uvicorn.run 阻塞), 正好交给 Playwright 的 webServer 托管 —— 不要指望它自己返回。
 *
 * 人工深挖(105 项断言)仍走 scripts/ui_smoke.cjs; 这里只放"每次改前端都该过一遍"的那几条。
 */

/**
 * 端口**刻意避开 8099**: 那是人工冒烟的惯用值, 多 clone 工作区下极易被别的会话残留 harness 占用
 * —— memory-bank/pitfalls/testing/smoke.md 已记 3 次复发, 其中一次是"复用了别 clone 的服务,
 * 12 项探针在旧代码上照样通过"的假信心。撞上端口时宁可失败, 也不要静默验错对象。
 */
export const PORT = 8137;
export const BASE_URL = `http://127.0.0.1:${PORT}`;

/** 合成种子总数 —— 与 ui_harness.py 的 `--torrents` 同值, 供数据契约断言使用。 */
export const TORRENTS = 300;

/** 参与冒烟的皮肤。`console` 不在其中: 人工冒烟脚本 ui_smoke.cjs 的 `--ui` 也只认 prism|atlas。 */
export const SKINS = ['prism', 'atlas'];

/**
 * 起桩服务的命令。用 `uv run` —— 与 .commands/dev/config.toml 的 dev.harness 保持**同一条口径**
 * (裸 `python` 会缺 qbittorrentapi, 别改成系统 python)。
 *
 * ⚠ 收尾依赖(踩过, 见 memory-bank/pitfalls/testing/smoke.md「webServer 收尾」条):
 * Playwright 停 webServer 时等的是子进程的 `'close'` 事件, 而 Node 的 `'close'` 要求**所有
 * stdio 管道都关闭**。Windows 上它用 `taskkill /pid <pid> /T /F`(同步 spawn), 非 Windows 上
 * 用 `process.kill(-pid, SIGKILL)` 杀整个进程组 —— 两条路都必须能**真正杀掉** `uv run` 拉起的
 * 子进程, 否则 Playwright 会卡在收尾不退出、桩服务残留占着端口。
 */
export const HARNESS_CMD = `uv run python scripts/ui_harness.py --torrents ${TORRENTS} --port ${PORT}`;

/**
 * 就绪探测 URL —— 用**页面**而不是 `/api/` 下的接口: 只探接口会被"旧进程仍在服务旧代码"蒙过去
 * (旧进程可能页面 404 但 /api 仍 200), 这是 smoke.md 里记的判据。
 */
export const READY_URL = `${BASE_URL}/${SKINS[0]}/`;
