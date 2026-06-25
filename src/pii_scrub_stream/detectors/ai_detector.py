"""AI powered PII detector using Microsoft Presidio and spaCy."""

import logging
from typing import List

from pii_scrub_stream.detectors.base import Detector, Match

logger = logging.getLogger(__name__)

try:
    from presidio_analyzer import AnalyzerEngine
    HAS_PRESIDIO = True
except ImportError:
    HAS_PRESIDIO = False


class AIDetector(Detector):
    """Detect PII entities using NLP via Microsoft Presidio and spaCy.
    
    Detects: PERSON, LOCATION, ORGANIZATION, NRP (National IDs), 
    IBAN_CODE, DATE_TIME, and more.
    """

    label = "AI_ENTITY"
    default_severity = "MEDIUM"

    def __init__(self, languages: List[str] = None):
        if not HAS_PRESIDIO:
            raise ImportError(
                "Presidio is not installed. Install the AI dependencies with: "
                "pip install 'pii-scrub-stream[ai]'"
            )
        
        self.languages = languages or ["en"]
        try:
            self.analyzer = AnalyzerEngine()
        except Exception as e:
            logger.error(f"Failed to initialize Presidio analyzer: {e}")
            raise

    def get_severity(self, presidio_type: str) -> str:
        """Map Presidio entity types to severity levels."""
        critical = {"CREDIT_CARD", "CRYPTO", "IBAN_CODE", "MEDICAL_LICENSE", "US_SSN"}
        high = {"NRP", "US_PASSPORT", "UK_NHS", "EMAIL_ADDRESS", "PHONE_NUMBER"}
        if presidio_type in critical:
            return "CRITICAL"
        if presidio_type in high:
            return "HIGH"
        return "MEDIUM"

    def detect(self, text: str) -> List[Match]:
        matches: List[Match] = []
        if not text:
            return matches

        for lang in self.languages:
            # Analyze text for entities
            results = self.analyzer.analyze(text=text, language=lang)
            
            for result in results:
                value = text[result.start:result.end]
                matches.append(Match(
                    start=result.start,
                    end=result.end,
                    value=value,
                    label=result.entity_type,
                    confidence=round(result.score, 2),
                    severity=self.get_severity(result.entity_type),
                    replacement=f"[{result.entity_type}_REDACTED]"
                ))

        return matches
