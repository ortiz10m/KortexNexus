"""Shim de compatibilidad hacia kortex_core.optimizer."""

from kortex_core.config import SISTEMA, es_admin as _es_admin
from kortex_core.optimizer import KernelOptimizer, SYSCTL_KORTEX

KernelInterface = KernelOptimizer

__all__ = ["KernelInterface", "KernelOptimizer", "SISTEMA", "SYSCTL_KORTEX", "_es_admin"]
