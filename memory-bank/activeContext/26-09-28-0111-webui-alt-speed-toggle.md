# ALT-01 WebUI 备用速度切换(乌龟)实施

> 摘要: 计划 26-09-28-0037 三模板中用户定 TPL-A(状态栏乌龟单图标双态) + TPL-C(限速浮层主/备同窗双组), 已实施完毕。后端 qbapi(get/set_alt_speed_limits + get/toggle_speed_limits_mode) + 路由(/api/speed/alt[/toggle], 金清单已同步) + 命令(speed_alt_set/speed_alt_toggle); 前端三主题 i-turtle sprite + .sb-alt 按钮 + 弹窗双组卡片 + speedAlt 状态/提交(未改动组不下发)。模式状态读 statsServer.use_alt_speed_limits(零新增查询); 备用限速走 app/preferences alt_*(qB 5.0 迁移只动主速度键)。test.full 1814 passed + 3 skipped(基线 26-09-28-0111); 档案 tasks/26-09-28-webui-alt-speed-toggle.md。
> 最后活动: 2026-09-28 01:11

## 正在进行

- 等待用户说「提交」—— 收尾回写已全部落盘(档案/切片/基线/坑条/索引重建)。

## 关键决策

- 切换用 toggle 端点原生语义, 新状态由主轮询回读(不本地预翻转)。
- 弹窗应用一次提交两组: 主速走既有 override 通道, 备速走 speed_alt_set; 任一组失败留在窗内重取回填。
- 曲线任务只写主速度, 备用速度无接管方(命令 docstring 已注明)。
- _doc-map 超 index-auto cap 本轮走"收口生成器头部"而非调 CAP_POLICY(坑条已补进 pitfalls/kb/cap-counting.md)。
