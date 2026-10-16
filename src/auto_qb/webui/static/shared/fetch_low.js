/* fetch_low.js — 低层带超时 fetch 单点(issue 26-10-16-1303-bug-webui-raw-fetch-bypass-no-timeout)
 *
 * 背景: 前端原有 5 处请求**有意或历史地**绕开 auth.js::_request(那一处已有请求级超时, 见
 * 26-10-16-0954), 直接裸 fetch:
 *   - 启动分片装载(boot.js) —— 鉴权就绪之前, 走不了 api() 的"无凭证不出网"门;
 *   - 本机免鉴权判定(lifecycle.js), 原因同上;
 *   - 导出下载(commands.js) —— 二进制流, 而 _request 固定按 JSON 解析;
 *   - 快捷键密钥读写(shortcuts.js x2) —— 自带 Authorization 头与自家错误收敛。
 * 裸 fetch 没有超时: 连接静默失效(服务端不响应 / TCP 半开 / 中间设备丢包)时 await 永不返回,
 * 各调用方的收尾动作整条停在中途 —— 装载链停在当前片(应用停在 v-cloak 前)、免鉴权判定停在
 * "验证中"、导出回执停在"进行中"、密钥面板的 kbKeysLoading 永不复位。界面无提示、不自愈。
 *
 * 本文件是这一族的**低层单点**: 只做「带超时的 fetch」, 返回**原始 Response** —— 不解析 JSON、
 * 不判 401 语义、不加任何请求头(那些是 auth.js::_request 的高层契约, 由调用方各自持有)。
 * !超时值: 与 auth.js 的请求级超时(AQB_FETCH_TIMEOUT_S/MS)是同一条口径的两处实现 —— auth.js
 *   那一处因工作区写入判据暂无法复用本单点(见 pitfalls/ops/agent-write-guard-secret-false-positive),
 *   两值靠守阵钉住相等(test_frontend_raw_fetch_timeout_single_point), 不要只改一边。
 * !boot.js 不用本文件: 它在清单脚本之前执行(装载链本身是放行其它脚本的前提), 自带一份等价的
 *   内联超时(AQB_BOOT_PART_TIMEOUT_MS, 值更短 —— 它阻塞整个首屏, 早失败更重要)。
 * !本文件不挂 window.*(不是 Vue mixin 片段), 且必须排在 tpl-manifest 的 scripts 最前
 *   (定义先于一切调用点)。
 */
const AQB_FETCH_LOW_TIMEOUT_S = 15;  // 秒值单点; 与 auth.js 的 AQB_FETCH_TIMEOUT_S 同值(守阵钉)
const AQB_FETCH_LOW_TIMEOUT_MS = AQB_FETCH_LOW_TIMEOUT_S * 1000;

/* 带超时的裸 fetch: 返回原始 Response(调用方自己判 ok / 解析体)。
 * 超时与外部取消收敛到同一个 controller(外部 signal 用**链接**而非覆盖 —— 与 _request 同款,
 * 防"将来加取消时被本函数的 signal 静默顶掉"); 定时器无论走哪条路径都在 finally 清掉。
 * AbortError 翻译成中文短句(超时带秒数 + timeout 标记), 与 auth.js::_request 文案同源 ——
 * 调用方的既有 catch / 错误态零改动就能显示「请求超时(15s)」而不是 "The operation was aborted"。 */
function aqbFetch(path, opts) {
  const options = opts || {};
  const ctl = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    ctl.abort();
  }, AQB_FETCH_LOW_TIMEOUT_MS);
  const ext = options.signal;
  if (ext) {
    if (ext.aborted) ctl.abort();
    else ext.addEventListener("abort", () => ctl.abort(), { once: true });
  }
  return fetch(path, { ...options, signal: ctl.signal }).catch((e) => {
    // fetch 与 body 读取都可能被中止, 两类都在这一处判定(与 _request 同口径)
    if (e && e.name === "AbortError") {
      const err = new Error(timedOut ? "请求超时(" + AQB_FETCH_LOW_TIMEOUT_S + "s)" : "请求已取消");
      err.timeout = timedOut;
      throw err;
    }
    throw e;
  }).finally(() => clearTimeout(timer));
}
