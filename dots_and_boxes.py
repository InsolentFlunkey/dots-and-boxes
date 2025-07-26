import sys
import random
import os
import json
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QMenuBar, QMenu, QInputDialog, QGridLayout, QHBoxLayout, QSizePolicy, QTableWidget, QTableWidgetItem
)
from PySide6.QtGui import QPainter, QPen, QColor, QAction
from PySide6.QtCore import Qt, QRectF, QSize, QTimer

GRID_SIZE = 4  # 4x4 dots = 3x3 boxes
DOT_RADIUS = 6
LINE_THICKNESS = 3
BOX_SIZE = 70
PADDING = 40
DEFAULT_PLAYER_NAME = "Player 1"

class DotsAndBoxesBoard(QWidget):
    def __init__(self, grid_size=GRID_SIZE, player1_name=DEFAULT_PLAYER_NAME, parent=None):
        super().__init__(parent)
        self.grid_size = grid_size
        self.player1_name = player1_name
        self.h_lines = [[False] * (self.grid_size - 1) for _ in range(self.grid_size)]
        self.v_lines = [[False] * self.grid_size for _ in range(self.grid_size - 1)]
        self.boxes = [[None] * (self.grid_size - 1) for _ in range(self.grid_size - 1)]
        self.current_player = 0  # 0 = Human, 1 = Computer
        self.scores = [0, 0]
        self.setFixedSize(
            QSize(
                BOX_SIZE * (self.grid_size - 1) + PADDING * 2,
                BOX_SIZE * (self.grid_size - 1) + PADDING * 2,
            )
        )
        self.status_callback = None
        self.game_over = False

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        # Draw dots
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                qp.setBrush(Qt.black)
                x = PADDING + c * BOX_SIZE
                y = PADDING + r * BOX_SIZE
                qp.drawEllipse(QRectF(x - DOT_RADIUS, y - DOT_RADIUS, 2 * DOT_RADIUS, 2 * DOT_RADIUS))

        # Draw horizontal lines
        qp.setPen(QPen(Qt.blue, LINE_THICKNESS))
        for r in range(self.grid_size):
            for c in range(self.grid_size - 1):
                if self.h_lines[r][c]:
                    x1 = PADDING + c * BOX_SIZE + DOT_RADIUS
                    y1 = PADDING + r * BOX_SIZE
                    x2 = PADDING + (c + 1) * BOX_SIZE - DOT_RADIUS
                    y2 = y1
                    qp.drawLine(x1, y1, x2, y2)

        # Draw vertical lines
        qp.setPen(QPen(Qt.red, LINE_THICKNESS))
        for r in range(self.grid_size - 1):
            for c in range(self.grid_size):
                if self.v_lines[r][c]:
                    x1 = PADDING + c * BOX_SIZE
                    y1 = PADDING + r * BOX_SIZE + DOT_RADIUS
                    x2 = x1
                    y2 = PADDING + (r + 1) * BOX_SIZE - DOT_RADIUS
                    qp.drawLine(x1, y1, x2, y2)

        # Draw claimed boxes
        for r in range(self.grid_size - 1):
            for c in range(self.grid_size - 1):
                owner = self.boxes[r][c]
                if owner is not None:
                    color = QColor(200, 255, 200, 150) if owner == 0 else QColor(200, 200, 255, 150)
                    qp.fillRect(
                        QRectF(
                            PADDING + c * BOX_SIZE + DOT_RADIUS,
                            PADDING + r * BOX_SIZE + DOT_RADIUS,
                            BOX_SIZE - 2 * DOT_RADIUS,
                            BOX_SIZE - 2 * DOT_RADIUS,
                        ),
                        color,
                    )
                    qp.setPen(Qt.black)
                    text = self.player1_name[:1].upper() if owner == 0 else "PC"
                    qp.drawText(
                        PADDING + c * BOX_SIZE + BOX_SIZE // 2 - 10,
                        PADDING + r * BOX_SIZE + BOX_SIZE // 2 + 10,
                        text
                    )

    def mousePressEvent(self, event):
        if self.current_player != 0 or self.game_over:
            return

        pos = event.position() if hasattr(event, 'position') else event.pos()
        r, c, is_h = self.detect_line_clicked(pos.x(), pos.y())
        if r is None:
            return

        if is_h:
            if self.h_lines[r][c]:
                return
            self.h_lines[r][c] = True
        else:
            if self.v_lines[r][c]:
                return
            self.v_lines[r][c] = True

        made_box = self.check_and_update_boxes()
        self.update()
        self.update_status()
        if not made_box:
            self.current_player = 1
            self.update_status()
            QTimer.singleShot(400, self.computer_move)

    def detect_line_clicked(self, x, y):
        # Check h_lines
        for r in range(self.grid_size):
            for c in range(self.grid_size - 1):
                x1 = PADDING + c * BOX_SIZE + DOT_RADIUS
                y1 = PADDING + r * BOX_SIZE
                x2 = PADDING + (c + 1) * BOX_SIZE - DOT_RADIUS
                y2 = y1
                if self.point_near_line(x, y, x1, y1, x2, y2):
                    return r, c, True
        # Check v_lines
        for r in range(self.grid_size - 1):
            for c in range(self.grid_size):
                x1 = PADDING + c * BOX_SIZE
                y1 = PADDING + r * BOX_SIZE + DOT_RADIUS
                x2 = x1
                y2 = PADDING + (r + 1) * BOX_SIZE - DOT_RADIUS
                if self.point_near_line(x, y, x1, y1, x2, y2):
                    return r, c, False
        return None, None, None

    def point_near_line(self, px, py, x1, y1, x2, y2, tol=8):
        # Calculate distance to line segment
        dx, dy = x2 - x1, y2 - y1
        if dx == dy == 0:
            return False
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        lx = x1 + t * dx
        ly = y1 + t * dy
        dist = ((lx - px) ** 2 + (ly - py) ** 2) ** 0.5
        return dist < tol

    def check_and_update_boxes(self):
        made_box = False
        for r in range(self.grid_size - 1):
            for c in range(self.grid_size - 1):
                if self.boxes[r][c] is not None:
                    continue
                if (
                    self.h_lines[r][c] and
                    self.h_lines[r + 1][c] and
                    self.v_lines[r][c] and
                    self.v_lines[r][c + 1]
                ):
                    self.boxes[r][c] = self.current_player
                    self.scores[self.current_player] += 1
                    made_box = True
        if self.is_game_over():
            self.game_over = True
            self.update_status()
        return made_box

    def is_game_over(self):
        for row in self.h_lines:
            if False in row:
                return False
        for row in self.v_lines:
            if False in row:
                return False
        return True

    def update_status(self):
        if self.status_callback:
            self.status_callback("")

    def computer_move(self):
        if self.current_player != 1 or self.game_over:
            return
        moves = self.available_moves()
        # Prefer moves that complete a box
        for move in moves:
            test = self.copy_state()
            test.make_move(*move, player=1)
            if test.check_and_update_boxes_for_move(*move, player=1):
                self.make_move(*move)
                made_box = self.check_and_update_boxes()
                self.update()
                self.update_status()
                if made_box:
                    QTimer.singleShot(400, self.computer_move)
                else:
                    self.current_player = 0
                    self.update_status()
                return
        # Otherwise, avoid making third side of a box
        safe_moves = []
        for move in moves:
            if not self.move_makes_third_side(move):
                safe_moves.append(move)
        if safe_moves:
            move = random.choice(safe_moves)
        else:
            move = random.choice(moves)
        self.make_move(*move)
        made_box = self.check_and_update_boxes()
        self.update()
        self.update_status()
        if made_box:
            QTimer.singleShot(400, self.computer_move)
        else:
            self.current_player = 0
            self.update_status()

    def available_moves(self):
        moves = []
        for r in range(self.grid_size):
            for c in range(self.grid_size - 1):
                if not self.h_lines[r][c]:
                    moves.append((r, c, True))
        for r in range(self.grid_size - 1):
            for c in range(self.grid_size):
                if not self.v_lines[r][c]:
                    moves.append((r, c, False))
        return moves

    def move_makes_third_side(self, move):
        r, c, is_h = move
        if is_h:
            # Top box
            if r > 0:
                n = 0
                if self.h_lines[r - 1][c]:
                    n += 1
                if self.v_lines[r - 1][c]:
                    n += 1
                if self.v_lines[r - 1][c + 1]:
                    n += 1
                if n == 2:
                    return True
            # Bottom box
            if r < self.grid_size - 1:
                n = 0
                if self.h_lines[r + 1][c]:
                    n += 1
                if self.v_lines[r][c]:
                    n += 1
                if self.v_lines[r][c + 1]:
                    n += 1
                if n == 2:
                    return True
        else:
            # Left box
            if c > 0:
                n = 0
                if self.v_lines[r][c - 1]:
                    n += 1
                if self.h_lines[r][c - 1]:
                    n += 1
                if self.h_lines[r + 1][c - 1]:
                    n += 1
                if n == 2:
                    return True
            # Right box
            if c < self.grid_size - 1:
                n = 0
                if self.v_lines[r][c + 1]:
                    n += 1
                if self.h_lines[r][c]:
                    n += 1
                if self.h_lines[r + 1][c]:
                    n += 1
                if n == 2:
                    return True
        return False

    def copy_state(self):
        new = DotsAndBoxesBoard()
        new.grid_size = self.grid_size
        new.h_lines = [row[:] for row in self.h_lines]
        new.v_lines = [row[:] for row in self.v_lines]
        new.boxes = [row[:] for row in self.boxes]
        new.current_player = self.current_player
        new.scores = self.scores[:]
        new.game_over = self.game_over
        return new

    def make_move(self, r, c, is_h, player=None):
        if is_h:
            self.h_lines[r][c] = True
        else:
            self.v_lines[r][c] = True

    def check_and_update_boxes_for_move(self, r, c, is_h, player):
        made_box = False
        # This only checks boxes *adjacent to this move*
        adjacent = []
        if is_h:
            if r > 0:
                adjacent.append((r - 1, c))
            if r < self.grid_size - 1:
                adjacent.append((r, c))
        else:
            if c > 0:
                adjacent.append((r, c - 1))
            if c < self.grid_size - 1:
                adjacent.append((r, c))
        for rr, cc in adjacent:
            if (
                self.h_lines[rr][cc] and
                self.h_lines[rr + 1][cc] and
                self.v_lines[rr][cc] and
                self.v_lines[rr][cc + 1] and
                self.boxes[rr][cc] is None
            ):
                made_box = True
        return made_box

class DotsAndBoxesGame(QWidget):
    def __init__(self, grid_size=GRID_SIZE):
        super().__init__()
        self.setWindowTitle("Dots and Boxes (Squares)")
        self.grid_size = grid_size
        self.player1_name = self.load_player1_name() or DEFAULT_PLAYER_NAME
        self.menu_bar = QMenuBar(self)
        self.menu_bar.setNativeMenuBar(False)  # For cross-platform consistency
        self.game_menu = QMenu("Game", self)
        self.menu_bar.addMenu(self.game_menu)

        self.action_new_same = QAction("New Game (Same Grid Size)", self)
        self.action_new_choose = QAction("New Game (Choose Grid Size)", self)
        self.action_set_name = QAction("Set Player 1 Name", self)
        self.action_exit = QAction("Exit", self)
        self.game_menu.addAction(self.action_new_same)
        self.game_menu.addAction(self.action_new_choose)
        self.game_menu.addAction(self.action_set_name)
        self.game_menu.addSeparator()
        self.game_menu.addAction(self.action_exit)

        self.action_new_same.triggered.connect(self.new_game_same)
        self.action_new_choose.triggered.connect(self.new_game_choose)
        self.action_set_name.triggered.connect(self.set_player1_name)
        self.action_exit.triggered.connect(self.close)

        self.board = DotsAndBoxesBoard(self.grid_size, self.player1_name)
        self.board.status_callback = self.update_status

        # Scoreboard: QTableWidget
        self.scoreboard = QTableWidget(3, 2)
        self.scoreboard.setFixedHeight(110)
        self.scoreboard.setEditTriggers(QTableWidget.NoEditTriggers)
        self.scoreboard.setSelectionMode(QTableWidget.NoSelection)
        self.scoreboard.setFocusPolicy(Qt.NoFocus)
        self.scoreboard.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scoreboard.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scoreboard.horizontalHeader().setVisible(False)
        self.scoreboard.verticalHeader().setVisible(False)
        self.scoreboard.setShowGrid(True)
        self.scoreboard.setStyleSheet("""
            QTableWidget {
                border: none;
                gridline-color: #888;
                background: transparent;
            }
            QTableWidget::item {
                border: 1px solid #888;
                padding: 6px;
                background: transparent;
                color: white;
            }
        """)
        self.scoreboard.setColumnWidth(0, 120)
        self.scoreboard.setColumnWidth(1, 120)
        self.scoreboard.setRowHeight(0, 30)
        self.scoreboard.setRowHeight(1, 30)
        self.scoreboard.setRowHeight(2, 30)

        # Status label for win/tie/game-over
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Center the scoreboard
        layout = QVBoxLayout()
        layout.setMenuBar(self.menu_bar)
        scoreboard_hbox = QHBoxLayout()
        scoreboard_hbox.addStretch(1)
        scoreboard_hbox.addWidget(self.scoreboard)
        scoreboard_hbox.addStretch(1)
        layout.addLayout(scoreboard_hbox)
        layout.addWidget(self.board)
        layout.addWidget(self.status_label)
        self.setLayout(layout)
        self.update_status("")

    def update_status(self, msg=None):
        player_name = self.player1_name
        computer_name = "Computer"
        scores = self.board.scores
        current_player = self.board.current_player
        game_over = self.board.game_over
        # Header
        header_item = QTableWidgetItem("Score")
        header_item.setTextAlignment(Qt.AlignCenter)
        header_item.setForeground(Qt.white)
        font = header_item.font()
        font.setBold(True)
        header_item.setFont(font)
        header_item.setFlags(Qt.ItemIsEnabled)
        self.scoreboard.setItem(0, 0, header_item)
        self.scoreboard.setSpan(0, 0, 1, 2)
        # Player names
        player_item = QTableWidgetItem(player_name)
        player_item.setTextAlignment(Qt.AlignCenter)
        computer_item = QTableWidgetItem(computer_name)
        computer_item.setTextAlignment(Qt.AlignCenter)
        # Highlight current player name
        if current_player == 0 and not game_over:
            player_item.setBackground(Qt.white)
            player_item.setForeground(Qt.black)
            font = player_item.font()
            font.setBold(True)
            player_item.setFont(font)
        if current_player == 1 and not game_over:
            computer_item.setBackground(Qt.white)
            computer_item.setForeground(Qt.black)
            font = computer_item.font()
            font.setBold(True)
            computer_item.setFont(font)
        self.scoreboard.setItem(1, 0, player_item)
        self.scoreboard.setItem(1, 1, computer_item)
        # Scores
        player_score_item = QTableWidgetItem(str(scores[0]))
        player_score_item.setTextAlignment(Qt.AlignCenter)
        computer_score_item = QTableWidgetItem(str(scores[1]))
        computer_score_item.setTextAlignment(Qt.AlignCenter)
        self.scoreboard.setItem(2, 0, player_score_item)
        self.scoreboard.setItem(2, 1, computer_score_item)
        # Status message
        if game_over:
            if scores[0] > scores[1]:
                status = f"{player_name} wins!  ( {scores[0]} to {scores[1]} )"
            elif scores[0] < scores[1]:
                status = f"{computer_name} wins!  ( {scores[1]} to {scores[0]} )"
            else:
                status = f"It's a tie!  ( {scores[0]} each )"
        else:
            turn = f"{player_name}'s" if current_player == 0 else f"{computer_name}'s"
            status = f"{turn} turn"
        self.status_label.setText(status)
        if msg and msg != status:
            self.status_label.setText(msg)

    def new_game_same(self):
        self._reset_board(self.grid_size, self.player1_name)

    def new_game_choose(self):
        size, ok = QInputDialog.getInt(self, "Choose Grid Size", "Grid size (number of dots, 3-10):", self.grid_size, 3, 10)
        if ok:
            self.grid_size = size
            self._reset_board(self.grid_size, self.player1_name)

    def _reset_board(self, grid_size, player1_name):
        self.layout().removeWidget(self.board)
        self.board.deleteLater()
        self.board = DotsAndBoxesBoard(grid_size, player1_name)
        self.board.status_callback = self.update_status
        self.layout().insertWidget(1, self.board)  # after scoreboard
        self.update_status("")

    def set_player1_name(self):
        name, ok = QInputDialog.getText(self, "Set Player 1 Name", "Enter Player 1's name:", text=self.player1_name)
        if ok and name.strip():
            self.player1_name = name.strip()
            self.save_player1_name(self.player1_name)
            self._reset_board(self.grid_size, self.player1_name)

    def load_player1_name(self):
        config_path = os.path.join(os.path.dirname(__file__), "player_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("player1_name", DEFAULT_PLAYER_NAME)
            except Exception:
                return DEFAULT_PLAYER_NAME
        return DEFAULT_PLAYER_NAME

    def save_player1_name(self, name):
        config_path = os.path.join(os.path.dirname(__file__), "player_config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"player1_name": name}, f)
        except Exception:
            pass

def main():
    app = QApplication(sys.argv)
    game = DotsAndBoxesGame()
    game.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
