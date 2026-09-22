# web/ 包拆分波次的新坑 (2026-09-22)

> 摘要: web.py → web/ 包拆分(plan 26-09-22-1857)实打实撞出来的四条 —— FastAPI 懒解析路由、包内 logger 命名、__file__ 基准降级、生成脚本转义陷阱。
> 触发: 拆 web/ 包, 改 factory, include_router, app.routes, getLogger, __file__, 生成脚本, 金清单守阵

### 新版 FastAPI 的 `include_router` 不再平铺路由
- **触发**: 遍历 `app.routes` 清点/断言路由(守阵/工具/文档)。- **判别**: 条目类型是 `fastapi.routing._IncludedRouter`(懒解析), `router`/`routes`/`app` 属性全取不到, 只有 `original_router`。- **处置**: 递归下钻 `original_router.routes`; 路由金清单守阵首版就因此假红(多出 0 / 丢失 9)。
### web/ 包子模块 logger 必须显式取名
- **触发**: 把子模块 logger 规范成 `getLogger(__name__)`。- **判别**: tests/test_web.py 多处按 `r.name == "auto_qb.web"` 断言 caplog(鉴权/token 3 条), 漂名必红。- **处置**: 包内所有子模块一律显式 `logging.getLogger("auto_qb.web")`。
### 单文件转包后 `__file__` 相对基准降一级
- **触发**: 包内用 `os.path.dirname(__file__)` 拼资源路径(静态目录等)。- **判别**: 路径静默失配, `isdir` 跳过整块挂载 → 页面 404 而非报错, 无栈可查。- **处置**: 上跳一级 `dirname(dirname(__file__))`; config.py→config/ 同型迁移时同样适用。
### 生成脚本模板写含 \x 转义的正则必须 raw 三引号
- **触发**: 非 raw 的 `'''...'''` 模板里写 `re.compile(r"[\x00-\x1f\x7f]")` 这类字面量。- **判别**: 生成文件混进**真 NUL 字节** → `SyntaxError: source code string cannot contain null bytes`(报错位置在 import 方, 真凶在被生成文件)。- **处置**: 模板用 raw 字符串; 用 `data.count(b'\x00')` 定位注入点。
