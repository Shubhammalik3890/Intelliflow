class Task:
    def __init__(self, task_id: str, tenant_id: str, cpu_required: float, memory_required: float, latency_sensitivity: str, description: str = ""):
        self.task_id = task_id
        self.tenant_id = tenant_id
        self.cpu_required = cpu_required
        self.memory_required = memory_required
        self.latency_sensitivity = latency_sensitivity
        self.description = description

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "tenant_id": self.tenant_id,
            "cpu_required": self.cpu_required,
            "memory_required": self.memory_required,
            "latency_sensitivity": self.latency_sensitivity,
            "description": self.description,
        }

def create_task(task_id: str, tenant_id: str, cpu: float, memory: float,
                sensitivity: str, description: str = "") -> Task:
    if cpu <= 0 or memory <= 0:
        raise ValueError("CPU and memory requirements must be greater than zero.")
    if sensitivity not in {"High", "Medium", "Low"}:
        raise ValueError("Sensitivity must be High, Medium, or Low.")
    return Task(task_id, tenant_id, float(cpu), float(memory), sensitivity, description)
