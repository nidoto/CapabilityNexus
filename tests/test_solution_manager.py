"""SolutionManager 测试（V1.9 Phase 10）。

覆盖：
  4. register / get / remove（运行时注册表增删）。
  5. 删除 active solution 时状态清理（active 指针清空）。
  额外：activate / combined_mapping_dict（聚合 active 的 mapping，不执行 MappingEngine）。
  （capability id 保持 string，无 enum，不复制 Graph，不接 GUI。）
"""

import tempfile

from core.capability_graph import GraphEdge
from core.capability_solution import CapabilitySolution, STATUS_ACTIVE
from core.solution_manager import SolutionManager
from core.solution_store import SolutionStore


def _tmp_manager():
    d = tempfile.mkdtemp(prefix="cnx_mgr_")
    return SolutionManager(store=SolutionStore(directory=d))


def _edge(src, tgt, **kw):
    return GraphEdge(src, tgt, **kw)


# 4. register / get / remove
def test_register_get_remove():
    mgr = _tmp_manager()
    sol = CapabilitySolution("sol-a")
    sol.add_edge(_edge("phone.roll", "x360.left_x"))
    sid = mgr.register(sol, "sol-1", metadata={"note": "x"})

    assert mgr.get(sid) is not None
    assert mgr.get(sid).name == "sol-a"
    assert sid in mgr.list_ids()
    # 已落盘
    assert mgr._store.exists(sid)

    assert mgr.remove(sid) is True
    assert mgr.get(sid) is None
    assert sid not in mgr.list_ids()
    assert mgr._store.exists(sid) is False
    # 重复 remove 返回 False
    assert mgr.remove(sid) is False


# 5. 删除 active solution 时状态清理
def test_remove_active_clears_pointer():
    mgr = _tmp_manager()
    sol = CapabilitySolution("sol-active")
    sol.add_edge(_edge("phone.roll", "x360.left_x"))
    sid = mgr.register(sol, "sol-active")

    mgr.activate(sid)
    assert mgr.active_id() == "sol-active"
    assert mgr.active_solution() is not None

    # 删除 active：指针应被清理
    mgr.remove(sid)
    assert mgr.active_id() is None
    assert mgr.active_solution() is None


# activate 设置 active 指针并标记 active 状态
def test_activate_marks_active():
    mgr = _tmp_manager()
    sol = CapabilitySolution("sol-b")
    sol.add_edge(_edge("phone.roll", "x360.right_x"))
    sid = mgr.register(sol, "sol-b")

    mgr.activate(sid)
    assert mgr.active_id() == "sol-b"
    assert mgr.get(sid).status == STATUS_ACTIVE


# combined_mapping_dict 聚合 active solution，格式与 MappingEngine 兼容
def test_combined_mapping_dict():
    mgr = _tmp_manager()
    sol = CapabilitySolution("sol-c")
    sol.add_edge(_edge("phone.roll", "x360.left_x", gain=0.5))
    sid = mgr.register(sol, "sol-c")

    # 未激活时为空
    assert mgr.combined_mapping_dict() == {}

    mgr.activate(sid)
    mapping = mgr.combined_mapping_dict()
    assert "phone.roll" in mapping
    item = mapping["phone.roll"][0]
    assert item["target"] == "x360.left_x"
    assert item["gain"] == 0.5
    assert set(item.keys()) == {"target", "gain", "return_to_center"}


# create 便捷路径：生成 id 并落盘
def test_create_generates_id():
    mgr = _tmp_manager()
    sid = mgr.create("sol-d", edges=[_edge("phone.gas", "x360.right_trigger")])
    assert sid.startswith("sol-")
    assert mgr.get(sid) is not None
    assert mgr._store.exists(sid)


# 多个 solution + 冷加载恢复
def test_load_from_store_restores():
    mgr = _tmp_manager()
    mgr.create("sol-a", edges=[_edge("phone.roll", "x360.left_x")], solution_id="a")
    mgr.create("sol-b", edges=[_edge("phone.roll", "x360.right_x")], solution_id="b")

    mgr2 = _tmp_manager()
    # 复用同一目录
    mgr2._store = mgr._store
    n = mgr2.load_from_store()
    assert n == 2
    assert set(mgr2.list_ids()) == {"a", "b"}


# capability id 仍是 string，无 enum
def test_no_enum_ids():
    import enum

    mgr = _tmp_manager()
    sid = mgr.create("sol-e", edges=[_edge("trainer.power", "x360.vibration")])
    for e in mgr.get(sid).list_edges():
        assert isinstance(e.source, str)
        assert isinstance(e.target, str)
        assert not isinstance(e.source, enum.Enum)
