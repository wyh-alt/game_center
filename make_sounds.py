import wave
import struct
import math
import os
import sys

def get_assets_dir():
    if hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.abspath(".")
    
    # 为了避免在只读目录(如_MEIPASS)下写入失败，我们选择在用户本地AppData或当前工作目录创建音频
    # 对于游戏音频，如果是生成的，放在用户的 temp 目录或当前工作目录是最好的
    # 但如果在_MEIPASS里，我们不能写入。
    # 最稳妥的方式：如果是打包环境，写入到系统的临时文件夹中，或者当前执行文件所在目录的assets下。
    assets_dir = os.path.join(os.path.abspath("."), 'assets')
    if not os.path.exists(assets_dir):
        try:
            os.makedirs(assets_dir)
        except Exception:
            # Fallback to temp dir if current dir is read-only
            import tempfile
            assets_dir = os.path.join(tempfile.gettempdir(), 'GameCenterAssets')
            if not os.path.exists(assets_dir):
                os.makedirs(assets_dir)
    return assets_dir

def make_wav(filename, gen_func):
    if os.path.exists(filename):
        return filename
    sample_rate = 44100
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        gen_func(f, sample_rate)
    return filename

def drop_gen(f, sample_rate):
    duration = 0.15
    num_samples = int(sample_rate * duration)
    for i in range(num_samples):
        t = float(i) / sample_rate
        freq = 800 * math.exp(-25 * t) + 200
        amp = 32767 * math.exp(-25 * t)
        val = int(amp * math.sin(2 * math.pi * freq * t))
        f.writeframesraw(struct.pack('<h', val))

def win_gen(f, sample_rate):
    notes = [(523.25, 0.1), (659.25, 0.1), (783.99, 0.1), (1046.50, 0.4)]
    for freq, duration in notes:
        num_samples = int(sample_rate * duration)
        for i in range(num_samples):
            t = float(i) / sample_rate
            amp = 32767 * math.exp(-5 * t)
            val = int(amp * math.sin(2 * math.pi * freq * t))
            f.writeframesraw(struct.pack('<h', val))

def skill_gen(f, sample_rate):
    duration = 0.2
    num_samples = int(sample_rate * duration)
    for i in range(num_samples):
        t = float(i) / sample_rate
        freq = 300 + 3000 * t
        amp = 32767 * math.exp(-15 * t)
        val = int(amp * math.sin(2 * math.pi * freq * t))
        f.writeframesraw(struct.pack('<h', val))

def start_gen(f, sample_rate):
    notes = [(523.25, 0.15), (783.99, 0.3)]
    for freq, duration in notes:
        num_samples = int(sample_rate * duration)
        for i in range(num_samples):
            t = float(i) / sample_rate
            amp = 32767 * math.exp(-10 * t)
            val = int(amp * math.sin(2 * math.pi * freq * t))
            f.writeframesraw(struct.pack('<h', val))

def init_assets():
    assets_dir = get_assets_dir()
    make_wav(os.path.join(assets_dir, 'drop.wav'), drop_gen)
    make_wav(os.path.join(assets_dir, 'win.wav'), win_gen)
    make_wav(os.path.join(assets_dir, 'skill.wav'), skill_gen)
    make_wav(os.path.join(assets_dir, 'start.wav'), start_gen)
    return assets_dir

if __name__ == '__main__':
    init_assets()
