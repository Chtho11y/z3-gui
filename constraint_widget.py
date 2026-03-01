from PySide6.QtWidgets import QWidget, QLineEdit
from PySide6.QtGui import QPainter, QPen, QFont, QColor
from PySide6.QtCore import Qt, QRect, QPoint


class RegionConstraintWidget(QWidget):
    def __init__(self, id, color, board):
        super().__init__()

        self.region = []
        self.id = id
        self.color = color
        self.board = board

    def commit_selection(self, cell):
        if cell not in self.region:
            self.region.append(cell)
        else:
            self.region.remove(cell)

    def draw(self, painter):
        """在给定的 painter 上绘制约束区域"""
        painter.setBrush(QColor(self.color.red(), self.color.green(), self.color.blue(), 100))
        painter.setPen(Qt.NoPen)

        for r, c in self.region:
            painter.drawRect(self.board.cell_rect(r, c))
        
        # 如果该约束正在被选中（board.active_constraint 指向它），
        # 则在区域内每个格子的左上角显示编号；否则在第一个格子左上角显示 id
        if self.region:
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            painter.setPen(Qt.black)

            if self.board.active_constraint is self:
                # 对区域内每个格子按当前顺序编号显示
                for idx, (r, c) in enumerate(self.region, start=1):
                    rect = self.board.cell_rect(r, c)
                    painter.drawText(rect.adjusted(2, 2, -2, -2), Qt.AlignTop | Qt.AlignLeft, str(idx))
            else:
                # 原有行为：在区域最上左的格子显示 id
                min_r = min(r for r, c in self.region)
                min_c = min(c for r, c in self.region if r == min_r)
                rect = self.board.cell_rect(min_r, min_c)
                painter.drawText(rect.adjusted(2, 2, -2, -2), Qt.AlignTop | Qt.AlignLeft, str(self.id))