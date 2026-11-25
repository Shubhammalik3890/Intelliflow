from src.nodes import Node
from src.tasks import Task
from src.vm_manager import VMManager

# Illustrative latency budgets used by this educational simulator.
LATENCY_BUDGET_MS = {"High": 20, "Medium": 60, "Low": 150}

class Scheduler:
    def __init__(self, policy: str = "Lowest-latency-first"):
        if policy not in {"Lowest-latency-first", "Capacity-aware"}:
            raise ValueError("Unknown placement policy.")
        self.policy = policy

    def choose_node(self, task: Task, nodes: list[Node]) -> Node | None:
        eligible = [
            node for node in nodes
            if node.latency_ms <= LATENCY_BUDGET_MS[task.latency_sensitivity]
            and node.can_host(task.cpu_required, task.memory_required)
        ]
        if not eligible:
            return None

        if self.policy == "Lowest-latency-first":
            return min(eligible, key=lambda node: (node.latency_ms, node.node_id))

        # Capacity-aware: prefer the node with the lowest projected combined
        # CPU/RAM utilization; use latency as a tie-breaker.
        def score(node: Node):
            cpu_after = (node.used_cpu + task.cpu_required) / node.cpu_capacity
            ram_after = (node.used_memory + task.memory_required) / node.memory_capacity
            projected_utilization = (cpu_after + ram_after) / 2
            return (projected_utilization, node.latency_ms)

        return min(eligible, key=score)

    def place_task(self, task: Task, nodes: list[Node],
                   vm_manager: VMManager) -> dict:
        node = self.choose_node(task, nodes)
        if node is None:
            return {
                "task_id": task.task_id,
                "tenant_id": task.tenant_id,
                "policy": self.policy,
                "selected_node": "Rejected",
                "simulated_latency_ms": None,
                "status": "Failed",
                "reason": "No node meets both the latency budget and resource requirements.",
                "vm_id": None,
            }

        vm = vm_manager.create_vm(task, node)
        if vm is None:
            return {
                "task_id": task.task_id,
                "tenant_id": task.tenant_id,
                "policy": self.policy,
                "selected_node": "Rejected",
                "simulated_latency_ms": None,
                "status": "Failed",
                "reason": "Resource allocation failed.",
                "vm_id": None,
            }

        # Simulated latency is the node's configured network/processing delay.
        return {
            "task_id": task.task_id,
            "tenant_id": task.tenant_id,
            "policy": self.policy,
            "selected_node": node.node_id,
            "simulated_latency_ms": node.latency_ms,
            "status": "Successful",
            "reason": "Task placed and simulated VM created.",
            "vm_id": vm.vm_id,
        }
