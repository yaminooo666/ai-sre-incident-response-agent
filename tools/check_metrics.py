from datetime import datetime ,timedelta
from fastapi import HTTPException, status
from tools.mock_store import METRIC_STORE




def check_metrics(service_name,metric_names,minutes,restart_time=None):

    metrics=METRIC_STORE.get(service_name)

    cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

    if restart_time is not None:
        cutoff_time = max(restart_time, cutoff_time)

    abnormal_metrics={
        "check_metrics":[],
        "abnormal_reasons":[]
    }

    if metrics is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="metrics not found"
        )


    
    for metric in metrics:
        abnormal_reasons=[]
        if metric.get("timestamp")>=cutoff_time:

            if "cpu_usage" in metric_names and metric.get("cpu_usage") > 85:
                abnormal_reasons.append(
                    f"high_cpu_usage: {metric.get('cpu_usage')}%"
                )

            if "memory_usage" in metric_names and metric.get("memory_usage") > 85:
                abnormal_reasons.append(
                    f"high_memory_usage: {metric.get('memory_usage')}%"
                )

            if "error_rate" in metric_names and metric.get("error_rate") > 0.1:
                abnormal_reasons.append(
                    f"high_error_rate: {metric.get('error_rate')}"
                )

            if "latency_ms" in metric_names and metric.get("latency_ms") > 1000:
                abnormal_reasons.append(
                    f"high_latency: {metric.get('latency_ms')}ms"
                )

            dict1 = {}
            dict1["timestamp"] = metric.get("timestamp")
            for i in metric_names:
                dict1[i] = metric.get(i)
           
            abnormal_metrics["check_metrics"].append(dict1)

            if abnormal_reasons:
                abnormal_metrics["abnormal_reasons"].extend(abnormal_reasons)

    if not abnormal_metrics["check_metrics"]:
        abnormal_metrics["abnormal_reasons"].append("no_metrics_data_in_time_window")
                

    return abnormal_metrics

   


def create_abnormal_metrics():
    METRIC_STORE ={
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
    return METRIC_STORE             