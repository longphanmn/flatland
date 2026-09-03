"""Simulation package — re-exports core for backwards compatibility."""

from __future__ import annotations

import sys as _sys
from types import ModuleType as _ModuleType

from .core import Simulation, glyph_for, personal_name_for, variation_for

__all__ = ["Simulation", "glyph_for", "personal_name_for", "variation_for"]

_core_name = __name__ + ".core"


def __getattr__(name: str):  # PEP 562
    return getattr(_sys.modules[_core_name], name)


def __dir__():
    try:
        return sorted(set(dir(_sys.modules[_core_name]) | set(globals().keys())))
    except Exception:
        return []


class _SimulationPackage(_ModuleType):
    def __setattr__(self, name, value):
        # Forward to all submodules that may have this name (constants, mixins)
        for mod_name in [
            _core_name,
            __name__ + ".constants",
            __name__ + ".serialization",
            __name__ + ".ecology",
            __name__ + ".environment",
            __name__ + ".settlement",
            __name__ + ".theology",
            __name__ + ".society",
            __name__ + ".lifecycle",
            __name__ + ".creature_update",
        ]:
            try:
                mod = _sys.modules.get(mod_name)
                if mod is not None and hasattr(mod, name):
                    setattr(mod, name, value)
                elif name.isupper() or name.startswith("_"):
                    # Also set even if not hasattr, for constants that may be created
                    try:
                        setattr(mod, name, value)
                    except Exception:
                        pass
            except Exception:
                pass
        # Also set on core
        try:
            setattr(_sys.modules[_core_name], name, value)
        except Exception:
            pass
        return super().__setattr__(name, value)


try:
    _sys.modules[__name__].__class__ = _SimulationPackage  # type: ignore[assignment]
except Exception:
    pass
