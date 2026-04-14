import sys
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import (FluentWindow, NavigationItemPosition, SubtitleLabel, 
                            LineEdit, PrimaryPushButton, TextEdit, ListWidget, 
                            CardWidget, PushButton, MessageBox, ComboBox,
                            InfoBar, InfoBarPosition, EditableComboBox)
import winsound
import json
import os
from qfluentwidgets import FluentIcon as FIF
from network import NetworkThread

HISTORY_FILE = "ip_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return ["127.0.0.1"]

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False)
    except:
        pass

class LobbyInterface(QWidget):
    def __init__(self, network: NetworkThread, parent=None):
        super().__init__(parent=parent)
        self.network = network
        self.setObjectName("LobbyInterface")
        
        # 布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)
        
        # --- 顶部连接区域 ---
        self.connect_card = CardWidget(self)
        self.connect_layout = QHBoxLayout(self.connect_card)
        self.connect_layout.setContentsMargins(15, 15, 15, 15)
        
        self.ip_input = EditableComboBox(self)
        self.ip_input.setPlaceholderText("服务器 IP (例如: 127.0.0.1)")
        self.ip_history = load_history()
        self.ip_input.addItems(self.ip_history)
        if self.ip_history:
            self.ip_input.setText(self.ip_history[0])
        
        self.name_input = LineEdit(self)
        self.name_input.setPlaceholderText("你的昵称")
        self.name_input.setText("玩家1")
        
        self.connect_btn = PrimaryPushButton("连接", self)
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        
        self.share_ip_btn = PushButton("分享我的IP地址", self)
        self.share_ip_btn.clicked.connect(self.on_share_ip_clicked)
        
        self.connect_layout.addWidget(self.ip_input)
        self.connect_layout.addWidget(self.name_input)
        self.connect_layout.addWidget(self.connect_btn)
        self.connect_layout.addWidget(self.share_ip_btn)
        
        self.main_layout.addWidget(self.connect_card)
        
        # --- 中部大厅区域 ---
        self.content_layout = QHBoxLayout()
        self.main_layout.addLayout(self.content_layout)
        
        # 房间列表
        self.room_card = CardWidget(self)
        self.room_layout = QVBoxLayout(self.room_card)
        self.room_label = SubtitleLabel("游戏房间", self)
        self.room_list = ListWidget(self)
        
        # 房间操作区
        self.room_action_layout = QHBoxLayout()
        self.game_combo = ComboBox(self)
        self.game_combo.addItems(["五子棋", "猜数字", "成语接龙", "你画我猜"])
        self.create_room_btn = PrimaryPushButton("创建房间", self)
        self.join_room_btn = PushButton("加入选中房间", self)
        
        self.create_room_btn.clicked.connect(self.on_create_room)
        self.join_room_btn.clicked.connect(self.on_join_room)
        
        self.room_action_layout.addWidget(self.game_combo)
        self.room_action_layout.addWidget(self.create_room_btn)
        self.room_action_layout.addWidget(self.join_room_btn)
        
        self.room_layout.addWidget(self.room_label)
        self.room_layout.addWidget(self.room_list)
        self.room_layout.addLayout(self.room_action_layout)
        
        # 聊天区域
        self.chat_card = CardWidget(self)
        self.chat_layout = QVBoxLayout(self.chat_card)
        self.chat_label = SubtitleLabel("大厅聊天", self)
        self.chat_display = TextEdit(self)
        self.chat_display.setReadOnly(True)
        
        self.chat_input_layout = QHBoxLayout()
        self.chat_input = LineEdit(self)
        self.chat_input.setPlaceholderText("输入消息...")
        self.chat_input.returnPressed.connect(self.send_chat)
        self.send_btn = PrimaryPushButton("发送", self)
        self.send_btn.clicked.connect(self.send_chat)
        
        self.chat_input_layout.addWidget(self.chat_input)
        self.chat_input_layout.addWidget(self.send_btn)
        
        self.chat_layout.addWidget(self.chat_label)
        self.chat_layout.addWidget(self.chat_display)
        self.chat_layout.addLayout(self.chat_input_layout)
        
        self.content_layout.addWidget(self.room_card, 2)
        self.content_layout.addWidget(self.chat_card, 1)
        
        # 禁用大厅交互直到连接
        self.set_lobby_enabled(False)
        
        # 绑定网络事件
        self.network.connected.connect(self.on_connected)
        self.network.disconnected.connect(self.on_disconnected)
        self.network.connection_failed.connect(self.on_connection_failed)
        self.network.message_received.connect(self.on_message)
        
        # 当前房间状态
        self.rooms_data = []

    def set_lobby_enabled(self, enabled):
        self.room_card.setEnabled(enabled)
        self.chat_card.setEnabled(enabled)
        self.ip_input.setEnabled(not enabled)
        self.name_input.setEnabled(not enabled)
        self.share_ip_btn.setEnabled(not enabled)
        self.connect_btn.setEnabled(True)
        if enabled:
            self.connect_btn.setText("断开连接")
            self.connect_btn.clicked.disconnect()
            self.connect_btn.clicked.connect(self.on_disconnect_clicked)
        else:
            self.connect_btn.setText("连接")
            self.connect_btn.clicked.disconnect()
            self.connect_btn.clicked.connect(self.on_connect_clicked)
            self.chat_display.clear()
            self.room_list.clear()

    def on_connect_clicked(self):
        ip = self.ip_input.text().strip()
        if not ip:
            return
            
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("连接中...")
            
        # 更新历史记录
        if ip in self.ip_history:
            self.ip_history.remove(ip)
        self.ip_history.insert(0, ip)
        self.ip_history = self.ip_history[:10] # 最多保存10条
        save_history(self.ip_history)
        
        # 更新下拉框
        self.ip_input.clear()
        self.ip_input.addItems(self.ip_history)
        self.ip_input.setText(ip)
        
        self.network.host = ip
        self.network.start()
        
    def on_share_ip_clicked(self):
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            ip = "127.0.0.1"
            
        QApplication.clipboard().setText(ip)
        self.ip_input.setText(ip)
        
        InfoBar.success(
            title="分享成功",
            content=f"已将我的IP地址 ({ip}) 复制到剪贴板，并尝试连接作为房主！",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self
        )
        self.on_connect_clicked()
        
    def on_connection_failed(self, error_msg):
        self.set_lobby_enabled(False)
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("连接")
        
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONHAND)
        except:
            pass
            
        InfoBar.error(
            title="连接失败",
            content=error_msg,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=5000,
            parent=self
        )
        
    def on_disconnect_clicked(self):
        self.network.stop()
        self.set_lobby_enabled(False)

    def on_connected(self):
        self.set_lobby_enabled(True)
        # 发送登录请求
        username = self.name_input.text()
        self.network.username = username
        self.network.send_message({"type": "login", "username": username})
        self.chat_display.append("<i>已连接到服务器。</i>")

    def on_disconnected(self):
        self.set_lobby_enabled(False)
        self.chat_display.append("<i>已从服务器断开。</i>")

    def send_chat(self):
        msg = self.chat_input.text().strip()
        if msg:
            self.network.send_message({"type": "chat", "msg": msg, "room_id": "lobby"})
            self.chat_input.clear()

    def on_message(self, msg: dict):
        msg_type = msg.get("type")
        if msg_type == "login_resp":
            if msg.get("success"):
                self.network.username = msg.get("username")
                self.name_input.setText(self.network.username)
        elif msg_type == "chat":
            sender = msg.get("sender", "Unknown")
            text = msg.get("msg", "")
            self.chat_display.append(f"<b>{sender}:</b> {text}")
            
            # Play sound and show notification if not from self
            if hasattr(self.network, 'username') and sender != self.network.username:
                try:
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
        elif msg_type == "room_list":
            self.rooms_data = msg.get("rooms", [])
            self.room_list.clear()
            for r in self.rooms_data:
                player_count = len(r['players']) + r['spectators']
                game_type = r.get('game_type', 'gomoku')
                game_name = "五子棋"
                if game_type == "guess_number":
                    game_name = "猜数字"
                elif game_type == "idiom_solitaire":
                    game_name = "成语接龙"
                elif game_type == "draw_guess":
                    game_name = "你画我猜"
                
                room_name = r.get('room_name', r['room_id'])
                creator = r.get('creator', '未知')
                status = "游戏中" if r.get('status') == "playing" else "等待中"
                self.room_list.addItem(f"[{game_name}] [{status}] {room_name} (房主: {creator}) - 人数: {player_count}")
        elif msg_type == "room_joined":
            # 房间加入成功，通知主窗口切换界面
            pass # 稍后在主窗口中处理
            
    def on_create_room(self):
        game = self.game_combo.currentText()
        game_type = "gomoku"
        if game == "猜数字":
            game_type = "guess_number"
        elif game == "成语接龙":
            game_type = "idiom_solitaire"
        elif game == "你画我猜":
            game_type = "draw_guess"
            
        self.network.send_message({"type": "create_room", "game_type": game_type})
        
    def on_join_room(self):
        current_row = self.room_list.currentRow()
        if current_row >= 0 and current_row < len(self.rooms_data):
            room_id = self.rooms_data[current_row]["room_id"]
            self.network.send_message({"type": "join_room", "room_id": room_id})
