# dev.harness 是常驻桩服务, 不是断言合集

> 摘要: `dev.harness` 只起一个 **uvicorn 常驻服务**(脚本末尾 `uvicorn.run(...)` 阻塞, 包内 timeout 900s), **不跑任何断言**; 它的 `when` 曾写「浏览器冒烟（真浏览器跑前端断言合集）」, 与命令实际形态不符 —— 按"冒烟闸门"跑它会**挂到超时**(2026-10-11 实测后台跑 6 分钟零输出, 只能 TaskStop)。断言面在 `commands run dev.e2e`(Playwright 自带 webServer 自动起/收桩)。`dev.harness` 的正确用途 = 手动开浏览器看 / 给外部工具连桩。包内 `when`/`note`/`doc` 已一并订正。
> 等级: L0
> 触发: 跑前端冒烟; dev.harness 卡住不退出; 后台任务无输出; "断言合集"跑哪条命令

## 触发 / 判别 / 处置

- **触发**: 改完前端要"跑真浏览器冒烟", 顺手选了 `dev.harness`。
- **判别**: 命令长时间无输出且不退出; 或 `commands show dev.harness` 的展开里**没有 test runner**(只有起桩脚本, 末尾是 `uvicorn.run(app, ...)` —— 设计上就不返回)。
- **处置**: 断言一律走 `commands run dev.e2e`(全量集; 分钟级的 fast 子集见 `dev.e2e` 的包内说明); `dev.harness` 只在需要**手动**开浏览器或给别的工具连桩时用, 用完按端口清(`commands run dev.port-kill -- <port>`)。
- **同族(症状同是"挂住", 成因不同)**: 本机 node 的 `spawnSync` 管道 stdio EBUSY 会让 e2e 用例**全 PASS 但命令不退出**(见 [playwright-teardown](playwright-teardown.md))—— 那条是**收尾失败**, 本档是**设计如此**, 别混。
