import sys
import random
import os
import json
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QMenuBar, QMenu, QInputDialog, QGridLayout, QHBoxLayout, QSizePolicy, QTableWidget, QTableWidgetItem, QPushButton, QDialog, QDialogButtonBox, QCheckBox, QMessageBox
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
        self.last_move = None  # (r, c, is_h)
        self.blinking = False
        self.blink_state = False
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self._blink_step)
        self.blink_count = 0
        self.blink_target = None
        self.setMouseTracking(True)
        self.hovered_line = None  # (r, c, is_h) or None

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
        for r in range(self.grid_size):
            for c in range(self.grid_size - 1):
                is_last = self.blinking and self.blink_target and (r, c, True) == self.blink_target
                if self.h_lines[r][c] and not (is_last and not self.blink_state):
                    qp.setPen(QPen(Qt.blue if not is_last or self.blink_state else Qt.gray, LINE_THICKNESS))
                    x1 = PADDING + c * BOX_SIZE + DOT_RADIUS
                    y1 = PADDING + r * BOX_SIZE
                    x2 = PADDING + (c + 1) * BOX_SIZE - DOT_RADIUS
                    y2 = y1
                    qp.drawLine(x1, y1, x2, y2)
                # Draw hover shadow for horizontal line
                if (
                    self.hovered_line
                    and self.hovered_line == (r, c, True)
                    and not self.h_lines[r][c]
                    and not self.blinking
                ):
                    qp.setPen(QPen(QColor(100, 100, 255, 120), LINE_THICKNESS + 2, Qt.DashLine))
                    x1 = PADDING + c * BOX_SIZE + DOT_RADIUS
                    y1 = PADDING + r * BOX_SIZE
                    x2 = PADDING + (c + 1) * BOX_SIZE - DOT_RADIUS
                    y2 = y1
                    qp.drawLine(x1, y1, x2, y2)

        # Draw vertical lines
        for r in range(self.grid_size - 1):
            for c in range(self.grid_size):
                is_last = self.blinking and self.blink_target and (r, c, False) == self.blink_target
                if self.v_lines[r][c] and not (is_last and not self.blink_state):
                    qp.setPen(QPen(Qt.red if not is_last or self.blink_state else Qt.gray, LINE_THICKNESS))
                    x1 = PADDING + c * BOX_SIZE
                    y1 = PADDING + r * BOX_SIZE + DOT_RADIUS
                    x2 = x1
                    y2 = PADDING + (r + 1) * BOX_SIZE - DOT_RADIUS
                    qp.drawLine(x1, y1, x2, y2)
                # Draw hover shadow for vertical line
                if (
                    self.hovered_line
                    and self.hovered_line == (r, c, False)
                    and not self.v_lines[r][c]
                    and not self.blinking
                ):
                    qp.setPen(QPen(QColor(255, 100, 100, 120), LINE_THICKNESS + 2, Qt.DashLine))
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

    def _start_blink(self, move, blinks=2):
        self.blinking = True
        self.blink_target = move
        self.blink_count = 0
        self.blink_state = True
        self.blink_total = blinks * 2  # on/off cycles
        self.blink_timer.start(120)
        self.update()

    def _blink_step(self):
        self.blink_state = not self.blink_state
        self.blink_count += 1
        self.update()
        if self.blink_count >= self.blink_total:
            self.blink_timer.stop()
            self.blinking = False
            self.blink_target = None
            self.update()
            # If it's the computer's turn and the game isn't over, trigger computer move
            if self.current_player == 1 and not self.game_over:
                QTimer.singleShot(100, self.computer_move)

    def show_last_move(self):
        if self.last_move:
            self._start_blink(self.last_move, blinks=3)

    def mousePressEvent(self, event):
        if self.current_player != 0 or self.game_over or self.blinking:
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

        self.last_move = (r, c, is_h)
        self._start_blink(self.last_move)
        made_box = self.check_and_update_boxes()
        self.update()
        self.update_status()
        if not made_box:
            self.current_player = 1
            self.update_status()
            QTimer.singleShot(400, self.computer_move)

    def mouseMoveEvent(self, event):
        if self.blinking or self.game_over or self.current_player != 0:
            if self.hovered_line is not None:
                self.hovered_line = None
                self.update()
            return
        pos = event.position() if hasattr(event, 'position') else event.pos()
        r, c, is_h = self.detect_line_clicked(pos.x(), pos.y())
        if r is not None:
            if is_h and not self.h_lines[r][c]:
                new_hover = (r, c, True)
            elif not is_h and not self.v_lines[r][c]:
                new_hover = (r, c, False)
            else:
                new_hover = None
        else:
            new_hover = None
        if new_hover != self.hovered_line:
            self.hovered_line = new_hover
            self.update()

    def leaveEvent(self, event):
        if self.hovered_line is not None:
            self.hovered_line = None
            self.update()

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
        if self.current_player != 1 or self.game_over or self.blinking:
            return
        moves = self.available_moves()
        # Prefer moves that complete a box
        for move in moves:
            test = self.copy_state()
            test.make_move(*move, player=1)
            if test.check_and_update_boxes_for_move(*move, player=1):
                self.make_move(*move)
                self.last_move = move
                self._start_blink(self.last_move)
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
        self.last_move = move
        self._start_blink(self.last_move)
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
        new.last_move = self.last_move
        new.blinking = self.blinking
        new.blink_state = self.blink_state
        new.blink_count = self.blink_count
        new.blink_target = self.blink_target
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

class WhoGoesFirstDialog(QDialog):
    def __init__(self, player_name, parent=None, animation_only=False, remember_checked=False, preselect=None):
        super().__init__(parent)
        self.setWindowTitle("Who goes first?")
        self.selected = None
        self.remember = False
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._anim_step)
        self.anim_index = 0
        self.anim_list = [0, 1] * 6  # Alternates 12 times
        self.anim_speeds = [60, 60, 80, 80, 100, 100, 120, 140, 180, 220, 300, 400]
        self.anim_final = None
        self.animation_only = animation_only
        self.remember_random = False  # Track if 'remember' was checked with Random
        self.preselect = preselect

        layout = QVBoxLayout()
        self.label = QLabel("Who should go first?" if not animation_only else "Randomly choosing who goes first...")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        btn_layout = QHBoxLayout()
        self.btn_player = QPushButton(player_name)
        self.btn_computer = QPushButton("Computer")
        btn_layout.addWidget(self.btn_player)
        btn_layout.addWidget(self.btn_computer)
        layout.addLayout(btn_layout)

        if not animation_only:
            self.btn_random = QPushButton("Random")
            btn_layout.addWidget(self.btn_random)
            self.btn_player.clicked.connect(lambda: self._choose(0))
            self.btn_computer.clicked.connect(lambda: self._choose(1))
            self.btn_random.clicked.connect(self._start_anim_remember)
            self.remember_box = QCheckBox("Remember my choice")
            self.remember_box.setChecked(remember_checked)
            # Preselect highlight
            if preselect == 0:
                self.btn_player.setStyleSheet("background: #e0e0e0; font-weight: bold;")
            elif preselect == 1:
                self.btn_computer.setStyleSheet("background: #e0e0e0; font-weight: bold;")
            elif preselect == 'random':
                self.btn_random.setStyleSheet("background: #e0e0e0; font-weight: bold;")
            layout.addWidget(self.remember_box)
        else:
            # In animation-only mode, disable buttons
            self.btn_player.setEnabled(False)
            self.btn_computer.setEnabled(False)
            QTimer.singleShot(300, self._start_anim)

        self.setLayout(layout)
        self.setFixedWidth(340)

    def _start_anim_remember(self):
        # Called when Random is clicked in full dialog
        self.remember_random = self.remember_box.isChecked()
        self._start_anim()

    def _choose(self, who):
        # If this was a remembered random, set selected to 'random' for config, but return the actual result for this game
        if hasattr(self, 'remember_random') and self.remember_random:
            self.selected = 'random'  # For config
            self.remember = True
            self._actual_random_result = who  # For this game only
            self.accept()
        else:
            self.selected = who
            if not self.animation_only:
                self.remember = self.remember_box.isChecked()
            self.accept()

    def _start_anim(self):
        self.btn_player.setStyleSheet("")
        self.btn_computer.setStyleSheet("")
        self.anim_index = 0
        self.anim_final = random.choice([0, 1])
        self.anim_list = [0, 1] * 6 + [self.anim_final] * 2
        self.anim_speeds = [60, 60, 80, 80, 100, 100, 120, 140, 180, 220, 300, 400, 500, 600]
        self.anim_timer.start(self.anim_speeds[0])

    def _anim_step(self):
        idx = self.anim_list[self.anim_index]
        self.btn_player.setStyleSheet("background: white; color: black; font-weight: bold;" if idx == 0 else "")
        self.btn_computer.setStyleSheet("background: white; color: black; font-weight: bold;" if idx == 1 else "")
        self.anim_index += 1
        if self.anim_index >= len(self.anim_list):
            self.anim_timer.stop()
            self._choose(self.anim_final)
        else:
            self.anim_timer.start(self.anim_speeds[min(self.anim_index, len(self.anim_speeds)-1)])

class DotsAndBoxesGame(QWidget):
    def __init__(self, grid_size=GRID_SIZE):
        super().__init__()
        self.setWindowTitle("Dots and Boxes (Squares)")
        config = self.load_player_config()
        self.grid_size = config.get("grid_size", GRID_SIZE)
        self.player1_name = config.get("player1_name", DEFAULT_PLAYER_NAME)
        self.who_goes_first = config.get("who_goes_first", None)  # 0=player, 1=computer, 'random', None=ask
        self.remember_who_goes_first = config.get("remember_who_goes_first", False)
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

        # Add menu item for 'Who goes first' dialog
        self.action_who_first = QAction("Who goes first...", self)
        self.game_menu.addAction(self.action_who_first)
        self.action_who_first.triggered.connect(self.show_who_goes_first_dialog)

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

        # Show last move button
        self.show_last_move_btn = QPushButton("Show last move")
        self.show_last_move_btn.clicked.connect(self.handle_show_last_move)
        self.show_last_move_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.show_last_move_btn.setMinimumWidth(120)
        self.show_last_move_btn.setStyleSheet("padding: 6px 18px;")

        # Center the scoreboard
        layout = QVBoxLayout()
        layout.setMenuBar(self.menu_bar)
        scoreboard_hbox = QHBoxLayout()
        scoreboard_hbox.addStretch(1)
        scoreboard_hbox.addWidget(self.scoreboard)
        scoreboard_hbox.addStretch(1)
        layout.addLayout(scoreboard_hbox)
        layout.addWidget(self.board)
        # Center the button horizontally
        btn_hbox = QHBoxLayout()
        btn_hbox.addStretch(1)
        btn_hbox.addWidget(self.show_last_move_btn)
        btn_hbox.addStretch(1)
        layout.addLayout(btn_hbox)
        layout.addWidget(self.status_label)
        self.setLayout(layout)
        self.update_status("")

        # Start a new game on app launch (shows 'Who goes first' dialog if needed)
        QTimer.singleShot(0, lambda: self._start_new_game(self.grid_size, self.player1_name))

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
        self._start_new_game(self.grid_size, self.player1_name)

    def new_game_choose(self):
        size, ok = QInputDialog.getInt(self, "Choose Grid Size", "Grid size (number of dots, 3-10):", self.grid_size, 3, 10)
        if ok:
            self.grid_size = size
            self.save_player_config(self.player1_name, self.grid_size)
            self._start_new_game(self.grid_size, self.player1_name)

    def _start_new_game(self, grid_size, player1_name):
        # Who goes first logic
        # Always reload config to get latest values
        config = self.load_player_config()
        self.who_goes_first = config.get("who_goes_first", None)
        self.remember_who_goes_first = config.get("remember_who_goes_first", False)
        who_first = self.who_goes_first if self.remember_who_goes_first else None
        if who_first is None:
            dlg = WhoGoesFirstDialog(player1_name, self)
            if dlg.exec() == QDialog.Accepted:
                # If Random was chosen and remember is checked, store 'random' in config, but use the actual result for this game
                if hasattr(dlg, 'remember_random') and dlg.remember_random:
                    self.who_goes_first = 'random'
                    self.remember_who_goes_first = True
                    self.save_player_config(player1_name, grid_size, 'random', True)
                    who_first = dlg._actual_random_result
                else:
                    who_first = dlg.selected
                    self.remember_who_goes_first = dlg.remember
                    if dlg.remember:
                        self.who_goes_first = dlg.selected
                    else:
                        self.who_goes_first = None
                    self.save_player_config(player1_name, grid_size, self.who_goes_first if self.remember_who_goes_first else None, self.remember_who_goes_first)
        if who_first == 'random':
            # Show only the animation dialog
            dlg = WhoGoesFirstDialog(player1_name, self, animation_only=True)
            if dlg.exec() == QDialog.Accepted:
                who_first = dlg.selected
        self.layout().removeWidget(self.board)
        self.board.deleteLater()
        self.board = DotsAndBoxesBoard(grid_size, player1_name)
        self.board.status_callback = self.update_status
        self.layout().insertWidget(1, self.board)  # after scoreboard
        self.update_status("")
        # Set who goes first
        if who_first == 1:
            self.board.current_player = 1
            QTimer.singleShot(400, self.board.computer_move)
        else:
            self.board.current_player = 0
        self.save_player_config(player1_name, grid_size, self.who_goes_first if self.remember_who_goes_first else None, self.remember_who_goes_first)

    def show_who_goes_first_dialog(self):
        # Determine preselect value
        preselect = None
        if self.remember_who_goes_first:
            preselect = self.who_goes_first
        dlg = WhoGoesFirstDialog(
            self.player1_name,
            self,
            animation_only=False,
            remember_checked=self.remember_who_goes_first,
            preselect=preselect
        )
        if dlg.exec() == QDialog.Accepted:
            self.who_goes_first = dlg.selected
            self.remember_who_goes_first = dlg.remember
            self.save_player_config(self.player1_name, self.grid_size, self.who_goes_first if self.remember_who_goes_first else None, self.remember_who_goes_first)
            # If the game hasn't started, restart automatically
            if not self.game_has_started():
                self._start_new_game(self.grid_size, self.player1_name)
            else:
                # Prompt to restart
                reply = QMessageBox.question(self, "Restart Game?", "Start a new game now with this setting?", QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self._start_new_game(self.grid_size, self.player1_name)

    def set_player1_name(self):
        name, ok = QInputDialog.getText(self, "Set Player 1 Name", "Enter Player 1's name:", text=self.player1_name)
        if ok and name.strip():
            self.player1_name = name.strip()
            self.save_player_config(self.player1_name, self.grid_size, self.who_goes_first if self.remember_who_goes_first else None, self.remember_who_goes_first)
            self._start_new_game(self.grid_size, self.player1_name)

    def load_player_config(self):
        config_path = os.path.join(os.path.dirname(__file__), "player_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data
            except Exception:
                return {}
        return {}

    def save_player_config(self, player1_name, grid_size, who_goes_first=None, remember_who_goes_first=False):
        config_path = os.path.join(os.path.dirname(__file__), "player_config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({
                    "player1_name": player1_name,
                    "grid_size": grid_size,
                    "who_goes_first": who_goes_first,
                    "remember_who_goes_first": remember_who_goes_first
                }, f)
        except Exception:
            pass

    def handle_show_last_move(self):
        self.board.show_last_move()

    def game_has_started(self):
        # Returns True if any move has been made
        if hasattr(self, 'board') and self.board:
            for row in self.board.h_lines:
                if any(row):
                    return True
            for row in self.board.v_lines:
                if any(row):
                    return True
        return False

def main():
    app = QApplication(sys.argv)
    game = DotsAndBoxesGame()
    game.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
