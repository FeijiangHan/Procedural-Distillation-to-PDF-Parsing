import re
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

__all__ = ['AuxProcessor']
class AuxProcessor:
    def __init__(self):
        # 页面标签模式
        self.page_pattern = re.compile(
            r'\\zref@newlabel\{(?:\d+-)?([^}]+)\}\{\\default\{([^}]+)\}\\page\{(\d+)\}\}'
        )
        
        # 坐标标签模式 - 修改以精确匹配 table* 和 figure* 的坐标
        self.pos_pattern = re.compile(
            r'\\zref@newlabel\{(?:\d+-)?(table\*|figure\*|[^}]+)-(\d+)\}\{(?:\\order\{\d+\})?\\posx\{(\d+)\}\\posy\{(\d+)\}\}'
        )
        
        # 需要匹配的坐标数量
        self.required_coords = {
            'math': 4,
            'header': 3,
            'figure': 2,
            'figure*': 2,
            'table': 2,
            'table*': 2,
            'figurecap': 2,
            'tablecap': 2,
            'figurecap*': 2,
            'tablecap*': 2
        }
        
        # 存储待处理的标签
        self.pending_labels: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        # 当前编号
        self.current_order = 1
        # 存储处理后的行
        self.processed_lines = []
        
        # 定义元素的遍历配置
        self.coord_config = {
            'math': {
                'count': 4,
                'direction': 'mixed',  # 混合遍历
                'strategy': 'specific',  # 特定顺序
                'pattern': [
                    {'index': 1, 'direction': 'backward'},  # -1 向前找
                    {'index': 2, 'direction': 'forward'},    # -2 向后找
                    {'index': 3, 'direction': 'forward'},    # -3 向后找
                    {'index': 4, 'direction': 'forward'}    # -4 向后找
                ]
            },
            'header': {
                'count': 3,
                'direction': 'backward',  # 向前遍历
                'strategy': 'sequential'
            },
            'figure': {
                'count': 2,
                'direction': 'backward',
                'strategy': 'sequential'
            },
            'figure*': {
                'count': 2,
                'direction': 'backward',
                'strategy': 'sequential'
            },
            'table': {
                'count': 2,
                'direction': 'backward',
                'strategy': 'sequential'
            },
            'table*': {
                # 'count': 2,
                # 'direction': 'mixed',  # 混合遍历
                # 'strategy': 'specific',  # 特定顺序
                # 'pattern': [
                #     {'index': 1, 'direction': 'backward'},  # -1 向前找
                #     {'index': 2, 'direction': 'forward'}    # -2 向后找
                # ]
                'count': 2,
                'direction': 'backward',
                'strategy': 'sequential'
            },
            'figurecap': {
                'count': 2,
                'direction': 'backward',
                'strategy': 'sequential'
            },
            'tablecap': {
                'count': 2,
                'direction': 'backward',
                'strategy': 'sequential'
            }
        }
        # 为带星号的 cap 添加相同的配置
        self.coord_config['figurecap*'] = self.coord_config['figurecap']
        self.coord_config['tablecap*'] = self.coord_config['tablecap']

    def create_cap_label(self, element_type: str, default_text: str, page: str, is_starred: bool = False) -> str:
        """创建 cap 标签
        
        Args:
            element_type: 元素类型 ('figure' 或 'table')
            default_text: 默认文本
            page: 页码
            is_starred: 是否是带星号的版本
        """
        cap_type = f"{element_type}cap{'*' if is_starred else ''}"
        return f"\\zref@newlabel{{{self.current_order}-{cap_type}}}{{\\default{{{default_text}}}\\page{{{page}}}}}\n"
        
    def process_file(self, input_file: str, output_file: str = None) -> None:
        """处理 aux 文件并添加正确的编号"""
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"未找到输入文件: {input_file}")
            
        if output_file is None:
            output_file = str(input_path.parent / f"{input_path.stem}_ordered.aux")
            
        # 读取所有行并处理
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        self.processed_lines = lines.copy()
        
        # 处理所有行并插入 cap 标签
        i = 0
        while i < len(self.processed_lines):
            line = self.processed_lines[i]
            
            # 检查是否需要插入 cap 标签
            page_match = self.page_pattern.match(line)
            if page_match:
                element_type, default_text, page = page_match.groups()
                
                # 检查是否是带星号的版本
                is_starred = element_type.endswith('*')
                base_type = element_type.rstrip('*')
                
                if base_type == 'figure':
                    # 先处理 figure 标签
                    processed_line = self.process_line(line, i)
                    self.processed_lines[i] = processed_line
                    # 然后插入并处理 figurecap 标签
                    cap_label = self.create_cap_label('figure', default_text, page, is_starred)
                    self.processed_lines.insert(i + 1, cap_label)
                    self.process_line(cap_label, i + 1)
                    i += 1
                elif base_type == 'table':
                    # 先插入并处理 tablecap 标签
                    cap_label = self.create_cap_label('table', default_text, page, is_starred)
                    self.processed_lines.insert(i, cap_label)
                    self.process_line(cap_label, i)
                    # 然后处理 table 标签
                    processed_line = self.process_line(line, i + 1)
                    self.processed_lines[i + 1] = processed_line
                    i += 1
                else:
                    # 处理其他类型的标签
                    processed_line = self.process_line(line, i)
                    self.processed_lines[i] = processed_line
            else:
                # 处理非页面标签
                processed_line = self.process_line(line, i)
                self.processed_lines[i] = processed_line
            i += 1
            
        # 写入输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(self.processed_lines)
            
        print(f"处理后的文件已保存到: {output_file}")

    def find_coords(self, element_type: str, current_line: int) -> List[Tuple[int, str]]:
        """根据配置查找坐标"""
        config = self.coord_config.get(element_type)
        if not config:
            return []

        all_coords = []
        # 收集所有相关坐标
        for i, line in enumerate(self.processed_lines):
            pos_match = self.pos_pattern.match(line)
            if pos_match and pos_match.group(1) == element_type:
                all_coords.append((i, line))

        if config['strategy'] == 'specific':
            # 特定顺序的处理（如 table*）
            return self._find_coords_specific(element_type, current_line, all_coords, config)
        else:
            # 连续遍历的处理
            return self._find_coords_sequential(element_type, current_line, all_coords, config)

    def _find_coords_specific(self, element_type: str, current_line: int, 
                            all_coords: List[Tuple[int, str]], config: Dict) -> List[Tuple[int, str]]:
        """处理特定顺序的坐标查找"""
        result = []
        for pattern in config['pattern']:
            idx = pattern['index']
            direction = pattern['direction']
            
            if direction == 'forward':
                # 向后查找
                for i, (line_num, line) in enumerate(all_coords):
                    if line_num > current_line and f'{element_type}-{idx}' in line:
                        result.append((line_num, line))
                        break
            else:
                # 向前查找
                for i, (line_num, line) in reversed(list(enumerate(all_coords))):
                    if line_num < current_line and f'{element_type}-{idx}' in line:
                        result.append((line_num, line))
                        break
        
        return sorted(result, key=lambda x: x[0])

    def _find_coords_sequential(self, element_type: str, current_line: int, 
                              all_coords: List[Tuple[int, str]], config: Dict) -> List[Tuple[int, str]]:
        """处理连续遍历的坐标查找"""
        count = config['count']
        direction = config['direction']
        
        if direction == 'forward':
            # 向后查找连续的坐标
            coords = []
            for i, (line_num, line) in enumerate(all_coords):
                if line_num > current_line:
                    coords.append((line_num, line))
                    if len(coords) == count:
                        break
            return coords if len(coords) == count else []
        else:
            # 向前查找连续的坐标
            coords = []
            for i, (line_num, line) in reversed(list(enumerate(all_coords))):
                if line_num < current_line:
                    coords.insert(0, (line_num, line))
                    if len(coords) == count:
                        break
            return coords if len(coords) == count else []

    def process_line(self, line: str, line_num: int) -> str:
        """处理单行内容"""
        page_match = self.page_pattern.match(line)
        if page_match:
            element_type, default_text, page = page_match.groups()
            current_order = self.current_order
            
            # 使用新的坐标查找方法
            coords = self.find_coords(element_type, line_num)
            if coords:
                # 更新这些坐标的编号
                for coord_line_num, coord_line in coords:
                    new_line = re.sub(
                        fr'\\zref@newlabel\{{(?:\d+-)?{re.escape(element_type)}-(\d+)\}}',
                        fr'\\zref@newlabel{{{current_order}-{element_type}-\1}}',
                        coord_line
                    )
                    self.processed_lines[coord_line_num] = new_line
            
            # 更新页面标签的编号
            new_line = re.sub(
                r'\\zref@newlabel\{(?:\d+-)?([^}]+)\}',
                fr'\\zref@newlabel{{{current_order}-\1}}',
                line
            )
            self.current_order += 1
            return new_line
            
        # 检查是否是坐标标签
        pos_match = self.pos_pattern.match(line)
        if pos_match:
            element_type, idx, posx, posy = pos_match.groups()
            # 将坐标标签添加到待处理列表
            self.pending_labels[element_type].append((line_num, line))
            return line
            
        return line

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='处理 LaTeX aux 文件以添加正确的编号')
    parser.add_argument('input_file', help='输入的 aux 文件')
    parser.add_argument('--output-file', help='输出文件（可选）')
    
    args = parser.parse_args()
    
    processor = AuxProcessor()
    processor.process_file(args.input_file, args.output_file)

if __name__ == "__main__":
    main()