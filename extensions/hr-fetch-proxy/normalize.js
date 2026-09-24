// 地址归一化: 选项页与后台共用**同一份**(避免两条路径各自演化)。
//
// 为什么必须有这层: 浏览器 API 对格式极其严格, 而报错全都指向不了根因 ——
//   · `chrome.permissions.request` 只吃**匹配模式**(必须带 scheme), 裸域名报
//     "Invalid value for origin pattern xxx: Missing scheme separator."(未捕获的拒绝);
//   · `fetch('127.0.0.1:8788/x')` 会被当成**相对地址**解析到扩展自己的 origin, 失败只报
//     "TypeError: Failed to fetch"; `localhost` 还可能解析到 IPv6 回环, 而后端只 listen 127.0.0.1;
//   · 后端端点是明文 HTTP(不提供 TLS), 写成 https 只会卡在握手。
// 所以: 一律先归一化成"唯一合法形态", 再交给浏览器 API 或落盘。
//
// 本文件**不引用 document / chrome**, 是纯函数 —— 选项页用 `<script>` 载入、后台用
// `importScripts()` 载入, pytest 侧用 node 直接 eval 它跑用例(见 tests/test_extension_proxy.py)。

/** 后端只监听回环(见 hr/server.py), 故端点主机只允许这几种写法 */
const LOOPBACK_HOSTS = ['127.0.0.1', 'localhost', '::1', '[::1]'];

function hasScheme(text) {
  return /^[a-z][a-z0-9+.-]*:\/\//i.test(text);
}

/**
 * 端点: `127.0.0.1:8788` / `http://localhost:8788/` / `https://127.0.0.1:8788` 都能收;
 * 统一成 `http://127.0.0.1:8788`。不合法时抛 Error(消息可直接给用户看)。
 */
function normalizeEndpoint(raw) {
  let text = String(raw || '').trim();
  if (!text) throw new Error('端点为空');
  if (!hasScheme(text)) text = 'http://' + text;  // 补 scheme(裸 host:port 是最常见的写错)
  let url;
  try {
    url = new URL(text);
  } catch (e) {
    throw new Error(`端点不是合法地址: ${raw}`);
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error(`端点只允许 http/https: ${raw}`);
  }
  if (LOOPBACK_HOSTS.indexOf(url.hostname) < 0) {
    // 后端只监听回环 ⇒ 填别的机器(含 NAS 上的实例)连不通; 那类实例应走"只读共享数据"
    throw new Error(`端点只能是本机回环地址(127.0.0.1): ${url.hostname}`);
  }
  if (!url.port) throw new Error(`端点缺少端口(后端默认 8788): ${raw}`);
  // localhost/::1 折成 127.0.0.1(后端 bind 的就是它); 协议固定 http(后端明文, 写 https 只会握手失败)
  const host = url.hostname === 'localhost' ? '127.0.0.1' : url.hostname;
  return `http://${host}:${url.port}`;
}

/**
 * 站点源: `pt.btschool.club` / `https://pt.btschool.club/x` 都能收;
 * 统一成 Chrome 要的匹配模式 `https://pt.btschool.club/*`。
 */
function normalizeOrigin(raw) {
  let text = String(raw || '').trim();
  if (!text) throw new Error('站点源为空');
  if (!hasScheme(text)) text = 'https://' + text;  // ❗权限 API 只吃带 scheme 的模式
  let url;
  try {
    url = new URL(text);
  } catch (e) {
    throw new Error(`站点源不是合法地址: ${raw}`);
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error(`站点源只允许 http/https: ${raw}`);
  }
  if (url.hostname.indexOf('.') < 0 && url.hostname !== 'localhost') {
    throw new Error(`站点源看起来不是域名: ${raw}`);
  }
  return `${url.protocol}//${url.host}/*`;
}
