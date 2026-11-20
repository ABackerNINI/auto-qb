"""静态前端挂载: UI 重定向 + StaticFiles 根挂载 + no-cache 中间件(整段平移).

必须在 create_app 全部 /api 路由注册之后调用(mount \"/\" 是兜底路由)。
"""
import os
import re

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from .static_version import compute_static_version

# UI 皮肤 cookie(shared/boot.js 写入): 打开任一 UI 即记录其目录段, 根路径 / 据此直达「上次使用的 UI」
# (修复关窗重开总回星图)。服务端只认「形状合法 + static/<名>/index.html 真实存在」的值 ——
# UI 改名/删除后旧 cookie 自动回落星图; 校验形状也挡住 `..` 等路径逃逸形状进重定向目标。
_UI_COOKIE = "autoqb_ui"
_UI_SEG_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")


def mount_static_ui(app: FastAPI) -> None:
    # 静态前端(UI 目录化: atlas=星图(旧) / prism=棱镜(新) / shared=公共逻辑层; 目录即 URL,
    # 新增 UI = static/<名字>/ 一个目录, 无需后端改动)
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    if os.path.isdir(static_dir):
        # D5: 静态树内容指纹挂载时算一次, 由下方中间件闭包持有 —— 每请求重算会让 V
        # 随运行期临时文件抖动; 令牌只在响应时替换, 绝不写回磁盘(自毁哈希稳定性)。
        version = compute_static_version(static_dir)

        def _remembered_ui(raw: str | None) -> str | None:
            """cookie 值 -> 可信 UI 目录名; 形状不合法或目录已不存在一律 None(回落默认)。"""
            if not raw or not _UI_SEG_RE.match(raw):
                return None
            if not os.path.isfile(os.path.join(static_dir, raw, "index.html")):
                return None
            return raw

        @app.get("/", include_in_schema=False)
        async def _ui_root(request: Request) -> RedirectResponse:
            """根路径进「上次使用的 UI」(cookie 由 shared/boot.js 在每套 UI 加载时写入);
            未记录 / 记录失效(UI 目录改名或删除)回落默认星图。"""
            remembered = _remembered_ui(request.cookies.get(_UI_COOKIE))
            return RedirectResponse(f"/{remembered}/" if remembered else "/atlas/", status_code=307)

        @app.get("/newui", include_in_schema=False)
        @app.get("/newui/{rest:path}", include_in_schema=False)
        async def _newui_legacy(rest: str = "") -> RedirectResponse:
            """旧 /newui/* 书签兼容: 307 到 /prism/*(观察一轮后可撤)。"""
            return RedirectResponse(f"/prism/{rest}", status_code=307)

        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

        @app.middleware("http")
        async def _static_no_cache(request, call_next):
            """静态资源禁用启发式缓存(不加 Cache-Control 时浏览器会自行缓存数小时) + HTML 版本令牌替换

            症状: 升级程序后仍加载旧 app.js/style.css, 界面“改了但没变”。
            用 no-cache(仍允许存储, 但每次必须带 ETag 重新校验): 未变更走 304, 变更为新内容。
            仅作用于非 /api 响应, 不影响接口语义。

            D4: HTML 经 StaticFiles(html=True) 直吐磁盘文件, 令牌不能写回盘, 故在响应层把
            __AQB_V__ 换成挂载时算好的 V: 只碰 text/html(不动 JS/CSS/PNG 二进制), body_iterator
            可能分块故先收齐再替换, 重建 Response 让 Starlette 按新字节回填 Content-Length。
            """
            response = await call_next(request)
            if request.url.path.startswith("/api"):
                return response
            response.headers["Cache-Control"] = "no-cache"
            # HEAD 只发头不发体: body_iterator 为空, 收齐重建会把 Content-Length 误置 0,
            # 破坏 HEAD 应回显与 GET 等效的长度语义 —— 原样返回, 仅保留 no-cache 头。
            if request.method == "HEAD":
                return response
            if "text/html" not in response.headers.get("content-type", ""):
                return response
            if response.status_code in (204, 304):
                return response
            # body_iterator 可能分块: 收齐后再替换, 避免半个令牌跨块漏替。
            chunks = []
            async for chunk in response.body_iterator:
                chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
            body = b"".join(chunks)
            # 消费过 body_iterator 就必须重建响应(否则体为空); 无令牌时逐字节原样还回。
            # 丢掉旧 content-length / transfer-encoding, 由 Response 按新长度重算。
            headers = {
                k: v
                for k, v in response.headers.items() if k.lower() not in ("content-length", "transfer-encoding")
            }
            body = body.replace(b"__AQB_V__", version.encode("ascii"))
            return Response(content=body, status_code=response.status_code, headers=headers)
