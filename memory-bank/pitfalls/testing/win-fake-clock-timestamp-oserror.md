# Windows 上 1970 前假时钟过 datetime.timestamp() 抛 OSError(不是 ValueError)

> 摘要: 生产纯函数新增「缺 self 状态时按传入 now 现场推算本地日/月 epoch」的回落分支, 被既有用例的 1970 附近假时钟(流量族惯用 `H1 = 11 * HOUR = 39600` 量级)首次触达 —— Windows 上 `datetime.timestamp()` 对 1970 前**本地**日期抛 `OSError [Errno 22] Invalid argument`, 一批与本次改动无关的既有用例在 Windows 面红、Linux 面绿。修法 = 两级推算包 `try/except (ValueError, OSError, OverflowError)` 静默缺级: 生产时钟恒正(≥1.7×10^9)该面不可达, 纯增益面缺一级只回到改动前形态。通用教训: 新读侧函数被假时钟 first-touch 时, 本地时间换算的异常面要按平台放宽, 且**别改用例时钟迁就实现**。
> 触发: Windows, 假时钟, 1970, timestamp, OSError, Errno 22, Invalid argument, v4_day_epoch, v4_month_epoch, 无关用例集体红, Linux 绿 Windows 红, 新增读侧函数, 本地时间换算, 异常型平台差分

**Refs:** memory-bank/tasks/26-10-14-webui-qb-traffic-agg-live-tail.md

### 假时钟(1970 附近)过 Windows 本地时间换算抛 OSError

- **触发**: 给生产函数新增「自身状态缺省时按传入 `now` 现场推算本地日/月 epoch」的分支(如 `agg.day_epoch is None -> v4_day_epoch(now)`), 而该函数的调用面包含喂 1970 附近人工时钟的既有用例; 或排查「本次只加了读侧分支, 却有一批与本次无关的既有用例在 Windows 上红、Linux 上绿」。
- **判别**: 栈顶落在 `datetime.timestamp()`(常经 `v4_day_epoch` / `v4_month_epoch` 的 `datetime.fromtimestamp(...)` 本地时区往返), 异常是 `OSError: [Errno 22] Invalid argument` 而**非** `ValueError` —— Windows 上 1970-01-01 之前的本地时间没有合法系统时间映射, 抛 OSError; Linux/macOS 同构造可走 ValueError 或直接成功(时区依赖), 于是表现为平台差分红灯。假时钟量级判据: 传入 `now` 在 10^5 秒上下(1970-01-01 前后一两天内); 生产时钟恒为正、≥1.7×10^9。
- **处置**: 两级(日/月)推算包 `try/except (ValueError, OSError, OverflowError)` 后 `pass` 静默缺该级, docstring 注明「生产时钟恒正不受影响, 纯增益面缺该级只回到修复前形态」。**别**只 catch `ValueError`(Windows 上是 OSError, 漏一个平台照红); **别**改既有用例的时钟去迁就实现(那会动无关守阵的时间基准, 把测试问题转成契约问题); **别**让异常外溢淹没真实缺陷面。
  **守阵**: 既有假时钟用例直跑新分支即是守阵(本次一批既有用例当场红验); 新写用例若要覆盖正路径, 用 `time.time()` 量级的真实时钟。
  **泛化**: 凡是「本地时区时间换算」(fromtimestamp / timestamp / 日界字符串)在生产新路径上首次触达, 先问调用面里有没有假时钟; except 元组按 `(ValueError, OSError, OverflowError)` 三型收, Windows 的 OSError 是最易漏的一个。
