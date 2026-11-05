"""test_web_hr_fs 测试计划: HR web 端点与搜索 / 文件系统端点

## 测试计划(每个测试函数一条)
- test_api_paths_endpoint: GET /api/paths 已知目录聚合(组 save_path + 现有种子 save_path 归一去重排序; 空路径跳过; 无副作用; 鉴权)
- test_api_open_path_endpoint: POST /api/open-path 打开目标文件夹(FX-14 + R10-10 + 2026-10-11 三层口径) —— 文件(单文件种子, select=True 定位选中) > root_path > content_path > save_path; 组按单个种子处理(单成员 / content_path 或 root_path 任一全同)与不一致回退组 save_path; 未知目标 404、kind 非法 400、客户端传 path 被忽略、无副作用、鉴权
- test_api_fs_dirs_endpoint: GET /api/fs/dirs 目录浏览(R10-11) —— 首屏允许根/只列目录(排除文件与越界符号链接)/上溯到根为止/.. 穿越与白名单外 403/不存在 404/无白名单空返回/鉴权/无副作用
- test_api_fs_dirs_case_sibling_is_outside_whitelist: **仅 Linux** —— 大小写兄弟目录(/x/Media 与 /x/media)必须判为越界, 白名单归一不得做 NTFS 式折叠(折叠 => 越界放行, fail-open)
- test_api_fs_mkdir_endpoint: POST /api/fs/mkdir 新建目录(R10-11) —— 正常创建/重名目录幂等/重名文件 409/名字含分隔符或点为 400/白名单外 403/父目录不存在 404/鉴权/不投命令
- test_fs_endpoints_route_fs_calls_through_long_path_prefix: fs 三端点的文件系统调用必须过 add_long_path_prefix_for_win(Windows 长路径 >MAX_PATH 否则 isdir 给假/scandir 抛错 ⇒ 误报 404)
- test_fs_endpoints_unmapped_root_semantic_404: Mapped 模式下白名单内但未命中 fs.path_map 的路径 -> fs 三端点语义化 404「不可判定」而非裸 500(BUG 回归: UNDETERMINED 禁止布尔化, 路由五处两态消费收进 _determinable 单点)
- test_fs_path_helpers_strip_long_path_prefix_before_compare: _bare/_fs_real 比较前剥长路径前缀(否则同一条路径的两种写法被判越界, 子目录全被过滤)
- testhr_view_fields_three_state: 详情字段透出站点侧三态与依据(接入站点才有值, 未接入全空)
- testhr_view_fields_excluded: HR 排除态视图(hr_excluded=True, 触发/达标 False, 站点侧全空, 桥不被打扰)
"""

import json

import os

import re

import sys

import tempfile

import time

from pathlib import Path

from types import SimpleNamespace

from unittest import mock

import pytest

from auto_qb.infra import file_access

from auto_qb.infra.utils import encode_group_key

from webui_helpers import _UI_ALL, _ui_aggregate, _hr_status_env, ENTRY_ROW_KEYS_API, HISTORY_ROW_KEYS

from web_hr_support import (
    _AUTH_HEADER_KEY,
)


def test_api_paths_endpoint(web_env):
    """GET /api/paths: 已知目录聚合(DLG-04): 组 save_path + 现有种子 save_path, 排序去重

    组 key 首元已是规范化 save_path; 种子侧经 path_normalize 归一分隔符后去重(反斜杠写法
    与组同径不重复); 空路径跳过; 只读快照无副作用; 鉴权沿用 /api/* 依赖。
    """
    mgr, client = web_env
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    mgr.store.groups = {
        ("R:/Downloads", ("a.mkv", "b.mkv")): ["HA", "HB"],
        ("D:/ISO", ("x.iso", )): ["HC"],
    }
    mgr.store.by_hash = {
        "HA": SimpleNamespace(hash="HA", save_path="R:\\Downloads"),  # 反斜杠写法 -> 与组 key 同径去重
        "HC": SimpleNamespace(hash="HC", save_path="D:/ISO"),
        "HD": SimpleNamespace(hash="HD", save_path="E:/TV/"),
        "HE": SimpleNamespace(hash="HE", save_path=""),  # 空路径跳过
    }
    r = client.get("/api/paths", headers=auth).json()
    assert r == {"paths": ["D:/ISO", "E:/TV/", "R:/Downloads"]}, r
    # 只读无副作用: 快照未被改动
    assert set(mgr.store.groups) == {("R:/Downloads", ("a.mkv", "b.mkv")), ("D:/ISO", ("x.iso", ))}
    assert set(mgr.store.by_hash) == {"HA", "HC", "HD", "HE"}
    # 鉴权: 无密钥 401
    assert client.get("/api/paths").status_code == 401


def test_api_open_path_endpoint(web_env, tmp_path):
    """POST /api/open-path (FX-14 + R10-10 + 2026-10-11 解析口径): 服务端派生目录/文件后打开

    解析顺序 **文件(单文件种子) > root_path > content_path > save_path** 逐层覆盖:
    目录型 content_path 打开该目录 / **文件型 content_path(单文件种子)取文件本身并带 select=True
    (R10-10 "在文件夹中选中相关文件")** / **content_path 不可用而 root_path 是已存在目录时取
    root_path** / content_path 未落盘(下载中, qB 报逻辑完成名而磁盘尚无该路径)回退 save_path,
    不因"未完成"而 404 / content 与 save_path 都不存在 404。
    组(kind=group)按**单个种子**处理的条件: 组内只含一个种子, 或成员 content_path / root_path
    **任一**归一后全同(辅种组常态) —— 走同一套解析; 内容确不一致则退回组 key 首元(save_path)。
    另覆盖: 未知组/未知 hash/不存在目录 404 / kind 非法 400 /
    **客户端额外传入的 path 被忽略**(安全红线: 否则等于把"任意文件执行"暴露给 WEB 端点) / 鉴权 401。
    """
    mgr, client = web_env
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    d_content = tmp_path / "content"
    d_content.mkdir()
    f_file = d_content / "movie.mkv"
    f_file.write_bytes(b"x")
    d_left = tmp_path / "left"
    d_left.mkdir()
    d_right = tmp_path / "right"
    d_right.mkdir()
    d_seed = tmp_path / "seeds"
    d_seed.mkdir()
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径(仅统一分隔符)
    rec = lambda h, save, content, root="": SimpleNamespace(  # noqa: E731  root_path 缺省 = 空串(单文件/老版本 qB)
        hash=h, save_path=str(save), content_path=str(content), root_path=str(root)
    )
    mgr.store.by_hash = {
        # 多文件种子: content_path / root_path 都是内容目录(qB 口径: root_path = 文件树首个公共子目录)
        "HA": rec("HA", d_seed, d_content, d_content),
        # 单文件种子: content_path 即该文件, root_path 为空(文件直接落在 save_path)
        "HB": rec("HB", d_seed, f_file),
        # content_path 缺失但 root_path 是内容目录 -> 新 root_path 层级接住
        "HC": rec("HC", d_seed, "", d_content),
        # 下载中单文件种子: content_path 是 qB 报的逻辑完成名, 磁盘上尚未落盘(或带 .!qB 后缀) —— 实际故障场景
        "HD": rec("HD", d_seed, d_seed / "incomplete.mkv"),
        # 下载中多文件种子: content_path 与 root_path 都还没落盘 -> 回退 save_path
        "HF": rec("HF", d_seed, d_seed / "NewMovie", d_seed / "NewMovie"),
        # content 与 save_path 都不存在: 回退后终检兜底 404
        "HE": rec("HE", tmp_path / "gone", tmp_path / "gone" / "x.mkv", tmp_path / "gone"),
        # ---- 组用例成员 ----
        "HB2": rec("HB2", d_seed, f_file),  # 与 HB 同一份单文件内容(辅种): content_path 全同
        "HI": rec("HI", d_seed, d_left, d_left),  # key_c: 与 HJ 内容确不一致
        "HJ": rec("HJ", d_seed, d_right, d_right),
        "HK": rec("HK", d_seed, d_content / "k1.mkv", d_content),  # key_d: content_path 各异但 root_path 全同
        "HL": rec("HL", d_seed, d_content / "l1.mkv", d_content),
    }
    k_a = (norm(d_seed), ("a.mkv", ))
    k_b = (norm(d_seed), ("b.mkv", ))
    k_c = (norm(d_seed), ("c.mkv", ))
    k_d = (norm(d_seed), ("d.mkv", ))
    mgr.store.groups = {
        k_a: ["HA"],  # 只含一个种子 -> 按单个种子
        k_b: ["HB", "HB2"],  # 多成员但 content_path 全同 -> 按单个种子
        k_c: ["HI", "HJ"],  # 内容确不一致 -> 退回组 key 首元(save_path)
        k_d: ["HK", "HL"],  # content_path 各异但 root_path 全同 -> 任一相同即按单个种子
    }
    # web_env 的 store 是轻量 namespace(get 恒 None), 这里按真实 Store.get 语义接上 by_hash
    mgr.store.get = lambda h: mgr.store.by_hash.get(h)
    post = lambda body: client.post("/api/open-path", json=body, headers=auth)  # noqa: E731
    # patch 地址 = auto_qb.web.common.open_path(web.py 拆 web/ 包后模块地址稳定化;
    # 原地址 auto_qb.web.open_path 随模块拆分失效 —— 管线性改动, plan 26-09-22-1857 W1)
    with mock.patch("auto_qb.webui.server.common.open_path") as spy:
        # 1. 目录型 content_path -> 打开该目录(进入语义, 不选中)
        r = post({"kind": "torrent", "hash": "HA"})
        assert r.status_code == 200 and r.json() == {"opened": norm(d_content), "select": False}, r.text
        spy.assert_called_once_with(norm(d_content), select=False)
        # 2. 文件型 content_path(单文件种子) -> 打开该文件并**定位选中**(R10-10)
        spy.reset_mock()
        assert post({"kind": "torrent", "hash": "HB"}).json() == {"opened": norm(f_file), "select": True}
        spy.assert_called_once_with(norm(f_file), select=True)
        # 2b. content_path 缺失但 root_path 是内容目录 -> root_path 层级接住
        spy.reset_mock()
        assert post({"kind": "torrent", "hash": "HC"}).json() == {"opened": norm(d_content), "select": False}
        spy.assert_called_once_with(norm(d_content), select=False)
        # 3. content_path 未落盘(下载中既非目录也非文件) -> 回退 save_path, 不 404
        spy.reset_mock()
        assert post({"kind": "torrent", "hash": "HD"}).json() == {"opened": norm(d_seed), "select": False}
        spy.assert_called_once_with(norm(d_seed), select=False)
        # 3b. 多文件且 content_path/root_path 都未落盘 -> 同样回退 save_path
        spy.reset_mock()
        assert post({"kind": "torrent", "hash": "HF"}).json() == {"opened": norm(d_seed), "select": False}
        spy.assert_called_once_with(norm(d_seed), select=False)
        # 4. 组只含一个种子 -> 按单个种子解析(内容目录)
        spy.reset_mock()
        assert post({
            "kind": "group",
            "key": encode_group_key(k_a)
        }).json() == {
            "opened": norm(d_content),
            "select": False
        }
        spy.assert_called_once_with(norm(d_content), select=False)
        # 4b. 组多成员但 content_path 全同(辅种组) -> 按单个种子解析(单文件 -> 定位选中)
        spy.reset_mock()
        assert post({"kind": "group", "key": encode_group_key(k_b)}).json() == {"opened": norm(f_file), "select": True}
        spy.assert_called_once_with(norm(f_file), select=True)
        # 4c. 组 content_path 各异但 root_path 全同(任一相同即可) -> 仍按单个种子解析
        spy.reset_mock()
        assert post({
            "kind": "group",
            "key": encode_group_key(k_d)
        }).json() == {
            "opened": norm(d_content),
            "select": False
        }
        spy.assert_called_once_with(norm(d_content), select=False)
        # 4d. 组内容确不一致 -> 退回组 key 首元(规范化 save_path)
        spy.reset_mock()
        assert post({"kind": "group", "key": encode_group_key(k_c)}).json() == {"opened": norm(d_seed), "select": False}
        spy.assert_called_once_with(norm(d_seed), select=False)
        # 5. 安全: 客户端多传的 path 被忽略 —— 打开的是服务端派生的目录, 不是它
        spy.reset_mock()
        post({"kind": "group", "key": encode_group_key(k_a), "path": "C:/Windows/System32"})
        spy.assert_called_once_with(norm(d_content), select=False)
        # 6. 未知组 / 未知 hash / 不存在目录 -> 404; kind 非法 -> 400; 均不调用系统打开
        spy.reset_mock()
        assert post({"kind": "group", "key": encode_group_key(("D:/nope", ("z", )))}).status_code == 404
        assert post({"kind": "torrent", "hash": "NOPE"}).status_code == 404
        assert post({"kind": "torrent", "hash": "HE"}).status_code == 404  # content 未落盘 + save_path 也不存在 -> 终检兜底 404
        assert post(
            {
                "kind": "group",
                "key": encode_group_key((norm(tmp_path / "missing"), ("a.mkv", )))
            }
        ).status_code == 404
        assert post({"kind": "wat"}).status_code == 400
        spy.assert_not_called()
    # 只读无副作用: 不入命令队列
    assert mgr.web.commands.empty()
    # 鉴权: 无密钥 401
    assert client.post("/api/open-path", json={"kind": "wat"}).status_code == 401


def test_api_fs_dirs_endpoint(web_env, tmp_path):
    """GET /api/fs/dirs (R10-11): 服务端目录浏览 —— 允许根白名单/只列目录/穿越防护/鉴权

    这是本项目唯一新增的**文件系统读**能力, 安全边界逐条固化: 1.首屏(path 空)= 允许根列表;
    2.只返回目录条目(同名文件不出现); 3.上溯到允许根为止(根之上 parent 为空);
    4.`..` 穿越与白名单外路径一律 403; 5.不存在/不是目录 404; 6.无白名单时空返回(不报错);
    7.指向根外的符号链接不出现在列表里(逃逸防护); 8.无密钥 401; 9.只读不入命令队列。
    """
    mgr, client = web_env
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    root = tmp_path / "root"
    (root / "sub" / "deep").mkdir(parents=True)
    (root / "b.txt").write_bytes(b"x")
    outside = tmp_path / "outside"
    outside.mkdir()
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    get = lambda p=None: client.get("/api/fs/dirs", headers=auth, params={} if p is None else {"path": p})  # noqa: E731

    # 1. 首屏 = 允许根列表(前端入口)
    body = get().json()
    assert body["path"] == "" and body["roots"] == [norm(root)]
    assert body["dirs"] == [{"name": norm(root), "path": norm(root)}]
    # 2. 列子目录: 只出现目录(同名文件被排除); 已在允许根 -> 不能再上溯
    body = get(norm(root)).json()
    assert [d["name"] for d in body["dirs"]] == ["sub"]
    assert body["path"] == norm(root) and body["parent"] == ""
    # 3. 进入子目录后可上溯回根
    body = get(norm(root / "sub")).json()
    assert [d["name"] for d in body["dirs"]] == ["deep"]
    assert body["parent"] == norm(root)
    # 4. 越界 / .. 穿越 / 不存在 -> 403 / 403 / 404
    assert get(norm(outside)).status_code == 403
    assert get(norm(root / ".." / "outside")).status_code == 403
    assert get(norm(root / "nope")).status_code == 404
    assert get(norm(root / "b.txt")).status_code == 404  # 目标存在但是文件 -> 不是目录
    # 5. 符号链接逃逸: 指向根外的子目录不进列表
    #    跳过条件有两种: (a) 环境不允许建链(Windows 未开开发者模式 -> OSError);
    #    (b) **建了但落成真实目录** —— 部分沙箱/文件系统重定向层会让 os.symlink "成功"却
    #    islink=False(实测 mode=0o40777), 此时根本不存在"逃逸链接", 断言无意义。
    #    这两种都是环境能力缺失, 不是代码缺陷 —— 真机上能建真链接时照常断言。
    link = root / "escape"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError, AttributeError):
        pass
    else:
        if os.path.islink(link):
            assert "escape" not in [d["name"] for d in get(norm(root)).json()["dirs"]]
    # 6. 无白名单(还没有任何已知保存路径) -> 空返回而非报错
    mgr.store.by_hash = {}
    assert get().json() == {"path": "", "parent": "", "roots": [], "dirs": []}
    # 7. 鉴权 + 只读无副作用
    assert client.get("/api/fs/dirs").status_code == 401
    assert mgr.web.commands.empty()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="只有大小写敏感的 FS(ext4)上两个名字才是两个目录; NTFS 上是同一个, 断言无意义")  # owner: abacker
def test_api_fs_dirs_case_sibling_is_outside_whitelist(web_env, tmp_path):
    """**大小写兄弟目录必须判为越界** —— `web._fs_real` 不得做 NTFS 式大小写折叠

    生产代码跑在**本机真实磁盘**上: Linux 下 `/x/Media` 与 `/x/media` 是两个**不同**目录。若把归一
    换成 `ntpath.normcase`(折叠大小写 + `/`->`\\`), 后者会被判成"在白名单内" ⇒ **越界放行**
    (fail-open, 安全方向反了)。`os.path.normcase` 在 Linux 是恒等函数, 恰恰是所需语义 —— 钉死它。
    WARN: 本条只能在 Linux 上真跑(NTFS 上根本建不出"仅大小写不同"的两个目录), 由 CI 验。
    """
    mgr, client = web_env
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    root = tmp_path / "Media"
    root.mkdir()
    sibling = tmp_path / "media"  # 仅大小写不同
    sibling.mkdir()
    # 前置校验: 这两者**确实是两个目录**(否则下面的 403 断言说明不了任何事)
    (root / "inside.txt").write_bytes(b"x")
    assert not (sibling / "inside.txt").exists(), "大小写兄弟必须是另一个目录, 否则本条断言无意义"
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    r = client.get("/api/fs/dirs", headers=auth, params={"path": norm(sibling)})
    assert r.status_code == 403, f"大小写兄弟目录不得被折叠进白名单(折叠 => 越界放行): {r.status_code}"


def test_api_fs_mkdir_endpoint(web_env, tmp_path):
    """POST /api/fs/mkdir (R10-11): 新建目录的边界 —— 单层名字/白名单/幂等/同名文件 409

    覆盖: 正常新建(目录真的出现在磁盘上 + 返回绝对路径) / 重名目录幂等(200 + existed=True) /
    同名**文件** 409 / 名字含分隔符或为 . .. -> 400 / 白名单外父目录 403 / 父目录不存在 404 /
    无密钥 401 / 不入命令队列(只建目录, 不碰任务队列与 state)。
    """
    mgr, client = web_env
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    post = lambda body: client.post("/api/fs/mkdir", json=body, headers=auth)  # noqa: E731

    # 1. 正常新建
    r = post({"path": norm(root), "name": "新文件夹"})
    assert r.status_code == 200 and r.json() == {"created": norm(root / "新文件夹"), "existed": False}, r.text
    assert (root / "新文件夹").is_dir()
    # 2. 重名目录幂等(不报错)
    assert post({"path": norm(root), "name": "新文件夹"}).json()["existed"] is True
    # 3. 同名文件 -> 409
    (root / "b.txt").write_bytes(b"x")
    assert post({"path": norm(root), "name": "b.txt"}).status_code == 409
    # 4. 名字含路径成分 / . / .. -> 400(只接受单层名字, 不做路径拼接)
    for bad in ("", "  ", "a/b", "a\\b", ".", ".."):
        assert post({"path": norm(root), "name": bad}).status_code == 400, bad
    # 5. 白名单外 / 父目录不存在 -> 403 / 404
    assert post({"path": norm(outside), "name": "x"}).status_code == 403
    assert post({"path": "", "name": "x"}).status_code == 403
    assert post({"path": norm(root / "missing"), "name": "x"}).status_code == 404
    # 6. 鉴权 + 不入命令队列(不绕过单一写线程: 只建目录)
    assert client.post("/api/fs/mkdir", json={"path": norm(root), "name": "x"}).status_code == 401
    assert mgr.web.commands.empty()


def test_fs_endpoints_route_fs_calls_through_long_path_prefix(web_env, tmp_path, monkeypatch):
    """fs 三端点的**文件系统调用**必须过 `add_long_path_prefix_for_win`(本次报障的核心)

    Windows 上 >MAX_PATH 的裸路径 `isdir` 给假 / `scandir` 抛 WinError 3 ⇒ 不加前缀时端点会
    误报 404, 而前端只看到"目录不存在或不可访问"。这里把前缀 helper 换成 spy, 逐端点钉住
    "确实调了它"。

    WARN: 测的是**路由**而不是平台效果: 真 Windows 行为在 Linux CI 上无法复现(平台固定约定见
    testing/file-conventions.md), 故宿主上前缀是恒等(前缀对 POSIX 路径无意义); 前缀本身的
    正确性与打开层分支另由 `test_exists_dir_file_apply_long_path_prefix` /
    `test_open_path_windows_*` 覆盖。26-09-27: 前缀单点收编进文件访问层(infra/file_access,
    plan 26-09-27-1407) —— spy 地址随单点迁到 `auto_qb.infra.utils.add_long_path_prefix_for_win`,
    断言意图不变(全部本地 syscall 过单点)。
    """
    from auto_qb.infra.utils import add_long_path_prefix_for_win as real_prefix

    mgr, client = web_env
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    root = tmp_path / "root"
    (root / "sub").mkdir(parents=True)
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径
    mgr.store.groups = {(norm(root), ("a.mkv", )): ["HA"]}
    mgr.store.by_hash = {
        "HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root), root_path=str(root))
    }
    mgr.store.get = lambda h: mgr.store.by_hash.get(h)

    calls = []

    def spy(p):
        calls.append(p)
        return real_prefix(p)

    monkeypatch.setattr("auto_qb.infra.utils.add_long_path_prefix_for_win", spy)

    # 1. 目录浏览
    assert client.get("/api/fs/dirs", headers=auth, params={"path": norm(root)}).status_code == 200
    assert norm(root) in calls, f"fs/dirs 的文件系统调用未过前缀 helper: {calls}"
    # 2. 新建目录
    calls.clear()
    assert client.post("/api/fs/mkdir", json={"path": norm(root), "name": "new"}, headers=auth).status_code == 200
    assert norm(root) in calls, f"fs/mkdir 的文件系统调用未过前缀 helper: {calls}"
    # 3. 打开目标文件夹(open_path 必须 mock —— 真调会弹资源管理器, 守阵判越界)
    calls.clear()
    with mock.patch("auto_qb.webui.server.common.open_path"):
        assert client.post("/api/open-path", json={"kind": "torrent", "hash": "HA"}, headers=auth).status_code == 200
    assert norm(root) in calls, f"open-path 的文件系统调用未过前缀 helper: {calls}"


def test_fs_endpoints_unmapped_root_semantic_404(web_env, tmp_path):
    """Mapped 模式下白名单内但未命中映射 -> 三端点语义化 404「不可判定」, 不是裸 500(BUG 回归)

    回归: fs 路由曾有五处两态布尔消费(not fa.isdir / if fa.exists / not fa.isfile),
    Mapped miss 时包装层返回 UNDETERMINED, 其 __bool__ 抛 TypeError ⇒ FastAPI 裸 500。
    收进 _determinable 单点分流后: 未命中 fs.path_map 的允许根 浏览/新建/打开 都返回
    带原因的 404(「不可判定」不冒充「不存在」, 报告 §05)。
    """
    from auto_qb.config import PathMapEntry

    mgr, client = web_env
    saved = file_access.get_file_access()
    file_access._instance = file_access.MappedFileAccess(
        (PathMapEntry(src="D:/Downloads", dst=str(tmp_path / "mnt")), )
    )
    try:
        auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
        unmapped = tmp_path / "unmapped"
        unmapped.mkdir()  # 宿主真实存在, 但前缀不在映射表里 -> 逻辑空间不可判定
        norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径
        mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(unmapped), content_path="", root_path="")}
        mgr.store.groups = {(norm(unmapped), ("a.mkv", )): ["HA"]}
        mgr.store.get = lambda h: mgr.store.by_hash.get(h)
        # 1. 目录浏览: 白名单内(是已知保存路径)但未命中映射 -> 404 不可判定
        r = client.get("/api/fs/dirs", headers=auth, params={"path": norm(unmapped)})
        assert r.status_code == 404 and "不可判定" in r.json()["detail"], r.text
        # 2. 新建文件夹: 父目录未命中映射 -> 404 不可判定
        r = client.post("/api/fs/mkdir", json={"path": norm(unmapped), "name": "x"}, headers=auth)
        assert r.status_code == 404 and "不可判定" in r.json()["detail"], r.text
        # 3. 打开路径(torrent): content_path 缺失回退 save_path(未命中) -> 404 不可判定
        r = client.post("/api/open-path", json={"kind": "torrent", "hash": "HA"}, headers=auth)
        assert r.status_code == 404 and "不可判定" in r.json()["detail"], r.text
        # 4. 打开路径(组): 组键首元未命中映射 -> 404 不可判定
        key = encode_group_key((norm(unmapped), ("a.mkv", )))
        r = client.post("/api/open-path", json={"kind": "group", "key": key}, headers=auth)
        assert r.status_code == 404 and "不可判定" in r.json()["detail"], r.text
    finally:
        file_access._instance = saved


def test_fs_path_helpers_strip_long_path_prefix_before_compare():
    """`_bare` / `_fs_real`: **比较前必须剥掉 `\\\\?\\` 前缀** —— 否则同一条路径的两种写法被判"越界"

    实测后果(Windows 真机): `os.scandir` 家族给出的 entry 路径**带前缀**, 而允许根
    不带 ⇒ `_within_roots` 恒 False ⇒ **子目录被全部过滤掉**(目录树恒空)。
    `os.path.realpath` 是否保留前缀**与路径长度有关**(实测短路径保留、长路径剥掉), 不能依赖它,
    故必须在比较前显式剥掉。

    本条是纯路径归一, **与宿主平台无关** ⇒ Linux CI 上也守得住(这正是把三个 helper 提到模块级
    而不是留在 `build_router` 闭包里的原因)。
    26-09-27: 前缀剥离/加前缀单点迁入文件访问层(infra/file_access, plan 26-09-27-1407),
    `_fs` 帮手随之删除(包装层内部自理) —— 剥前缀契约改在 file_access 单点断言, `_bare`
    保留薄委托供路由侧钉住。
    """
    from auto_qb.webui.server.routes import fs as fs_mod

    bare = os.path.abspath("x")
    assert fs_mod._bare("\\\\?\\" + bare) == bare
    assert fs_mod._bare(bare) == bare, "无前缀原样返回"
    assert fs_mod._bare("\\\\?\\UNC\\server\\share") == "\\\\server\\share", "UNC 形态还原"
    # 带前缀与不带前缀必须归一到同一个可比较形式(_fs_real 委托包装层, 内部先剥再规范化)
    assert fs_mod._fs_real("\\\\?\\" + bare) == fs_mod._fs_real(bare)
    # 前缀单点幂等: 已是带前缀形态再进包装层不得叠加 —— path_normalize 会把 `\\?\\` 折坏成 `/?/`
    fa = file_access.LocalFileAccess()
    assert fa._pref(fa._pref(bare)) == fa._pref(bare)
    assert file_access._norm_logical(file_access._norm_logical("\\\\?\\" + bare)) == file_access._norm_logical(bare)
