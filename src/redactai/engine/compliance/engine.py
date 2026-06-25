"""Compliance Engine for RedactAI."""

from dataclasses import dataclass, field

from redactai.engine.detectors.base import Match


@dataclass
class Finding:
    """A compliance finding derived from a Match."""
    match: Match
    regulations: set[str]
    compliance_severity: str
    remediation: str


@dataclass
class ComplianceReport:
    """Summary of compliance findings for a given payload."""
    total_findings: int
    regulations_triggered: set[str]
    critical_findings: int
    high_findings: int
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_findings": self.total_findings,
            "regulations_triggered": list(self.regulations_triggered),
            "critical_findings": self.critical_findings,
            "high_findings": self.high_findings,
            "findings": [
                {
                    "type": f.match.label,
                    "value_redacted": f.match.replacement,
                    "regulations": list(f.regulations),
                    "severity": f.compliance_severity,
                    "remediation": f.remediation,
                }
                for f in self.findings
            ],
        }


class ComplianceAnalyzer:
    """Analyze Matches and map them to regulatory frameworks."""

    # Map entity labels to relevant regulations
    REGULATION_MAP: dict[str, set[str]] = {
        "CREDIT_CARD": {"PCI DSS", "GDPR", "CCPA"},
        "SSN": {"HIPAA", "GDPR", "CCPA", "SOC2"},
        "EMAIL": {"GDPR", "CCPA"},
        "PHONE": {"GDPR", "CCPA"},
        "IPV4": {"GDPR", "CCPA"},
        "IPV6": {"GDPR", "CCPA"},
        "AWS_KEY": {"SOC2", "ISO 27001"},
        "OPENAI_KEY": {"SOC2", "ISO 27001"},
        "JWT": {"SOC2"},
        "PASSWORD": {"SOC2", "ISO 27001", "PCI DSS"},
        "SECRET": {"SOC2", "ISO 27001"},
        "CLOUD_KEY": {"SOC2", "ISO 27001"},
        "AUTH_TOKEN": {"SOC2", "ISO 27001"},
        "CRYPTO_KEY": {"SOC2", "ISO 27001"},
        "NETWORK_SECRET": {"SOC2", "ISO 27001"},
        "API_KEY": {"SOC2", "ISO 27001"},
        "GITHUB_TOKEN": {"SOC2", "ISO 27001"},
        # AI specific entities
        "PERSON": {"GDPR", "CCPA"},
        "LOCATION": {"GDPR", "CCPA"},
        "ORGANIZATION": {"GDPR", "CCPA"},
        "NRP": {"GDPR", "CCPA", "HIPAA"},
        "MEDICAL_LICENSE": {"HIPAA", "GDPR"},
        "UK_NHS": {"GDPR", "HIPAA"},
        "US_PASSPORT": {"GDPR", "CCPA"},
        "IBAN_CODE": {"PCI DSS", "GDPR"},
    }

    def analyze(self, matches: list[Match]) -> ComplianceReport:
        findings: list[Finding] = []
        regs_triggered: set[str] = set()
        critical_count = 0
        high_count = 0

        for m in matches:
            regs = self.REGULATION_MAP.get(m.label, {"GDPR", "CCPA"})
            regs_triggered.update(regs)

            # Map match severity to compliance severity
            comp_severity = m.severity
            if comp_severity == "CRITICAL":
                critical_count += 1
            elif comp_severity == "HIGH":
                high_count += 1

            # Determine remediation
            remediation = "Redact or tokenize immediately."
            if "PCI DSS" in regs:
                remediation = "Must be vaulted or tokenized via PCI-compliant vendor."
            elif "SOC2" in regs or "ISO 27001" in regs:
                remediation = "Rotate credential immediately and redact from logs."
            elif "HIPAA" in regs:
                remediation = "De-identify according to HIPAA Safe Harbor."

            findings.append(Finding(
                match=m,
                regulations=regs,
                compliance_severity=comp_severity,
                remediation=remediation
            ))

        return ComplianceReport(
            total_findings=len(findings),
            regulations_triggered=regs_triggered,
            critical_findings=critical_count,
            high_findings=high_count,
            findings=findings,
        )
