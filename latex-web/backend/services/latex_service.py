import os
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

# 导入项目模块
from latex_marker import LatexMarker
from process_tex.latex_compiler import LatexCompiler

class LatexService:
    """LaTeX编译服务"""
    
    def __init__(self, papers_dir: Path, output_dir: Path, temp_dir: Path):
        self.papers_dir = papers_dir
        self.output_dir = output_dir
        self.temp_dir = temp_dir
        self.project_root = self.papers_dir.parent.parent  # tex2bbox目录
        self.logger = None
        
    def compile_tex(self, paper_id: str, tex_file: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """编译LaTeX文件"""
        try:
            # 构建路径，与shell脚本保持一致
            tex_file = f"data/papers/{paper_id}/paper.tex"  # 使用固定的paper.tex
            tex_path = self.project_root / tex_file
            
            if not tex_path.exists():
                self.logger.error(f"TeX file not found: {tex_path}")
                return False, None, "TeX file not found"
                
            # 构建输出目录路径
            base_name = tex_path.parent.name  # 例如：arXiv-2412.04472v1
            output_dir = self.project_root / "output" / base_name  # 直接使用最终目录
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 编译LaTeX文件
            compiler = LatexCompiler()  # 不需要指定output_dir，它会使用默认值
            success = compiler.compile(
                str(tex_path),  # 直接传递文件路径
                clean_auxiliary=False  # 使用正确的参数名
            )
            
            if not success:
                self.logger.error("Compilation failed")
                return False, None, "Compilation failed"
                
            # 检查最终的PDF文件
            output_pdf = output_dir / "paper.pdf"
            if not output_pdf.exists():
                self.logger.error("PDF not generated")
                return False, None, "PDF not generated"
                
            return True, "Compilation successful", None
            
        except Exception as e:
            self.logger.error(f"Compilation error: {str(e)}")
            return False, None, str(e) 