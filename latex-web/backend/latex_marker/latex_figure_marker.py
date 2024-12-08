import re
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class FigureMatch:
    """Store information about a matched figure"""
    start: int
    end: int
    content: str
    is_double_column: bool  # True for textwidth/linewidth or figure*
    has_subfigures: bool
    caption_pos: Optional[Tuple[int, int]] = None

class LatexFigureMarker:
    """Insert position markers into LaTeX figures based on width settings"""
    
    def __init__(self):
        # Patterns for figure environments
        self.figure_patterns = [
            r'\\begin\{figure\*?\}.*?\\end\{figure\*?\}',
        ]
        
        # Patterns for width detection
        self.double_column_indicators = [
            r'\\includegraphics\[.*?(?:textwidth|linewidth).*?\]',
            r'\\begin\{figure\*\}'
        ]
        
        # Pattern for subfigures
        self.subfigure_pattern = r'\\subfigure\['
        
        # 添加表格检测模式
        self.nested_table_pattern = re.compile(r'\\begin\{tabular\}.*?\\end\{tabular\}', re.DOTALL)
        
        # 修改宽度检测模式，使其更精确
        self.width_pattern = re.compile(r'\\includegraphics\[.*?width\s*=\s*(.*?)(?:,|\])')
        
        self.compiled_patterns = {
            'figure': [re.compile(p, re.DOTALL) for p in self.figure_patterns],
            'double_column': [re.compile(p, re.DOTALL) for p in self.double_column_indicators],
            'subfigure': re.compile(self.subfigure_pattern)
        }

    def _calculate_group_width(self, content: str) -> float:
        """计算分组图片的总宽度比例"""
        # 找到所有的 includegraphics 命令
        width_pattern = r'\\includegraphics\[.*?width\s*=\s*([\d.]+)\\(?:textwidth|linewidth)[^\]]*\]'
        
        # 按行分割内容
        lines = content.split('\\\\')
        max_line_width = 0.0
        
        for line in lines:
            # 找到这一行中所有的宽度设置
            widths = re.findall(width_pattern, line)
            if widths:
                # 将字符串转换为浮点数并求和
                line_width = sum(float(w) for w in widths)
                max_line_width = max(max_line_width, line_width)
        
        return max_line_width

    def _is_double_column(self, figure_content: str) -> bool:
        """Check if figure is double column width
        
        双栏图的判断规则：
        1. 如果是 figure* 环境，一定是双栏
        2. 如果是普通 figure 环境：
           - 检查 \includegraphics 的宽度设置
           - 如果包含 \textwidth，需要进一步判断：
             a. 如果是分组图片（包含 & 和 \\），计算每行的总宽度
             b. 如果总宽度 > 0.5，则是双栏
             c. 如果总宽度 <= 0.5，则是单栏
           - 如果是单个图片且使用 \textwidth，则是双栏
           - 如果使用 \linewidth，则是单栏
        """
        # 首先检查是否是 figure* 环境
        if r'\begin{figure*}' in figure_content:
            return True
            
        # 检查是否是分组图片
        if '&' in figure_content and '\\\\' in figure_content:
            total_width = self._calculate_group_width(figure_content)
            # 如果总宽度大于 0.5，认为是双栏
            return total_width > 0.5
            
        # 对于单个图片，检查宽度设置
        width_matches = self.width_pattern.finditer(figure_content)
        for match in width_matches:
            width_value = match.group(1).strip()
            if r'\textwidth' in width_value:
                # 对于单个图片，使用 \textwidth 就是双栏
                return True
            if r'\linewidth' in width_value:
                return False
                
        return False

    def _has_subfigures(self, figure_content: str) -> bool:
        """Check if figure contains subfigures"""
        return bool(self.compiled_patterns['subfigure'].search(figure_content))

    def _find_figures(self, content: str) -> List[FigureMatch]:
        """Find all figures and determine their properties"""
        figures = []
        
        for pattern in self.compiled_patterns['figure']:
            for match in pattern.finditer(content):
                figure_content = match.group(0)
                
                # Create FigureMatch object
                figure = FigureMatch(
                    start=match.start(),
                    end=match.end(),
                    content=figure_content,
                    is_double_column=self._is_double_column(figure_content),
                    has_subfigures=self._has_subfigures(figure_content)
                )
                
                # Find caption position if exists
                caption_match = re.search(r'\\caption\{([^}]*)\}', figure_content)
                if caption_match:
                    caption_start = match.start() + caption_match.start()
                    caption_end = match.start() + caption_match.end()
                    figure.caption_pos = (caption_start, caption_end)
                
                figures.append(figure)
        
        return figures

    def _generate_markers(self, figure: FigureMatch) -> List[Tuple[int, str]]:
        """Generate markers for a figure based on its properties"""
        markers = []
        
        # Determine figure type based on double column check
        marker_prefix = "figure*" if figure.is_double_column else "figure"
        cap_prefix = "figurecap*" if figure.is_double_column else "figurecap"
        
        # Find position for first marker (after \begin{figure})
        begin_match = re.search(r'\\begin\{figure\*?\}(\[.*?\])?', figure.content)
        if begin_match:
            marker_pos = figure.start + begin_match.end()
            markers.append((marker_pos, f"\n    \\zsavepos{{{marker_prefix}-1}}"))
        
        # 检查是否包含嵌套的表格
        nested_table = self.nested_table_pattern.search(figure.content)
        if nested_table:
            # 找到表格结束位置
            table_end = figure.start + nested_table.end()
            
            # 检查表格结束后是否有 \vspace
            content_after_table = figure.content[nested_table.end():]
            vspace_match = re.search(r'(\s*)(\\vspace\{[^}]+\})', content_after_table)
            if vspace_match:
                vspace_start = nested_table.end() + vspace_match.start(2)
                # 在 \vspace 前插入注释符号
                markers.append((figure.start + vspace_start, "%"))
            
            # 在表格结束后添加第二个标记（空一行）
            markers.append((table_end, f"\n\n\\zsavepos{{{marker_prefix}-2}}"))
            
            # 检查 figure*-2 后是否有 \vspace
            content_after_marker = figure.content[table_end:]
            vspace_after_match = re.search(r'\n\s*(\\vspace\{[^}]+\})', content_after_marker)
            if vspace_after_match:
                vspace_start = table_end + vspace_after_match.start(1)
                # 在 \vspace 前插入注释符号
                markers.append((figure.start + vspace_start, "%"))
        else:
            # 处理普通图片的情况
            if figure.has_subfigures:
                # Handle subfigures case
                content = figure.content
                pos = 0
                last_subfigure_end = None
                
                while True:
                    subfigure_match = re.search(r'\\subfigure\[.*?\]', content[pos:])
                    if not subfigure_match:
                        break
                    
                    start_pos = pos + subfigure_match.end()
                    # Find matching closing brace for the subfigure content
                    brace_count = 0
                    content_end = start_pos
                    
                    for i, char in enumerate(content[start_pos:], start=start_pos):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                content_end = i + 1
                                break
                    
                    if content_end > start_pos:
                        last_subfigure_end = figure.start + content_end
                        pos = content_end
                    else:
                        break
                
                if last_subfigure_end:
                    # 检查 subfigure 结束后是否有 \vspace
                    content_after_subfig = figure.content[last_subfigure_end - figure.start:]
                    vspace_match = re.search(r'(\s*)(\\vspace\{[^}]+\})', content_after_subfig)
                    if vspace_match:
                        vspace_start = last_subfigure_end + vspace_match.start(2)
                        markers.append((vspace_start, "%"))
                    
                    markers.append((last_subfigure_end, f"\n\n\\zsavepos{{{marker_prefix}-2}}\n"))
                    
                    # 检查 figure*-2 后是否有 \vspace
                    vspace_after_match = re.search(r'\n\s*(\\vspace\{[^}]+\})', content_after_subfig)
                    if vspace_after_match:
                        vspace_start = last_subfigure_end + vspace_after_match.start(1)
                        markers.append((vspace_start, "%"))
            else:
                # Handle single figure case
                includegraphics = re.search(r'\\includegraphics\[.*?\]\{.*?\}', figure.content)
                if includegraphics:
                    marker_pos = figure.start + includegraphics.end()
                    
                    # 检查 includegraphics 后是否有 \vspace
                    content_after_img = figure.content[includegraphics.end():]
                    vspace_match = re.search(r'(\s*)(\\vspace\{[^}]+\})', content_after_img)
                    if vspace_match:
                        vspace_start = marker_pos + vspace_match.start(2)
                        markers.append((vspace_start, "%"))
                    
                    markers.append((marker_pos, f"\n    \\zsavepos{{{marker_prefix}-2}}\n"))
                    
                    # 检查 figure*-2 后是否有 \vspace
                    vspace_after_match = re.search(r'\n\s*(\\vspace\{[^}]+\})', content_after_img)
                    if vspace_after_match:
                        vspace_start = marker_pos + vspace_after_match.start(1)
                        markers.append((vspace_start, "%"))
        
        # Add caption markers if caption exists
        if figure.caption_pos:
            caption_start, _ = figure.caption_pos
            # Find the true end of the caption command
            caption_end = self._find_caption_end(figure.content, 
                                               caption_start - figure.start) + figure.start
            
            markers.extend([
                (caption_start, f"\\zsavepos{{{cap_prefix}-1}}"),  # Before \caption
                (caption_end, f"\\zsavepos{{{cap_prefix}-2}}")  # After the entire caption command
            ])
        
        # Add zlabel before \end{figure}
        end_figure_match = re.search(r'\\end\{figure\*?\}', figure.content)
        if end_figure_match:
            end_pos = figure.start + end_figure_match.start()
            markers.append((end_pos, f"\n    \\zlabel{{{marker_prefix}}}\n"))
        
        return markers

    def _clean_figure_content(self, content: str) -> str:
        """Remove all blank lines within figure environment"""
        # Find all figure environments
        figure_matches = []
        for pattern in self.compiled_patterns['figure']:
            figure_matches.extend(pattern.finditer(content))
        
        # Process content in reverse order to maintain positions
        figure_matches = sorted(figure_matches, key=lambda x: x.start(), reverse=True)
        cleaned_content = content
        
        for match in figure_matches:
            figure_content = match.group(0)
            # Remove consecutive blank lines, preserving indentation
            cleaned_figure = re.sub(r'\n\s*\n', '\n', figure_content)
            # Replace original content
            cleaned_content = (
                cleaned_content[:match.start()] +
                cleaned_figure +
                cleaned_content[match.end():]
            )
        
        return cleaned_content

    def insert_markers(self, content: str) -> str:
        """Insert position markers into LaTeX figures"""
        # First clean up blank lines in figures
        content = self._clean_figure_content(content)
        
        # Find all figures
        figures = self._find_figures(content)
        
        # Generate all markers
        all_markers = []
        for figure in figures:
            markers = self._generate_markers(figure)
            all_markers.extend(markers)
        
        # Sort markers by position (reverse order to maintain positions)
        all_markers.sort(key=lambda x: x[0], reverse=True)
        
        # Insert markers
        marked_content = content
        for pos, marker in all_markers:
            marked_content = marked_content[:pos] + marker + marked_content[pos:]
        
        return marked_content

    def _find_caption_end(self, content: str, start_pos: int) -> int:
        """Find the true end position of a caption command by matching braces"""
        brace_count = 0
        in_math = False
        math_symbol = None
        
        for i, char in enumerate(content[start_pos:], start=start_pos):
            if char == '$':
                in_math = not in_math
                math_symbol = '$'
            elif char == '{' and not in_math:
                brace_count += 1
            elif char == '}' and not in_math:
                brace_count -= 1
                if brace_count == 0:
                    return i + 1  # Return position after the closing brace
        
        return start_pos  # Return original position if no match found

def process_file(input_file: str, output_file: Optional[str] = None) -> str:
    """Process a LaTeX file and insert figure markers"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        marker = LatexFigureMarker()
        marked_content = marker.insert_markers(content)
        
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
    
    parser = argparse.ArgumentParser(description='Insert position markers into LaTeX figures')
    parser.add_argument('input_file', help='Input LaTeX file')
    parser.add_argument('--output-file', help='Output file (optional)')
    
    args = parser.parse_args()
    
    result = process_file(args.input_file, args.output_file)
    return 0 if result is not None else 1

if __name__ == "__main__":
    exit(main()) 