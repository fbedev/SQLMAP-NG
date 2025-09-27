from __future__ import annotations

from typing import Dict, List

from app.modules.base import ModuleMetadata, ScannerModule
from app.modules.live_sqli import MODULE as live_sqli_module
from app.modules.simulated_sqli import MODULE as simulated_sqli_module


REGISTERED_MODULES: Dict[str, ScannerModule] = {
    simulated_sqli_module.metadata.id: simulated_sqli_module,
    live_sqli_module.metadata.id: live_sqli_module,
}


def list_modules() -> List[ModuleMetadata]:
    return [module.metadata for module in REGISTERED_MODULES.values()]


def get_module(module_id: str) -> ScannerModule | None:
    return REGISTERED_MODULES.get(module_id)
