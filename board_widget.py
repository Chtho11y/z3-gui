from PySide6.QtWidgets import QWidget, QLineEdit
from PySide6.QtGui import QPainter, QPen, QFont, QColor
from PySide6.QtCore import Qt, QRect, QPoint
from modes import ViewMode, EditMode, SelectMode


class GridLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.move_callback = None
        self.focus_out_callback = None

        # 透明输入框
        self.setFrame(False)
        self.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: black;
            }
        """)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            if self.move_callback:
                direction = {
                    Qt.Key_Left: 'left',
                    Qt.Key_Right: 'right',
                    Qt.Key_Up: 'up',
                    Qt.Key_Down: 'down'
                }[event.key()]
                self.move_callback(direction)
            event.accept()
        else:
            super().keyPressEvent(event)

    def focusOutEvent(self, event):
        if self.focus_out_callback:
            self.focus_out_callback()
        super().focusOutEvent(event)


class GridBoard(QWidget):
    def __init__(self, main_win=None, n=9):
        super().__init__()
        self.n = n

        self.grid_values = [["" for _ in range(n)] for _ in range(n)]

        # 编辑模式相关
        self.editor = GridLineEdit(self)
        self.editor.setAlignment(Qt.AlignCenter)
        self.editor.setMaxLength(1)
        self.editor.hide()
        self.editor.returnPressed.connect(self.finish_edit)
        self.editor.move_callback = self.on_move_key
        self.editor.focus_out_callback = self.on_editor_focus_out

        self.edit_row = None
        self.edit_col = None

        # 选区模式相关
        self.constraints = {}   # 所有已确认区域
        self.active_constraint = None

        self.input_mode = "view"  # view, edit, select
        self.dragging = False
        self.last_drag_cell = None  # 记录上次拖动的格子
        self.mode = ViewMode(self)
        self.mode_name = 'view'

        self.main_window = main_win

    def set_size(self, n: int, preserve: bool = False) -> None:
        if not isinstance(n, int) or n <= 0:
            return
        if n == self.n:
            return

        new_grid = [["" for _ in range(n)] for _ in range(n)]
        if preserve:
            min_n = min(self.n, n)
            for r in range(min_n):
                for c in range(min_n):
                    new_grid[r][c] = self.grid_values[r][c]

        self.n = n
        self.grid_values = new_grid
        self.constraints = {}
        self.active_constraint = None
        self.edit_row = None
        self.edit_col = None
        self.editor.hide()
        self.set_mode('view')
        self.update()

    def set_mode(self, mode_name, constraint=None):
        if hasattr(self, 'mode') and self.mode:
            try:
                self.mode.exit()
            except Exception:
                pass
        self.mode_name = mode_name
        if mode_name == 'select':
            self.mode = SelectMode(self)
            self.mode.enter(constraint)
        elif mode_name == 'edit':
            self.mode = EditMode(self)
            self.mode.enter()
        else:
            self.mode = ViewMode(self)
            self.mode.enter()

    # ---------- 坐标工具 ----------
    def board_rect(self):
        side = min(self.width(), self.height())
        x = (self.width() - side) // 2
        y = (self.height() - side) // 2
        return QRect(x, y, side, side)

    def pos_to_cell(self, pos: QPoint):
        rect = self.board_rect()
        if not rect.contains(pos):
            return None
        cell = rect.width() / self.n
        col = int((pos.x() - rect.left()) / cell)
        row = int((pos.y() - rect.top()) / cell)
        return row, col

    # ---------- 区域选择 ----------
    def start_selection(self, constraint):
        self.set_mode('select', constraint)
        self.update()

    def mousePressEvent(self, event):
        if hasattr(self, 'mode') and self.mode:
            self.mode.on_mouse_press(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, 'mode') and self.mode:
            self.mode.on_mouse_move(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if hasattr(self, 'mode') and self.mode:
            self.mode.on_mouse_release(event)
        else:
            self.dragging = False
            self.last_drag_cell = None

    def keyPressEvent(self, event):
        handled = False
        if hasattr(self, 'mode') and self.mode:
            handled = self.mode.on_key_press(event)
        if not handled:
            super().keyPressEvent(event)

    # ========= 编辑模式 =========
    def commit_edit(self):
        if self.edit_row is not None:
            self.grid_values[self.edit_row][self.edit_col] = self.editor.text()

    def start_edit(self, row, col):
        self.commit_edit()  # 自动保存旧格
        self.set_mode('edit')

        rect = self.cell_rect(row, col)
        self.editor.setGeometry(rect)
        self.editor.setText(self.grid_values[row][col])
        self.editor.show()
        self.editor.setFocus()
        self.editor.selectAll()

        font = QFont("Arial", int(rect.height() * 0.6))
        self.editor.setFont(font)

        self.edit_row, self.edit_col = row, col
        self.update()

    def on_move_key(self, direction):
        self.commit_edit()

        r, c = self.edit_row, self.edit_col
        if direction == 'left': c = max(0, c - 1)
        if direction == 'right': c = min(self.n - 1, c + 1)
        if direction == 'up': r = max(0, r - 1)
        if direction == 'down': r = min(self.n - 1, r + 1)

        self.start_edit(r, c)

    def finish_edit(self):
        self.commit_edit()
        r = self.edit_row + 1
        if r < self.n:
            self.start_edit(r, self.edit_col)
        else:
            self.editor.hide()
        self.set_mode('view')
        self.update()

    def on_editor_focus_out(self):
        self.commit_edit()
        self.editor.hide()
        self.edit_row = None
        self.set_mode('view')
        self.update()

    def confirm_selection(self):
        if self.active_constraint:
            self.active_constraint = None
        self.set_mode('view')
        self.update()

    # ---------- 绘制 ----------
    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.board_rect()
        cell = rect.width() / self.n

        painter.fillRect(self.rect(), Qt.white)
        painter.fillRect(rect, Qt.white)

        # 画已有区域（选区模式）
        for id, c in self.constraints.items():
            c.draw(painter)

        # 高亮正在编辑的格子
        if self.edit_row is not None and self.input_mode == "edit":
            painter.fillRect(self.cell_rect(self.edit_row, self.edit_col), QColor(220, 220, 220))

        # 网格
        thin_pen = QPen(Qt.black, 1)
        thick_pen = QPen(Qt.black, 3)

        for i in range(self.n + 1):
            painter.setPen(thick_pen if i % 3 == 0 else thin_pen)
            painter.drawLine(rect.left(), rect.top() + i * cell, rect.right(), rect.top() + i * cell)
            painter.drawLine(rect.left() + i * cell, rect.top(), rect.left() + i * cell, rect.bottom())

        # 绘制数字
        font = QFont("Arial", int(cell / 2))
        painter.setFont(font)

        for r in range(self.n):
            for c in range(self.n):
                val = self.grid_values[r][c]
                if val:
                    painter.drawText(self.cell_rect(r, c), Qt.AlignCenter, val)

    def cell_rect(self, r, c):
        rect = self.board_rect()
        cell = rect.width() / self.n
        return QRect(rect.left() + c * cell, rect.top() + r * cell, cell, cell)

    def export_board(self):
        """导出棋盘数据和已定义的约束区域为字典，便于后续转换为 z3 表达式。

        返回结构示例：
        {
            'n': 9,
            'grid_values': [[...], ...],
            'constraints': [
                {'id': 1, 'region': [[r,c], ...], 'color': (r,g,b,a)},
                ...
            ]
        }
        """
        return {
            'n': self.n,
            'grid_values': [list(row) for row in self.grid_values],
            'constraints': [
                {
                    'id': cid,
                    'name': c.name,
                    'region': [[r, c] for (r, c) in c.region],
                    'color': (c.color.red(), c.color.green(), c.color.blue(), c.color.alpha()),
                }
                for cid, c in self.constraints.items()
            ],
        }

    def import_board(self, data: dict) -> None:
        """从导出的字典恢复棋盘状态。"""
        n = int(data.get('n', self.n))
        grid_values = data.get('grid_values')
        self.set_size(n, preserve=False)
        if isinstance(grid_values, list):
            self.grid_values = [list(row) for row in grid_values]
        self.update()

    def get_context(self):
        return self.main_window.get_context()
