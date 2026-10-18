from datetime import datetime,timedelta


METRIC_STORE = {}

def create_abnormal_metrics():
    return {
        "payment-service": [
            {
                "timestamp": datetime.utcnow() - timedelta(minutes=2),
                "cpu_usage": 45,
                "memory_usage": 62,
                "error_rate": 0.02,
                "latency_ms": 180
            },
            {
                "timestamp": datetime.utcnow() - timedelta(minutes=1),
                "cpu_usage": 92,
                "memory_usage": 88,
                "error_rate": 0.18,
                "latency_ms": 1200
            }
        ]
    }