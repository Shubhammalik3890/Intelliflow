class Node:
    def __init__(self, node_id: str, node_type: str, cpu_capacity: float, memory_capacity: float, latency_ms: float, used_cpu: float = 0.0, used_memory: float = 0.0):
        self.node_id = node_id
        self.node_type = node_type
        self.cpu_capacity = cpu_capacity
        self.memory_capacity = memory_capacity
        self.latency_ms = latency_ms
        self.used_cpu = used_cpu
        self.used_memory = used_memory

    def available_cpu(self) -> float:
        return max(0.0, self.cpu_capacity - self.used_cpu)

    def available_memory(self) -> float:
        return max(0.0, self.memory_capacity - self.used_memory)

    def cpu_utilization(self) -> float:
        return (self.used_cpu / self.cpu_capacity * 100) if self.cpu_capacity else 0.0

    def memory_utilization(self) -> float:
        return (self.used_memory / self.memory_capacity * 100) if self.memory_capacity else 0.0

    def can_host(self, cpu_required: float, memory_required: float) -> bool:
        return (
            cpu_required > 0
            and memory_required > 0
            and self.available_cpu() >= cpu_required
            and self.available_memory() >= memory_required
        )

    def allocate_resources(self, cpu_required: float, memory_required: float) -> bool:
        if not self.can_host(cpu_required, memory_required):
            return False
        self.used_cpu += cpu_required
        self.used_memory += memory_required
        return True

    def release_resources(self, cpu_allocated: float, memory_allocated: float) -> None:
        self.used_cpu = max(0.0, self.used_cpu - cpu_allocated)
        self.used_memory = max(0.0, self.used_memory - memory_allocated)

    def reset_usage(self) -> None:
        self.used_cpu = 0.0
        self.used_memory = 0.0

def create_default_nodes() -> list[Node]:
    return [
        Node("EDGE-01", "Edge", 4, 8, 5),
        Node("FOG-01", "Fog", 8, 16, 20),
        Node("CLOUD-01", "Cloud", 16, 64, 80),
    ]
