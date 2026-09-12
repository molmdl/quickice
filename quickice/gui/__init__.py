"""QuickIce GUI Application.

Startup-performance note (slow-gui-startup fix): re-exports are LAZY via
PEP 562 ``__getattr__``. The ion renderer (and anything importing
vtkmodules) must not load merely because ``quickice.gui`` was imported —
see quickice/gui/vtk_utils.py and AGENTS.md lazy-import rule.
"""

import importlib

# name -> submodule that defines it
_EXPORT_TO_MODULE = {
    "MainWindow": "main_window",
    "run_app": "main_window",
    "PhaseDiagramPanel": "phase_diagram_widget",
    "HydratePanel": "hydrate_panel",
    "IonPanel": "ion_panel",
    # Ion renderer (imports vtkmodules — keep lazy)
    "NA_COLOR": "ion_renderer",
    "CL_COLOR": "ion_renderer",
    "NA_VDW_RADIUS": "ion_renderer",
    "CL_VDW_RADIUS": "ion_renderer",
    "create_na_actor": "ion_renderer",
    "create_cl_actor": "ion_renderer",
    "render_ion_structure": "ion_renderer",
    "add_ion_actors_to_viewer": "ion_renderer",
    "remove_ion_actors_from_viewer": "ion_renderer",
    "toggle_ion_visibility": "ion_renderer",
}

__all__ = sorted(_EXPORT_TO_MODULE)


def __getattr__(name: str):
    """PEP 562 lazy re-export: load the defining submodule on first access."""
    try:
        submodule = _EXPORT_TO_MODULE[name]
    except KeyError:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from None
    module = importlib.import_module(f"{__name__}.{submodule}")
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(_EXPORT_TO_MODULE))
