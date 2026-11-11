# Slip clutch in the design study

Date: 2026-11-10. Status: draft for approval. Extends `2026-11-10-design-study-design.md`.

## Intent

The real drivetrain has a slip clutch **before the gearbox** (motor side) so the sail can feather in strong gusts. The design study's survival case assumes the sail stays locked beam-on at a normal-force coefficient of 1.2 at 45 kn. With the clutch that case is wrong, and the study's main conclusion (survival and minimum-wind speed cannot both be met) depends on it. The study should model the clutch, with the slip torque as a design variable "within reasonable limits".

## What changes

### New design variables
- **Slip torque** `T_s` (N·m, motor side). The torque at the mast is about `T_s · N / η_back`, where `N` is the gear ratio and `η_back` is the back-driving efficiency. Back-driving through the gearbox is assumed less efficient than driving, and `η_back` is a placeholder estimate.
- **Mast axis position** (fraction of chord, now 0.24), as a second variable in a margin-line pair with the slip torque. For the sail to feather like a weathervane the axis must be ahead of the aerodynamic centre (about 0.25 chord).

### Reasonable limits (placeholders, new `Param`s)
- Slip torque sweep range: 0.02 to 0.4 N·m (motor side). The upper end is where the mast-side torque reaches the 30 N·m gearbox rating at the current ratio and efficiency; the lower end is about the current motor holding torque.
- Mast axis sweep range: 0.15 to 0.30 chord.
- Gust factor on the design wind for the holding check: 1.5.
- Residual feathering angle: 5°.
- Minimum feathering stability, the distance of the axis ahead of the aerodynamic centre: 0.02 chord.

### The window the slip torque must sit in (mast-side torque)
- **Lower bound:** above the holding torque at the design wind with gust factor and the torque safety factor, so the sail does not feather in ordinary gusts and lose drive. At the current design this is about 1.6 N·m (the existing holding torque) times the gust factor.
- **Upper bound:** low enough that the sail slips before the load becomes unsurvivable. Locked at 45 kn the mast torque is about 4.0 N·m at the current design, so the clutch must slip below that; it must also stay under the gearbox rating.
- At the current design the window is therefore narrow, roughly 1.6 to 4 N·m at the mast, and the study should show how it moves with sail area and mast axis.

### Load cases
- **Pre-slip (gust) case:** the sail holds up to the angle where the mast torque reaches the slip torque. The structural and heeling loads are those at that angle, in the design wind with gust factor and in the survival wind.
- **Feathered case:** after slipping, the sail sits at the residual angle; its loads (mostly drag) and the hull windage give the survival moment.
- **Locked (jammed clutch) case:** the current survival case, kept as a selectable fail-safe check, off by default.
- If the slip torque exceeds the locked-case torque the clutch never slips, and the result must reduce to the current numbers. This is the main correctness check.

### New and changed margins in `evaluate`
- `slip_hold`: slip torque against holding torque × gust factor × safety factor (minimum).
- `slip_gearbox`: mast-side slip torque against the gearbox rating (maximum).
- `feather_stability`: axis distance ahead of the aerodynamic centre (minimum).
- `survival`, `deflection`, `strength`, `stability_range`: now evaluated for the governing of the pre-slip and feathered cases.
- The existing gearbox survival check uses the slip-limited torque.

### Study views
- The map's objective shading is re-derived from the new survival margin, with the slip torque held at the current design value.
- A new margin-line pair: slip torque and mast axis, showing `slip_hold`, `slip_gearbox`, `feather_stability`, `survival` and `strength`, so the window between the lower and upper bounds is visible.
- The what-binds table gains the new margins.

## Goals
- See how the slip torque and mast axis move survival, strength and the drivetrain checks.
- See whether the conflict between survival and minimum-wind speed disappears once the sail feathers.
- Reduce exactly to the current results when the clutch never slips.

## Non-goals
- Gust dynamics: how far a gust overshoots before the clutch slips, and clutch response time. The model is quasi-static, with the gust factor standing in for the dynamics.
- A clutch part selection or its detailed friction behaviour.

## Anti-goals
- Hiding the narrowness of the window: a design that technically has a window of a few percent should show as marginal.
- Changing single-design results: the existing cells and the Design Summary keep their numbers.

## Builder's calls (flagged, not agreed)
- `η_back` (back-driving efficiency) default, taken equal to the drive efficiency until measured.
- How the slip angle is found when the mast torque is not monotonic in angle (take the first angle at which the torque reaches the slip torque, going up from zero).
- Whether the gust factor also applies in the survival wind (default: no, the survival wind is already an extreme).
- Where the feathering-stability margin takes the aerodynamic centre from (0.25 chord for the section, or the polar's own value).

## Open questions
- Whether the lower bound should use the existing holding torque (which includes friction and a safety factor) or the aerodynamic torque alone, to avoid counting the safety factor twice.
- Whether the real clutch has a fixed slip torque or an adjustable one; this only affects how the result is described.
