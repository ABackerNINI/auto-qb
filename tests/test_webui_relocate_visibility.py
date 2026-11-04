"""WebUI 迁移可见性 P0/P1(plan 26-11-04-1042): 快照/标注/组级聚合/指纹/行内徽标/筛选/详情段

## 测试计划
- test_state_of_phase_merges: 相位归并到 moving / pending_finalize / done / failed / cancelled(未知按 moving)
- test_member_relocate_origin_mover_and_contract: 成员标注字段、mover 精确归属、origin 来自 job、save_path 不变
- test_origin_roundtrip_and_legacy_unknown: web/rule/cli origin 落账回读; 旧 state 条目缺 origin 回落 unknown
- test_snapshot_prefers_active_job_over_old_terminal: 同 hash 活跃新 job 取代终态旧 job, 快照换代并置 full 脏
- test_group_relocate_priority_mixed_and_order_independent: 组级 failed>moving>pending_finalize>done、同优先级多 job 记 mixed、pending/total/job_ids/dst、成员顺序无关、全 cancelled 为 None
- test_relocate_null_when_disabled_or_no_jobs: relocate 关 / 无 job(含旧 state 无 relocate 段) => relocate 字段 null
- test_view_build_does_not_probe_filesystem_or_iterate_jobs: 列表构建期不 lstat/stat/readlink/islink, 不遍历 _jobs
- test_decorate_fingerprint_includes_relocate: decorate.js 成员/组 relocate 签名进指纹且槽位长度同步
- test_p1_badge_rendered_in_path_cells: 组行/种子行路径列渲染 button.rel-badge, click.stop 只开详情
- test_p1_badge_state_mapping_node: node 探针验证 moving/pending/failed/mixed 词表与 done/空态不挂徽标
- test_p1_filter_semantics_and_path_filter_untouched: 迁移状态筛走 facetRows/_facetOptions, 路径筛仍按 save_path
- test_p1_filter_behavior_node: node 探针真跑 filteredGroups/relocateOptions —— 组内或、跨筛与、路径筛叠加、清空重置
- test_p1_detail_section_and_endpoint_projection: 详情端点带 relocate; 无 job 时详情段整段不渲染
- test_p1_detail_endpoint_passes_relocate: 真实 /api/torrents/{hash} 端点: 有 job 回传 relocate 投影, 无 job 为 null, save_path 不变
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest

from auto_qb.core.modules import relocate_units as ru
from auto_qb.core.modules.relocate_units import RelocateJob
from helpers import relocate_env


def _job(
    job_id: str,
    hashes=("HA", "HB"),
    *,
    mover: str = "HA",
    phase: str = ru.PHASE_MOVING,
    origin: str = "web",
    updated_at: float = 1.0,
    created_at: float = 0.5,
    alias_paths=(),
) -> RelocateJob:
    return RelocateJob(
        job_id=job_id,
        hashes=tuple(hashes),
        mover=mover,
        src=r"R:\src",
        dst=r"R:\dst",
        scope=r"R:\src",
        alias_kind="file" if alias_paths else "",
        alias_paths=tuple(alias_paths),
        phase=phase,
        origin=origin,
        created_at=created_at,
        updated_at=updated_at,
    )


def _row(env, recs=None):
    key = next(iter(env.mgr.store.groups))
    if recs is None:
        recs = [env.mgr.store.by_hash[h] for h in env.mgr.store.groups[key]]
    return env.mgr._build_group_row(key, recs, set())


@pytest.mark.parametrize(
    "phase,state",
    [
        (ru.PHASE_MOVING, "moving"),
        (ru.PHASE_WATCHING, "moving"),
        (ru.PHASE_MOVED, "pending_finalize"),
        (ru.PHASE_ARMED, "pending_finalize"),
        (ru.PHASE_REMOVING, "pending_finalize"),
        (ru.PHASE_REMOVED, "pending_finalize"),
        (ru.PHASE_FINALIZING, "pending_finalize"),
        (ru.PHASE_DONE, "done"),
        (ru.PHASE_FAILED, "failed"),
        (ru.PHASE_CANCELLED, "cancelled"),
        ("", "moving"),
        ("legacy_unknown", "moving"),
    ],
)
def test_state_of_phase_merges(phase, state):
    from auto_qb.webui.views_relocate import state_of_phase

    assert state_of_phase(phase) == state


def test_member_relocate_origin_mover_and_contract(tmp_path):
    env = relocate_env(tmp_path)
    env.mgr.ctx.relocate.register_job(
        _job("j1", phase=ru.PHASE_MOVING, origin="rule", alias_paths=["a", "b"], updated_at=5.0)
    )
    ha = env.mgr._member_view(env.mgr.store.by_hash["HA"])["relocate"]
    hb = env.mgr._member_view(env.mgr.store.by_hash["HB"])["relocate"]
    assert ha and hb
    assert ha["state"] == "moving" and ha["phase"] == ru.PHASE_MOVING
    assert ha["mover"] is True, "mover 必须按 job.mover 精确匹配"
    assert hb["mover"] is False
    assert ha["origin"] == "rule", "origin 必须来自 job, 不得按调用路径猜"
    assert ha["alias_kind"] == "file" and ha["alias_count"] == 2
    assert ha["job_id"] == "j1" and ha["updated_at"] == 5.0
    assert ha["created_at"] == 0.5, "设置时间来自 job 登记时刻, 必须随 relocate 投影下发"
    # 不改 save_path: 迁移可见性只加标注, 路径筛选仍按 qB save_path 语义
    assert env.mgr._member_view(env.mgr.store.by_hash["HA"])["save_path"] == env.src


def test_origin_roundtrip_and_legacy_unknown():
    for origin in ("web", "rule", "cli"):
        d = ru.job_to_dict(_job("j", origin=origin))
        assert d["origin"] == origin
        assert ru.job_from_dict(d).origin == origin
    legacy = ru.job_to_dict(_job("j", origin="web"))
    legacy.pop("origin")
    assert ru.job_from_dict(legacy).origin == "unknown", "旧 state 条目缺 origin 必须回落 unknown"


def test_snapshot_prefers_active_job_over_old_terminal(tmp_path):
    env = relocate_env(tmp_path)
    mod = env.mgr.ctx.relocate
    mod.register_job(_job("j_old", phase=ru.PHASE_DONE, updated_at=100.0))
    assert mod.jobs_snapshot().job_for("HA")["job_id"] == "j_old"
    mod.register_job(_job("j_new", phase=ru.PHASE_MOVING, updated_at=1.0))
    snap = mod.jobs_snapshot()
    assert snap.job_for("HA")["job_id"] == "j_new", "同一 hash 必须取活跃 job, 即使终态 job 更新更晚"
    assert env.mgr._member_view(env.mgr.store.by_hash["HA"])["relocate"]["state"] == "moving"
    assert snap.generation >= 2
    assert env.mgr.web.group_view_dirty is True
    assert "relocate_jobs" in env.mgr.web._pending_full_reasons


def test_group_relocate_priority_mixed_and_order_independent(tmp_path):
    env = relocate_env(tmp_path)
    mod = env.mgr.ctx.relocate
    key = next(iter(env.mgr.store.groups))
    members = [env.mgr.store.by_hash[h] for h in env.mgr.store.groups[key]]

    mod.register_job(_job("j_fail", hashes=("HA", ), phase=ru.PHASE_FAILED, updated_at=2.0))
    mod.register_job(_job("j_move", hashes=("HB", ), phase=ru.PHASE_MOVING, updated_at=3.0))
    row = env.mgr._build_group_row(key, members, set())
    assert row["relocate"]["state"] == "failed", "failed 优先于 moving"
    assert row["relocate"]["pending"] == 1 and row["relocate"]["total"] == 2
    assert row["relocate"]["job_ids"] == ["j_fail", "j_move"]

    # 同一 hash 的活跃新 job 取代终态 failed: 组成员标注取活跃者, failed 不再挂出
    mod.register_job(_job("j_armed_a", hashes=("HA", ), phase=ru.PHASE_ARMED, updated_at=4.0))
    row = env.mgr._build_group_row(key, members, set())
    assert row["relocate"]["state"] == "moving", "moving(HB) 优先于 pending_finalize(HA)"
    assert "j_fail" not in row["relocate"]["job_ids"], "被活跃 job 取代的终态 job 不进组级标注"

    # 同优先级两个不同 job => mixed
    mod.register_job(_job("j_move_a2", hashes=("HA", ), phase=ru.PHASE_MOVING, updated_at=5.0))
    row = env.mgr._build_group_row(key, members, set())
    assert row["relocate"]["state"] == "mixed", "同优先级两个 job 必须 mixed"
    assert row["relocate"]["pending"] == 2

    # 顺序无关
    assert env.mgr._build_group_row(key, list(reversed(members)), set())["relocate"] == row["relocate"]

    # dst 去重排序
    assert row["relocate"]["dst"] == [r"R:\dst"]

    # 先撤销在途 job, 再登记单个全组 done => done(非 mixed)
    for jid, hashes in (("j_move_a2", ("HA", )), ("j_armed_a", ("HA", )), ("j_move", ("HB", ))):
        mod.register_job(_job(jid, hashes=hashes, phase=ru.PHASE_CANCELLED, updated_at=7.0))
    mod.register_job(_job("j_done", phase=ru.PHASE_DONE, updated_at=8.0))
    row2 = env.mgr._build_group_row(key, members, set())
    assert row2["relocate"]["state"] == "done" and row2["relocate"]["pending"] == 0

    # 全 cancelled => 无组级标注
    mod.register_job(_job("j_done", phase=ru.PHASE_CANCELLED, updated_at=9.0))
    assert env.mgr._build_group_row(key, members, set())["relocate"] is None


def test_relocate_null_when_disabled_or_no_jobs(tmp_path):
    env = relocate_env(tmp_path)
    # 无 job(等价旧 state.json 没有 relocate 段) => null
    assert env.mgr._member_view(env.mgr.store.by_hash["HA"])["relocate"] is None
    assert _row(env)["relocate"] is None

    env.mgr.ctx.relocate.register_job(_job("j1", phase=ru.PHASE_MOVING))
    assert env.mgr._member_view(env.mgr.store.by_hash["HA"])["relocate"] is not None

    # relocate 关: 即使内存仍有 job 也必须 null
    env.mgr.config.relocate.enabled = False
    assert env.mgr._member_view(env.mgr.store.by_hash["HA"])["relocate"] is None
    assert _row(env)["relocate"] is None


def test_view_build_does_not_probe_filesystem_or_iterate_jobs(tmp_path, monkeypatch):
    env = relocate_env(tmp_path)
    mod = env.mgr.ctx.relocate
    mod.register_job(_job("j1", phase=ru.PHASE_MOVING, alias_paths=["a"]))
    members = env.mgr.store.by_hash["HA"]

    calls = []

    def _boom(*a, **k):
        calls.append((a, k))
        raise AssertionError("列表构建期禁止文件系统探测")

    for name in ("lstat", "stat", "readlink"):
        monkeypatch.setattr(os, name, _boom)
    monkeypatch.setattr(os.path, "islink", _boom)

    class _NoIterJobs(dict):
        def __iter__(self):
            raise AssertionError("Web 构建期禁止遍历 _jobs")

        def values(self):
            raise AssertionError("Web 构建期禁止遍历 _jobs")

        def items(self):
            raise AssertionError("Web 构建期禁止遍历 _jobs")

    monkeypatch.setattr(mod, "_jobs", _NoIterJobs(mod._jobs))
    env.mgr._member_view(members)
    row = _row(env)
    assert row["members"][0]["relocate"]["state"] == "moving"
    assert not calls


def test_decorate_fingerprint_includes_relocate():
    from pathlib import Path

    js = (Path(__file__).resolve().parents[1] /
          "src/auto_qb/webui/static/shared/decorate.js").read_text(encoding="utf-8")
    assert "function _relocateSig(" in js and "function _groupRelocateSig(" in js
    assert "_relocateSig(m.relocate)" in js
    assert "fp.length !== ms.length * 8 + 3" in js, "成员 relocate 槽 + 组 relocate 槽必须同步长度"
    assert "_groupRelocateSig(g.relocate)" in js
    assert "r.armed_at" in js and "r.src" in js, "P1 详情/徽标消费 src/armed_at, 必须进装饰指纹"
    assert "r.created_at" in js, "P1 详情消费设置时间, 新字段必须进装饰指纹"


def _static(name: str) -> str:
    from pathlib import Path

    return (Path(__file__).resolve().parents[1] / "src/auto_qb/webui/static" / name).read_text(encoding="utf-8")


def test_p1_badge_rendered_in_path_cells():
    cells = _static("shared/tpl/xtpl-cells.html")
    assert cells.count('class="rel-badge"') >= 2, "组行与种子行路径列都要有迁移徽标"
    assert cells.count('type="button" class="rel-badge"') == 2, "徽标必须是可访问 button(非 div/span)"
    assert cells.count('@click.stop="$root.relocateOpen(') == 2, "徽标点击只能开详情, 不得冒泡触发路径筛选"
    assert cells.count("$root.relocateBadge(") >= 4, "徽标文案/类/title 必须走同一展示方法, 模板不写状态字面量"
    assert ".g-save-path.has-rel" in _static("shared/row_lang.css")
    css = _static("shared/row_lang.css")
    assert ".rl-scope .rel-badge" in css
    # 可访问性验收: 焦点环必须钉在徽标自己身上(文件里别处也有 :focus-visible, 泛断言守不住)
    assert ".rl-scope .rel-badge:focus-visible" in css, "徽标必须有焦点可见样式"


_NODE_BADGE_PROBE = r"""
const fs=require('fs'),vm=require('vm');
const sandbox={window:{},console};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
const M=Object.assign({},sandbox.window.AQB_DECORATE.methods);
const call=(name,row)=>M[name].call(Object.assign({},M),row);
const b=(row)=>{const x=call('relocateBadge',row);return x&&{label:x.label,cls:x.cls,title:x.title};};
const out={
  moving:b({relocate:{state:'moving',src:'R:/src',dst:'R:/dst'}}),
  pending:b({relocate:{state:'pending_finalize',src:'R:/src',dst:'R:/dst',armed_at:5}}),
  failed:b({relocate:{state:'failed',src:'R:/src',dst:'R:/dst',reason:'boom'}}),
  mixed:b({members:[{}],relocate:{state:'mixed',pending:1,total:2,dst:['R:/dst']}}),
  done:b({relocate:{state:'done',src:'R:/src',dst:'R:/dst'}}),
  cancelled:b({relocate:{state:'cancelled',src:'R:/src',dst:'R:/dst'}}),
  none:b({relocate:null}),
  buckets:call('_relocateBuckets',{members:[
    {relocate:{state:'moving'}},{relocate:{state:'pending_finalize'}},{relocate:{state:'done'}},{}
  ]}),
  target:call('relocateTargetHash',{members:[{hash:'H0'},{hash:'H1',relocate:{mover:true}}]}),
  targetNone:call('relocateTargetHash',{members:[{hash:'H0'}]}),
};
process.stdout.write(JSON.stringify(out));
"""


def test_p1_badge_state_mapping_node():
    node = shutil.which("node")
    if not node:
        return
    from pathlib import Path

    js = Path(__file__).resolve().parents[1] / "src/auto_qb/webui/static/shared/decorate.js"
    proc = subprocess.run([node, "-e", _NODE_BADGE_PROBE, str(js)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)

    assert out["moving"]["label"] == "迁移中" and out["moving"]["cls"] == "moving"
    assert out["moving"]["title"].startswith("迁移中") and "R:/src → R:/dst" in out["moving"]["title"]
    assert out["pending"]["label"] == "待收尾" and out["pending"]["cls"] == "pending"
    assert "已武装收尾" in out["pending"]["title"]
    assert out["failed"]["label"] == "迁移失败" and out["failed"]["cls"] == "failed"
    assert "boom" in out["failed"]["title"]
    assert out["mixed"]["label"] == "迁移多任务" and out["mixed"]["cls"] == "mixed"
    # 空态/终态绝不挂徽标 —— 没有迁移记录时不得出现「已完成」误导结论
    assert out["done"] is None and out["cancelled"] is None and out["none"] is None
    # 组级筛选桶: 组内任一成员落档即保留; done 只贡献「有过迁移」
    assert "迁移中" in out["buckets"] and "待收尾" in out["buckets"] and "有过迁移" in out["buckets"]
    assert out["target"] == "H1", "组行徽标优先打开搬移成员详情"
    assert out["targetNone"] == "H0", "无迁移成员时退回组内首成员"


def test_p1_filter_semantics_and_path_filter_untouched():
    filters = _static("shared/filters.js")
    state = _static("shared/state.js")
    assert "relocateFilter: []" in state
    assert "relocateOptions() {" in filters
    assert '_facetOptions("relocate")' in filters and 'kind === "relocate"' in filters
    assert 'kind: "relocate", label: "迁移状态"' in filters
    assert "this.relocateFilter.length" in filters, "迁移状态筛选必须进入筛选激活判定/应用分支"
    assert '_relocateBuckets(g)' in filters and '_relocateBuckets(r)' in filters
    assert '_relocateBuckets(m)' in _static("shared/hr.js"), "展开组成员也要吃迁移状态筛选"
    # 路径筛选保持 qB save_path 语义不变(用户已拍板)
    assert "this.pathFilter.includes(g.save_path)" in filters
    assert "this.pathFilter.includes(r.save_path || \"\")" in filters
    assert "filterFromChip('path', g.save_path)" in _static("shared/tpl/xtpl-cells.html")
    assert "filterFromChip('path', m.save_path)" in _static("shared/tpl/xtpl-cells.html")


_NODE_FILTER_PROBE = r"""
const fs=require('fs'),vm=require('vm');
const sandbox={window:{},console};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);  // decorate.js
vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),sandbox);  // filters.js
const M=sandbox.window.AQB_FILTERS.methods, C=sandbox.window.AQB_FILTERS.computed;
const D=sandbox.window.AQB_DECORATE.methods;
const groups=[
  {key:'g1',save_path:'R:/a',members:[{hash:'H1',relocate:{state:'moving'}},{hash:'H2'}]},
  {key:'g2',save_path:'R:/a',members:[{hash:'H3',relocate:{state:'pending_finalize'}}]},
  {key:'g3',save_path:'R:/b',members:[{hash:'H4',relocate:{state:'moving'}}]},
  {key:'g4',save_path:'R:/a',members:[{hash:'H5',relocate:{state:'done'}}]},
];
const base={sortedGroups:groups,facetRows:groups,groups:groups,torrents:[],kindFilter:'',
  hrFilter:[],hrSrcFilter:[],relocateFilter:[],pathFilter:[],tagFilter:[],categoryFilter:[],
  siteFilter:[],searchQuery:'',searchHits:new Set(),searchPending:false,searchUncovered:[]};
const ctx=(over)=>Object.assign({},base,D,M,over);
const ids=(rows)=>rows.map(g=>g.key);
process.stdout.write(JSON.stringify({
  moving:ids(C.filteredGroups.call(ctx({relocateFilter:['迁移中']}))),
  multi:ids(C.filteredGroups.call(ctx({relocateFilter:['迁移中','待收尾']}))),
  andPath:ids(C.filteredGroups.call(ctx({relocateFilter:['迁移中'],pathFilter:['R:/a']}))),
  pathOnly:ids(C.filteredGroups.call(ctx({pathFilter:['R:/a']}))),
  cleared:ids(C.filteredGroups.call(ctx({relocateFilter:[],pathFilter:[]}))),
  options:C.relocateOptions.call(ctx({})),
  active:C.filtersActive.call(ctx({relocateFilter:['迁移中']})),
  facets:C.facetsActive.call(ctx({relocateFilter:['迁移中']})),
}));
"""


def test_p1_filter_behavior_node():
    """行为面: 迁移状态筛 = 组内或 / 跨筛与 / 路径筛保持 save_path / 清空可重置"""
    node = shutil.which("node")
    if not node:
        return
    from pathlib import Path

    shared = Path(__file__).resolve().parents[1] / "src/auto_qb/webui/static/shared"
    proc = subprocess.run(
        [node, "-e", _NODE_FILTER_PROBE,
         str(shared / "decorate.js"),
         str(shared / "filters.js")],
        capture_output=True,
        text=True
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)

    assert out["moving"] == ["g1", "g3"], "组内任一成员迁移中即保留整组(或语义)"
    assert out["multi"] == ["g1", "g2", "g3"], "同一筛选器多选 = 或; done 组不命中"
    assert out["andPath"] == ["g1"], "迁移状态与路径筛为且; 路径筛仍按 save_path"
    assert out["pathOnly"] == ["g1", "g2", "g4"], "路径筛语义不受迁移状态筛影响(用户已拍板)"
    assert out["cleared"] == ["g1", "g2", "g3", "g4"]
    assert out["options"] == [
        {
            "value": "有过迁移",
            "count": 4
        },
        {
            "value": "迁移中",
            "count": 2
        },
        {
            "value": "待收尾",
            "count": 1
        },
    ], "选项计数 = 含该状态的组数"
    assert out["active"] is True and out["facets"] is True, "迁移筛必须进入 filtersActive/facetsActive"


def test_p1_detail_section_and_endpoint_projection():
    route = _static("../server/routes/torrent_detail.py")
    assert '"relocate": relocate(hash) if relocate else None' in route
    assert 'getattr(manager, "_relocate_member", None)' in route
    rows = _static("shared/drawer_rows.js")
    assert 'title: "迁移"' in rows and "if (rel)" in rows
    assert 'label: "迁移状态"' in rows and 'label: "设置来源"' in rows
    assert 'label: "任务标识"' in rows and 'label: "收尾武装"' in rows
    assert 'label: "设置时间"' in rows, "plan P1-2 要求详情段展示设置时间"
    tpl02 = _static("shared/drawer_tpl/02-general-cards-low.js")
    tpl03 = _static("shared/drawer_tpl/03-general-dossier-collapsed.js")
    assert 'secs["迁移"]' in tpl02 and 'secs["迁移"]' in tpl03


def test_p1_detail_endpoint_passes_relocate(web_env):
    """真实端点: 有 job 透传 relocate 投影, 无 job 为 null; save_path 语义不变"""
    from auto_qb.torrents import TorrentRecord
    from auto_qb.webui.views_relocate import member_relocate

    mgr, client = web_env
    records = {
        "HA": TorrentRecord(hash="HA", name="X", save_path=r"R:\src"),
        "HB": TorrentRecord(hash="HB", name="Y", save_path=r"R:\src"),
    }
    mgr.store.get = records.get
    job = {
        "job_id": "j1",
        "phase": ru.PHASE_MOVING,
        "src": r"R:\src",
        "dst": r"R:\dst",
        "alias_paths": [],
        "created_at": 1234.5
    }
    mgr._relocate_member = lambda h: member_relocate(job, h) if h == "HA" else None
    auth = {"Authorization": f"Bearer {mgr.web.token}"}

    ha = client.get("/api/torrents/HA", headers=auth).json()["torrent"]
    assert ha["relocate"]["state"] == "moving" and ha["relocate"]["dst"] == r"R:\dst"
    assert ha["relocate"]["created_at"] == 1234.5
    assert ha["save_path"] == r"R:\src", "迁移可见性不得改写 qB save_path 语义"

    hb = client.get("/api/torrents/HB", headers=auth).json()["torrent"]
    assert hb["relocate"] is None, "无 job 时字段恒在但值为 null(详情段整段不渲染)"
