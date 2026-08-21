"""SolutionPackage / SolutionSerializer 测试（V1.9 Phase 15）。

覆盖：
  1. CapabilitySolution -> SolutionPackage 转换正常（包装而非复制）。
  2. to_dict / from_dict 数据一致。
  3. save / load 文件恢复正常。
  4. solution edge 保留（phone.roll -> x360.left_x 不丢失）。
  5. capability id 保持 string，无 enum。
  6. 不影响已有测试（本文件独立，不修改旧模块）。
"""

import enum
import json
import os
import tempfile

from core.capability_graph import GraphEdge
from core.capability_solution import CapabilitySolution
from core.solution_package import SolutionPackage
from core.solution_serializer import SolutionSerializer


def _make_solution():
    sol = CapabilitySolution("Racing Solution", status="accepted")
    sol.add_edge(GraphEdge(
        "phone.roll", "x360.left_x", gain=0.5,
        origin="auto", confidence=0.9,
    ))
    return sol


# 1. CapabilitySolution -> SolutionPackage（包装而非复制）
def test_solution_to_package_wraps():
    sol = _make_solution()
    pkg = SolutionPackage(sol, id="racing", name="Racing Solution", description="d", metadata={"version": 1})
    # 包装：持有同一 solution 实例，而非复制逻辑
    assert pkg.solution is sol
    assert pkg.id == "racing"
    assert pkg.name == "Racing Solution"
    assert pkg.description == "d"
    assert pkg.metadata == {"version": 1}


# 2. to_dict / from_dict 一致
def test_to_from_dict_roundtrip():
    sol = _make_solution()
    pkg = SolutionPackage(sol, id="racing", name="Racing Solution", description="desc", metadata={"version": 1})
    d = pkg.to_dict()
    assert d["id"] == "racing"
    assert d["name"] == "Racing Solution"
    assert d["description"] == "desc"
    assert d["metadata"] == {"version": 1}
    assert "solution" in d

    pkg2 = SolutionPackage.from_dict(d)
    assert pkg2.id == "racing"
    assert pkg2.name == "Racing Solution"
    assert pkg2.description == "desc"
    assert pkg2.metadata == {"version": 1}
    # 内部 solution 重建且边保留
    assert len(pkg2.solution.list_edges()) == 1
    assert pkg2.solution.list_edges()[0].source == "phone.roll"


# 3. save / load 文件恢复正常
def test_save_load_file():
    sol = _make_solution()
    pkg = SolutionPackage(sol, id="racing", name="Racing Solution", description="d", metadata={"version": 1})

    d = tempfile.mkdtemp(prefix="cnx_pkg_")
    path = os.path.join(d, "racing.solution")
    SolutionSerializer().save(pkg, path)
    assert os.path.exists(path)

    loaded = SolutionSerializer().load(path)
    assert isinstance(loaded, SolutionPackage)
    assert loaded.id == "racing"
    assert loaded.name == "Racing Solution"
    # 便捷方法 pkg.save / SolutionPackage.load 同样可用
    path2 = os.path.join(d, "racing2.solution")
    pkg.save(path2)
    loaded2 = SolutionPackage.load(path2)
    assert loaded2.id == "racing"


# 4. solution edge 保留（phone.roll -> x360.left_x 不丢失）
def test_edge_preserved():
    sol = _make_solution()
    pkg = SolutionPackage(sol, id="racing")
    pkg2 = SolutionPackage.from_dict(pkg.to_dict())

    edges = pkg2.solution.list_edges()
    assert len(edges) == 1
    e = edges[0]
    assert e.source == "phone.roll"
    assert e.target == "x360.left_x"
    assert e.gain == 0.5
    # auto/manual 元数据保留
    assert e.origin == "auto"
    assert e.confidence == 0.9


# 5. capability id 保持 string，无 enum
def test_capability_ids_are_strings():
    sol = _make_solution()
    pkg = SolutionPackage(sol, id="racing")
    pkg2 = SolutionPackage.from_dict(pkg.to_dict())

    for e in pkg2.solution.list_edges():
        assert isinstance(e.source, str)
        assert isinstance(e.target, str)
        assert not isinstance(e.source, enum.Enum)
    # 包 id 也是字符串
    assert isinstance(pkg2.id, str)


# 6. 结构形如规范（id/name/description/metadata/solution）
def test_dict_shape_matches_spec():
    sol = _make_solution()
    pkg = SolutionPackage(sol, id="racing", name="Racing Solution", description="d", metadata={"version": 1})
    d = pkg.to_dict()
    assert set(d.keys()) == {"id", "name", "description", "metadata", "solution"}
    # 内部 solution 字段至少含 name/status/edges
    assert "edges" in d["solution"]
    assert "status" in d["solution"]
