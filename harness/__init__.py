"""ICE benchmark harness.

Self-contained. No product code under ``ice/`` or ``ice_nexus/`` is modified by
anything in this package. The ICE engine is driven only through its public
surface (``ICEKernel``, ``EpisodicManager``, ``ContextPager``); the one
concession is a documented license-gate bypass in :mod:`benchmarks.harness.ice_env`.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
