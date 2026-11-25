from math import floor

from src.nodes import create_default_nodes
from src.tasks import Task
from src.scheduler import Scheduler
from src.vm_manager import VMManager
from src.metrics import summarize_results

def run_policy_experiment(policy: str, tasks: list[Task]) -> dict:
    nodes = create_default_nodes()
    manager = VMManager()
    scheduler = Scheduler(policy)
    records = [scheduler.place_task(task, nodes, manager) for task in tasks]
    return {"policy": policy, "records": records, "summary": summarize_results(records, nodes)}

def run_overload_experiment(tasks: list[Task]) -> dict:
    if not tasks:
        raise ValueError("At least one submitted task is required for the overload experiment.")

    nodes = create_default_nodes()
    manager = VMManager()
    scheduler = Scheduler("Lowest-latency-first")
    cpu_per_round = sum(task.cpu_required for task in tasks)
    memory_per_round = sum(task.memory_required for task in tasks)
    repetitions = max(
        floor(sum(node.cpu_capacity for node in nodes) / cpu_per_round),
        floor(sum(node.memory_capacity for node in nodes) / memory_per_round),
    ) + 1
    overload_tasks = [
        Task(
            task_id=f"{task.task_id}-OVERLOAD-{repetition:03d}-{task_index:03d}",
            tenant_id=task.tenant_id,
            cpu_required=task.cpu_required,
            memory_required=task.memory_required,
            latency_sensitivity=task.latency_sensitivity,
            description=task.description,
        )
        for repetition in range(1, repetitions + 1)
        for task_index, task in enumerate(tasks, start=1)
    ]
    records = [scheduler.place_task(task, nodes, manager) for task in overload_tasks]
    return {"records": records, "summary": summarize_results(records, nodes)}

def run_capacity_latency_experiment(tasks: list[Task]) -> dict:
    baseline_nodes = create_default_nodes()
    baseline_manager = VMManager()
    baseline_scheduler = Scheduler("Lowest-latency-first")
    baseline_records = [baseline_scheduler.place_task(task, baseline_nodes, baseline_manager) for task in tasks]

    changed_nodes = create_default_nodes()
    # Demonstrate changed infrastructure: Edge capacity increases and Fog
    # latency decreases. These values are deliberately illustrative.
    changed_nodes[0].cpu_capacity = 8
    changed_nodes[0].memory_capacity = 16
    changed_nodes[1].latency_ms = 10
    changed_manager = VMManager()
    changed_scheduler = Scheduler("Lowest-latency-first")
    changed_records = [changed_scheduler.place_task(task, changed_nodes, changed_manager) for task in tasks]

    return {
        "baseline_records": baseline_records,
        "baseline_summary": summarize_results(baseline_records, baseline_nodes),
        "changed_records": changed_records,
        "changed_summary": summarize_results(changed_records, changed_nodes),
    }
