from google import genai
from google.genai import errors, types
from httpx import HTTPError
from pydantic import ValidationError

from app.ai.base import (
    AIAnalyzerConfigurationError,
    AIAnalyzerResponseError,
    AIAnalyzerUnavailableError,
    AIAssetAnalyzer,
    AIModelUnavailableError,
)
from app.ai.schemas import AIAnalysisExecution, AIAnalysisResult, AssetTelemetryContext
from app.core.config import settings


SYSTEM_INSTRUCTION = """
You are an engineering decision-support assistant analyzing synthetic telemetry for software development.
No manufacturer operating envelope, OEM specification, or validated engineering alarm threshold has been provided.
Do not invent alarm limits or describe any value as exceeding a certified limit.
Do not claim equipment failure, an unsafe condition, or a particular mechanical fault is certain or proven.
Clearly distinguish directly observed telemetry facts from cautious interpretations and possible explanations.
The risk score and risk level represent analytical concern based only on the observed pattern; they are not a
certified equipment safety classification. Recommendations must be actions for qualified engineer review,
inspection, validation, or investigation. Do not recommend an autonomous shutdown or any control action that the
software itself performs. A qualified engineer remains the final decision-maker.
""".strip()


class GeminiAssetAnalyzer(AIAssetAnalyzer):
    def analyze(self, context: AssetTelemetryContext) -> AIAnalysisExecution:
        if settings.GEMINI_API_KEY is None:
            raise AIAnalyzerConfigurationError("Gemini API credentials are not configured")

        primary_model = settings.GEMINI_MODEL
        try:
            result = self._generate(primary_model, context)
        except AIModelUnavailableError:
            fallback_model = settings.GEMINI_FALLBACK_MODEL
            result = self._generate(fallback_model, context)
            return AIAnalysisExecution(
                result=result,
                primary_model=primary_model,
                model_used=fallback_model,
                fallback_used=True,
            )

        return AIAnalysisExecution(
            result=result,
            primary_model=primary_model,
            model_used=primary_model,
            fallback_used=False,
        )

    def _generate(self, model: str, context: AssetTelemetryContext) -> AIAnalysisResult:
        try:
            client = genai.Client(api_key=settings.GEMINI_API_KEY.get_secret_value())
            response = client.models.generate_content(
                model=model,
                contents=(
                    "Analyze the following deterministic telemetry context. Base every observation on the supplied "
                    "statistics and ordered series. Return concise, structured decision support.\n\n"
                    + context.model_dump_json(indent=2)
                ),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=AIAnalysisResult,
                    temperature=0.1,
                ),
            )
        except errors.APIError as exc:
            if exc.code == 429:
                raise AIAnalyzerUnavailableError("Gemini quota or rate limit was reached") from exc
            message = (exc.message or "").lower()
            fallback_eligible = (
                exc.code == 503
                or (
                    exc.code not in {400, 401, 403, 404, 429}
                    and (
                        exc.status == "UNAVAILABLE"
                        or "high demand" in message
                        or "capacity" in message
                    )
                )
            )
            if fallback_eligible:
                raise AIModelUnavailableError("Gemini is temporarily unavailable") from exc
            if exc.code >= 500:
                raise AIAnalyzerUnavailableError("Gemini is temporarily unavailable") from exc
            raise AIAnalyzerResponseError("Gemini rejected the analysis request") from exc
        except (HTTPError, OSError, TimeoutError) as exc:
            raise AIAnalyzerUnavailableError("Gemini could not be reached") from exc

        try:
            if isinstance(response.parsed, AIAnalysisResult):
                return response.parsed
            if response.parsed is not None:
                return AIAnalysisResult.model_validate(response.parsed)
            return AIAnalysisResult.model_validate_json(response.text)
        except (ValidationError, TypeError, ValueError) as exc:
            raise AIAnalyzerResponseError("Gemini returned an invalid structured response") from exc
