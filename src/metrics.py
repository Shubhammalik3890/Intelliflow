import pandas as pd

def summarize_results(records: list[dict], nodes) -> dict:
    df = pd.DataFrame(records)
    successful = int((df["status"] == "Successful").sum()) if not df.empty else 0
    failed = int((df["status"] == "Failed").sum()) if not df.empty else 0
    latencies = (
        pd.to_numeric(df.loc[df["status"] == "Successful", "simulated_latency_ms"], errors="coerce")
        if not df.empty else pd.Series(dtype=float)
    )
    return {
        "total_tasks": len(records),
        "successful_tasks": successful,
        "failed_tasks": failed,
        "success_rate_pct": round(successful / len(records) * 100, 2) if records else 0.0,
        "average_latency_ms": round(float(latencies.mean()), 2) if not latencies.empty else None,
        "nodes": [
            {
                "node_id": node.node_id,
                "node_type": node.node_type,
                "cpu_utilization_pct": round(node.cpu_utilization(), 2),
                "memory_utilization_pct": round(node.memory_utilization(), 2),
                "used_cpu": round(node.used_cpu, 2),
                "used_memory": round(node.used_memory, 2),
            }
            for node in nodes
        ],
    }

def results_dataframe(records: list[dict]) -> pd.DataFrame:
    columns = [
        "task_id", "tenant_id", "policy", "selected_node",
        "simulated_latency_ms", "status", "reason", "vm_id"
    ]
    return pd.DataFrame(records, columns=columns)
