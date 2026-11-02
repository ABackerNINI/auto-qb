# 4907 passed + 2 skipped —— 找回 flux 弹窗毛玻璃(blur 透视底回归) + 透明修复双守阵后全量基线

> 摘要: 找回 flux 弹窗毛玻璃(blur 透视底回归) + 透明修复双守阵后全量基线
> 基线时间: 2026-11-03 01:12
**Refs:**

## 验收数字

`commands run test.full`(2026-11-03 01:12)实测:

```text
TOTAL                                                22531    134   7732    128    99%
4907 passed, 2 skipped, 3 warnings in 206.74s (0:03:26)
```

口径: 根目录全量(Windows 并行 `-n 8` + 覆盖率), Total coverage 99.11%; 与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。
前两次同命令分别在 HR discovery 端口用例上撞 `WinError 10013`(`test_start_all_busy_returns_false_and_retries` / `test_runtime_discovery_bind_failure_keeps_data_endpoint`), 单跑均转绿 —— 并行 `_free_port` 抢端口的环境 flake, 与本轮 CSS 改动无关。

## 本改动面

- `src/auto_qb/webui/static/flux/css/components.css`: `--msg-surface` 拆角色底 `--msg-base`(`.modal-mask` 回落 `--bg-card`/alpha .82, 提示条续走兜底 `--bg-elev`); `.modal` 补 `-webkit-backdrop-filter` 前缀别名, 无前缀 blur(14px) 保留
- `tests/test_webui_static_skins.py`: 新增 `_scan_flux_modal_frost`(弹窗 blur 双写法 + 半透明底 vs `--bg-pop` 不透明 + 八类无 blur 浮层仍消费 `--bg-pop` + `--bg-card` alpha < `--bg-elev` 双向守阵); `_scan_backdrop_filter` 计数口径改为按规则体归并(`-webkit-` 别名不重复计数), flux 预算仍为 4
- 口径回写 `memory-bank/conventions/webui.md` 与 `memory-bank/pitfalls/web-ui/overlays.md`
