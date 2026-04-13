from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import SubtitleLabel, PushButton, CardWidget, LineEdit, TextEdit, PrimaryPushButton

class DrawBoard(QWidget):
    draw_line_signal = pyqtSignal(int, int, int, int) # x1, y1, x2, y2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(600, 450)
        self.pixmap = QPixmap(self.size())
        self.pixmap.fill(Qt.GlobalColor.white)
        
        self.can_draw = False
        self.last_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)

    def mousePressEvent(self, event):
        if self.can_draw and event.button() == Qt.MouseButton.LeftButton:
            self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.can_draw and (event.buttons() & Qt.MouseButton.LeftButton) and self.last_pos:
            current_pos = event.pos()
            
            # Draw locally
            self.draw_line(self.last_pos.x(), self.last_pos.y(), current_pos.x(), current_pos.y())
            
            # Emit signal to sync
            self.draw_line_signal.emit(self.last_pos.x(), self.last_pos.y(), current_pos.x(), current_pos.y())
            
            self.last_pos = current_pos

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_pos = None

    def draw_line(self, x1, y1, x2, y2):
        painter = QPainter(self.pixmap)
        pen = QPen(Qt.GlobalColor.black, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(x1, y1, x2, y2)
        self.update()

    def clear_board(self):
        self.pixmap.fill(Qt.GlobalColor.white)
        self.update()


class DrawInterface(QWidget):
    def __init__(self, network, parent=None):
        super().__init__(parent)
        self.network = network
        self.setObjectName("DrawInterface")
        
        self.main_layout = QHBoxLayout(self)
        
        # 左侧画板
        self.board_layout = QVBoxLayout()
        self.board = DrawBoard(self)
        self.word_label = SubtitleLabel("Waiting for game to start...", self)
        
        self.board_layout.addWidget(self.word_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.board_layout.addWidget(self.board)
        self.board_layout.addStretch(1)
        
        # 右侧聊天与控制面板
        self.panel = CardWidget(self)
        self.panel_layout = QVBoxLayout(self.panel)
        self.panel.setFixedWidth(250)
        
        self.title = SubtitleLabel("Draw & Guess", self)
        self.chat_display = TextEdit(self)
        self.chat_display.setReadOnly(True)
        
        self.chat_input = LineEdit(self)
        self.chat_input.setPlaceholderText("Guess here...")
        self.chat_input.returnPressed.connect(self.send_guess)
        
        self.leave_btn = PushButton("Leave Room", self)
        self.leave_btn.clicked.connect(self.leave_room)
        
        self.panel_layout.addWidget(self.title)
        self.panel_layout.addWidget(self.chat_display)
        self.panel_layout.addWidget(self.chat_input)
        self.panel_layout.addWidget(self.leave_btn)
        
        self.main_layout.addLayout(self.board_layout)
        self.main_layout.addWidget(self.panel)
        
        # 信号连接
        self.board.draw_line_signal.connect(self.on_draw_line)
        self.network.message_received.connect(self.handle_network_message)
        
        self.my_role = ""
        self.is_drawer = False
        
    def send_guess(self):
        text = self.chat_input.text().strip()
        if text:
            self.network.send_message({
                "type": "game_action",
                "action": "guess",
                "text": text
            })
            my_name = getattr(self.network, 'username', 'Me')
            self.chat_display.append(f"<b>{my_name}:</b> {text}")
            self.chat_input.clear()

    def on_draw_line(self, x1, y1, x2, y2):
        self.network.send_message({
            "type": "game_action",
            "action": "draw_line",
            "coords": [x1, y1, x2, y2]
        })

    def leave_room(self):
        self.network.send_message({"type": "leave_room"})
        self.network.message_received.emit({"type": "_local_leave_room"})

    def reset_game(self):
        self.board.clear_board()
        self.chat_display.clear()
        self.word_label.setText("Waiting for game to start...")
        self.board.can_draw = False

    def handle_network_message(self, msg: dict):
        msg_type = msg.get("type")
        
        if msg_type == "room_joined":
            room_info = msg.get("room_info", {})
            game_type = room_info.get("game_type", "")
            if game_type == "draw":
                self.my_role = msg.get("role", "spectator")
                self.reset_game()
            
        elif msg_type == "game_action":
            action = msg.get("action")
            if action == "start_draw":
                drawer = msg.get("drawer")
                word = msg.get("word")
                my_name = getattr(self.network, 'username', '')
                
                self.board.clear_board()
                self.chat_display.append("<b>System:</b> Game started!")
                
                if my_name == drawer:
                    self.is_drawer = True
                    self.board.can_draw = True
                    self.word_label.setText(f"Your turn to draw: {word}")
                else:
                    self.is_drawer = False
                    self.board.can_draw = False
                    # hide word length with underscores
                    hidden = " ".join(["_" for _ in word])
                    self.word_label.setText(f"{drawer} is drawing: {hidden}")
                    
            elif action == "draw_line":
                coords = msg.get("coords")
                if coords and len(coords) == 4:
                    self.board.draw_line(coords[0], coords[1], coords[2], coords[3])
                    
            elif action == "guess":
                sender = msg.get("sender", "Unknown")
                text = msg.get("text", "")
                self.chat_display.append(f"<b>{sender}:</b> {text}")
                
            elif action == "win_draw":
                winner = msg.get("winner")
                word = msg.get("word")
                self.chat_display.append(f"<b style='color:green;'>{winner} guessed the word: {word}!</b>")
                self.board.can_draw = False
