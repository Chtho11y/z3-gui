from PySide6.QtCore import Qt


class ModeBase:
    def __init__(self, board):
        self.board = board

    def enter(self, *args, **kwargs):
        pass

    def exit(self):
        pass

    def on_mouse_press(self, event):
        pass

    def on_mouse_move(self, event):
        pass

    def on_mouse_release(self, event):
        pass

    def on_key_press(self, event):
        return False

    def paint(self, painter):
        pass


class ViewMode(ModeBase):
    def on_mouse_press(self, event):
        rect = self.board.board_rect()
        if rect.contains(event.position().toPoint()):
            col = int((event.position().x() - rect.left()) / (rect.width() / self.board.n))
            row = int((event.position().y() - rect.top()) / (rect.height() / self.board.n))
            self.board.start_edit(row, col)
        else:
            self.board.commit_edit()
            self.board.editor.hide()


class EditMode(ModeBase):
    def enter(self, *args, **kwargs):
        self.board.input_mode = 'edit'

    def exit(self):
        self.board.input_mode = 'view'

    def on_mouse_press(self, event):
        # clicking while editing should commit current edit and possibly start new one
        rect = self.board.board_rect()
        if rect.contains(event.position().toPoint()):
            col = int((event.position().x() - rect.left()) / (rect.width() / self.board.n))
            row = int((event.position().y() - rect.top()) / (rect.height() / self.board.n))
            self.board.start_edit(row, col)
        else:
            self.board.commit_edit()
            self.board.editor.hide()


class SelectMode(ModeBase):
    def enter(self, constraint=None):
        self.board.input_mode = 'select'
        self.board.active_constraint = constraint
        if constraint and constraint.id not in self.board.constraints:
            self.board.constraints[constraint.id] = constraint

    def on_mouse_press(self, event):
        cell = self.board.pos_to_cell(event.position().toPoint())
        if cell:
            self.board.dragging = True
            self.board.last_drag_cell = cell
            if self.board.active_constraint:
                self.board.active_constraint.commit_selection(cell)
            self.board.update()

    def on_mouse_move(self, event):
        if self.board.dragging:
            cell = self.board.pos_to_cell(event.position().toPoint())
            if cell and cell != self.board.last_drag_cell:
                if self.board.active_constraint:
                    self.board.active_constraint.commit_selection(cell)
                self.board.last_drag_cell = cell
                self.board.update()

    def on_mouse_release(self, event):
        self.board.dragging = False
        self.board.last_drag_cell = None

    def on_key_press(self, event):
        if event.key() == Qt.Key_Return:
            self.board.confirm_selection()
            return True
        return False
