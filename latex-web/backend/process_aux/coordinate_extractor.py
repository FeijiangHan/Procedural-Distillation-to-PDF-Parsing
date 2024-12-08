import re
import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

__all__ = ['CoordinateExtractor']
class CoordinateExtractor:
    """Extract page numbers and coordinates from LaTeX aux file"""
    
    def __init__(self):
        # Pattern for page labels with order number
        self.page_pattern = re.compile(
            r'\\zref@newlabel\{(\d+)-([^}]+(?:\*)?)\}\{\\default\{[^}]+\}\\page\{(\d+)\}\}'
        )
        
        # Pattern for coordinate labels with order number
        self.coord_pattern = re.compile(
            r'\\zref@newlabel\{(\d+)-([^}]+(?:\*)?)-(\d+)\}\{(?:\\order\{\d+\})?\\posx\{(\d+)\}\\posy\{(\d+)\}\}'
        )
        
        # Pattern for LaTeX dimensions
        self.dimension_pattern = re.compile(
            r'\\newlabel\{(columnwidth|textwidth|lineheight|linewidth|paperheight|headsep|textheight|footskip)\}\{\{([^}]+)pt\}\}'
        )
        
        # Store coordinates by page and element
        self.coordinates = defaultdict(lambda: defaultdict(dict))  # 使用字典存储坐标，以保持索引顺序
        
        # Store LaTeX dimensions
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

    def pt_to_sp(self, pt_value: float) -> int:
        """Convert points to scaled points (sp)"""
        return int(pt_value * 65536)

    def process_file(self, input_file: str, output_file: str = None) -> None:
        """Process aux file and extract coordinates"""
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
            
        if output_file is None:
            output_file = str(input_path.parent / "latex_coordinates.json")
        
        # First pass: collect page numbers for each element
        element_pages = {}  # {order-type: page_number}
        coordinates = defaultdict(lambda: defaultdict(dict))  # ���用字典存储坐标，以保持索引顺序
        
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # First find all dimension labels
            print("Finding LaTeX dimensions...")
            for match in self.dimension_pattern.finditer(content):
                dim_type, value = match.groups()
                pt_value = float(value)
                sp_value = self.pt_to_sp(pt_value)
                self.dimensions[dim_type] = sp_value
                print(f"Found {dim_type}: {pt_value}pt ({sp_value}sp)")
            
            # Then find all page labels
            print("\nFinding page labels...")
            for match in self.page_pattern.finditer(content):
                order, elem_type, page = match.groups()
                key = f"{order}-{elem_type}"
                element_pages[key] = page
                print(f"Found element {key} on page {page}")
            
            # Finally find coordinates for each element
            print("\nFinding coordinates...")
            for match in self.coord_pattern.finditer(content):
                order, elem_type, idx, posx, posy = match.groups()
                key = f"{order}-{elem_type}"
                
                if key in element_pages:
                    page = element_pages[key]
                    # 使用索引作为字典键存储坐标
                    coordinates[page][key][int(idx)] = [int(posx), int(posy)]
                    print(f"Found coordinates for {key}-{idx} on page {page}: [{posx}, {posy}]")
                else:
                    print(f"Warning: No page number found for {key}")
        
        # Convert defaultdict to regular dict and sort coordinates
        output_data = {
            'dimensions': self.dimensions,
            'coordinates': {}
        }
        
        for page in coordinates:
            output_data['coordinates'][page] = {}
            for element_key, coords_dict in coordinates[page].items():
                # 将字典转换为按索引排序的列表
                sorted_coords = [coords_dict[i] for i in sorted(coords_dict.keys())]
                output_data['coordinates'][page][element_key] = sorted_coords
        
        # Write JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
            
        print(f"\nCoordinates and dimensions saved to: {output_file}")
        print("\nDimensions:")
        for dim_type, value in self.dimensions.items():
            print(f"  {dim_type}: {value}sp")
        print("\nCoordinates structure:")
        for page, elements in output_data['coordinates'].items():
            print(f"Page {page}:")
            for element_key, coords in elements.items():
                print(f"  {element_key}: {coords}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract coordinates from LaTeX aux file')
    parser.add_argument('input_file', help='Input aux file')
    parser.add_argument('--output-file', help='Output JSON file (optional)')
    
    args = parser.parse_args()
    
    extractor = CoordinateExtractor()
    extractor.process_file(args.input_file, args.output_file)

if __name__ == "__main__":
    main() 