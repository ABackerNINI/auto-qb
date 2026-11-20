"""静态前端内容版本 V(计划 26-11-20-0727 P2-1/D5): 给 static/ 树一个内容指纹.

四套 index.html head 资源 URL 上的 ?v=__AQB_V__ 在响应时替换为 V: 浏览器据此在
"同内容稳定 / 任一纳入文件变化即变"之间切缓存, 避免升级后仍吃旧 JS/CSS。

口径:
- 只纳入白名单扩展名(.js/.html/.css/.png)的静态源码; 日志/.pyc/临时文件不进 ——
  否则运行期噪声文件会让 V 抖动, 缓存永远撞不中。
- 稳定: os.walk 收集后按相对路径排序(不依赖目录遍历顺序); 每项写入路径与内容的
  长度前缀 + 原字节, 消除"路径/内容拼接"的歧义碰撞。
- 取 sha256 前 16 位十六进制: 足够区分一次前端发布, 又短到不污染 URL。
"""
import hashlib
import os

_VERSION_EXTS = (".js", ".html", ".css", ".png")
_VERSION_HEX_LEN = 16


def compute_static_version(static_dir: str) -> str:
    """static_dir 的内容哈希: 同内容恒等, 任一纳入文件变化即变.

    挂载时算一次由调用方闭包持有; 本函数无进程内缓存, 便于测试用临时树反复计算.
    """
    entries = []
    for root, dirs, files in os.walk(static_dir):
        dirs.sort()
        for name in files:
            if not name.lower().endswith(_VERSION_EXTS):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, static_dir).replace(os.sep, "/")
            with open(path, "rb") as f:
                entries.append((rel, f.read()))
    entries.sort(key=lambda e: e[0])
    h = hashlib.sha256()
    for rel, content in entries:
        rb = rel.encode("utf-8")
        h.update(len(rb).to_bytes(8, "big"))
        h.update(rb)
        h.update(len(content).to_bytes(8, "big"))
        h.update(content)
    return h.hexdigest()[:_VERSION_HEX_LEN]
