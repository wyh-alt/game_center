import sys
import os
import ctypes
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from qfluentwidgets import FluentWindow, NavigationItemPosition, SubtitleLabel, setTheme, Theme
from qfluentwidgets import FluentIcon as FIF

from network import NetworkThread
from lobby_ui import LobbyInterface
from games.gomoku import GomokuInterface
from games.guess_number import GuessNumberInterface
from games.idiom_solitaire import IdiomSolitaireInterface
from games.draw_guess import DrawGuessInterface

try:
    import make_sounds
    make_sounds.init_assets()
except Exception as e:
    print("Error init assets:", e)

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        
        self.network = NetworkThread()
        
        # init interfaces
        self.lobby_interface = LobbyInterface(self.network, self)
        self.gomoku_interface = GomokuInterface(self.network, self)
        self.guess_number_interface = GuessNumberInterface(self.network, self)
        self.idiom_solitaire_interface = IdiomSolitaireInterface(self.network, self)
        self.draw_guess_interface = DrawGuessInterface(self.network, self)
        
        self.initNavigation()
        self.initWindow()
        self.initBGM()
        
        # 绑定网络事件来切换界面
        self.network.message_received.connect(self.handle_network_message)

    def initBGM(self):
        self.bgm_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.bgm_player.setAudioOutput(self.audio_output)
        
        # 加载指定的BGM文件
        bgm_path = get_resource_path("おはなばたけ~1.m4a")
        if os.path.exists(bgm_path):
            self.bgm_player.setSource(QUrl.fromLocalFile(bgm_path))
            self.bgm_player.setLoops(QMediaPlayer.Loops.Infinite) # 设置循环播放
            self.audio_output.setVolume(0.3) # 默认音量 30%
            self.bgm_player.play()
            self.is_muted = False
        else:
            self.is_muted = True

    def toggle_bgm(self):
        if self.is_muted:
            self.audio_output.setMuted(False)
            self.is_muted = False
            # 图标变为非静音
            if hasattr(self, 'bgm_nav_item'):
                self.bgm_nav_item.setIcon(FIF.MUSIC)
        else:
            self.audio_output.setMuted(True)
            self.is_muted = True
            # 图标变为静音
            if hasattr(self, 'bgm_nav_item'):
                self.bgm_nav_item.setIcon(FIF.MUTE)

    def initNavigation(self):
        self.addSubInterface(self.lobby_interface, FIF.HOME, '游戏大厅')
        self.addSubInterface(self.gomoku_interface, FIF.GAME, '技能五子棋')
        self.addSubInterface(self.guess_number_interface, FIF.EDUCATION, '猜数字')
        self.addSubInterface(self.idiom_solitaire_interface, FIF.MESSAGE, '成语接龙')
        self.addSubInterface(self.draw_guess_interface, FIF.PALETTE, '你画我猜')
        
        # 添加底部的 BGM 控制按钮
        self.bgm_nav_item = self.navigationInterface.addItem(
            routeKey='bgm_toggle',
            icon=FIF.MUSIC,
            text='BGM 开/关',
            onClick=self.toggle_bgm,
            position=NavigationItemPosition.BOTTOM,
            selectable=False
        )
        
    def initWindow(self):
        self.resize(900, 700)
        
        # 加载自定义图标
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon(FIF.GAME.icon()))
            
        self.setWindowTitle('局域网游戏中心')
        
        # 设置毛玻璃效果
        self.setMicaEffectEnabled(True)

    def handle_network_message(self, msg: dict):
        msg_type = msg.get("type")
        if msg_type == "room_joined":
            room_info = msg.get("room_info", {})
            game_type = room_info.get("game_type", "")
            if game_type == "gomoku":
                self.switchTo(self.gomoku_interface)
            elif game_type == "guess_number":
                self.switchTo(self.guess_number_interface)
            elif game_type == "idiom_solitaire":
                self.switchTo(self.idiom_solitaire_interface)
            elif game_type == "draw_guess":
                self.switchTo(self.draw_guess_interface)
        elif msg_type == "_local_leave_room":
            self.switchTo(self.lobby_interface)

if __name__ == '__main__':
    # 强制 Windows 将该应用视为独立程序，以显示我们自定义的任务栏图标
    myappid = 'mycompany.myproduct.subproduct.version' # 任意字符串即可
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    
    # 全局应用图标
    icon_path = get_resource_path("icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        
    setTheme(Theme.AUTO)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
