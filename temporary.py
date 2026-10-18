from services.ai_schemas import ReEvaluationResult

ReEvaluationResult.model_json_schema()

result = ReEvaluationResult(
    decision="manual_followup",
    reason="Test fallback")

print(result)
