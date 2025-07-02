#!/usr/bin/env python3
# interactive_proofreader.py
#
# Interactive LaTeX proofreading tool with LLM integration
# pip install pylatexenc requests
#
# Usage:
#   python interactive_proofreader.py
#   (Then follow the interactive prompts)

import re
import sys
import requests
import time
import subprocess
import os
import json
from pylatexenc.latexwalker import LatexWalker, LatexMacroNode

# Configuration will be loaded from config.json
OPENROUTER_CONFIG = None

def check_latexdiff_available():
    """Check if latexdiff is available on the system"""
    try:
        result = subprocess.run(['latexdiff', '--version'], 
                              capture_output=True, text=True, timeout=10)
        # latexdiff --version returns 255 but still works, and outputs to stderr
        # Check if latexdiff is available by looking for "LATEXDIFF" in the output
        output = result.stdout + result.stderr
        return "LATEXDIFF" in output
    except Exception as e:
        return False

def run_latexdiff(original_file, corrected_file, diff_file):
    """Run latexdiff to create a highlighted diff file"""
    try:
        # Use CCHANGEBAR type for colored highlighting
        cmd = ['latexdiff', '--type=CCHANGEBAR', original_file, corrected_file]
        
        print(f"Running latexdiff to create highlighted diff...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            # Write the diff output to file
            with open(diff_file, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
            print(f"Diff file created successfully: {diff_file}")
            return True
        else:
            print(f"latexdiff failed with return code {result.returncode}")
            if result.stderr:
                print(f"Error output: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("latexdiff timed out after 120 seconds")
        return False
    except Exception as e:
        print(f"Error running latexdiff: {str(e)}")
        return False

def load_system_prompt():
    """Load the system prompt from general_prompt.txt"""
    try:
        with open('general_prompt.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("Warning: general_prompt.txt not found. Using default prompt.")
        return "You are a scientific proofreader. Correct the text and highlight changes with \\hl{}."

def send_to_llm(text, system_prompt, retry_count=0):
    """Send text to LLM for proofreading with retry logic"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_CONFIG['api_key']}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": OPENROUTER_CONFIG["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": OPENROUTER_CONFIG["temperature"]
    }
    
    try:
        response = requests.post(
            f"{OPENROUTER_CONFIG['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=OPENROUTER_CONFIG["timeout"]
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content'].strip()
            else:
                raise Exception("Invalid response format from API")
        else:
            raise Exception(f"API returned status code {response.status_code}: {response.text}")
            
    except Exception as e:
        if retry_count < OPENROUTER_CONFIG["max_retries"]:
            print(f"  → API call failed, retrying ({retry_count + 1}/{OPENROUTER_CONFIG['max_retries']})...")
            time.sleep(2 ** retry_count)  # Exponential backoff
            return send_to_llm(text, system_prompt, retry_count + 1)
        else:
            print(f"  → Failed after {OPENROUTER_CONFIG['max_retries']} retries: {str(e)}")
            return text  # Return original text on failure

def get_user_input():
    """Get input file path from user with validation"""
    print("=" * 60)
    print("  Interactive LaTeX Proofreader")
    print("=" * 60)
    print()
    print("This tool will automatically proofread your LaTeX document using AI.")
    print("It processes section titles, abstracts, highlights, keywords, captions, and paragraphs.")
    print()
    
    while True:
        input_path = input("Enter the path to your LaTeX document: ").strip()
        
        # Remove quotes if user wrapped the path in quotes
        if input_path.startswith('"') and input_path.endswith('"'):
            input_path = input_path[1:-1]
        if input_path.startswith("'") and input_path.endswith("'"):
            input_path = input_path[1:-1]
        
        if not input_path:
            print("Error: Please enter a file path.")
            continue
            
        # Convert to absolute path for consistency
        input_path = os.path.abspath(input_path)
        
        # Check if file exists
        if not os.path.exists(input_path):
            print(f"Error: File not found: {input_path}")
            retry = input("Would you like to try again? (y/n): ").strip().lower()
            if retry not in ['y', 'yes']:
                print("Exiting...")
                sys.exit(1)
            continue
            
        # Check if it's a file (not a directory)
        if not os.path.isfile(input_path):
            print(f"Error: Path is not a file: {input_path}")
            continue
            
        # Check if it's readable
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                f.read(1)  # Try to read first character
        except Exception as e:
            print(f"Error: Cannot read file: {str(e)}")
            continue
            
        return input_path

def generate_output_paths(input_path: str):
    """Generate output file paths based on input path"""
    # Get directory and base filename
    input_dir = os.path.dirname(input_path)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    # Generate output paths
    corrected_path = os.path.join(input_dir, f"{base_name}_corrected.tex")
    diff_path = os.path.join(input_dir, f"{base_name}_diff.tex")
    
    return corrected_path, diff_path

def confirm_processing(input_path: str, corrected_path: str, diff_path: str):
    """Show user what will be generated and get confirmation"""
    print()
    print("Processing plan:")
    print(f"  Input file:     {input_path}")
    print(f"  Corrected file: {corrected_path}")
    if check_latexdiff_available():
        print(f"  Diff file:      {diff_path}")
        print("  (latexdiff is available - diff highlighting will be generated)")
    else:
        print("  (latexdiff not available - only corrected version will be generated)")
    print()
    
    # Check if output files already exist
    existing_files = []
    if os.path.exists(corrected_path):
        existing_files.append(corrected_path)
    if os.path.exists(diff_path):
        existing_files.append(diff_path)
        
    if existing_files:
        print("Warning: The following output files already exist and will be overwritten:")
        for file in existing_files:
            print(f"  - {file}")
        print()
    
    while True:
        response = input("Proceed with processing? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            print("Processing cancelled.")
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")

def get_section_context(content: str, position: int) -> str:
    """
    Find the current section context for a given position in the document.
    Returns the most recent section/subsection title before the position.
    """
    # Look backwards from position to find the most recent section
    text_before = content[:position]
    
    # Find all section commands before this position
    section_pattern = r'\\(chapter|section|subsection|subsubsection|paragraph|subparagraph)\s*\{([^}]*)\}'
    sections = list(re.finditer(section_pattern, text_before))
    
    if not sections:
        return "Document Start"
    
    # Get the last (most recent) section
    last_section = sections[-1]
    section_type = last_section.group(1)
    section_title = last_section.group(2).strip()
    
    return f"{section_type.title()}: \"{section_title}\""

def process_file(input_path: str, output_path: str):
    print("Loading configuration and system prompt...")
    system_prompt = load_system_prompt()
    
    print(f"Parsing LaTeX file: {input_path}")
    # 1) load
    content = open(input_path, 'r', encoding='utf-8').read()

    # 2) parse for sectioning macros
    walker = LatexWalker(content)
    nodes, _, _ = walker.get_latex_nodes()

    edits = []
    section_cmds = {
        'section','subsection','subsubsection',
        'paragraph','subparagraph','chapter'
    }

    # Collect section titles
    section_titles = []
    for node in nodes:
        if isinstance(node, LatexMacroNode) and node.macroname in section_cmds:
            arglist = getattr(node.nodeargd, 'argnlist', None)
            if arglist:
                grp = arglist[0].node  # this is a LatexGroupNode
                inner = content[grp.pos+1 : grp.pos_end-1]
                section_titles.append((grp.pos, grp.pos_end, inner, node.macroname))

    # 3) detect LaTeX environments (abstract, highlights, keywords)
    environments = ['abstract', 'highlights', 'keywords']
    env_elements = []
    
    for env_name in environments:
        pattern = rf'\\begin\{{{env_name}\}}(.*?)\\end\{{{env_name}\}}'
        for match in re.finditer(pattern, content, re.DOTALL):
            env_content = match.group(1).strip()
            env_elements.append((match.start(), match.end(), env_content, env_name))

    # 4) regex for \caption{…} - improved to handle nested braces
    captions = []
    pos = 0
    while True:
        # Find \caption{
        match = re.search(r'\\caption\s*\{', content[pos:])
        if not match:
            break
        
        start_pos = pos + match.start()
        brace_pos = pos + match.end() - 1  # position of opening brace
        
        # Find matching closing brace
        brace_count = 1
        i = brace_pos + 1
        while i < len(content) and brace_count > 0:
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
            i += 1
        
        if brace_count == 0:  # Found matching brace
            end_pos = i
            orig = content[brace_pos + 1:i - 1]  # content between braces
            captions.append((start_pos, end_pos, orig))
            pos = end_pos
        else:
            pos = start_pos + match.end()

    # 5) regex for paragraphs = text blocks separated by blank lines
    para_pat = re.compile(r'(?:\n|^)([^\n][\s\S]*?)(?=\n\s*\n)', re.MULTILINE)
    paragraphs = []
    for m in para_pat.finditer(content):
        para = m.group(1)
        # skip if it's purely a macro, empty, or a comment
        if (para.strip().startswith('\\') or 
            para.strip().startswith('%') or 
            not para.strip()):
            continue
        paragraphs.append((m.start(1), m.end(1), para))

    # Print summary of found elements
    print(f"Found {len(section_titles)} section titles, {len([e for e in env_elements if e[3] == 'abstract'])} abstract, {len([e for e in env_elements if e[3] == 'highlights'])} highlights, {len([e for e in env_elements if e[3] == 'keywords'])} keywords, {len(captions)} captions, {len(paragraphs)} paragraphs")
    print()

    # Process section titles
    if section_titles:
        print("Processing section titles...")
        for i, (start_pos, end_pos, inner, macro_name) in enumerate(section_titles, 1):
            print(f"[{i}/{len(section_titles)}] Processing {macro_name}: \"{inner.strip()[:50]}{'...' if len(inner.strip()) > 50 else ''}\" ({len(inner)} chars)")
            
            corrected_text = send_to_llm(inner, system_prompt)
            if corrected_text != inner:
                print(f"  → Text corrected")
            else:
                print(f"  → No changes needed")
            
            replacement = '{' + corrected_text + '}'
            edits.append((start_pos + (end_pos - start_pos - len(inner) - 2), end_pos - 1, replacement))
        print()

    # Process environments
    for env_name in environments:
        env_items = [e for e in env_elements if e[3] == env_name]
        if env_items:
            print(f"Processing {env_name}...")
            for i, (start_pos, end_pos, env_content, _) in enumerate(env_items, 1):
                section_context = get_section_context(content, start_pos)
                print(f"[{i}/{len(env_items)}] Processing {env_name} in {section_context} ({len(env_content)} chars)")
                
                corrected_text = send_to_llm(env_content, system_prompt)
                if corrected_text != env_content:
                    print(f"  → Text corrected")
                else:
                    print(f"  → No changes needed")
                
                repl = f"\\begin{{{env_name}}}{corrected_text}\\end{{{env_name}}}"
                edits.append((start_pos, end_pos, repl))
            print()

    # Process captions
    if captions:
        print("Processing captions...")
        for i, (start_pos, end_pos, orig) in enumerate(captions, 1):
            section_context = get_section_context(content, start_pos)
            print(f"[{i}/{len(captions)}] Processing caption in {section_context}: \"{orig.strip()[:50]}{'...' if len(orig.strip()) > 50 else ''}\" ({len(orig)} chars)")
            
            corrected_text = send_to_llm(orig, system_prompt)
            if corrected_text != orig:
                print(f"  → Text corrected")
            else:
                print(f"  → No changes needed")
            
            repl = f"\\caption{{{corrected_text}}}"
            edits.append((start_pos, end_pos, repl))
        print()

    # Process paragraphs
    if paragraphs:
        print("Processing paragraphs...")
        for i, (start_pos, end_pos, para) in enumerate(paragraphs, 1):
            section_context = get_section_context(content, start_pos)
            print(f"[{i}/{len(paragraphs)}] Processing paragraph in {section_context}: \"{para.strip()[:50]}{'...' if len(para.strip()) > 50 else ''}\" ({len(para.strip())} chars)")
            
            corrected_text = send_to_llm(para, system_prompt)
            if corrected_text != para:
                print(f"  → Text corrected")
            else:
                print(f"  → No changes needed")
            
            edits.append((start_pos, end_pos, corrected_text))
        print()

    print("Applying corrections to document...")
    # 6) apply all edits in reverse order so offsets stay valid
    edits.sort(key=lambda x: x[0], reverse=True)
    out = content
    for start, end, repl in edits:
        out = out[:start] + repl + out[end:]

    # 7) write result
    print(f"Writing corrected output to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(out)
    
    print(f"Processing complete! Total elements processed: {len(edits)}")
    
    # 8) Generate diff file using latexdiff
    if check_latexdiff_available():
        # Generate diff filename automatically
        base_name = os.path.splitext(output_path)[0]
        diff_file = f"{base_name}_diff.tex"
        
        print(f"latexdiff is available. Creating highlighted diff file...")
        success = run_latexdiff(input_path, output_path, diff_file)
        
        if success:
            print(f"Three files generated:")
            print(f"  - Original: {input_path}")
            print(f"  - Corrected: {output_path}")
            print(f"  - Highlighted diff: {diff_file}")
        else:
            print(f"latexdiff failed, but corrected file was created successfully.")
            print(f"Two files available:")
            print(f"  - Original: {input_path}")
            print(f"  - Corrected: {output_path}")
    else:
        print("latexdiff is not available on this system.")
        print("Continuing with corrected version only.")
        print(f"Two files available:")
        print(f"  - Original: {input_path}")
        print(f"  - Corrected: {output_path}")
        print("To enable diff highlighting, please install latexdiff (usually part of texlive-extra-utils package)")

def load_config():
    """Load configuration from config.json or create it on first run"""
    global OPENROUTER_CONFIG
    
    config_file = 'config.json'
    
    if not os.path.exists(config_file):
        print("=" * 60)
        print("  First Time Setup")
        print("=" * 60)
        print()
        print("Welcome! This appears to be your first time running the proofreader.")
        print("To use this tool, you need an OpenRouter API key.")
        print()
        print("To get an API key:")
        print("1. Visit https://openrouter.ai/")
        print("2. Sign up or log in")
        print("3. Go to 'Keys' section")
        print("4. Create a new API key")
        print()
        
        api_key = input("Please enter your OpenRouter API key: ").strip()
        
        if not api_key:
            print("Error: API key cannot be empty.")
            sys.exit(1)
        
        if not api_key.startswith('sk-or-v1-'):
            print("Warning: API key doesn't look like a typical OpenRouter key (should start with sk-or-v1-)")
            confirm = input("Continue anyway? (y/n): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("Setup cancelled.")
                sys.exit(1)
        
        # Test the API key
        print("\nTesting API key...")
        test_config = {
            "api_key": api_key,
            "base_url": "https://openrouter.ai/api/v1",
            "model": "openai/chatgpt-4o-latest",
            "max_retries": 1,
            "timeout": 30,
            "temperature": 0.1
        }
        
        if test_api_key(test_config):
            print("✓ API key is valid!")
            
            # Create config.json
            config_data = {
                "openrouter": test_config
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
            
            print(f"✓ Configuration saved to {config_file}")
            print()
            OPENROUTER_CONFIG = test_config
        else:
            print("✗ API key test failed. Please check your key and try again.")
            sys.exit(1)
    else:
        # Load existing configuration
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            if 'openrouter' not in config_data:
                print(f"Error: Invalid configuration format in {config_file}")
                print("Please check the config.json.example file for the correct format.")
                sys.exit(1)
            
            OPENROUTER_CONFIG = config_data['openrouter']
            
            # Validate required fields
            required_fields = ['api_key', 'base_url', 'model']
            for field in required_fields:
                if field not in OPENROUTER_CONFIG:
                    print(f"Error: Missing '{field}' in configuration.")
                    sys.exit(1)
            
            # Set defaults for optional fields
            OPENROUTER_CONFIG.setdefault('max_retries', 3)
            OPENROUTER_CONFIG.setdefault('timeout', 120)
            OPENROUTER_CONFIG.setdefault('temperature', 0.1)
            
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {config_file}: {str(e)}")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            sys.exit(1)

def test_api_key(config):
    """Test if the API key is working with a simple request"""
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "max_tokens": 5,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=config["timeout"]
        )
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"  Error testing API key: {str(e)}")
        return False

def main():
    """Main interactive interface"""
    try:
        # Load configuration first
        load_config()
        
        # Get input file from user
        input_path = get_user_input()
        
        # Generate output paths
        corrected_path, diff_path = generate_output_paths(input_path)
        
        # Show processing plan and get confirmation
        if not confirm_processing(input_path, corrected_path, diff_path):
            sys.exit(0)
        
        print()
        print("Starting proofreading process...")
        print("-" * 40)
        
        # Process the file
        process_file(input_path, corrected_path)
        
        print()
        print("=" * 60)
        print("  Processing Complete!")
        print("=" * 60)
        
        # Show final summary
        files_created = [corrected_path]
        if check_latexdiff_available() and os.path.exists(diff_path):
            files_created.append(diff_path)
        
        print("Files created:")
        for file_path in files_created:
            print(f"  ✓ {file_path}")
        
        print()
        print("You can now:")
        print("  - Review the corrected LaTeX file")
        if diff_path in files_created:
            print("  - Compile the diff file to see highlighted changes")
        print("  - Use the corrected version for your final document")
        print()
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
