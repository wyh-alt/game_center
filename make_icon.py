from PIL import Image, ImageDraw

def create_icon():
    # 创建一个 256x256 的图像，带透明通道
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制圆角矩形底板 (Win11风格)
    margin = 16
    radius = 48
    box = [margin, margin, size - margin, size - margin]
    
    # 渐变蓝色底板
    color_bg = (30, 144, 255, 255) # DodgerBlue
    draw.rounded_rectangle(box, radius, fill=color_bg)
    
    # 绘制游戏手柄轮廓
    # 左半边
    draw.ellipse([50, 90, 110, 150], fill=(255, 255, 255, 255))
    # 右半边
    draw.ellipse([146, 90, 206, 150], fill=(255, 255, 255, 255))
    # 中间连接
    draw.rectangle([80, 90, 176, 150], fill=(255, 255, 255, 255))
    
    # 左侧十字键
    draw.rectangle([75, 105, 85, 135], fill=color_bg)
    draw.rectangle([65, 115, 95, 125], fill=color_bg)
    
    # 右侧ABXY按钮
    draw.ellipse([160, 115, 170, 125], fill=color_bg)
    draw.ellipse([182, 115, 192, 125], fill=color_bg)
    draw.ellipse([171, 104, 181, 114], fill=color_bg)
    draw.ellipse([171, 126, 181, 136], fill=color_bg)

    # 保存为 ICO，包含多种尺寸
    img.save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])

if __name__ == '__main__':
    create_icon()
