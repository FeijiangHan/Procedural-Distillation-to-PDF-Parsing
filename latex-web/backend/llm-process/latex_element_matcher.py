import re
from typing import Set, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class LatexElement:
    """LaTeX元素的数据类"""
    type: str
    content: str
    start: int
    end: int

class LatexElementMatcher:
    """LaTeX文档元素匹配器"""
    def __init__(self):
        # 定义各种元素的匹配模式
        self.patterns = {
            'math': [
                # 行间公式
                r'\\begin\{equation\*?\}.*?\\end\{equation\*?\}',
                r'\\begin\{align\*?\}.*?\\end\{align\*?\}',
                r'\\begin\{eqnarray\*?\}.*?\\end\{eqnarray\*?\}',
                r'\\begin\{multline\*?\}.*?\\end\{multline\*?\}',
                r'\\begin\{gather\*?\}.*?\\end\{gather\*?\}',
                r'\$\$.*?\$\$',
                # 行内公式
                r'\$[^$]+\$',
                r'\\begin\{math\}.*?\\end\{math\}',
                r'\\begin\{displaymath\}.*?\\end\{displaymath\}',
                # 其他数学环境
                r'\\begin\{split\}.*?\\end\{split\}',
                r'\\begin\{cases\}.*?\\end\{cases\}',
                r'\\begin\{matrix\}.*?\\end\{matrix\}',
                r'\\begin\{pmatrix\}.*?\\end\{pmatrix\}',
                r'\\begin\{bmatrix\}.*?\\end\{bmatrix\}',
                r'\\begin\{vmatrix\}.*?\\end\{vmatrix\}'
            ],
            'figure': [
                # 基本图片环境
                r'\\begin\{figure\*?\}.*?\\end\{figure\*?\}',
                # 子图
                r'\\subfigure\{.*?\}',
                r'\\subfloat\{.*?\}',
                # includegraphics命令
                r'\\includegraphics(\[.*?\])?\{.*?\}',
                # 其他图片相关
                r'\\begin\{wrapfigure\}.*?\\end\{wrapfigure\}',
                r'\\begin\{floatrow\}.*?\\end\{floatrow\}'
            ],
            # 'figure_caption': [
            #     r'\\caption\{[^}]*\}'
            # ],
            'table': [
                # 基本表格环境
                r'\\begin\{table\*?\}.*?\\end\{table\*?\}',
                r'\\begin\{tabular\}.*?\\end\{tabular\}',
                r'\\begin\{tabularx\}.*?\\end\{tabularx\}',
                r'\\begin\{tabbing\}.*?\\end\{tabbing\}',
                r'\\begin\{longtable\}.*?\\end\{longtable\}',
                # 其他表格相关
                r'\\begin\{threeparttable\}.*?\\end\{threeparttable\}',
                r'\\begin\{supertabular\}.*?\\end\{supertabular\}'
            ],
            # 'table_caption': [
            #     r'\\caption\{[^}]*\}'
            # ],
            'heading': [
                # 章节标题
                r'\\chapter\{[^}]*\}',
                r'\\section\{[^}]*\}',
                r'\\subsection\{[^}]*\}',
                r'\\subsubsection\{[^}]*\}',
                r'\\paragraph\{[^}]*\}',
                r'\\subparagraph\{[^}]*\}',
                # 带星号的变体
                r'\\chapter\*\{[^}]*\}',
                r'\\section\*\{[^}]*\}',
                r'\\subsection\*\{[^}]*\}',
                r'\\subsubsection\*\{[^}]*\}',
                r'\\paragraph\*\{[^}]*\}',
                r'\\subparagraph\*\{[^}]*\}'
            ],
            # 'title': [
            #     # 文档标题相关
            #     r'\\title\{[^}]*\}',
            #     r'\\author\{[^}]*\}',
            #     r'\\date\{[^}]*\}',
            #     r'\\thanks\{[^}]*\}',
            #     r'\\institute\{[^}]*\}'
            # ],
            # 'list': [
            #     # 列表环境
            #     r'\\begin\{itemize\}.*?\\end\{itemize\}',
            #     r'\\begin\{enumerate\}.*?\\end\{enumerate\}',
            #     r'\\begin\{description\}.*?\\end\{description\}',
            #     r'\\item\s.*?(?=\\item|\n\\end\{|$)'
            # ],
            # 'quote': [
            #     # 引用环境
            #     r'\\begin\{quote\}.*?\\end\{quote\}',
            #     r'\\begin\{quotation\}.*?\\end\{quotation\}',
            #     r'\\begin\{verse\}.*?\\end\{verse\}'
            # ],
            # 'code': [
            #     # 代码环境
            #     r'\\begin\{verbatim\}.*?\\end\{verbatim\}',
            #     r'\\begin\{lstlisting\}.*?\\end\{lstlisting\}',
            #     r'\\begin\{minted\}.*?\\end\{minted\}',
            #     r'\\verb\|.*?\|'
            # ],
            'text': [
                # 普通文本，但排除特殊命令和环境
                r'(?<!\\)(?:[^$\\{}]+|\\.)+',
                # 文本格式化命令
                r'\\textbf\{[^}]*\}',
                r'\\textit\{[^}]*\}',
                r'\\texttt\{[^}]*\}',
                r'\\emph\{[^}]*\}'
            ]
        }
        
        # 编译所有正则表达式
        self.compiled_patterns = {
            element_type: [re.compile(pattern, re.DOTALL) for pattern in patterns]
            for element_type, patterns in self.patterns.items()
        }
    
    def find_elements(self, content: str) -> Set[str]:
        """查找LaTeX内容中存在的元素类型"""
        elements = set()
        for element_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(content):
                    elements.add(element_type)
                    break
        return elements
    
    def extract_elements(self, content: str) -> List[LatexElement]:
        """提取LaTeX内容中的所有元素及其位置"""
        elements = []
        for element_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(content):
                    elements.append(LatexElement(
                        type=element_type,
                        content=match.group(0),
                        start=match.start(),
                        end=match.end()
                    ))
        
        # 按位置排序
        elements.sort(key=lambda x: x.start)
        return elements
    
    def analyze_file(self, file_path: str) -> Dict[str, int]:
        """分析LaTeX文件中各类元素的数量"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        element_counts = {}
        for element_type, patterns in self.compiled_patterns.items():
            count = 0
            for pattern in patterns:
                count += len(pattern.findall(content))
            if count > 0:
                element_counts[element_type] = count
        
        return element_counts

def main():
    """用于测试和演示的主函数"""
    import sys
    if len(sys.argv) < 2:
        print("Usage: python latex_element_matcher.py <latex_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not Path(file_path).exists():
        print(f"文件不存在: {file_path}")
        sys.exit(1)
    
    matcher = LatexElementMatcher()
    
   
    # 提取元素
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n详细元素列表:")
    elements = matcher.extract_elements(content)
    for i, element in enumerate(elements, 1):
        print(f"\n{i}. {element.type}:")
        print(f"   位置: {element.start}-{element.end}")
        print(f"   内容: {element.content[:100]}...")

     # 分析文件
    print(f"\n分析文件: {file_path}")
    counts = matcher.analyze_file(file_path)
    print("\n元素统计:")
    for element_type, count in counts.items():
        print(f"{element_type}: {count}")
    
if __name__ == "__main__":
    main() 