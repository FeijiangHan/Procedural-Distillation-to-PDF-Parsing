from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
from utils.logger import setup_logger
from utils.cache import FileCache

logger = setup_logger('file_service')

class FileService:
    """文件处理服务"""
    
    def __init__(self, papers_dir: Path, output_dir: Path, cache_dir: Path):
        self.papers_dir = papers_dir
        self.output_dir = output_dir
        self.cache = FileCache(cache_dir)
        self.logger = logger
        self.project_root = Path(__file__).parent.parent  # latex-web/backend
        
    def get_available_papers(self) -> List[Dict]:
        """获取可用的论文列表"""
        cached_papers = self.cache.get('available_papers')
        if cached_papers:
            self.logger.debug("Using cached paper list")
            return cached_papers
            
        try:
            papers = []
            for paper_dir in self.papers_dir.iterdir():
                if paper_dir.is_dir():
                    tex_file = paper_dir / "paper.tex"
                    if tex_file.exists():
                        papers.append({
                            "id": paper_dir.name,
                            "name": paper_dir.name,
                            "texFile": f"papers/{paper_dir.name}/paper.tex"
                        })
                        
            self.cache.set('available_papers', papers)
            self.logger.info(f"Found {len(papers)} papers")
            return papers
            
        except Exception as e:
            self.logger.error(f"Error scanning papers: {str(e)}")
            raise
        
    def get_tex_content(self, paper_id: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """获取TeX文件内容"""
        try:
            tex_file = self.papers_dir / paper_id / "paper.tex"
            
            if not tex_file.exists():
                return None, None, "TeX file not found"
                
            with open(tex_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return content, tex_file.name, None
            
        except Exception as e:
            return None, None, str(e)
            
    def get_pdf_path(self, paper_id: str) -> Optional[Path]:
        """获取PDF文件路径"""
        # 查找的输出目录结构
        pdf_path = self.project_root / "output" / paper_id / "paper.pdf"
        if pdf_path.exists():
            return pdf_path
            
        self.logger.warning(f"PDF not found for paper {paper_id}")
        return None
        
    def get_marked_pdf_paths(self, paper_id: str) -> List[Path]:
        """获取标注后的PDF文件路径"""
        # 使用新的路径结构
        marked_pdf = self.project_root / "visualizations" / paper_id / "paper_marked.pdf"
        self.logger.debug(f"Looking for marked PDF at: {marked_pdf}")
        if marked_pdf.exists():
            self.logger.info(f"Found marked PDF: {marked_pdf}")
            return [marked_pdf]
        self.logger.warning(f"Marked PDF not found at: {marked_pdf}")
        return [] 