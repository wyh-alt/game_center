import sys
import os
import base64
from PyQt6.QtCore import Qt, QTimer, QPoint, QBuffer, QIODevice
from PyQt6.QtGui import QPainter, QPen, QPixmap, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QDialog, QPushButton
from qfluentwidgets import SubtitleLabel, PrimaryPushButton, CardWidget, PushButton, TextEdit, LineEdit, ProgressBar
from qfluentwidgets import FluentIcon as FIF, ToolButton

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class DrawingBoard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(500, 500)
        self.pixmap = QPixmap(500, 500)
        self.pixmap.fill(Qt.GlobalColor.white)
        self.drawing = False
        self.last_point = QPoint()
        self.can_draw = False
        self.current_color = QColor("#4A4A4A")
        self.history = []

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        
        # 绘制边框
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawRect(0, 0, 499, 499)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.can_draw:
            self.drawing = True
            self.last_point = event.pos()
            self.history.append(self.pixmap.copy())
            if len(self.history) > 20:
                self.history.pop(0)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton) and self.drawing and self.can_draw:
            painter = QPainter(self.pixmap)
            painter.setPen(QPen(self.current_color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawLine(self.last_point, event.pos())
            self.last_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.can_draw:
            self.drawing = False
            self.request_sync()

    def clear_board(self):
        if self.can_draw:
            self.history.append(self.pixmap.copy())
            if len(self.history) > 20:
                self.history.pop(0)
        self.pixmap.fill(Qt.GlobalColor.white)
        self.update()
        if self.can_draw:
            self.request_sync()

    def undo(self):
        if self.can_draw and self.history:
            self.pixmap = self.history.pop()
            self.update()
            self.request_sync()

    def request_sync(self):
        if self.can_draw and hasattr(self, 'sync_callback') and self.sync_callback:
            self.sync_callback(self.get_image_data())

    def get_image_data(self):
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.ReadWrite)
        self.pixmap.save(buffer, "PNG")
        return base64.b64encode(buffer.data()).decode('utf-8')

    def set_image_data(self, b64_data):
        if not b64_data: return
        img_data = base64.b64decode(b64_data)
        self.pixmap.loadFromData(img_data, "PNG")
        self.update()


class ColorButton(QPushButton):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_selected = False
        self.update_style()

    def set_selected(self, selected):
        self.is_selected = selected
        self.update_style()

    def update_style(self):
        border_color = "rgba(0, 0, 0, 0.4)" if self.is_selected else "transparent"
        border_width = "3px" if self.is_selected else "2px"
        self.setStyleSheet(f"""
            ColorButton {{
                background-color: {self.color.name()};
                border-radius: 12px;
                border: {border_width} solid {border_color};
            }}
            ColorButton:hover {{
                border: 3px solid rgba(0, 0, 0, 0.3);
            }}
            ColorButton:disabled {{
                background-color: {self.color.name()};
                opacity: 0.5;
            }}
        """)

class DrawGuessInterface(QWidget):
    def __init__(self, network, parent=None):
        super().__init__(parent)
        self.network = network
        self.setObjectName("DrawGuessInterface")
        
        self.main_layout = QHBoxLayout(self)
        
        # Left: Board
        self.board_card = CardWidget(self)
        self.board_layout = QVBoxLayout(self.board_card)
        
        self.game_title = SubtitleLabel("你画我猜 (2-8人)", self)
        self.game_status = SubtitleLabel("等待玩家加入...", self)
        
        self.timer_bar = ProgressBar(self)
        self.timer_bar.setRange(0, 60)
        self.timer_bar.setValue(60)
        self.timer_bar.setTextVisible(True)
        self.timer_bar.setFormat("倒计时: %v s")
        self.timer_bar.setFixedHeight(20)
        self.timer_bar.hide()
        
        self.board = DrawingBoard(self)
        self.board.sync_callback = self.on_sync_drawing
        
        self.tools_layout = QHBoxLayout()
        
        # 颜色选择按钮
        self.color_layout = QHBoxLayout()
        self.colors = [
            ("#4A4A4A", "深灰"),
            ("#D98880", "柔红"),
            ("#85C1E9", "淡蓝"),
            ("#7DCEA0", "薄荷绿"),
            ("#F7DC6F", "奶黄")
        ]
        self.color_btns = []
        for color, name in self.colors:
            btn = ColorButton(color, self)
            btn.setToolTip(name)
            btn.clicked.connect(lambda checked, c=color, b=btn: self.set_pen_color(c, b))
            self.color_layout.addWidget(btn)
            self.color_btns.append(btn)
            
        if self.color_btns:
            self.color_btns[0].set_selected(True)
            
        self.undo_btn = ToolButton(FIF.CANCEL, self)
        self.undo_btn.setToolTip("撤销 (Undo)")
        self.undo_btn.clicked.connect(self.board.undo)
        
        self.clear_btn = ToolButton(FIF.DELETE, self)
        self.clear_btn.setToolTip("清空画板 (Clear)")
        self.clear_btn.clicked.connect(self.board.clear_board)
        
        self.submit_btn = PrimaryPushButton("提交画作", self)
        self.submit_btn.clicked.connect(self.on_submit_drawing)
        
        self.tools_layout.addLayout(self.color_layout)
        self.tools_layout.addStretch(1)
        self.tools_layout.addWidget(self.undo_btn)
        self.tools_layout.addWidget(self.clear_btn)
        self.tools_layout.addWidget(self.submit_btn)
        
        self.board_layout.addWidget(self.game_title)
        self.board_layout.addWidget(self.game_status)
        self.board_layout.addWidget(self.timer_bar)
        self.board_layout.addWidget(self.board)
        self.board_layout.addLayout(self.tools_layout)
        
        self.main_layout.addWidget(self.board_card, 2)
        
        # Right: Panel
        self.panel = CardWidget(self)
        self.panel_layout = QVBoxLayout(self.panel)
        
        self.score_label = QLabel("计分板:", self)
        self.score_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.score_list = QListWidget(self)
        
        self.chat_display = TextEdit(self)
        self.chat_display.setReadOnly(True)
        self.chat_display.setFixedHeight(200)
        
        self.chat_input_layout = QHBoxLayout()
        self.chat_input = LineEdit(self)
        self.chat_input.setPlaceholderText("输入猜测词语或消息...")
        self.chat_input.returnPressed.connect(self.send_guess_or_chat)
        self.send_btn = PrimaryPushButton("发送", self)
        self.send_btn.clicked.connect(self.send_guess_or_chat)
        self.chat_input_layout.addWidget(self.chat_input)
        self.chat_input_layout.addWidget(self.send_btn)
        
        self.start_btn = PrimaryPushButton("开始游戏 (仅房主)", self)
        self.start_btn.clicked.connect(self.on_start_game)
        self.start_btn.hide()
        
        self.leave_btn = PushButton("离开房间", self)
        self.leave_btn.clicked.connect(self.leave_room)
        
        self.panel_layout.addWidget(self.score_label)
        self.panel_layout.addWidget(self.score_list)
        self.panel_layout.addWidget(QLabel("猜测与聊天:"))
        self.panel_layout.addWidget(self.chat_display)
        self.panel_layout.addLayout(self.chat_input_layout)
        self.panel_layout.addWidget(self.start_btn)
        self.panel_layout.addWidget(self.leave_btn)
        
        self.main_layout.addWidget(self.panel, 1)
        
        self.network.message_received.connect(self.handle_network_message)
        
        self.room_info = {}
        self.my_role = ""
        self.is_drawer = False
        self.game_phase = "waiting" # waiting, drawing, guessing
        self.correct_guessers = []
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_tick)
        self.time_left = 0

    def set_pen_color(self, color, btn=None):
        self.board.current_color = QColor(color)
        if btn:
            for b in self.color_btns:
                b.set_selected(b == btn)

    def on_sync_drawing(self, img_b64):
        if self.game_phase == "drawing" and self.is_drawer:
            self.network.send_message({"type": "game_action", "action": "sync_drawing", "image": img_b64})

    def reset_game(self):
        self.timer.stop()
        self.timer_bar.hide()
        self.board.clear_board()
        self.board.can_draw = False
        self.board.history.clear()
        self.undo_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.submit_btn.setEnabled(False)
        for btn in self.color_btns:
            btn.setEnabled(False)
        self.chat_input.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.game_phase = "waiting"

    def on_timer_tick(self):
        if self.time_left > 0:
            self.time_left -= 1
            self.timer_bar.setValue(self.time_left)
            
            if self.game_phase == "drawing" and self.is_drawer and self.board.drawing:
                if self.time_left % 2 == 0:
                    self.board.request_sync()
            
            if self.time_left in [1, 2, 3]:
                # 在猜词阶段，非画手且没猜对时，播放倒计时；在画画阶段，画手播放倒计时
                my_name = getattr(self.network, 'username', '')
                if self.game_phase == "guessing" and not self.is_drawer and my_name not in self.correct_guessers:
                    self.play_sound("countdown")
                elif self.game_phase == "drawing" and self.is_drawer:
                    self.play_sound("countdown")
                    
            if self.time_left == 0:
                if self.game_phase == "drawing" and self.is_drawer:
                    self.on_submit_drawing()
                elif self.game_phase == "guessing" and self.is_drawer:
                    self.network.send_message({"type": "game_action", "action": "end_round_request"})

    def send_guess_or_chat(self):
        msg = self.chat_input.text().strip()
        if msg:
            if self.game_phase == "guessing" and not self.is_drawer:
                self.network.send_message({"type": "game_action", "action": "guess", "word": msg})
            else:
                self.network.send_message({"type": "chat", "msg": msg, "room_id": self.room_info.get("room_id", "")})
            self.chat_input.clear()

    def on_submit_drawing(self):
        if self.game_phase == "drawing" and self.is_drawer:
            img_b64 = self.board.get_image_data()
            self.network.send_message({"type": "game_action", "action": "submit_drawing", "image": img_b64})
            self.board.can_draw = False
            self.undo_btn.setEnabled(False)
            self.clear_btn.setEnabled(False)
            self.submit_btn.setEnabled(False)
            for btn in self.color_btns:
                btn.setEnabled(False)
            self.game_status.setText("画作已提交，等待大家猜词...")

    def on_start_game(self):
        self.network.send_message({"type": "game_action", "action": "request_start"})

    def leave_room(self):
        self.network.send_message({"type": "leave_room"})
        self.network.message_received.emit({"type": "_local_leave_room"})

    def play_sound(self, sound_type):
        import winsound
        sound_file = get_resource_path(f"assets/{sound_type}.wav")
        if os.path.exists(sound_file):
            winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)

    def handle_network_message(self, msg: dict):
        msg_type = msg.get("type")
        
        if msg_type == "room_joined":
            self.room_info = msg.get("room_info", {})
            self.my_role = msg.get("role", "spectator")
            self.chat_display.clear()
            self.score_list.clear()
            for p in self.room_info.get("players", []):
                self.score_list.addItem(f"{p}: 0 分")
            self.reset_game()
            self.game_status.setText("已加入房间，等待中...")
            my_name = getattr(self.network, 'username', '')
            creator = self.room_info.get("creator", "")
            if my_name == creator:
                self.start_btn.show()
            else:
                self.start_btn.hide()
            
        elif msg_type == "chat":
            room_id = msg.get("room_id")
            if room_id == self.room_info.get("room_id"):
                sender = msg.get("sender", "Unknown")
                text = msg.get("msg", "")
                self.chat_display.append(f"<b>{sender}:</b> {text}")
                
        elif msg_type == "room_update":
            self.room_info = msg.get("room_info", {})
            if self.game_phase == "waiting":
                self.score_list.clear()
                for p in self.room_info.get("players", []):
                    self.score_list.addItem(f"{p}: 0 分")
            
        elif msg_type == "game_action":
            action = msg.get("action")
            if action == "start_round":
                self.play_sound("start")
                self.reset_game()
                self.start_btn.hide()
                drawer = msg.get("drawer")
                word = msg.get("word")
                scores = msg.get("scores", {})
                self.correct_guessers = []
                
                self.score_list.clear()
                for p, s in scores.items():
                    self.score_list.addItem(f"{p}: {s} 分")
                    
                self.game_phase = "drawing"
                self.board.clear_board()
                self.chat_display.append(f"<i style='color:blue'>--- 新的一轮开始，画手是 {drawer} ---</i>")
                
                my_name = getattr(self.network, 'username', '')
                if my_name == drawer:
                    self.is_drawer = True
                    self.board.can_draw = True
                    self.undo_btn.setEnabled(True)
                    self.clear_btn.setEnabled(True)
                    self.submit_btn.setEnabled(True)
                    for btn in self.color_btns:
                        btn.setEnabled(True)
                    self.chat_input.setEnabled(True) # Drawer can still chat
                    self.send_btn.setEnabled(True)
                    self.game_status.setText(f"你的回合，请画出: 【{word}】")
                    
                    self.time_left = 60
                    self.timer_bar.setRange(0, 60)
                    self.timer_bar.setValue(60)
                    self.timer_bar.show()
                    self.timer.start(1000)
                else:
                    self.is_drawer = False
                    self.board.can_draw = False
                    self.undo_btn.setEnabled(False)
                    self.clear_btn.setEnabled(False)
                    self.submit_btn.setEnabled(False)
                    for btn in self.color_btns:
                        btn.setEnabled(False)
                    self.chat_input.setEnabled(True)
                    self.send_btn.setEnabled(True)
                    self.game_status.setText(f"等待 {drawer} 作画...")
                    
                    self.timer_bar.hide()
                    self.timer.stop()
                    
            elif action == "sync_drawing":
                if not self.is_drawer and self.game_phase == "drawing":
                    self.board.set_image_data(msg.get("image"))
                    
            elif action == "submit_drawing":
                self.game_phase = "guessing"
                self.board.set_image_data(msg.get("image"))
                self.play_sound("drop")
                
                if self.is_drawer:
                    self.time_left = 30
                    self.timer_bar.setRange(0, 30)
                    self.timer_bar.setValue(30)
                    self.timer_bar.show()
                    self.timer.start(1000)
                else:
                    self.game_status.setText("画作已提交，请开始猜词！")
                    self.time_left = 30
                    self.timer_bar.setRange(0, 30)
                    self.timer_bar.setValue(30)
                    self.timer_bar.show()
                    self.timer.start(1000)
                    
            elif action == "player_guessed_correctly":
                player = msg.get("player")
                self.play_sound("win")
                self.correct_guessers.append(player)
                self.chat_display.append(f"<b style='color:green'>{player} 猜对了！</b>")
                
                my_name = getattr(self.network, 'username', '')
                if my_name == player:
                    self.chat_input.setEnabled(False)
                    self.send_btn.setEnabled(False)
                    self.game_status.setText("恭喜你猜对了，等待其他玩家...")
                    
                # 检查是否所有人都猜对了，如果是则房主/画手立刻发送结算请求
                if self.is_drawer and len(self.correct_guessers) >= len(self.room_info.get("players", [])) - 1:
                    self.timer.stop()
                    self.on_timer_tick() # trigger round end
                    
            elif action == "round_end":
                self.timer.stop()
                self.timer_bar.hide()
                self.game_phase = "waiting"
                word = msg.get("word")
                scores = msg.get("scores", {})
                round_scores = msg.get("round_scores", {})
                drawer = msg.get("drawer", "未知")
                
                self.chat_display.append(f"<i style='color:purple'>回合结束！正确答案是: 【{word}】</i>")
                self.game_status.setText(f"回合结束！答案是: 【{word}】")
                
                self.score_list.clear()
                for p, s in scores.items():
                    self.score_list.addItem(f"{p}: {s} 分")
                    
                # 弹窗显示本轮得分
                dialog = QDialog(self)
                dialog.setWindowTitle("本轮得分情况")
                dialog.setFixedSize(300, 400)
                layout = QVBoxLayout(dialog)
                layout.addWidget(SubtitleLabel(f"本轮答案: 【{word}】", dialog))
                layout.addWidget(QLabel(f"画手: {drawer}", dialog))
                
                score_list = QListWidget(dialog)
                for p, s in round_scores.items():
                    score_list.addItem(f"{p}: +{s} 分")
                layout.addWidget(score_list)
                
                # 5秒后自动关闭弹窗
                QTimer.singleShot(5000, dialog.accept)
                dialog.exec()
                    
            elif action == "game_over":
                self.timer.stop()
                self.timer_bar.hide()
                self.game_phase = "waiting"
                scores = msg.get("scores", {})
                
                self.chat_display.append("<b style='color:red'>--- 游戏结束 ---</b>")
                self.game_status.setText("游戏结束！")
                
                self.score_list.clear()
                for p, s in scores.items():
                    self.score_list.addItem(f"{p}: {s} 分")
                    
                # 弹窗显示最终积分排行榜
                dialog = QDialog(self)
                dialog.setWindowTitle("游戏结束 - 积分排行榜")
                dialog.setFixedSize(300, 400)
                layout = QVBoxLayout(dialog)
                layout.addWidget(SubtitleLabel("最终排行榜", dialog))
                
                score_list = QListWidget(dialog)
                sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                for i, (p, s) in enumerate(sorted_scores):
                    rank = i + 1
                    item_text = f"第 {rank} 名: {p} ({s} 分)"
                    if rank == 1:
                        item_text = "🏆 " + item_text
                    score_list.addItem(item_text)
                layout.addWidget(score_list)
                
                my_name = getattr(self.network, 'username', '')
                creator = self.room_info.get("creator", "")
                
                if my_name == creator:
                    btn_layout = QHBoxLayout()
                    play_again_btn = PrimaryPushButton("再来一局", dialog)
                    close_btn = PushButton("确定", dialog)
                    
                    def on_play_again_clicked():
                        dialog.accept()
                        self.on_start_game()
                        
                    play_again_btn.clicked.connect(on_play_again_clicked)
                    close_btn.clicked.connect(dialog.accept)
                    
                    btn_layout.addWidget(play_again_btn)
                    btn_layout.addWidget(close_btn)
                    layout.addLayout(btn_layout)
                else:
                    close_btn = PrimaryPushButton("确定", dialog)
                    close_btn.clicked.connect(dialog.accept)
                    layout.addWidget(close_btn)
                    
                dialog.exec()
                    
                if my_name == creator:
                    self.start_btn.show()
                    self.start_btn.setText("再来一局")
