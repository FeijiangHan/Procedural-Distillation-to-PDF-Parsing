import re
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class MathMatch:
    """Store information about a matched equation"""
    start: int
    end: int
    content: str
    env_type: str  # 'equation'

class LatexMathMarker:
    """Insert position markers into LaTeX equations"""
    
    def __init__(self):
        # Pattern for equation environment
        self.math_patterns = {
            'equation': r'\\begin\{equation\*?\}.*?\\end\{equation\*?\}'
        }
        
        # Compile patterns
        self.compiled_patterns = {
            env_type: re.compile(pattern, re.DOTALL) 
            for env_type, pattern in self.math_patterns.items()
        }

    def _find_equations(self, content: str) -> List[MathMatch]:
        """Find all equations in the content"""
        equations = []
        
        for env_type, pattern in self.compiled_patterns.items():
            for match in pattern.finditer(content):
                equations.append(MathMatch(
                    start=match.start(),
                    end=match.end(),
                    content=match.group(0),
                    env_type=env_type
                ))
        
        # Sort equations by position
        equations.sort(key=lambda x: x.start)
        return equations

    def _generate_markers(self, equation: MathMatch) -> List[Tuple[int, str]]:
        """Generate markers for an equation"""
        markers = []
        
        # Find begin and end positions
        begin_match = re.search(r'\\begin\{equation\*?\}', equation.content)
        end_match = re.search(r'\\end\{equation\*?\}', equation.content)
        
        if begin_match and end_match:
            # 检查前面是否已经有空行
            content_before = self.current_content[:equation.start].rstrip()
            needs_newline_before = not content_before.endswith('\n\n')
            
            # Position before \begin{equation}
            prefix = '\n\n' if needs_newline_before else '\n'
            markers.append(
                (equation.start, f"{prefix}\\zsavepos{{math-1}}\n")
            )
            
            # Position after \begin{equation}
            begin_pos = equation.start + begin_match.end()
            markers.append(
                (begin_pos, "\n\\zlabel{math}\n    \\zsavepos{math-2}")
            )
            
            # Position before \end{equation}
            end_pos = equation.start + end_match.start()
            markers.extend([
                (end_pos, "    \\zsavepos{math-3}")
            ])
            
            # 检查后面是否已经有空行
            content_after = self.current_content[equation.end:].lstrip()
            needs_newline_after = not content_after.startswith('\n\n')
            
            # Position after \end{equation}
            suffix = '\n\n' if needs_newline_after else '\n'
            markers.append(
                (equation.end, f"\n\\zsavepos{{math-4}}{suffix}")
            )
        
        return markers

    def insert_markers(self, content: str) -> str:
        """Insert position markers into LaTeX equations"""
        # Store content for _generate_markers to use
        self.current_content = content
        
        # Find all equations
        equations = self._find_equations(content)
        
        # Generate all markers
        all_markers = []
        for equation in equations:
            markers = self._generate_markers(equation)
            all_markers.extend(markers)
        
        # Sort markers by position (reverse order to maintain positions)
        all_markers.sort(key=lambda x: x[0], reverse=True)
        
        # Insert markers
        marked_content = content
        for pos, marker in all_markers:
            marked_content = marked_content[:pos] + marker + marked_content[pos:]
        
        # Clean up consecutive equations
        marked_content = self._clean_consecutive_equations(marked_content)
        
        return marked_content

    def _clean_consecutive_equations(self, content: str) -> str:
        """Remove extra newlines between consecutive equations"""
        # Find all math-4 followed by math-1 patterns
        pattern = r'\\zsavepos\{math-4\}\n+\\zsavepos\{math-1\}'
        
        # Replace with exactly one blank line between them
        cleaned_content = re.sub(pattern, r'\\zsavepos{math-4}\n\n\\zsavepos{math-1}', content)
        
        return cleaned_content

def process_file(input_file: str, output_file: Optional[str] = None) -> str:
    """Process a LaTeX file and insert equation markers"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        marker = LatexMathMarker()
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
    
    parser = argparse.ArgumentParser(description='Insert position markers into LaTeX equations')
    parser.add_argument('input_file', help='Input LaTeX file')
    parser.add_argument('--output-file', help='Output file (optional)')
    
    args = parser.parse_args()
    
    result = process_file(args.input_file, args.output_file)
    return 0 if result is not None else 1

if __name__ == "__main__":
    main() 