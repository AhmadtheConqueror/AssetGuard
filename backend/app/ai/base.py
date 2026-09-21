from abc import ABC, abstractmethod

from app.ai.schemas import AIAnalysisExecution, AssetTelemetryContext


class AIAnalyzerError(RuntimeError):
    pass


class AIAnalyzerConfigurationError(AIAnalyzerError):
    pass


class AIAnalyzerUnavailableError(AIAnalyzerError):
    pass


class AIModelUnavailableError(AIAnalyzerUnavailableError):
    pass


class AIAnalyzerResponseError(AIAnalyzerError):
    pass


class AIAssetAnalyzer(ABC):
    @abstractmethod
    def analyze(self, context: AssetTelemetryContext) -> AIAnalysisExecution:
        raise NotImplementedError
