from enum import Enum


class ErrorSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class FamilyCenterError(Exception):
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR):
        self.message = message
        self.severity = severity
        super().__init__(self.message)
