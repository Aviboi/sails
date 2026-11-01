import marimo

__generated_with = "0.25.0"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Transatlantic Sail: Design History (v0 → v5)

    **CUSail · Sails subsystem · Avram Dreyer · 26 Sep 2026**

    This notebook records the **earlier estimates** that led to the current baseline (v5), in the order they were made. The baseline itself, and the trade studies that justify it, are in `2_Calculations.py`. The reasoning behind each change is in `1_Design_Decisions.md`.

    To keep the method identical, the first cell runs `2_Calculations.py` quietly. That loads all its inputs, equations (E#) and functions; the only new thing here is which configurations are evaluated. Running this notebook therefore takes about as long as the main one.

    | Ver. | Change | Section |
    |---|---|---|
    | v0 | First area estimate, NACA 0015 foil, 0.90 m² | H1 |
    | v1 | Hull measured from CAD (see `2_Calculations.py` Part 3) | — |
    | v2 | Section switched to the cambered plate (D6), still 0.90 m² | H2 |
    | v3 | Span cut to 1.00 × 0.75 m (4:3) | H3 |
    | v4 | Mast moved from 1.20 m to 1.00 m from the bow (D7) | H4 |
    | — | Trade sweep run on the v3/v4 sail | H5 |
    | v5 | 0.95 × 0.65 m (D8) | H6 |
    | v5.1 | Sail mass re-estimated from the construction design (D10): the current baseline, in `2_Calculations.py` | H6 |
    """)
    return


@app.cell
def _():
    import importlib
    import matplotlib.pyplot as plt

    # Run the main notebook headlessly and reuse its definitions (replaces the old `%run`).
    _main = importlib.import_module("2_Calculations")
    _, _defs = _main.app.run()
    plt.close("all")
    B, BASE, FOIL, PLATE = _defs["B"], _defs["BASE"], _defs["FOIL"], _defs["PLATE"]
    M_rud, helm_sweep, margins = _defs["M_rud"], _defs["helm_sweep"], _defs["margins"]
    rho_w, size_rig, table = _defs["rho_w"], _defs["size_rig"], _defs["table"]
    print(f"Loaded main notebook: baseline {BASE['span']} × {BASE['chord']} m, hold {B['T_hold']:.0f} N·m")
    return B, BASE, FOIL, M_rud, PLATE, helm_sweep, margins, rho_w, size_rig, table


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## H0. The mass model used through v5
    Until v5 the sail mass was an **allowance**, not a construction estimate:
    - **Plate:** 0.6 kg/m² per face, plus 15 % of that for ribs, spine and bonds, plus a 10 mm, 60 kg/m³ core.
    - **Foil:** the same skin weight over 2.04 × chord, plus 25 % for ribs.

    $$m_{sail,plate} = 0.6\cdot 2(1.02A)(1.15) + 60\cdot 0.010\,A, \qquad m_{sail,foil} = 0.6\cdot 2.04\,c\,s\,(1.25)$$

    v5.1 replaced it with the itemised construction estimate (main notebook 5.3). To reproduce the numbers as they were at the time, v0–v5 below use the allowance.
    """)
    return


@app.cell
def _(B, PLATE):
    def sail_mass_allowance(span, chord, sec):
        A = span*chord
        return 0.60*2*1.02*A*1.15 + 60*0.010*A if "camber" in sec else 0.60*2.04*chord*span*1.25
    ALLOW = sail_mass_allowance
    print(f"Allowance at 0.95 × 0.65 m: {ALLOW(0.95, 0.65, PLATE):.2f} kg;  itemised construction estimate (v5.1): {B['m_sail']:.2f} kg")
    return (ALLOW,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## H1. v0: first area estimate (foil)
    With no transatlantic calculations yet, the keel team needed a sail area. It was scaled from the CUSail comp boat's sail-area/displacement ratio (SA/D ≈ 17.7, E22), reduced to 10–14 for an ocean boat that must survive rather than race: $A = SA/D\cdot\nabla^{2/3}$ with $\nabla = 25/1025$ m³.
    """)
    return


@app.cell
def _(rho_w):
    Vol = 25/rho_w
    print(f"∇^(2/3) = {Vol**(2/3):.4f} m²;  SA/D 10 → {10*Vol**(2/3):.2f} m², 14 → {14*Vol**(2/3):.2f} m²  (placeholder given to Luis: 0.85–1.2 m²)")
    print("v0 picked 0.90 m² = 1.20 m span × 0.75 m chord, NACA 0015 foil.")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## H2. v2: plate vs foil at 1.20 × 0.75 m (D6)
    Once the hull was measured (v1), the first full sizing ran for both sections at the v0 planform. This comparison led to D6. The plate needs a much stronger drive and has no passive feathering. In exchange it is far simpler to build, has nothing aloft that can flood, gives more light-air lift, and has a smaller sweep circle.
    """)
    return


@app.cell
def _(ALLOW, FOIL, PLATE, size_rig, table):
    v2p, v2f = size_rig(1.20, 0.75, PLATE, build=ALLOW), size_rig(1.20, 0.75, FOIL, build=ALLOW)
    table([["Sweep circle", f"Ø {2*v2p['R_sweep']:.2f} m", f"Ø {2*v2f['R_sweep']:.2f} m"],
           ["Rig mass @ CG", f"{v2p['m_rig']:.2f} kg @ {v2p['z_rig']:+.2f}", f"{v2f['m_rig']:.2f} kg @ {v2f['z_rig']:+.2f}"],
           ["Sealed volume aloft", "0 L", f"{0.685*FOIL['t_c']*0.75**2*1.20*1000:.0f} L"],
           ["Full power until (GZ)", f"{v2p['V_fp']:.1f} kn", f"{v2f['V_fp']:.1f} kn"],
           ["Operating torque", f"{v2p['T_op']:.0f} N·m", f"{v2f['T_op']:.0f} N·m"],
           ["Survival", f"hold {v2p['T_hold']:.0f} N·m, static {v2p['T_static']:.0f}", f"clutch slips {v2f['T_hold']:.0f} N·m, static {v2f['T_static']:.0f}"],
           ["Mast moment lim / ult", f"{v2p['M_lim']:.0f} / {v2p['M_ult']:.0f} N·m", f"{v2f['M_lim']:.0f} / {v2f['M_ult']:.0f} N·m"]],
          ["v2 size 1.20 × 0.75 m (0.90 m²)", "Plate", "Foil"])
    return (v2p,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## H3. v3: planform to 4:3 (1.00 × 0.75 m)
    At 1.20 × 0.75 m the plate's hold of ~105 N·m (static ~158) was far beyond any small worm gearbox. The span was cut to a 4:3 planform, keeping the aspect ratio in the 1:1–3:2 range the team preferred. The mast stayed at ~1.20 m from the bow.
    """)
    return


@app.cell
def _(ALLOW, PLATE, size_rig):
    v3 = size_rig(1.00, 0.75, PLATE, build=ALLOW)
    print(f"v3 1.00 × 0.75 m: A {v3['A']:.2f} m², hold {v3['T_hold']:.0f} N·m, static {v3['T_static']:.0f} N·m, "
          f"M_deck {v3['M_lim']:.0f}/{v3['M_ult']:.0f} N·m, rig {v3['m_rig']:.2f} kg, full power to {v3['V_fp']:.1f} kn, AVS {v3['AVS']:.0f}°")
    return (v3,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## H4. v4: mast moved from 1.20 m to 1.00 m (D7)
    The balance model (main notebook 5.11) was first run on the v3 sail. It showed the 1.20 m position was unstable downwind (running CE aft of the CLR), which led to the move to 1.00 m. The same study for the final sail is in main notebook 6.2.
    """)
    return


@app.cell
def _(M_rud, PLATE, helm_sweep, table):
    rows = []
    for mx in (0.80, 0.90, 1.00, 1.10, 1.20, 1.30):
        s = helm_sweep(mx, 1.00, 0.75, PLATE)
        lee = max(0.0, -s[s[:, 0] >= 40, 2].min()); run = s[-1, 1]
        rows.append([f"{mx:.2f}", f"{s[s[:,0]==45,1][0]*1000:+.0f}", f"{run*1000:+.0f} " + ("tracks" if run < 0 else "**unstable**"), f"{lee:.1f} ({lee/M_rud*100:.0f} %)"])
    table(rows, ["Mast x (m), v3/v4 sail", "CE − CLR at 45° AWA (mm)", "CE − CLR running (mm)", "Max lee helm, N·m (% of rudder)"])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## H5. Trade sweep on the v3/v4 sail
    The sweep (main notebook 6.3) was first run to find out why v3/v4 was still hard to fit. The v3/v4 sail was marginal on three constraints at once, which is what led to v5:
    """)
    return


@app.cell
def _(ALLOW, PLATE, margins, size_rig):
    v4 = size_rig(1.00, 0.75, PLATE, build=ALLOW)
    print("v3/v4 sail (1.00 × 0.75, 7 kg @ 0.28), margins (E59): " + ", ".join(f"{k} {m:.2f}" for k, m in margins(v4).items()))
    return (v4,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## H6. Version summary
    """)
    return


@app.cell
def _(ALLOW, B, FOIL, PLATE, size_rig, table, v2p, v3, v4):
    v0f = size_rig(1.20, 0.75, FOIL, build=ALLOW); v5a = size_rig(0.95, 0.65, PLATE, build=ALLOW)
    vers = [("v0", "foil 1.20×0.75, mast ~1.2", v0f), ("v2", "plate 1.20×0.75, mast 1.20–1.25", v2p), ("v3", "plate 1.00×0.75, mast 1.20", v3),
            ("v4", "plate 1.00×0.75, mast 1.00", v4), ("v5", "plate 0.95×0.65, mast 1.00 (allowance mass)", v5a),
            ("v5.1 (baseline)", "as v5, itemised sail construction (D10)", B)]
    table([[n, d, f"{r['A']:.2f}", f"{r['T_hold']:.0f} / {r['T_static']:.0f}", f"{r['M_lim']:.0f} / {r['M_ult']:.0f}", f"{r['R_deck']:.0f}",
            f"{r['m_rig']:.2f} @ {r['z_rig']:+.2f}", f"{r['V_fp']:.1f}"] for n, d, r in vers],
          ["Ver.", "Configuration", "A (m²)", "Hold / static (N·m)", "M_deck lim / ult (N·m)", "R_deck (N)", "Rig kg @ m", "Full power to (kn)"])
    print("v0 foil: 'hold' = clutch slip torque. v1 was the hull measurement only. v0–v5 use the H0 allowance mass.")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Corrections made when the calculations were consolidated (26 Sep)
    - **Ballast ratio:** full power to 12 kn needs ~24 % of 23.2 kg, not ~22 %.
    - **Slewing power:** at 180° in 20 s it is ~3 W mechanical, not ~5 W. The ~12 W electrical figure was already right.
    - **Bushing spacing:** 0.226 m, not 0.225 m.
    - **Foil full-power wind:** 14.1 kn by the GZ method (now used for both sections), not 15 kn by the small-angle GM method.

    ### v5.1 (27 Sep): sail mass from the construction design
    The itemised glass/foam construction (main notebook 5.3) weighs more than the H0 allowance, mainly because of the spine, edge closeouts, bond lines and paint. Loads and drive torque are unchanged. Rig mass, CG, full-power wind, AVS and the ballast needed all move (table above).
    """)
    return


if __name__ == "__main__":
    app.run()
