// 扩展侧**硬上限**(第二条闸: 后端出错时的兜底) —— 唯一事实源: 后台与选项页共用同一份。
//
// 第一道闸在后端(min_torrent_interval + 小时/天配额 + 熔断)。这里是**独立的**计数:
// 即便后端代码写错、配置被改坏、或有人手工灌任务, 浏览器也不会把站点打爆(2026-09-25 用户指定)。
//
// 口径: **「访问」与「下载种子」分开计数**, 各自时/日两级 ——
//   page    = HR 统计页访问(含兜底渲染那一次额外的顶层导航);
//   torrent = .torrent 下载。
// 窗口键(idempotent, 与后端同一套口径): 存下当时的「小时键 / 日键」, 键变了就把计数归零 ——
// 所以 MV3 的 service worker 被回收重启也不会把计数重置掉(靠键比较, 不靠进程存活)。
//
// ❗超限时扩展**拒绝该次请求并如实回传**(kind='ext-quota' + retry_after), 由后端记成
//   「本轮让位」而不是一次取数失败 —— 后者会推进熔断, 把「后端频控失效」误报成「站点故障」。
const SITE_CAPS = {
  page: { label: 'HR 页访问', perHour: 10, perDay: 50 },
  torrent: { label: '.torrent 下载', perHour: 50, perDay: 200 },
};

//: 计数台账在 chrome.storage.local 里的键: { "<host>": { page: {hk,dk,hour,day}, torrent: {...} } }
const SITE_LEDGER_KEY = 'siteLedger';
