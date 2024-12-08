import re
from pathlib import Path
from typing import Optional
from .latex_figure_marker import LatexFigureMarker
from .latex_math_marker import LatexMathMarker
from .latex_heading_marker import LatexHeadingMarker
from .latex_table_marker import LatexTableMarker
from .latex_preamble_marker import LatexPreambleMarker

__all__ = ['LatexMarker']
class LatexMarker:
    """Integrated marker for LaTeX files"""
    
    def __init__(self, is_twocolumn: bool = True):
        """
        Initialize all markers
        
        Args:
            is_twocolumn: True for two-column layout, False for one-column layout
        """
        self.preamble_marker = LatexPreambleMarker()
        self.figure_marker = LatexFigureMarker()
        self.math_marker = LatexMathMarker()
        self.heading_marker = LatexHeadingMarker()
        self.table_marker = LatexTableMarker(is_twocolumn=is_twocolumn)

    def _process_input_files(self, content: str, base_dir: Path) -> str:
        """处理所有 \input 命令，标记输入的文件并更新路径"""
        def replace_input(match):
            input_path = match.group(1)
            # 移除可能存在的 .tex 扩展名
            input_path = input_path.replace('.tex', '')
            
            # 构建完整的输入和输出路径
            input_file = base_dir / f"{input_path}.tex"
            if not input_file.exists():
                print(f"Warning: Input file not found: {input_file}")
                return match.group(0)
            
            # 生成标记后的文件名
            marked_path = f"{input_path}_marked.tex"
            marked_file = base_dir / marked_path
            
            # 处理输入文件
            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    input_content = f.read()
                
                # 递归处理输入文件中的 \input 命令
                input_content = self._process_input_files(input_content, input_file.parent)
                
                # 标记文件内容
                marked_content = self.process_content(input_content, is_input=True)
                
                # 写入标记后的文件
                with open(marked_file, 'w', encoding='utf-8') as f:
                    f.write(marked_content)
                print(f"Processed input file: {input_file} -> {marked_file}")
                
                # 返回更新后的 \input 命令
                return f"\\input{{{marked_path}}}"
                
            except Exception as e:
                print(f"Error processing input file {input_file}: {str(e)}")
                return match.group(0)
        
        # 查找并处理所有 \input 命令
        pattern = r'\\input\{([^}]+)\}'
        return re.sub(pattern, replace_input, content)

    def process_content(self, content: str, is_input: bool = False) -> str:
        """
        Process LaTeX content with all markers
        
        Args:
            content: Input LaTeX content
            is_input: True if processing an input file, False for main file
        """
        try:
            # 只在主文件中插入包和命令
            if not is_input:
                content = self.preamble_marker.insert_markers(content)
            
            # 标记所有元素
            content = self.heading_marker.insert_markers(content)
            content = self.math_marker.insert_markers(content)
            content = self.table_marker.insert_markers(content)
            content = self.figure_marker.insert_markers(content)
            
            return content
        except Exception as e:
            print(f"Error processing content: {str(e)}")
            return content

def process_file(input_file: str, output_file: Optional[str] = None, 
                is_twocolumn: bool = True) -> str:
    """
    Process a LaTeX file with all markers
    
    Args:
        input_file: Input LaTeX file path
        output_file: Output file path (optional)
        is_twocolumn: True for two-column layout, False for one-column layout
    
    Returns:
        Processed LaTeX content
    """
    try:
        # 读取输入文件
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 创建标记器
        marker = LatexMarker(is_twocolumn=is_twocolumn)
        
        # 处理所有输入文件
        base_dir = Path(input_file).parent
        content = marker._process_input_files(content, base_dir)
        
        # 处理主文件内容
        marked_content = marker.process_content(content)
        
        # 写入输出文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(marked_content)
            print(f"Marked content saved to: {output_file}")
        
        return marked_content
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Insert all position markers into LaTeX files')
    parser.add_argument('input_file', help='Input LaTeX file')
    parser.add_argument('--output-file', help='Output file (optional)')
    parser.add_argument('--single-column', action='store_true',
                      help='Use single-column layout (default is two-column)')
    
    args = parser.parse_args()
    
    result = process_file(args.input_file, args.output_file, 
                         is_twocolumn=not args.single_column)
    return 0 if result is not None else 1

if __name__ == "__main__":
    main() 