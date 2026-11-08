# 沙箱工作区里新建的 venv 读不到自己的 pyvenv.cfg (exit 107)

> 摘要: agent 沙箱给工作区目录打了 Low 完整性标签 + 沙箱 capability ACE, 在**工作区内**新建的 venv, 其 `Scripts/python.exe` 读不到**同目录的** `pyvenv.cfg` —— 报 `Cannot read ... pyvenv.cfg` / exit 107 (`uv run` 另报 `uv trampoline failed to spawn Python child process: permission denied (os error 5)`); 重建 venv 无效, 把同一份 venv 拷到工作区外即正常。处置 = `UV_PROJECT_ENVIRONMENT` 指到工作区外。
> 触发: exit 107, Cannot read pyvenv.cfg, pyvenv.cfg 不可读, uv run 失败, 工具 venv 坏, permission denied os error 5, uv trampoline, venv 重建无效, gtm 测试跑不了, UV_PROJECT_ENVIRONMENT, uv sync --reinstall, trampoline 失效, 既有 venv 突然坏
**Refs:** memory-bank/tasks/26-10-21-test-gtm-coverage-gate.md

### 工作区内 venv 自读 pyvenv.cfg 失败 → 重建也没用

- **触发**: 在 agent 工具 shell 里对**工作区内的子包**(实测 `tools/global-traffic-monitor`)跑它的依赖同步或测试命令(`commands run env.sync` / `commands run test.gtm`, 二者底层分别是 uv 的依赖同步与测试执行)。venv 建在工作区内(`<子包>/.venv`), 且该工作区目录树带着沙箱标记(`icacls <工作区>` 可见 `Mandatory Label\Low Mandatory Level:(OI)(CI)(NW)` + `S-1-4-<capability>:(OI)(CI)(W,D,DC)`)。工作区**外**的老 venv(如仓库根 `.venv`, 打标前建的)不受影响, 所以「主仓能跑、子包不能跑」。
- **判别**: 三层证据, 缺一不可 ——
  · `cat .venv/pyvenv.cfg` **能读**(文件本身没坏, 内容正常), 但 `.venv/Scripts/python.exe -V` 报 `Cannot read '<abs>/pyvenv.cfg'` 且 **exit 107**(`uv run` 则报 `uv trampoline failed to spawn Python child process ... permission denied (os error 5)`)。
  · 删掉重建**症状不变**(换 uv 托管解释器 / 换 `--python` 装成完整副本, 都还是 107) ⇒ 不是 venv 内容坏, 是位置坏。
  · `cp -r .venv /tmp/venvcopy && /tmp/venvcopy/Scripts/python.exe -V` **正常** ⇒ 判死: 位置问题, 不是 venv 问题。
  · 反证: 同一台机器上 `icacls .venv /setintegritylevel Medium` / `icacls /grant` 一律「拒绝访问」—— 沙箱 token 不给改 ACL 的权限, 所以**别在 ACL 上折腾**。
- **处置**: 把工程环境放到工作区外, 用 uv 的官方开关重定向:
  ```bash
  export UV_PROJECT_ENVIRONMENT=/tmp/gtm-venv     # Windows: H:/Temp/gtm-venv
  commands run env.sync && commands run test.gtm  # 仍在子包目录里跑, addopts/rootdir 口径不变
  ```
  之后 `commands run <task>`(引擎继承调用方环境)同样能跑。**这是本机沙箱的绕道, 不是项目口径**: 命令配置文件里**不要**写死 `UV_PROJECT_ENVIRONMENT`, CI 与用户本机照旧用子包内 `.venv`。踩到时在交付说明里点明「本机数字取自工作区外 venv, 与 CI 同一份 addopts」。
- **复发**: 0

### 既有 `.venv` trampoline 突然失效 —— `uv sync --reinstall` 一条愈 (同族不同症, S5/S6 轮实测)

- **触发**: 主仓/子包**既有、此前一直能跑**的 `.venv`(工作区外或打标前所建, 与上面第一条的位置前提相反)在某轮工具 shell 里 `uv run` 系命令突然全部起不来, 报 uv trampoline spawn 失败类症状 —— 同族(都是 trampoline 起不来), 不同症(位置与 ACL 都没问题, 是 venv 内部 trampoline/环境本体损坏陈旧)。
- **判别**: 与第一条的三点区别 —— ① 位置无关: 同一份 venv 不存在「拷出去就好」的反证; ② `pyvenv.cfg` 可读性与 ACL 均正常, `icacls` 无 Low 标签差异; ③ 时间轴: 环境之前恒可用, 突现失效(第一条是「工作区内新建即坏」)。同时命中三点 ⇒ 本条; 若拿不准, 先试本条处置(代价低), 愈不了再回第一条判别链。
- **处置**: `uv sync --reinstall`(即 `commands run env.sync` 的 reinstall 形态)整环境重建, 一次愈, 不必动 ACL、不必 `UV_PROJECT_ENVIRONMENT` 重定向; 重建后照常 `commands run <task>`。
- **复发**: 0
