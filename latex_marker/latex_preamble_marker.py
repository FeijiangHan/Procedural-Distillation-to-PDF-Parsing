import re
from typing import List, Tuple, Optional
from pathlib import Path

class LatexPreambleMarker:
    """Insert required packages and commands into LaTeX preamble"""
    
    def __init__(self):
        self.required_packages = [
            "zref-savepos",
            "zref-user",
            "layouts"
        ]
        
        self.required_commands = r"""
\makeatletter
\protected@write\@auxout{}{
    \string\newlabel{columnwidth}{{\the\columnwidth}}
}
\protected@write\@auxout{}{
    \string\newlabel{textwidth}{{\the\textwidth}}
}
\protected@write\@auxout{}{
    \string\newlabel{lineheight}{{\the\baselineskip}}
}
\protected@write\@auxout{}{
    \string\newlabel{linewidth}{{\the\linewidth}}
}
\protected@write\@auxout{}{
    \string\newlabel{textheight}{{\the\textheight}}
}
\protected@write\@auxout{}{
    \string\newlabel{paperheight}{{\the\paperheight}}
}
\protected@write\@auxout{}{
    \string\newlabel{headsep}{{\the\headsep}}
}
\protected@write\@auxout{}{
    \string\newlabel{footskip}{{\the\footskip}}
}
\makeatother
"""

    def _preprocess_content(self, content: str) -> str:
        """预处理 LaTeX 内容
        
        1. 移除注释（保留%符号）
        2. 合并多个空行为单个空行
        3. 删除 \section 后面的 \columnbreak
        """
        # 首先删除 \section 后面的 \columnbreak
        content = re.sub(
            r'(\\section\*?\{[^}]*\})\s*\\columnbreak',
            r'\1',
            content
        )
        
        lines = content.split('\n')
        result = []
        empty_line_count = 0
        
        for line in lines:
            # 处理每一行，处理转义的%和注释
            processed_line = ''
            i = 0
            while i < len(line):
                if line[i:i+2] == '\\%':
                    processed_line += '\\%'
                    i += 2
                elif line[i] == '%':
                    # 保留%符号但移除注释内容
                    processed_line += '%'
                    break
                else:
                    processed_line += line[i]
                    i += 1
            
            processed_line = processed_line.rstrip()
            
            # 处理空行
            if not processed_line or processed_line == '%':
                empty_line_count += 1
                if empty_line_count <= 1:  # 只保留第一个空行
                    result.append(processed_line)
            else:
                empty_line_count = 0  # 重置非空行的计数器
                result.append(processed_line)
        
        # 合并行，保留单个空行
        return '\n'.join(result)

    def _find_document_begin(self, content: str) -> int:
        """Find the position of \begin{document}"""
        match = re.search(r'\\begin\{document\}', content)
        return match.start() if match else -1

    def _find_package_insertions(self, content: str) -> List[Tuple[int, str]]:
        """Find positions to insert packages"""
        # Look for last \usepackage command
        last_package = list(re.finditer(r'\\usepackage(\[.*?\])?\{.*?\}', content))
        if last_package:
            pos = last_package[-1].end()
            return [(pos, '\n' + '\n'.join(f"\\usepackage{{{pkg}}}" 
                                          for pkg in self.required_packages))]
        
        # If no packages found, insert after documentclass
        doc_class = re.search(r'\\documentclass(\[.*?\])?\{.*?\}', content)
        if doc_class:
            return [(doc_class.end(), '\n\n' + '\n'.join(f"\\usepackage{{{pkg}}}" 
                                                        for pkg in self.required_packages))]
        
        return []

    def _expand_input_commands(self, content: str, base_dir: str) -> str:
        """展开所有 \input 命令为实际内容
        
        Args:
            content: LaTeX 内容
            base_dir: 基础目录路径
            
        Returns:
            展开后的内容
        """
        def replace_input(match):
            input_path = match.group(1)
            # 移除可能的 .tex 扩展名
            input_path = input_path.replace('.tex', '')
            
            # 构建完整的输入路径
            input_file = Path(base_dir) / f"{input_path}.tex"
            if not input_file.exists():
                print(f"Warning: Input file not found: {input_file}")
                return match.group(0)
            
            try:
                # 读取输入文件
                with open(input_file, 'r', encoding='utf-8') as f:
                    input_content = f.read()
                
                # 递归处理输入文件中的 \input 命令
                return self._expand_input_commands(input_content, str(input_file.parent))
                
            except Exception as e:
                print(f"Error processing input file {input_file}: {str(e)}")
                return match.group(0)
        
        # 查找并替换所有 \input 命令
        pattern = r'\\input\{([^}]+)\}'
        return re.sub(pattern, replace_input, content)

    def insert_markers(self, content: str, base_dir: str = '.') -> str:
        """插入所需的包和命令到 LaTeX 导言区
        
        Args:
            content: LaTeX 内容
            base_dir: 基础目录路径（用于处理 \input 命令）
            
        Returns:
            处理后的内容
        """
        # 首先展开所有 \input 命令
        content = self._expand_input_commands(content, base_dir)
        
        # 预处理内容
        content = self._preprocess_content(content)
        
        # Find \begin{document}
        doc_begin = self._find_document_begin(content)
        if doc_begin == -1:
            print("Warning: \\begin{document} not found")
            return content
        
        # Find positions for package insertions
        package_insertions = self._find_package_insertions(content)
        
        # Add commands before \begin{document}
        all_insertions = package_insertions + [(doc_begin, f"\n\n{self.required_commands}\n")]
        
        # Sort insertions by position (reverse order)
        all_insertions.sort(key=lambda x: x[0], reverse=True)
        
        # Insert packages and commands
        marked_content = content
        for pos, text in all_insertions:
            marked_content = marked_content[:pos] + text + marked_content[pos:]
        
        return marked_content

def process_file(input_file: str, output_file: Optional[str] = None) -> str:
    """处理 LaTeX 文件并插入所需的包和命令"""
    try:
        # 尝试以 UTF-8 读取
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 如果 UTF-8 失败，尝试 latin-1
            with open(input_file, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # 获取输入文件的基础目录
        base_dir = str(Path(input_file).parent)
        
        marker = LatexPreambleMarker()
        marked_content = marker.insert_markers(content, base_dir)
        
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
    
    parser = argparse.ArgumentParser(description='Insert required packages and commands into LaTeX preamble')
    parser.add_argument('input_file', help='Input LaTeX file')
    parser.add_argument('--output-file', help='Output file (optional)')
    
    args = parser.parse_args()
    
    result = process_file(args.input_file, args.output_file)
    return 0 if result is not None else 1

if __name__ == "__main__":
    main() 