import os
import re
import sys
import time
import queue
import threading
from typing import List, Optional, Dict, Set
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime
import argparse

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.callbacks import get_openai_callback

from LLM.latex_element_matcher import LatexElementMatcher
from LLM.latex_standardizer import standardize_tex_file

class APIKeyManager:
    """Manages the allocation and usage of multiple API keys"""
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.key_queue = queue.Queue()
        self.key_locks = {}  # Track the usage status of each key
        
        for key in api_keys:
            self.key_queue.put(key)
            self.key_locks[key] = threading.Lock()
    
    def get_api_key(self) -> Optional[str]:
        """Get an available API key"""
        try:
            key = self.key_queue.get(timeout=30)  # 30 seconds timeout
            return key
        except queue.Empty:
            return None
    
    def release_api_key(self, key: str):
        """Release API key back to the queue"""
        if key in self.key_locks:
            self.key_queue.put(key)

def load_element_guide(element_type: str, instructions_dir: str) -> str:
    """Load annotation guide for specific element type"""
    guide_path = os.path.join(instructions_dir, f"{element_type}.md")
    try:
        with open(guide_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Warning: Unable to read annotation guide for {element_type}: {str(e)}")
        return ""

class LatexReviser:
    """LaTeX document reviser"""
    def __init__(self, api_manager: APIKeyManager, instructions_dir: str, max_retries: int = 3):
        self.api_manager = api_manager
        self.instructions_dir = instructions_dir
        self.element_matcher = LatexElementMatcher()
        self.max_retries = max_retries
        self.standardize_first = True
        self.system_prompt = """You are a LaTeX document revision expert. Please modify the LaTeX content according to the provided annotation guidelines.
Please ensure:
1. Add position markers strictly following the guidelines
2. Maintain correct LaTeX formatting
3. Only output the complete modified LaTeX content
4. Do not add any explanations or markers
5. Maintain the original section structure and document semantics
        """
    
    def build_revision_guide(self, latex_content: str) -> str:
        """Build revision guide"""
        try:
            # Find element types in the document
            elements = self.element_matcher.find_elements(latex_content)
            
            # Load and combine relevant revision guides
            guides = []
            for element in elements:
                guide = load_element_guide(element, self.instructions_dir)
                if guide:
                    guides.append(f"### {element.replace('_', ' ').title()} Annotation Guide\n{guide}")
            
            if not guides:
                raise ValueError("No matching element annotation guides found")
            
            # Build prompt message
            element_info = "\n".join([f"Document contains {element} type elements." for element in elements])
            
            return f"""Please modify the LaTeX document according to the following annotation guidelines. {element_info}

Annotation Guidelines:
{'\n\n'.join(guides)}"""
            
        except Exception as e:
            print(f"Error building revision guide: {str(e)}", file=sys.stderr)
            return ""

    def revise_latex(self, latex_path: str) -> Optional[str]:
        """Modify LaTeX file based on document elements, with retry mechanism"""
        for attempt in range(self.max_retries):
            try:
                # Get API key
                api_key = self.api_manager.get_api_key()
                if not api_key:
                    raise Exception("Unable to get available API key")
                
                try:
                    # Standardize first if needed
                    if self.standardize_first:
                        temp_file = latex_path + "standardized"
                        if standardize_tex_file(latex_path, temp_file, api_key):
                            with open(temp_file, 'r', encoding='utf-8') as f:
                                latex_content = f.read()
                            os.remove(temp_file)
                        else:
                            # Use original file if standardization fails
                            with open(latex_path, 'r', encoding='utf-8') as f:
                                latex_content = f.read()
                    else:
                        with open(latex_path, 'r', encoding='utf-8') as f:
                            latex_content = f.read()
                    
                    # Build revision guide
                    revision_guide = self.build_revision_guide(latex_content)
                    if not revision_guide:
                        print(f"Warning: No matching revision guides found: {latex_path}")
                        return latex_content
                    
                    # Set up GPT model
                    chat = ChatOpenAI(
                        model_name="gpt-4",
                        openai_api_key=api_key,
                        temperature=0.1
                    )
                    
                    # Construct messages
                    messages = [
                        SystemMessage(content=self.system_prompt),
                        HumanMessage(content=f"""Please modify the LaTeX content according to the following revision guidelines:

Revision Guidelines:
{revision_guide}

LaTeX Content:
{latex_content}""")
                    ]
                    
                    # Call API
                    with get_openai_callback() as cb:
                        response = chat(messages)
                        print(f"Token usage - Total: {cb.total_tokens}, Cost: ${cb.total_cost}")
                    
                    revised_content = response.content
                    
                    # Validate output
                    if not self.validate_latex(revised_content):
                        raise ValueError("Invalid LaTeX content generated by GPT")
                    
                    return revised_content
                    
                finally:
                    self.api_manager.release_api_key(api_key)
                    
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}", file=sys.stderr)
                if attempt < self.max_retries - 1:
                    print(f"Preparing attempt {attempt + 2}...")
                    time.sleep(2 * (attempt + 1))  # Exponential backoff
                continue
        
        print(f"File processing failed: {latex_path} after {self.max_retries} attempts", file=sys.stderr)
        return None

    def debug_prompt(self, latex_path: str, debug_dir: str = "./log/prompt_debug") -> bool:
        """
        Debug mode: Save constructed prompt without calling LLM
        
        Args:
            latex_path: Path to the LaTeX file
            debug_dir: Directory to save debug files
        
        Returns:
            bool: Whether the prompt construction was successful
        """
        try:
            # Create debug directory
            debug_dir = Path(debug_dir)
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            # Read LaTeX content
            with open(latex_path, 'r', encoding='utf-8') as f:
                latex_content = f.read()
            
            # Build revision guide
            revision_guide = self.build_revision_guide(latex_content)
            if not revision_guide:
                print(f"Warning: No matching revision guides found: {latex_path}")
                return False
            
            # Construct messages
            messages = [
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": f"""Please modify the LaTeX content according to the following revision guidelines:

Revision Guidelines:
{revision_guide}

LaTeX Content:
{latex_content}"""
                }
            ]
            
            # Create timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = Path(latex_path).stem
            debug_file = debug_dir / f"prompt_debug_{file_name}_{timestamp}.json"
            
            # Save prompt to file
            debug_info = {
                "timestamp": timestamp,
                "file_name": file_name,
                "messages": messages
            }
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, ensure_ascii=False, indent=2)
                
            print(f"Prompt debug info saved to: {debug_file}")
            return True
            
        except Exception as e:
            print(f"Error in prompt debugging: {str(e)}", file=sys.stderr)
            return False

def process_latex_files(instructions_dir: str, latex_dir: str, output_dir: str, api_keys: List[str]):
    """Process multiple LaTeX files"""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize API manager and reviser
    api_manager = APIKeyManager(api_keys)
    reviser = LatexReviser(api_manager, instructions_dir)
    
    # Get all LaTeX files
    latex_files = sorted(
        [f for f in os.listdir(latex_dir) if f.startswith('split_part_') and f.endswith('.tex')],
        key=lambda x: int(re.search(r'split_part_(\d+)', x).group(1))
    )
    
    def process_file(latex_file: str):
        try:
            input_path = os.path.join(latex_dir, latex_file)
            output_path = os.path.join(output_dir, f"{latex_file[:-4]}_revised.tex")
            
            # Revise LaTeX content
            revised_content = reviser.revise_latex(input_path)
            
            if revised_content:
                # Write revised content
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(revised_content)
                print(f"File revision completed: {latex_file}")
            else:
                print(f"File revision failed: {latex_file}", file=sys.stderr)
                
        except Exception as e:
            print(f"Error processing file {latex_file}: {str(e)}", file=sys.stderr)
    
    # Use thread pool to process files in parallel
    with ThreadPoolExecutor(max_workers=len(api_keys)) as executor:
        executor.map(process_file, latex_files)

def load_api_keys(key_file: str) -> List[str]:
    """
    Load API keys from a text file
    
    Args:
        key_file: Path to the file containing API keys (one key per line)
    
    Returns:
        List of API keys
    """
    try:
        with open(key_file, 'r', encoding='utf-8') as f:
            # Remove empty lines and whitespace
            keys = [line.strip() for line in f.readlines() if line.strip()]
        
        if not keys:
            raise ValueError("No API keys found in the file")
            
        return keys
        
    except Exception as e:
        raise ValueError(f"Error loading API keys from {key_file}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Process LaTeX files with GPT')
    parser.add_argument('--instructions-dir', default='instructions',
                      help='Directory containing annotation guides')
    parser.add_argument('--latex-dir', default='data/output_chunks',
                      help='Directory containing LaTeX files')
    parser.add_argument('--output-dir', default='data/revised_chunks',
                      help='Directory for output files')
    parser.add_argument('--api-key-file',
                      help='Path to file containing API keys (one key per line)')
    parser.add_argument('--debug-prompt', action='store_true',
                      help='Enable prompt debug mode (no API calls)')
    parser.add_argument('--debug-dir', default='./log/prompt_debug/gpt_latex_reviser',
                      help='Directory for debug files')
    
    args = parser.parse_args()
    
    try:
        if args.debug_prompt:
            # Debug mode: only save prompts
            api_manager = APIKeyManager(["dummy_key"])  # Dummy key for initialization
            reviser = LatexReviser(api_manager, args.instructions_dir)
            
            latex_files = sorted(
                [f for f in os.listdir(args.latex_dir) if f.startswith('split_part_') and f.endswith('.tex')],
                key=lambda x: int(re.search(r'split_part_(\d+)', x).group(1))
            )
            
            for latex_file in latex_files:
                input_path = os.path.join(args.latex_dir, latex_file)
                reviser.debug_prompt(input_path, args.debug_dir)
                
        else:
            # Normal mode: process files with API
            if not args.api_key_file:
                raise ValueError("API key file is required for normal operation (use --api-key-file)")
            
            # Load API keys from file
            api_keys = load_api_keys(args.api_key_file)
            print(f"Loaded {len(api_keys)} API keys")
            
            process_latex_files(
                args.instructions_dir,
                args.latex_dir,
                args.output_dir,
                api_keys
            )
            
    except Exception as e:
        print(f"Program execution error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 