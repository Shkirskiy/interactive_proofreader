# Interactive LaTeX Proofreader

An AI-powered tool for automatically proofreading LaTeX documents with an intuitive interactive interface.

## Features

- **Interactive Interface**: No need to remember command-line syntax
- **Secure Configuration**: API keys stored locally, never committed to version control
- **First-Run Setup**: Guided configuration on initial use
- **Comprehensive Processing**: Handles section titles, abstracts, highlights, keywords, captions, and paragraphs
- **AI-Powered**: Uses ChatGPT-4o-latest for high-quality proofreading
- **LaTeX-Aware**: Preserves all formatting, math expressions, and citations
- **Automatic Output**: Generates corrected files in the same directory as your original document
- **Diff Generation**: Creates highlighted difference files when latexdiff is available
- **Error Handling**: Robust validation and retry logic

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get an OpenRouter API key:**
   - Visit [openrouter.ai](https://openrouter.ai/)
   - Sign up or log in
   - Go to the 'Keys' section
   - Create a new API key

3. **Run the tool:**
   ```bash
   python interactive_proofreader.py
   ```
   
   On first run, you'll be guided through the setup process.

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Install Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- `pylatexenc>=2.10` - LaTeX document parsing
- `requests>=2.25.0` - HTTP requests for API communication

### Optional: Install latexdiff
For highlighted difference generation:

```bash
# On macOS with MacTeX:
# latexdiff is usually included with MacTeX

# On Ubuntu/Debian:
sudo apt-get install texlive-extra-utils

# On other systems:
# Install as part of your LaTeX distribution
```

## Configuration

### First-Time Setup
When you run the tool for the first time, it will guide you through configuration:

1. You'll be prompted to enter your OpenRouter API key
2. The tool will test the API key to ensure it's valid
3. Configuration will be saved to `config.json` (automatically ignored by git)
4. If needed, adapt general_prompt.txt for your specific needs

### Manual Configuration
If you prefer to set up configuration manually:

1. Copy `config.json.example` to `config.json`
2. Edit `config.json` and replace `YOUR_API_KEY_HERE` with your actual API key
3. Adjust other settings if needed (model, timeout, etc.)

### Configuration File Format
```json
{
    "openrouter": {
        "api_key": "sk-or-v1-your-actual-key-here",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/chatgpt-4o-latest",
        "max_retries": 3,
        "timeout": 120,
        "temperature": 0.1
    }
}
```

## Security

🔒 **API Key Security:**
- API keys are stored locally in `config.json`
- `config.json` is automatically excluded from git commits
- Never share your `config.json` file
- Use `config.json.example` as a template for others

⚠️ **Important:** Never commit your actual API key to version control!

## Usage

1. Run the script:
   ```bash
   python interactive_proofreader.py
   ```

2. Follow the interactive prompts:
   - Enter the path to your LaTeX document
   - Review the processing plan
   - Confirm to start proofreading

3. The tool will automatically:
   - Parse your LaTeX document
   - Send text sections to AI for proofreading
   - Apply corrections while preserving formatting
   - Generate output files in the same directory

## Output Files

For a document named `paper.tex`, the tool generates:

- `paper_corrected.tex` - The proofread version
- `paper_diff.tex` - Highlighted differences (if latexdiff is available)

## What Gets Processed

- **Section titles**: `\section{}`, `\subsection{}`, etc.
- **Special environments**: `abstract`, `highlights`, `keywords`
- **Captions**: `\caption{}` commands for figures and tables
- **Paragraphs**: Regular text blocks separated by blank lines

## Example Usage

```bash
$ python interactive_proofreader.py
============================================================
  Interactive LaTeX Proofreader
============================================================

This tool will automatically proofread your LaTeX document using AI.
It processes section titles, abstracts, highlights, keywords, captions, and paragraphs.

Enter the path to your LaTeX document: ~/Documents/my_paper.tex

Processing plan:
  Input file:     /Users/username/Documents/my_paper.tex
  Corrected file: /Users/username/Documents/my_paper_corrected.tex
  Diff file:      /Users/username/Documents/my_paper_diff.tex
  (latexdiff is available - diff highlighting will be generated)

Proceed with processing? (y/n): y

Starting proofreading process...
[Processing continues...]
```

## Error Handling

The tool includes comprehensive error handling:

- **File validation**: Checks if files exist and are readable
- **Path handling**: Supports both absolute and relative paths, handles quoted paths
- **API retries**: Automatic retry with exponential backoff for API failures
- **Graceful degradation**: Continues without latexdiff if not available
- **User confirmation**: Warns about overwriting existing files

## Technical Details

- **AI Model**: OpenAI ChatGPT-4o-latest via OpenRouter
- **LaTeX Parsing**: Uses pylatexenc for robust LaTeX document parsing
- **Diff Generation**: Leverages latexdiff with CCHANGEBAR type for highlighting
- **File Handling**: Preserves original file encoding and structure

## Notes

- The tool preserves ALL LaTeX formatting including math expressions, citations, and special characters
- Processing time depends on document length and API response times
- API calls include retry logic to handle temporary failures
- Large documents are processed section by section for better reliability

## Troubleshooting

1. **ModuleNotFoundError**: Install required packages with `pip install pylatexenc requests`
2. **File not found**: Check the file path and ensure the file exists
3. **Permission errors**: Ensure you have write permissions in the output directory
4. **API errors**: Check your internet connection; the tool will retry automatically

For more advanced usage or custom configurations, see the script's configuration section.
