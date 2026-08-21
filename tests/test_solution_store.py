"""SolutionStore 测试（V1.9 Phase 10）。

覆盖：
  1. save / load roundtrip。
  2. 多个 solution 保存。
  3. JSON 数据保持：id / name / status / edges / metadata。
  （capability id 保持 string，无 enum，不复制 Graph。）
"""

import json
import os
import tempfile

from core.capability_graph import GraphEdge
from core.capability_solution import CapabilitySolution, STATUS_ACTIVE
from core.solution_store import SolutionStore


def _tmp_store():
    d = tempfile.mkdtemp(prefix="cnx_sol_")
    return SolutionStore(directory=d), d


def _make_solution(name="sol-a", status="draft"):
    sol = CapabilitySolution(name, status=status)
    sol.add_edge(GraphEdge(
        "phone.roll", "x360.left_x", gain=1.0, origin="auto", confidence=0.8,
    ))
    return sol


# 1. save / load roundtrip
def test_save_load_roundtrip():
    store, _ = _tmp_store()
    sol = _make_solution()
    sid = store.save(sol, "sol-1", metadata={"note": "auto-detected"})

    loaded = store.load(sid)
    assert loaded is not None
    sol2, meta2 = loaded
    assert sol2.name == "sol-a"
    assert sol2.status == "draft"
    edges = sol2.list_edges()
    assert len(edges) == 1
    assert edges[0].source == "phone.roll"
    assert edges[0].target == "x360.left_x"
    assert edges[0].confidence == 0.8
    assert meta2.get("note") == "auto-detected"


# 2. 多个 solution 保存
def test_multiple_solutions():
    store, _ = _tmp_store()
    store.save(_make_solution("sol-a"), "sol-1")
    store.save(_make_solution("sol-b", status="accepted"), "sol-2")

    ids = store.list_ids()
    assert ids == ["sol-1", "sol-2"]
    # 各自独立，互不覆盖
    a = store.load("sol-1")[0]
    b = store.load("sol-2")[0]
    assert a.name == "sol-a"
    assert b.name == "sol-b"
    assert b.status == "accepted"


# 3. JSON 数据保持 id / name / status / edges / metadata
def test_json_envelope_fields():
    store, d = _tmp_store()
    sol = _make_solution()
    store.save(sol, "sol-x", metadata={"source_graph": "main", "tag": "v1"})

    path = os.path.join(d, "sol-x.json")
    with open(path, "r", encoding="utf-8") as f:
        envelope = json.load(f)

    assert "id" in envelope and envelope["id"] == "sol-x"
    assert envelope["name"] == "sol-a"
    assert envelope["status"] == "draft"
    assert "edges" in envelope and isinstance(envelope["edges"], list)
    assert "metadata" in envelope
    assert envelope["metadata"].get("tag") == "v1"
    # 不复制整图：envelope 只含选中的边，没有 nodes / graph 结构
    assert "nodes" not in envelope
    assert "graph" not in envelope


# 3b. capability id 是 string，无 enum
def test_no_enum_ids():
    import enum

    store, _ = _tmp_store()
    store.save(_make_solution(), "sol-e")
    sol2 = store.load("sol-e")[0]
    for e in sol2.list_edges():
        assert isinstance(e.source, str)
        assert isinstance(e.target, str)
        assert not isinstance(e.source, enum.Enum)


# 删除后 load 返回 None
def test_delete():
    store, _ = _tmp_store()
    store.save(_make_solution(), "sol-d")
    assert store.exists("sol-d") is True
    assert store.delete("sol-d") is True
    assert store.load("sol-d") is None
    assert store.delete("sol-d") is False
