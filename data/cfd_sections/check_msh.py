#!/usr/bin/env python3
"""Independent check of a 2D Fluent ASCII mesh (.msh): reads the file back and tests it.

Checks: zones and counts; c0 lies on the LEFT and c1 on the RIGHT of every directed face n0->n1 (the convention Fluent 26.1 accepted; the opposite gave negative volumes);
every cell closes (sum of outward face vectors = 0); all cell areas are positive; minimum interior angle.
Usage: python check_msh.py mesh.msh
"""
import re
import sys

import numpy as np


def parse(path):
    text = open(path).read()
    nodes = None
    cells_decl = None
    faces = []          # (zone, bc, n0, n1, c0, c1)
    zones = {}
    for m in re.finditer(r"\(45 \((\d+) (\S+) (\S+)\)\(\)\)", text):
        zones[int(m.group(1))] = (m.group(2), m.group(3))
    m = re.search(r"\(10 \(1 1 ([0-9a-f]+) 1 2\)\(\n(.*?)\)\)\n", text, re.S)
    n_nodes = int(m.group(1), 16)
    nodes = np.array([[float(v) for v in ln.split()] for ln in m.group(2).strip().splitlines()])
    assert len(nodes) == n_nodes
    m = re.search(r"\(12 \(2 1 ([0-9a-f]+) 1 0\)\(\n(.*?)\)\)\n", text, re.S)
    n_cells = int(m.group(1), 16)
    ctype = np.array(m.group(2).split(), dtype=int)
    assert len(ctype) == n_cells
    for m in re.finditer(r"\(13 \(([0-9a-f]+) ([0-9a-f]+) ([0-9a-f]+) ([0-9a-f]+) 2\)\(\n(.*?)\)\)\n", text, re.S):
        z, first, last, bc = (int(m.group(i), 16) for i in range(1, 5))
        rows = [[int(v, 16) for v in ln.split()] for ln in m.group(5).strip().splitlines()]
        assert len(rows) == last - first + 1, "face count mismatch in zone %d" % z
        for r in rows:
            faces.append((z, bc, r[0] - 1, r[1] - 1, r[2] - 1, r[3] - 1))
    return nodes, ctype, faces, zones


def main(path):
    xyz, ctype, faces, zones = parse(path)
    n_cells = len(ctype)
    cell_nodes = [set() for _ in range(n_cells)]
    for z, bc, a, b, c0, c1 in faces:
        cell_nodes[c0].update((a, b))
        if c1 >= 0:
            cell_nodes[c1].update((a, b))
    cen = np.array([xyz[list(s)].mean(axis=0) for s in cell_nodes])
    clos = np.zeros((n_cells, 2))
    bad_right = bad_left = 0
    for z, bc, a, b, c0, c1 in faces:
        d = xyz[b] - xyz[a]
        cross0 = d[0] * (cen[c0][1] - xyz[a][1]) - d[1] * (cen[c0][0] - xyz[a][0])
        if cross0 <= 0:
            bad_right += 1                                  # c0 must be on the left (positive cross product)
        left = np.array([-d[1], d[0]])
        clos[c0] += left
        if c1 >= 0:
            cross1 = d[0] * (cen[c1][1] - xyz[a][1]) - d[1] * (cen[c1][0] - xyz[a][0])
            if cross1 >= 0:
                bad_left += 1
            clos[c1] -= left
    # areas and angles from the node sets (order nodes around the centroid)
    areas, min_ang = [], 180.0
    for s, cn in zip(cell_nodes, cen):
        idx = list(s)
        ang = np.arctan2(xyz[idx][:, 1] - cn[1], xyz[idx][:, 0] - cn[0])
        p = xyz[idx][np.argsort(ang)]
        x, y = p[:, 0], p[:, 1]
        areas.append(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
        for k in range(len(p)):
            u, v = p[k - 1] - p[k], p[(k + 1) % len(p)] - p[k]
            cosang = np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v))
            min_ang = min(min_ang, np.degrees(np.arccos(np.clip(cosang, -1, 1))))
    areas = np.array(areas)
    print(f"{path}: nodes {len(xyz)}, cells {n_cells} ({(ctype == 1).sum()} tri, {(ctype == 3).sum()} quad), faces {len(faces)}")
    for zid, (zt, zn) in sorted(zones.items()):
        n = sum(1 for f in faces if f[0] == zid)
        print(f"  zone {zid}: {zt} '{zn}'" + (f", {n} faces" if n else ""))
    print(f"c0 not on the left of n0->n1: {bad_right} faces;  c1 not on the right: {bad_left} faces  (both should be 0)")
    print(f"max |cell closure| {np.abs(clos).max():.2e}  (should be ~0)")
    print(f"cell area min {areas.min():.3e}, max {areas.max():.3e}; any non-positive: {bool((areas <= 0).any())}")
    print(f"minimum interior angle {min_ang:.1f} deg")
    ok = bad_right == 0 and bad_left == 0 and np.abs(clos).max() < 1e-9 and not (areas <= 0).any()
    print("RESULT:", "OK" if ok else "PROBLEM")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
