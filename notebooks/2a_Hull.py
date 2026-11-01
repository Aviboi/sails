# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "ipython>=9.18.0",
#     "marimo>=0.23.3",
#     "matplotlib>=3.11.2",
#     "numpy>=2.5.4",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import math, os, csv
    import numpy as np
    import matplotlib.pyplot as plt
    from IPython.display import Markdown, display

    def table(rows, header):
        s = '| ' + ' | '.join(header) + ' |' + chr(10) + '|' + '---|' * len(header) + chr(10)  # Show a list of rows as a formatted table.
        s = s + chr(10).join(('| ' + ' | '.join((str(c) for c in r)) + ' |' for r in rows))
        display(Markdown(s))
    plt.rcParams.update({'figure.dpi': 110, 'axes.grid': True, 'grid.alpha': 0.3, 'font.size': 9})
    return csv, math, np, os, plt, table


@app.cell
def _():
    rho_w = 1025.0   # kg/m³ seawater  [L1]
    return (rho_w,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Hull hydrostatics and stability, from CAD

    **CUSail · Sails subsystem** · Part 3 of the PDR calculations, split out because it is self-contained. It needs only `data/hull_stations_from_CAD.csv` and the seawater density. `2_Calculations.py` runs this notebook and reuses `KM`, `T_canoe`, `freeboard`, `gz_curve`, `avs`, `ANGLES`, `STATIONS`, `XS` and `KEEL_Z`. Section and equation numbers (3.x, E1–E10) are kept so cross-references still work.

    **Source tags:** **[M]** measured from CAD · **[L#]** literature (references in `2_Calculations.py`, App. A). SI units; **x** runs aft from the bow plane, **y** outboard.

    ## 3.1 Where the hull data comes from
    The only hull geometry is `Transatlantic Hull Shell.SLDPRT` (Box/26-27, last saved 9/14; the Master Assembly contains only this part). It is lofted through 14 cross-section sketches. Each sketch has the same four pieces, so the ten numbers per station in `data/hull_stations_from_CAD.csv` describe it fully:

    1. a **flat deck** from the centreline out to the **sheer point**
    2. a straight **side line** from the sheer point to tangent point **T1** (slight tumblehome)
    3. a **bilge arc** from T1 to T2, with a given centre and radius (75 mm amidships)
    4. a **bottom arc** from T2 to the keel on the centreline

    The bottom arc is tangent to the bilge arc at T2. A tangent arc's centre lies on the line through the bilge centre and T2, and it also lies on the centreline (the section is symmetric). Those two conditions give:

    $$z_c = z_b + t\,(z_{T2}-z_b),\quad t=\frac{-y_b}{y_{T2}-y_b} \tag{E1}$$
    $$R_{bot} = \sqrt{y_{T2}^2 + (z_{T2}-z_c)^2} \tag{E2}$$

    **If the hull CAD changes, re-measure these ten numbers per station and Run All.**
    """)
    return


@app.cell
def _(csv, table):
    STATIONS = []
    with open('../data/hull_stations_from_CAD.csv') as _fh:
        for _row in csv.DictReader((line for line in _fh if not line.startswith('#'))):
            STATIONS.append({k: float(v) for k, v in _row.items()})
    table([[f"{s['x']:.2f}", f"({s['sheer_y']:.3f}, {s['sheer_z']:.3f})", f"({s['T1_y']:.3f}, {s['T1_z']:.3f})", f"({s['T2_y']:.3f}, {s['T2_z']:.3f})", f"({s['bilge_cy']:.3f}, {s['bilge_cz']:.3f}), r {s['bilge_r']:.3f}"] for s in STATIONS], ['x (m)', 'sheer (y, z)', 'T1 (y, z)', 'T2 (y, z)', 'bilge centre, radius'])
    return (STATIONS,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3.2 Rebuilding each section as a polygon
    Each section is drawn as a polygon: 20 points on the bottom arc, 20 on the bilge arc, the sheer point, then mirrored to port. Every section has the same number of points, so the stern face (x = 2.00 m, which has no sketch) can be extrapolated point-by-point from the last two stations.
    """)
    return


@app.cell
def _(STATIONS, math, np, plt):
    N_ARC = 20

    def half_section(s):
        yb, zb, rb = (s['bilge_cy'], s['bilge_cz'], s['bilge_r'])
        y2, z2 = (s['T2_y'], s['T2_z'])
        t = -yb / (y2 - yb)
        zc = zb + t * (z2 - zb)
        R = math.hypot(y2, z2 - zc)
        pts = [(0.0, zc - R)]
        a0, a1 = (-math.pi / 2, math.atan2(z2 - zc, y2))
        pts = pts + [(R * math.cos(a), zc + R * math.sin(a)) for a in np.linspace(a0, a1, N_ARC + 1)[1:]]
        b0, b1 = (math.atan2(z2 - zb, y2 - yb), math.atan2(s['T1_z'] - zb, s['T1_y'] - yb))
        pts = pts + [(yb + rb * math.cos(a), zb + rb * math.sin(a)) for a in np.linspace(b0, b1, N_ARC + 1)[1:]]
        pts.append((s['sheer_y'], s['sheer_z']))
        return np.array(pts)

    def full_section(s):
        h = half_section(s)
        port = h[::-1].copy()
        port[:, 0] = port[:, 0] * -1
        return np.vstack([h, port[:-1]])
    XS = np.array([s['x'] for s in STATIONS] + [2.0])
    POLYS = [full_section(s) for s in STATIONS]
    POLYS.append(2 * POLYS[-1] - POLYS[-2])
    KEEL_Z = {s['x']: half_section(s)[0, 1] for s in STATIONS}
    _fig, _ax = plt.subplots(1, 2, figsize=(11, 3.4), gridspec_kw=dict(width_ratios=[1.25, 1]))
    for x, P in zip(XS, POLYS):
        side = -1 if x <= 1.0 else 1
        _h = P[:len(P) // 2 + 1]
        _ax[0].plot(side * _h[:, 0], _h[:, 1], lw=0.9, c='C0' if side < 0 else 'C1')
    _ax[0].axhline(-0.0303, c='C2', ls='--', lw=1)
    _ax[0].text(-0.26, -0.045, '25 kg WL (3.3)', color='C2')
    _ax[0].set(aspect='equal', title='Body plan (left: x ≤ 1.00 m, right: aft)', xlabel='y (m)', ylabel='CAD z (m)')
    _s = STATIONS[8]
    _h = half_section(_s)
    _ax[1].plot(_h[:, 0], _h[:, 1], c='k')
    _ax[1].plot([0, _s['sheer_y']], [_s['sheer_z']] * 2, c='k')
    for _lab, (_y, z) in {'sheer': (_s['sheer_y'], _s['sheer_z']), 'T1': (_s['T1_y'], _s['T1_z']), 'T2': (_s['T2_y'], _s['T2_z']), 'bilge centre': (_s['bilge_cy'], _s['bilge_cz']), 'keel': tuple(_h[0])}.items():
        _ax[1].plot(_y, z, 'o', ms=4)
        _ax[1].annotate(_lab, (_y, z), textcoords='offset points', xytext=(5, 4))
    _ax[1].set(aspect='equal', title=f"Station x = {_s['x']:.2f} m: the four pieces", xlabel='y (m)')
    plt.tight_layout()
    plt.show()
    return KEEL_Z, POLYS, XS


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3.3 Upright hydrostatics
    Each section polygon is clipped at a trial waterline height $h$ (Sutherland–Hodgman half-plane clipping). Its immersed area and centroid come from the shoelace formulas:

    $$A = \tfrac12\sum_i (y_i z_{i+1} - y_{i+1} z_i) \tag{E3}$$
    $$\bar y = \frac{1}{6A}\sum_i (y_i+y_{i+1})(y_i z_{i+1}-y_{i+1}z_i),\quad \bar z \text{ likewise} \tag{E4}$$

    Integrating along x with the trapezoidal rule gives the standard hydrostatic quantities [L8]:

    $$\nabla = \int A_s\,dx, \qquad \Delta = \rho_w \nabla \tag{E5}$$
    $$LCB = \frac{\int x A_s\,dx}{\nabla}, \qquad KB = \frac{\int \bar z A_s\,dx}{\nabla} \tag{E6}$$
    $$BM = \frac{I_T}{\nabla}, \qquad I_T = \int \frac{B_{wl}^3}{12}\,dx \tag{E7}$$
    $$KM = KB + BM \tag{E8}$$

    $A_s$ is the immersed section area and $B_{wl}$ the waterline beam at each station. The waterline $h$ is found by bisection so that $\rho_w\nabla$ equals the displacement.
    """)
    return


@app.cell
def _(KEEL_Z, POLYS, STATIONS, XS, np, rho_w):
    def clip_below(P, h):
        # Part of polygon P (rows of y, z) that lies below the horizontal line z = h.
        out = []
        for p, q in zip(P, np.roll(P, -1, axis=0)):
            if p[1] <= h: out.append(p)
            if (p[1] <= h) != (q[1] <= h):
                out.append(p + (h - p[1]) / (q[1] - p[1]) * (q - p))
        return np.array(out)

    def area_centroid(P):
        # (E3), (E4): shoelace area and centroid (y, z) of a polygon.
        if len(P) < 3: return 0.0, 0.0, 0.0
        y, z = P[:, 0], P[:, 1]; y1, z1 = np.roll(y, -1), np.roll(z, -1)
        c = y*z1 - y1*z; A = c.sum() / 2
        if abs(A) < 1e-12: return 0.0, 0.0, 0.0
        return abs(A), ((y + y1)*c).sum() / (6*A), ((z + z1)*c).sum() / (6*A)

    def trapz(f, x):
        f, x = np.asarray(f, float), np.asarray(x, float)
        return float(np.sum((f[1:] + f[:-1])/2*np.diff(x)))

    def immersed(polys, h):
        # (E5), (E6): immersed volume and centre of buoyancy (x, y, z) for sections already rotated to the heel angle.
        a = np.array([area_centroid(clip_below(P, h)) for P in polys])   # columns: area, y-bar, z-bar
        V = trapz(a[:, 0], XS)
        if V == 0: return 0.0, 0.0, 0.0, 0.0
        return (V, trapz(a[:, 0]*XS, XS)/V, trapz(a[:, 0]*a[:, 1], XS)/V, trapz(a[:, 0]*a[:, 2], XS)/V)

    def find_waterline(polys, mass):
        # Bisection on the waterline height h so that rho_w * V = mass.
        lo = min(P[:, 1].min() for P in polys); hi = max(P[:, 1].max() for P in polys)
        for _ in range(50):
            h = (lo + hi) / 2
            lo, hi = (h, hi) if rho_w*immersed(polys, h)[0] < mass else (lo, h)
        return (lo + hi) / 2

    def waterline_beam(P, h):
        ys = [p[0] + (h - p[1])/(q[1] - p[1])*(q[0] - p[0]) for p, q in zip(P, np.roll(P, -1, axis=0))
              if (p[1] - h)*(q[1] - h) <= 0 and p[1] != q[1]]
        return max(ys) - min(ys) if ys else 0.0

    def upright(mass):
        h = find_waterline(POLYS, mass)
        V, LCB, _, zB = immersed(POLYS, h)
        Bwl = np.array([waterline_beam(P, h) for P in POLYS])
        BM  = trapz(Bwl**3/12, XS) / V                                   # (E7)
        return dict(WL_cad=h, V=V, LCB=LCB, KB=zB - h, BM=BM, KM=zB - h + BM,   # (E8)
                    Bwl=Bwl.max(), Awp=trapz(Bwl, XS), draft=h - min(KEEL_Z.values()), freeboard=STATIONS[8]["sheer_z"] - h)

    return find_waterline, immersed, upright


@app.cell
def _(KEEL_Z, STATIONS, table, upright):
    H25 = upright(25.0)
    WL_CAD, T_canoe, freeboard, KM = H25["WL_cad"], H25["draft"], H25["freeboard"], H25["KM"]
    table([["Waterline (CAD z)", f"{WL_CAD:+.4f} m", "sits on the bilge/bottom tangent line: likely the intended design WL"],
           ["Canoe-body draft", f"{T_canoe:.4f} m", "hull review lists 0.0774 m (≈ 27–28 kg)"],
           ["Freeboard, midbody (x 0.95–1.10)", f"{freeboard:.3f} m", "flat deck at CAD z 0.150"],
           ["LCB", f"{H25['LCB']:.3f} m from bow", "the keel bulb must sit near here for trim"],
           ["KB / BM / **KM** (above WL)", f"{H25['KB']:+.3f} / {H25['BM']:.3f} / **{KM:+.3f} m**", ""],
           ["WL beam / waterplane area", f"{H25['Bwl']:.3f} m / {H25['Awp']:.3f} m²", ""],
           ["Immersion", f"{(upright(26.0)['WL_cad'] - WL_CAD)*1000:.1f} mm per kg", ""]],
          ["At 25 kg", "Value", "Note"])
    print("Keel-to-deck depth by station (m):", ", ".join(f"{s['x']:.2f}: {s['sheer_z'] - KEEL_Z[s['x']]:.3f}" for s in STATIONS))
    print("Max half-beam by station (m):     ", ", ".join(f"{s['x']:.2f}: {s['T1_y']:.3f}" for s in STATIONS))
    return KM, T_canoe, WL_CAD, freeboard


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Findings used later:**
    - The hull is ~0.25 m deep everywhere aft of x ≈ 0.35 m, so depth does not constrain where the mast goes. What it does fix is the **bushing spacing** (5.2).
    - Forward of x ≈ 0.5 m the half-beam drops below ~0.18 m, too narrow to put a motor beside the mast (6.2).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3.4 Heeled stability: the righting-arm (GZ) curve
    The small-angle formula (E34) overstates the righting moment once the flat deck edge and the bilge start changing the waterplane. So the full curve is computed:

    1. Rotate every section polygon by the heel angle φ.
    2. Find the waterline that keeps the displaced volume constant (bisection, as in 3.3).
    3. Take the lateral centre of buoyancy $y_B(\phi)$ of the immersed shape.
    4. The centre of gravity G sits on the centreline at CAD height $z_G$. After rotation its lateral position is $y_G = -z_G\sin\phi$.
    5. The righting arm is the lateral distance from G to B, positive when B lies further toward the immersed side than G:

    $$GZ(\phi) = y_G - y_B = -z_G\sin\phi - y_B(\phi) \tag{E9}$$
    $$RM(\phi) = \Delta\,g\,GZ(\phi) \tag{E10}$$

    $y_B(\phi)$ depends only on the hull and the displacement, not on G. It is computed once on a grid of displacements (20–33 kg) and heel angles (0–180°), saved to `data/heeled_buoyancy_curves.csv`, and interpolated afterwards. The deck is treated as watertight, and keel and rudder buoyancy are ignored.

    The **angle of vanishing stability (AVS)** is the first angle where GZ crosses zero.
    """)
    return


@app.cell
def _(POLYS, WL_CAD, csv, find_waterline, immersed, math, np, os):
    ANGLES = np.arange(0, 181, 2.0)
    DISPS = np.arange(20.0, 33.01, 1.0)
    CACHE = '../data/heeled_buoyancy_curves.csv'

    def rotate(P, phi_deg):
        c, s = (math.cos(math.radians(phi_deg)), math.sin(math.radians(phi_deg)))
        return np.column_stack([P[:, 0] * c - P[:, 1] * s, P[:, 0] * s + P[:, 1] * c])

    def yB_curve(mass):
        return np.array([immersed(R, find_waterline(R, mass))[2] for R in ([rotate(P, phi) for P in POLYS] for phi in ANGLES)])  # Lateral centre of buoyancy vs heel angle, at constant displacement.
    if not os.path.exists(CACHE):
        print('Computing heeled buoyancy curves (about a minute)...')
        with open(CACHE, 'w', newline='') as _fh:
            w = csv.writer(_fh)
            w.writerow(['displacement_kg', 'heel_deg', 'yB_m'])
            for d in DISPS:
                for phi, _y in zip(ANGLES, yB_curve(d)):
                    w.writerow([d, phi, f'{_y:.6f}'])
    _c = np.loadtxt(CACHE, delimiter=',', skiprows=1)
    YB = _c[:, 2].reshape(len(DISPS), len(ANGLES))

    def yB_at(mass):
        i = int(np.clip(np.searchsorted(DISPS, mass) - 1, 0, len(DISPS) - 2))
        f = (mass - DISPS[i]) / (DISPS[i + 1] - DISPS[i])  # Linear interpolation of the y_B curve between the tabulated displacements.
        return YB[i] * (1 - f) + YB[i + 1] * f

    def gz_curve(mass, KG):
        zG_cad = WL_CAD + KG
        return -zG_cad * np.sin(np.radians(ANGLES)) - yB_at(mass)  # (E9). KG = CG height above the 25 kg WL.  Returns GZ (m) at each angle in ANGLES.

    def avs(gz):
        k = np.where((gz[:-1] > 0) & (gz[1:] <= 0))[0]
        return 180.0 if len(k) == 0 else float(ANGLES[k[0]] + 2 * gz[k[0]] / (gz[k[0]] - gz[k[0] + 1]))
    print('y_B at 25 kg, first few angles:', np.round(yB_at(25.0)[:6], 4))
    return ANGLES, avs, gz_curve


if __name__ == "__main__":
    app.run()
