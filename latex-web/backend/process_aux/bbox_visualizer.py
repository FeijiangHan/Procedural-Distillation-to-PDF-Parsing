import json
import fitz  # PyMuPDF
import os
from pathlib import Path
from typing import Dict, List, Tuple
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import random

__all__ = ['BBoxVisualizer']
class BBoxVisualizer:
    def __init__(self, dpi: int = 72):
        self.dpi = dpi
        
        # 预定义的颜色列表
        self.PREDEFINED_COLORS = [
            "red", "green", "blue", "orange", "purple", "cyan",
            "magenta", "yellow", "lime", "pink", "brown", "teal",
            "olive", "maroon", "navy", "grey", "black"
        ]
        
        # 为每种元素类型分配固定颜色
        self.colors = {
            'header': '#FF4B4B',      # 鲜红色
            'figure': '#4B7BFF',      # 鲜蓝色
            'figure*': '#4B7BFF',     # 鲜蓝色
            'figurecap': '#4BC6FF',   # 浅蓝色
            'figurecap*': '#4BC6FF',  # 浅蓝色
            'table': '#4BFF4B',       # 鲜绿色
            'table*': '#4BFF4B',      # 鲜绿色
            'tablecap': '#B4FF4B',    # 浅绿色
            'tablecap*': '#B4FF4B',   # 浅绿色
            'math': '#FF4BFF'         # 鲜紫色
        }
        
        # 创建临时目录
        self.temp_dir = Path(__file__).parent / "temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        matplotlib.rcParams['savefig.directory'] = str(self.temp_dir)
        
        # 添加 columnwidth 属性
        self.columnwidth = None  # 将在 visualize_bboxes 中设置
        
    def sp_to_pt(self, sp: int) -> float:
        """Convert Scaled Point (sp) to points (pt)"""
        return sp / 65536  # 1 sp = 1/65536 pt
        
    def convert_bbox_to_pixels(self, bbox: List[int], page_height_pt: float) -> List[float]:
        """Convert bbox from LaTeX coordinates (sp) to PDF coordinates (pt)"""
        # Convert from sp to pt
        x1_pt = self.sp_to_pt(bbox[0])
        y1_pt = self.sp_to_pt(bbox[1])
        x2_pt = self.sp_to_pt(bbox[2])
        y2_pt = self.sp_to_pt(bbox[3])
        
        # LaTeX coordinates are from bottom-left, PDF from top-left
        # Need to flip Y coordinates
        y1_pdf = page_height_pt - y1_pt
        y2_pdf = page_height_pt - y2_pt
        
        # Make sure y1 is always smaller than y2 (top is smaller in PDF coordinates)
        y_min = min(y1_pdf, y2_pdf)
        y_max = max(y1_pdf, y2_pdf)
        
        # Convert to pixels using DPI
        scale = self.dpi / 72.0  # PDF points to pixels
        x1_px = x1_pt * scale
        x2_px = x2_pt * scale
        y1_px = y_min * scale
        y2_px = y_max * scale
        
        return [x1_px, y1_px, x2_px, y2_px]
        
    def get_element_color(self, element_key: str) -> str:
        """Get color for element type"""
        base_type = element_key.split('-', 1)[1]
        return self.colors.get(base_type, '#808080')  # 默认使用灰色
        
    def visualize_bboxes(self, pdf_path: str, bbox_file: str, output_dir: str = None) -> None:
        """Visualize bounding boxes on PDF pages"""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
        if not os.path.exists(bbox_file):
            raise FileNotFoundError(f"BBox file not found: {bbox_file}")
            
        # Create output directory if not exists
        if output_dir is None:
            output_dir = str(Path(pdf_path).parent / "bbox_visualization")
        os.makedirs(output_dir, exist_ok=True)
        
        # Load bounding boxes
        with open(bbox_file, 'r', encoding='utf-8') as f:
            bbox_data = json.load(f)
            
        # 设置 columnwidth（假设为页面宽度的一半）
        pdf_document = fitz.open(pdf_path)
        self.columnwidth = pdf_document[0].rect.width / 2
        
        try:
            # Process each page
            for page_num in bbox_data:
                page_idx = int(page_num) - 1
                if page_idx >= len(pdf_document):
                    print(f"Warning: Page {page_num} not found in PDF")
                    continue
                    
                # Get page
                page = pdf_document[page_idx]
                width_pt = page.rect.width
                height_pt = page.rect.height
                
                # Convert page to image with proper scaling
                zoom = self.dpi / 72.0  # Scale factor for desired DPI
                matrix = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=matrix)
                img_data = pix.tobytes("png")
                
                # Save temporary PNG file
                temp_png = self.temp_dir / f"temp_page_{page_num}.png"
                with open(temp_png, 'wb') as f:
                    f.write(img_data)
                
                # Read image using matplotlib
                img = plt.imread(str(temp_png))
                
                # Create figure with proper size
                fig, ax = plt.subplots(figsize=(width_pt/72*zoom, height_pt/72*zoom))
                ax.imshow(img)
                
                # Draw bounding boxes
                for element_key, bbox in bbox_data[page_num].items():
                    # Convert coordinates
                    bbox_px = self.convert_bbox_to_pixels(bbox, height_pt)
                    
                    # Get color for this element
                    color = self.get_element_color(element_key)
                    
                    # Create rectangle
                    width = bbox_px[2] - bbox_px[0]
                    height = bbox_px[3] - bbox_px[1]
                    rect = patches.Rectangle(
                        (bbox_px[0], bbox_px[1]), 
                        width, 
                        height,
                        linewidth=2,
                        edgecolor=color,
                        facecolor='none',
                        alpha=0.7
                    )
                    ax.add_patch(rect)
                    
                    # 修改标签位置逻辑
                    label_y = bbox_px[1] + height/2  # 标签垂直居中对齐
                    ha = 'left'  # 默认左对齐
                    padding = 5  # 标签和边界框之间的间距
                    
                    if bbox_px[0] > self.columnwidth * (self.dpi / 72.0):
                        # 如果框在右半边，标签放在右侧
                        label_x = bbox_px[2] + padding  # 边界框右侧
                        ha = 'left'
                    else:
                        # 如果框在左半边，标签放在左侧
                        label_x = bbox_px[0] - padding  # 边界框左侧
                        ha = 'right'
                    
                    plt.text(
                        label_x, 
                        label_y,
                        element_key,
                        color='white',
                        fontsize=8,
                        fontweight='bold',
                        horizontalalignment=ha,
                        verticalalignment='center',  # 改为垂直居中
                        bbox=dict(
                            facecolor=color,
                            alpha=0.7,
                            edgecolor='none',
                            boxstyle='round,pad=0.5'
                        )
                    )
                
                # Save figure
                plt.axis('off')
                plt.tight_layout(pad=0)
                output_path = os.path.join(output_dir, f"page_{page_num}_bbox.png")
                plt.savefig(output_path, dpi=200, bbox_inches='tight', pad_inches=0)
                plt.close()
                
                # Remove temporary PNG file
                temp_png.unlink()
                
                print(f"Saved visualization for page {page_num} to: {output_path}")
                
        finally:
            pdf_document.close()
            # Clean up temporary directory
            if self.temp_dir.exists():
                for file in self.temp_dir.glob("*"):
                    file.unlink()
                self.temp_dir.rmdir()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Visualize bounding boxes on PDF pages')
    parser.add_argument('pdf_file', help='Input PDF file')
    parser.add_argument('bbox_file', help='Input JSON file with bounding boxes')
    parser.add_argument('--output-dir', help='Output directory for visualizations')
    parser.add_argument('--dpi', type=int, default=72, help='DPI for output images')
    
    args = parser.parse_args()
    
    visualizer = BBoxVisualizer(dpi=args.dpi)
    visualizer.visualize_bboxes(args.pdf_file, args.bbox_file, args.output_dir)

if __name__ == "__main__":
    main() 