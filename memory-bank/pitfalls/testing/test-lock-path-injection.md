# S12 后测试装配 Storage 必须注入 lock_path, 否则命中真实用户级目录

> 摘要: 工具侧 `Storage` 的默认锁锚点(S12/D8)从 `data_dir` 迁到用户级指针目录(`%LOCALAPPDATA%/global-traffic-monitor/instance.lock` 等) —— 于是 `Storage(str(tmp_path))` 后直接 `acquire_lock()` 的测试**不再动 tmp**, 而是去锁真实用户目录: 沙箱内 `os.makedirs` 报 `PermissionError [WinError 5]`, 沙箱外更隐蔽(污染真实目录 / 跨用例互相抢锁)。修法 = 每处装配显式传 `lock_path=<tmp>/instance.lock`, 发现指针同理传 `endpoint_file=<tmp>/endpoint.json`。
> 等级: L0
> 触发: 加/改工具侧测试, Storage, acquire_lock, 真实用户目录, PermissionError WinError 5, 拒绝访问, AppData, LOCALAPPDATA, global-traffic-monitor, instance.lock, endpoint.json, 锁锚点, 跨用例抢锁, S12

## 现象与处置(2026-10-17 实测, 专题 26-10-17-0339 S12)

- **触发**: S12 把单实例锁锚点移出 `data_dir`(改锚到用户级指针目录)后, 任何仍写 `Storage(str(tmp_path))`(不传 `lock_path`)再 `acquire_lock()` 的既有测试。
- **判别**: 工具套件里该用例报 `PermissionError: [WinError 5] 拒绝访问。: 'C:\\Users\\<user>\\AppData\\Local\\global-traffic-monitor'`(沙箱拦 `os.makedirs` 白名单外目录); 沙箱外表现更隐蔽 —— 真实用户目录被创建/被锁, 多个用例或真机运行中的工具互相抢同一把锁。
  根因: `Storage.__init__` 默认 `lock_path = instance_lock_path()`(用户级目录), 与 `data_dir` 解耦是**设计**(D8), 但测试需要 hermetic。
- **处置**:
  ①装配点(`make_storage` / `make_server` / `make_env` 及直接构造处)统一显式传 `lock_path=str(tmp_path / "instance.lock")`;
  ②发现指针同理: `ControlServer(endpoint_file=str(tmp_path / "endpoint.json"))`, 否则 `start()` 会往真实用户目录写 `endpoint.json`;
  ③默认 installer 替身补 `is_registered()`(start() 写指针会探 `autostart_registered`), 免得跑真 `schtasks`/`systemctl`;
  ④换锁锚点 / 默认落点一类「设计即解耦」的改动, 收尾必跑**全量工具套件**(不只改动的那个文件), 才能扫出所有未注入的装配点。
