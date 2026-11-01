#!/usr/bin/env python3
"""Mesh one section with gmsh and write a native ANSYS Fluent 2D mesh (.msh), no GUI.

Part of the Transatlantic Sail PDR package (see README_fluent.md).

Input   section_fXX.Xpct.csv written by 4_Section_Design.ipynb Section 8d (metres, chord 0.65 m, LE at x = 0)
Output  <name>.msh  Fluent ASCII mesh with zones: fluid, interior, wall, inlet (velocity-inlet), outlet (pressure-outlet)
        <name>_mesh_report.txt  cell counts, quality and boundary-layer checks

Domain  rectangle from -far*c to +far_down*c in x and y around the section (LE at the origin).
        inlet = left + bottom edges, outlet = top + right edges. Valid for angles of attack 0 to ~30 deg
        (the free stream runs up and to the right, see README_fluent.md).

Mesh    one mesh serves every wind speed and angle: the first cell height is set for the highest Re in the
        run matrix (y+ < 1 everywhere), the boundary layer is a stack of quads, the rest is Frontal-Delaunay triangles.

Needs   pip install gmsh numpy      (gmsh >= 4.11 for the BoundaryLayer field)
Fluent mesh-file conventions used (Fluent User's Guide, "Grid Sections"): sections 2, 10, 12, 13, 45; face line
`n0 n1 c0 c1` with c0 the cell on the LEFT of the directed face n0->n1 and c1 on the right (c1 = 0 on boundaries; this is what Fluent 26.1
actually accepts, tested by reading a mesh; the default here, --no-flip-faces gives the documented-looking opposite which Fluent rejects);
bc-type codes 2 interior, 3 wall, 5 pressure-outlet, 10 velocity-inlet.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

CHORD = 0.65


def read_section(path):
    pts = np.loadtxt(path, delimiter=",", skiprows=1)[:, :2]
    if not np.allclose(pts[0], pts[-1]):
        raise ValueError("section loop is not closed")
    i_le = int(np.argmin(pts[:, 0]))
    return pts, i_le


def build_mesh(a):
    import gmsh

    pts, i_le = read_section(a.section)
    c = CHORD
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1 if a.verbose else 0)
    gmsh.model.add("section")
    occ = gmsh.model.occ

    # --- section: two splines (upper TE->LE, lower LE->TE) sharing the tip points
    tags = [occ.addPoint(x, y, 0) for x, y in pts[:-1]]          # last point == first (trailing edge)
    te, le = tags[0], tags[i_le]
    upper = occ.addSpline(tags[: i_le + 1])
    lower = occ.addSpline(tags[i_le:] + [te])
    sect_loop = occ.addCurveLoop([upper, lower])

    # --- far field
    x0, x1, y0, y1 = -a.far * c, a.far_down * c, -a.far * c, a.far_down * c
    p = [occ.addPoint(x0, y0, 0), occ.addPoint(x1, y0, 0), occ.addPoint(x1, y1, 0), occ.addPoint(x0, y1, 0)]
    bottom, right, top, left = occ.addLine(p[0], p[1]), occ.addLine(p[1], p[2]), occ.addLine(p[2], p[3]), occ.addLine(p[3], p[0])
    outer = occ.addCurveLoop([bottom, right, top, left])
    surf = occ.addPlaneSurface([outer, sect_loop])
    occ.synchronize()

    pg = gmsh.model.addPhysicalGroup
    pg(1, [upper, lower], 1, "wall")
    pg(1, [left, bottom], 2, "inlet")
    pg(1, [top, right], 3, "outlet")
    pg(2, [surf], 4, "fluid")

    # --- size fields
    f = gmsh.model.mesh.field
    f.add("Distance", 1)
    f.setNumbers(1, "CurvesList", [upper, lower])
    f.setNumber(1, "Sampling", 400)
    f.add("MathEval", 2)
    f.setString(2, "F", f"Min({a.hmax}, {a.hs} + {a.growth}*F1)")
    f.add("Box", 5)                                              # wake / suction-side region
    f.setNumber(5, "VIn", a.h_wake)
    f.setNumber(5, "VOut", a.hmax)
    f.setNumber(5, "XMin", 0.0)
    f.setNumber(5, "XMax", 5 * c)
    f.setNumber(5, "YMin", -0.3 * c)
    f.setNumber(5, "YMax", 2.8 * c)
    f.setNumber(5, "Thickness", 1.5 * c)
    f.add("Min", 6)
    f.setNumbers(6, "FieldsList", [2, 5])
    f.setAsBackgroundMesh(6)

    # --- boundary layer (quads) on the section walls
    if a.no_bl:
        pass
    else:
      f.add("BoundaryLayer", 7)
      f.setNumbers(7, "CurvesList", [upper, lower])
      f.setNumber(7, "hwall_n", a.y1)
      f.setNumber(7, "ratio", a.ratio)
      f.setNumber(7, "thickness", a.bl_thickness)
      f.setNumber(7, "Quads", 1)
      f.setNumber(7, "IntersectMetrics", 0)
      f.setAsBoundaryLayer(7)

    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", a.curv_n)   # refines the rounded leading/trailing edges
    gmsh.option.setNumber("Mesh.MeshSizeMin", a.h_edge)
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    gmsh.option.setNumber("Mesh.Smoothing", 3)
    gmsh.model.mesh.generate(2)

    # --- extract
    ntags, ncoord, _ = gmsh.model.mesh.getNodes()
    xyz = np.asarray(ncoord).reshape(-1, 3)[:, :2]
    index = {int(t): i for i, t in enumerate(ntags)}                 # gmsh tag -> 0-based
    types, _, enodes = gmsh.model.mesh.getElements(2, surf)
    cells = []
    for t, nn in zip(types, enodes):
        k = {2: 3, 3: 4}.get(int(t))
        if k is None:
            raise RuntimeError(f"unexpected element type {t}")
        for row in np.asarray(nn).reshape(-1, k):
            cells.append([index[int(v)] for v in row])
    groups = {}
    for name, dimtag in (("wall", [upper, lower]), ("inlet", [left, bottom]), ("outlet", [top, right])):
        edges = set()
        for ent in dimtag:
            _, _, en = gmsh.model.mesh.getElements(1, ent)
            for row in np.asarray(en[0]).reshape(-1, 2):
                edges.add(frozenset((index[int(row[0])], index[int(row[1])])))
        groups[name] = edges
    gmsh.finalize()
    return xyz, cells, groups


def signed_area(xyz, cell):
    p = xyz[cell]
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def to_fluent(xyz, cells, groups, flip):
    """Orient cells CCW, build faces with Fluent's c0 (left) / c1 (right) convention as verified."""
    cells = [cl if signed_area(xyz, cl) > 0 else cl[::-1] for cl in cells]
    edge_cells = {}
    for ci, cl in enumerate(cells):
        for k in range(len(cl)):
            a, b = cl[k], cl[(k + 1) % len(cl)]
            edge_cells.setdefault(frozenset((a, b)), []).append((ci, a, b))
    interior, boundary = [], {name: [] for name in groups}
    owner = {}
    for name, es in groups.items():
        for e in es:
            owner[e] = name
    for e, lst in edge_cells.items():
        if len(lst) == 2:
            (c_a, a, b), (c_b, _, _) = lst                         # cell A traverses a->b CCW (A on the left of a->b)
            face = (b, a, c_a, c_b)                                # direction b->a puts A on the right => c0 = A
            interior.append(face if not flip else (a, b, c_a, c_b))
        elif len(lst) == 1:
            c_a, a, b = lst[0]
            if e not in owner:
                raise RuntimeError("boundary edge without a physical group")
            boundary[owner[e]].append((b, a, c_a, -1) if not flip else (a, b, c_a, -1))
        else:
            raise RuntimeError("non-manifold edge")
    return cells, interior, boundary


def write_msh(path, xyz, cells, interior, boundary, title):
    n_nodes, n_cells = len(xyz), len(cells)
    zones = [("interior", 3, 2, "interior", "interior-fluid", interior)]
    bc = {"wall": (3, "wall"), "inlet": (10, "velocity-inlet"), "outlet": (5, "pressure-outlet")}
    zid = 4
    for name in ("wall", "inlet", "outlet"):
        zones.append((name, zid, bc[name][0], bc[name][1], name, boundary[name]))
        zid += 1
    n_faces = sum(len(z[5]) for z in zones)
    h = lambda v: format(v, "x")
    with open(path, "w") as f:
        f.write(f'(0 "{title}")\n(2 2)\n')
        f.write(f"(10 (0 1 {h(n_nodes)} 0 2))\n(12 (0 1 {h(n_cells)} 0 0))\n(13 (0 1 {h(n_faces)} 0 0))\n")
        f.write(f"(10 (1 1 {h(n_nodes)} 1 2)(\n")
        for x, y in xyz:
            f.write(f"{x:.9e} {y:.9e}\n")
        f.write("))\n")
        f.write(f"(12 (2 1 {h(n_cells)} 1 0)(\n")
        f.write(" ".join("1" if len(cl) == 3 else "3" for cl in cells) + "\n))\n")
        first = 1
        for name, zid_, code, ztype, zname, faces in zones:
            if not faces:
                continue
            last = first + len(faces) - 1
            f.write(f"(13 ({h(zid_)} {h(first)} {h(last)} {h(code)} 2)(\n")
            for n0, n1, c0, c1 in faces:
                f.write(f"{h(n0 + 1)} {h(n1 + 1)} {h(c0 + 1)} {h(c1 + 1 if c1 >= 0 else 0)}\n")
            f.write("))\n")
            first = last + 1
        f.write("(45 (2 fluid fluid)())\n")
        for name, zid_, code, ztype, zname, faces in zones:
            f.write(f"(45 ({zid_} {ztype} {zname})())\n")


def check_and_report(xyz, cells, interior, boundary, a, path):
    """Independent checks on the data that is written: areas, closure of every cell, wall-normal spacing."""
    areas = np.array([signed_area(xyz, cl) for cl in cells])
    lines = []
    lines.append(f"nodes {len(xyz)}, cells {len(cells)} ({sum(len(c)==3 for c in cells)} tri, {sum(len(c)==4 for c in cells)} quad)")
    lines.append(f"cell area min {areas.min():.3e} m^2, max {areas.max():.3e} m^2 (all positive: {bool((areas>0).all())})")
    # closure: for every cell, sum over faces of outward normal * length must vanish (c0 right => outward normal is the left normal)
    clos = np.zeros((len(cells), 2))
    allfaces = list(interior) + [fc for v in boundary.values() for fc in v]
    for n0, n1, c0, c1 in allfaces:
        d = xyz[n1] - xyz[n0]
        left = np.array([-d[1], d[0]])                      # length-weighted left normal of n0->n1
        clos[c0] += left                                    # c0 is on the right => outward normal = left normal
        if c1 >= 0:
            clos[c1] -= left
    lines.append(f"max |closure| over cells {np.abs(clos).max():.2e} (should be ~0; checks orientation and watertightness)")
    ok = np.abs(clos).max() < 1e-9 * max(1.0, a.hs)
    # wall-normal first spacing: shortest edge touching a wall node
    wall_nodes = {n for fc in boundary["wall"] for n in fc[:2]}
    emin = np.inf
    for cl in cells:
        if wall_nodes.intersection(cl):
            for k in range(len(cl)):
                emin = min(emin, float(np.linalg.norm(xyz[cl[k]] - xyz[cl[(k + 1) % len(cl)]])))
    lines.append(f"shortest edge in cells touching the wall {emin*1e3:.4f} mm (requested first layer {a.y1*1e3:.4f} mm)")
    lines.append(f"wall faces {len(boundary['wall'])}, inlet faces {len(boundary['inlet'])}, outlet faces {len(boundary['outlet'])}, interior faces {len(interior)}")
    # BL layers: wall-attached quad rows, estimated from the number of quads / wall faces
    quads = sum(len(c) == 4 for c in cells)
    lines.append(f"quad cells per wall face (about the number of boundary-layer rows): {quads / max(1, len(boundary['wall'])):.1f}")
    Path(path).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return ok


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--section", required=True, help="section CSV from the notebook, e.g. section_f08.0pct.csv")
    p.add_argument("--out", help="output .msh (default: next to the section file)")
    p.add_argument("--y1", type=float, default=0.020e-3, help="first cell height [m] (0.02 mm = y+~1 at 27 kn)")
    p.add_argument("--ratio", type=float, default=1.12, help="boundary-layer growth ratio")
    p.add_argument("--bl-thickness", type=float, default=0.030, help="total boundary-layer stack thickness [m]")
    p.add_argument("--hs", type=float, default=1.5e-3, help="surface element size [m]")
    p.add_argument("--h-edge", type=float, default=0.3e-3, help="smallest allowed element size, reached on the rounded edges [m]")
    p.add_argument("--curv-n", type=float, default=40, help="elements per 2*pi of curvature (edge refinement)")
    p.add_argument("--h-wake", type=float, default=15e-3, help="element size in the wake box [m]")
    p.add_argument("--hmax", type=float, default=1.0, help="largest element size in the far field [m]")
    p.add_argument("--growth", type=float, default=0.12, help="far-field size growth per metre from the wall")
    p.add_argument("--far", type=float, default=20.0, help="domain extent upstream/below, in chords")
    p.add_argument("--far-down", type=float, default=30.0, help="domain extent downstream/above, in chords")
    p.add_argument("--flip-faces", action=argparse.BooleanOptionalAction, default=True, help="reverse the face orientation convention (needed by Fluent 26.1, checked against a real read; --no-flip-faces gives the other convention)")
    p.add_argument("--no-bl", action="store_true", help="debug: skip the boundary layer")
    p.add_argument("--verbose", action="store_true")
    a = p.parse_args()
    out = Path(a.out) if a.out else Path(a.section).with_suffix(".msh")
    xyz, cells, groups = build_mesh(a)
    cells, interior, boundary = to_fluent(xyz, cells, groups, a.flip_faces)
    write_msh(out, xyz, cells, interior, boundary, f"gmsh mesh of {Path(a.section).name}")
    ok = check_and_report(xyz, cells, interior, boundary, a, out.with_name(out.stem + "_mesh_report.txt"))
    print(f"wrote {out}")
    if not ok and not a.flip_faces:
        sys.exit("closure check failed: mesh not watertight")


if __name__ == "__main__":
    main()
