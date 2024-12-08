import re
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class TableMatch:
    """Store information about a matched table"""
    start: int
    end: int
    content: str
    is_textwidth: bool
    index: int
    caption_pos: Optional[Tuple[int, int]] = None

class LatexTableMarker:
    """Insert position markers into LaTeX tables based on width settings"""
    
    def __init__(self, is_twocolumn: bool = True):
        """
        Initialize the marker
        
        Args:
            is_twocolumn: True for two-column layout, False for one-column layout
        """
        # Patterns for table environments
        self.table_patterns = [
            r'\\begin\{table\*?\}.*?\\end\{table\*?\}',
        ]
        
        # Patterns for width detection
        self.textwidth_patterns = [
            r'\\resizebox\{.*?textwidth\}',  # \resizebox{1.0\textwidth}
            r'\\begin\{tabularx\}\{\\textwidth\}',  # tabularx with textwidth
            r'\\begin\{tabular\}\{.*?textwidth.*?\}',  # tabular with textwidth
        ]
        
        self.compiled_patterns = {
            'table': [re.compile(p, re.DOTALL) for p in self.table_patterns],
            'textwidth': [re.compile(p, re.DOTALL) for p in self.textwidth_patterns],
        }
        self.is_twocolumn = is_twocolumn

    def _is_textwidth_table(self, table_content: str) -> bool:
        """Check if table is set to textwidth"""
        # Check for explicit textwidth settings
        textwidth_indicators = [
            r'\\resizebox\{.*?textwidth\}',  # \resizebox{1.0\textwidth}
            r'\\begin\{tabularx\}\{\\textwidth\}',  # tabularx with textwidth
            r'\\begin\{tabular\}\{.*?textwidth.*?\}',  # tabular with textwidth
            r'\\begin\{table\*\}',  # table* environment (typically full width)
            r'\\setlength\{\\tabcolsep\}.*?\\textwidth',  # manual width setting
        ]
        
        for pattern in textwidth_indicators:
            if re.search(pattern, table_content, re.DOTALL):
                return True
        
        # Check for basic tabular without width specification (default columnwidth)
        basic_tabular = re.search(r'\\begin\{tabular\}\{[^}]*\}', table_content)
        if basic_tabular and 'textwidth' not in basic_tabular.group(0):
            return False
        
        return False

    def _find_tables(self, content: str) -> List[TableMatch]:
        """Find all tables and determine their width settings"""
        tables = []
        table_count = 0
        
        for pattern in self.compiled_patterns['table']:
            for match in pattern.finditer(content):
                table_count += 1
                table_content = match.group(0)
                
                # Create TableMatch object
                table = TableMatch(
                    start=match.start(),
                    end=match.end(),
                    content=table_content,
                    is_textwidth=self._is_textwidth_table(table_content),
                    index=table_count
                )
                
                # Find caption position if exists
                caption_match = re.search(r'\\caption\{([^}]*)\}', table_content)
                if caption_match:
                    caption_start = match.start() + caption_match.start()
                    caption_end = match.start() + caption_match.end()
                    table.caption_pos = (caption_start, caption_end)
                
                tables.append(table)
        
        return tables

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

    def _find_closing_brace(self, content: str, start_pos: int) -> int:
        """找到匹配的右大括号位置"""
        brace_count = 1
        for i, char in enumerate(content[start_pos:], start=start_pos):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return i + 1
        return start_pos

    def _comment_vspaces(self, content: str, start_pos: int, end_pos: int) -> List[Tuple[int, str]]:
        """在指定范围内为所有 \vspace 命令添加注释"""
        markers = []
        search_content = content[start_pos:end_pos]
        # 匹配前面可能有的空白字符
        for vspace_match in re.finditer(r'\s*(\\vspace\{[^}]+\})', search_content):
            # 在 \vspace 命令前面添加注释符号，保持在同一行
            vspace_start = vspace_match.start(1)  # 使用组1来获取实际的 \vspace 开始位置
            markers.append((start_pos + vspace_start, "%"))
        return markers

    def _find_centering_pos(self, content: str) -> int:
        """找到 \centering 命令的位置"""
        centering_match = re.search(r'\\centering\s*', content)
        if centering_match:
            return centering_match.end()
        return 0

    def _handle_resizebox_table(self, table: TableMatch, marker_prefix: str) -> List[Tuple[int, str]]:
        """处理包含 \resizebox 的表格"""
        markers = []
        
        resize_match = re.search(
            r'\\resizebox\{[^}]+\}\{!?\}\s*\{',  # 精确匹配 \resizebox{width}{!}{
            table.content
        )
        if not resize_match:
            return []
            
        # 添加 marker-1 标记在 \resizebox 上面一行
        markers.append((table.start + resize_match.start(), f"\n\\zsavepos{{{marker_prefix}-1}}\n"))
        
        # 找到 \resizebox 的右侧大括号
        brace_count = 1
        end_pos = resize_match.end()
        for i, char in enumerate(table.content[end_pos:], start=end_pos):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i + 1
                    break
        
        # 添加 marker-2 标记在右侧大括号下面一行
        markers.append((table.start + end_pos, f"\n\n\\zsavepos{{{marker_prefix}-2}}%"))
        
        return markers

    def _handle_scalebox_table(self, table: TableMatch, marker_prefix: str) -> List[Tuple[int, str]]:
        """处理包含 \scalebox 的表格"""
        markers = []
        
        scalebox_match = re.search(
            r'\\scalebox\{[^}]+\}\s*\{',  # 精确匹配 \scalebox{scale}{
            table.content
        )
        if not scalebox_match:
            return []
            
        # 添加 marker-1 标记在 \scalebox 上面一行
        markers.append((table.start + scalebox_match.start(), f"\n\\zsavepos{{{marker_prefix}-1}}\n"))
        
        # 找到 \end{tabular} 和右侧大括号
        tabular_end = re.search(r'\\end\{tabular\}[^}]*\}', table.content)
        if tabular_end:
            end_pos = tabular_end.end()
            # 添加 marker-2 标记在右侧大括号下面一行
            markers.append((table.start + end_pos, f"\n\n\\zsavepos{{{marker_prefix}-2}}%"))
        
        return markers

    def _handle_regular_table(self, table: TableMatch, marker_prefix: str) -> List[Tuple[int, str]]:
        """处理普通表格（没有 resize/scale box）"""
        markers = []
        
        # 找到 \begin{tabular} 或 \begin{tabularx} 位置
        tabular_begin = re.search(r'\\begin\{tabular(?:x|y)?\*?\}', table.content)
        if tabular_begin:
            # 添加 marker-1 标记在 \begin{tabular} 上面一行
            markers.append((table.start + tabular_begin.start(), f"\n\\zsavepos{{{marker_prefix}-1}}\n"))
            
            # 找到对应的 \end{tabular} 位置
            tabular_end = re.search(r'\\end\{tabular(?:x|y)?\*?\}', table.content)
            if tabular_end:
                end_pos = table.start + tabular_end.end()
                # 添加 marker-2 标记在 \end{tabular} 后面空一行
                markers.append((end_pos, f"\n\n\\zsavepos{{{marker_prefix}-2}}%"))
        
        return markers

    def _generate_markers(self, table: TableMatch) -> List[Tuple[int, str]]:
        """Generate markers for a table based on its width setting"""
        markers = []
        marker_prefix = "table*" if table.is_textwidth else "table"
        cap_prefix = "tablecap*" if table.is_textwidth else "tablecap"
        
        # 尝试处理 \resizebox 表格
        resize_markers = self._handle_resizebox_table(table, marker_prefix)
        if resize_markers:
            markers.extend(resize_markers)
        else:
            # 尝试处理 \scalebox 表格
            scalebox_markers = self._handle_scalebox_table(table, marker_prefix)
            if scalebox_markers:
                markers.extend(scalebox_markers)
            else:
                # 处理普通表格
                regular_markers = self._handle_regular_table(table, marker_prefix)
                if regular_markers:
                    markers.extend(regular_markers)

        # 处理所有 \vspace
        if markers:
            end_table = re.search(r'\\end\{table\*?\}', table.content)
            if end_table:
                last_marker_pos = markers[-1][0] + len(markers[-1][1])
                vspace_markers = self._comment_vspaces(
                    table.content,
                    last_marker_pos - table.start,
                    end_table.start()
                )
                markers.extend((table.start + pos, marker) for pos, marker in vspace_markers)

        # Add caption markers if caption exists
        if table.caption_pos:
            caption_start, _ = table.caption_pos
            caption_end = self._find_caption_end(table.content, 
                                               caption_start - table.start) + table.start
            
            # 如果前面有 table*-2，需要空一行
            if any(marker_prefix in marker[1] for marker in markers):
                markers.extend([
                    (caption_start, f"\n\\zsavepos{{{cap_prefix}-1}}"),
                    (caption_end, f"\\zsavepos{{{cap_prefix}-2}}")
                ])
            else:
                markers.extend([
                    (caption_start, f"\\zsavepos{{{cap_prefix}-1}}"),
                    (caption_end, f"\\zsavepos{{{cap_prefix}-2}}")
                ])
        
        # Add zlabel before \end{table}
        end_table_match = re.search(r'\\end\{table\*?\}', table.content)
        if end_table_match:
            end_pos = table.start + end_table_match.start()
            markers.append((end_pos, f"\n    \\zlabel{{{marker_prefix}}}\n"))
        
        return markers

    def insert_markers(self, content: str) -> str:
        """Insert position markers into LaTeX tables"""
        # Find all tables
        tables = self._find_tables(content)
        
        # Generate all markers
        all_markers = []
        for table in tables:
            markers = self._generate_markers(table)
            all_markers.extend(markers)
        
        # Sort markers by position (reverse order to maintain positions)
        all_markers.sort(key=lambda x: x[0], reverse=True)
        
        # Insert markers
        marked_content = content
        for pos, marker in all_markers:
            marked_content = marked_content[:pos] + marker + marked_content[pos:]
        
        return marked_content

def process_file(input_file: str, output_file: Optional[str] = None, is_twocolumn: bool = True) -> str:
    """
    Process a LaTeX file and insert table markers
    
    Args:
        input_file: Input LaTeX file path
        output_file: Output file path (optional)
        is_twocolumn: True for two-column layout, False for one-column layout
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        marker = LatexTableMarker(is_twocolumn=is_twocolumn)
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
    
    parser = argparse.ArgumentParser(description='Insert position markers into LaTeX tables')
    parser.add_argument('input_file', help='Input LaTeX file')
    parser.add_argument('--output-file', help='Output file (optional)')
    parser.add_argument('--single-column', action='store_true',
                      help='Use single-column layout (default is two-column)')
    
    args = parser.parse_args()
    
    result = process_file(args.input_file, args.output_file, not args.single_column)
    return 0 if result is not None else 1

if __name__ == "__main__":
    main() 