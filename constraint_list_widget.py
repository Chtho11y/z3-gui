from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QListWidget, QListWidgetItem, QPushButton, QColorDialog,
    QDialog, QPlainTextEdit, QTextEdit
)
from PySide6.QtCore import Qt, QSize, QRect, QRegularExpression
from PySide6.QtGui import QColor, QFont, QPainter, QTextFormat, QSyntaxHighlighter, QTextCharFormat, QKeyEvent
from constraint_widget import RegionConstraintWidget
import random


class _LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self._editor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont('Consolas' if 'Consolas' in QFont().families() else 'Courier New', 10))
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)
        self.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                selection-background-color: #264f78;
                selection-color: #ffffff;
            }
            """
        )
        self._lineNumberArea = _LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Tab and not (event.modifiers() & Qt.ShiftModifier):
            self.insertPlainText(' ' * 4)
            return
        super().keyPressEvent(event)

    def lineNumberAreaWidth(self):
        digits = max(1, len(str(max(1, self.blockCount()))))
        space = 8 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self._lineNumberArea.scroll(0, dy)
        else:
            self._lineNumberArea.update(0, rect.y(), self._lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self._lineNumberArea)
        painter.fillRect(event.rect(), QColor(42, 42, 42))

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        fm = self.fontMetrics()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor(133, 133, 133))
                painter.drawText(0, top, self._lineNumberArea.width() - 4, fm.height(), Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(43, 43, 43)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)


class SimpleHighlighter(QSyntaxHighlighter):
    def __init__(self, parent, context=None):
        super().__init__(parent.document())
        self.rules = []
        ctx = context or {}
        funcs = ctx.get('functions', [])
        vars_ = ctx.get('variables', [])
        keys = ctx.get('keywords', [])

        fmt_func = QTextCharFormat()
        fmt_func.setForeground(QColor(106, 153, 85))
        fmt_func.setFontItalic(True)

        fmt_var = QTextCharFormat()
        fmt_var.setForeground(QColor(0x9c, 0xdc, 0xfe))

        fmt_key = QTextCharFormat()
        fmt_key.setForeground(QColor(86, 156, 214))
        fmt_key.setFontWeight(QFont.Bold)

        fmt_rule = QTextCharFormat()
        fmt_rule.setForeground(QColor(255, 215, 0))
        pattern = QRegularExpression(r"@\w+")
        self.rules.append((pattern, fmt_rule))

        fmt_number = QTextCharFormat()
        fmt_number.setForeground(QColor(181, 206, 168))
        pattern = QRegularExpression(r"[^\w]\d+")
        self.rules.append((pattern, fmt_number))

        for w in funcs:
            if not w:
                continue
            pattern = QRegularExpression(r"\b" + QRegularExpression.escape(w) + r"\b")
            self.rules.append((pattern, fmt_func))

        for w in vars_:
            if not w:
                continue
            pattern = QRegularExpression(r"\b" + QRegularExpression.escape(w) + r"\b")
            self.rules.append((pattern, fmt_var))

        for w in keys:
            if not w:
                continue
            pattern = QRegularExpression(r"\b" + QRegularExpression.escape(w) + r"\b")
            self.rules.append((pattern, fmt_key))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                start = m.capturedStart()
                length = m.capturedLength()
                self.setFormat(start, length, fmt)


class ExprDialog(QDialog):
    def __init__(self, parent=None, text='', context=None):
        super().__init__(parent)
        self.setWindowTitle('编辑表达式')
        self.resize(600, 360)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #252526;
                color: #d4d4d4;
            }
            QPushButton {
                background-color: #3a3d41;
                color: #d4d4d4;
                border: 1px solid #4a4d52;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #45494e;
            }
            QPushButton:pressed {
                background-color: #2f3237;
            }
            """
        )
        self.editor = CodeEditor(self)
        self.editor.setPlainText(text or '')
        self.highlighter = SimpleHighlighter(self.editor, context or {})

        btn_ok = QPushButton('确定')
        btn_cancel = QPushButton('取消')
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)

        layout = QVBoxLayout(self)
        layout.addWidget(self.editor)
        layout.addLayout(btn_row)



class ConstraintEditor(QWidget):
    def __init__(
        self,
        board,
        cid,
        list_widget=None,
        is_default=False,
    ):
        super().__init__()
        self.board = board
        self.cid = cid
        self.list_widget = list_widget
        self.is_default = is_default
        
        # 默认限制使用黑色，其他使用随机颜色
        if is_default:
            self.color = QColor(0, 0, 0)
        else:
            self.color = QColor.fromHsv(random.randint(0, 359), 160, 255)
    
        self.mode = "editing"
        self.data = {"condition": "", "expr": ""}

        self.constraint_widget = RegionConstraintWidget(
            id=self.cid,
            color=self.color,
            board=self.board,
        )
        if self.list_widget and not self.is_default:
            try:
                self.list_widget.register_constraint_widget(self.constraint_widget)
            except Exception:
                pass

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(6, 4, 6, 4)
        self.main_layout.setSpacing(2)

        self.build_edit_ui()
        self.build_display_ui()

        self.show_edit_mode()
        self.start_region_selection()

    def build_edit_ui(self):
        self.edit_widget = QWidget()
        # 使用垂直布局，使表达式输入框另起一行
        layout = QVBoxLayout(self.edit_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 第一行：名称（或变量名）、类型下拉、颜色按钮
        top_row = QHBoxLayout()

        # 名称编辑（默认限制为变量名）
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("变量名" if self.is_default else "名称")
        self.name_edit.setFixedWidth(140)
        top_row.addWidget(self.name_edit)

        # 颜色选择按钮（默认限制不显示）
        if not self.is_default:
            self.color_btn = QPushButton()
            self.color_btn.setFixedSize(24, 24)
            self.update_color_button()
            self.color_btn.clicked.connect(self.choose_color)
            top_row.addWidget(self.color_btn)

        self.combo = QComboBox()
        if self.is_default:
            self.combo.addItems(["数字范围"])
            self.combo.setEnabled(False)  # 默认限制不可修改类型
        else:
            self.combo.addItems(["总计", "每项", "每行", "每列", "每宫", "相邻项"])

        top_row.addWidget(self.combo)

        layout.addLayout(top_row)

        # 第二行：表达式预览（文本）放在按钮上方
        self.expr_preview_label = QLabel("")
        self.expr_preview_label.setStyleSheet("color: #333;")
        self.expr_preview_label.setWordWrap(True)
        f = QFont('Consolas' if 'Consolas' in QFont().families() else 'Courier New', 10)
        self.expr_preview_label.setFont(f)
        # 允许鼠标选中文本以便复制
        self.expr_preview_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.expr_preview_label)

        # 表达式编辑按钮与 确认/删除 放在同一行
        bottom_row = QHBoxLayout()

        # 表达式编辑按钮
        self.expr_btn = QPushButton("编辑表达式...")
        self.expr_btn.clicked.connect(self.open_expr_editor)
        bottom_row.addWidget(self.expr_btn)

        bottom_row.addStretch(1)
        self.confirm_btn = QPushButton("确认")
        self.confirm_btn.clicked.connect(self.finish_edit)
        bottom_row.addWidget(self.confirm_btn)

        self.delete_btn = QPushButton("删除")
        # 默认限制不可删除
        if self.is_default:
            self.delete_btn.setEnabled(False)
            self.delete_btn.setVisible(False)
        else:
            self.delete_btn.clicked.connect(self.delete_self)
        bottom_row.addWidget(self.delete_btn)

        layout.addLayout(bottom_row)

        self.main_layout.addWidget(self.edit_widget)

    def build_display_ui(self):
        self.display_widget = QWidget()
        layout = QVBoxLayout(self.display_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.title = QLabel()
        self.content = QLabel()
        self.content.setWordWrap(True)

        layout.addWidget(self.title)
        layout.addWidget(self.content)

        self.main_layout.addWidget(self.display_widget)

    def choose_color(self):
        """打开颜色选择对话框"""
        color = QColorDialog.getColor(self.color, self, "选择约束颜色")
        if color.isValid():
            self.color = color
            self.constraint_widget.color = color
            self.update_color_button()
            self.board.update()
    
    def update_color_button(self):
        """更新颜色按钮的背景色"""
        if not self.is_default:
            self.color_btn.setStyleSheet(
                f"background-color: rgb({self.color.red()}, {self.color.green()}, {self.color.blue()}); "
                f"border: 1px solid #888;"
            )

    def show_edit_mode(self):
        # 通知列表开始编辑（会自动结束其他正在编辑的项）
        if self.list_widget:
            self.list_widget.start_editing(self)
        
        self.mode = "editing"
        self.display_widget.hide()
        self.edit_widget.show()
        # focus 到表达式按钮，按下打开编辑器
        try:
            self.expr_btn.setFocus()
        except Exception:
            pass

        # 默认限制不触发区域选择
        if not self.is_default and self._is_active_list():
            self.start_region_selection()

        # 将已有名称显示到编辑框
        if self.data.get('name'):
            self.name_edit.setText(self.data.get('name'))
        # 将已有表达式显示为上方文本预览（编辑模式下可见）
        if self.data.get('expr'):
            preview = self._expr_preview(self.data.get('expr'))
            try:
                self.expr_preview_label.setText(preview)
                self.expr_preview_label.setToolTip(self.data.get('expr'))
            except Exception:
                pass
        
        self.update_item_size()

    def show_display_mode(self):
        # 保存编辑的数据
        self.data["condition"] = self.combo.currentText()
        # expr 存储在 self.data['expr']（由表达式编辑器更新）
        self.data["name"] = self.name_edit.text()
        
        self.mode = "display"
        self.edit_widget.hide()
        self.display_widget.show()

        text = f"{self.data['condition']} : {self.data.get('expr','')}"
        title_name = f" {self.data['name']}" if self.data.get('name') else ''
        self.title.setText(f"● #{self.cid}{title_name}")
        self.title.setStyleSheet(
            f"color: rgb({self.color.red()}, {self.color.green()}, {self.color.blue()}); font-weight: bold;"
        )
        # 使用等宽字体展示表达式内容
        mfont = QFont('Consolas' if 'Consolas' in QFont().families() else 'Courier New', 10)
        self.content.setFont(mfont)
        self.title.setFont(mfont)
        self.content.setText(text)

    def finish_edit(self):
        self.board.confirm_selection()
        self.show_display_mode()
        self.update_item_size()
    
    def update_item_size(self):
        if not self.list_widget:
            return

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if self.list_widget.itemWidget(item) is self:
                item.setSizeHint(self.sizeHint())
                break

    def delete_self(self):
        # 从列表中移除自身的项，并从 board.constraints 中删除关联的区域
        if self.list_widget.current_editing_editor is self:
            self.list_widget.current_editing_editor = None
        if self.list_widget:
            lw = self.list_widget
            for i in range(lw.count()):
                it = lw.item(i)
                if lw.itemWidget(it) is self:
                    lw.takeItem(i)
                    break

        # 从 board 中移除已登记的约束
        try:
            if self.cid in self.board.constraints:
                del self.board.constraints[self.cid]
                self.board.update()
        except Exception:
            pass
        if self.list_widget and not self.is_default:
            try:
                self.list_widget.unregister_constraint_widget(self.cid)
            except Exception:
                pass


    def mouseDoubleClickEvent(self, event):
        if self.mode == "display":
            self.combo.setCurrentText(self.data["condition"])
            # 恢复名称到编辑框并进入编辑模式
            self.name_edit.setText(self.data.get('name', ''))
            self.show_edit_mode()
            # 默认限制不触发区域选择
            if not self.is_default:
                self.board.start_selection(self.constraint_widget)

    def start_region_selection(self):
        if not self.is_default:
            self.board.start_selection(self.constraint_widget)

    def _is_active_list(self) -> bool:
        if not self.list_widget:
            return True
        return getattr(self.list_widget, "is_active", True)

    def open_expr_editor(self):
        # 尝试从 board 获取 context（包含 functions, variables, keywords）
        context = self.board.get_context().to_editor_context() if hasattr(self.board, 'get_context') else {}

        current = self.data.get('expr', '')
        dlg = ExprDialog(self, current, context)
        if dlg.exec():
            try:
                self.data['expr'] = dlg.editor.toPlainText()
            except Exception:
                self.data['expr'] = dlg.editor.toPlainText()
            # 更新上方文本预览与提示，使编辑模式下也能看到表达式内容预览
            preview = self._expr_preview(self.data.get('expr', ''))
            try:
                self.expr_preview_label.setText(preview)
                self.expr_preview_label.setToolTip(self.data.get('expr', ''))
            except Exception:
                pass
            self.update_item_size()

    def _expr_preview(self, expr, maxlen=48):
        if not expr:
            return "编辑表达式..."
        lines = expr.splitlines()
        max_lines = 3
        selected = lines[:max_lines]
        trimmed = []
        for ln in selected:
            if len(ln) > maxlen:
                trimmed.append(ln[:maxlen-3] + '...')
            else:
                trimmed.append(ln)
        return '\n'.join(trimmed)

    def sizeHint(self):
        # 返回足够的大小以容纳两行
        # 根据 expr 的实际行数动态调整高度，避免固定过宽或过高
        expr_text = self.data.get('expr', '')

        lines = expr_text.count('\n') + 1 if expr_text else 1
        fm = self.fontMetrics()
        line_height = fm.lineSpacing()

        max_visible_lines = 6
        visible_lines = min(lines, max_visible_lines)
        expr_height = visible_lines * line_height + 12

        top_row_height = max(28, self.name_edit.sizeHint().height() if hasattr(self, 'name_edit') else 28)
        # 在显示模式下不需要为按钮行保留高度
        button_row_height = 0 if getattr(self, 'mode', 'display') == 'display' else 34

        total_height = top_row_height + expr_height + button_row_height + 12
        print("Size hint calculated:", total_height)

        # 宽度设置为合理的值，避免过宽；主要高度随行数变化
        width = 300
        return QSize(width, total_height)


class ConstraintListWidget(QListWidget):
    def __init__(
        self,
        board,
        variable_name: str = "",
        variable_id: int = 0,
    ):
        super().__init__()
        self.board = board
        self.variable_name = variable_name
        self.variable_id = variable_id
        self.is_active = True
        self.default_editor = None
        self.current_editing_editor = None  # 跟踪当前正在编辑的编辑器
        self._constraints = {}
		
        # 添加默认的数字范围限制
        self.add_default_constraint()
		
        self.add_constraint_item()
        self.itemClicked.connect(self.on_item_clicked)
    
    def add_default_constraint(self):
        """添加默认的数字范围限制"""
        item = QListWidgetItem()
        default_editor = ConstraintEditor(
            self.board,
            0,
            self,
            is_default=True,
        )
        if self.variable_name:
            try:
                default_editor.name_edit.setText(self.variable_name)
                default_editor.data["name"] = self.variable_name
            except Exception:
                pass
        item.setSizeHint(default_editor.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, default_editor)
        self.default_editor = default_editor

    def set_variable_meta(self, variable_name: str, variable_id: int) -> None:
        self.variable_name = variable_name
        self.variable_id = variable_id
        if self.default_editor:
            self.default_editor.cid = variable_id
            try:
                self.default_editor.name_edit.setText(variable_name)
                self.default_editor.data["name"] = variable_name
            except Exception:
                pass
            self.default_editor.update_item_size()

    def reset_constraints(self, variable_name: str = "", variable_id: int = 0) -> None:
        """清空所有约束并重建默认栏。"""
        self.variable_name = variable_name
        self.variable_id = variable_id
        self.clear()
        self._constraints = {}
        if self.is_active:
            self.board.constraints = {}
        self.board.update()
        self.add_default_constraint()
        self.add_constraint_item()

    def register_constraint_widget(self, widget: RegionConstraintWidget) -> None:
        self._constraints[widget.id] = widget
        if self.is_active:
            self.board.constraints = dict(self._constraints)
            self.board.update()

    def unregister_constraint_widget(self, cid: int) -> None:
        if cid in self._constraints:
            del self._constraints[cid]
            if self.is_active:
                self.board.constraints = dict(self._constraints)
                self.board.update()

    def activate(self, board) -> None:
        self.is_active = True
        self.board = board
        for widget in self._constraints.values():
            widget.board = board
        self.board.constraints = dict(self._constraints)
        self.board.active_constraint = None
        self.board.update()

    def deactivate(self) -> None:
        self.is_active = False

    def start_editing(self, editor):
        """开始编辑某个约束，自动结束之前的编辑"""
        if self.current_editing_editor and self.current_editing_editor != editor:
            # 结束之前的编辑
            if self.current_editing_editor.mode == "editing":
                self.current_editing_editor.finish_edit()
        self.current_editing_editor = editor
    
    def add_constraint_item(self):
        item = QListWidgetItem("＋ 添加限制")
        self.addItem(item)

    def on_item_clicked(self, item):
        if "添加限制" in item.text():
            # 获取列表中的索引
            row = self.row(item)
            
            # 创建新的编辑器
            cid = self.count() - 1  # 减1是因为有"添加限制"项
            editor = ConstraintEditor(self.board, cid, self)
            self.register_constraint_widget(editor.constraint_widget)
            
            # 用编辑器替换当前的"添加限制"项
            item.setText("")  # 清空文本，避免显示在背景
            item.setSizeHint(editor.sizeHint())
            self.setItemWidget(item, editor)
            
            # 在新的位置插入新的"添加限制"项
            new_item = QListWidgetItem("＋ 添加限制")
            self.insertItem(row + 1, new_item)

    def export_constraints(self):
        """导出所有约束及其表达式、区域和颜色为列表，便于后续编译为 z3 表达式。

        返回每个约束的结构：
        {
            'id': int,
            'condition': str,
            'expr': str,
            'color': (r,g,b,a),
            'region': [[r,c], ...]
        }
        """
        result = []
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            # 忽略“添加限制”文本项（没有 widget）
            if widget is None:
                continue
            # widget 是 ConstraintEditor
            try:
                cid = widget.cid
            except Exception:
                continue

            # 获取当前显示/编辑的值：优先读取 UI 上的最新值
            condition = widget.combo.currentText() if hasattr(widget, 'combo') else widget.data.get('condition', '')
            expr = widget.data.get('expr', '')

            name = widget.name_edit.text() if hasattr(widget, 'name_edit') else widget.data.get('name', '')

            data = {
                'id': cid,
                'condition': condition,
                'expr': expr,
                'name': name,
                'color': (widget.color.red(), widget.color.green(), widget.color.blue(), widget.color.alpha()),
                'region': []
            }

            # 从 board 上抓取对应的 RegionConstraintWidget，获取其 region
            cw = self._constraints.get(cid)
            if cw:
                data['region'] = [[r, c] for (r, c) in cw.region]

            result.append(data)

        return result
