"""
Basic Usage Example for RedactAI Engine.
This demonstrates how to instantiate the engine and scan a simple string.
"""
from redactai.gateway.config.settings import get_settings
from redactai.gateway.core.container import Container
from redactai.gateway.core.models import Record

def main() -> None:
    # 1. Initialize the engine via container
    settings = get_settings().model_copy(deep=True)
    settings.detectors = ("email", "phone", "aws_key")
    container = Container(settings)
    engine = container.build_engine()
    engine.redact = True
    
    # 2. Text containing sensitive data
    text = "Please contact me at john.doe@example.com or call +1-555-019-8372. My AWS key is AKIAIOSFODNN7EXAMPLE."
    
    # 3. Scan the text (ProcessingEngine takes an iterable of Records)
    records = [Record(content=text, id="record-1")]
    
    # 4. Output the results
    print("--- Original ---")
    print(text)
    print("\n--- Redacted ---")
    
    with engine:
        for result in engine.process(records):
            print(result.redacted)
            print("\n--- Findings ---")
            for label in result.labels:
                print(f"[{label}] detected!")

if __name__ == "__main__":
    main()
