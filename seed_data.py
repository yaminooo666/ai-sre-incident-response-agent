from database import SessionLocal
import models

db = SessionLocal()

try:
    runbook1 = models.Runbook(
        title="Payment Service High Error Rate Runbook",
        service_name="payment-service",
        alert_type="high_error_rate",
        content="""
1. Check recent application error logs.
2. Inspect service latency and error rate metrics.
3. Verify whether downstream dependencies are failing.
4. If service remains unstable, restart the affected service instance after approval.
"""
    )

    runbook2 = models.Runbook(
        title="Auth Service High Error Rate Runbook",
        service_name="auth-service",
        alert_type="high_error_rate",
        content="""
1. Check authentication failure logs.
2. Inspect request spike and latency metrics.
3. Verify cache and token validation dependencies.
4. Escalate if failures continue.
"""
    )

    history1 = models.IncidentHistory(
        incident_title="Payment service error spike on checkout",
        service_name="payment-service",
        alert_type="high_error_rate",
        severity=3,
        problem_summary="The payment service error rate increased sharply during peak traffic.",
        resolution_summary="Engineers checked logs and metrics, found unstable service instances, and restarted the affected instance.",
        outcome="resolved"
    )

    history2 = models.IncidentHistory(
        incident_title="Payment service database connection exhaustion",
        service_name="payment-service",
        alert_type="db_connection_exhausted",
        severity=4,
        problem_summary="The payment service could not acquire new database connections.",
        resolution_summary="The team inspected connection pool metrics, checked DB-related logs, and restarted the service after approval.",
        outcome="resolved"
    )

    db.add(runbook1)
    db.add(runbook2)
    db.add(history1)
    db.add(history2)
    db.commit()

    print("Seed data inserted successfully.")

finally:
    db.close()