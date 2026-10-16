# global-traffic-monitor (gtm)

整机流量历史记录小工具 —— TrafficMonitor 替代。

独立于 auto-qb 主进程、开机自启: 以 psutil 采样整机全适配器流量 (排除回环与
down 网卡), 以 TrafficMonitor 兼容格式 (`history_traffic.dat`: 每行
"YYYY/MM/DD 上传KB/下载KB") 原子落盘; 当日累计上下行合计变化超过阈值
(默认 100 MiB) 时, 向所有存活订阅的 auto-qb 实例推送通知 (带单调事件号),
后者即时重读历史文件并刷新 WebUI 历史流量图。

## 定位与边界

- 工具是 `history_traffic.dat` 的**唯一写者**; 落盘用「临时文件 + os.replace」
  原子替换, 任意数量读者在任意时刻见到完整一致的文件。
- 工具**不参与**限速联动, 仅记录整机流量历史 (与 TrafficMonitor 同口径)。
- 多个 auto-qb 实例可同时订阅 (各自端点 + token + 心跳租约), 互不干扰。
- 通知推送与文件落盘解耦: 推送失败不影响落盘, 订阅者丢失通知可靠慢轮询兜底,
  两条通道互为冗余。

## 依赖与隔离

- 运行时依赖仅 psutil + filelock; HTTP 控制面与客户端全部 stdlib
  (`http.server` / `urllib.request`) —— 三平台 pip install 即装。
- 自带独立 venv (uv 管理, 落在本目录 `.venv/`), 与 auto-qb 主项目环境互不污染。

## 目录结构

```
src/gtm/
  __init__.py   版本与包说明
  __main__.py   CLI 入口 (gtm)
  config.py     工具配置加载/校验/热重载 (S3)
  sampler.py    psutil 采样 + 日界累计 + 重置/恢复 (S1)
  storage.py    TM 兼容落盘 + state.json 原子写 + 单实例锁 (S2)
  server.py     本地控制面 127.0.0.1:8099 (S3)
  notifier.py   阈值事件推送订阅者 (S4)
  installer.py  三平台自启注册/卸载 (S5)
tests/          模块守阵 (随 S1-S9 逐步扩充; 当前仅 S0 冒烟)
```

## 开发

```bash
uv sync                 # 在本目录建独立 venv 并安装依赖
uv run gtm --version    # 验证安装与入口
uv run pytest -q        # 运行测试
```

## 自启 (S5 落地后)

Windows 计划任务 (登录时触发) / Linux systemd --user / macOS launchd, 由
auto-qb WebUI 设置页开关幂等注册, 也可命令行 `gtm install-autostart` 直接跑。

## 设计单点

实施计划: [memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html](../../memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html)
可行性报告: [memory-bank/reports/26-10-13-1034-report-global-traffic-source-lag.html](../../memory-bank/reports/26-10-13-1034-report-global-traffic-source-lag.html)
