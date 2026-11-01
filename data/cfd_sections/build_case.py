#!/usr/bin/env python3
"""Build a Fluent case from a mesh made by make_mesh.py, with no GUI (PyFluent).

Reads the .msh, sets Transition SST, the inlet turbulence, solver schemes and the force/moment reports,
initialises, and saves <out>.cas.h5. Then run_fluent_sweep.py loops over the angles.

STATUS: written from the PyFluent settings-API documentation and NOT run against a Fluent installation.
Every step is wrapped: a failing step is logged and the script carries on, so you get one list of what needs
fixing for your Fluent/PyFluent version. Check the printed state of the inlet and the schemes, and run
`--check-only` first if you want the mesh checks without changing anything.

Defaults relied on (Fluent's own): air at 1.225 kg/m^3 and 1.7894e-5 Pa s, pressure outlet at 0 gauge, pressure-based
steady solver, length unit metres. The script prints the material values it finds so you can confirm them.

Anything the settings API does not accept in your version can be applied as raw TUI text with --tui-extra FILE
(one TUI command per line; each is sent through (ti-menu-load-string ...)).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_fluent_sweep as sweep  # noqa: E402  (shares launch, reports and inlet helpers)

LOG = []


def step(name, fn):
    try:
        out = fn()
        LOG.append((name, "ok", ""))
        print(f"[ok]     {name}" + (f": {out}" if out else ""))
    except Exception as e:  # noqa: BLE001 - report every failure, keep going
        LOG.append((name, "FAILED", repr(e)))
        print(f"[FAILED] {name}: {e!r}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mesh", required=True, help="Fluent .msh from make_mesh.py")
    p.add_argument("--out", required=True, help="case file to write, e.g. f08_tu0.1.cas.h5")
    p.add_argument("--tu", type=float, default=0.1, help="inlet turbulence intensity in PERCENT (0.1 ~ Ncrit 8, 0.5 ~ Ncrit 4)")
    p.add_argument("--visc-ratio", type=float, default=5.0, help="inlet turbulent viscosity ratio")
    p.add_argument("--v0", type=float, default=4.12, help="initial inlet speed [m/s] (the sweep sets the real one per case)")
    p.add_argument("--np", type=int, default=4)
    p.add_argument("--gui", action="store_true")
    p.add_argument("--check-only", action="store_true", help="read the mesh, run the mesh check and exit")
    p.add_argument("--tui-extra", help="file of extra TUI commands to run after the settings above")
    a = p.parse_args()

    solver = sweep.launch(a.np, a.gui)
    s = solver.settings

    def read_mesh():
        try:
            s.file.read_mesh(file_name=str(a.mesh))
        except AttributeError:
            solver.file.read(file_type="mesh", file_name=str(a.mesh))

    step("read mesh", read_mesh)
    step("mesh check (look for negative volumes and the domain extents in the Fluent output)", lambda: solver.tui.mesh.check())
    if a.check_only:
        solver.exit()
        return

    step("viscous model = transition-sst", lambda: setattr(s.setup.models.viscous, "model", "transition-sst"))

    def inlet():
        bc = s.setup.boundary_conditions.velocity_inlet["inlet"]
        bc.momentum.velocity_specification_method = "Components"
        bc.momentum.velocity_components.set_state([a.v0, 0.0])
        bc.turbulence.turbulence_specification = "Intermittency, Intensity and Viscosity Ratio"   # Transition SST's option name (26.1)
        bc.turbulence.turbulent_intensity = a.tu / 100.0          # the API takes a fraction (check the printed state)
        bc.turbulence.turbulent_viscosity_ratio = a.visc_ratio
        return bc.get_state() if hasattr(bc, "get_state") else ""

    step("inlet: components, intensity, viscosity ratio", inlet)

    def materials():
        air = s.setup.materials.fluid["air"]
        return f"density {air.density.value if hasattr(air.density, 'value') else air.density}, viscosity {air.viscosity.value if hasattr(air.viscosity, 'value') else air.viscosity}"

    step("print air properties (expect 1.225 and 1.7894e-05)", materials)

    step("flow scheme = Coupled", lambda: setattr(s.solution.methods.p_v_coupling, "flow_scheme", "Coupled"))
    def discretisation(key, val):
        m = s.solution.methods
        ds = m.spatial_discretization.discretization_scheme if hasattr(m, "spatial_discretization") else m.discretization_scheme   # Fluent 24.2 keeps it directly under methods
        ds[key] = val

    for key, val in (("pressure", "second-order"), ("mom", "second-order-upwind"), ("k", "second-order-upwind"),
                     ("omega", "second-order-upwind"), ("intermit", "second-order-upwind"), ("retheta", "second-order-upwind")):
        step(f"discretisation {key} = {val}", lambda key=key, val=val: discretisation(key, val))

    step("report definitions fx, fy, mz (moment about the pivot)", lambda: sweep.ensure_reports(solver, "wall"))
    step("initialise", lambda: sweep.initialise(solver))

    if a.tui_extra:
        for line in Path(a.tui_extra).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith(";"):
                step(f"TUI: {line}", lambda line=line: solver.scheme_eval.scheme_eval(f'(ti-menu-load-string "{line}")'))

    def save():
        try:
            s.file.write_case(file_name=str(a.out))
        except AttributeError:
            solver.file.write(file_type="case", file_name=str(a.out))

    step(f"write case {a.out}", save)
    failed = [x for x in LOG if x[1] != "ok"]
    Path(a.out).with_suffix(".setup_log.txt").write_text("\n".join(f"{n}: {st} {msg}" for n, st, msg in LOG) + "\n")
    print(f"\n{len(LOG) - len(failed)} steps ok, {len(failed)} failed")
    for n, st, msg in failed:
        print(f"  FAILED: {n}: {msg}")
    solver.exit()


if __name__ == "__main__":
    main()
