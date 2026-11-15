# docker CLI 格式化字段默认截短 ID —— 跨命令比对镜像/容器身份必须 --no-trunc

> 摘要: `docker images --format {{.ID}}` 与 `docker ps --format {{.Image}}`(镜像已无 tag 时)默认输出**截短 12 位** ID, 而 `docker container inspect --format {{.Image}}` 给的是 **full `sha256:...`** —— 两个来源直接做相等比对**恒失配**: 白名单「活面保护」把在跑容器的镜像 tag 误判成可删候选, 「引用中不删」判据把被容器引用的悬空 ID 漏筛。修法 = 枚举命令一律 `--no-trunc`, 让两侧都落在 full sha 域; 守阵钉调用形态防回归。
> 触发: docker images ID, docker ps Image, 截短, 12 位, sha256, --no-trunc, 镜像比对, 活面, 悬空, 误列候选

**Refs:** memory-bank/tasks/26-11-15-test-linux-clean.md

### 演练把在跑容器的镜像 tag 列成「将删」

- **触发**: 2026-11-15 test.linux-clean 演练轮(本仓宿主): 容器 auto-qb-testbed 在跑, 镜像 `auto-qb-testbed:073a459e` 与 `latest` 同 ID(`sha256:5d0c72fb...`)。三层「旧 tag 候选」逻辑含活面保护(tag 的镜像 ID == 在跑容器镜像 ID 则保留), 但实测仍输出「将 untag auto-qb-testbed:073a459e」。
- **判别**: `docker container inspect --format {{.Image}}` = `sha256:5d0c72fb...`(full), 而 `docker images --format {{.ID}}` = `5d0c72fbcf71`(12 位截短)—— 字符串相等恒 False, 活面规则静默失效。**不是**选择逻辑写错, 是两个 docker 子命令的默认输出域不同。悬空「无容器引用」判据同理: `docker ps -a --format {{.Image}}` 对已无 tag 的镜像也显示截短 ID, 与 `--no-trunc` 枚举出的 full sha 悬空候选永不相交 → 筛除永不生效。
- **处置**: 所有要拿 ID/镜像身份做比对的枚举一律 `--no-trunc`(images / images -f dangling / ps -a 三处), 让活面比对与引用筛除都落在 full sha 域; 守阵 `test_images_calls_use_no_trunc` 钉调用形态(`--no-trunc` 出现次数), 改坏即红。反向做法(两侧都归一成短 ID 前缀比对)也可行但要多一层归一逻辑, 不如让 docker 直接给 full。接线单点: `.commands/test/scripts/linux_clean.py`(main 宿主面枚举段)。
- **复发**: 1 —— 2026-11-15(test.linux-clean 落地轮): 守阵 18 条全绿仍漏 —— 守阵只钉了**纯函数**(喂的是合成 full sha, 合成域内自洽), 失配发生在**真实 docker 调用的输出域**上, 纯函数钉面天然看不见; 实机演练(无参只读)才暴露。**为什么没提前命中**: 守阵纪律「不依赖本机 docker 状态」导致接线面(调用形态)只有一条 count 断言, 且当时只数了 images 两处、漏了 ps 一处(复评轮补齐 count==3)。教训: 纯函数守阵 + 真实 CLI 接线之间有结构性盲区, 涉外部命令输出域的接线必须有**实机演练轮**(哪怕只读)兜底, 且守阵要把**每一处**调用的形态都数到。
