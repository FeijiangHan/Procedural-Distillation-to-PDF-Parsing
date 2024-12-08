import os
import sys
from pathlib import Path
from typing import Tuple, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

# 直接导入需要的类和函数
from process_aux.aux_processor import AuxProcessor
from process_aux.coordinate_extractor import CoordinateExtractor
from process_aux.bbox_calculator import BBoxCalculator
from process_aux.visualize_pdf import PdfVisualizer

class MarkerService:
    """PDF标注服务"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.project_root = output_dir.parent.parent.parent  # tex2bbox目录
        self.logger = None
        
    def mark_pdf(self, paper_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """标注PDF文件"""
        try:
            # 构建路径，与shell脚本保持一致
            tex_file = f"data/papers/{paper_id}/paper.tex"
            tex_path = self.project_root / tex_file
            
            if not tex_path.exists():
                self.logger.error("TeX file not found")
                return False, None, "TeX file not found"
                
            # 构建目录和文件路径
            base_name = tex_path.parent.name
            output_dir = self.project_root / "output" / base_name
            vis_dir = self.project_root / "visualizations" / base_name
            
            # 检查编译后的PDF是否存在
            pdf_path = output_dir / "paper.pdf"
            if not pdf_path.exists():
                self.logger.error("PDF file not found")
                return False, None, "PDF file not found"
                
            # 创建必要的目
            output_dir.mkdir(parents=True, exist_ok=True)
            vis_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                # 1. 处理aux文件
                self.logger.info("Step 1: Processing aux file...")
                aux_file = output_dir / "paper.aux"
                if not aux_file.exists():
                    self.logger.error("AUX file not found")
                    return False, None, "AUX file not found"
                    
                aux_processor = AuxProcessor()
                aux_processor.process(aux_file)
                
                # 2. 提取坐标
                self.logger.info("Step 2: Extracting coordinates...")
                ordered_aux = output_dir / "paper_ordered.aux"
                if not ordered_aux.exists():
                    self.logger.error("Ordered AUX file not found")
                    return False, None, "Ordered AUX file not found"
                    
                extractor = CoordinateExtractor()
                extractor.extract(ordered_aux)
                
                # 3. 计算边界框
                self.logger.info("Step 3: Calculating bounding boxes...")
                coords_file = output_dir / "latex_coordinates.json"
                bbox_file = output_dir / "latex_coordinates_bbox.json"
                if not coords_file.exists():
                    self.logger.error("Coordinates file not found")
                    return False, None, "Coordinates file not found"
                    
                BBoxCalculator(
                    str(coords_file),
                    output_file=str(bbox_file)
                )
                
                # 4. 可视化PDF
                self.logger.info("Step 4: Visualizing PDF...")
                if not bbox_file.exists():
                    self.logger.error("Bounding box file not found")
                    return False, None, "Bounding box file not found"
                    
                visualizer = PdfVisualizer()
                visualizer.visualize_pdf(
                    pdf_path,
                    bbox_file,
                    vis_dir / "paper.marked.pdf"
                )
                
                # 检查最终输出文件
                marked_pdf = vis_dir / "paper.marked.pdf"
                if not marked_pdf.exists():
                    self.logger.error("Marked PDF not generated")
                    return False, None, "Marked PDF not generated"
                
                self.logger.info("Mark pipeline completed successfully!")
                return True, "Marking successful", None
                
            except Exception as e:
                self.logger.error(f"Error in marking process: {str(e)}")
                return False, None, str(e)
                
        except Exception as e:
            self.logger.error(f"Marking pipeline failed: {str(e)}")
            return False, None, "Marking pipeline failed" 