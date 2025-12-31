"""
将🏛️ Emoji转换为ICO图标文件
"""
from PIL import Image, ImageDraw, ImageFont
import os

def draw_simple_senate(draw, size, color=(100, 149, 237)):
    """绘制简化版元老院图标（用于小尺寸）"""
    # 绘制柱子（3根）
    col_width = size // 8
    col_height = int(size * 0.6)
    base_y = size - size // 6
    
    # 三根柱子
    for i in [1, 3, 5]:
        x = int(size * i / 7)
        draw.rectangle(
            [x, base_y - col_height, x + col_width, base_y],
            fill=color
        )
    
    # 顶部三角形屋顶
    roof_points = [
        (size // 2, size // 8),  # 顶点
        (size // 10, base_y - col_height),  # 左下
        (size - size // 10, base_y - col_height)  # 右下
    ]
    draw.polygon(roof_points, fill=color)
    
    # 底座
    draw.rectangle(
        [size // 10, base_y, size - size // 10, size - size // 12],
        fill=color
    )

def create_senate_icon(output_path="senate.ico"):
    """创建元老院图标（🏛️）"""
    # 创建多个尺寸的图标（ICO格式标准）
    sizes = [256, 128, 64, 48, 32, 16]
    images = []
    
    for size in sizes:
        # 创建带透明背景的图片
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 小尺寸使用简化图标，大尺寸使用emoji
        if size <= 32:
            # 小尺寸：使用简化的几何图形
            draw_simple_senate(draw, size, color=(100, 149, 237, 255))
        else:
            # 大尺寸：使用emoji
            try:
                # Windows 10/11 的 emoji 字体
                font_size = int(size * 0.75)
                font = ImageFont.truetype("seguiemj.ttf", font_size)
                
                # 计算emoji居中位置
                emoji = "🏛️"
                bbox = draw.textbbox((0, 0), emoji, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (size - text_width) // 2 - bbox[0]
                y = (size - text_height) // 2 - bbox[1]
                
                # 绘制emoji
                draw.text((x, y), emoji, font=font, embedded_color=True)
            except:
                # 如果emoji字体失败，也使用简化图标
                draw_simple_senate(draw, size, color=(100, 149, 237, 255))
        
        images.append(img)
    
    # 保存为ICO文件（多尺寸）
    images[0].save(output_path, format='ICO', sizes=[(img.width, img.height) for img in images])
    print(f"✅ 图标已生成: {output_path}")
    print(f"   包含尺寸: {', '.join([f'{s}x{s}' for s in sizes])}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "senate.ico")
    create_senate_icon(output_path)
