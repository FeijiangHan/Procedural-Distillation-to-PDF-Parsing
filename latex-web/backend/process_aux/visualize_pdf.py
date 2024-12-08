import fitz  # PyMuPDF
import json
from pathlib import Path
import logging
from typing import Dict, List, Tuple

__all__ = ['PdfVisualizer']
class PdfVisualizer:
    """将边界框直接绘制在PDF上"""
    
    def __init__(self, dpi: int = 200):
        self.logger = logging.getLogger('pdf_visualizer')
        # 使用与bbox_visualizer相同的颜色方案
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
        self.dpi = dpi
        self.columnwidth = None  # 将在visualize_pdf中设置
        
    def hex_to_rgb(self, hex_color: str) -> Tuple[float, float, float]:
        """将十六进制颜色转换为RGB元组（0-1范围）"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return (r, g, b)
        
    def sp_to_pt(self, sp: int) -> float:
        """将TeX的scaled points转换为PDF points"""
        return sp / 65536  # 1 sp = 1/65536 pt
        
    def convert_bbox(self, bbox: List[int], page_height: float) -> List[float]:
        """转换边界框坐标"""
        # 转换为points
        x1 = self.sp_to_pt(bbox[0])
        y1 = self.sp_to_pt(bbox[1])
        x2 = self.sp_to_pt(bbox[2])
        y2 = self.sp_to_pt(bbox[3])
        
        # 翻转Y坐标（PDF坐标系原点在左上角）
        y1 = page_height - y1
        y2 = page_height - y2
        
        # 确保y1 < y2
        if y1 > y2:
            y1, y2 = y2, y1
            
        return [x1, y1, x2, y2]
        
    def get_element_color(self, element_type: str) -> Tuple[float, float, float]:
        """获取元素类型对应的颜色"""
        # 如果包含'-'则分割，否则使用整个类型
        base_type = element_type.split('-', 1)[1] if '-' in element_type else element_type
        hex_color = self.colors.get(base_type, '#808080')  # 默认灰色
        return self.hex_to_rgb(hex_color)
        
    def draw_bbox(self, page: fitz.Page, bbox: List[float], 
                  element_type: str, element_key: str):
        """在页面上绘制边界框"""
        # 获取颜色
        color = self.get_element_color(element_type)
        
        # 获取页面边界
        page_width = page.rect.width
        
        # 绘制矩形
        page.draw_rect(
            fitz.Rect(bbox),
            color=color,
            width=1.5,
            stroke_opacity=0.7
        )
        
        # 计算标签位置
        label_y = bbox[1] + (bbox[3] - bbox[1])/2  # 垂直居中
        padding = 5  # 标签和边界框之间的间距
        label_offset = 20  # 标签固定偏移距离
        
        # 计算边界框的中心点
        box_center_x = (bbox[0] + bbox[2]) / 2
        
        if box_center_x > self.columnwidth:
            # 右半边的框，标签默认放在右侧
            label_x = bbox[2] + padding
            ha = 'left'
            label_x = bbox[2] - label_offset
            # 如果标签会超出右边界，向左移动固定距离
            if label_x > page_width:
                label_x = bbox[2] - label_offset
                ha = 'right'
        else:
            # 左半边的框，标签默认放在左侧
            label_x = bbox[0]
            ha = 'right'
            
            # 如果标签会超出左边界，向右移动固定距离
            # if label_x < 0:
            # label_x = bbox[0] + label_offset
            # ha = 'left'
        
        # 使用matplotlib生成标签图片
        import matplotlib.pyplot as plt
        import io
        
        # 创建一个临时图像来绘制标签
        fig, ax = plt.subplots(figsize=(2, 0.5))
        ax.set_axis_off()
        
        # 绘制文本和背景框
        text = ax.text(
            0.5 if ha == 'center' else 0.1 if ha == 'left' else 0.9,
            0.5,
            element_key,
            color='white',
            fontsize=8,
            fontweight='bold',
            horizontalalignment=ha,
            verticalalignment='center',
            bbox=dict(
                facecolor=color,
                alpha=0.7,
                edgecolor='none',
                boxstyle='round,pad=0.5'
            )
        )
        
        # 调整图像大小以适应文本
        bbox = text.get_window_extent(fig.canvas.get_renderer())
        fig.tight_layout(pad=0.1)
        
        # 将图像保存到内存
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight', 
                   transparent=True, pad_inches=0)
        plt.close()
        
        # 将图像插入PDF
        buf.seek(0)
        img = fitz.Pixmap(buf.getvalue())
        
        # 计算插入位置和缩放
        scale = 0.3  # 调整缩放以匹配所需大小
        rect = fitz.Rect(
            label_x - (img.width * scale if ha == 'right' else 0),  # 右对齐时需要向左偏移
            label_y - img.height * scale / 2,
            label_x + (img.width * scale if ha == 'left' else 0),  # 左对齐时向右延伸
            label_y + img.height * scale / 2
        )
        
        # 插入图像
        page.insert_image(rect, pixmap=img)

    def convert_to_coco(self, bbox_data: Dict, page_num: str, page_height: float, page_width: float) -> Dict:
        """将边界框数据转换为COCO格式"""
        # 标签映射
        label_mapping = {
            "figure": "Figure",
            "figure*": "Figure",
            "figurecap": "FigureCaption",
            "figurecap*": "FigureCaption",
            "header": "Heading",
            "math": "MathBlock",
            "table": "Table",
            "table*": "Table",
            "tablecap": "TableCaption",
            "tablecap*": "TableCaption",
            "text": "Text"
        }

        coco_data = {
            "flags": {},
            "shapes": []
        }

        shape_id = 1
        for element_key, bbox in bbox_data[page_num].items():
            element_type = element_key.split('-', 1)[1]
            if element_type in label_mapping:
                # 转换坐标
                pdf_bbox = self.convert_bbox(bbox, page_height)
                
                shape = {
                    "description": element_key,
                    "label": label_mapping[element_type],
                    "points": [
                        [pdf_bbox[0], pdf_bbox[1]],  # 左上角
                        [pdf_bbox[2], pdf_bbox[3]]   # 右下角
                    ],
                    "group_id": shape_id,
                    "parent_id": None,
                    "shape_id": f"S_{shape_id}",
                    "shape_type": "rectangle",
                    "flags": {}
                }
                coco_data["shapes"].append(shape)
                shape_id += 1

        return coco_data

    def visualize_pdf(self, pdf_path: str, bbox_file: str, output_dir: str = None):
        """在PDF上绘制边界框并生成COCO格式标注"""
        try:
            # 设置默认输出目录
            if output_dir is None:
                output_dir = Path(pdf_path).parent
            else:
                output_dir = Path(output_dir)
                
            # 创建pages子目录
            pages_dir = output_dir / "pages"
            pages_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建标注目录
            annotations_dir = output_dir / "annotations"
            annotations_dir.mkdir(parents=True, exist_ok=True)
            
            # 设置PDF输出路径
            pdf_output = output_dir / f"{Path(pdf_path).stem}_marked.pdf"
            
            # 加载边界框数据
            with open(bbox_file, 'r') as f:
                bbox_data = json.load(f)
                
            # 打开PDF并设置columnwidth
            pdf = fitz.open(pdf_path)
            self.columnwidth = pdf[0].rect.width / 2  # 设置页面宽度的一半作为columnwidth
            
            try:
                # 处理每一页
                for page_num in bbox_data:
                    # 获取页面
                    page_idx = int(page_num) - 1
                    if page_idx >= len(pdf):
                        self.logger.warning(f"Page {page_num} not found in PDF")
                        continue
                        
                    page = pdf[page_idx]
                    page_height = page.rect.height
                    
                    # 按元素类型分组绘制，保持绘制顺序一致
                    elements_by_type = {}
                    for element_key, bbox in bbox_data[page_num].items():
                        element_type = element_key.split('-', 1)[1]
                        if element_type not in elements_by_type:
                            elements_by_type[element_type] = []
                        elements_by_type[element_type].append((element_key, bbox))
                    
                    # 按固定顺序绘制不同类型的元素
                    draw_order = ['header', 'math', 'figure', 'figure*', 'figurecap', 'figurecap*',
                                'table', 'table*', 'tablecap', 'tablecap*']
                    
                    for element_type in draw_order:
                        if element_type in elements_by_type:
                            for element_key, bbox in elements_by_type[element_type]:
                                pdf_bbox = self.convert_bbox(bbox, page_height)
                                self.draw_bbox(page, pdf_bbox, element_type, element_key)
                                
                    # 额保存每页的图片
                    page = pdf[page_idx]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x缩放以获得更好的质量
                    img_path = pages_dir / f"page_{page_num}.png"
                    pix.save(str(img_path))
                    
                    # 生成并保存COCO格式标注
                    coco_data = self.convert_to_coco(
                        bbox_data, 
                        page_num,
                        page.rect.height,
                        page.rect.width
                    )
                    annotation_path = annotations_dir / f"page_{page_num}.json"
                    with open(annotation_path, 'w', encoding='utf-8') as f:
                        json.dump(coco_data, f, indent=2, ensure_ascii=False)
                    
                    self.logger.info(f"Saved annotation for page {page_num} to: {annotation_path}")
                
                # 保存标注后的PDF
                pdf.save(str(pdf_output))
                self.logger.info(f"Visualized PDF saved to: {pdf_output}")
                self.logger.info(f"Page images saved to: {pages_dir}")
                
            finally:
                pdf.close()
                
        except Exception as e:
            self.logger.error(f"Error visualizing PDF: {str(e)}")
            raise

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Visualize bounding boxes on PDF')
    parser.add_argument('pdf_file', help='Input PDF file')
    parser.add_argument('bbox_file', help='Input JSON file with bounding boxes')
    parser.add_argument('--output-dir', help='Output directory for PDF and images')
    parser.add_argument('--dpi', type=int, default=200, help='DPI for visualization')
    
    args = parser.parse_args()
    
    visualizer = PdfVisualizer(dpi=args.dpi)
    visualizer.visualize_pdf(args.pdf_file, args.bbox_file, args.output_dir)

if __name__ == '__main__':
    main() 