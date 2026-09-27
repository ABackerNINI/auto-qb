"""test_file_access 测试计划: infra/file_access 文件访问层(plan 26-09-27-1407)

## 测试计划(每个测试函数一条)
- test_local_passthrough_equivalence: Local 直通等价(存在性/大小/磁盘/列举/新建, 真实临时目录)
- test_local_long_path_prefix_single_point: Local 全部 syscall 过长路径前缀单点(收编散点后仍在)
- test_local_never_undetermined: Local 实现永不产生 UNDETERMINED(三态只属于映射 miss)
- test_local_open_path_delegates: Local open_path 委托 utils.open_path
- test_undetermined_not_boolean: UNDETERMINED 不可作布尔值(隐式真值判断直接抛错 —— 防误判缺失)
- test_mapped_hit_and_miss_tristate: 映射命中取真值 / miss 三态(exists/isdir/isfile -> UNDETERMINED;
  getsize/disk_usage -> FileAccessError)
- test_mapped_matching_rules: casefold + 分隔符折叠 + `\\\\?\\` 前缀剥离 + 尾斜杠归一 + 精确根
- test_mapped_prefix_boundary: `/` 边界强制(D:/Downloads 不得命中 D:/Downloads2)
- test_mapped_scandir_logical_space: scandir entry 译回逻辑空间(白名单消费方零改动的前提)
- test_mapped_mkdir_real_and_miss: mkdir 挂载点可写即真实执行; miss 报 FileAccessError(不可判定)
- test_mapped_realpath_lexical: Mapped realpath_lexical 纯词法(normcase+normpath, 不解析符号链接)
- test_mapped_open_path_not_supported: 容器 open_path 恒 NotSupported(B/C 类根因, 优雅降级)
- test_init_file_access_by_config: 空表 -> Local; 非空 -> Mapped(单例构建, R 级热重载不切换)
- test_selfcheck_mount_missing_and_readonly: 挂载点不存在 WARNING; 只读探测 INFO; 命中率 0% WARNING; Local 空转
- test_check_filelist_undetermined: 跳检前置映射 miss -> 「路径不可判定」(不误报文件缺失)
- test_grouping_missing_scan_undetermined_skips: 缺文件扫描映射 miss -> 跳过该组(不暂停不打标)
- test_grouping_missing_scan_local_stops: Local 缺文件 -> 整组暂停 + MISSING 标签(既有行为不劣化)
- test_expr_exists_and_disk_undetermined: exists()/disk_* 表达式映射 miss -> ExprError(显式报错优于静默)
- test_freespace_condition_undetermined: freespace 条件映射 miss -> ExprError; 真实 OSError 仍静默 False
- test_fs_config_validation_errors: fs.path_map 校验聚合(空值/相对路径/to 无根斜杠/重复/前缀歧义)
"""
import os
import shutil
from types import SimpleNamespace

import pytest

from auto_qb.config import ConfigError, PathMapEntry, load_config
from auto_qb.infra import file_access
from auto_qb.infra.file_access import (
    UNDETERMINED,
    DirEntry,
    FileAccessError,
    LocalFileAccess,
    MappedFileAccess,
    NotSupported,
    get_file_access,
    init_file_access,
    path_map_selfcheck,
)
from auto_qb.core.mixins.grouping import GroupingMixin
from auto_qb.core.mixins.checking import CheckingMixin
from auto_qb.rules.conditions import FreespaceCondition
from auto_qb.rules.expr.errors import ExprError

import helpers


@pytest.fixture
def fa():
    """单例隔离: 每个用例保存/还原全局实现(避免 Mapped 泄漏到其它测试)"""
    saved = get_file_access()
    yield
    file_access._instance = saved


def _mapped(tmp_path, src="D:/Downloads"):
    """构造映射: 逻辑空间 <src> -> 容器空间 tmp_path(tmp_path 扮演挂载点, 真实可读写)"""
    return MappedFileAccess((PathMapEntry(src=src, dst=str(tmp_path).replace(os.sep, "/")), ))


# ---------------------------------------------------------------- Local


def test_local_passthrough_equivalence(tmp_path):
    """Local 直通与裸 syscall 等价: 存在性/大小/磁盘/列举/新建, 结果与行为收编前一致"""
    fa = LocalFileAccess()
    d = tmp_path / "dir"
    d.mkdir()
    f = d / "a.bin"
    f.write_bytes(b"x" * 123)
    assert fa.exists(str(d)) and fa.exists(str(f))
    assert fa.isdir(str(d)) and not fa.isdir(str(f))
    assert fa.isfile(str(f)) and not fa.isfile(str(d))
    assert not fa.exists(str(tmp_path / "nope"))
    assert fa.getsize(str(f)) == 123
    total, used, free = fa.disk_usage(str(tmp_path))
    assert total >= used >= 0 and free >= 0
    entries = fa.scandir(str(d))
    assert [e.name for e in entries] == ["a.bin"] and not entries[0].is_dir
    assert entries[0].path.endswith("/a.bin")
    fa.mkdir(str(d / "sub"))
    assert (d / "sub").is_dir()


def test_local_long_path_prefix_single_point(tmp_path, monkeypatch):
    """收编后 Local 的本地 syscall 仍全部过长路径前缀单点(spy 包住 utils 单点)"""
    calls = []
    real = file_access.utils.add_long_path_prefix_for_win

    def spy(p):
        calls.append(p)
        return real(p)

    monkeypatch.setattr(file_access.utils, "add_long_path_prefix_for_win", spy)
    fa = LocalFileAccess()
    d = tmp_path / "d"
    d.mkdir()
    fa.exists(str(d))
    fa.isdir(str(d))
    fa.isfile(str(d))
    fa.getsize(str(d))
    fa.disk_usage(str(d))
    fa.scandir(str(d))
    fa.mkdir(str(d / "s"))
    assert len(calls) >= 7, f"存在未过前缀单点的 syscall: {len(calls)} 次"
    assert os.path.normcase(fa.realpath_lexical(str(d))) == os.path.normcase(str(d))


def test_local_never_undetermined(tmp_path):
    """Local 永不产生 UNDETERMINED(三态只属于映射 miss; 行为等价收编的验收线)"""
    fa = LocalFileAccess()
    assert fa.exists(str(tmp_path)) is True
    assert fa.exists(str(tmp_path / "nope")) is False
    assert fa.isdir(str(tmp_path)) is True
    assert fa.isfile(str(tmp_path)) is False


def test_local_open_path_delegates(tmp_path, monkeypatch):
    """Local open_path 委托 utils.open_path(宿主直跑行为不变)"""
    seen = []
    monkeypatch.setattr(file_access.utils, "open_path", lambda p, select=False: seen.append((p, select)))
    LocalFileAccess().open_path(str(tmp_path), select=True)
    assert seen == [(str(tmp_path), True)]


# ---------------------------------------------------------------- 哨兵


def test_undetermined_not_boolean():
    """UNDETERMINED 隐式真值判断直接抛错 —— 防止 `if not exists()` 把不可判定当缺失(报告 §05)"""
    with pytest.raises(TypeError):
        bool(UNDETERMINED)
    with pytest.raises(TypeError):
        not UNDETERMINED
    assert "UNDETERMINED" in repr(UNDETERMINED)


# ---------------------------------------------------------------- Mapped: 三态


def test_mapped_hit_and_miss_tristate(tmp_path):
    """命中取真值(容器空间实况); miss: 存在性 -> UNDETERMINED, 取值 -> FileAccessError"""
    fa = _mapped(tmp_path)
    hit = tmp_path / "sub"
    hit.mkdir()
    (hit / "a.bin").write_bytes(b"x" * 7)
    # 命中: 容器空间真值
    assert fa.exists("D:/Downloads/sub/a.bin") is True
    assert fa.isdir("D:/Downloads/sub") is True
    assert fa.isfile("D:/Downloads/sub/a.bin") is True
    assert fa.getsize("D:/Downloads/sub/a.bin") == 7
    assert fa.exists("D:/Downloads/sub/ghost.bin") is False  # 命中区域内的真缺失仍是真缺失
    assert fa.isdir("D:/Downloads/sub/ghost.bin") is False
    # miss: 一律不可判定, 绝不判「不存在」
    assert fa.exists("E:/Elsewhere/a.bin") is UNDETERMINED
    assert fa.isdir("E:/Elsewhere") is UNDETERMINED
    assert fa.isfile("E:/Elsewhere/a.bin") is UNDETERMINED
    with pytest.raises(FileAccessError):
        fa.getsize("E:/Elsewhere/a.bin")
    with pytest.raises(FileAccessError):
        fa.disk_usage("E:/Elsewhere")
    # 取值错误的文案必须说清「不可判定」, 不能让用户以为是文件坏了
    with pytest.raises(FileAccessError, match="不可判定"):
        fa.getsize("E:/Elsewhere/a.bin")


def test_mapped_matching_rules(tmp_path):
    """匹配规则: casefold + 分隔符折叠 + `\\\\?\\` 前缀剥离 + 尾斜杠归一 + 精确根"""
    fa = _mapped(tmp_path, src="D:/Downloads")
    (tmp_path / "x.bin").write_bytes(b"x")
    # casefold: qB 报回的大小写与配置写法不一致也要命中
    assert fa.exists("d:/downloads/x.bin") is True
    assert fa.exists("D:\\DOWNLOADS\\x.bin") is True
    # \\?\ 前缀: 匹配前剥掉(容器是 Linux 本不会出现, 防御性)
    assert fa.exists("\\\\?\\D:/Downloads/x.bin") is True
    # 尾斜杠: from 带不带尾斜杠同判(映射表本身带尾斜杠的写法)
    fa2 = MappedFileAccess((PathMapEntry(src="D:/Downloads/", dst=str(tmp_path).replace(os.sep, "/") + "/"), ))
    assert fa2.exists("D:/Downloads/x.bin") is True
    # 精确根: 根本身也映射(目录浏览首屏允许根 = save_path 本身)
    assert fa.map_to_container("D:/Downloads") == str(tmp_path).replace(os.sep, "/")


def test_mapped_prefix_boundary(tmp_path):
    """`/` 边界强制: D:/Downloads 不得命中 D:/Downloads2(plan 预演钉板的实现细节)"""
    fa = _mapped(tmp_path, src="D:/Downloads")
    assert fa.map_to_container("D:/Downloads2/a.bin") is None
    assert fa.exists("D:/Downloads2/a.bin") is UNDETERMINED


def test_mapped_scandir_logical_space(tmp_path):
    """scandir entry 译回逻辑空间 —— fs.py 白名单拿 entry.path 与逻辑空间 roots 比较能命中(报告 §04 坑)"""
    fa = _mapped(tmp_path)
    (tmp_path / "Season 1").mkdir()
    (tmp_path / "file.bin").write_bytes(b"x")
    entries = fa.scandir("D:/Downloads")
    by_name = {e.name: e for e in entries}
    assert set(by_name) == {"Season 1", "file.bin"}
    assert by_name["Season 1"].is_dir is True
    assert by_name["file.bin"].is_dir is False
    assert by_name["Season 1"].path == "D:/Downloads/Season 1"  # 逻辑空间, 非容器路径
    assert not by_name["Season 1"].path.startswith(str(tmp_path))


def test_mapped_mkdir_real_and_miss(tmp_path):
    """mkdir: 挂载点可写即真实执行(2026-09-27 拍板放宽); miss 报不可判定"""
    fa = _mapped(tmp_path)
    fa.mkdir("D:/Downloads/newdir")
    assert (tmp_path / "newdir").is_dir()  # 真目录, qB 同挂 :rw 即能看到
    with pytest.raises(FileAccessError, match="不可判定"):
        fa.mkdir("E:/Elsewhere/newdir")


def test_mapped_realpath_lexical(tmp_path):
    """Mapped realpath_lexical 纯词法: normcase + normpath, 不做符号链接解析
    (逻辑路径在容器里不真实存在, realpath 只会拼坏; 逃逸防护退化为词法比较)"""
    fa = _mapped(tmp_path)
    out = fa.realpath_lexical("d:/Downloads/./a/../b")
    assert out == os.path.normcase("d:/Downloads/b")
    assert "realpath" not in out


def test_mapped_open_path_not_supported(tmp_path):
    """容器 open_path 恒 NotSupported —— 与挂载无关(B/C 类根因), 端点据此 501 语义化降级"""
    with pytest.raises(NotSupported):
        _mapped(tmp_path).open_path("D:/Downloads")
    with pytest.raises(NotSupported):
        _mapped(tmp_path).open_path("D:/Downloads/a.bin", select=True)


# ---------------------------------------------------------------- 单例与自检


def test_init_file_access_by_config(fa):
    """空表 -> Local(完全现状, 保守默认); 非空 -> Mapped; 单例经 get_file_access 消费"""
    init_file_access(SimpleNamespace(fs=SimpleNamespace(path_map=())))
    assert isinstance(get_file_access(), LocalFileAccess)
    init_file_access(SimpleNamespace(fs=SimpleNamespace(path_map=(PathMapEntry(src="D:/D", dst="/m"), ))))
    assert isinstance(get_file_access(), MappedFileAccess)
    # config 缺 fs 段(旧 Config 实例)也不炸
    init_file_access(SimpleNamespace())
    assert isinstance(get_file_access(), LocalFileAccess)


def test_selfcheck_mount_missing_and_readonly(tmp_path, fa, caplog):
    """自检: 挂载点不存在 WARNING; 命中率 0% WARNING; 只读探测 INFO; Local 空转"""
    import logging

    # Local: 直接返回, 不发任何日志
    init_file_access(SimpleNamespace(fs=SimpleNamespace(path_map=())))
    with caplog.at_level(logging.DEBUG, logger="auto_qb.infra.file_access"):
        path_map_selfcheck(["D:/Downloads"])
    assert caplog.text == ""

    # Mapped: 挂载点不存在 -> WARNING
    missing = MappedFileAccess((PathMapEntry(src="D:/Downloads", dst="/mnt/definitely-not-here"), ))
    file_access._instance = missing
    with caplog.at_level(logging.WARNING, logger="auto_qb.infra.file_access"):
        path_map_selfcheck(["D:/Downloads"])
    assert "挂载点不存在" in caplog.text

    # 命中率 0%: save_path 全部 miss -> WARNING(映射表可能写错)
    good = _mapped(tmp_path)
    file_access._instance = good
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="auto_qb.infra.file_access"):
        path_map_selfcheck(["E:/Elsewhere", "F:/Other"])
    assert "无一命中" in caplog.text
    # 有命中(或无种子) -> 不报
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="auto_qb.infra.file_access"):
        path_map_selfcheck(["D:/Downloads"])
    assert "无一命中" not in caplog.text
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="auto_qb.infra.file_access"):
        path_map_selfcheck([])
    assert "无一命中" not in caplog.text

    # 只读探测: 建探针目录抛 EACCES -> INFO「只读」(预告 mkdir 不可用, 不阻塞)
    def ro_mkdir(p):
        raise OSError(13, "Permission denied")

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="auto_qb.infra.file_access"):
        monkey_ro = ro_mkdir
        real_mkdir = os.mkdir
        os.mkdir = ro_mkdir
        try:
            path_map_selfcheck(["D:/Downloads"])
        finally:
            os.mkdir = real_mkdir
    assert "挂载点只读" in caplog.text


# ---------------------------------------------------------------- 消费方三态语义


def _fake_torrent(save_path):
    return SimpleNamespace(
        log_repr="HA[T]",
        hash="HA",
        tracker_name="T",
        save_path=save_path,
        state_enum=SimpleNamespace(is_complete=True, is_errored=False, is_checking=False),
    )


def test_check_filelist_undetermined(fa):
    """跳检前置映射 miss -> 「路径不可判定」错误串(不误报「文件缺失」, 跳检保守停住)"""
    api = SimpleNamespace(torrents_files=lambda h: [SimpleNamespace(name="a.mkv", size=1)])
    init_file_access(SimpleNamespace(fs=SimpleNamespace(path_map=(PathMapEntry(src="D:/Downloads", dst="/m"), ))))
    result = CheckingMixin.check_filelist(api, _fake_torrent("E:/Elsewhere"))
    assert "路径不可判定" in result


def test_grouping_missing_scan_undetermined_skips(fa):
    """缺文件扫描映射 miss -> 跳过该组 + WARNING: 不暂停、不打标(报告 §05 红线)"""
    init_file_access(SimpleNamespace(fs=SimpleNamespace(path_map=(PathMapEntry(src="D:/Downloads", dst="/m"), ))))
    g, stopped, tagged = _bare_grouping()
    sizes = {"HA": {"a.mkv": 1}}
    g._check_missing_files([_fake_torrent("E:/Elsewhere")], sizes, dry_run=False, key="k")
    assert not stopped and not tagged  # 不可判定绝不触发暂停/打标


def test_grouping_missing_scan_local_stops(fa):
    """Local 缺文件 -> 整组暂停 + MISSING 标签(既有行为不劣化); 文件在 -> 零动作"""
    file_access._instance = LocalFileAccess()
    tmp = tmp_dir()
    g, stopped, tagged = _bare_grouping()
    # 真实缺失
    g._check_missing_files([_fake_torrent(tmp)], {"HA": {"ghost.mkv": 1}}, dry_run=False, key="k")
    assert stopped and tagged
    # 文件在且大小一致 -> 零动作
    stopped.clear()
    tagged.clear()
    g._missing_scanned_keys.clear()
    real = os.path.join(tmp, "ok.mkv")
    with open(real, "wb") as f:
        f.write(b"x" * 5)
    g._check_missing_files([_fake_torrent(tmp)], {"HA": {"ok.mkv": 5}}, dry_run=False, key="k")
    assert not stopped and not tagged


def tmp_dir():
    import tempfile
    return tempfile.mkdtemp()


def _bare_grouping():
    """构造绕过 __init__ 的 GroupingMixin 宿主(只供 _check_missing_files 的依赖面)"""
    stopped, tagged = [], []

    class _G(GroupingMixin):
        pass

    g = _G.__new__(_G)
    g.config = SimpleNamespace(grouping=SimpleNamespace(check_missing_files=True, missing_tag="MISSING"))
    g._missing_scanned_keys = set()
    g.api = SimpleNamespace(torrents_stop=lambda **kw: stopped.append(kw))
    g._add_tags = lambda t, tags, dry, log_level=None: tagged.append((t.hash, tuple(tags)))
    return g, stopped, tagged


def test_expr_exists_and_disk_undetermined(fa, monkeypatch, tmp_path):
    """exists()/disk_* 表达式映射 miss -> ExprError(显式报错优于静默 False, 与 disk_* 现状同口径);
    命中时取容器空间真值"""
    from auto_qb.rules.expr.env import _disk_total, _exists, _freespace

    init_file_access(SimpleNamespace(fs=SimpleNamespace(path_map=(PathMapEntry(src="D:/Downloads", dst="/m"), ))))
    with pytest.raises(ExprError, match="不可判定"):
        _exists(None, ["E:/Elsewhere"])
    with pytest.raises(ExprError, match="不可判定"):
        _disk_total(None, ["E:/Elsewhere"])
    with pytest.raises(ExprError, match="不可判定"):
        _freespace(None, ["E:/Elsewhere"])

    # 命中: disk_* 走容器空间(挂载点即同一块盘) —— patch shutil.disk_usage 验证取到值
    file_access._instance = _mapped(tmp_path)
    monkeypatch.setattr(shutil, "disk_usage", lambda p: SimpleNamespace(total=100, used=30, free=70))
    assert _disk_total(None, ["D:/Downloads"]) == 100
    assert _freespace(None, ["D:/Downloads"]) == 70
    assert _exists(None, ["D:/Downloads"]) is True


def test_freespace_condition_undetermined(fa, monkeypatch):
    """freespace 条件: 映射 miss -> ExprError; 真实 OSError 仍静默 False(既有口径不变)"""
    init_file_access(SimpleNamespace(fs=SimpleNamespace(path_map=(PathMapEntry(src="D:/Downloads", dst="/m"), ))))
    cond = FreespaceCondition({"path": "E:/Elsewhere", "amount": "<100GiB"})
    with pytest.raises(ExprError, match="不可判定"):
        cond.match(SimpleNamespace())


# ---------------------------------------------------------------- 配置校验


def _write_cfg(tmp_path, fs_body):
    raw = f"""
config:
  qbittorrent: {{host: h, port: 1, username: u, password: p}}
  trackers:
    T: {{domains: [a.com]}}
{fs_body}
"""
    p = tmp_path / "cfg.yml"
    p.write_text(raw, encoding="utf-8")
    return load_config(str(p))


def test_fs_config_roundtrip(tmp_path):
    """合法 fs.path_map 解析: entry 元组 + 尾斜杠保留原样(匹配层归一, 校验只拦歧义)"""
    cfg = _write_cfg(tmp_path, """
  fs:
    path_map:
      - from: 'D:/Downloads/'
        to: '/mnt/downloads'
""")
    assert cfg.fs.path_map == (PathMapEntry(src="D:/Downloads/", dst="/mnt/downloads"), )


def test_fs_config_empty_is_off(tmp_path):
    """空表/整段缺省 = 功能关(保守默认): path_map 为空元组"""
    assert _write_cfg(tmp_path, "  fs:\n    path_map: []\n").fs.path_map == ()
    assert _write_cfg(tmp_path, "").fs.path_map == ()


def test_fs_config_validation_errors(tmp_path):
    """校验聚合: 相对路径 from / to 缺根斜杠 / 重复 from / 前缀歧义 / 未知键 / 非列表"""
    cases = [
        ("  fs:\n    path_map:\n      - from: 'relative/path'\n        to: '/m'\n", "必须是绝对路径"),
        ("  fs:\n    path_map:\n      - from: 'D:/Downloads'\n        to: 'mnt/no-root'\n", "必须是"),
        (
            "  fs:\n    path_map:\n      - from: 'D:/Downloads'\n        to: '/a'\n      - from: 'd:/downloads/'\n        to: '/b'\n",
            "重复"
        ),
        (
            "  fs:\n    path_map:\n      - from: 'D:/Downloads'\n        to: '/a'\n      - from: 'D:/Downloads/sub'\n        to: '/b'\n",
            "歧义"
        ),
        ("  fs:\n    path_map:\n      - from: 'D:/Downloads'\n        to: '/a'\n        via: 'x'\n", "未知键"),
        ("  fs:\n    path_map: 'not-a-list'\n", "必须是列表"),
        ("  fs:\n    unknown_key: 1\n", "未知键"),
    ]
    for body, needle in cases:
        with pytest.raises(ConfigError, match=needle):
            _write_cfg(tmp_path, body)
