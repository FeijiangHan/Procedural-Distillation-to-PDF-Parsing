import re
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class HeadingMatch:
    """Store information about a matched heading"""
    start: int
    end: int
    content: str
    level: str  # 'section', 'subsection', etc.

class LatexHeadingMarker:
    """Insert position markers into LaTeX headings"""
    
    def __init__(self):
        # Only match section, subsection, subsubsection, and paragraph
        self.heading_patterns = {
            'section': r'\\section\*?\{[^}]*\}',
            'subsection': r'\\subsection\*?\{[^}]*\}',
            'subsubsection': r'\\subsubsection\*?\{[^}]*\}',
            # 'paragraph': r'\\paragraph\*?\{[^}]*\}'
        }
        
        # Compile patterns
        self.compiled_patterns = {
            level: re.compile(pattern) for level, pattern in self.heading_patterns.items()
        }

    def _find_headings(self, content: str) -> List[HeadingMatch]:
        """Find all headings in the content"""
        headings = []
        
        for level, pattern in self.compiled_patterns.items():
            for match in pattern.finditer(content):
                headings.append(HeadingMatch(
                    start=match.start(),
                    end=match.end(),
                    content=match.group(0),
                    level=level
                ))
        
        # Sort headings by position
        headings.sort(key=lambda x: x.start)
        return headings

    def _find_previous_end_environment(self, content: str, start_pos: int) -> bool:
        """检查前面最近的元素是否是 figure/table 的结束标记
        
        Args:
            content: 文本内容
            start_pos: 当前位置
            
        Returns:
            bool: 如果前面是 figure/table 结束标记返回 True，否则返回 False
        """
        # 获取前面的内容
        previous_content = content[:start_pos].rstrip()
        if not previous_content:
            return False
        
        # 查找最后一个非空行
        last_line = previous_content.split('\n')[-1].strip()
        
        # 检查是否是 figure 或 table 的结束标记
        end_patterns = [
            r'\\end\{figure\*?\}',
            r'\\end\{table\*?\}'
        ]
        
        for pattern in end_patterns:
            if re.match(pattern, last_line):
                return True
            
        return False

    def _generate_markers(self, heading: HeadingMatch) -> List[Tuple[int, str]]:
        """Generate markers for a heading"""
        markers = []
        
        # Find the positions of opening and closing braces
        brace_match = re.search(r'\{([^}]*)\}', heading.content)
        if brace_match:
            # 在标题前添加固定的命令
            prefix = (
                "\n\\phantom{Invisible Text}\n"
                "\\vspace{-\\baselineskip}\n"
                "\n"
                "\\zsavepos{header-1}"
            )
            markers.append((heading.start, prefix))
            
            # Position before the closing brace
            content_end = heading.start + brace_match.end(0) - 1
            
            # Position after the closing brace
            after_brace = heading.start + brace_match.end(0)
            
            # Add header-2 before closing brace, header-3 and zlabel after closing brace
            markers.extend([
                (content_end, f"\\zsavepos{{header-2}}"),
                (after_brace, f"\\zsavepos{{header-3}}\\zlabel{{header}}\n")
            ])
        
        return markers

    def insert_markers(self, content: str) -> str:
        """Insert position markers into LaTeX headings"""
        # Store content for _find_previous_end_environment to use
        self.current_content = content
        
        # Find all headings
        headings = self._find_headings(content)
        
        # Generate all markers
        all_markers = []
        for heading in headings:
            # 检查前后是否已经有空行
            has_newline_before = content[max(0, heading.start-1):heading.start].endswith('\n')
            has_newline_after = content[heading.end:min(len(content), heading.end+1)].startswith('\n')
            
            markers = self._generate_markers(heading)
            
            # 如果前后没有空行，添加相应的标记
            if not has_newline_before:
                markers.append((heading.start, "\n"))
            if not has_newline_after:
                markers.append((heading.end, "\n"))
            
            all_markers.extend(markers)
        
        # Sort markers by position (reverse order to maintain positions)
        all_markers.sort(key=lambda x: x[0], reverse=True)
        
        # Insert markers
        marked_content = content
        for pos, marker in all_markers:
            marked_content = marked_content[:pos] + marker + marked_content[pos:]
        
        return marked_content

def process_file(input_file: str, output_file: Optional[str] = None) -> str:
    """Process a LaTeX file and insert heading markers"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        marker = LatexHeadingMarker()
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
    
    parser = argparse.ArgumentParser(description='Insert position markers into LaTeX headings')
    parser.add_argument('input_file', help='Input LaTeX file')
    parser.add_argument('--output-file', help='Output file (optional)')
    
    args = parser.parse_args()
    
    result = process_file(args.input_file, args.output_file)
    return 0 if result is not None else 1

if __name__ == "__main__":
    main() 