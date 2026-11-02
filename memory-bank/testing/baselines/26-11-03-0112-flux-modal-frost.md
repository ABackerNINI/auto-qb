# 4914 passed + 2 skipped —— 找回 flux 弹窗毛玻璃(blur 透视底回归) + 透明修复双守阵后全量基线

> 摘要: 找回 flux 弹窗毛玻璃(blur 透视底回归) + 透明修复双守阵后全量基线
> 基线时间: 2026-11-03 01:12
**Refs:**

## 验收数字

`commands run test.full`(2026-11-03 01:46, rebase 后的 develop)实测:

```text
TOTAL                                                22531    134   7732    128    99%
4914 passed, 2 skipped, 3 warnings in 172.17s (0:02:52)
```

口径: 根目录全量(Windows 并行 `-n 8` + 覆盖率), Total coverage 99.11%; 与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。
首次全量(01:12, rebase 前)为 4907 passed; rebase 并入 `73949f10`(大文件拆分 R1)后 +7 个测试。先前两次同命令分别在 HR discovery 端口用例上撞 `WinError 10013`(`test_start_all_busy_returns_false_and_retries` / `test_runtime_discovery_bind_failure_keeps_data_endpoint`), 单跑均转绿 —— 并行 `_free_port` 抢端口的环境 flake, 与本轮 CSS 改动无关(已入池 issue 26-11-03-0115)。

## 本改动面

- `src/auto_qb/webui/static/flux/css/components.css`: `--msg-surface` 拆角色底 `--msg-base`(`.modal-mask` 回落 `--bg-card`/alpha .82, 提示条续走兜底 `--bg-elev`); `.modal` 补 `-webkit-backdrop-filter` 前缀别名, 无前缀 blur(14px) 保留
- `tests/webui_static_scan_css.py`(R1 拆分后承载 CSS 扫描; 原 `tests/test_webui_static_skins.py` 已拆销): 新增 `_scan_flux_modal_frost`(弹窗 blur 双写法 + 半透明底 vs `--bg-pop` 不透明 + 八类无 blur 浮层仍消费 `--bg-pop` + `--bg-card` alpha < `--bg-elev` 双向守阵); `_scan_backdrop_filter` 计数口径改为按规则体归并(`-webkit-` 别名不重复计数), flux 预算仍为 4
- 口径回写 `memory-bank/conventions/webui.md` 与 `memory-bank/pitfalls/web-ui/overlays.md`
