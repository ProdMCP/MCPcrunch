import json
import datetime
from typing import Dict, Any, Optional
from .models import FullReport, Severity
from .validators.deterministic import DeterministicValidator
from .validators.semantic import SemanticValidator
from .llm.base import LLMBase
from .scoring import generate_report

class MCPcrunch:
    def __init__(self, schema_path: str, llm: Optional[LLMBase] = None):
        self.deterministic_validator = DeterministicValidator(schema_path)
        self.semantic_validator = SemanticValidator(llm) if llm else None
        self.rules_count_det = len(self.deterministic_validator.rules)
        self.rules_count_sem = len(self.semantic_validator.rules) if self.semantic_validator else 0

    def audit(self, spec_data: Dict[str, Any]) -> FullReport:
        # Run deterministic validation
        det_issues = self.deterministic_validator.validate(spec_data)
        det_report = generate_report(self.rules_count_det, det_issues)

        # Run semantic validation if LLM is available
        sem_issues = []
        if self.semantic_validator:
            sem_issues = self.semantic_validator.validate(spec_data)
        
        sem_report = generate_report(self.rules_count_sem, sem_issues)

        overall_score = (det_report.score + sem_report.score) // 2 if self.semantic_validator else det_report.score

        return FullReport(
            deterministic=det_report,
            semantic=sem_report,
            overall_score=overall_score,
            timestamp=datetime.datetime.now().isoformat(),
            openmcp_version=spec_data.get("openmcp", "unknown")
        )
