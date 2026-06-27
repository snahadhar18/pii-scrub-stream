import os
from pathlib import Path

def process_file(filepath):
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception:
        return

    original_content = content

    # Package path replacements
    content = content.replace("redactai.engine", "redactai.engine")
    content = content.replace("redactai.gateway", "redactai.gateway")
    
    # In pyproject.toml and similar, we might have redactai.engine.engine ... wait. 
    # Let's fix the specific CLI script name if it exists.
    content = content.replace("redactai.engine.cli.main:cli", "redactai.engine.cli.main:cli")
    
    # Text replacements
    content = content.replace("redactai", "redactai")
    content = content.replace("redactai", "redactai")
    content = content.replace("RedactAI", "RedactAI")
    content = content.replace("RedactAI", "RedactAI")
    
    # Specific fix for tests where it tries to resolve absolute paths
    # Because tests are now in tests/engine and tests/gateway
    content = content.replace("tests/engine/test_", "tests/engine/test_")
    
    if content != original_content:
        filepath.write_text(content, encoding='utf-8')
        print(f"Updated {filepath}")

def main():
    root_dir = Path(".")
    
    # Extensions to process
    exts = {".py", ".toml", ".md", ".yml", ".yaml", ".txt", ".ini"}
    
    for root, dirs, files in os.walk(root_dir):
        if ".git" in root or ".pytest_cache" in root or ".cursor" in root or "__pycache__" in root:
            continue
            
        for file in files:
            if Path(file).suffix in exts:
                process_file(Path(root) / file)

if __name__ == "__main__":
    main()
