from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import SubtitleLabel, CardWidget, PushButton

class ReversiBoard(QWidget):
    piece_placed = pyqtSignal(int, int) # row, col

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(500, 500)
        self.grid_size = 8
        self.cell_size = 500 // self.grid_size
        
        # 0=empty, 1=black, 2=white
        self.board = [[0] * self.grid_size for _ in range(self.grid_size)]
        self.init_board()
        
        self.is_my_turn = False
        self.my_color = 0 # 1 or 2
        
        self.valid_moves = []

    def init_board(self):
        self.board = [[0] * self.grid_size for _ in range(self.grid_size)]
        self.board[3][3] = 2
        self.board[4][4] = 2
        self.board[3][4] = 1
        self.board[4][3] = 1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景
        painter.setBrush(QColor(34, 139, 34)) # 绿色背景
        painter.drawRect(self.rect())
        
        # 网格
        pen = QPen(Qt.GlobalColor.black, 2)
        painter.setPen(pen)
        for i in range(self.grid_size + 1):
            painter.drawLine(0, i * self.cell_size, self.width(), i * self.cell_size)
            painter.drawLine(i * self.cell_size, 0, i * self.cell_size, self.height())
            
        # 绘制棋子和合法提示
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                center = QPoint(int((c + 0.5) * self.cell_size), int((r + 0.5) * self.cell_size))
                radius = self.cell_size // 2 - 4
                
                if self.board[r][c] != 0:
                    if self.board[r][c] == 1:
                        painter.setBrush(Qt.GlobalColor.black)
                    else:
                        painter.setBrush(Qt.GlobalColor.white)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(center, radius, radius)
                elif self.is_my_turn and (r, c) in self.valid_moves:
                    # 提示合法落子点
                    painter.setBrush(QColor(0, 0, 0, 50) if self.my_color == 1 else QColor(255, 255, 255, 100))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(center, radius//3, radius//3)

    def mousePressEvent(self, event):
        if not self.is_my_turn:
            return
            
        pos = event.pos()
        col = int(pos.x() // self.cell_size)
        row = int(pos.y() // self.cell_size)
        
        if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
            if (row, col) in self.valid_moves:
                self.piece_placed.emit(row, col)

    def update_valid_moves(self):
        self.valid_moves = []
        if self.my_color == 0:
            return
            
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.is_valid_move(r, c, self.my_color):
                    self.valid_moves.append((r, c))

    def is_valid_move(self, row, col, color):
        if self.board[row][col] != 0:
            return False
            
        opponent = 3 - color
        directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
        
        for dr, dc in directions:
            r, c = row + dr, col + dc
            found_opponent = False
            
            while 0 <= r < self.grid_size and 0 <= c < self.grid_size and self.board[r][c] == opponent:
                found_opponent = True
                r += dr
                c += dc
                
            if found_opponent and 0 <= r < self.grid_size and 0 <= c < self.grid_size and self.board[r][c] == color:
                return True
                
        return False

    def flip_pieces(self, row, col, color):
        self.board[row][col] = color
        opponent = 3 - color
        directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
        
        for dr, dc in directions:
            r, c = row + dr, col + dc
            pieces_to_flip = []
            
            while 0 <= r < self.grid_size and 0 <= c < self.grid_size and self.board[r][c] == opponent:
                pieces_to_flip.append((r, c))
                r += dr
                c += dc
                
            if pieces_to_flip and 0 <= r < self.grid_size and 0 <= c < self.grid_size and self.board[r][c] == color:
                for fr, fc in pieces_to_flip:
                    self.board[fr][fc] = color

    def count_pieces(self):
        black = sum(row.count(1) for row in self.board)
        white = sum(row.count(2) for row in self.board)
        return black, white

    def has_valid_move(self, color):
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.is_valid_move(r, c, color):
                    return True
        return False


class ReversiInterface(QWidget):
    def __init__(self, network, parent=None):
        super().__init__(parent)
        self.network = network
        self.setObjectName("ReversiInterface")
        
        self.main_layout = QHBoxLayout(self)
        
        # 左侧棋盘
        self.board = ReversiBoard(self)
        self.main_layout.addWidget(self.board)
        
        # 右侧面板
        self.panel = CardWidget(self)
        self.panel_layout = QVBoxLayout(self.panel)
        
        self.title = SubtitleLabel("黑白棋", self)
        self.status_label = SubtitleLabel("等待玩家加入...", self)
        
        self.score_label = SubtitleLabel("黑: 2 | 白: 2", self)
        
        self.leave_btn = PushButton("离开房间", self)
        self.leave_btn.clicked.connect(self.leave_room)
        
        self.panel_layout.addWidget(self.title)
        self.panel_layout.addWidget(self.status_label)
        self.panel_layout.addWidget(self.score_label)
        self.panel_layout.addStretch(1)
        self.panel_layout.addWidget(self.leave_btn)
        
        self.main_layout.addWidget(self.panel)
        
        # 连接信号
        self.board.piece_placed.connect(self.on_piece_placed)
        self.network.message_received.connect(self.handle_network_message)
        
        self.room_info = {}
        self.my_role = "" # "player" or "spectator"
        self.current_turn_color = 1

    def leave_room(self):
        self.network.send_message({"type": "leave_room"})
        self.network.message_received.emit({"type": "_local_leave_room"})

    def reset_game(self):
        self.board.init_board()
        self.board.is_my_turn = False
        self.current_turn_color = 1
        self.update_score()
        self.board.update_valid_moves()
        self.board.update()

    def update_score(self):
        b, w = self.board.count_pieces()
        self.score_label.setText(f"黑: {b} | 白: {w}")

    def on_piece_placed(self, row, col):
        self.network.send_message({
            "type": "game_action",
            "action": "place",
            "row": row,
            "col": col,
            "color": self.board.my_color
        })

    def handle_network_message(self, msg: dict):
        msg_type = msg.get("type")
        
        if msg_type == "room_joined":
            self.room_info = msg.get("room_info", {})
            if self.room_info.get("game_type") == "reversi":
                self.my_role = msg.get("role", "spectator")
                self.reset_game()
                self.status_label.setText("已加入房间，等待中...")
            
        elif msg_type == "room_update":
            self.room_info = msg.get("room_info", {})
                
        elif msg_type == "game_action":
            action = msg.get("action")
            if action == "start":
                black_player = msg.get("black")
                white_player = msg.get("white")
                my_name = getattr(self.network, 'username', '')
                
                self.reset_game()
                
                if my_name == black_player:
                    self.board.my_color = 1
                    self.board.is_my_turn = True
                    self.status_label.setText("你的回合 (黑子)")
                elif my_name == white_player:
                    self.board.my_color = 2
                    self.board.is_my_turn = False
                    self.status_label.setText("对手回合 (白子)")
                else:
                    self.board.my_color = 0
                    self.board.is_my_turn = False
                    self.status_label.setText("观战中")
                
                self.board.update_valid_moves()
                self.board.update()
                
            elif action == "place":
                r, c = msg.get("row"), msg.get("col")
                color = msg.get("color")
                
                self.board.flip_pieces(r, c, color)
                self.update_score()
                
                # Check game over or pass
                opponent_color = 3 - color
                if self.board.has_valid_move(opponent_color):
                    self.current_turn_color = opponent_color
                elif self.board.has_valid_move(color):
                    self.current_turn_color = color
                    # 如果我在观战或者不该我操作，通知一下有一方跳过了回合
                else:
                    # Game Over
                    self.current_turn_color = 0
                    b, w = self.board.count_pieces()
                    if b > w:
                        self.status_label.setText("黑子 获胜！")
                    elif w > b:
                        self.status_label.setText("白子 获胜！")
                    else:
                        self.status_label.setText("平局！")
                    self.board.is_my_turn = False
                    self.board.update()
                    return

                # Switch turn
                if self.my_role == "player":
                    if self.board.my_color == self.current_turn_color:
                        self.board.is_my_turn = True
                        self.status_label.setText("你的回合")
                    else:
                        self.board.is_my_turn = False
                        self.status_label.setText("对手回合")
                        
                self.board.update_valid_moves()
                self.board.update()
