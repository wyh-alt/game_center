import socket
import json
import threading
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import time

class NetworkThread(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    connection_failed = pyqtSignal(str)
    message_received = pyqtSignal(dict)
    
    def __init__(self, host='127.0.0.1', port=8888):
        super().__init__()
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        
    def run(self):
        self.running = True
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3.0) # 3秒连接超时
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(None) # 连接成功后恢复阻塞模式
            self.connected.emit()
            
            buffer = ""
            while self.running:
                data = self.socket.recv(1024)
                if not data:
                    break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        msg = json.loads(line.strip())
                        self.message_received.emit(msg)
        except socket.timeout:
            self.connection_failed.emit(f"连接超时：无法连接到 {self.host}:{self.port}")
            self.running = False
        except ConnectionRefusedError:
            self.connection_failed.emit(f"连接被拒绝：目标机器积极拒绝 {self.host}:{self.port}")
            self.running = False
        except Exception as e:
            if self.running: # 如果不是主动stop引起的异常
                self.connection_failed.emit(f"连接错误：{str(e)}")
            self.running = False
            print(f"Connection error: {e}")
        finally:
            if self.socket:
                self.socket.close()
            self.disconnected.emit()
                
    def send_message(self, msg: dict):
        if self.socket and self.running:
            try:
                data = json.dumps(msg).encode('utf-8')
                self.socket.sendall(data + b'\n')
            except Exception as e:
                print(f"Send error: {e}")
                
    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
        self.wait()
