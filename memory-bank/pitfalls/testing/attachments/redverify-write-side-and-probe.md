# 红验锚点 · 形态十写侧污染与不可达探针(外迁)

> 摘要: `pitfalls/testing/redverify-anchor-lineendings.md` 形态十与「探针放在不可达的分支上」两条原文整体外迁(2026-11-05 压缩), 正文原样照搬, 标题降一级以避开坑档条目扫描。
> 触发: write_text, read_text, CRLF 污染, LF 约定, eol=lf, ANCHOR-MISS, 两种读法, 基线复跑顺序, KB 回写, 探针空转, 不可达分支, readonly_config_paths, ui_only

## 形态十: LF 约定仓库里 `write_text()` 反向污染行尾 + `read_text()` 探针把暗点洗白（global-traffic-monitor S1 临时红验）

- **触发**: 对工具包 `tools/global-traffic-monitor/src/gtm/sampler.py`(纯 LF, 仓库 `.gitattributes` `eol=lf`)做 4 条临时单行锚点突变红验。首版脚本按老配方写: 读用 `read_bytes().decode()`, 写用 `write_text()`。第一处 apply 后**整文件被静默转成 CRLF**(`write_text` 默认 newline=None 在 Windows 把 `\n` 翻译成 `\r\n`), 之后每条 LF 锚点 `count == 0` ⇒ 第 2 条起全部 `ANCHOR-MISS` 假失配。
- **同源第二面(更隐蔽)**: 失配排查时用的**手工探针**是 `Path.read_text()` —— 它走 universal newlines, 把 CRLF **归一成 LF**, 于是探针显示"锚点明明在", 与脚本内 `read_bytes().decode()` 的结果**互相矛盾**, 一明一暗把"文件已被写脏"这个事实藏了一半。判别: 同一文件两种读法给出不同行尾事实时, 以 **bytes 层**为准, 先查是不是有人用文本模式写过。
- **第三面(脚本逻辑, 非行尾)**: 首版把「基线复跑」放在 `finally` 还原**之前**, 循环结束直接跑测试 —— 彼时文件还挂着最后一条变异, 于是基线复跑假红告警; 正确顺序是先还原再复跑。
- **处置**: ①红验/变异类脚本**全程 `read_bytes` / `write_bytes`**, 不碰文本模式(形态四③的同一条纪律, 这次是**写侧**污染); ②探针与脚本**必须同一种读法**(都用 bytes 层或都归一化), 两读矛盾出现时停手查写侧; ③`finally` 里先 `write_bytes(orig)` 再跑基线复跑, 并校验还原后字节恒等; ④仓库 LF 约定下, 任何在 Windows 上生成的 `.py` 落盘后都应复查 `CRLF count == 0`(本轮 sampler.py 被污染后是靠提交前复查发现的)。⑤**同一坑不止在红验脚本里**: **知识库文档回写**也踩过同型 —— 用 python `Path.write_text()` 改 tasks/activeContext/plans 三处 md/html, 5 个改动文件全被静默转成 CRLF(HEAD 里全是纯 LF); 判别仍是提交前 `git status` 全量 bytes 复查; 处置=**凡在 Windows 上改仓库内文本文件, 一律 `read_bytes`/`write_bytes`**(或用不翻译行尾的编辑器), KB 回写同样适用, 不只是红验脚本。

## 另一个同源陷阱: 探针放在不可达的分支上（空转）

- 修完锚点后仍有 1 条 SURVIVED(`readonly_config_paths__mutmut_2`, `continue` → `break`)。手工推算两者「应当有差别」(断链会丢后续字段)却仍绿, 先怀疑是判据/脚本问题而不是急着判等价变异 —— 查下去原因不在行尾, 而在**探针设计**: 首版合成结构把 `ui_only` 叶放在**顶层**, 而 `readonly_config_paths()` 走的是 `real_config_fields()`, 后者**已先行滤掉 ui_only** —— 那句 `if f.ui_only: continue` 在顶层**永远进不去**, `continue` 与 `break` 自然同结果, 探针空转。
  - **判别**: 一条变异在「手工算过应当有差别」的前提下仍 SURVIVED, 先问「我造的输入真的进得了那一行的分支吗」, 别急着判等价变异。
  - **处置**: 把合成结构改成**嵌套层** `[ui_only 叶][readonly 叶]` 放在一个非 readonly 的 object 段里 —— 嵌套段不做 ui_only 过滤, `continue`/`break` 才真正分化(改完即 KILLED)。
  - **这条与形态一二同源**: 三者都是「脚本/探针看着在验, 其实没验到」。红验的**唯一可信信号**是「锚点命中数 == 1 且跑完变红」, 缺任一半都不能算验过。
