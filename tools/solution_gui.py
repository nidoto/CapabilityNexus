"""Solution GUI Panel（V1.9 Phase 13）。

基于现有 GUI 技术栈（tkinter/ttk）的 Solution 用户确认面板。
**本文件为新增文件，不修改既有 cnx_gui.py / app.py**；未来由 GUI 宿主在
_build_layout 中实例化并嵌入（本次 Phase 13 不接线，以遵守"禁止修改旧文件"）。

职责（仅用户确认层，不侵入核心能力链）：
  1. 展示 AutoRouter 发现结果（Source ↓ Target / score），可勾选；
  2. 勾选 -> controller.toggle -> workflow.select/deselect（GUI 不自己维护 Graph）；
  3. "Create Solution" -> workflow.create_draft(name)，Manager 中出现 draft；
  4. "Confirm" -> workflow.confirm(id)，draft -> accepted；
  5. "Activate" -> workflow.activate(id)，经 SolutionRuntime 接通 MappingEngine
     （GUI 不直接调用 MappingEngine）。

数据全部来自 SolutionController（core/solution_ui_model），GUI 不直接访问
Graph 内部或 MappingEngine 内部。
"""

import tkinter as tk
from tkinter import ttk


class SolutionPanel:
    """Solution 用户确认面板（tkinter/ttk）。"""

    def __init__(
        self,
        parent,
        controller,
        source_provider=None,
        target_provider=None,
    ):
        """
        :param parent: 父容器（ttk.Frame 等）
        :param controller: SolutionController 实例（驱动 workflow）
        :param source_provider: 0参 callable，返回源 CapabilityDefinition 列表
        :param target_provider: 0参 callable，返回目标 CapabilityDefinition 列表
        """
        self.controller = controller
        self._source_provider = source_provider
        self._target_provider = target_provider
        self._check_vars = {}  # (source, target) -> BooleanVar

        self._build(parent)

    # ------------------------------------------------------------------
    def _build(self, parent):
        box = ttk.LabelFrame(parent, text="Solution Builder")
        box.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 顶部操作按钮
        bar = ttk.Frame(box)
        bar.pack(fill=tk.X, padx=6, pady=(4, 2))
        ttk.Button(bar, text="Discover", command=self._on_discover).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Create Solution", command=self._on_create).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Confirm", command=self._on_confirm).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Activate", command=self._on_activate).pack(side=tk.LEFT, padx=2)

        # 发现结果列表（可勾选）
        cand_frame = ttk.LabelFrame(box, text="Discovered Connections")
        cand_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self.cand_tree = ttk.Treeview(
            cand_frame, columns=("target", "score"), show="tree headings", height=8
        )
        self.cand_tree.heading("#0", text="source")
        self.cand_tree.heading("target", text="target")
        self.cand_tree.heading("score", text="score")
        self.cand_tree.column("#0", width=140)
        self.cand_tree.column("target", width=140)
        self.cand_tree.column("score", width=80)
        self.cand_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.cand_tree.bind("<Double-1>", self._on_toggle)

        # 已建 Solution 状态
        status_frame = ttk.LabelFrame(box, text="Solutions")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self.status_tree = ttk.Treeview(
            status_frame, columns=("status", "edges"), show="tree headings", height=6
        )
        self.status_tree.heading("#0", text="name")
        self.status_tree.heading("status", text="status")
        self.status_tree.heading("edges", text="edges")
        self.status_tree.column("#0", width=160)
        self.status_tree.column("status", width=100)
        self.status_tree.column("edges", width=80)
        self.status_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.refresh()

    # ------------------------------------------------------------------
    # 交互
    # ------------------------------------------------------------------
    def _on_discover(self):
        sources = self._source_provider() if self._source_provider else []
        targets = self._target_provider() if self._target_provider else []
        self.controller.run_discovery(sources, targets)
        self.refresh()

    def _on_toggle(self, event):
        item = self.cand_tree.identify_row(event.y)
        if not item:
            return
        values = self.cand_tree.item(item, "values")
        source = self.cand_tree.item(item, "text")
        target = values[0] if values else ""
        # 切换勾选：调用 controller -> workflow.select/deselect
        self.controller.toggle(source, target)
        self.refresh()

    def _on_create(self):
        self.controller.create_draft("Solution")
        self.refresh()

    def _on_confirm(self):
        sid = self._selected_status_id()
        if sid:
            self.controller.confirm(sid)
            self.refresh()

    def _on_activate(self):
        sid = self._selected_status_id()
        if sid:
            self.controller.activate(sid)
            self.refresh()

    def _selected_status_id(self):
        sel = self.status_tree.selection()
        if not sel:
            return None
        item = sel[0]
        return self.status_tree.item(item, "text")  # 我们存 id 于 text

    # ------------------------------------------------------------------
    # 刷新（从 controller 读取 View，不直接访问 Graph/MappingEngine）
    # ------------------------------------------------------------------
    def refresh(self):
        # 候选列表
        self.cand_tree.delete(*self.cand_tree.get_children())
        self._check_vars.clear()
        for c in self.controller.candidates():
            self.cand_tree.insert(
                "", "end", text=c.source, values=(c.target, f"{c.score:.2f}"),
            )

        # 状态列表
        self.status_tree.delete(*self.status_tree.get_children())
        for s in self.controller.statuses():
            self.status_tree.insert(
                "", "end", text=s.id, values=(s.status, len(s.edges)),
            )
