#!/usr/bin/env python3
"""PyFluent sweep over angle of attack for one pre-built 2D section case.

Part of the Transatlantic Sail PDR package (see 4_Section_Design.ipynb, Section 8d).

What it does
  Reads run_matrix.csv (written by the notebook), selects the rows for one camber / wind case,
  and for each angle: sets the inlet velocity components, (re)initialises, iterates until the
  forces stop changing, reads Fx, Fy and the pivot moment Mz, converts them to CL, CD, Cm
  (equations below) and appends a row to a results CSV. Finished cases are skipped on restart.

What it does NOT do (do these once in the Fluent GUI and save the case; see README_fluent.md)
  Materials, Transition SST, discretisation, boundary-condition zones, turbulence intensity.
  Use one saved case per camber and per turbulence intensity.

Conventions (match the notebook)
  Chord c = 0.65 m, unit depth, pivot at (0.325, 0) m, nose-up moment positive.
  Free stream direction (cos a, sin a); a is the angle of attack.
  L = -Fx sin a + Fy cos a      D = Fx cos a + Fy sin a
  CL = L/(q c)   CD = D/(q c)   Cm = Mz/(q c^2)   q = 0.5 rho V^2

STATUS: the Fluent calls below were checked by name against the PyFluent 0.43 generated settings API for Fluent
24.2, 25.1, 25.2 and 26.1 (verify_api.py), but this script has NOT been run against a Fluent installation. Run one case with --max-cases 1 and check
the printed raw report output first. Names and return formats change between PyFluent/Fluent versions.
The matrix handling, the force rotation and the CSV logic are tested (--selftest, --dry-run).
"""
import argparse
import csv
import math
import sys
import time
from pathlib import Path

RHO = 1.225           # kg/m^3, must match the case file
CHORD = 0.65          # m
PIVOT = (0.325, 0.0)  # m


# ---------------------------------------------------------------- pure-Python helpers (no Fluent needed)
def rotate_forces(fx, fy, alpha_deg):
    """Global (Fx, Fy) -> (lift, drag) for free-stream direction (cos a, sin a)."""
    a = math.radians(alpha_deg)
    return -fx * math.sin(a) + fy * math.cos(a), fx * math.cos(a) + fy * math.sin(a)


def coefficients(fx, fy, mz, alpha_deg, v):
    q = 0.5 * RHO * v * v
    lift, drag = rotate_forces(fx, fy, alpha_deg)
    return lift / (q * CHORD), drag / (q * CHORD), mz / (q * CHORD * CHORD)


def load_cases(matrix_path, camber, wind, priority, alphas):
    rows = []
    with open(matrix_path, newline="") as f:
        for r in csv.DictReader(f):
            if camber is not None and abs(float(r["camber_pct"]) - camber) > 1e-6:
                continue
            if wind is not None and r["wind"] != wind:
                continue
            if priority is not None and int(r["priority"]) > priority:
                continue
            if alphas is not None and float(r["alpha_deg"]) not in alphas:
                continue
            rows.append(r)
    rows.sort(key=lambda r: (r["wind"], float(r["alpha_deg"])))
    return rows


def done_keys(out_path, tag):
    keys = set()
    if Path(out_path).exists():
        with open(out_path, newline="") as f:
            for r in csv.DictReader(f):
                if r["tag"] == tag:
                    keys.add((r["camber_pct"], r["wind"], r["alpha_deg"]))
    return keys


def find_numbers(obj, out=None):
    """Collect every float in a nested list/dict/tuple, in order (the compute() return format varies by version)."""
    out = [] if out is None else out
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            find_numbers(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            find_numbers(v, out)
    return out


def extract_report_values(raw, names):
    """Return {name: value}. Uses dict keys if present, otherwise the order of `names`."""
    found = {}
    if isinstance(raw, dict):
        for n in names:
            for k, v in raw.items():
                if n in str(k):
                    nums = find_numbers(v)
                    if nums:
                        found[n] = nums[0]
    if len(found) == len(names):
        return found
    nums = find_numbers(raw)
    if len(nums) >= len(names):
        return dict(zip(names, nums[: len(names)]))
    raise RuntimeError(f"Could not read {names} from report output: {raw!r}")


def selftest():
    for a in (0, 6, 12, 30):
        lift, drag = 1.3, 0.2
        ar = math.radians(a)
        fx = drag * math.cos(ar) - lift * math.sin(ar)
        fy = lift * math.cos(ar) + drag * math.sin(ar)
        l2, d2 = rotate_forces(fx, fy, a)
        assert abs(l2 - lift) < 1e-12 and abs(d2 - drag) < 1e-12, (a, l2, d2)
    cl, cd, cm = coefficients(0.0, 10.0, 2.0, 0.0, 4.12)
    q = 0.5 * RHO * 4.12 ** 2
    assert abs(cl - 10.0 / (q * CHORD)) < 1e-12 and abs(cm - 2.0 / (q * CHORD ** 2)) < 1e-12
    assert extract_report_values({"fx": [1.0, "N"], "fy": [2.0], "mz": [3.0]}, ["fx", "fy", "mz"]) == {"fx": 1.0, "fy": 2.0, "mz": 3.0}
    assert extract_report_values([{"a": 1}, 2, [3]], ["fx", "fy", "mz"]) == {"fx": 1.0, "fy": 2.0, "mz": 3.0}
    print("selftest OK")


# ---------------------------------------------------------------- Fluent calls (verify against your version)
def launch(np_, show_gui):
    import ansys.fluent.core as pyfluent
    return pyfluent.launch_fluent(
        mode="solver",
        dimension=pyfluent.Dimension.TWO,
        precision="double",
        processor_count=np_,
        ui_mode="gui" if show_gui else "no_gui",
    )


def read_case(solver, case):
    try:
        solver.settings.file.read_case(file_name=str(case))
    except AttributeError:                       # older PyFluent
        solver.file.read(file_type="case", file_name=str(case))


def ensure_reports(solver, wall_zone):
    """Create Fx, Fy and the pivot moment report definitions if the case does not have them."""
    rd = solver.settings.solution.report_definitions
    if "fx" not in rd.force.get_object_names():
        rd.force["fx"] = {"zones": [wall_zone], "force_vector": [1, 0, 0]}
    if "fy" not in rd.force.get_object_names():
        rd.force["fy"] = {"zones": [wall_zone], "force_vector": [0, 1, 0]}
    if "mz" not in rd.moment.get_object_names():
        rd.moment["mz"] = {"zones": [wall_zone], "mom_center": [PIVOT[0], PIVOT[1], 0], "mom_axis": [0, 0, 1]}


def set_inlet(solver, inlet_zone, vx, vy):
    bc = solver.settings.setup.boundary_conditions.velocity_inlet[inlet_zone]
    bc.momentum.velocity_specification_method = "Components"
    bc.momentum.velocity_components.set_state([vx, vy])   # a list object in the settings API; 2D takes two entries


def initialise(solver):
    try:
        solver.settings.solution.initialization.hybrid_initialize()
    except AttributeError:
        solver.settings.solution.initialization.initialize()


def read_forces(solver, first_print=[True]):
    rd = solver.settings.solution.report_definitions
    raw = rd.compute(report_defs=["fx", "fy", "mz"])
    if first_print[0]:
        print("RAW compute() output (check the parsing against this):", raw)
        first_print[0] = False
    v = extract_report_values(raw, ["fx", "fy", "mz"])
    return v["fx"], v["fy"], v["mz"]


def converge(solver, alpha, v, chunk, max_chunks, tol):
    """Iterate in chunks until CL and Cm change by less than tol between chunks."""
    prev, total = None, 0
    for _ in range(max_chunks):
        solver.settings.solution.run_calculation.iterate(iter_count=chunk)
        total += chunk
        fx, fy, mz = read_forces(solver)
        cl, cd, cm = coefficients(fx, fy, mz, alpha, v)
        print(f"  alpha {alpha:5.1f}  it {total:5d}  CL {cl:7.3f}  CD {cd:7.4f}  Cm {cm:7.3f}", flush=True)
        if prev is not None and abs(cl - prev[0]) < tol and abs(cm - prev[2]) < tol:
            return fx, fy, mz, total, True
        prev = (cl, cd, cm)
    return fx, fy, mz, total, False


# ---------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--matrix", default="run_matrix.csv")
    p.add_argument("--case", help="saved Fluent case (.cas.h5) for ONE camber and ONE turbulence intensity")
    p.add_argument("--camber", type=float, help="camber percent to run, e.g. 8.0")
    p.add_argument("--wind", help='wind label from the matrix: "4 kn", "8 kn" or "27 kn"')
    p.add_argument("--priority", type=int, default=None, help="1 = priority-1 cases only; 2 = all")
    p.add_argument("--alphas", help="comma list of angles, e.g. 0,4,8")
    p.add_argument("--tag", default="tu0.1", help="label stored with each result (e.g. the turbulence intensity)")
    p.add_argument("--out", default="results.csv")
    p.add_argument("--inlet", default="inlet")
    p.add_argument("--wall", default="wall")
    p.add_argument("--np", type=int, default=4, help="processors")
    p.add_argument("--chunk", type=int, default=200, help="iterations between convergence checks")
    p.add_argument("--max-chunks", type=int, default=10)
    p.add_argument("--tol", type=float, default=2e-3, help="max change in CL and Cm between chunks")
    p.add_argument("--reinit", action="store_true", help="re-initialise for every angle (default: continue from the previous angle)")
    p.add_argument("--max-cases", type=int, default=None)
    p.add_argument("--gui", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="list the cases and inlet components, do not start Fluent")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        selftest()
        return
    alphas = {float(x) for x in a.alphas.split(",")} if a.alphas else None
    cases = load_cases(a.matrix, a.camber, a.wind, a.priority, alphas)
    done = done_keys(a.out, a.tag)
    todo = [r for r in cases if (r["camber_pct"], r["wind"], r["alpha_deg"]) not in done]
    if a.max_cases:
        todo = todo[: a.max_cases]
    print(f"{len(cases)} matching cases, {len(cases) - len(todo)} already done, {len(todo)} to run")
    if a.dry_run or not todo:
        for r in todo:
            print(f"  camber {r['camber_pct']} %, {r['wind']}, alpha {r['alpha_deg']} deg: V = {r['V_mps']} m/s, "
                  f"components ({float(r['V_mps']) * float(r['flow_x']):.4f}, {float(r['V_mps']) * float(r['flow_y']):.4f}), first cell {float(r['y1_m']) * 1e3:.3f} mm")
        return
    if not a.case:
        sys.exit("--case is required unless --dry-run")

    solver = launch(a.np, a.gui)
    read_case(solver, a.case)
    ensure_reports(solver, a.wall)

    new_file = not Path(a.out).exists()
    cols = ["tag", "camber_pct", "wind", "Re", "alpha_deg", "V_mps", "Fx_N", "Fy_N", "Mz_Nm", "CL", "CD", "Cm_pivot", "iterations", "converged", "seconds"]
    with open(a.out, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        if new_file:
            w.writeheader()
        last_wind = None
        for r in todo:
            v, alpha = float(r["V_mps"]), float(r["alpha_deg"])
            t0 = time.time()
            set_inlet(solver, a.inlet, v * float(r["flow_x"]), v * float(r["flow_y"]))
            if a.reinit or r["wind"] != last_wind:
                initialise(solver)
            last_wind = r["wind"]
            fx, fy, mz, iters, ok = converge(solver, alpha, v, a.chunk, a.max_chunks, a.tol)
            cl, cd, cm = coefficients(fx, fy, mz, alpha, v)
            w.writerow(dict(tag=a.tag, camber_pct=r["camber_pct"], wind=r["wind"], Re=r["Re"], alpha_deg=r["alpha_deg"], V_mps=r["V_mps"],
                            Fx_N=fx, Fy_N=fy, Mz_Nm=mz, CL=cl, CD=cd, Cm_pivot=cm, iterations=iters, converged=ok, seconds=round(time.time() - t0, 1)))
            fh.flush()
            print(f"alpha {alpha:5.1f}  CL {cl:7.3f}  CD {cd:7.4f}  Cm_pivot {cm:7.3f}  {'converged' if ok else 'NOT converged'} ({iters} it)")
    solver.exit()


if __name__ == "__main__":
    main()
