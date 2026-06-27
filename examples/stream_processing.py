"""
Stream Processing Example.
Demonstrates how to use the StreamProcessor for filtering large streams in real time.
"""
import sys
from pathlib import Path
from redactai.gateway.config.settings import get_settings
from redactai.gateway.core.container import Container
from redactai.gateway.streaming.stream import StreamProcessor

def main() -> None:
    input_file = Path("examples/sample.log")
    output_file = Path("examples/output.log")
    
    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        return

    # 1. Initialize the engine via container
    settings = get_settings().model_copy(deep=True)
    settings.detectors = ("email", "phone", "ssn", "aws_key")
    settings.processing.workers = 4
    container = Container(settings)
    engine = container.build_engine()
    engine.redact = True
    
    # 2. Create the stream processor
    processor = StreamProcessor(engine, emit_redacted=True)
    
    print(f"Streaming {input_file} -> {output_file}...")
    
    with input_file.open('r', encoding='utf-8') as f_in, \
         output_file.open('w', encoding='utf-8') as f_out:
        
        # 3. Stream process from stdin to stdout equivalents
        processor.run(f_in, f_out)
            
    print("Done! Check output.log")

if __name__ == "__main__":
    main()
