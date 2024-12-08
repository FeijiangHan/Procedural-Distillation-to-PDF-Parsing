import os
import sys
from pathlib import Path
from typing import Tuple, Optional
import shutil
import logging

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent  # latex-web/backend
sys.path.append(str(project_root))

class PipelineService:
    """统一的编译和标注服务"""
    
    def __init__(self, papers_dir: Path, output_dir: Path):
        self.papers_dir = papers_dir  # latex-web/backend/data/papers
        self.output_dir = output_dir  # latex-web/backend/output
        self.project_root = Path(__file__).parent.parent  # latex-web/backend
        self.logger = logging.getLogger('pipeline_service')
        
    def process_tex(self, paper_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """处理TeX文件：编译并标注
        
        Args:
            paper_id: 论文ID (e.g., arXiv-2412.04472v1)
            
        Returns:
            (success, message, error_details)
        """
        try:
            # 1. 构建输入输出路径
            tex_file = self.papers_dir / paper_id / "paper.tex"  # data/papers/arXiv-2412.04472v1/paper.tex
            if not tex_file.exists():
                return False, None, "TeX file not found"
                
            tex_dir = tex_file.parent  # data/papers/arXiv-2412.04472v1
            marked_tex = tex_dir / "paper_marked.tex"  # data/papers/arXiv-2412.04472v1/paper_marked.tex
            
            # 修改这里，直接使用 output_dir 而不是再加 paper_id
            output_dir = self.output_dir  # latex-web/backend/output
            vis_dir = self.project_root / "visualizations"  # latex-web/backend/visualizations
            
            # 创建必要的目录
            output_dir.mkdir(parents=True, exist_ok=True)
            vis_dir.mkdir(parents=True, exist_ok=True)
            
            # 2. 标记LaTeX文件
            self.logger.info("Step 1: Marking LaTeX file...")
            from latex_marker.latex_marker import LatexMarker
            marker = LatexMarker(is_twocolumn=False)
            
            # 读取输入文件
            with open(tex_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 处理所有输入文件
            content = marker._process_input_files(content, tex_file.parent)
            
            # 处理主文件内容
            marked_content = marker.process_content(content)
            
            # 写入输出文件
            with open(marked_tex, 'w', encoding='utf-8') as f:
                f.write(marked_content)
                
            if marked_content is None:
                return False, None, "Marking failed"
            
            # 3. 编译标记后的LaTeX文件
            self.logger.info("Step 2: Compiling marked LaTeX...")
            from process_tex.latex_compiler import LatexCompiler
            compiler = LatexCompiler(output_dir=str(output_dir))
            success = compiler.compile(
                str(marked_tex),
                clean_auxiliary=False
            )
            if not success:
                return False, None, "Compilation failed"
                
            # 4. 处理aux文件
            self.logger.info("Step 3: Processing aux file...")
            aux_file = output_dir / paper_id / "paper.aux"
            if not aux_file.exists():
                return False, None, "AUX file not found"
                
            from process_aux.aux_processor import AuxProcessor
            processor = AuxProcessor()
            ordered_aux = output_dir / paper_id / "paper_ordered.aux"
            processor.process_file(
                str(aux_file),
                str(ordered_aux)
            )
            
            # 5. 提取坐标
            self.logger.info("Step 4: Extracting coordinates...")
            if not ordered_aux.exists():
                return False, None, "Ordered AUX file not found"
                
            from process_aux.coordinate_extractor import CoordinateExtractor
            extractor = CoordinateExtractor()
            coords_file = output_dir / paper_id / "latex_coordinates.json"
            extractor.process_file(
                str(ordered_aux),
                str(coords_file)
            )
            
            # 6. 计算边界框
            self.logger.info("Step 5: Calculating bounding boxes...")
            if not coords_file.exists():
                return False, None, "Coordinates file not found"
                
            bbox_file = output_dir / paper_id / "latex_coordinates_bbox.json"
            from process_aux.bbox_calculator import BBoxCalculator
            calculator = BBoxCalculator()
            calculator.process_file(
                str(coords_file),
                str(bbox_file)
            )
            
            # 7. 可视化PDF
            self.logger.info("Step 6: Visualizing PDF...")
            pdf_file = output_dir / paper_id / "paper.pdf"
            vis_dir = self.project_root / "visualizations" / paper_id
            vis_dir.mkdir(parents=True, exist_ok=True)
            
            from process_aux.visualize_pdf import PdfVisualizer
            visualizer = PdfVisualizer()
            visualizer.visualize_pdf(
                str(pdf_file),
                str(bbox_file),
                str(vis_dir)
            )
            
            # 检查标注后的PDF是否生成
            marked_pdf = vis_dir / "paper_marked.pdf"
            self.logger.info(f"Created marked PDF at: {marked_pdf}")
            if not marked_pdf.exists():
                return False, None, "Failed to create marked PDF"
            
            return True, "Processing completed successfully", None
            
        except Exception as e:
            self.logger.error(f"Processing error: {str(e)}")
            return False, None, str(e)