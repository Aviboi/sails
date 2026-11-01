# Transatlantic Sail: Design Decision Log

**CUSail · Sails subsystem · Avram Dreyer · baseline v5.1, 26 Sep 2026 · PDR Sun 4 Oct**

This log records every design decision for the transatlantic sail in the order it was made: what was decided, what else was considered, why, what it costs, and what would make us revisit it.

The numbers come from **`2_Calculations.ipynb`** (the current baseline and the trade studies behind it) and **`3_Design_History.ipynb`** (the earlier estimates v0–v5), both in this folder, plus **`4_Section_Design.ipynb`** for the exact plate cross-section (equations S1–S19, sources [L#] in its own Section 11). References like **(NB 6.2)** point to sections of the main notebook, **(E51)** to its numbered equations (NB Part 2), **(H3)** to sections of the history notebook, and tags like [L5] to the reference list (NB Appendix A). Together these files are the complete record.

---

## Index

| # | Version | Topic | Decision | Status | Evidence |
|---|---|---|---|---|---|
| D0 | pre-v0 | Architecture | Rigid sail on a rotating mast, driven from inside the hull | Active | — |
| D1 | pre-v0 | Configuration | Rectangular planform, mast on the sail's axis | Active (pivot moved to 50 % chord by D6) | NB 5.1 |
| D2 | pre-v0 | Configuration | Rotation ±200° with hard end stops, no slip ring | Active | — |
| D3 | pre-v0 | Survival | How the sail is held in a storm | **Revised by D6**: self-locking hold, no survival clutch | NB 5.9 |
| D4 | pre-v0 | Structure | Freestanding mast, no side stays | Active | NB 5.6 |
| D5 | pre-v0 | Requirements | Operating and survival environment; design wind 50 kn | Active | NB 1.3 |
| D6 | v2 | Section | 8 % cambered plate, pivot 50 % chord; NACA 0015 foil kept as alternative | Active, with switch-back criteria | NB 4, 6.1; H2 |
| D7 | v4 | Placement | Mast 1.00 m aft of the bow (was 1.20 m) | Active, depends on keel CLR | NB 5.11, 6.2; H4 |
| D8 | v5 | Size | 0.95 × 0.65 m, 0.62 m², AR 1.46 | Active, final after gearbox check | NB 6.3, 6.4; H3, H5 |
| D9 | v5 | Drive | Self-locking worm (NMRV050, or NMRV040 + 2:1), geared DC/BLDC on 5 V | Direction set; unit not yet chosen | NB 6.5 |
| D10 | v5.1 | Construction | E-glass/epoxy faces on a 10 mm PVC-foam core, mast bonded through | Active; verify mass with a sample panel | NB 5.3, 5.8, 6.7; H6 |
| D11 | v5.2 | Section detail | Plate cross-section: 8 % arc kept; rounded-edge, spine and thickness details provisional pending bench data | Provisional; ranking-grade tool only | `4_Section_Design.ipynb` |

Findings that are not decisions but steer the design: **F1** sizing levers, **F2** AVS deferred to the hull, **F3** ballast need, **F4** weather-routing assumption.

### Version history

| Ver. | What changed | Why |
|---|---|---|
| v0 | First area: 0.90 m² (1.20 × 0.75 m), NACA 0015 foil | SA/D scaled down from the comp boat (H1) |
| v1 | Hull measured from CAD | Needed real freeboard, draft and stability (NB Part 3) |
| v2 | Section switched to the cambered plate (D6) | Manufacturing, flooding, light air (H2) |
| v3 | Span cut: 1.00 × 0.75 m (4:3) | Plate hold torque ~105 N·m was unrealistic (H3) |
| v4 | Mast 1.20 → 1.00 m from bow (D7) | Downwind directional stability (H4) |
| — | Trade sweep | Found the drive is the binding constraint (NB 6.3; H5) |
| v5 | 0.95 × 0.65 m (D8); drive hardware direction (D9) | Fit one worm gearbox size (NB 6.4, 6.5) |
| v5.1 | Sail construction designed (D10); sail mass itemised, 1.24 → 2.07 kg | The allowance left out the spine, edges, bond lines and paint (NB 5.3; H0, H6) |
| v5.2 | Section-design notebook (D11): 8 % camber retained; tool limits and a CP discrepancy recorded | Needed a documented method for the exact section (`4_Section_Design.ipynb`) |

---

## Topic A. Mission, architecture and requirements

### Context
The boat is CUSail's MicroTransat entry: an autonomous Atlantic crossing, mostly downwind in the trade winds. The best recent precedent is Oshen's C-Star PC13, which completed the first unaided MicroTransat crossing on 13 Sep 2026: 2,926 nmi in 127 days, through a tropical storm with ~9 m waves [L11]. The same team's 2025 attempt ended three-quarters of the way across when a storm destroyed the sail. That history sets the priorities. **The sail must survive a four-month crossing and at least one severe storm. Speed is secondary.**

### D0: Direct-driven rigid sail (pre-v0; confirmed at the 9/14 mech meeting)
**Decision.** A rigid sail on a rotating mast, driven by a motor and gearbox inside the hull.

**Options considered.**
- A free-rotating wingsail trimmed by a tail
- A soft sail with sheets
- A direct-driven rigid sail (C-Star, Offshore Sensing Sailbuoy)

**Rationale.** This follows Marco's durability research and the two platforms with real ocean endurance. The argument is about exposure:
- All the moving parts (motor, gearbox, encoder) live inside a sealed hull.
- The only things outside are a solid sail and a round mast, with one rotary seal.
- A wingsail puts a tail, its actuator and a free pivot in the spray and the wave impacts.
- A soft sail adds sheets, chafe and UV-degrading cloth.

**Consequence.** The drive carries every aerodynamic moment about the mast, so it becomes the component the design depends on (D3, D8, D9).

### D5: Environment and load cases (revised 26 Sep)
**Decision.**
- Operate in sea state 5; survive sea state 6 or higher.
- Sail at full power in Beaufort 2–6 (~4–27 kn); depower (feather) above that.
- Survive winds of 40–50 kn, and design to 50 kn.
- Speed is secondary: Bft 5 is fine for performance, and the upper end of the range is the real constraint.

**Notes.** On the standard Beaufort scale [L2], 40–50 kn spans Bft 8 to low Bft 10. Designing to 50 kn covers both readings of "Beaufort 8".

These conditions become four load cases (NB 1.3, 5.5):

| Case | Condition | q | What it sizes |
|---|---|---|---|
| Cruise | Bft 3–5 | ≤ ~70 Pa | Performance, area, daily energy |
| Max powered | 27 kn | 118 Pa | Heeling moment, drive operating torque |
| Survival, held | 50 kn, sail feathered and held | 405 Pa | Drive holding torque, end stops |
| Survival, broadside | 50 kn, sail broadside | 405 Pa | Mast root, bearings, plate structure. For the plate this is the likely failed-drive state. |

The structural safety factor is 1.5 on limit loads, a conventional first-pass value [A].

**Mission-level assumption (F4).** Anything worse than 50 kn is avoided by Nav's weather-aware routing (forecast data over Iridium). This belongs in the PDR risk list. NB 5.5 shows a breaking crest at 3 m/s would load the mast to about three times its design moment, so the boat cannot be designed to ride out the worst case.

---

## Topic B. Configuration

### D1: Rectangular planform, mast on the sail's axis (pre-v0)
**Decision.** A rectangular sail with the mast on its axis of symmetry, as on the C-Star.

**Rationale.**
- It keeps the drivetrain and manufacturing simple. The drivetrain is already the most complicated part of the design.
- It avoids a tapered or swept sail whose CP wanders spanwise.
- A symmetric sail is also mass-balanced about the mast, so wave motion adds almost no torque (NB 5.9: 0.2 N·m).

**Later change.** D6 put the pivot at 50 % chord (the arc's symmetry axis) rather than at the centre of pressure.

### D2: Rotation ±200° with hard end stops, no slip ring (pre-v0)
**Decision.** Limited rotation of ±200°, with hard end stops and no slip ring.

**Rationale.**
- 400° of travel lets the sail reach any feathering or trim angle from any wind direction without unwinding through the wind.
- A slip ring would be another sealed, wearing part in the wet zone.
- Any wiring runs inside the mast as a service loop within ±200°. This rules out masthead electronics, so the anemometer goes on a bow or stern pole (Topic F).

**Revisit if** position sensing or controls need continuous rotation.

### D4: Freestanding mast, no side stays (pre-v0)
**Decision.** A freestanding mast with no side stays. Stays matter more for the comp boat's main-and-jib rig.

**Rationale.**
- At the final size the CF tube has a 4× stress margin (NB 5.6), so stays are not needed for strength.
- Stays would add deck fittings and fatigue points.
- Stays would interfere with a sail that must rotate through ±200°.

**Revisit if** the mast has to shrink drastically for mass, or deflection becomes a control problem (currently 3.5 mm at the CE at the limit load).

---

## Topic C. Sail section

### D3: Survival holding strategy (pre-v0; revised by D6)
**Original position.**
- A clutched drive was preferred for survivability. The sail would weathervane when the clutch slipped, though a clutch complicates controls.
- Avoid back-driving where possible; otherwise a back-drive protection circuit is needed for the power board.
- Self-locking is simpler but could reduce stability in a storm.

**Revision (with D6, v2).** A cambered plate on a mid-chord pivot does **not** weathervane. Its free equilibrium is roughly broadside. A slip clutch would therefore swing it broadside in exactly the storm it is meant to survive. For the plate baseline the survival mode is:
- the drive **holds** the sail feathered through a **self-locking worm**
- the gearbox and end stops are rated for **SF × hold torque, static** (NB 5.9, E52)
- an optional overload clutch set above ~80 N·m can protect the gear teeth from wave impacts, but it is not relied on for survival

The clutch strategy survives only in the foil alternative (NB 6.1).

### D6: 8 % circular-arc cambered plate, pivot at 50 % chord (v2)
**Decision.** The baseline section is an 8 % circular-arc cambered plate pivoted at mid-chord, as on the C-Star. The NACA 0015 foil with a 20 %-chord pivot (the v0 baseline) is kept as the PDR alternative.

**Options considered.** Both sections were first compared at the v2 size (H2); NB 6.1 repeats the comparison at the final size.

**Why the plate.**
- **Manufacturing.** A circular arc is a developable surface. It can be laid up over a cylinder or simple former (R = 1.04 m at the final chord) as a flat sandwich panel, with no two-sided mould, internal ribs or sealed shell (NB 5.1, E20).
- **Nothing aloft can flood.** A hollow foil encloses ~41 L at the final size (69 L at v2). If that fills through a crack it puts tens of kilograms 0.6 m above the waterline and very likely capsizes the boat for good. The foil can be foam-filled or compartmented, but that costs mass aloft, which is the foil's other binding constraint.
- **Light-air lift.** Thin cambered plates keep their lift at Re ~10⁵, where thick symmetric sections separate early: C_F,max ≈ 1.3 vs ~1.1 [L4, L5]. Light patches and the doldrums are where a small autonomous boat loses days.
- **Smaller sweep circle.** A mid-chord pivot sweeps Ø 0.65 m against the foil's Ø 1.04 m. On a 0.49 m-beam deck that leaves much more room for solar panels and nav hardware.
- **Why mid-chord.** The arc is symmetric fore–aft. Rotated end-for-end, it presents its concave (pressure) side to windward on either tack, so one fixed-camber plate works on both tacks.

**What it costs.** This is the key trade, and the PDR should state it plainly:
1. **No passive feathering.** If the drive fails, the sail ends up broadside, so 50 kn broadside is a credible design case (D3, NB 5.5).
2. **Much higher drive torque.** The camber couple (C_m ≈ −πf/c ≈ −0.25 [L3]) and a CP that swings ±130 mm about the axis mean the drive must hold ~63 N·m. The foil's clutch slips at ~17 N·m (NB 6.1).
3. **The CE moves with point of sail,** which makes helm balance and mast placement more delicate (D7).
4. **Lower full-power wind,** because the plate's force coefficient is higher and, as built (D10), it is heavier aloft than an unfilled foil shell: 12.3 vs 14.0 kn by the GZ method (NB 6.1). An earlier note gave 15 kn for the foil using the small-angle GM method, which overstates it. Foam-filling the foil against flooding would close most of the mass gap.

**What each concept depends on.** The plate works only if the drive can hold ~63 N·m (≥ 94 N·m static) reliably for four months within ~0.14 m of height. The foil works only if the sail can be made light and flood-proof with its CG on the axis.

**Switch back to the foil if:**
- no worm arrangement meets 94 N·m static within the packaging and mass budget (D9), or
- CFD or a bench test shows the plate's holding torque well above 63 N·m (NB Appendix B #1), or
- the team judges a failed drive leaving the sail broadside to be unacceptable.

---

### D11: Plate cross-section detail (v5.2, provisional)
**Decision.** Keep the 8 % circular-arc section of D6. Take the plate thickness from the D10 layup (10.8 mm: 10 mm core + 2 × 2 plies at an assumed 0.20 mm per cured ply). Round both long edges as ellipses 1.5 % of chord long (tip radius ≈ 3 mm) and fair the mast spine symmetrically (55 mm, ±100 mm) as already set in D6. The edge radius and spine fairing are **provisional**: they are chosen for manufacturing and structure, because the aerodynamic tool cannot resolve their effect.

**Method.** `4_Section_Design.ipynb`: a parametric section generator (S1–S6), thin-airfoil checks (S8, S9), NeuralFoil 2D polars with a lifting-line AR 1.46 correction (S10–S12), pivot moment (S13–S15), and a sweep over camber 5–10 %, thickness 8–13 mm and edge ellipse 0.8–3 % of chord. Ncrit 9 and 4 bracket transition.

**What the work shows.**
- Camber is the only factor that matters. 5 → 10 % raises light-air lift (CL at 10°, Re 9×10⁴: 0.56 → 0.65) and lowers 2D-predicted L/D. Thickness (8–13 mm) and edge radius (0.8–3 % c) move the metrics by ≲ 4 %, so there is no aerodynamic case for changing the baseline.
- The tool is **optimistic on drag**: for Bot's 22.3 % plate at Re 2.4×10⁵ it gives L/D ≈ 27–30 against ≈ 14 reported (about 2×). Its own confidence is low (≲ 0.3 over 0–25°, ≈ 0 for the spine and for Bot-type plates). Use it for ranking only.
- **No stall is found in 0–25°**, though the literature on sharp thin plates reports lift jumps, double stall and unsteady loads. Peak CL in the notebook is CL(25°), a lower bound.
- **Centre of pressure.** The tool puts CP at ≈ 0.45–0.6 c in the lift regime (about at the pivot), not ≈ 0.30 c as assumed in NB Part 5 and D6 cost 2. This affects the CE-versus-mast helm numbers (D7).
- **Thrust versus apparent-wind angle (notebook Section 8c, fixed apparent wind, no hull resistance).** Downwind (β ≥ 120°) camber and section make almost no difference. Camber 6 → 10 % adds about 5–15 % drive only on a reach or closer (β ≲ 90°, 10–20 kn apparent). Plate versus NACA 0015 on the reach depends on the assumed plate stall angle: 12° puts the foil ~25–30 % ahead at β = 60–90°, 18° gives parity (the foil's tool-derived geometric stall is 33°). The heel limit used there is lateral force only, which is less conservative than the whole-force method behind the 12.8 kn full-power wind; check with Luis.
- **Drive torque is not checked.** In the lift regime the pivot moment is |Cm_p| ≈ 0.14 (≈ 7 N·m at 27 kn, ≈ 22 N·m at 50 kn). The 19 / 63 N·m drive requirements come from stalled and broadside loading, which 2D analysis cannot reproduce, so they stand until measured.

**Options considered.** Camber 5–10 % (7 and 9 % are the only plausible alternatives; the tool gives no evidence to move), thicker or thinner core, sharper edges (more laminar-bubble risk at Re ~10⁵, not modelled).

**What would change it.** A bench test or CFD of the baseline plate (CL, Cm about the pivot and CP against angle at Re 1–3×10⁵), used to rescale the polars. A measured CP far from 0.30 c would reopen D7.

---

## Topic D. Placement on the hull

### D7: Mast 1.00 m aft of the bow (v4; supersedes 1.20–1.25 m)
**Decision.** The mast axis is at x ≈ 1.00 m, on the centreline, just forward of mid-length.

**The rule: downwind stability first.** Most of the crossing is running or broad-reaching before the trade winds.
- When running, the plate is broadside and its CP is at mid-chord, on the axis. So the running CE is simply the mast position.
- For the boat to track downwind by itself, the CE must be ahead of the centre of lateral resistance (CLR). Then a yaw disturbance swings the bow back downwind, the way a drogue does.
- With the CE aft of the CLR, the stern tries to lead. The rudder must fight continuously, which costs energy and invites a broach in following seas.
- The CLR is estimated at 1.15 m (range 1.12–1.23 m) because the keel is not drawn yet. At 1.20 m the running CE sat 50 mm *aft* of it: unstable. At 1.00 m it is 150 mm ahead, which covers the whole uncertainty band (NB 6.2; first found on the v3 sail, H4).

**Why not further forward.** Close-hauled, the plate's CE moves ahead of the mast (CP at ~30 % from the windward edge), which gives lee helm. With the v4 sail, lee helm was 47 % of the placeholder rudder's capacity at 1.00 m and 83 % at 0.80 m (H4). With the final v5 sail it is 3.3 N·m, or 36 % (NB 5.11, 6.2).

This is a different philosophy from a crewed yacht, which is usually set up with slight weather helm upwind [L8]. We optimise for downwind tracking and accept mild lee helm on the less common upwind legs.

**Packaging confirms the choice (NB 3.3, 6.2).**
- Hull depth is ~0.25 m everywhere aft of x ≈ 0.35 m, so depth does not constrain the position.
- At 1.00 m the hull is near its widest (half-beam 0.244 m), which leaves room for a motor beside the mast.
- Forward of ~0.5 m the hull is too narrow.

**Interfaces this creates.**
- The deck penetration, heel pad and sweep circle (deck x 0.675–1.325 m) all sit at x ≈ 1.0 m.
- The keel root (likely x ≈ 1.0–1.2 m) lands under or just aft of the heel bushing. The keel box and heel pad should be one structure, and the fin bolts must clear the pad (Luis, Ava).
- Megan should size the rudder against the lee-helm curve in NB 5.11 / 6.2.

**Revisit when** the keel CLR and the rudder are drawn: change the inputs in NB 1.4 and re-run; 5.11 and 6.2 update.

---

## Topic E. Size

### D8: 0.95 × 0.65 m, 0.62 m², AR 1.46 ≈ 3:2 (v5; supersedes 1.00 × 0.75 m and 1.20 × 0.75 m)
**Philosophy: err small.** The team priority is survivability and drivetrain margin over speed. The resulting sail is deliberately modest: SA/D ≈ 7.3, against ~17.7 for our comp boat (NB 5.1, E22). A smaller sail cuts every survival load in proportion, and cuts drive torque more than proportionally.

**How the size was found.**
1. v0 (0.90 m²) came from scaling the comp boat's SA/D (H1).
2. With the plate, that size needed ~105 N·m hold (H2), so v3 cut the span to 1.00 × 0.75 m.
3. The trade sweep (NB 6.3; first run on the v3/v4 sail, H5) ran every span, chord and keel combination against four constraints: drive, full-power wind, AVS and mast. Its key finding (F1) is that **the drive limits chord and heel limits span.** The v3/v4 sail was marginal on three constraints at once, and the mast was never close to limiting.
4. Every term in the torque is proportional to q·A·c, so hold torque grows as **A^1.5/√AR** (NB 6.4, E60). The v4 sail needed 132 N·m static, above what a single common worm size carries (NB 6.5). **0.95 × 0.65 m brings it to 94 N·m**, which fits an NMRV050-class worm directly, or an NMRV040 behind a 2:1 final stage.

Every other load drops too (H6):

| | v4 | v5 |
|---|---|---|
| 50 kn broadside force | 410 N | 338 N |
| Mast moment (limit) | 246 N·m | 194 N·m |
| Deck bearing (limit) | 1.5 kN | 1.2 kN |
| Rig | 2.6 kg | 2.3 kg (3.2 kg with the v5.1 construction estimate, D10) |

**Why not a higher aspect ratio.** At fixed area, AR 1.5 → 2.0 cuts hold torque only 13 %, but raises mast moment 13 % and heeling moment 8 % (NB 6.4). It also raises mass aloft, air draft and shading, and lowers the Reynolds number, which gives a sharper stall. The low-AR range (1:1–3:2) matches the C-Star.

If the drive is still tight after gearbox selection, the preferred levers are, in order:
1. a final gear stage
2. a small area cut to ~0.55 m²
3. at most AR ≈ 1.75

**What it costs.** Versus the 0.75 m² sail, force is 18 % lower in winds below ~11 kn, roughly 9 % less light-air boat speed (NB 6.4). Above ~11–13 kn both sails are depowered anyway, so there is no difference. For a survival-first mission this is acceptable.

**Finalised by** the gearbox candidate's static rating and fit (D9, open item 1).

### Findings from the sizing work
- **F1: Sizing levers.** Chord and area are limited by drive torque; span is limited by heel (full-power wind). Keel levers are weak: +1 kg of bulb ≈ +0.5 kn of full-power wind and +5° AVS, and +0.06 m of depth ≈ +0.5 kn and +6° (NB 6.3).
- **F2: AVS is a hull and layout issue, deferred.** With the watertight flat deck, AVS is 124° with the v5.1 rig mass (133° with the earlier allowance). That is short of the 135° placeholder, and full self-righting from inverted needs the system CG ~0.2 m below the waterline, which no practical keel reaches (NB 6.3). Sail size moves AVS only moderately (about −5° per +0.1 m of span), and the sail's construction mass about as much (D10). The options for a team decision are: lower the hull systems, add buoyancy aloft (a sealed tip strip on the plate), change the deck, or accept a lower target.
- **F3: The sail needs little ballast.** Full power to 12 kn needs ~6.5 kg of bulb at 0.28 m: a ~26 % ballast ratio on the resulting 25.1 kg (NB 6.6; 5.5 kg before the v5.1 mass update). With 7 kg it holds to 12.3 kn. The keel can be sized for survivability rather than sail power. The GZ curve is used rather than GM·sin φ, because the flat deck edge and the bilge make the small-angle estimate ~18 % optimistic at 20° (NB 5.4, E34 vs E10).

---

## Topic F. Structure, drive and deck layout

### Mast and bushings (supports D4)
**Mast.** Roll-wrapped CF tube, 42 mm OD × 2.5 mm wall, bonded into the sail spine.
- σ_ult ≈ 101 MPa against 400 MPa allowable (NB 5.6).
- A 35 mm tube would still give ~2.7× margin. 42 mm is kept for spine stiffness and bond area, for fatigue (~1.6 million wave cycles per crossing at the mast root, spine bond, bushings and seal), and for a larger seal surface.
- A stainless or hard-anodised sleeve goes under the seal.

**Bushings.** Two polymer plain bushings (iglide/Vesconite type, 42 mm ID): one at the deck, and one ~25 mm above the inside of the hull bottom. The hull depth fixes the spacing at 0.226 m.
- Reactions are 0.86 kN at the heel and 1.20 kN at the deck (limit), scaling as moment ÷ spacing (NB 5.7, E43).
- Plain polymer bushings are chosen over rolling bearings for corrosion resistance and tolerance of grit. The mast turns slowly and rarely, so robustness matters more than friction.
- A ~75 mm raised deck boss (spacing 0.30 m) would cut the deck reaction by ~18 % and give the drive more height. Worth discussing with Ava.

**Plate.** The construction is D10 (Topic G). Its structural checks (NB 5.8) are summarised there.

### D9: Drive hardware direction (v5)
**Gearbox.** A self-locking worm with i ≳ 50 (static efficiency < 50 % [L14]), holding at zero power. Two options (NB 6.5, catalog continuous ratings [L13]):
- **(a) NMRV050-class at i = 60–80:** carries the full 63 N·m hold, with margin 1.15–1.4 on the continuous rating.
- **(b) NMRV040-class plus a 2:1 spur or chain stage on the mast:** the worm sees ~31 N·m, with margin 1.1–1.4. This probably fits the ~0.14 m of height between the bushings better, and the worm still locks the whole train.

In both cases, confirm on the datasheet: static or peak rating, self-locking at the chosen ratio, and housing height and mass.

**Motor.** A geared DC or BLDC motor into the worm, on the existing 5 V / 10 A rail, with no 12 V boost converter (NB 6.5).
- Operating torque is 19 N·m. At 180° in 20 s that is ~3 W mechanical, ~12 W electrical at 25 % overall efficiency. At 180° in 10 s it is ~6 W and ~23 W.
- At ~2,000:1 overall, the motor needs only ~30 mN·m.
- A stepper adds nothing: the worm already holds at zero power, and steppers lose torque at 5 V and draw holding current. A 12 V stepper remains the fallback if open-loop positioning is wanted.
- Daily energy is ~3.4 Wh, of which ~2.4 Wh is standby, so actuation energy is not a driver (NB 5.10).

**Sensing.** An absolute encoder on the mast itself, so gear backlash or a slipped coupling never corrupts the sail angle.

**Open: the "last-move" wind.** This is the highest wind in which the drive must still rotate the sail rather than only hold it.
- Feathered by 27 kn → the motor train is sized for ~19 N·m.
- Re-trim at 35 kn → ~31 N·m.
- The gearbox is sized by the hold either way.

**Packaging.** Reserve ~200 × 150 × 130 mm around the mast at x ≈ 1.00 m, kept clear of the keel box.

### Deck layout and keep-outs (follows from D2, D6, D7)
- Nothing taller than 0.10 m inside the Ø 0.65 m sweep circle (deck x 0.675–1.325 m).
- Solar: clear aft of x ≈ 1.33 m (~0.65 m of the widest deck); clear but narrow forward of 0.67 m. Both are shaded at times by the 1.23 m tip.
- No masthead electronics (D2). The anemometer goes on a bow or stern pole outside the sweep circle. Bow is preferred: the stern sits in the sail's wake, while the bow sees only upwash, which can be calibrated.

---

## Topic G. Sail construction

### D10: E-glass/epoxy on a PVC-foam core, mast bonded through (v5.1)
**Decision.** The plate is a foam-core sandwich (NB 5.3):
- **Faces:** 2 × 200 g/m² plain-weave E-glass per face, epoxy, vacuum-bagged (~0.39 mm, ~0.67 kg/m² per face).
- **Core:** 10 mm PVC foam at 60 kg/m³ (Divinycell H60 class [L12]), scored so it drapes onto the 1.04 m arc.
- **Edges:** all four sealed with thickened epoxy and a glass wrap.
- **Spine:** the mast passes through the plate. The two halves are bonded to it with four fillets and 2 extra plies per face over ±100 mm.
- **Finish:** UV-stable polyurethane paint.
- **Tooling:** vacuum-bagged on a 1.04 m-radius former.

The itemised sail mass is 2.07 kg (E26–E29).

**Options considered.** Five constructions were sized to the same loads and criteria (NB 6.7):

| Option | Sail | Full power to | AVS | Bulb for 12 kn |
|---|---|---|---|---|
| A. Glass/foam sandwich (chosen) | 2.07 kg | 12.3 kn | 124° | 6.5 kg |
| B. Carbon/foam sandwich | 1.69 kg | 12.5 kn | 128° | 6.0 kg |
| C. Aluminium 5052 sheet, 1 mm, on 4 waterjet-cut ribs | 2.41 kg | 12.0 kn | 120° | 6.9 kg |
| D. Polycarbonate sheet, 2 mm, on 6 ribs | 2.39 kg | 12.0 kn | 120° | 6.9 kg |
| E. Aluminium composite panel (ACM), 3 mm, on 3 ribs | 2.90 kg | 11.7 kn | 114° | 7.6 kg |

**Rationale.**
- **Strength does not set the layup.** At ultimate load the face stress is ~11 MPa against a 100 MPa allowable, and core shear is 26 kPa against 350 kPa. Tip deflection at limit is 2.2 mm against 5 mm (NB 5.8, E47–E50). A 7 mm core would still meet the deflection limit. The two-ply faces are set by damage tolerance: impact, handling and abrasion.
- **Composite vs non-composite.** On mass alone the composite is only ~0.3 kg ahead of the best sheet-and-rib options. That is worth ~0.3 kn of full-power wind and ~4° of AVS. The composite is chosen for three other reasons:
  1. **No mechanical joints in the fatigue zone.** Sheet-and-rib sails carry every wave load (~1.6 million cycles) through rivet or bolt holes and rib roots in seawater.
  2. **Smooth faces.** The sheet options need 11–15 mm ribs on a 52 mm-deep arc. They would go on the concave face, which is always the pressure side because the plate flips end-for-end, but they still disturb the flow.
  3. **Damage tolerance and repair.** Glass/epoxy dents locally and patches with epoxy. Riveted aluminium cracks progressively, and polycarbonate crazes under UV or stress.

  The extra manufacturing effort is modest: one former, vacuum bagging and two cure cycles.
- **Glass, not carbon.** Glass is more tolerant of impact and abrasion, cheaper, and has no galvanic issue with aluminium hardware. Carbon faces would save ~0.4 kg aloft.
- **Foam, not balsa or honeycomb.** Balsa and honeycomb soak up water once damaged, and something eventually will damage the sail.
- **Epoxy, not polyester or vinylester.** Epoxy bonds to foam better and has better fatigue life, and the spine bond is the critical joint.

**Consequence: the v5.1 mass update.** The earlier allowance (0.6 kg/m² per face + 15 %, 1.24 kg) left out the spine, edge closeouts, bond lines and paint. Using the itemised 2.07 kg:

| | v5 (allowance) | v5.1 (itemised) |
|---|---|---|
| Rig mass | 2.3 kg @ +0.60 m | 3.2 kg @ +0.64 m |
| Full power until | 12.8 kn | 12.3 kn |
| AVS | 133° | 124° |
| Bulb for full power to 12 kn | 5.5 kg | 6.5 kg |

Loads, mast sizing, bearing reactions and drive torque are unchanged (NB 6.7; H6).

**Revisit if:**
- a weighed sample panel and spine section differ from the estimate by more than ~20 %
- the team sets an AVS requirement: carbon faces (B) or a sealed tip strip then become attractive
- a vacuum-bagged layup can't be scheduled: fall back to option C, aluminium sheet on waterjet-cut ribs, with a fatigue inspection plan

---

## Open items and owners

| # | Item | Owner | Affects |
|---|---|---|---|
| 1 | Gearbox candidate: static/peak rating, self-locking at the chosen ratio, housing height and mass | Audrey | Finalises D8, D9 |
| 2 | "Last-move" wind | Audrey, Nav | Motor torque |
| 3 | Keel CLR and ballast | Luis | D7 margin, F3 |
| 4 | Rudder size and position | Megan | D7 lee-helm % |
| 5 | Plate moment and CP by CFD, then a bench test (the section notebook gives CP ≈ 0.45–0.6 c vs 0.30 c assumed) | Avram | D6 switch-back, D7, D8, D11 |
| 6 | Raised deck boss | Ava | Bearing loads, drive height |
| 7 | AVS requirement | Team | F2 |
| 8 | Weather-routing assumption in the PDR risks | Nav | F4 |
| 9 | Updated displacement / hull CAD newer than 9/14 | Hull | Re-run NB Part 3 |
| 10 | Build and weigh a 300 × 300 mm sample panel and a spine section | Avram | D10 mass, F2, F3 |

The assumptions behind these numbers, ranked by effect, are in NB Appendix B.

---

## Corrections to earlier notes
Moving everything into the notebook turned up a few small errors in earlier notes:
- **Ballast ratio:** full power to 12 kn needs ~24 % of 23.2 kg, not ~22 %.
- **Slewing power:** at 180° in 20 s it is ~3 W mechanical, not ~5 W. The ~12 W electrical figure was already right.
- **Bearing spacing:** 0.226 m, not 0.225 m.
- **Foil full-power wind:** 14.1 kn by the GZ method (used for both sections now), not 15 kn by the small-angle GM method.
