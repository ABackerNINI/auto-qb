// 地址归一化: 选项页与后台共用**同一份**(避免两条路径各自演化)。
//
// 为什么必须有这层: 浏览器 API 对格式极其严格, 而报错全都指向不了根因 ——
//   · `chrome.permissions.request` 只吃**匹配模式**(必须带 scheme), 裸域名报
//     "Invalid value for origin pattern xxx: Missing scheme separator."(未捕获的拒绝);
//   · `fetch('127.0.0.1:8788/x')` 会被当成**相对地址**解析到扩展自己的 origin, 失败只报
//     "TypeError: Failed to fetch"; `localhost` 还可能解析到 IPv6 回环, 而后端 bind 的是 127.0.0.1;
//   · 后端原生是明文 HTTP; 写 https 只对「反代终止 TLS」的部署有意义 —— scheme **保留不折**
//     (去端口+跨机, 计划 26-10-14-1241: 裸填补 http://, 写 https:// 的用户是反代形态)。
// 所以: 一律先归一化成"唯一合法形态", 再交给浏览器 API 或落盘。
//
// 主机判据(计划 26-10-14-1241 §01 派生口径): 回环 ∪ 私网段(10.* / 172.16-31.* / 192.168.*)
// —— 后端默认只听回环, 配了 hr_check.channel.host 才到私网; 公网域名/地址一律拒(部署形态
// 不支持, 也是安全边界)。主机名无法按字面量分类(不做 DNS), 不支持 —— NAS 请填内网 IP。
//
// 本文件**不引用 document / chrome**, 是纯函数 —— 选项页用 `<script>` 载入、后台用
// `importScripts()` 载入, pytest 侧用 node 直接 eval 它跑用例(见 tests/test_extension_proxy.py)。

/**
 * 允许的端点主机判据: 回环(127/8、::1、localhost) ∪ 私网三段 —— 逐字面量判断, 不做 DNS。
 */
function isAllowedEndpointHost(hostname) {
  const h = String(hostname || '').toLowerCase();
  if (h === 'localhost' || h === '::1' || h === '[::1]') return true;
  const m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(h);
  if (!m) return false; // 其余形态(域名 / 非回环 IPv6)一律拒
  const octets = [Number(m[1]), Number(m[2]), Number(m[3]), Number(m[4])];
  if (octets.some((n) => n > 255)) return false;
  if (octets[0] === 127) return true; // 127.0.0.0/8
  const a = octets[0];
  const b = octets[1];
  if (a === 10) return true; // 10.0.0.0/8
  if (a === 192 && b === 168) return true; // 192.168.0.0/16
  if (a === 172 && b >= 16 && b <= 31) return true; // 172.16.0.0/12
  return false;
}

function hasScheme(text) {
  return /^[a-z][a-z0-9+.-]*:\/\//i.test(text);
}

/**
 * 解析端点/发现地址的公共层: 补 scheme(裸 host:port) -> URL 解析 -> scheme 域 -> 主机判据。
 * requirePort=true(数据端点)缺端口报错; false(发现地址)由调用方补默认端口。
 */
function parseEndpointUrl(raw, what, requirePort) {
  let text = String(raw || '').trim();
  if (!text) throw new Error(what + '为空');
  if (!hasScheme(text)) text = 'http://' + text; // 补 scheme(裸 host:port 是最常见的写错)
  let url;
  try {
    url = new URL(text);
  } catch (e) {
    throw new Error(what + '不是合法地址: ' + raw);
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error(what + '只允许 http/https: ' + raw);
  }
  if (!isAllowedEndpointHost(url.hostname)) {
    throw new Error(what + '只支持回环或内网地址(127.* / 10.* / 172.16-31.* / 192.168.*): ' + url.hostname);
  }
  if (requirePort && !url.port) {
    throw new Error(what + '缺少端口(数据端口随机化后由发现自动分发; 手动兜底时必填): ' + raw);
  }
  return url;
}

/** localhost 折 127.0.0.1(后端 bind 的是它); scheme 保留(https = 反代形态) */
function foldHost(url) {
  return url.hostname === 'localhost' ? '127.0.0.1' : url.hostname;
}

/**
 * 端点: `127.0.0.1:8788` / `http://localhost:8788/` / `https://192.168.1.10:8443` 都能收;
 * 统一成 `协议://host:端口`(scheme 保留; 缺端口报错)。不合法时抛 Error(消息可直接给用户看)。
 */
function normalizeEndpoint(raw) {
  const url = parseEndpointUrl(raw, '端点', true);
  return url.protocol + '//' + foldHost(url) + ':' + url.port;
}

/**
 * 发现地址: 同一套主机判据; **缺端口补 18788**(与后端 hr.discovery.DISCOVERY_DEFAULT_PORT
 * 同源, 协议守阵钉住)—— 用户只填 `http://192.168.1.10` 也合法。
 */
function normalizeDiscovery(raw) {
  const url = parseEndpointUrl(raw, '发现地址', false);
  const port = url.port || '18788';
  return url.protocol + '//' + foldHost(url) + ':' + port;
}

/**
 * 站点源: `pt.btschool.club` / `https://pt.btschool.club/x` 都能收;
 * 统一成 Chrome 要的匹配模式 `https://pt.btschool.club/*`。
 */
function normalizeOrigin(raw) {
  let text = String(raw || '').trim();
  if (!text) throw new Error('站点源为空');
  if (!hasScheme(text)) text = 'https://' + text; // !权限 API 只吃带 scheme 的模式
  let url;
  try {
    url = new URL(text);
  } catch (e) {
    throw new Error('站点源不是合法地址: ' + raw);
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error('站点源只允许 http/https: ' + raw);
  }
  if (url.hostname.indexOf('.') < 0 && url.hostname !== 'localhost') {
    throw new Error('站点源看起来不是域名: ' + raw);
  }
  return url.protocol + '//' + url.host + '/*';
}
