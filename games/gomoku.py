import sys
import os
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QUrl, QTimer
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
from qfluentwidgets import SubtitleLabel, PrimaryPushButton, CardWidget, PushButton, TextEdit, LineEdit, InfoBar, InfoBarPosition, ProgressBar

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class GomokuBoard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(500, 500)
        self.grid_size = 15
        self.cell_size = 500 // (self.grid_size + 1)
        self.board = [[0] * self.grid_size for _ in range(self.grid_size)]
        self.is_my_turn = False
        self.my_color = 0 
        self.skill_mode = None 
        self.selected_pos = None 
        self.swap_first_pos = None
        self.last_placed_piece = None
        self.banned_points = {} 
        self.highlights = [] 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(QColor(230, 200, 160))
        painter.drawRect(self.rect())
        
        pen = QPen(Qt.GlobalColor.black, 1)
        painter.setPen(pen)
        for i in range(self.grid_size):
            painter.drawLine(self.cell_size, (i+1)*self.cell_size, 
                             self.grid_size*self.cell_size, (i+1)*self.cell_size)
            painter.drawLine((i+1)*self.cell_size, self.cell_size, 
                             (i+1)*self.cell_size, self.grid_size*self.cell_size)
                             
        star_points = [(3, 3), (11, 3), (3, 11), (11, 11), (7, 7)]
        painter.setBrush(Qt.GlobalColor.black)
        for r, c in star_points:
            x = (c + 1) * self.cell_size
            y = (r + 1) * self.cell_size
            painter.drawEllipse(QPoint(x, y), 3, 3)
            
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                x = (c + 1) * self.cell_size
                y = (r + 1) * self.cell_size
                
                if self.board[r][c] != 0:
                    if self.board[r][c] == 1:
                        painter.setBrush(Qt.GlobalColor.black)
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawEllipse(QPoint(x, y), self.cell_size//2 - 2, self.cell_size//2 - 2)
                    elif self.board[r][c] == 2:
                        painter.setBrush(Qt.GlobalColor.white)
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawEllipse(QPoint(x, y), self.cell_size//2 - 2, self.cell_size//2 - 2)
                    elif self.board[r][c] == 3:
                        painter.setBrush(QColor(100, 100, 100))
                        painter.setPen(Qt.GlobalColor.black)
                        painter.drawRect(x - self.cell_size//2 + 2, y - self.cell_size//2 + 2, self.cell_size - 4, self.cell_size - 4)
                        painter.setPen(QPen(Qt.GlobalColor.white, 2))
                        painter.drawLine(x - self.cell_size//2 + 6, y - self.cell_size//2 + 6, x + self.cell_size//2 - 6, y + self.cell_size//2 - 6)
                        painter.drawLine(x + self.cell_size//2 - 6, y - self.cell_size//2 + 6, x - self.cell_size//2 + 6, y + self.cell_size//2 - 6)
                    
                if self.selected_pos == (r, c) or self.swap_first_pos == (r, c):
                    painter.setPen(QPen(Qt.GlobalColor.red, 3))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawEllipse(QPoint(x, y), self.cell_size//2, self.cell_size//2)
                    
                if (r, c) in self.banned_points:
                    painter.setPen(QPen(Qt.GlobalColor.red, 2))
                    painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                    painter.drawText(x - 8, y + 6, "禁")
                    
        for r, c in self.highlights:
            x = (c + 1) * self.cell_size
            y = (r + 1) * self.cell_size
            painter.setPen(QPen(Qt.GlobalColor.yellow, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPoint(x, y), self.cell_size//2, self.cell_size//2)
            
        if self.last_placed_piece:
            r, c = self.last_placed_piece
            x = (c + 1) * self.cell_size
            y = (r + 1) * self.cell_size
            painter.setPen(QPen(Qt.GlobalColor.red, 2))
            painter.setBrush(Qt.GlobalColor.red)
            painter.drawEllipse(QPoint(x, y), 3, 3)

    def mousePressEvent(self, event):
        if not self.is_my_turn:
            return
        pos = event.pos()
        col = round(pos.x() / self.cell_size) - 1
        row = round(pos.y() / self.cell_size) - 1
        if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
            interface = self.parent()
            
            if self.skill_mode is None:
                if self.board[row][col] == 0:
                    if (row, col) in self.banned_points and self.banned_points[(row, col)]["color"] == self.my_color:
                        InfoBar.warning("禁手", "此处被对方禁手，无法落子", parent=interface)
                        return
                    interface.network.send_message({"type": "game_action", "action": "place", "row": row, "col": col, "color": self.my_color})
            elif self.skill_mode == "remove":
                if self.board[row][col] in [1, 2] and (row, col) != self.last_placed_piece:
                    interface.commit_skill("remove")
                    interface.network.send_message({"type": "game_action", "action": "skill_remove", "row": row, "col": col})
                    self.skill_mode = None
            elif self.skill_mode == "swap":
                if self.board[row][col] in [1, 2] and (row, col) != self.last_placed_piece:
                    if not self.swap_first_pos:
                        self.swap_first_pos = (row, col)
                        self.update()
                    elif self.swap_first_pos != (row, col):
                        r1, c1 = self.swap_first_pos
                        interface.commit_skill("swap")
                        interface.network.send_message({"type": "game_action", "action": "skill_swap", "r1": r1, "c1": c1, "r2": row, "c2": col})
                        self.skill_mode = None
                        self.swap_first_pos = None
            elif self.skill_mode == "move":
                if not self.selected_pos:
                    if self.board[row][col] == self.my_color and (row, col) != self.last_placed_piece:
                        self.selected_pos = (row, col)
                        self.update()
                else:
                    if self.board[row][col] == 0 and ((row, col) not in self.banned_points or self.banned_points[(row, col)]["color"] != self.my_color):
                        fr, fc = self.selected_pos
                        interface.commit_skill("move")
                        interface.network.send_message({"type": "game_action", "action": "skill_move", "from_r": fr, "from_c": fc, "to_r": row, "to_c": col})
                        self.skill_mode = None
                        self.selected_pos = None
                    elif self.board[row][col] == self.my_color and (row, col) != self.last_placed_piece:
                        self.selected_pos = (row, col)
                        self.update()
            elif self.skill_mode == "block":
                if self.board[row][col] == 0:
                    interface.commit_skill("block")
                    interface.network.send_message({"type": "game_action", "action": "skill_block", "row": row, "col": col})
                    self.skill_mode = None
            elif self.skill_mode == "ban":
                if self.board[row][col] == 0:
                    interface.commit_skill("ban")
                    interface.network.send_message({"type": "game_action", "action": "skill_ban", "row": row, "col": col, "target_color": 3 - self.my_color})
                    self.skill_mode = None
                    interface.status_label.setText("已使用禁手，请正常落子")

    def check_win(self, row, col, color):
        directions = [(1,0), (0,1), (1,1), (1,-1)]
        for dr, dc in directions:
            count = 1
            for step in (1, -1):
                r, c = row + step*dr, col + step*dc
                while 0 <= r < self.grid_size and 0 <= c < self.grid_size and self.board[r][c] == color:
                    count += 1
                    r += step*dr
                    c += step*dc
            if count >= 5:
                return True
        return False
        
    def check_open_three(self, row, col, color):
        directions = [(1,0), (0,1), (1,1), (1,-1)]
        open_threes = 0
        for dr, dc in directions:
            line = []
            for i in range(-4, 5):
                nr, nc = row + i*dr, col + i*dc
                if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                    line.append(self.board[nr][nc])
                else:
                    line.append(-1)
            s = "".join(str(x) if x in [0,1,2,3] else "W" for x in line)
            target = f"0{color}{color}{color}0"
            if target in s:
                open_threes += 1
        return open_threes > 0
        
    def get_best_moves(self, color, count=3):
        scores = []
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.board[r][c] == 0 and ((r, c) not in self.banned_points or self.banned_points[(r, c)]["color"] != color):
                    score = self.evaluate_point(r, c, color)
                    scores.append((score, r, c))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [(r, c) for s, r, c in scores[:count]]

    def evaluate_point(self, r, c, color):
        score = 0
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for dr, dc in directions:
            my_count = 1
            my_open = 0
            for step in [1, -1]:
                for i in range(1, 5):
                    nr, nc = r + step*i*dr, c + step*i*dc
                    if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                        if self.board[nr][nc] == color:
                            my_count += 1
                        elif self.board[nr][nc] == 0:
                            my_open += 1
                            break
                        else:
                            break
                    else:
                        break
            if my_count >= 5: score += 100000
            elif my_count == 4 and my_open > 0: score += 10000
            elif my_count == 3 and my_open == 2: score += 1000
            elif my_count == 3 and my_open == 1: score += 100
            elif my_count == 2 and my_open == 2: score += 10
            
            op_color = 3 - color
            op_count = 1
            op_open = 0
            for step in [1, -1]:
                for i in range(1, 5):
                    nr, nc = r + step*i*dr, c + step*i*dc
                    if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                        if self.board[nr][nc] == op_color:
                            op_count += 1
                        elif self.board[nr][nc] == 0:
                            op_open += 1
                            break
                        else:
                            break
                    else:
                        break
            if op_count >= 4 and op_open > 0: score += 8000
            elif op_count == 3 and op_open == 2: score += 800
            elif op_count == 2 and op_open == 2: score += 8
        return score

class GomokuInterface(QWidget):
    def __init__(self, network, parent=None):
        super().__init__(parent)
        self.network = network
        self.setObjectName("GomokuInterface")
        
        self.main_layout = QHBoxLayout(self)
        self.board = GomokuBoard(self)
        self.main_layout.addWidget(self.board)
        
        self.panel = CardWidget(self)
        self.panel_layout = QVBoxLayout(self.panel)
        
        self.title = SubtitleLabel("技能版五子棋", self)
        self.status_label = SubtitleLabel("等待玩家加入...", self)
        
        self.timer_bar = ProgressBar(self)
        self.timer_bar.setRange(0, 15)
        self.timer_bar.setValue(15)
        self.timer_bar.setTextVisible(True)
        self.timer_bar.setFormat("倒计时: %v s")
        self.timer_bar.setFixedHeight(20)
        self.timer_bar.hide()
        
        self.score_label = QLabel("计分板: 暂无数据", self)
        self.score_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        self.skills_layout = QGridLayout()
        self.skill_btns = {}
        self.skill_limits = {
            "remove": 2, "swap": 2, "move": 2, "block": 1,
            "see_through": 1, "backtrack": 1, "freeze": 1, "ban": 1
        }
        self.skill_names = {
            "remove": "消除", "swap": "交换", "move": "移动", "block": "阻挡",
            "see_through": "透视", "backtrack": "回溯", "freeze": "冻结", "ban": "禁手"
        }
        self.skill_descs = {
            "remove": "移除任意棋子(非刚落下)",
            "swap": "交换两棋子(非刚落下)",
            "move": "移动己方棋子(单局2次)",
            "block": "放置永久障碍(占回合)",
            "see_through": "高亮对方下步可能点位(不占回合)",
            "backtrack": "撤销对方上步并原位禁手(占回合)",
            "freeze": "冻结对方下回合技能(不占回合)",
            "ban": "禁下指定空位3回合(不占回合)"
        }
        self.skill_inventory = {s: 0 for s in self.skill_limits}
        self.skill_used = {s: 0 for s in self.skill_limits}
        
        skills = list(self.skill_limits.keys())
        for i, sk_id in enumerate(skills):
            btn = PushButton(self.skill_names[sk_id], self)
            btn.clicked.connect(lambda checked, s=sk_id: self.activate_skill(s))
            self.skill_btns[sk_id] = btn
            self.skills_layout.addWidget(btn, i // 2, i % 2)
            
        self.chat_display = TextEdit(self)
        self.chat_display.setReadOnly(True)
        self.chat_display.setFixedHeight(120)
        
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
        
        self.panel_layout.addWidget(self.title)
        self.panel_layout.addWidget(self.status_label)
        self.panel_layout.addWidget(self.timer_bar)
        self.panel_layout.addWidget(self.score_label)
        self.panel_layout.addWidget(QLabel("技能区:"))
        self.panel_layout.addLayout(self.skills_layout)
        self.panel_layout.addStretch(1)
        self.panel_layout.addWidget(QLabel("房间聊天:"))
        self.panel_layout.addWidget(self.chat_display)
        self.panel_layout.addLayout(self.chat_input_layout)
        self.panel_layout.addWidget(self.play_again_btn)
        self.panel_layout.addWidget(self.leave_btn)
        
        self.main_layout.addWidget(self.panel)
        
        self.network.message_received.connect(self.handle_network_message)
        
        self.room_info = {}
        self.my_role = "" 
        self.player_scores = {}
        self.is_frozen = False
        self.next_turn_frozen = False
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_tick)
        self.time_left = 0
        
    def on_timer_tick(self):
        if self.time_left > 0:
            self.time_left -= 1
            self.timer_bar.setValue(self.time_left)
            if self.time_left == 0 and self.board.is_my_turn:
                self.auto_random_place()
                
    def auto_random_place(self):
        import random
        # 寻找可落子的地方
        valid_spots = []
        for r in range(self.board.grid_size):
            for c in range(self.board.grid_size):
                if self.board.board[r][c] == 0:
                    if (r, c) not in self.board.banned_points or self.board.banned_points[(r, c)]["color"] != self.board.my_color:
                        valid_spots.append((r, c))
        if valid_spots:
            r, c = random.choice(valid_spots)
            self.network.send_message({"type": "game_action", "action": "place", "row": r, "col": c, "color": self.board.my_color})
            
    def update_scoreboard(self):
        players = self.room_info.get("players", [])
        if len(players) == 2:
            p1, p2 = players[0], players[1]
            s1 = self.player_scores.get(p1, 0)
            s2 = self.player_scores.get(p2, 0)
            self.score_label.setText(f"计分板: {p1} ({s1}) - {p2} ({s2})")
        elif len(players) == 1:
            p1 = players[0]
            s1 = self.player_scores.get(p1, 0)
            self.score_label.setText(f"计分板: {p1} ({s1}) - 等待加入...")
        else:
            self.score_label.setText("计分板: 等待玩家加入...")

    def handle_game_over(self, winner_color):
        self.timer.stop()
        self.timer_bar.hide()
        self.board.is_my_turn = False
        self.update_skill_buttons()
        
        winner_name = None
        if winner_color == 1:
            winner = "黑子"
            winner_name = self.current_black
        elif winner_color == 2:
            winner = "白子"
            winner_name = self.current_white
        else:
            winner = "平局"
            
        if winner_name:
            self.player_scores[winner_name] = self.player_scores.get(winner_name, 0) + 1
            
        self.update_scoreboard()
        
        if winner_color != 0:
            self.status_label.setText(f"{winner} ({winner_name}) 获胜！")
        else:
            self.status_label.setText("双方同时达成连五，平局！")
            
        if self.my_role == "player":
            self.play_again_btn.show()
            self.play_again_btn.setEnabled(True)
            self.play_again_btn.setText("再来一局")

    def play_sound(self, sound_type):
        import winsound
        sound_file = get_resource_path(f"assets/{sound_type}.wav")
        if os.path.exists(sound_file):
            winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)

    def leave_room(self):
        self.network.send_message({"type": "leave_room"})
        self.network.message_received.emit({"type": "_local_leave_room"})

    def reset_game(self):
        self.timer.stop()
        self.timer_bar.hide()
        self.board.board = [[0] * self.board.grid_size for _ in range(self.board.grid_size)]
        self.board.is_my_turn = False
        self.board.skill_mode = None
        self.board.selected_pos = None
        self.board.swap_first_pos = None
        self.board.last_placed_piece = None
        self.board.banned_points = {}
        self.board.highlights = []
        
        self.skill_inventory = {s: 0 for s in self.skill_limits}
        self.skill_used = {s: 0 for s in self.skill_limits}
        self.is_frozen = False
        self.next_turn_frozen = False
        
        self.play_again_btn.hide()
        self.board.update()
        self.update_skill_buttons()

    def send_chat(self):
        msg = self.chat_input.text().strip()
        if msg:
            self.network.send_message({"type": "chat", "msg": msg, "room_id": self.room_info.get("room_id", "")})
            self.chat_input.clear()

    def on_play_again(self):
        self.play_again_btn.setEnabled(False)
        self.play_again_btn.setText("等待对方同意...")
        self.network.send_message({"type": "game_action", "action": "play_again_request"})

    def activate_skill(self, skill_id):
        if not self.board.is_my_turn or self.is_frozen: return
        if self.skill_inventory[skill_id] <= 0: return
        if self.skill_used[skill_id] >= self.skill_limits[skill_id]: return

        if skill_id == "see_through":
            self.commit_skill("see_through")
            op_color = 3 - self.board.my_color
            best_moves = self.board.get_best_moves(op_color, 3)
            self.board.highlights = best_moves
            self.board.update()
            self.network.send_message({"type": "game_action", "action": "skill_see_through"})
            self.status_label.setText("已使用透视，请正常落子")
        elif skill_id == "backtrack":
            if not self.board.last_placed_piece:
                InfoBar.error("错误", "没有可撤销的落子", parent=self)
                return
            self.commit_skill("backtrack")
            r, c = self.board.last_placed_piece
            self.network.send_message({"type": "game_action", "action": "skill_backtrack", "row": r, "col": c, "target_color": 3 - self.board.my_color})
        elif skill_id == "freeze":
            self.commit_skill("freeze")
            self.network.send_message({"type": "game_action", "action": "skill_freeze"})
            self.status_label.setText("已冻结对方，请正常落子")
        else:
            self.board.skill_mode = skill_id
            self.board.selected_pos = None
            self.board.swap_first_pos = None
            self.status_label.setText(f"请使用技能：{self.skill_names[skill_id]}")
            self.update_skill_buttons()

    def commit_skill(self, skill_id):
        self.skill_inventory[skill_id] -= 1
        self.skill_used[skill_id] += 1
        self.play_sound("skill")
        self.update_skill_buttons()

    def draw_skill(self):
        available = [s for s in self.skill_limits.keys() if self.skill_used[s] + self.skill_inventory[s] < self.skill_limits[s]]
        if available:
            import random
            drawn = random.choice(available)
            self.skill_inventory[drawn] += 1
            self.chat_display.append(f"<i style='color:green'>你抽取到了技能：{self.skill_names[drawn]}</i>")
            self.update_skill_buttons()

    def update_skill_buttons(self):
        for sk_id, btn in self.skill_btns.items():
            inv = self.skill_inventory.get(sk_id, 0)
            used = self.skill_used.get(sk_id, 0)
            limit = self.skill_limits.get(sk_id, 0)
            
            btn.setText(f"{self.skill_names[sk_id]} ({inv})")
            btn.setToolTip(f"{self.skill_descs[sk_id]}\n已使用: {used}/{limit}")
            
            if not self.board.is_my_turn or self.is_frozen or inv <= 0 or used >= limit:
                btn.setEnabled(False)
            else:
                btn.setEnabled(True)

    def advance_turn(self, sender_color):
        to_remove = []
        for pt, data in self.board.banned_points.items():
            if data["color"] == sender_color:
                data["turns"] -= 1
                if data["turns"] <= 0:
                    to_remove.append(pt)
        for pt in to_remove:
            del self.board.banned_points[pt]
            
        self.time_left = 15
        self.timer_bar.setValue(self.time_left)
        self.timer_bar.show()
        if not self.timer.isActive():
            self.timer.start(1000)
            
        if sender_color == self.board.my_color:
            self.board.is_my_turn = False
            self.update_skill_buttons()
            self.status_label.setText("对手回合")
        else:
            self.board.is_my_turn = True
            self.is_frozen = self.next_turn_frozen
            self.next_turn_frozen = False
            self.board.highlights = []
            self.status_label.setText("你的回合 (黑子)" if self.board.my_color == 1 else "你的回合 (白子)")
            self.update_skill_buttons()

    def handle_network_message(self, msg: dict):
        msg_type = msg.get("type")
        
        if msg_type == "room_joined":
            self.room_info = msg.get("room_info", {})
            self.my_role = msg.get("role", "spectator")
            self.player_scores = {}
            self.chat_display.clear()
            self.reset_game()
            self.status_label.setText("已加入房间，等待中...")
            self.update_scoreboard()
            
        elif msg_type == "chat":
            room_id = msg.get("room_id")
            if room_id == self.room_info.get("room_id"):
                sender = msg.get("sender", "Unknown")
                text = msg.get("msg", "")
                self.chat_display.append(f"<b>{sender}:</b> {text}")
                
                if hasattr(self.network, 'username') and sender != self.network.username:
                    try:
                        import winsound
                        winsound.MessageBeep(winsound.MB_OK)
                        InfoBar.info(
                            title="新消息",
                            content=f"{sender}: {text}",
                            orient=Qt.Orientation.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP_RIGHT,
                            duration=3000,
                            parent=self
                        )
                    except Exception:
                        pass
                        
        elif msg_type == "room_update":
            self.room_info = msg.get("room_info", {})
            self.update_scoreboard()
            
        elif msg_type == "game_action":
            action = msg.get("action")
            if action == "play_again_status":
                count = msg.get("count")
                total = msg.get("total")
                self.status_label.setText(f"等待再来一局... ({count}/{total})")
            elif action == "start":
                self.play_sound("start")
                self.reset_game()
                black_player = msg.get("black")
                white_player = msg.get("white")
                self.current_black = black_player
                self.current_white = white_player
                self.update_scoreboard()
                
                self.time_left = 15
                self.timer_bar.setValue(self.time_left)
                self.timer_bar.show()
                self.timer.start(1000)
                
                my_name = getattr(self.network, 'username', '')
                if my_name == black_player:
                    self.board.my_color = 1
                    self.board.is_my_turn = True
                    self.status_label.setText("你的回合 (黑子)")
                    self.update_skill_buttons()
                elif my_name == white_player:
                    self.board.my_color = 2
                    self.board.is_my_turn = False
                    self.status_label.setText("对手回合 (白子)")
                    self.update_skill_buttons()
                else:
                    self.board.my_color = 0
                    self.board.is_my_turn = False
                    self.status_label.setText("观战中")
                    self.update_skill_buttons()
                    
            elif action == "place":
                self.play_sound("drop")
                r, c = msg.get("row"), msg.get("col")
                color = msg.get("color")
                self.board.board[r][c] = color
                self.board.last_placed_piece = (r, c)
                self.board.update()
                
                if color == self.board.my_color:
                    if self.board.check_open_three(r, c, color):
                        self.chat_display.append("<i style='color:orange'>触发活三连！额外抽取一个技能！</i>")
                        self.draw_skill()
                        
                if self.board.check_win(r, c, color):
                    self.play_sound("win")
                    self.handle_game_over(color)
                    return
                    
                self.advance_turn(color)
                
            elif action == "skill_remove":
                self.play_sound("skill")
                r, c = msg.get("row"), msg.get("col")
                self.board.board[r][c] = 0
                self.board.update()
                
                sender = msg.get("sender")
                sender_color = 1 if sender == self.current_black else 2
                self.advance_turn(sender_color)
                
            elif action == "skill_move":
                self.play_sound("skill")
                from_r, from_c = msg.get("from_r"), msg.get("from_c")
                to_r, to_c = msg.get("to_r"), msg.get("to_c")
                
                piece_color = self.board.board[from_r][from_c]
                self.board.board[from_r][from_c] = 0
                self.board.board[to_r][to_c] = piece_color
                self.board.update()
                
                if self.board.check_win(to_r, to_c, piece_color):
                    self.play_sound("win")
                    self.handle_game_over(piece_color)
                    return
                    
                self.advance_turn(piece_color)
                
            elif action == "skill_swap":
                self.play_sound("skill")
                r1, c1 = msg.get("r1"), msg.get("c1")
                r2, c2 = msg.get("r2"), msg.get("c2")
                
                color1 = self.board.board[r1][c1]
                color2 = self.board.board[r2][c2]
                self.board.board[r1][c1] = color2
                self.board.board[r2][c2] = color1
                self.board.update()
                
                win1 = self.board.check_win(r1, c1, color2)
                win2 = self.board.check_win(r2, c2, color1)
                
                if win1 or win2:
                    self.play_sound("win")
                    if win1 and win2:
                        self.handle_game_over(0)
                    elif win1:
                        self.handle_game_over(color2)
                    else:
                        self.handle_game_over(color1)
                    return
                    
                sender = msg.get("sender")
                sender_color = 1 if sender == self.current_black else 2
                self.advance_turn(sender_color)
                
            elif action == "skill_block":
                self.play_sound("skill")
                r, c = msg.get("row"), msg.get("col")
                self.board.board[r][c] = 3
                self.board.update()
                
                sender = msg.get("sender")
                sender_color = 1 if sender == self.current_black else 2
                self.advance_turn(sender_color)
                
            elif action == "skill_ban":
                self.play_sound("skill")
                r, c = msg.get("row"), msg.get("col")
                color = msg.get("target_color")
                self.board.banned_points[(r, c)] = {"color": color, "turns": 3}
                self.board.update()
                
            elif action == "skill_see_through":
                self.play_sound("skill")
                sender = msg.get("sender")
                self.chat_display.append(f"<i style='color:gray'>{sender} 使用了透视技能</i>")
                
            elif action == "skill_backtrack":
                self.play_sound("skill")
                r = msg.get("row")
                c = msg.get("col")
                target_color = msg.get("target_color")
                if r is not None and c is not None:
                    if self.board.board[r][c] in [1, 2]:
                        self.board.board[r][c] = 0
                        self.board.last_placed_piece = None
                    self.board.banned_points[(r, c)] = {"color": target_color, "turns": 1}
                    self.board.update()
                sender = msg.get("sender")
                self.chat_display.append(f"<i style='color:gray'>{sender} 使用了回溯技能</i>")
                sender_color = 1 if sender == self.current_black else 2
                self.advance_turn(sender_color)
                
            elif action == "skill_freeze":
                self.play_sound("skill")
                sender = msg.get("sender")
                if sender != getattr(self.network, 'username', ''):
                    self.next_turn_frozen = True
                self.chat_display.append(f"<i style='color:gray'>{sender} 使用了冻结技能</i>")