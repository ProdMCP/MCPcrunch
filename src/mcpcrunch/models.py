from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"

class ValidationRule(BaseModel):
    id: str
    category: str
    name: str
    description: str
    severity: Severity

class ValidationIssue(BaseModel):
    rule_id: str
    path: str
    message: str
    severity: Severity
    evidence: Optional[str] = None

class ValidationReport(BaseModel):
    score: int = 0
    total_rules: int = 0
    passed_rules: int = 0
    issues: List[ValidationIssue] = []
    metadata: Dict[str, Any] = {}

class FullReport(BaseModel):
    deterministic: ValidationReport
    semantic: ValidationReport
    overall_score: int = 0
    timestamp: str
    openmcp_version: str
