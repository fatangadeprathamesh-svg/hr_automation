from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class RuleOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class RuleSeverity(str, Enum):
    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


class RuleResult(BaseModel):
    rule_id: str
    rule_version: str = "1.0"
    status: RuleOutcome
    severity: RuleSeverity
    evidence: Dict[str, Any] = Field(default_factory=dict)
    policy_version: str
    suggested_action: Optional[str] = None
    is_data_health_issue: bool = False


class BaseRule(ABC):
    rule_id: str
    rule_version: str = "1.0"

    @abstractmethod
    def evaluate(self, context: Dict[str, Any], policy_config: Dict[str, Any], policy_version: str) -> List[RuleResult]:
        """
        Executes deterministic rule check against the employee period context.
        Must return 4 outcomes only: pass, fail, unknown, not_applicable.
        """
        pass
