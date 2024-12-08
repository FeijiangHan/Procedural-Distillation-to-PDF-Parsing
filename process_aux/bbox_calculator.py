import json
from pathlib import Path
from typing import Dict, List, Tuple

__all__ = ['BBoxCalculator']

class BBoxCalculator:
    def __init__(self):
        self.dimensions = {
            'columnwidth': 0,
            'textheight': 0,
            'textwidth': 0,
            'lineheight': 0,
            'linewidth': 0,
            'paperheight': 0,
            'headsep': 0,
            'footskip': 0
        }
        # 添加 header 高度列表
        self.min_header_height = float('inf')  # 初始化为无穷大
        
    def _correct_y1_coordinate(self, y1: int, y2: int, element_position: List[bool], k2: int = 0) -> int:
        """修正 y1 坐标
        
        当 y1 < y2 时，使用公式重新计算 y1 坐标：
        y1 = textheight - (paperheight-(headsep+textheight+footskip))/2
        """
        ismodified = [False, False]
        if y1 < y2:
            bottom = (self.dimensions['paperheight'] - 
                      self.dimensions['textheight']) / 2
            height = self.dimensions['textheight'] + bottom + self.dimensions['footskip']
            if element_position[1] and k2 < (bottom+self.dimensions['footskip']) * 1.5: # Bottom of the page
                y2 = bottom + self.dimensions['footskip']
                ismodified[1] = True
            elif element_position[0]: # Top of the page
                y1 = height
                ismodified[0] = True
            else:
                y1 = height
                ismodified[0] = True
            
        return y1, y2, ismodified
        
    def calculate_bbox(self, coords: List[List[int]], element_type: str, element_key: str) -> List[int]:
        """计算不同类型元素的边界框"""
        # 存储当前处理的元素键，供 caption 处理使用
        self.current_element_key = element_key
        
        if not coords:
            return []
            
        if element_type.startswith('math'):
            return self.calculate_math_bbox(coords, element_key)
        elif element_type == 'header':
            # 获取当前页码
            page = next(
                (page for page, elements in self.bbox_data.items() 
                 if element_key in elements),
                None
            )
            return self.calculate_header_bbox(coords, element_key, page)
        elif element_type.startswith('figure') and not element_type.startswith('figurecap'):
            return self.calculate_figure_bbox(coords, element_type)
        elif element_type.startswith('table') and not element_type.startswith('tablecap'):
            return self.calculate_table_bbox(coords, element_type)
        elif element_type.startswith('figurecap'):
            return self.calculate_figurecap_bbox(coords, element_type)
        elif element_type.startswith('tablecap'):
            return self.calculate_tablecap_bbox(coords, element_type)
        else:
            return []
            
    def calculate_math_bbox(self, coords: List[List[int]], element_key: str = None) -> List[int]:
        """计算数学公式的边界框"""
        if len(coords) != 4:
            return []
            
        # 按照特定顺序解析坐标
        y1 = coords[0][1]  # math-1 的 y
        x1 = coords[1][0] - 300000  # math-2 的 x
        x2 = coords[2][0] + 300000  # math-3 的 x
        y2 = coords[3][1]  # math-4 的 y
        
        k = coords[1][1] # 用于判断是否是页面底部
        
        # 检查是否是页面第一个或最后一个元素
        is_first_element = False
        is_last_element = False
        if element_key:
            order = int(element_key.split('-')[0])
            page_elements = sorted([
                int(key.split('-')[0]) 
                for key in self.current_elements 
                if key.split('-')[0].isdigit()
            ])
            is_first_element = page_elements[0] == order
            is_last_element = page_elements[-1] == order
        
        # 使用辅助方法修正 y1 坐标
        y1, y2, ismodified = self._correct_y1_coordinate(y1, y2, [is_first_element, is_last_element], k)
        
        if ismodified[0]:
            y1 += 500000
            y2 += 300000
        else:
            y1 -= 600000
            y2 += 300000
            if ismodified[1]:
                y2 += 500000
                
        return [x1, y1, x2, y2]
        
    def calculate_header_bbox(self, coords: List[List[int]], element_key: str, page: str) -> List[int]:
        """计算标题的边界框"""
        if len(coords) != 3:
            return []
            
        k1, y1 = coords[0]  # 第一个坐标点
        x2, k2 = coords[1]   # 第二个坐标点的 x
        x1, y2 = coords[2]   # 第三个坐标点的 y
        
        # 检查是否是页面第一个元素
        order = int(element_key.split('-')[0])
        page_elements = sorted([
            int(key.split('-')[0]) 
            for key in self.current_elements 
            if key.split('-')[0].isdigit()
        ])
        is_first_element = page_elements[0] == order
        is_last_element = page_elements[-1] == order
        
        
        # 使用辅助方法修正 y1 坐标
        y1, y2, ismodified = self._correct_y1_coordinate(y1, y2, [is_first_element, is_last_element], k2)
        
        top = self.dimensions['paperheight'] - self.dimensions['footskip'] - self.min_header_height
        # 如果不是top
        if y1 < top:
            y1 -= 600000
        y2 += 100000

        # 计算当前 header 的高度
        current_height = abs(y2 - y1)  # 使用绝对值
        
        # 如果当前高度大于最小高度，使用最小高度重新计算 y1
        if current_height > self.min_header_height * 1.5 or current_height < self.min_header_height * 0.6:
            if not is_first_element:
                y1 = y2 + self.min_header_height + 300000
            else:
                y1 = y2 + self.min_header_height
            print(f"Adjusting header height: {current_height} -> {self.min_header_height}, y1: {y1}")
        return [x1, y1, x2, y2]
        
    def calculate_figure_bbox(self, coords: List[List[int]], element_type: str) -> List[int]:
        """计算图片的边界框"""
        if len(coords) != 2:
            return []
            
        x1, y1 = coords[0]
        _, y2 = coords[1]
        
        # 根据是否是跨栏确定宽度
        width = self.dimensions['textwidth'] if '*' in element_type else self.dimensions['columnwidth']
        
        return [x1, y1, x1 + width, y2]
        
    def calculate_table_bbox(self, coords: List[List[int]], element_type: str) -> List[int]:
        """计算表格的边界框"""
        if len(coords) != 2:
            return []
            
        x1, y1 = coords[0]
        _, y2 = coords[1]
        
        y2 -= 300000
        
        # 根据是否是跨栏确定宽度
        width = self.dimensions['textwidth'] if '*' in element_type else self.dimensions['columnwidth']
        
        return [x1, y1, x1 + width, y2]
        
    def _get_corresponding_element_bbox(self, element_key: str, page: str) -> List[int]:
        """获取对应的主元素（figure/table）的边界框"""
        order = int(element_key.split('-')[0])
        element_type = element_key.split('-', 1)[1]
        base_type = element_type.replace('cap', '')
        
        # 尝试前后序号查找对应元素
        possible_keys = [
            f"{order-1}-{base_type}",  # 往前找
            f"{order+1}-{base_type}",  # 往后找
            f"{order-1}-{base_type}*",  # 带星号往前找
            f"{order+1}-{base_type}*"   # 带星号往后找
        ]
        
        for key in possible_keys:
            if key in self.bbox_data.get(page, {}):
                return self.bbox_data[page][key]
        
        return []

    def calculate_figurecap_bbox(self, coords: List[List[int]], element_type: str) -> List[int]:
        """计算图片标题的边界框"""
        if len(coords) != 2:
            return []
            
        x1, y1 = coords[0]  # 第一个坐标点
        x2, y2 = coords[1]  # 第二个坐标点
        
        # 根据是否是跨栏确定宽度
        width = self.dimensions['textwidth'] if '*' in element_type else self.dimensions['columnwidth']
        
        # 获取当前页码
        page = next(
            (page for page, elements in self.bbox_data.items() 
             if self.current_element_key in elements),
            None
        )
        
        if page:
            # 获取对应 figure 的边界框
            figure_bbox = self._get_corresponding_element_bbox(self.current_element_key, page)
            if figure_bbox and y1 > figure_bbox[3]:  # y1 > figure 的 y2
                y1 = figure_bbox[3]  # 使用 figure 的 y2
                y2 = y1  # caption 高度设为 0
        
        return [x2, y1, x2 + width, y2]
        
    def calculate_tablecap_bbox(self, coords: List[List[int]], element_type: str) -> List[int]:
        """计算表格标题的边界框"""
        if len(coords) != 2:
            return []
            
        x1, y1 = coords[0]  # 第一个坐标点
        x2, y2 = coords[1]  # 第二个坐标点
        
        # 根据是否是跨栏确定宽度
        width = self.dimensions['textwidth'] if '*' in element_type else self.dimensions['columnwidth']
        
        # 获取当前页码
        page = next(
            (page for page, elements in self.bbox_data.items() 
             if self.current_element_key in elements),
            None
        )
        
        if page:
            # 获取对应 table 的边界框
            table_bbox = self._get_corresponding_element_bbox(self.current_element_key, page)
            if table_bbox and y1 > table_bbox[3]:  # y1 > table 的 y2
                y1 = table_bbox[3]  # 使用 table 的 y2
                y2 = y1  # caption 高度设为 0
        
        return [x2, y1, x2 + width, y2]
        
    def _update_min_height(self, height: int) -> None:
        """更新最小 header 高度"""
        self.min_header_height = min(self.min_header_height, height)
        
    def process_file(self, input_file: str, output_file: str = None) -> None:
        """处理坐标文件并计算边界框"""
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
            
        if output_file is None:
            output_file = str(input_path.parent / "latex_bboxes.json")
            
        # 读取坐标文件
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 更新���度信息
        self.dimensions = data['dimensions']
        coordinates = data['coordinates']
            
        # 计算每个元素的边界框
        self.bbox_data = {}
        self.min_header_height = float('inf')  # 重置最小高度
        
        # 第一遍：找到全局最小 header 高度
        for page, elements in coordinates.items():
            for element_key, coords in elements.items():
                element_type = element_key.split('-', 1)[1]
                if element_type == 'header':
                    _, y1 = coords[0]
                    _, y2 = coords[2]
                    height = abs(y2 - y1)  # 使用绝对值
                    self._update_min_height(height)
        
        # 第二遍：计算边界框
        for page, elements in coordinates.items():
            self.bbox_data[page] = {}
            self.current_elements = set(elements.keys())
            
            for element_key, coords in elements.items():
                element_type = element_key.split('-', 1)[1]
                bbox = self.calculate_bbox(coords, element_type, element_key)
                
                if bbox:
                    if element_type.endswith('cap'):
                        order = element_key.split('-')[0]
                        base_type = element_type.replace('cap', '')
                        starred_key = f"{order}-{base_type}*"
                        if starred_key in self.current_elements:
                            element_key = f"{order}-{base_type}cap*"
                    
                    self.bbox_data[page][element_key] = bbox
        
        # 写入结果文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.bbox_data, f, indent=2, ensure_ascii=False)
            
        print(f"Bounding boxes saved to: {output_file}")
        print("\nStructure:")
        for page, elements in self.bbox_data.items():
            print(f"Page {page}:")
            for element_key, bbox in elements.items():
                print(f"  {element_key}: {bbox}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate bounding boxes from LaTeX coordinates')
    parser.add_argument('input_file', help='Input JSON file with coordinates')
    parser.add_argument('--output-file', help='Output JSON file (optional)')
    
    args = parser.parse_args()
    
    calculator = BBoxCalculator()
    calculator.process_file(args.input_file, args.output_file)

if __name__ == "__main__":
    main() 