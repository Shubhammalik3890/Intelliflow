from itertools import count
from src.nodes import Node
from src.tasks import Task


class VirtualMachine:
    def __init__(
        self,
        vm_id: str,
        task_id: str,
        tenant_id: str,
        host_node: str,
        allocated_cpu: float,
        allocated_ram: float,
        status: str = "Running",
    ):
        self.vm_id = vm_id
        self.task_id = task_id
        self.tenant_id = tenant_id
        self.host_node = host_node
        self.allocated_cpu = allocated_cpu
        self.allocated_ram = allocated_ram
        self.status = status

    def to_dict(self) -> dict:
        return {
            "vm_id": self.vm_id,
            "task_id": self.task_id,
            "tenant_id": self.tenant_id,
            "host_node": self.host_node,
            "allocated_cpu": self.allocated_cpu,
            "allocated_ram": self.allocated_ram,
            "status": self.status,
        }


class VMManager:
    def __init__(self):
        self.vms: list[VirtualMachine] = []
        self._counter = count(1)

    def create_vm(self, task: Task, node: Node) -> VirtualMachine | None:
        if not node.allocate_resources(task.cpu_required, task.memory_required):
            return None
        vm = VirtualMachine(
            vm_id=f"VM-{next(self._counter):03d}",
            task_id=task.task_id,
            tenant_id=task.tenant_id,
            host_node=node.node_id,
            allocated_cpu=task.cpu_required,
            allocated_ram=task.memory_required,
        )
        self.vms.append(vm)
        return vm

    def stop_vm(self, vm_id: str, nodes: list[Node]) -> bool:
        vm = next((item for item in self.vms if item.vm_id == vm_id), None)
        if vm is None or vm.status != "Running":
            return False
        node = next((item for item in nodes if item.node_id == vm.host_node), None)
        if node is None:
            return False
        node.release_resources(vm.allocated_cpu, vm.allocated_ram)
        vm.status = "Stopped"
        return True

    def running_vms(self) -> list[VirtualMachine]:
        return [vm for vm in self.vms if vm.status == "Running"]
