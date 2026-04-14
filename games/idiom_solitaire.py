import sys
import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import SubtitleLabel, PrimaryPushButton, CardWidget, PushButton, TextEdit, LineEdit, ListWidget, ProgressBar

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class IdiomSolitaireInterface(QWidget):
    def __init__(self, network, parent=None):
        super().__init__(parent)
        self.network = network
        self.setObjectName("IdiomSolitaireInterface")
        
        self.main_layout = QHBoxLayout(self)
        
        # 左侧游戏区
        self.game_card = CardWidget(self)
        self.game_layout = QVBoxLayout(self.game_card)
        
        self.game_title = SubtitleLabel("成语接龙", self)
        self.game_status = SubtitleLabel("等待玩家加入...", self)
        
        self.timer_bar = ProgressBar(self)
        self.timer_bar.setRange(0, 30)
        self.timer_bar.setValue(30)
        self.timer_bar.setTextVisible(True)
        self.timer_bar.setFormat("倒计时: %v s")
        self.timer_bar.setFixedHeight(20)
        self.timer_bar.hide()
        
        self.idiom_layout = QHBoxLayout()
        self.idiom_input = LineEdit(self)
        self.idiom_input.setPlaceholderText("输入成语...")
        self.idiom_btn = PrimaryPushButton("提交", self)
        self.idiom_btn.clicked.connect(self.on_submit_idiom)
        self.idiom_input.returnPressed.connect(self.on_submit_idiom)
        self.idiom_layout.addWidget(self.idiom_input)
        self.idiom_layout.addWidget(self.idiom_btn)
        
        self.history_display = ListWidget(self)
        
        self.game_layout.addWidget(self.game_title)
        self.game_layout.addWidget(self.game_status)
        self.game_layout.addWidget(self.timer_bar)
        self.game_layout.addLayout(self.idiom_layout)
        self.game_layout.addWidget(QLabel("接龙记录:"))
        self.game_layout.addWidget(self.history_display)
        
        self.main_layout.addWidget(self.game_card, 2)
        
        # 右侧面板 (聊天和操作)
        self.panel = CardWidget(self)
        self.panel_layout = QVBoxLayout(self.panel)
        
        self.score_label = QLabel("计分板: 等待加入...", self)
        self.score_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        self.chat_display = TextEdit(self)
        self.chat_display.setReadOnly(True)
        self.chat_display.setFixedHeight(200)
        
        self.chat_input_layout = QHBoxLayout()
        self.chat_input = LineEdit(self)
        self.chat_input.setPlaceholderText("输入消息...")
        self.chat_input.returnPressed.connect(self.send_chat)
        self.send_btn = PrimaryPushButton("发送", self)
        self.send_btn.clicked.connect(self.send_chat)
        self.chat_input_layout.addWidget(self.chat_input)
        self.chat_input_layout.addWidget(self.send_btn)
        
        self.start_btn = PrimaryPushButton("开始游戏 (仅房主)", self)
        self.start_btn.clicked.connect(self.on_start_game)
        self.start_btn.hide()
        
        self.leave_btn = PushButton("离开房间", self)
        self.leave_btn.clicked.connect(self.leave_room)
        
        self.panel_layout.addWidget(self.score_label)
        self.panel_layout.addWidget(QLabel("房间聊天:"))
        self.panel_layout.addWidget(self.chat_display)
        self.panel_layout.addLayout(self.chat_input_layout)
        self.panel_layout.addStretch(1)
        self.panel_layout.addWidget(self.start_btn)
        self.panel_layout.addWidget(self.leave_btn)
        
        self.main_layout.addWidget(self.panel, 1)
        
        self.network.message_received.connect(self.handle_network_message)
        
        self.room_info = {}
        self.my_role = "" 
        self.current_turn = ""
        self.is_my_turn = False
        self.last_idiom = ""
        self.game_over = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_tick)
        self.time_left = 0

    def update_scoreboard(self):
        players = self.room_info.get("players", [])
        if players:
            self.score_label.setText(f"计分板: {', '.join(players)}")
        else:
            self.score_label.setText("计分板: 等待加入...")

    def on_timer_tick(self):
        if self.time_left > 0 and not self.game_over:
            self.time_left -= 1
            self.timer_bar.setValue(self.time_left)
            
            if self.time_left in [1, 2, 3] and self.is_my_turn:
                self.play_sound("countdown")
                
            if self.time_left == 0 and self.is_my_turn:
                # Timeout, this player loses
                self.network.send_message({
                    "type": "game_action",
                    "action": "timeout_lose",
                    "player": self.network.username
                })

    def set_input_enabled(self, enabled):
        self.idiom_input.setEnabled(enabled)
        self.idiom_btn.setEnabled(enabled)

    def reset_game(self):
        self.timer.stop()
        self.timer_bar.hide()
        self.history_display.clear()
        self.set_input_enabled(False)
        self.last_idiom = ""
        self.game_over = False

    def send_chat(self):
        msg = self.chat_input.text().strip()
        if msg:
            self.network.send_message({"type": "chat", "msg": msg, "room_id": self.room_info.get("room_id", "")})
            self.chat_input.clear()

    def leave_room(self):
        self.network.send_message({"type": "leave_room"})
        self.network.message_received.emit({"type": "_local_leave_room"})

    def on_start_game(self):
        # Notify server to start game
        self.network.send_message({"type": "game_action", "action": "request_start"})

    def on_submit_idiom(self):
        idiom = self.idiom_input.text().strip()
        if not idiom: return
        self.network.send_message({"type": "game_action", "action": "submit_idiom", "idiom": idiom})
        self.idiom_input.clear()

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
            self.reset_game()
            self.update_scoreboard()
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
            self.update_scoreboard()
            
        elif msg_type == "game_action":
            action = msg.get("action")
            if action == "start":
                self.play_sound("start")
                self.reset_game()
                self.start_btn.hide()
                self.current_turn = msg.get("current_turn")
                my_name = getattr(self.network, 'username', '')
                
                self.time_left = 30
                self.timer_bar.setValue(self.time_left)
                self.timer_bar.show()
                self.timer.start(1000)
                
                if my_name == self.current_turn:
                    self.is_my_turn = True
                    self.game_status.setText("你的回合: 请输入第一个成语")
                    self.set_input_enabled(True)
                else:
                    self.is_my_turn = False
                    self.game_status.setText(f"等待 {self.current_turn} 的回合...")
                    self.set_input_enabled(False)
            elif action == "submit_idiom":
                sender = msg.get("sender")
                idiom = msg.get("idiom")
                
                if not getattr(self, "idiom_validator", None):
                    try:
                        import idiom_validator
                        self.idiom_validator = idiom_validator
                    except ImportError:
                        self.idiom_validator = None

                # Check logic
                from pypinyin import pinyin, Style
                try:
                    import pypinyin
                except ImportError:
                    # Basic validation without pypinyin
                    is_valid = True
                    if self.idiom_validator and not self.idiom_validator.is_valid_idiom(idiom):
                        is_valid = False
                    elif self.last_idiom and idiom[0] != self.last_idiom[-1]:
                        is_valid = False
                        
                    if is_valid:
                        self.play_sound("drop")
                        self.history_display.addItem(f"{sender}: {idiom}")
                        self.last_idiom = idiom
                        
                        # Next turn calculation handled by server
                        self.network.send_message({"type": "game_action", "action": "idiom_valid", "idiom": idiom})
                    else:
                        if getattr(self.network, 'username', '') == sender:
                            self.play_sound("skill")
                            if self.idiom_validator and not self.idiom_validator.is_valid_idiom(idiom):
                                self.game_status.setText("接龙失败：不是有效的成语！")
                            else:
                                self.game_status.setText("接龙失败：首尾字不一致！")
                else:
                    is_valid = True
                    if self.idiom_validator and not self.idiom_validator.is_valid_idiom(idiom):
                        is_valid = False
                    elif self.last_idiom:
                        py1 = pinyin(self.last_idiom[-1], style=Style.NORMAL)[0][0]
                        py2 = pinyin(idiom[0], style=Style.NORMAL)[0][0]
                        if py1 != py2 and self.last_idiom[-1] != idiom[0]:
                            is_valid = False
                    
                    if is_valid:
                        self.play_sound("drop")
                        self.history_display.addItem(f"{sender}: {idiom}")
                        self.last_idiom = idiom
                        
                        if getattr(self.network, 'username', '') == sender:
                            self.network.send_message({"type": "game_action", "action": "idiom_valid", "idiom": idiom})
                    else:
                        if getattr(self.network, 'username', '') == sender:
                            self.play_sound("skill")
                            if self.idiom_validator and not self.idiom_validator.is_valid_idiom(idiom):
                                self.game_status.setText("接龙失败：不是有效的成语！")
                            else:
                                self.game_status.setText("接龙失败：首尾字/音不一致！")
                            
            elif action == "timeout_lose":
                player = msg.get("player")
                self.history_display.addItem(f"{player} 回答超时！")
                self.play_sound("skill")
                self.game_status.setText(f"游戏结束！{player} 超时判负！")
                self.game_over = True
                self.set_input_enabled(False)
                self.timer.stop()
                self.timer_bar.hide()
                
                my_name = getattr(self.network, 'username', '')
                creator = self.room_info.get("creator", "")
                if my_name == creator:
                    self.start_btn.show()
                    self.start_btn.setText("再来一局")
                    
            elif action == "next_turn":
                self.current_turn = msg.get("current_turn")
                my_name = getattr(self.network, 'username', '')
                
                self.time_left = 30
                self.timer_bar.setValue(self.time_left)
                self.timer_bar.show()
                self.timer.start(1000)
                
                if my_name == self.current_turn:
                    self.is_my_turn = True
                    self.game_status.setText(f"你的回合: 接 {self.last_idiom[-1]}")
                    self.set_input_enabled(True)
                else:
                    self.is_my_turn = False
                    self.game_status.setText(f"等待 {self.current_turn} 的回合...")
                    self.set_input_enabled(False)
