# 包目录迁移的 import 清点纪律

> 本文件是生成物, 不要手改 —— 由 gen_kb_index.py 扫描三行头元数据生成。
> 库内细路由见 [../_index.md](../_index.md)。
> 摘要: 移动/归拢包目录时 import 引用清点的漏网形态与守阵同步清单 —— 方案 C 实施实录 (W4a 五轮、W4b 三轮)。
> 触发: 目录迁移, 包移动, git mv, import 更新, 引用清点, 守阵路径, mock 字符串, logger 名

## 六类必查引用形态 (宽模式一次性扫全, 别按记忆列清单)

移动 `X.py` 前对全仓 (src / tests / scripts / docs 注释) 跑**一组宽正则**, 覆盖以下全部形态;
任何一种只靠印象列清单都会漏 (方案 C 实施中 ①②③ 各漏过一轮):

1. **点号 from-import**: `from .x import` / `from ..x import` / `from ...x import` —— 按目录深度逐档处理
2. **空格模块对象形态**: `from . import x` / `from .. import x` —— 点后是**空格**, 上面正则匹配不到;
   `from auto_qb import x` (tests 常用) 同属此类
3. **逗号多名字形态**: `from .. import curves, utils` —— 名字在列表中段/尾部都会漏, 必须按**行**扫含名字的 from 行
4. **mock/patch/setattr 字符串**: `mock.patch("auto_qb.qbmanager.time.sleep")` / `monkeypatch.setattr("auto_qb.utils.urlparse", ...)` —— 字符串里的模块路径, 编译期查不出
5. **TYPE_CHECKING 块与函数内延迟导入**: 顶层 grep 命中不了 `if TYPE_CHECKING:` 与函数体内的 `from .x import` —— 按**文件**扫而非按行
6. **动态加载脚本**: `importlib.util.spec_from_file_location("qb_capture", "scripts/qb_capture.py")` —— test 动态加载的脚本自己还有一套 import (W4a 最后一个漏网点)

## 清点时的天然陷阱

- **同名包内模块**: `rules/expr/errors.py` 与 `config/errors.py` 与根 `errors.py` 同名 ——
  `from .errors import` 在不同文件指向完全不同的目标, 替换前必须逐文件确认归属, 不能全局一把梭。
- **anchor 跳文件**: 批量替换脚本用"文件含某形态才处理"的 anchor 时, anchor 必须覆盖**全部待改形态**;
  anchor 只认点号形态会整文件跳过只含空格形态的文件 (test_exporter/test_rule_engine 各踩一次)。
- **相对深度逐档数**: `web/`→`webui/server/` 是**+1 层** (上游引用 `..`→`...`), 而
  `mixins/`→`core/mixins/` 也是 +1 层但 `mixins/web_commands.py`→`webui/commands.py` **不变** ——
  每个移动对单独数层, 别套用上一个的结论 (W3 曾把 webui/views.py 的 `..` 误加成 `...` 越界)。
- **包内既有跨包依赖**: 移动会改变"谁依赖谁"的表面形态 —— infra/notify.py 引 config.NotifyConfig、
  rules/base.py 引 qbmanager/qbapi 都是**既有事实依赖**, 移动时同步改路径并把例外写进依赖纪律,
  不要当成"不该存在的引用"顺手删。

## 守阵同步清单 (路径硬编码处)

- 源码文本守阵: `open(...)` 钉源码路径的 (test_qbmanager → core/qbmanager.py;
  test_sim_corpus `_EXPECTED_PROBES` 键 + 红验 fixture 的 tmp_path 路径)
- 前端资产守阵: test_web 钉 `webui/static` 绝对拼接路径
- logger 名断言: `getLogger(__name__)` 的模块名随包移动漂移 (auto_qb.mixins.web_commands →
  auto_qb.webui.commands 等), caplog 按 `r.name` 断言的守阵必须同步;
  **例外**: 有意冻结的命名空间 (webui/server 包冻结 `auto_qb.web`, 包改名不改 logger 名)
- 生产侧同构点: FastAPI StaticFiles 挂载的 `os.path.dirname(__file__)` 相对拼接、
  图标等资源路径、pyproject.scripts 的入口模块路径

## 验证顺序 (每移动一波)

`python -c "import auto_qb, auto_qb.core, ..."` 导入冒烟 (先抓循环导入/越界)
→ `pytest --collect-only` 收集零 ERROR (抓 import 面)
→ 全量 pytest (行为零变更判据) → 守阵红 = 路径同步项, 逐个核对后与移动同波提交。
