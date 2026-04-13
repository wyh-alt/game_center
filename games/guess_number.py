import sys
import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import SubtitleLabel, PrimaryPushButton, CardWidget, PushButton, TextEdit, LineEdit, SpinBox, ProgressBar

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class GuessNumberInterface(QWidget):
    def __init__(self, network, parent=None):
        super().__init__(parent)
        self.network = network
        self.setObjectName("GuessNumberInterface")
        
        self.main_layout = QHBoxLayout(self)
        
        # 左侧游戏区
        self.game_card = CardWidget(self)
        self.game_layout = QVBoxLayout(self.game_card)
        
        self.game_title = SubtitleLabel("猜数字 (1-100)", self)
        self.game_status = SubtitleLabel("等待玩家加入...", self)
        
        self.timer_bar = ProgressBar(self)
        self.timer_bar.setRange(0, 60)
        self.timer_bar.setValue(60)
        self.timer_bar.setTextVisible(True)
        self.timer_bar.setFormat("倒计时: %v s")
        self.timer_bar.setFixedHeight(20)
        self.timer_bar.hide()
        
        # 出题区
        self.think_layout = QHBoxLayout()
        self.think_input = SpinBox(self)
        self.think_input.setRange(1, 100)
        self.think_input.setValue(50)
        self.think_btn = PrimaryPushButton("确定数字", self)
        self.think_btn.clicked.connect(self.on_think)
        self.think_layout.addWidget(QLabel("想一个数字:"))
        self.think_layout.addWidget(self.think_input)
        self.think_layout.addWidget(self.think_btn)
        
        # 猜题区
        self.guess_layout = QHBoxLayout()
        self.guess_input = SpinBox(self)
        self.guess_input.setRange(1, 100)
        self.guess_input.setValue(50)
        self.guess_btn = PrimaryPushButton("猜!", self)
        self.guess_btn.clicked.connect(self.on_guess)
        self.guess_layout.addWidget(QLabel("猜数字:"))
        self.guess_layout.addWidget(self.guess_input)
        self.guess_layout.addWidget(self.guess_btn)
        
        self.history_display = TextEdit(self)
        self.history_display.setReadOnly(True)
        
        self.game_layout.addWidget(self.game_title)
        self.game_layout.addWidget(self.game_status)
        self.game_layout.addWidget(self.timer_bar)
        self.game_layout.addLayout(self.think_layout)
        self.game_layout.addLayout(self.guess_layout)
        self.game_layout.addWidget(QLabel("游戏记录:"))
        self.game_layout.addWidget(self.history_display)
        
        self.main_layout.addWidget(self.game_card, 2)
        
        # 右侧面板 (聊天和操作)
        self.panel = CardWidget(self)
        self.panel_layout = QVBoxLayout(self.panel)
        
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
        
        self.play_again_btn = PrimaryPushButton("再来一局", self)
        self.play_again_btn.clicked.connect(self.on_play_again)
        self.play_again_btn.hide()
        
        self.leave_btn = PushButton("离开房间", self)
        self.leave_btn.clicked.connect(self.leave_room)
        
        self.panel_layout.addWidget(QLabel("房间聊天:"))
        self.panel_layout.addWidget(self.chat_display)
        self.panel_layout.addLayout(self.chat_input_layout)
        self.panel_layout.addStretch(1)
        self.panel_layout.addWidget(self.play_again_btn)
        self.panel_layout.addWidget(self.leave_btn)
        
        self.main_layout.addWidget(self.panel, 1)
        
        self.network.message_received.connect(self.handle_network_message)
        
        self.room_info = {}
        self.my_role = "" 
        self.is_thinker = False
        self.target_number = None
        self.guesser_name = ""
        self.thinker_name = ""

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_tick)
        self.time_left = 0

    def on_timer_tick(self):
        if self.time_left > 0:
            self.time_left -= 1
            self.timer_bar.setValue(self.time_left)
            if self.time_left == 0 and not self.is_thinker and self.my_role == "player":
                # Timeout, guesser loses
                self.network.send_message({
                    "type": "game_action",
                    "action": "timeout_lose",
                    "guesser": self.network.username
                })

    def set_think_enabled(self, enabled):
        self.think_input.setEnabled(enabled)
        self.think_btn.setEnabled(enabled)

    def set_guess_enabled(self, enabled):
        self.guess_input.setEnabled(enabled)
        self.guess_btn.setEnabled(enabled)

    def reset_game(self):
        self.timer.stop()
        self.timer_bar.hide()
        self.history_display.clear()
        self.set_think_enabled(False)
        self.set_guess_enabled(False)
        self.play_again_btn.hide()
        self.target_number = None

    def send_chat(self):
        msg = self.chat_input.text().strip()
        if msg:
            self.network.send_message({"type": "chat", "msg": msg, "room_id": self.room_info.get("room_id", "")})
            self.chat_input.clear()

    def on_play_again(self):
        self.play_again_btn.setEnabled(False)
        self.play_again_btn.setText("等待对方同意...")
        self.network.send_message({"type": "game_action", "action": "play_again_request"})

    def leave_room(self):
        self.network.send_message({"type": "leave_room"})
        self.network.message_received.emit({"type": "_local_leave_room"})

    def on_think(self):
        self.target_number = self.think_input.value()
        self.set_think_enabled(False)
        self.network.send_message({"type": "game_action", "action": "number_set"})
        self.history_display.append(f"<i>你设定了数字: {self.target_number}</i>")
        self.game_status.setText("等待对方猜测...")

    def on_guess(self):
        guess = self.guess_input.value()
        self.network.send_message({"type": "game_action", "action": "guess", "value": guess})

    def handle_game_over(self, winner_name):
        self.timer.stop()
        self.timer_bar.hide()
        self.set_guess_enabled(False)
        if self.my_role == "player":
            self.play_again_btn.show()
            self.play_again_btn.setEnabled(True)
            self.play_again_btn.setText("再来一局")

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
            self.game_status.setText("已加入房间，等待中...")
            
        elif msg_type == "chat":
            room_id = msg.get("room_id")
            if room_id == self.room_info.get("room_id"):
                sender = msg.get("sender", "Unknown")
                text = msg.get("msg", "")
                self.chat_display.append(f"<b>{sender}:</b> {text}")
                
        elif msg_type == "room_update":
            self.room_info = msg.get("room_info", {})
            
        elif msg_type == "game_action":
            action = msg.get("action")
            if action == "play_again_status":
                count = msg.get("count")
                total = msg.get("total")
                self.game_status.setText(f"等待再来一局... ({count}/{total})")
            elif action == "start":
                self.play_sound("start")
                self.reset_game()
                thinker = msg.get("thinker")
                guesser = msg.get("guesser")
                self.thinker_name = thinker
                self.guesser_name = guesser
                my_name = getattr(self.network, 'username', '')
                
                if my_name == thinker:
                    self.is_thinker = True
                    self.game_status.setText("你的回合: 请想一个1-100的数字")
                    self.set_think_enabled(True)
                    self.set_guess_enabled(False)
                elif my_name == guesser:
                    self.is_thinker = False
                    self.game_status.setText("等待对方出题...")
                    self.set_think_enabled(False)
                    self.set_guess_enabled(False)
                else:
                    self.game_status.setText("观战中")
            elif action == "number_set":
                self.time_left = 60
                self.timer_bar.setValue(self.time_left)
                self.timer_bar.show()
                self.timer.start(1000)
                
                if not self.is_thinker and self.my_role == "player":
                    self.game_status.setText("对方已出题，请开始猜数字！")
                    self.set_guess_enabled(True)
                elif self.my_role != "player":
                    self.history_display.append("<i>出题人已确定数字。</i>")
            elif action == "guess":
                self.play_sound("drop")
                sender = msg.get("sender")
                guess = msg.get("value")
                if self.is_thinker:
                    # Thinker checks the guess
                    if guess == self.target_number:
                        result = "正确"
                    elif guess > self.target_number:
                        result = "大了"
                    else:
                        result = "小了"
                    
                    self.network.send_message({
                        "type": "game_action",
                        "action": "guess_result",
                        "guess": guess,
                        "result": result,
                        "guesser": sender
                    })
            elif action == "timeout_lose":
                guesser = msg.get("guesser")
                self.history_display.append(f"<b>{guesser}</b> 猜题超时！")
                self.play_sound("skill")
                self.game_status.setText(f"游戏结束！{self.thinker_name} 获胜！")
                self.handle_game_over(self.thinker_name)
            elif action == "guess_result":
                guess = msg.get("guess")
                result = msg.get("result")
                guesser = msg.get("guesser")
                
                self.history_display.append(f"<b>{guesser}</b> 猜了 {guess} -> <b>{result}</b>")
                
                if result == "正确":
                    self.play_sound("win")
                    self.game_status.setText(f"游戏结束！{guesser} 猜对了！")
                    self.handle_game_over(guesser)
