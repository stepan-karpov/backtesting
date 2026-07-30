"""Backtesting packages for the microstructure research lab (lighter, hyperliquid).

A regular package (not a namespace) so a compiled extension like ``lighter._engine``
resolves to a single canonical path and is imported exactly once — importing it under
two names (e.g. a duplicated sys.path entry under pytest) would double-register its
pybind11 types and fail.
"""
