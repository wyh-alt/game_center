import socket
import threading
import json
import uuid
from typing import Dict, List, Optional

HOST = '0.0.0.0'
PORT = 8888

import random

class Room:
    def __init__(self, room_id: str, room_name: str, game_type: str, host_client):
        self.room_id = room_id
        self.room_name = room_name
        self.game_type = game_type
        self.host = host_client
        self.players = [host_client]
        self.spectators = []
        self.game_state = {}
        self.status = "waiting" # waiting or playing
        
    def add_player(self, client):
        max_p = getattr(self, "max_players", 2)
        if len(self.players) < max_p:
            self.players.append(client)
            if len(self.players) == max_p:
                self.status = "playing"
            return True
        return False
        
    def add_spectator(self, client):
        self.spectators.append(client)
        
    def remove_client(self, client):
        if client in self.players:
            self.players.remove(client)
            self.status = "waiting"
        if client in self.spectators:
            self.spectators.remove(client)
        if client == self.host and self.players:
            self.host = self.players[0]
            
    def broadcast(self, message: dict, sender=None):
        for client in self.players + self.spectators:
            if client != sender:
                client.send_msg(message)

    def _handle_draw_guess_round_end(self, room):
        total_guessers = len(room.players) - 1
        correct_count = len(room.correct_guessers)
        
        drawer_name = room.players[room.drawer_index].username
        
        # 记录本轮得分
        round_scores = {p.username: 0 for p in room.players}
        
        # 所有人答对画手不加分，否则画手每个答对的人+5分
        if 0 < correct_count < total_guessers:
            points = correct_count * 5
            room.scores[drawer_name] += points
            round_scores[drawer_name] = points
            
        # 猜对者依次得分：8, 7, 6, 5... (保底2分)
        for i, p_name in enumerate(room.correct_guessers):
            points = max(2, 8 - i)
            if p_name in room.scores:
                room.scores[p_name] += points
                round_scores[p_name] = points
                
        room.broadcast({
            "type": "game_action",
            "action": "round_end",
            "scores": room.scores,
            "round_scores": round_scores,
            "word": room.current_word,
            "correct_guessers": room.correct_guessers,
            "drawer": drawer_name
        }, sender=None)
        
        room.drawer_index += 1
        import threading
        threading.Timer(5.0, lambda: room.start_draw_round() if room in room.host.server.rooms.values() else None).start()
        
    def start_draw_round(self):
        if not hasattr(self, 'drawer_index'):
            self.drawer_index = 0
            
        if self.drawer_index >= len(self.players):
            self.broadcast({"type": "game_action", "action": "game_over", "scores": self.scores})
            self.status = "waiting"
            return
            
        drawer = self.players[self.drawer_index]
        
        # 定义题库
        word_bank = [
            # 基础物品与动植物
            "苹果", "香蕉", "汽车", "房子", "大象", "电脑", "手机", "键盘", "鼠标", "耳机", 
            "老虎", "狮子", "熊猫", "长颈鹿", "猴子", "飞机", "火车", "火箭", "轮船", "自行车", 
            "月亮", "太阳", "星星", "云朵", "彩虹", "冰淇淋", "蛋糕", "巧克力", "汉堡", "披萨", 
            "篮球", "足球", "网球", "排球", "羽毛球", "吉他", "钢琴", "小提琴", "架子鼓", "笛子",
            "西瓜", "草莓", "葡萄", "柠檬", "樱桃", "电视", "冰箱", "洗衣机", "空调", "微波炉",
            "雨伞", "手表", "眼镜", "帽子", "围巾", "书包", "鞋子", "袜子", "手套", "衣服",
            "椅子", "桌子", "沙发", "床", "柜子", "门", "窗户", "钥匙", "锁", "镜子",
            "杯子", "碗", "盘子", "筷子", "勺子", "锅", "刀", "叉", "水壶", "茶壶",
            "书", "笔", "本子", "尺子", "橡皮", "黑板", "粉笔", "剪刀", "胶水", "胶带",
            "花", "树", "草", "叶子", "蘑菇", "山", "水", "河", "海", "石头",
            # 动物类扩充
            "兔子", "青蛙", "乌龟", "蛇", "马", "羊", "牛", "猪", "狗", "猫",
            "鸭子", "企鹅", "袋鼠", "骆驼", "斑马", "犀牛", "河马", "鳄鱼", "鲸鱼", "海豚",
            "鲨鱼", "章鱼", "海豹", "海马", "螃蟹", "龙虾", "水母", "海星", "北极熊", "树懒",
            "蝴蝶", "蜜蜂", "蜻蜓", "蚂蚁", "蜘蛛", "蚊子", "苍蝇", "甲虫", "毛毛虫", "蜗牛",
            # 食物类扩充
            "桃子", "李子", "梨", "哈密瓜", "菠萝", "芒果", "木瓜", "火龙果", "猕猴桃", "椰子",
            "白菜", "萝卜", "土豆", "番茄", "黄瓜", "茄子", "辣椒", "南瓜", "冬瓜", "苦瓜",
            "玉米", "红薯", "洋葱", "大蒜", "生姜", "葱", "芹菜", "香菜", "韭菜", "花菜",
            "面条", "米饭", "包子", "饺子", "馒头", "油条", "煎饼", "热狗", "三明治", "薯条",
            "可乐", "雪碧", "果汁", "牛奶", "咖啡", "茶", "奶茶", "豆浆", "酸奶", "冰水",
            # 日常用品扩充
            "牙刷", "牙膏", "毛巾", "香皂", "洗发水", "沐浴露", "梳子", "吹风机", "脸盆", "浴缸",
            "扫把", "拖把", "垃圾桶", "抹布", "吸尘器", "纸巾", "湿巾", "垃圾袋", "塑料袋", "购物袋",
            "订书机", "回形针", "大头针", "图钉", "夹子", "橡皮筋", "修正液", "订书钉", "文件夹", "档案袋",
            "日历", "挂钟", "闹钟", "相册", "相框", "画", "海报", "花瓶", "盆栽", "鱼缸",
            "台灯", "吊灯", "手电筒", "蜡烛", "火柴", "打火机", "电池", "插座", "插头", "电线",
            # 职业与人物
            "医生", "护士", "警察", "消防员", "教师", "学生", "厨师", "服务员", "司机", "飞行员",
            "宇航员", "科学家", "工程师", "建筑工人", "农民", "渔民", "邮递员", "快递员", "外卖员", "清洁工",
            "画家", "音乐家", "歌手", "演员", "导演", "摄影师", "记者", "作家", "诗人", "魔术师",
            # 自然景观与杂项
            "天空", "大地", "海洋", "湖泊", "河流", "小溪", "瀑布", "高山", "丘陵", "峡谷",
            "森林", "草原", "沙漠", "绿洲", "湿地", "冰川", "雪山", "火山", "地震", "龙卷风",
            "外星人", "机器人", "怪兽", "恐龙", "美人鱼", "独角兽", "雪人", "稻草人", "木偶", "天使"
        ]
        
        # 确保房间有已使用题目记录
        if not hasattr(self, 'used_words'):
            self.used_words = set()
            
        # 找出还没用过的题目
        available_words = [w for w in word_bank if w not in self.used_words]
        
        # 如果题目都用光了，就清空记录重新开始
        if not available_words:
            self.used_words.clear()
            available_words = word_bank
            
        word = random.choice(available_words)
        self.used_words.add(word)
        
        self.current_word = word
        self.correct_guessers = []
        
        for p in self.players + self.spectators:
            msg = {
                "type": "game_action",
                "action": "start_round",
                "drawer": drawer.username,
                "word": word if p == drawer else "",
                "scores": self.scores
            }
            p.send_msg(msg)
                
    def get_info(self):
        return {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "game_type": self.game_type,
            "creator": self.host.username,
            "status": self.status,
            "players": [p.username for p in self.players],
            "spectators": len(self.spectators)
        }

class ClientHandler(threading.Thread):
    def __init__(self, server, conn, addr):
        super().__init__()
        self.server = server
        self.conn = conn
        self.addr = addr
        self.username = f"Guest_{addr[1]}"
        self.current_room: Optional[Room] = None
        self.running = True

    def send_msg(self, msg_dict: dict):
        try:
            data = json.dumps(msg_dict).encode('utf-8')
            self.conn.sendall(data + b'\n')
        except Exception as e:
            print(f"Send error to {self.username}: {e}")

    def run(self):
        buffer = ""
        while self.running:
            try:
                data = self.conn.recv(1024)
                if not data:
                    break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self.handle_msg(json.loads(line.strip()))
            except Exception as e:
                print(f"Error handling {self.username}: {e}")
                break
        self.server.remove_client(self)

    def handle_msg(self, msg: dict):
        msg_type = msg.get("type")
        
        if msg_type == "login":
            requested_name = msg.get("username", self.username)
            base_name = requested_name
            counter = 1
            existing_names = [c.username for c in self.server.clients if c != self]
            while requested_name in existing_names:
                requested_name = f"{base_name}_{counter}"
                counter += 1
            self.username = requested_name
            self.send_msg({"type": "login_resp", "success": True, "username": self.username})
            self.server.broadcast_lobby({"type": "chat", "sender": "系统", "msg": f"{self.username} 加入了大厅。"})
            self.server.send_room_list(self)
            
        elif msg_type == "chat":
            room_id = msg.get("room_id")
            msg_text = msg.get("msg", "")
            chat_msg = {"type": "chat", "sender": self.username, "msg": msg_text, "room_id": room_id}
            if room_id == "lobby":
                self.server.broadcast_lobby(chat_msg)
            elif self.current_room:
                room = self.current_room
                if room.game_type == "draw_guess" and room.status == "playing" and hasattr(room, 'current_word'):
                    if room.current_word in msg_text:
                        chat_msg["msg"] = msg_text.replace(room.current_word, "<span style='color:green'>****</span>")
                self.current_room.broadcast(chat_msg)
                
        elif msg_type == "create_room":
            if self.current_room:
                self.handle_msg({"type": "leave_room"})
            game_type = msg.get("game_type", "gomoku")
            room_id = str(uuid.uuid4())[:8]
            
            adjectives = ["快乐的", "神秘的", "闪耀的", "安静的", "勇敢的", "聪明的", "温柔的", "神奇的", "幸运的", "可爱的"]
            nouns = ["苹果", "小猫", "太阳", "小狗", "房子", "大树", "汽车", "月亮", "星星", "花朵", "游戏"]
            room_name = f"{random.choice(adjectives)}{random.choice(nouns)}的房间"
            
            max_players = 2
            if game_type == "idiom_solitaire" or game_type == "draw_guess":
                max_players = 8
            
            room = Room(room_id, room_name, game_type, self)
            room.max_players = max_players
            self.server.rooms[room_id] = room
            self.current_room = room
            self.send_msg({"type": "room_joined", "room_info": room.get_info(), "role": "player"})
            self.server.broadcast_room_list()
            
        elif msg_type == "join_room":
            room_id = msg.get("room_id")
            if self.current_room and self.current_room.room_id == room_id:
                return
            if self.current_room:
                self.handle_msg({"type": "leave_room"})
            room = self.server.rooms.get(room_id)
            if room:
                max_p = getattr(room, "max_players", 2)
                if len(room.players) < max_p:
                    room.add_player(self)
                    self.current_room = room
                    self.send_msg({"type": "room_joined", "room_info": room.get_info(), "role": "player"})
                else:
                    room.add_spectator(self)
                    self.current_room = room
                    self.send_msg({"type": "room_joined", "room_info": room.get_info(), "role": "spectator"})
                
                room.broadcast({"type": "room_update", "room_info": room.get_info()})
                self.server.broadcast_room_list()
                
                if len(room.players) == 2 and room.game_type == "gomoku":
                    room.last_black = room.players[0]
                    room.broadcast({
                        "type": "game_action",
                        "action": "start",
                        "black": room.players[0].username,
                        "white": room.players[1].username
                    }, sender=None) # Broadcast to all including spectators
                elif len(room.players) == 2 and room.game_type == "guess_number":
                    room.last_thinker = room.players[0]
                    room.thinker = room.players[0]
                    room.guesser = room.players[1]
                    room.broadcast({
                        "type": "game_action",
                        "action": "start",
                        "thinker": room.thinker.username,
                        "guesser": room.guesser.username
                    }, sender=None)
                elif len(room.players) >= 2 and room.game_type == "idiom_solitaire":
                    # 成语接龙只要人数大于等于2，且由房主发开始消息，这里自动处理不够好。
                    # 不过可以每次有人加入就发一次状态。或者如果满了自动开始。
                    if len(room.players) == room.max_players:
                        room.broadcast({
                            "type": "game_action",
                            "action": "start",
                            "players": [p.username for p in room.players],
                            "current_turn": room.players[0].username
                        }, sender=None)
            else:
                self.send_msg({"type": "error", "msg": "找不到房间。"})
                
        elif msg_type == "leave_room":
            if self.current_room:
                room = self.current_room
                is_host = (self == room.host)
                if hasattr(room, "play_again_requests") and self in room.play_again_requests:
                    room.play_again_requests.remove(self)
                room.remove_client(self)
                
                if not room.players or is_host:
                    for spec in list(room.spectators) + list(room.players):
                        spec.send_msg({"type": "error", "msg": "玩家已退出，房间解散"})
                        spec.send_msg({"type": "_local_leave_room"})
                        spec.current_room = None
                    if room.room_id in self.server.rooms:
                        del self.server.rooms[room.room_id]
                else:
                    room.broadcast({"type": "room_update", "room_info": room.get_info()})
                    
                self.current_room = None
                self.server.broadcast_room_list()
                
        elif msg_type == "game_action":
            if self.current_room:
                action = msg.get("action")
                room = self.current_room
                if action == "guess":
                    if room.game_type == "draw_guess":
                        word = msg.get("word", "")
                        if hasattr(room, 'drawer_index') and room.drawer_index < len(room.players):
                            drawer_name = room.players[room.drawer_index].username
                            if self.username != drawer_name and self.username not in room.correct_guessers:
                                masked_word = word
                                if hasattr(room, 'current_word') and room.current_word in word:
                                    masked_word = word.replace(room.current_word, "<span style='color:green'>****</span>")
                                
                                chat_msg = {"type": "chat", "sender": self.username, "msg": masked_word, "room_id": room.room_id}
                                room.broadcast(chat_msg, sender=None)
                                
                                if word == room.current_word:
                                    room.correct_guessers.append(self.username)
                                    room.broadcast({"type": "game_action", "action": "player_guessed_correctly", "player": self.username}, sender=None)
                                    
                                    # If all guessers guessed correctly, end round early
                                    if len(room.correct_guessers) == len(room.players) - 1:
                                        room._handle_draw_guess_round_end(room)
                    else:
                        msg["sender"] = self.username
                        self.current_room.broadcast(msg)
                elif action == "play_again_request":
                    if not hasattr(room, "play_again_requests"):
                        room.play_again_requests = set()
                    room.play_again_requests.add(self)
                    
                    room.broadcast({"type": "game_action", "action": "play_again_status", "count": len(room.play_again_requests), "total": len(room.players)}, sender=None)
                    
                    if len(room.play_again_requests) == len(room.players) and len(room.players) == 2:
                        room.play_again_requests.clear()
                        if room.game_type == "gomoku":
                            if not hasattr(room, "last_black"):
                                room.last_black = room.players[0]
                                
                            if room.last_black == room.players[0]:
                                new_black = room.players[1]
                                new_white = room.players[0]
                            else:
                                new_black = room.players[0]
                                new_white = room.players[1]
                                
                            room.last_black = new_black
                            room.broadcast({
                                "type": "game_action",
                                "action": "start",
                                "black": new_black.username,
                                "white": new_white.username
                            }, sender=None)
                        elif room.game_type == "guess_number":
                            if not hasattr(room, "last_thinker"):
                                room.last_thinker = room.players[0]
                                
                            if room.last_thinker == room.players[0]:
                                new_thinker = room.players[1]
                                new_guesser = room.players[0]
                            else:
                                new_thinker = room.players[0]
                                new_guesser = room.players[1]
                                
                            room.last_thinker = new_thinker
                            room.broadcast({
                                "type": "game_action",
                                "action": "start",
                                "thinker": new_thinker.username,
                                "guesser": new_guesser.username
                            }, sender=None)
                elif action == "request_start":
                    if room.game_type == "idiom_solitaire" and len(room.players) >= 2:
                        room.current_turn_index = 0
                        room.broadcast({
                            "type": "game_action",
                            "action": "start",
                            "current_turn": room.players[0].username
                        }, sender=None)
                    elif room.game_type == "draw_guess" and len(room.players) >= 2:
                        room.drawer_index = 0
                        room.scores = {p.username: 0 for p in room.players}
                        room.status = "playing"
                        room.start_draw_round()
                        self.server.broadcast_room_list()
                elif action == "submit_drawing":
                    msg["sender"] = self.username
                    room.broadcast(msg)
                elif action == "submit_idiom":
                    msg["sender"] = self.username
                    room.broadcast(msg)
                elif action == "idiom_valid":
                    room.current_turn_index = (room.current_turn_index + 1) % len(room.players)
                    next_player = room.players[room.current_turn_index].username
                    room.broadcast({
                        "type": "game_action",
                        "action": "next_turn",
                        "current_turn": next_player
                    }, sender=None)
                elif action == "end_round_request":
                    if room.game_type == "draw_guess" and hasattr(room, 'drawer_index') and self == room.players[room.drawer_index]:
                        room._handle_draw_guess_round_end(room)
                else:
                    msg["sender"] = self.username
                    self.current_room.broadcast(msg)

class GameServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients: List[ClientHandler] = []
        self.rooms: Dict[str, Room] = {}

    def start(self):
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(5)
        print(f"Server started on {HOST}:{PORT}")
        
        try:
            while True:
                conn, addr = self.server_socket.accept()
                print(f"New connection from {addr}")
                client = ClientHandler(self, conn, addr)
                self.clients.append(client)
                client.start()
        except KeyboardInterrupt:
            print("Server stopping...")
        finally:
            self.server_socket.close()

    def remove_client(self, client: ClientHandler):
        if client in self.clients:
            self.clients.remove(client)
        if client.current_room:
            room = client.current_room
            is_host = (client == room.host)
            if hasattr(room, "play_again_requests") and client in room.play_again_requests:
                room.play_again_requests.remove(client)
            room.remove_client(client)
            if not room.players or is_host:
                for spec in list(room.spectators) + list(room.players):
                    spec.send_msg({"type": "error", "msg": "玩家已退出，房间解散"})
                    spec.send_msg({"type": "_local_leave_room"})
                    spec.current_room = None
                if room.room_id in self.rooms:
                    del self.rooms[room.room_id]
            else:
                room.broadcast({"type": "room_update", "room_info": room.get_info()})
            self.broadcast_room_list()
        print(f"Client {client.username} disconnected.")

    def broadcast_lobby(self, msg: dict):
        for client in self.clients:
            if client.current_room is None:
                client.send_msg(msg)

    def broadcast_room_list(self):
        rooms_info = [r.get_info() for r in self.rooms.values()]
        for client in self.clients:
            client.send_msg({"type": "room_list", "rooms": rooms_info})

    def send_room_list(self, client: ClientHandler):
        rooms_info = [r.get_info() for r in self.rooms.values()]
        client.send_msg({"type": "room_list", "rooms": rooms_info})

if __name__ == "__main__":
    server = GameServer()
    server.start()
