import os
import re
import time
from typing import Optional, Dict, Tuple
from pathlib import Path
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.callbacks import get_openai_callback
import json
from datetime import datetime
import argparse

class LatexStandardizer:
    """LaTeX document standardizer"""
    def __init__(self, init_file: str = "instructions/init.md", max_retries: int = 3, debug: bool = False):
        self.init_file = init_file
        self.max_retries = max_retries
        self.debug = debug
        self.debug_dir = Path("./log/prompt_debug/latex_standardizer")
        self.system_prompt = """
        You are a LaTeX document standardization expert. Please modify the LaTeX content according to the provided specifications.
        Please ensure:
        1. Convert all elements strictly according to the specifications
        2. Maintain the document semantics unchanged
        3. Only output the modified LaTeX content
        4. Do not add any explanations or markers
        """
        
    def load_init_rules(self) -> str:
        """Load initialization rules file"""
        try:
            with open(self.init_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            raise ValueError(f"Unable to read standardization rules file {self.init_file}: {str(e)}")

    def validate_latex(self, content: str) -> bool:
        """Validate basic LaTeX format"""
        # Check basic LaTeX syntax
        if not content.strip():
            return False
            
        # Check environment pairs
        env_pattern = r'\\begin\{([^}]+)\}'
        end_pattern = r'\\end\{([^}]+)\}'
        begins = re.findall(env_pattern, content)
        ends = re.findall(end_pattern, content)
        
        if len(begins) != len(ends):
            return False
            
        # Check bracket matching
        brackets = {'{': '}', '[': ']', '(': ')'}
        stack = []
        
        for char in content:
            if char in brackets:
                stack.append(char)
            elif char in brackets.values():
                if not stack or brackets[stack.pop()] != char:
                    return False
        
        return len(stack) == 0

    def _save_debug_info(self, messages: list, response: str = None, prompt_only: bool = False) -> None:
        """
        Save prompt and response for debugging purposes
        
        Args:
            messages: List of messages to be sent to LLM
            response: Response from LLM (optional)
            prompt_only: If True, only save the prompt without waiting for response
        """
        if not self.debug:
            return
            
        # Create debug directory if it doesn't exist
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_suffix = "_prompt" if prompt_only else "_full"
        debug_file = self.debug_dir / f"debug_{timestamp}{file_suffix}.json"
        
        # Prepare debug info
        debug_info = {
            "timestamp": timestamp,
            "messages": [
                {
                    "role": "system" if isinstance(msg, SystemMessage) else "user",
                    "content": msg.content
                }
                for msg in messages
            ]
        }
        
        if not prompt_only and response is not None:
            debug_info["response"] = response
            
        # Save to file
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(debug_info, f, ensure_ascii=False, indent=2)
            
        print(f"Debug info saved to: {debug_file}")

    def standardize_latex(self, content: str, api_key: str) -> Optional[str]:
        """Standardize LaTeX content"""
        try:
            # Load standardization rules
            init_rules = self.load_init_rules()
            
            # Set up GPT model
            chat = ChatOpenAI(
                model_name="gpt-4",
                openai_api_key=api_key,
                temperature=0.1
            )
            
            # Construct messages
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"""
                Please modify the LaTeX content according to the following specifications:

                Specifications:
                {init_rules}

                LaTeX content:
                {content}
                """)
            ]
            
            # Save prompt before API call if debug is enabled
            if self.debug:
                self._save_debug_info(messages, prompt_only=True)
            
            # Call API
            with get_openai_callback() as cb:
                response = chat(messages)
                print(f"Token usage - Total: {cb.total_tokens}, Cost: ${cb.total_cost}")
            
            standardized_content = response.content
            
            # Save full debug info if debug is enabled
            if self.debug:
                self._save_debug_info(messages, standardized_content, prompt_only=False)
            
            # Validate output
            if not self.validate_latex(standardized_content):
                raise ValueError("Invalid LaTeX content generated by GPT")
            
            return standardized_content
            
        except Exception as e:
            print(f"Error during standardization: {str(e)}")
            return None

    def standardize_with_retry(self, content: str, api_key: str) -> Tuple[Optional[str], bool]:
        """Standardize with retry mechanism"""
        for attempt in range(self.max_retries):
            try:
                result = self.standardize_latex(content, api_key)
                if result:
                    return result, True
                print(f"Attempt {attempt + 1} failed, preparing to retry...")
                time.sleep(2 * (attempt + 1))  # Exponential backoff
            except Exception as e:
                print(f"Error in attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                continue
        return None, False

    def process_file(self, input_file: str, output_file: str, api_key: str) -> bool:
        """Process single LaTeX file with retry mechanism"""
        for attempt in range(self.max_retries):
            try:
                # Read input file
                with open(input_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Standardize with retry
                standardized_content, success = self.standardize_with_retry(content, api_key)
                
                if success and standardized_content:
                    # Write to output file
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(standardized_content)
                    print(f"File standardization completed: {input_file} -> {output_file}")
                    return True
                
                print(f"Attempt {attempt + 1} failed, preparing to retry...")
                if attempt < self.max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    
            except Exception as e:
                print(f"Error processing file in attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                continue
        
        print(f"File standardization failed: {input_file} after {self.max_retries} attempts")
        return False

def standardize_tex_file(
    input_file: str, 
    output_file: str, 
    api_key: str, 
    init_file: str = "instructions/init.md",
    debug: bool = False
) -> bool:
    """
    Convenience function for standardizing LaTeX files
    
    Args:
        input_file: Input LaTeX file path
        output_file: Output LaTeX file path
        api_key: GPT-4 API key
        init_file: Standardization rules file path
        debug: Whether to enable prompt debugging
    
    Returns:
        bool: Whether the processing was successful
    """
    standardizer = LatexStandardizer(init_file, debug=debug)
    return standardizer.process_file(input_file, output_file, api_key) 

def main():
    parser = argparse.ArgumentParser(description='Standardize LaTeX files')
    parser.add_argument('input_file', help='Input LaTeX file path')
    parser.add_argument('output_file', help='Output LaTeX file path')
    parser.add_argument('--api-key', required=True, help='OpenAI API key')
    parser.add_argument('--init-file', default='instructions/init.md',
                      help='Path to initialization rules file')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug mode to save prompts and responses')
    parser.add_argument('--prompt-only', action='store_true',
                      help='In debug mode, only save prompts without responses')
    
    args = parser.parse_args()
    
    standardizer = LatexStandardizer(args.init_file, debug=args.debug)
    if args.prompt_only:
        standardizer._save_debug_info = lambda messages, response=None, **kwargs: \
            standardizer._save_debug_info(messages, response, prompt_only=True)
    
    success = standardizer.process_file(args.input_file, args.output_file, args.api_key)
    return 0 if success else 1

if __name__ == '__main__':
    exit(main()) 