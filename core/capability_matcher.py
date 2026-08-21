"""Capability Matcher Layer（V1.9 Phase 7）。

在 Capability Graph（Phase 6）与 Capability Definition（Phase 5）之上，
提供**能力兼容性推断**：给定源能力定义与目标能力定义，算出是否可连、
以及连接置信度（score），并基于一组候选目标排序给出建议。

职责边界（与已有分层解耦）：
- 只读 CapabilityDefinition 的静态元数据（value_type / category / unit ...），
  不执行转换、不持有运行时值（实时值归 RuntimeStateService）；
- 不知道事件如何广播（CapabilityRouter 不变）；
- 不修改 MappingEngine：matcher 只产出 (compatible, score)，
  由上层（auto_route / GUI）据此决定是否建 GraphEdge；
- category 亲和规则集中在本模块，便于未来扩展，不硬编码进 Router/Provider/Consumer。

设计约束：
- capability 使用字符串 id（与 CapabilityEvent / CapabilityDefinition 一致），
  不引入 enum。
- 本层是纯函数式推断，无副作用、无内部状态，天然线程安全。
"""

from typing import List, Optional, Tuple

from core.capability_definition import CapabilityDefinition

# 数值可互操作类型：int 可喂 float（数值无损），float 也可读作 int 近似。
_NUMERIC_TYPES = {"int", "float"}

# 兼容分类亲和（除"完全相同"与"motion->axis"之外的弱亲和，微调分数）。
_CATEGORY_AFFINITY = {
    ("sensor", "axis"): 0.15,
    ("motion", "sensor"): 0.15,
    ("button", "button"): 0.30,   # 完全相同已在别处加，这里留作显式兜底
}

# 判定为"可连"的最低分数阈值。
_THRESHOLD = 0.5


def _type_score(source: CapabilityDefinition, target: CapabilityDefinition) -> float:
    """取值类型兼容分：0 / 0.5 / 0.6。"""
    st, tt = source.value_type, target.value_type
    if st == tt:
        return 0.5
    if st in _NUMERIC_TYPES and tt in _NUMERIC_TYPES:
        # int <-> float 数值互操作：给足分数，使 int->float 即便无分类匹配也可连。
        return 0.6
    return 0.0


def _category_score(source: CapabilityDefinition, target: CapabilityDefinition) -> float:
    """分类亲和分：完全相同 / motion->axis 给满，其它弱亲和微调。"""
    sc, tc = source.category, target.category
    if sc == tc:
        return 0.3
    # motion 源驱动 axis 目标（陀螺仪/加速度计 -> 转向轴），语义上强亲和，提升分数。
    if sc == "motion" and tc == "axis":
        return 0.3
    return _CATEGORY_AFFINITY.get((sc, tc), 0.0)


def compatibility(
    source: CapabilityDefinition,
    target: CapabilityDefinition,
) -> Tuple[bool, float]:
    """计算源能力到目标能力的兼容性与置信度。

    返回 (compatible, score)：
      - score     : 0~1 的浮点分数（类型分 + 分类分）。
      - compatible: score >= 阈值即视为可连。

    "完全不同类型"（类型不兼容且无分类亲和）会得到 0 分 -> compatible=False。
    """
    score = _type_score(source, target) + _category_score(source, target)
    score = round(score, 3)
    return score >= _THRESHOLD, score


def suggest_targets(
    source: CapabilityDefinition,
    candidates: List[CapabilityDefinition],
) -> List[Tuple[CapabilityDefinition, float, bool]]:
    """基于分数对候选目标排序，返回 [(target_def, score, compatible), ...]。

    按 score 降序排列（同分按 id 稳定排序），最佳建议在前；
    兼容与不完全兼容的候选都返回，由调用方按需过滤（如只取 compatible=True）。
    """
    results = []
    for cand in candidates:
        compatible, score = compatibility(source, cand)
        results.append((cand, score, compatible))
    results.sort(key=lambda r: (-r[1], r[0].id))
    return results
