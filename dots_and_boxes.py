import sys
import random
import os
import json
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QMenuBar, QMenu, 
    QInputDialog, QHBoxLayout, QSizePolicy, QTableWidget, QTableWidgetItem, 
    QPushButton, QDialog, QDialogButtonBox, QCheckBox, QRadioButton, QButtonGroup, QMessageBox
)
from PySide6.QtGui import QPainter, QPen, QColor, QAction, QPalette
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
        # NOTE: This method name must remain 'paintEvent' to override the Qt event handler.
        # Renaming to 'paint_event' (PEP8) would break PySide6/Qt event dispatch.
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        self._draw_dots(qp)
        self._draw_horizontal_lines(qp)
        self._draw_vertical_lines(qp)
        self._draw_hover_shadows(qp)
        self._draw_claimed_boxes(qp)

    def _draw_dots(self, qp):
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                qp.setBrush(Qt.black)
                x = PADDING + c * BOX_SIZE
                y = PADDING + r * BOX_SIZE
                qp.drawEllipse(QRectF(x - DOT_RADIUS, y - DOT_RADIUS, 2 * DOT_RADIUS, 2 * DOT_RADIUS))

    def _draw_horizontal_lines(self, qp):
        for r in range(self.grid_size):
            for c in range(self.grid_size - 1):
                self._draw_single_horizontal_line(qp, r, c)

    def _draw_single_horizontal_line(self, qp, r, c):
        is_last = self.blinking and self.blink_target and (r, c, True) == self.blink_target
        if self.h_lines[r][c] and not (is_last and not self.blink_state):
            qp.setPen(QPen(
                Qt.blue if not is_last or self.blink_state else Qt.gray, 
                LINE_THICKNESS, 
                Qt.SolidLine if not is_last or self.blink_state else Qt.DashLine
            ))
            x1 = PADDING + c * BOX_SIZE + DOT_RADIUS
            y1 = PADDING + r * BOX_SIZE
            x2 = PADDING + (c + 1) * BOX_SIZE - DOT_RADIUS
            y2 = y1
            qp.drawLine(x1, y1, x2, y2)

    def _draw_vertical_lines(self, qp):
        for r in range(self.grid_size - 1):
            for c in range(self.grid_size):
                is_last = self.blinking and self.blink_target and (r, c, False) == self.blink_target
                if self.v_lines[r][c] and not (is_last and not self.blink_state):
                    qp.setPen(QPen(
                        Qt.red if not is_last or self.blink_state else Qt.gray, LINE_THICKNESS
                    ))
                    x1 = PADDING + c * BOX_SIZE
                    y1 = PADDING + r * BOX_SIZE + DOT_RADIUS
                    x2 = x1
                    y2 = PADDING + (r + 1) * BOX_SIZE - DOT_RADIUS
                    qp.drawLine(x1, y1, x2, y2)

    def _draw_hover_shadows(self, qp):
        # Horizontal hover
        for r in range(self.grid_size):
            for c in range(self.grid_size - 1):
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
        # Vertical hover
        for r in range(self.grid_size - 1):
            for c in range(self.grid_size):
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

    def _draw_claimed_boxes(self, qp):
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
        move = self._find_box_completing_move(moves)
        if move is None:
            move = self._find_safe_move(moves)
        if move is None:
            move = self._find_least_damaging_move(moves)
        self._execute_computer_move(move)

    def _find_box_completing_move(self, moves):
        for move in moves:
            test = self.copy_state()
            test.make_move(*move, player=1)
            if test.check_and_update_boxes_for_move(*move, player=1):
                return move
        return None

    def _find_safe_move(self, moves):
        safe_moves = [move for move in moves if not self.move_makes_third_side(move)]
        return random.choice(safe_moves) if safe_moves else None

    def _find_least_damaging_move(self, moves):
        # For each move, simulate and count the full chain of boxes the opponent could claim
        min_chain = None
        best_moves = []
        for move in moves:
            test = self.copy_state()
            test.make_move(*move, player=1)
            chain = test._simulate_opponent_chain()
            if min_chain is None or chain < min_chain:
                min_chain = chain
                best_moves = [move]
            elif chain == min_chain:
                best_moves.append(move)
        return random.choice(best_moves) if best_moves else random.choice(moves)

    def _simulate_opponent_chain(self):
        # Simulate the opponent's turn, recursively claiming all possible boxes in a chain
        total = 0
        while True:
            moves = self.available_moves()
            best = None
            best_count = 0
            for move in moves:
                count = self._count_new_boxes(*move, player=0)
                if count > best_count:
                    best_count = count
                    best = move
            if best and best_count > 0:
                self.make_move(*best, player=0)
                self.check_and_update_boxes_for_move(*best, player=0)
                total += best_count
            else:
                break
        return total

    def _count_new_boxes(self, r, c, is_h, player):
        # Count how many boxes are completed by this move
        count = 0
        for rr, cc in self._adjacent_boxes(r, c, is_h):
            if (
                self.h_lines[rr][cc] and
                self.h_lines[rr + 1][cc] and
                self.v_lines[rr][cc] and
                self.v_lines[rr][cc + 1] and
                self.boxes[rr][cc] is None
            ):
                count += 1
        return count

    def _adjacent_boxes(self, r, c, is_h):
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
        return adjacent

    def _execute_computer_move(self, move):
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
            if r > 0 and self._box_has_two_sides(self.h_lines, self.v_lines, r - 1, c):
                return True
            # Bottom box
            if r < self.grid_size - 1 and self._box_has_two_sides(self.h_lines, self.v_lines, r, c):
                return True
        else:
            # Left box
            if c > 0 and self._box_has_two_sides(self.h_lines, self.v_lines, r, c - 1):
                return True
            # Right box
            if c < self.grid_size - 1 and self._box_has_two_sides(self.h_lines, self.v_lines, r, c):
                return True
        return False

    def _box_has_two_sides(self, h_lines, v_lines, r, c):
        n = 0
        if h_lines[r][c]: n += 1
        if h_lines[r + 1][c]: n += 1
        if v_lines[r][c]: n += 1
        if v_lines[r][c + 1]: n += 1
        return n == 2

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
    def __init__(
        self, player_name, parent=None, 
        animation_only=False, remember_checked=False, preselect=None
        ):
        
        """
        Dialog for selecting who goes first.
        :param player_name: Name of the player
        :param parent: Parent widget
        :param animation_only: If True, only show the animation
        :param remember_checked: If True, remember the choice
        :param preselect: Preselect a choice (0=player, 1=computer, 'random')
        """
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
        self.label = QLabel(
            "Who should go first?" if not animation_only else "Randomly choosing who goes first..."
            )
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)


        if not animation_only:
            self.radio_group = QButtonGroup(self)
            self.radio_player = QRadioButton(player_name)
            self.radio_computer = QRadioButton("Computer")
            self.radio_random = QRadioButton("Random")
            self.radio_group.addButton(self.radio_player, 0)
            self.radio_group.addButton(self.radio_computer, 1)
            self.radio_group.addButton(self.radio_random, 2)
            radio_layout = QHBoxLayout()
            radio_layout.addWidget(self.radio_player)
            radio_layout.addWidget(self.radio_computer)
            radio_layout.addWidget(self.radio_random)
            layout.addLayout(radio_layout)
            # Preselect
            if preselect == 0:
                self.radio_player.setChecked(True)
            elif preselect == 1:
                self.radio_computer.setChecked(True)
            elif preselect == 'random':
                self.radio_random.setChecked(True)
            else:
                self.radio_player.setChecked(True)
            self.remember_box = QCheckBox("Remember my choice")
            self.remember_box.setChecked(remember_checked)
            layout.addWidget(self.remember_box)
            # Submit button
            btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            btn_box.accepted.connect(self._on_submit)
            btn_box.rejected.connect(self.reject)
            layout.addWidget(btn_box)
        else:
            # In animation-only mode, just run the animation
            self.btn_player = QPushButton(player_name)
            self.btn_computer = QPushButton("Computer")
            btn_layout = QHBoxLayout()
            btn_layout.addWidget(self.btn_player)
            btn_layout.addWidget(self.btn_computer)
            layout.addLayout(btn_layout)
            self.btn_player.setEnabled(False)
            self.btn_computer.setEnabled(False)
            QTimer.singleShot(300, self._start_anim)

        self.setLayout(layout)
        self.setFixedWidth(340)

    def _on_submit(self):
        idx = self.radio_group.checkedId()
        if idx == 0:
            self.selected = 0
        elif idx == 1:
            self.selected = 1
        elif idx == 2:
            self.selected = 'random'
        else:
            self.selected = 0
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
            self.selected = self.anim_final
            self.accept()
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
        self.dark_mode = config.get("dark_mode", None)
        self.menu_bar = QMenuBar(self)
        self.menu_bar.setNativeMenuBar(False)  # For cross-platform consistency
        self.game_menu = QMenu("Game Menu", self)
        self.menu_bar.addMenu(self.game_menu)

        self.action_new_same = QAction("New Game (Same Grid Size)", self)
        self.action_new_choose = QAction("New Game (Choose Grid Size)", self)
        self.action_set_name = QAction("Set Player 1 Name", self)
        self.action_who_first = QAction("Who goes first...", self)
        self.action_toggle_dark = QAction("Toggle Dark/Light Mode", self)
        self.action_exit = QAction("Exit", self)
        self.game_menu.addAction(self.action_new_same)
        self.game_menu.addAction(self.action_new_choose)
        self.game_menu.addAction(self.action_set_name)
        self.game_menu.addAction(self.action_who_first)
        self.game_menu.addAction(self.action_toggle_dark)
        self.game_menu.addSeparator()
        self.game_menu.addAction(self.action_exit)

        self.action_new_same.triggered.connect(self.new_game_same)
        self.action_new_choose.triggered.connect(self.new_game_choose)
        self.action_set_name.triggered.connect(self.set_player1_name)
        self.action_exit.triggered.connect(self.close)
        self.action_who_first.triggered.connect(self.show_who_goes_first_dialog)
        self.action_toggle_dark.triggered.connect(self.toggle_dark_mode)

        # Create the game board before adding to layout
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

        # Apply theme on startup (after scoreboard is created)
        if self.dark_mode is not None:
            self.apply_dark_mode(self.dark_mode)
        else:
            # Use system default
            self.dark_mode = self.is_system_dark_mode()
            self.apply_dark_mode(self.dark_mode)

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
        who_first = self._determine_who_goes_first(grid_size, player1_name)
        self._reset_board_and_start(grid_size, player1_name, who_first)

    def _determine_who_goes_first(self, grid_size, player1_name):
        config = self.load_player_config()
        self.who_goes_first = config.get("who_goes_first", None)
        self.remember_who_goes_first = config.get("remember_who_goes_first", False)
        who_first = self.who_goes_first if self.remember_who_goes_first else None
        if who_first is None:
            dlg = WhoGoesFirstDialog(player1_name, self)
            if dlg.exec() == QDialog.Accepted:
                who_first = dlg.selected
                self.remember_who_goes_first = dlg.remember
                if dlg.remember:
                    self.who_goes_first = dlg.selected
                else:
                    self.who_goes_first = None
                self.save_player_config(player1_name, grid_size, self.who_goes_first if self.remember_who_goes_first else None, self.remember_who_goes_first)
        if who_first == 'random':
            dlg = WhoGoesFirstDialog(player1_name, self, animation_only=True)
            if dlg.exec() == QDialog.Accepted:
                who_first = dlg.selected
        return who_first

    def _reset_board_and_start(self, grid_size, player1_name, who_first):
        self.layout().removeWidget(self.board)
        self.board.deleteLater()
        self.board = DotsAndBoxesBoard(grid_size, player1_name)
        self.board.status_callback = self.update_status
        self.layout().insertWidget(1, self.board)  # after scoreboard
        self.update_status("")
        if who_first == 1:
            self.board.current_player = 1
            QTimer.singleShot(400, self.board.computer_move)
        else:
            self.board.current_player = 0
        self.save_player_config(
            player1_name, grid_size, self.who_goes_first if self.remember_who_goes_first else None, 
            self.remember_who_goes_first
        )

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

    def save_player_config(self, player1_name, grid_size, who_goes_first=None, remember_who_goes_first=False, dark_mode=None):
        config_path = os.path.join(os.path.dirname(__file__), "player_config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                config = {
                    "player1_name": player1_name,
                    "grid_size": grid_size,
                    "who_goes_first": who_goes_first,
                    "remember_who_goes_first": remember_who_goes_first
                }
                if dark_mode is not None:
                    config["dark_mode"] = dark_mode
                json.dump(config, f)
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

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.apply_dark_mode(self.dark_mode)
        self.save_player_config(
            self.player1_name, self.grid_size, self.who_goes_first if self.remember_who_goes_first else None,
            self.remember_who_goes_first, self.dark_mode
        )

    def apply_dark_mode(self, enabled):
        app = QApplication.instance()
        if enabled:
            # Cobalt blue-gray dark mode
            dark_palette = QPalette()
            dark_palette.setColor(QPalette.Window, QColor('#22304a'))
            dark_palette.setColor(QPalette.WindowText, Qt.white)
            dark_palette.setColor(QPalette.Base, QColor('#22304a'))
            dark_palette.setColor(QPalette.AlternateBase, QColor('#2a3a5a'))
            dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
            dark_palette.setColor(QPalette.ToolTipText, Qt.white)
            dark_palette.setColor(QPalette.Text, Qt.white)
            dark_palette.setColor(QPalette.Button, QColor('#2a3a5a'))
            dark_palette.setColor(QPalette.ButtonText, Qt.white)
            dark_palette.setColor(QPalette.BrightText, QColor('#3a7bd5'))
            dark_palette.setColor(QPalette.Link, QColor('#3a7bd5'))
            dark_palette.setColor(QPalette.Highlight, QColor('#3a7bd5'))
            dark_palette.setColor(QPalette.HighlightedText, Qt.white)
            dark_palette.setColor(QPalette.Light, QColor('#3a7bd5'))
            dark_palette.setColor(QPalette.Mid, QColor('#3a4a6a'))
            dark_palette.setColor(QPalette.Midlight, QColor('#2a3a5a'))
            dark_palette.setColor(QPalette.Dark, QColor('#1a2233'))
            dark_palette.setColor(QPalette.Shadow, QColor('#1a2233'))
            app.setPalette(dark_palette)
            self._set_scoreboard_text_color('white')
            app.setStyleSheet("""
                QMenu {
                    background-color: #2a3a5a;
                    color: white;
                    border: 1px solid #3a4a6a;
                    border-radius: 8px;
                    padding: 4px;
                }
                QMenu::item:selected {
                    background: #3a7bd5;
                    color: white;
                }
            """
            )
            self.show_last_move_btn.setStyleSheet(
                """
                QPushButton {
                    padding: 6px 18px;
                    background: #2a3a5a;
                    color: white;
                    border: 1px solid #3a4a6a;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: #3a4a6a;
                }
                QPushButton:pressed {
                    background: #22304a;
                }
                """
            )
        else:
            # Blue-gray light mode
            light_palette = QPalette()
            light_palette.setColor(QPalette.Window, QColor('#f4f7fb'))
            light_palette.setColor(QPalette.WindowText, QColor('#222b3a'))
            light_palette.setColor(QPalette.Base, QColor('#eaf0fa'))
            light_palette.setColor(QPalette.AlternateBase, QColor('#f4f7fb'))
            light_palette.setColor(QPalette.ToolTipBase, QColor('#f4f7fb'))
            light_palette.setColor(QPalette.ToolTipText, QColor('#222b3a'))
            light_palette.setColor(QPalette.Text, QColor('#222b3a'))
            light_palette.setColor(QPalette.Button, QColor('#eaf0fa'))
            light_palette.setColor(QPalette.ButtonText, QColor('#222b3a'))
            light_palette.setColor(QPalette.BrightText, QColor('#3a7bd5'))
            light_palette.setColor(QPalette.Link, QColor('#3a7bd5'))
            light_palette.setColor(QPalette.Highlight, QColor('#3a7bd5'))
            light_palette.setColor(QPalette.HighlightedText, QColor('#222b3a'))
            light_palette.setColor(QPalette.Light, QColor('#3a7bd5'))
            light_palette.setColor(QPalette.Mid, QColor('#b0bed9'))
            light_palette.setColor(QPalette.Midlight, QColor('#eaf0fa'))
            light_palette.setColor(QPalette.Dark, QColor('#b0bed9'))
            light_palette.setColor(QPalette.Shadow, QColor('#b0bed9'))
            app.setPalette(light_palette)
            self._set_scoreboard_text_color('#222b3a')
            app.setStyleSheet("""
                QMenu {
                    background-color: #eaf0fa;
                    color: #222b3a;
                    border: 1px solid #b0bed9;
                    border-radius: 8px;
                    padding: 4px;
                }
                QMenu::item:selected {
                    background: #3a7bd5;
                    color: white;
                }
            """
            )
            self.show_last_move_btn.setStyleSheet(
                """
                QPushButton {
                    padding: 6px 18px;
                    background: #eaf0fa;
                    color: #222b3a;
                    border: 1px solid #b0bed9;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: #dbe7f6;
                }
                QPushButton:pressed {
                    background: #b0bed9;
                }
                """
            )

    def _set_scoreboard_text_color(self, color):
        self.scoreboard.setStyleSheet(f"""
            QTableWidget {{
                border: none;
                gridline-color: #888;
                background: transparent;
            }}
            QTableWidget::item {{
                border: 1px solid #888;
                padding: 6px;
                background: transparent;
                color: {color};
            }}
        """)

    def is_system_dark_mode(self):
        # Simple heuristic: check palette background color
        app = QApplication.instance()
        return app.palette().color(QPalette.Window).value() < 128

def main():
    app = QApplication(sys.argv)
    game = DotsAndBoxesGame()
    game.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
