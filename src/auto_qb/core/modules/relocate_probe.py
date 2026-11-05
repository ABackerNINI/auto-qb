"""relocate_probe: 同机强探测 E1(假种一次性探测) —— 计划 26-11-04-0055 §04 P2

设计依据: 报告 26-11-03-2306 §11。用 qB 自己的搬运路径(setLocation)真写一次目标盘,
同时证明「qB 读得到本机 src」(证读: recheck 进 1.0)与「qB 写得到本机 dst」(证写:
本机 dst 出现文件且 size/SHA-1 一致、src 侧消失)。探测结论的缓存/消费在 relocate_mod
(P1 的 probe_get/probe_put)与执行链(P3 接线), 本模块只做探测与清理, 不做缓存决策 ——
调用方按 ProbeResult.env 决定是否写缓存(D7: FS 不可达(env=False)才缓存, 环境性失败
(env=True)不缓存, 下次重探)。

失败二分(报告 §11.3, 拍板 D7):
- env=False(FS 不可达, 可缓存): 证读超时(recheck 进不了 1.0)/ 证写超时或内容不符;
- env=True(环境性, 不缓存): 本机写探针失败(磁盘满/权限)/ add 被拒 / recheck 或
  setLocation 被 qB 拒绝 / 种子不可见 / API 异常(网络/凭据/连接中断)。

隔离与清理(报告 §11.4, 拍板 D8/R1/R2):
- 探针文件写入固定前缀临时子目录(`<src>/aqb-probe-<rand>/`, 不在 dst 根散落);
- add 参数: is_stopped=True(pitfalls/backend/qb-api.md「添加选项」节: 停止位只能用
  is_stopped= 传, is_paused=False 会被库折成 None)、use_auto_torrent_management=False
  (optional 字段省略 = 回落 qB 会话默认, 恒显式下发)、category 空、tag=TAG_PROBE、
  无 tracker、autoTMM=false —— 避免被用户分类/自动管理规则搬走;
- 各阶段失败路径一律执行尽力清理(finally 语义), 绝不把探针种子留在用户 qB 里;
  清理失败不改变探测结论, 只进 evidence 并 logger.warning;
- 崩溃残留兜底: sweep_probe_residue 按 tag 扫描删除, 挂 relocate 生命周期启动钩子。

qbapi 口径: 全部 qB 调用走 ctx.api(QbApi Facade 既有透传方法 torrents_add(文件方式)/
torrents_recheck/torrents_set_location/torrents_delete(delete_files=True)/torrents_info
(tag= 过滤)), 本文件不裸散 client 调用、不新建连接方式。
"""
import hashlib
import os
import secrets
import shutil
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

from ...infra import clock
from ...infra import file_access
from .relocate_common import logger

# ---------- 常量单点(计划 §04 P2-⑤: 每步独立短超时, 总预算收敛; 真机实测常态 ~1.3s) ----------

TAG_PROBE = "aqb-probe"  # 探测种子隔离标签(R1: tag 隔离 + 启动扫描兜底都按它)
PROBE_DIR_PREFIX = "aqb-probe-"  # 临时子目录固定前缀(D8: 目录隔离不散落; 残留扫描按前缀认领)
PROBE_FILE_SIZE = 4096  # 探针内容 4KiB(单 piece)
PROBE_PIECE_LENGTH = 16384  # piece length 16KiB => 1 个 piece
PROBE_READ_TIMEOUT_S = 10.0  # 证读预算: 种子可见 + recheck 进 1.0
PROBE_WRITE_TIMEOUT_S = 10.0  # 证写预算: setLocation 后 dst 出现一致文件且 src 消失
PROBE_CLEANUP_TIMEOUT_S = 5.0  # 清理预算: deleteFiles + 轮询种子消失
PROBE_POLL_INTERVAL_S = 0.25  # 轮询间隔(报告 §11.2 实测口径)

# 探测结论合法取值(与 relocate_mod._PROBE_STATUSES 对齐)
STATUS_PASSED = "passed"
STATUS_FAILED = "failed"


@dataclass
class ProbeResult:
    """一次 E1 探测的结论(status/reason/env/evidence)

    status: "passed" | "failed"; reason: 稳定的 snake 判语(P3/P5 按 env + reason 出文案);
    env: True = 环境性失败(D7: 不写缓存); evidence: 进 state 的证据 dict(JSON 兼容)。
    """

    status: str
    reason: str
    env: bool
    evidence: dict = field(default_factory=dict)


# ---------- 指纹(拍板 D3: 失效指纹 = host+port+username+password/api_key 哈希) ----------


def probe_fingerprint(qb_config: Any) -> str:
    """qB 连接身份指纹: sha1("host|port|username|secret") 十六进制截短 16 位

    secret 取 password(登录凭据, 首选)或 api_key(5.x Bearer 直连, 备选), 两者有谁用谁,
    都空则空串。任一字段变化 => 指纹变化 => 缓存失效重探(P3 消费)。
    """
    host = getattr(qb_config, "host", "") or ""
    port = getattr(qb_config, "port", "") or ""
    username = getattr(qb_config, "username", "") or ""
    secret = getattr(qb_config, "password", "") or getattr(qb_config, "api_key", "") or ""
    raw = f"{host}|{port}|{username}|{secret}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


# ---------- 造种(报告 §11.1-1: 单文件 4KiB / piece 16KiB / 手工 bencode / 无 tracker / 非私有) ----------


def _bencode(obj: Any) -> bytes:
    """最小 bencode 编码(只够本模块造种用; 解码侧已有 hr/bencode.py, 不引第三方)"""
    if isinstance(obj, bool):
        raise TypeError("bencode 不接受 bool")
    if isinstance(obj, int):
        return b"i%de" % obj
    if isinstance(obj, bytes):
        return b"%d:%s" % (len(obj), obj)
    if isinstance(obj, str):
        data = obj.encode("utf-8")
        return b"%d:%s" % (len(data), data)
    if isinstance(obj, (list, tuple)):
        return b"l" + b"".join(_bencode(v) for v in obj) + b"e"
    if isinstance(obj, dict):
        out = [b"d"]
        for key in sorted(obj):  # 规范要求按键字节序排序
            encoded_key = key.encode("utf-8") if isinstance(key, str) else key
            out.append(_bencode(encoded_key))
            out.append(_bencode(obj[key]))  # 回查用原 key(编码副本只是输出形态)
        out.append(b"e")
        return b"".join(out)
    raise TypeError(f"bencode 不支持的类型: {type(obj)!r}")


def make_probe_content() -> bytes:
    """探针内容: 4KiB 随机字节(内容随机 => SHA-1 比对有区分度, 不可能撞上旧文件)"""
    return os.urandom(PROBE_FILE_SIZE)


def build_probe_torrent(content: bytes, name: str) -> bytes:
    """手工 bencode 的单文件 .torrent(约 102B): 无 announce(无 tracker)、无私有标志

    infohash = sha1(bencode(info)), 可由本函数输出反推 —— 单测用 hr.bencode.bdecode 回读钉结构。
    """
    info = {
        "length": len(content),
        "name": name,
        "piece length": PROBE_PIECE_LENGTH,
        "pieces": hashlib.sha1(content).digest(),
    }
    return _bencode({"info": info})


# ---------- 探测主函数 ----------


def _failed(evidence: dict, reason: str, env: bool, extra: dict | None = None) -> ProbeResult:
    """失败结论统一出口: 附加重写 evidence 后返回(保持各失败路径形状一致)"""
    if extra:
        evidence.update(extra)
    return ProbeResult(STATUS_FAILED, reason, env, evidence)


def _map_local(path: str) -> str:
    """qB 视角逻辑路径 -> 本机 syscall 路径(file_access.map_to_container 既有单点)

    与 relocate_proof._syscall / relocate_plan._syscall 同款: 未命中/无映射/查询失败
    原样返回 —— 宿主直跑(零映射)行为与不映射逐字节一致; 容器部署(path_map 非空)时,
    探测的本机读写侧必须经它换算, 否则本机 stat 不到 qB 视角路径, 证写超时(env=False)
    被永久缓存, 多成员组被永久硬拦。qB API 侧(save_path/location)保持逻辑路径不动。
    """
    try:
        fa = file_access.get_file_access()
        return fa.map_to_container(path) or path
    except Exception:  # noqa: BLE001 - 映射查询失败按原路径(本机直跑形态, 旧行为)
        return path


def _await_probe_torrent(api: Any, deadline: float, evidence: dict) -> Any:
    """轮询按 tag 列种子直到探针种子可见(报告实测 add 后 ~0.26s 可见); 超时/异常返回 None

    按 tag 而非 hash 定位: add 响应形态跨版本分裂(Web API 2.14.0 前后), 而 tag 是我们
    自己下发的确定事实; 单一写线程下同 tag 只会有探测种子(启动扫描已清历史残留)。
    """
    while clock.SYSTEM_CLOCK.monotonic() < deadline:
        try:
            tors = api.torrents_info(tag=TAG_PROBE) or []
        except Exception as e:  # noqa: BLE001 - API 异常按环境性失败处理
            evidence["error"] = str(e)
            return None
        for tor in tors:
            if getattr(tor, "hash", None):
                return tor
        time.sleep(PROBE_POLL_INTERVAL_S)
    return None


def _read_progress_poll(api: Any, torrent_hash: str, deadline: float, evidence: dict) -> str:
    """轮询 recheck 进度; 返回 "ok" / "timeout"(FS 不可达方向) / "api_error"(环境性)"""
    while True:
        try:
            tors = api.torrents_info(torrent_hashes=[torrent_hash]) or []
        except Exception as e:  # noqa: BLE001 - API 异常(网络/连接中断)按环境性失败
            evidence["error"] = str(e)
            return "api_error"
        progress = getattr(tors[0], "progress", 0.0) if tors else 0.0
        if tors and float(progress or 0.0) >= 1.0:
            return "ok"
        if clock.SYSTEM_CLOCK.monotonic() >= deadline:
            return "timeout"
        time.sleep(PROBE_POLL_INTERVAL_S)


def _file_matches(path: str, expect_sha: str, expect_size: int) -> bool:
    """本机文件 size + SHA-1 双比对(任一不符/读不了都算不一致)"""
    try:
        if os.path.getsize(path) != expect_size:
            return False
        digest = hashlib.sha1()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest() == expect_sha
    except OSError:
        return False


def _write_proof_poll(dst_file: str, src_file: str, expect_sha: str, expect_size: int, deadline: float) -> str:
    """轮询证写: dst 出现一致文件且 src 消失; 返回 "ok"/"timeout"/"mismatch"

    dst 出现但内容尚不符可能是跨卷复制进行中(报告 §11.3: 跨卷时 qB 逐文件复制),
    不当场判 mismatch —— 统一收口在超时时刻再定性(dst 在场 = mismatch, 不在场 = timeout)。
    """
    while True:
        if os.path.isfile(dst_file) and _file_matches(dst_file, expect_sha, expect_size):
            if not os.path.exists(src_file):
                return "ok"
            # dst 已一致但源未消失: qB 只复制未搬走, 继续等( setLocation 语义应搬走)
        if clock.SYSTEM_CLOCK.monotonic() >= deadline:
            return "mismatch" if os.path.isfile(dst_file) else "timeout"
        time.sleep(PROBE_POLL_INTERVAL_S)


def _cleanup(api: Any, torrent_hash: str, dirs: Iterable[str], evidence: dict) -> None:
    """尽力清理(finally 语义): deleteFiles 删种子 -> 轮询消失 -> rmtree 两侧临时目录

    失败不抛不改变探测结论: 进 evidence["cleanup"] 并 logger.warning(R2: 启动扫描/人工兜底)。
    hash 拿不到(add 受理但按 tag 不可见, probe_hash=None)时按 tag 补一次定位删除(尽力,
    失败只 warning —— 残留由启动扫描兜底), 免得探针种子留在用户 qB 里。
    """
    info: dict[str, Any] = {"torrent_deleted": False, "torrent_gone": None, "dirs_removed": [], "residue": []}
    deadline = clock.SYSTEM_CLOCK.monotonic() + PROBE_CLEANUP_TIMEOUT_S
    if not torrent_hash:
        # 种子不可见(add 受理但按 tag 列不出)拿不到 hash: 按 tag 补删(同一写线程下同 tag
        # 只有探测种子; 此刻仍不可见 = 真没有, 轮询空列表零动作)
        try:
            for tor in api.torrents_info(tag=TAG_PROBE) or []:
                h = getattr(tor, "hash", None)
                if not h:
                    continue
                try:
                    api.torrents_delete(torrent_hashes=[h], delete_files=True)
                    info["torrent_deleted"] = True
                except Exception as e:  # noqa: BLE001 - 尽力删除, 失败只告警
                    info["tag_delete_error"] = str(e)
                    logger.warning(f"relocate | probe: 按 tag 补删探测种子失败 {h}({e})")
        except Exception as e:  # noqa: BLE001 - 定位失败只告警, 结论不受清理失败影响
            info["tag_locate_error"] = str(e)
            logger.warning(f"relocate | probe: 按 tag 定位探测种子失败({e}) —— 残留由启动扫描清理")
    if torrent_hash:
        try:
            api.torrents_delete(torrent_hashes=[torrent_hash], delete_files=True)
            info["torrent_deleted"] = True
        except Exception as e:  # noqa: BLE001 - 清理路径不抛: 结论不受清理失败影响
            info["delete_error"] = str(e)
            logger.warning(f"relocate | probe: 删除探测种子失败({e}) —— 残留由启动扫描按 tag 清理")
        while clock.SYSTEM_CLOCK.monotonic() < deadline:
            try:
                if not (api.torrents_info(torrent_hashes=[torrent_hash]) or []):
                    info["torrent_gone"] = True
                    break
            except Exception as e:  # noqa: BLE001 - 轮询失败只记录, 继续目录清理
                info["gone_error"] = str(e)
                break
            time.sleep(PROBE_POLL_INTERVAL_S)
        if info["torrent_gone"] is not True:
            info["torrent_gone"] = False
    for d in dirs:
        try:
            shutil.rmtree(d)
            info["dirs_removed"].append(d)
        except FileNotFoundError:
            info["dirs_removed"].append(d)  # 本就不存在(如被整目录搬走): 视为清理完成
        except Exception as e:  # noqa: BLE001 - 同上: 只告警不抛
            info["residue"].append(d)
            logger.warning(f"relocate | probe: 临时目录清理失败 {d}({e})")
    leftover = sorted(d for d in dirs if os.path.exists(d))
    if leftover:
        info["residue"] = sorted(set(info["residue"]) | set(leftover))
        logger.warning(f"relocate | probe: 清理后仍有残留 {leftover} —— 启动扫描/人工清理兜底")
    evidence["cleanup"] = info


def run_probe(ctx: Any, src: str, dst: str) -> ProbeResult:
    """E1 同机强探测: 造种 -> 落源 -> add -> 证读(recheck) -> 证写(setLocation) -> 清理

    ctx: AppContext 形态(消费 ctx.api; 无 api/客户端视为环境性失败)。src/dst 是待证明
    同 FS 的一对目录(通常为组 content_root 与迁移目标卷根)。每步独立短超时(常量单点),
    各阶段失败路径都执行尽力清理(finally), 绝不把探针种子留在用户 qB 里。
    """
    started = clock.SYSTEM_CLOCK.monotonic()
    evidence: dict = {"method": "e1"}
    api = getattr(ctx, "api", None)
    if api is None or getattr(api, "client", None) is None:
        return _failed(evidence, "api_unavailable", True)
    token = secrets.token_hex(6)
    name = f"{PROBE_DIR_PREFIX}{token}.bin"  # info.name = aqb-probe-<rand>.bin
    src_dir = os.path.join(src, PROBE_DIR_PREFIX + token)  # D8: 临时子目录隔离(qB 视角逻辑路径)
    dst_dir = os.path.join(dst, PROBE_DIR_PREFIX + token)
    # 本机读写侧统一经 map_to_container 换算(major 修: 容器 path_map 部署下 qB 视角路径
    # 本机 stat 不到, 直用会证写超时被永久缓存); qB API 侧 save_path/location 保持逻辑路径
    local_src_dir = _map_local(src_dir)
    local_dst_dir = _map_local(dst_dir)
    local_src_file = os.path.join(local_src_dir, name)
    local_dst_file = os.path.join(local_dst_dir, name)
    evidence.update(name=name, src_dir=src_dir, dst_dir=dst_dir, size=PROBE_FILE_SIZE)
    content = make_probe_content()
    expect_sha = hashlib.sha1(content).hexdigest()
    evidence["sha1"] = expect_sha
    torrent = build_probe_torrent(content, name)
    probe_hash = None
    try:
        # a. 落源(本机写; 磁盘满/权限失败 = 环境性)
        try:
            os.makedirs(local_src_dir)
            with open(local_src_file, "wb") as f:
                f.write(content)
        except OSError as e:
            return _failed(evidence, "local_write_failed", True, {"error": str(e)})
        # b. add(paused/stopped 兼容: 停止位只能用 is_stopped= 传, 见 qb-api 坑档)
        try:
            api.torrents_add(
                torrent_files=[torrent],
                save_path=src_dir,
                category=None,
                tags=TAG_PROBE,
                is_stopped=True,
                use_auto_torrent_management=False,
            )
        except Exception as e:  # noqa: BLE001 - add 被拒(磁盘满/队列满/4xx) = 环境性
            return _failed(evidence, "add_rejected", True, {"error": str(e)})
        # c. 证读: 显式 recheck, 轮询 progress==1.0(qB 校验通过 = 读到了本机这份内容)
        tor = _await_probe_torrent(api, clock.SYSTEM_CLOCK.monotonic() + PROBE_READ_TIMEOUT_S, evidence)
        if tor is None:
            # 可见超时与 API 异常都是环境性(qB 状态/连接问题, 与 FS 无关)
            reason = "torrent_invisible" if "error" not in evidence else "api_error"
            return _failed(evidence, reason, True)
        probe_hash = tor.hash
        evidence["hash"] = probe_hash
        try:
            api.torrents_recheck(torrent_hashes=[probe_hash])
        except Exception as e:  # noqa: BLE001 - recheck 被拒 = 环境性
            return _failed(evidence, "recheck_rejected", True, {"error": str(e)})
        read_verdict = _read_progress_poll(
            api, probe_hash,
            clock.SYSTEM_CLOCK.monotonic() + PROBE_READ_TIMEOUT_S, evidence
        )
        if read_verdict == "api_error":
            return _failed(evidence, "api_error", True)
        if read_verdict != "ok":
            return _failed(evidence, "read_proof_timeout", False)  # FS 不可达方向(可缓存)
        evidence["read_ok"] = True
        # d. 证写: setLocation 到 dst 侧临时子目录, 本机轮询 dst 出现一致文件 + src 消失
        try:
            api.torrents_set_location(torrent_hashes=[probe_hash], location=dst_dir)
        except Exception as e:  # noqa: BLE001 - setLocation 被拒 = 环境性
            return _failed(evidence, "set_location_rejected", True, {"error": str(e)})
        verdict = _write_proof_poll(
            local_dst_file, local_src_file, expect_sha, len(content),
            clock.SYSTEM_CLOCK.monotonic() + PROBE_WRITE_TIMEOUT_S
        )
        if verdict != "ok":
            extra = {}
            if os.path.isfile(local_dst_file):
                extra["dst_seen"] = True
            if os.path.exists(local_src_file):
                extra["src_present"] = True
            return _failed(evidence, "write_mismatch" if verdict == "mismatch" else "write_proof_timeout", False, extra)
        evidence["write_ok"] = True
        evidence["elapsed_s"] = round(clock.SYSTEM_CLOCK.monotonic() - started, 3)
        return ProbeResult(STATUS_PASSED, "ok", False, evidence)
    finally:
        # e. 清理(所有出口都走): deleteFiles -> 轮询种子消失 -> rmtree 两侧临时目录(本机侧)
        _cleanup(api, probe_hash, (local_src_dir, local_dst_dir), evidence)


# ---------- 启动残留扫描(R2: 崩溃在 add 之后 delete 之前会留探测种子+文件) ----------


def sweep_probe_residue(ctx: Any) -> int:
    """按 tag=TAG_PROBE 列种子, deleteFiles 删除并清理已知前缀的临时目录; 返回清理条数

    幂等(重复调用二次为 0), 异常一律吞掉只 logger.warning —— 扫描失败绝不能挡启动。
    deleteFiles 双条件(保守默认): tag 命中只说明"可能"是探测种子, 种子名或保存路径带
    aqb-probe 固定前缀才认领并删文件 —— 极端(用户自己打了同名 tag 的种子)只删种子记录,
    绝不 delete_files 误删用户数据; 目录侧同样只清自己命名规律的路径。
    """
    api = getattr(ctx, "api", None)
    if api is None or getattr(api, "client", None) is None:
        return 0
    try:
        tors = api.torrents_info(tag=TAG_PROBE) or []
    except Exception as e:  # noqa: BLE001 - 扫描失败只告警, 不挡启动
        logger.warning(f"relocate | probe: 启动残留扫描列种子失败({e})")
        return 0
    cleaned = 0
    for tor in tors:
        t_hash = getattr(tor, "hash", None)
        save_path = getattr(tor, "save_path", "") or ""
        ours = str(getattr(tor, "name", "") or "").startswith(PROBE_DIR_PREFIX) or \
            os.path.basename(str(save_path).rstrip("\\/")).startswith(PROBE_DIR_PREFIX)
        try:
            if t_hash:
                api.torrents_delete(torrent_hashes=[t_hash], delete_files=ours)
        except Exception as e:  # noqa: BLE001 - 单条失败不影响其余条目
            logger.warning(f"relocate | probe: 残留探测种子删除失败 {t_hash}({e})")
            continue
        cleaned += 1
        base = os.path.basename(str(save_path).rstrip("\\/"))
        if base.startswith(PROBE_DIR_PREFIX):  # 只清自己命名规律的目录(保守默认)
            try:
                shutil.rmtree(save_path)
            except Exception as e:  # noqa: BLE001 - 目录清理失败只告警
                logger.warning(f"relocate | probe: 残留目录清理失败 {save_path}({e})")
    if cleaned:
        logger.warning(f"relocate | probe: 启动扫描清理上次崩溃残留探测种子 {cleaned} 个")
    return cleaned
