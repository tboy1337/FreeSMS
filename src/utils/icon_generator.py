"""
Icon generator for SMS application
"""
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def generate_sms_icon(output_path, size=256, background_color=(74, 108, 212), text_color=(255, 255, 255)):
    """
    Generate a simple SMS icon
    
    Args:
        output_path: Path to save the icon
        size: Icon size in pixels
        background_color: Background color as RGB tuple
        text_color: Text color as RGB tuple
    """
    # Validate input parameters
    if size <= 0:
        raise ValueError("Size must be greater than 0")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Create a new image with the specified background color
    img = Image.new('RGB', (size, size), background_color)
    draw = ImageDraw.Draw(img)
    
    # Calculate speech bubble dimensions
    padding = size // 8
    bubble_width = size - (padding * 2)
    bubble_height = size - (padding * 2)
    corner_radius = size // 10
    
    # Draw rounded rectangle for speech bubble
    draw.rounded_rectangle(
        [(padding, padding), (size - padding, size - padding)],
        corner_radius,
        fill=(255, 255, 255),
        outline=None
    )
    
    # Draw tail of speech bubble
    tail_size = size // 6
    tail_points = [
        (padding + bubble_width // 4, size - padding),  # Start point on bottom edge
        (padding + bubble_width // 8, size - padding // 2),  # Point outside bubble
        (padding + bubble_width // 2, size - padding)  # End point on bottom edge
    ]
    draw.polygon(tail_points, fill=(255, 255, 255), outline=None)
    
    # Draw "SMS" text
    try:
        # Try to load a font, fall back to default if not available
        font_size = size // 3
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        text = "SMS"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Position text in the center of the bubble
        text_x = padding + (bubble_width - text_width) // 2
        text_y = padding + (bubble_height - text_height) // 2 - (tail_size // 2)
        
        # Draw the text
        draw.text((text_x, text_y), text, font=font, fill=text_color)
    except:
        # If text drawing fails, draw simple lines
        center_x = size // 2
        center_y = size // 2
        line_length = size // 4
        line_width = size // 16
        
        # Draw "S"
        s_y_top = center_y - line_length // 2
        s_y_middle = center_y
        s_y_bottom = center_y + line_length // 2
        s_x_left = center_x - line_length
        s_x_right = center_x - line_length // 2
        
        # Top horizontal line of S
        draw.line([(s_x_left, s_y_top), (s_x_right, s_y_top)], fill=background_color, width=line_width)
        # Middle vertical line of S
        draw.line([(s_x_left, s_y_top), (s_x_left, s_y_middle)], fill=background_color, width=line_width)
        # Middle horizontal line of S
        draw.line([(s_x_left, s_y_middle), (s_x_right, s_y_middle)], fill=background_color, width=line_width)
        # Bottom vertical line of S
        draw.line([(s_x_right, s_y_middle), (s_x_right, s_y_bottom)], fill=background_color, width=line_width)
        # Bottom horizontal line of S
        draw.line([(s_x_left, s_y_bottom), (s_x_right, s_y_bottom)], fill=background_color, width=line_width)
    
    # Save the image
    img.save(output_path)
    return output_path

if __name__ == "__main__":
    # If run directly, generate icon in the assets directory
    script_dir = Path(__file__).parent
    assets_dir = script_dir.parent / "gui" / "assets"
    assets_dir.mkdir(exist_ok=True)
    
    # Generate icon
    icon_path = assets_dir / "sms_icon.png"
    generate_sms_icon(icon_path)
    print(f"Icon generated at: {icon_path}")
    
    # Also generate ICO format for Windows
    try:
        from PIL import Image
        img = Image.open(icon_path)
        ico_path = assets_dir / "sms_icon.ico"
        img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        print(f"ICO generated at: {ico_path}")
    except Exception as e:
        print(f"Failed to generate ICO: {e}") 