# 3125 —— WEBUI 限速曲线预览图配色并入流量方向色族

> 摘要: 用户令「WEBUI 设置限速曲线预览图颜色改为上传/下载色, 与其它地方统一」。三套皮肤(console `css/components.css` / atlas `css/views.css` / prism `css/views.css`)的 `.ce-chart-up` / `.ce-chart-down` 五处配色(曲线线色 / 面积填充 / 悬停标记点 / 图例方向标 / 档位组方向条)由旧的自证配色(上传 `--warn` / 下载 `--blue`, 2026-09-28 引入)换成流量方向色族 `--today-up` / `--today-down`, 与状态栏速度组 · 今日流量卡 · 历史流量图 · qB 流量图同源; 面积填充改 `color-mix(in srgb, <令牌> 16%, transparent)`(从同一令牌现算, 主题改 up/down 指向亦同族), 令牌缺失回退 `--indigo` / `--teal`。纯 CSS 令牌改动, 未新增或修改任何 Python 测试。
> 基线时间: 2026-10-11 18:43
> 档案: [tasks/26-09-27-webui-curve-chart](../../tasks/26-09-27-webui-curve-chart.md)

**Refs:** memory-bank/tasks/26-09-27-webui-curve-chart.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步 `c2a723a3`; 工作树含本轮 3 个前端 CSS 文件改动时实测)
- 命令: `commands run test.full`
- **实测 (Windows)**: **3125 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16464 语句 / 148 未覆盖 / 5608 分支 / 133 partial; 本轮 31.00s)
- 改动面(摘要): `src/auto_qb/webui/static/console/css/components.css` + `src/auto_qb/webui/static/atlas/css/views.css` + `src/auto_qb/webui/static/prism/css/views.css`(纯 CSS, pytest-cov 不计); 回写件 `memory-bank/conventions/webui.md` / `memory-bank/tasks/26-09-27-webui-curve-chart.md` / 本切片 / `memory-bank/activeContext/26-10-11-1843-webui-curve-chart.md`。见 kb.baseline。
