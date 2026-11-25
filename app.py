import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from src.nodes import create_default_nodes
from src.tasks import Task, create_task
from src.scheduler import Scheduler
from src.vm_manager import VMManager
from src.experiments import (
    run_capacity_latency_experiment,
    run_overload_experiment,
    run_policy_experiment,
)
from src.metrics import results_dataframe

st.set_page_config(page_title="Edge–Fog–Cloud Task Scheduler", page_icon="☁️", layout="centered")
st.title("☁️ Edge–Fog–Cloud Task Scheduler")
st.write("Enter a task and check whether it will run on **Edge, Fog, or Cloud**.")

if "nodes" not in st.session_state:
    st.session_state.nodes = create_default_nodes()
if "vm_manager" not in st.session_state:
    st.session_state.vm_manager = VMManager()
if "history" not in st.session_state:
    st.session_state.history = []
if "submitted_tasks" not in st.session_state:
    st.session_state.submitted_tasks = []

st.subheader("1. Enter task details")
with st.form("task_form"):
    task_name = st.text_input("Task name", value="My Task")
    tenant_id = st.text_input("Tenant ID", value="user-1")
    col1, col2 = st.columns(2)
    with col1:
        cpu = st.number_input("CPU required (cores)", min_value=0.1, max_value=16.0, value=1.0, step=0.5)
    with col2:
        ram = st.number_input("RAM required (GB)", min_value=0.1, max_value=64.0, value=1.0, step=0.5)
    sensitivity = st.selectbox("Latency sensitivity", ["High", "Medium", "Low"], help="High = needs a very fast response; Low = can tolerate more delay.")
    submitted = st.form_submit_button("Check task placement", type="primary", width="stretch")

if submitted:
    try:
        task = create_task(
            task_id=task_name.strip() or "Task",
            tenant_id=tenant_id.strip() or "user-1",
            cpu=float(cpu),
            memory=float(ram),
            sensitivity=sensitivity,
            description=task_name.strip() or "Task",
        )
        result = Scheduler(policy="Lowest-latency-first").place_task(task, st.session_state.nodes, st.session_state.vm_manager)
        st.session_state.submitted_tasks.append(task.to_dict())
        st.session_state.history.insert(0, {
            "Task": task.task_id, "CPU": task.cpu_required, "RAM (GB)": task.memory_required,
            "Sensitivity": task.latency_sensitivity, "Selected location": result["selected_node"],
            "Latency (ms)": result["simulated_latency_ms"],
            "Status": result["status"], "Reason": result["reason"],
        })
        st.session_state.last_result = result
    except Exception as exc:
        st.error(f"Could not process this task: {exc}")

if "last_result" in st.session_state:
    result = st.session_state.last_result
    st.subheader("2. Placement result")
    if result["status"] == "Successful":
        tier = result["selected_node"].split("-")[0].title()
        st.success(f"Your task will run on **{tier}**.")
        st.metric("Simulated latency", f"{result['simulated_latency_ms']} ms")
        st.caption("Selected from nodes meeting the task's latency limit and available CPU/RAM.")
    else:
        st.error("No suitable node found — task rejected.")
        st.write(result["reason"])

st.divider()
st.subheader("3. Current Edge / Fog / Cloud capacity")
node_rows = [{
    "Location": n.node_type, "Latency": f"{n.latency_ms} ms",
    "Available CPU": f"{n.available_cpu():g} / {n.cpu_capacity:g} cores",
    "Available RAM": f"{n.available_memory():g} / {n.memory_capacity:g} GB",
} for n in st.session_state.nodes]
st.dataframe(pd.DataFrame(node_rows), hide_index=True, width="stretch")

st.subheader("4. Task history")
if st.session_state.history:
    history_dataframe = pd.DataFrame(st.session_state.history)
    history_dataframe["Latency (ms)"] = pd.to_numeric(
        history_dataframe["Latency (ms)"],
        errors="coerce",
    ).astype("float64")
    st.dataframe(history_dataframe, hide_index=True, width="stretch")
else:
    st.info("No tasks submitted yet. Add a task above to see where it gets placed.")

st.divider()
st.subheader("5. Experiment analysis and performance metrics")

if st.session_state.submitted_tasks:
    submitted_tasks = [Task(**task_data) for task_data in st.session_state.submitted_tasks]
    lowest_latency = run_policy_experiment("Lowest-latency-first", submitted_tasks)
    capacity_aware = run_policy_experiment("Capacity-aware", submitted_tasks)
    overload_result = run_overload_experiment(submitted_tasks)
    capacity_result = run_capacity_latency_experiment(submitted_tasks)
    scenarios = [
        ("Lowest-latency-first", lowest_latency["records"], lowest_latency["summary"]),
        ("Capacity-aware", capacity_aware["records"], capacity_aware["summary"]),
        (
            "Capacity/latency changed",
            capacity_result["changed_records"],
            capacity_result["changed_summary"],
        ),
        ("Overload (submitted tasks repeated)", overload_result["records"], overload_result["summary"]),
    ]
    baseline_summary = capacity_result["baseline_summary"]
    scenarios.insert(
        2,
        ("Capacity/latency baseline", capacity_result["baseline_records"], baseline_summary),
    )

    summary_rows = []
    experiment_records = []
    for label, records, summary in scenarios:
        summary_nodes = summary["nodes"]
        summary_rows.append({
            "Experiment": label,
            "Tasks": summary["total_tasks"],
            "Placed": summary["successful_tasks"],
            "Rejected": summary["failed_tasks"],
            "Success rate (%)": summary["success_rate_pct"],
            "Average latency (ms)": summary["average_latency_ms"],
            "Mean CPU utilization (%)": round(
                sum(node["cpu_utilization_pct"] for node in summary_nodes) / len(summary_nodes), 2
            ),
            "Mean RAM utilization (%)": round(
                sum(node["memory_utilization_pct"] for node in summary_nodes) / len(summary_nodes), 2
            ),
        })
        result_rows = results_dataframe(records)
        result_rows.insert(0, "Experiment", label)
        experiment_records.append(result_rows)

    summary_table = pd.DataFrame(summary_rows)
    st.caption(
        f"All scenarios use the {len(submitted_tasks)} task(s) submitted in this app session. "
        "The overload case repeats those same tasks until aggregate node capacity is exceeded."
    )
    st.dataframe(summary_table, hide_index=True, width="stretch")

    figure, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    baseline_placements = pd.DataFrame(lowest_latency["records"])
    placement_counts = baseline_placements["selected_node"].value_counts()
    node_labels = [node["node_id"] for node in lowest_latency["summary"]["nodes"]]
    node_labels.append("Rejected")
    axes[0].bar(
        node_labels,
        [int(placement_counts.get(node, 0)) for node in node_labels],
        color="#4C78A8",
    )
    axes[0].set_title("Task placement")
    axes[0].set_ylabel("Tasks")
    axes[0].tick_params(axis="x", rotation=30)

    baseline_nodes = pd.DataFrame(lowest_latency["summary"]["nodes"]).set_index("node_id")
    baseline_nodes[["cpu_utilization_pct", "memory_utilization_pct"]].rename(
        columns={
            "cpu_utilization_pct": "CPU",
            "memory_utilization_pct": "RAM",
        }
    ).plot(kind="bar", ax=axes[1], color=["#59A14F", "#F28E2B"])
    axes[1].set_title("Resource utilization (baseline)")
    axes[1].set_ylabel("Utilization (%)")
    axes[1].set_ylim(0, 100)
    axes[1].tick_params(axis="x", rotation=30)
    axes[1].legend(title="Resource")

    scenario_labels = [row["Experiment"] for row in summary_rows]
    success_rates = [row["Success rate (%)"] for row in summary_rows]
    average_latencies = [row["Average latency (ms)"] for row in summary_rows]
    scenario_positions = range(len(scenario_labels))
    axes[2].bar(scenario_positions, success_rates, color="#59A14F", label="Success rate")
    axes[2].set_title("Quality of service")
    axes[2].set_ylabel("Success rate (%)")
    axes[2].set_ylim(0, 100)
    axes[2].set_xticks(list(scenario_positions))
    axes[2].set_xticklabels(scenario_labels, rotation=35, ha="right")
    latency_axis = axes[2].twinx()
    valid_latencies = [
        (position, latency)
        for position, latency in zip(scenario_positions, average_latencies)
        if latency is not None
    ]
    if valid_latencies:
        latency_positions, latency_values = zip(*valid_latencies)
        latency_axis.plot(
            latency_positions,
            latency_values,
            color="#E15759",
            marker="o",
            label="Average latency",
        )
    latency_axis.set_ylabel("Average latency (ms)")
    axes[2].legend(loc="upper left")
    latency_axis.legend(loc="upper right")
    figure.tight_layout()
    st.pyplot(figure, width="stretch")
    plt.close(figure)

    with st.expander("Show experiment task-level results"):
        all_experiment_records = pd.concat(experiment_records, ignore_index=True)
        st.dataframe(all_experiment_records, hide_index=True, width="stretch")
        st.download_button(
            "Download experiment results (CSV)",
            all_experiment_records.to_csv(index=False).encode("utf-8"),
            "experiment_results.csv",
            "text/csv",
            width="stretch",
        )
else:
    st.info(
        "Submit tasks above to see the policy, overload, and capacity/latency experiments. "
        "The analysis uses only tasks entered during this session."
    )

col_a, col_b = st.columns(2)
with col_a:
    if st.button("Reset capacity and history", width="stretch"):
        st.session_state.nodes = create_default_nodes()
        st.session_state.vm_manager = VMManager()
        st.session_state.history = []
        st.session_state.submitted_tasks = []
        st.session_state.pop("last_result", None)
        st.rerun()
with col_b:
    if st.session_state.history:
        csv = pd.DataFrame(st.session_state.history).to_csv(index=False).encode("utf-8")
        st.download_button("Download results (CSV)", csv, "task_placement_results.csv", "text/csv", width="stretch")

with st.expander("How does the decision work?"):
    st.markdown("""
    - **High sensitivity:** maximum latency 20 ms.
    - **Medium sensitivity:** maximum latency 60 ms.
    - **Low sensitivity:** maximum latency 150 ms.
    - A node must also have enough free CPU and RAM.
    - Among eligible nodes, the scheduler chooses the one with the lowest latency.

    This is an educational simulation; it does not launch real cloud servers or virtual machines.
    """)
