from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabBar, QLabel, QComboBox,
    QStackedWidget, QSplitter, QPushButton, QDialog, QTextEdit, QHBoxLayout
)
from PySide6.QtCore import Qt
from typing import Dict
from board_widget import GridBoard
from constraint_list_widget import ConstraintListWidget
from context import GlobalContext


class BrowserTabBar(QTabBar):
    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        size.setHeight(28)
        size.setWidth(size.width() + 20)
        return size

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Z3 Visual Solver")
        self.resize(1300, 850)

        self._variable_pages = []
        self._next_var_id = 1
        self._board_size = 9

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # ===== Tabs =====
        # TabBar 和测试导出按钮行
        top_row = QHBoxLayout()
        self.tabbar = BrowserTabBar()
        self.tabbar.setTabsClosable(True)
        self.tabbar.tabCloseRequested.connect(self._on_tab_close)
        self.tabbar.currentChanged.connect(self._on_tab_changed)
        top_row.addWidget(self.tabbar)

        self.export_btn = QPushButton("测试导出")
        self.export_btn.clicked.connect(self._on_export_clicked)
        top_row.addWidget(self.export_btn)

        main_layout.addLayout(top_row)

        self.pages = QStackedWidget()
        main_layout.addWidget(self.pages, 1)

        # ===== 页面 =====
        self._create_base_tab()
        self._add_variable_tab("数字", select=False)
        self._add_variable_tab("颜色", select=False)
        self._ensure_plus_tab()
        self.tabbar.setCurrentIndex(1)
        self.pages.setCurrentIndex(1)

    def _plus_index(self) -> int:
        if self.tabbar.count() == 0:
            return -1
        last_index = self.tabbar.count() - 1
        if self.tabbar.tabText(last_index) == "+":
            return last_index
        return -1

    def _ensure_plus_tab(self) -> None:
        if self._plus_index() == -1:
            self.tabbar.addTab("+")
        plus_index = self._plus_index()
        if plus_index >= 0:
            self.tabbar.setTabButton(plus_index, QTabBar.RightSide, None)
            self.tabbar.setTabButton(plus_index, QTabBar.LeftSide, None)
        self.tabbar.setTabButton(0, QTabBar.RightSide, None)
        self.tabbar.setTabButton(0, QTabBar.LeftSide, None)

    def _create_base_tab(self) -> None:
        self.tabbar.addTab("基础信息")
        base_page = QWidget()
        base_layout = QVBoxLayout(base_page)
        base_layout.setContentsMargins(12, 12, 12, 12)

        row = QHBoxLayout()
        row.addWidget(QLabel("Board 大小"))
        self.size_combo = QComboBox()
        self.size_combo.addItems(["4", "6", "9", "12", "16"])
        self.size_combo.setCurrentText(str(self._board_size))
        self.size_combo.currentTextChanged.connect(self._on_board_size_changed)
        row.addWidget(self.size_combo)
        row.addStretch(1)

        base_layout.addLayout(row)
        base_layout.addStretch(1)
        self.pages.addWidget(base_page)

    def _add_variable_tab(self, name: str, select: bool = True) -> None:
        var_id = self._next_var_id
        self._next_var_id += 1

        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Horizontal)
        board = GridBoard(self, self._board_size)
        constraint_list = ConstraintListWidget(board, variable_name=name, variable_id=var_id)
        splitter.addWidget(board)
        splitter.addWidget(constraint_list)
        splitter.setSizes([800, 300])
        page_layout.addWidget(splitter)

        payload = {
            "page": page,
            "board": board,
            "constraint_list": constraint_list,
            "id": var_id,
            "name": name,
        }
        insert_index = self._plus_index()
        if insert_index == -1:
            insert_index = self.tabbar.count()

        self.tabbar.insertTab(insert_index, name)
        self.pages.insertWidget(insert_index, payload["page"])
        self._variable_pages.insert(insert_index, payload)
        self._ensure_plus_tab()
        if select:
            self.tabbar.setCurrentIndex(insert_index)

    def _on_tab_changed(self, index: int) -> None:
        plus_index = self._plus_index()
        if index == plus_index:
            name = f"变量{self._next_var_id}"
            self._add_variable_tab(name, select=True)
            return
        if 0 <= index < self.pages.count():
            self.pages.setCurrentIndex(index)

    def _on_tab_close(self, index: int) -> None:
        plus_index = self._plus_index()
        if index == plus_index or index == 0:
            return
        if len(self._variable_pages) <= 1:
            return
        var_idx = index - 1
        page = self._variable_pages.pop(var_idx)
        self.pages.removeWidget(page["page"])
        self.tabbar.removeTab(index)
        self._ensure_plus_tab()
        if self.tabbar.currentIndex() == -1 and self._variable_pages:
            self.tabbar.setCurrentIndex(1)
        if 0 <= self.tabbar.currentIndex() < self.pages.count():
            self.pages.setCurrentIndex(self.tabbar.currentIndex())

    def _on_board_size_changed(self, text: str) -> None:
        try:
            n = int(text)
        except ValueError:
            return
        self._board_size = n
        for payload in self._variable_pages:
            payload["board"].set_size(n, preserve=False)
            payload["constraint_list"].reset_constraints(payload["name"], payload["id"])

    def get_context(self):
        """获取 context 对象，包含当前所有变量和约束的信息，供表达式编辑器使用。"""

        context = GlobalContext(self._board_size)
        
        for payload in self._variable_pages:
            var_id = payload["id"]
            name = payload["name"]
            board_state = payload["board"].grid_values
            constraints = payload["constraint_list"].export_constraints()
            
            context.add_variable(var_id, name, board_state, constraints)

        return context

    def _on_export_clicked(self):

        from z3_ast import compile_single_constraint

        state = self.get_context()

        print(state.to_dict())

        compile_res = {}
        for var_id, var_info in state.vars.items():
            var_name = var_info["name"]
            for c in var_info["constraints"]:
                c_name = c["name"]
                c_str = c["expr"]
                try:
                    compile_res[c_name] = compile_single_constraint(c_str, c["id"], var_id, c["region"], state)
                except Exception as e:
                    compile_res[c_name] = f"编译失败: {str(e)}"
        

        dialog = QDialog(self)
        dialog.setWindowTitle("导出状态")
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        text_edit.setText(str(state.to_dict())+ "\n\n编译结果：\n" + str(compile_res))


        layout.addWidget(text_edit)
        dialog.resize(600, 400)
        dialog.exec()
