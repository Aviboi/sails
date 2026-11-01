"""Check the settings-API paths used by build_case.py and run_fluent_sweep.py against the PyFluent generated API.
No Fluent needed: pip install ansys-fluent-core, then python verify_api.py [v252 ...]  (default: every version shipped).
Only names are checked, not allowed string values or runtime behaviour.
"""
import importlib, sys
PATHS = """file.read_mesh
file.read_case
file.write_case
setup.models.viscous.model
setup.boundary_conditions.velocity_inlet.*.momentum.velocity_specification_method
setup.boundary_conditions.velocity_inlet.*.momentum.velocity_components
setup.boundary_conditions.velocity_inlet.*.turbulence.turbulence_specification
setup.boundary_conditions.velocity_inlet.*.turbulence.turbulent_intensity
setup.boundary_conditions.velocity_inlet.*.turbulence.turbulent_viscosity_ratio
setup.materials.fluid.*.density
setup.materials.fluid.*.viscosity
solution.methods.p_v_coupling.flow_scheme
solution.methods.spatial_discretization.discretization_scheme|solution.methods.discretization_scheme
solution.report_definitions.force.*.zones
solution.report_definitions.force.*.force_vector
solution.report_definitions.moment.*.zones
solution.report_definitions.moment.*.mom_center
solution.report_definitions.moment.*.mom_axis
solution.report_definitions.compute
solution.initialization.hybrid_initialize
solution.initialization.initialize
solution.run_calculation.iterate""".split()

def children(cls):
    d = dict(getattr(cls, "_child_classes", {}) or {})
    return d

def walk(root, path):
    cls = root; trail = []
    for part in path.split("."):
        if part == "*":
            cls = getattr(cls, "child_object_type", None)
            if cls is None: return False, "/".join(trail) + " (no child_object_type)"
            trail.append("*"); continue
        ch = children(cls)
        al = getattr(cls, "_child_aliases", {}) or {}
        if part in ch: cls = ch[part]
        elif part in al: return False, f"{'/'.join(trail)}: '{part}' is an ALIAS for {al[part]}"
        else: return False, f"{'/'.join(trail)}: no '{part}'; has {sorted(ch)[:12]}"
        trail.append(part)
    return True, cls

import os, ansys.fluent.core.generated as _g
versions = sys.argv[1:] or sorted(d for p in _g.__path__ for d in os.listdir(p) if d.startswith("v") and d[1:].isdigit())
for v in versions:
    S = importlib.import_module(f"ansys.fluent.core.generated.{v}.solver.settings")
    print(f"== {v}")
    for p in PATHS:
        alts = [walk(S.root, q) for q in p.split("|")]
        ok, r = next((a for a in alts if a[0]), alts[0])
        extra = ""
        if ok and p.endswith(("iterate","read_mesh","write_case","read_case","compute","hybrid_initialize")):
            extra = " args=" + str(sorted(children(r)))
        print(("  ok   " if ok else "  MISS ") + p.split("|")[0] + (extra if ok else "  -> " + r))
