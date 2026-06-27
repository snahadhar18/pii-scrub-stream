"""
Batch Processing Example.
Demonstrates how to use the Ingestion Engine to process CSV files.
"""
from pathlib import Path
from redactai.gateway.config.settings import get_settings
from redactai.gateway.core.container import Container
from redactai.gateway.ingestion.factory import SourceType

def main() -> None:
    input_file = Path("examples/sample.csv")
    output_file = Path("examples/output.csv")
    
    if not input_file.exists():
        print("Creating a dummy CSV file for testing...")
        with input_file.open('w') as f:
            f.write("id,name,email,notes\n")
            f.write("1,Alice,alice@example.com,Phone: +1-555-019-8372\n")
            f.write("2,Bob,bob@example.com,No sensitive info here.\n")

    # 1. Initialize the engine via container
    settings = get_settings().model_copy(deep=True)
    settings.detectors = ("email", "phone")
    settings.processing.workers = 2
    container = Container(settings)
    factory = container.ingestion_factory()

    print(f"Processing CSV: {input_file} -> {output_file}")
    
    # 2. Process the CSV
    out = output_file.open("w", encoding="utf-8")
    with container.build_engine() as engine:
        engine.redact = True
        with factory.for_path(str(input_file), SourceType.CSV) as source:
            for result in engine.process(source.read_records()):
                out.write((result.redacted or "") + "\n")
    
    out.close()
    print("Done! Processed records successfully.")

if __name__ == "__main__":
    main()
