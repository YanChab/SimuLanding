from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from .engine import (
    EngineOutput,
    _endstop,
    _integrate_const_acc,
    _trailing_arm_local_step,
    _jambe_brace_step,
    TrailingArmLocalState,
)
from .engine_strait_strut import (
    _init_strait_strut_local_state,
    _rot_sol_to_lg,
    _strait_strut_advance_local_state,
    _strait_strut_resolve_damper_step,
    _ffrijoi_nlg,
    _ffribag_nlg,
    _bushing_loads,
    _drag_brace_step,
    StraitStrutLocalState,
)
from .engine_leaf_spring import leaf_spring_step
from .errors import OVERSTROKE_CODES, SimError, make_overstroke_warning
from .gas import GasSpring
from .inputs import AircraftParamsSI, TrailingArmParamsSI, _strut_geom_si
from .metering import build_section_table
from .tyre import build_tyre_tables, f_tyre, mu, r_eff
from .units import G


OUTPUT_COLUMNS_AC: dict[str, str] = {
    "temps": "Temps (s)",
    "aircraft_cg_z": "Aircraft.CG.z (m)",
    "aircraft_cg_vz": "Aircraft.CG.vz (m/s)",
    "aircraft_cg_az": "Aircraft.CG.az (m/s²)",
    "aircraft_pitch": "Aircraft.Pitch (rad)",
    "aircraft_pitch_rate": "Aircraft.PitchRate (rad/s)",
    "aircraft_pitch_acc": "Aircraft.PitchAcc (rad/s²)",
    "aircraft_fz_total": "Aircraft.Fz total (N)",
    "aircraft_fz_nlg": "Aircraft.Fz NLG (N)",
    "aircraft_fz_mlg_left": "Aircraft.Fz MLG left (N)",
    "aircraft_fz_mlg_right": "Aircraft.Fz MLG right (N)",
    "aircraft_mx_total": "Aircraft.Mpitch total (N.m)",
    "aircraft_e_kin_fuse": "Énergie.Cinétique fuselage (J)",
    "aircraft_e_kin_trains": "Énergie.Cinétique trains (J)",
    "aircraft_e_stock": "Énergie.Stockée totale (J)",
    "aircraft_e_diss": "Énergie.Dissipée totale (J)",
    "aircraft_e_input": "Énergie.Apport total (J)",
    "aircraft_e_residual": "Énergie.Résidu de bilan (J)",
    "nlg_stroke": "NLG.d (m)",
    "nlg_velocity": "NLG.v (m/s)",
    "nlg_ftot": "NLG.Ftot (N)",
    "nlg_fhyd": "NLG.Fhyd (N)",
    "nlg_ffrijoi": "NLG.FFriJoi (N)",
    "nlg_ffribag": "NLG.FFriBag (N)",
    "nlg_fgas": "NLG.FGas (N)",
    "nlg_pg": "NLG.Pg (bar)",
    "nlg_pc": "NLG.Pc (bar)",
    "nlg_pd": "NLG.Pd (bar)",
    "nlg_delta_pc": "NLG.DeltaPc (bar)",
    "nlg_delta_pd": "NLG.DeltaPd (bar)",
    "nlg_hyd_qc_total": "NLG.Hyd.Qc total (m³/s)",
    "nlg_hyd_qc_bh": "NLG.Hyd.Qc BH (m³/s)",
    "nlg_hyd_qc_leak": "NLG.Hyd.Qc fuite (m³/s)",
    "nlg_hyd_leak_ratio": "NLG.Hyd.Part fuite (-)",
    "nlg_hyd_re_leak": "NLG.Hyd.Re fuite (-)",
    "nlg_hyd_conv_err": "NLG.Hyd.Erreur conv (-)",
    "nlg_hyd_conv_iter": "NLG.Hyd.Iter conv (-)",
    "nlg_secbh": "NLG.Section BH (mm²)",
    "nlg_tyre_defl": "NLG.TyreDefl (m)",
    "nlg_tyre_ftyre": "NLG.Tyre.FTyre (N)",
    "nlg_tyre_mu": "NLG.Tyre.Mu (-)",
    "nlg_tyre_slip": "NLG.Tyre.Slip (-)",
    "nlg_tyre_omega": "NLG.Tyre.Omega (rad/s)",
    "nlg_tyre_alpha": "NLG.Tyre.Alpha (rad/s²)",
    "nlg_tr_x": "NLG.TR.X (N)",
    "nlg_reaction_h": "NLG.Reaction H (N)",
    "nlg_reaction_v": "NLG.Reaction V (N)",
    "nlg_xgt": "NLG.XGt (N)",
    "nlg_xgb": "NLG.XGb (N)",
    "nlg_db_brace_T": "NLG.DragBrace.Effort bielle (N)",
    "nlg_db_b1_fx": "NLG.DragBrace.B1 Fx (N)",
    "nlg_db_b1_fy": "NLG.DragBrace.B1 Fy (N)",
    "nlg_db_b1_fz": "NLG.DragBrace.B1 Fz (N)",
    "nlg_db_b2_fx": "NLG.DragBrace.B2 Fx (N)",
    "nlg_db_b2_fy": "NLG.DragBrace.B2 Fy (N)",
    "nlg_db_b2_fz": "NLG.DragBrace.B2 Fz (N)",
    "nlg_db_f1_fx": "NLG.DragBrace.F1 Fx (N)",
    "nlg_db_f1_fy": "NLG.DragBrace.F1 Fy (N)",
    "nlg_db_f1_fz": "NLG.DragBrace.F1 Fz (N)",
    "nlg_db_f2_fx": "NLG.DragBrace.F2 Fx (N)",
    "nlg_db_f2_fy": "NLG.DragBrace.F2 Fy (N)",
    "nlg_db_f2_fz": "NLG.DragBrace.F2 Fz (N)",
    "nlg_db_brace_fx": "NLG.DragBrace.Bielle Fx (N)",
    "nlg_db_brace_fy": "NLG.DragBrace.Bielle Fy (N)",
    "nlg_db_brace_fz": "NLG.DragBrace.Bielle Fz (N)",
    "nlg_accms": "NLG.AccMs (m/s²)",
    "nlg_accmns": "NLG.AccMns (m/s²)",
    "nlg_vitmns": "NLG.VitMns (m/s)",
    "nlg_depmns": "NLG.DepMns (m)",
    "nlg_tors_res_x": "NLG.Torseur.Resultante X (N)",
    "nlg_tors_res_z": "NLG.Torseur.Resultante Z (N)",
    "nlg_tors_res_norm": "NLG.Torseur.Resultante norme (N)",
    "nlg_torsb_fx": "NLG.Torseur@B.Fx (N)",
    "nlg_torsb_fz": "NLG.Torseur@B.Fz (N)",
    "nlg_torsb_mx": "NLG.Torseur@B.Mx (N.m)",
    "nlg_torsb_my": "NLG.Torseur@B.My tangage (N.m)",
    "nlg_torsb_mz": "NLG.Torseur@B.Mz (N.m)",
    "mlg_left_stroke": "MLG left.d (m)",
    "mlg_left_velocity": "MLG left.v (m/s)",
    "mlg_left_ftot": "MLG left.Ftot (N)",
    "mlg_left_fhyd": "MLG left.Fhyd (N)",
    "mlg_left_ffrijoi": "MLG left.FFriJoi (N)",
    "mlg_left_fgas": "MLG left.FGas (N)",
    "mlg_left_pg": "MLG left.Pg (bar)",
    "mlg_left_pc": "MLG left.Pc (bar)",
    "mlg_left_pd": "MLG left.Pd (bar)",
    "mlg_left_delta_pc": "MLG left.DeltaPc (bar)",
    "mlg_left_delta_pd": "MLG left.DeltaPd (bar)",
    "mlg_left_hyd_qc_total": "MLG left.Hyd.Qc total (m³/s)",
    "mlg_left_hyd_qc_bh": "MLG left.Hyd.Qc BH (m³/s)",
    "mlg_left_hyd_qc_leak": "MLG left.Hyd.Qc fuite (m³/s)",
    "mlg_left_hyd_leak_ratio": "MLG left.Hyd.Part fuite (-)",
    "mlg_left_hyd_re_leak": "MLG left.Hyd.Re fuite (-)",
    "mlg_left_hyd_conv_err": "MLG left.Hyd.Erreur conv (-)",
    "mlg_left_hyd_conv_iter": "MLG left.Hyd.Iter conv (-)",
    "mlg_left_secbh": "MLG left.Section BH (mm²)",
    "mlg_left_tyre_defl": "MLG left.TyreDefl (m)",
    "mlg_left_tyre_ftyre": "MLG left.Tyre.FTyre (N)",
    "mlg_left_tyre_mu": "MLG left.Tyre.Mu (-)",
    "mlg_left_tyre_slip": "MLG left.Tyre.Slip (-)",
    "mlg_left_tyre_omega": "MLG left.Tyre.Omega (rad/s)",
    "mlg_left_tyre_alpha": "MLG left.Tyre.Alpha (rad/s²)",
    "mlg_left_fx": "MLG left.Fx (N)",
    "mlg_left_reaction_h": "MLG left.Reaction H (N)",
    "mlg_left_reaction_v": "MLG left.Reaction V (N)",
    "mlg_left_accms": "MLG left.AccMs (m/s²)",
    "mlg_left_db_brace_T": "MLG left.DragBrace.Effort bielle (N)",
    "mlg_left_db_b1_fx": "MLG left.DragBrace.B1 Fx (N)",
    "mlg_left_db_b1_fy": "MLG left.DragBrace.B1 Fy (N)",
    "mlg_left_db_b1_fz": "MLG left.DragBrace.B1 Fz (N)",
    "mlg_left_db_b2_fx": "MLG left.DragBrace.B2 Fx (N)",
    "mlg_left_db_b2_fy": "MLG left.DragBrace.B2 Fy (N)",
    "mlg_left_db_b2_fz": "MLG left.DragBrace.B2 Fz (N)",
    "mlg_left_db_f1_fx": "MLG left.DragBrace.F1 Fx (N)",
    "mlg_left_db_f1_fy": "MLG left.DragBrace.F1 Fy (N)",
    "mlg_left_db_f1_fz": "MLG left.DragBrace.F1 Fz (N)",
    "mlg_left_db_f2_fx": "MLG left.DragBrace.F2 Fx (N)",
    "mlg_left_db_f2_fy": "MLG left.DragBrace.F2 Fy (N)",
    "mlg_left_db_f2_fz": "MLG left.DragBrace.F2 Fz (N)",
    "mlg_left_db_brace_fx": "MLG left.DragBrace.Bielle Fx (N)",
    "mlg_left_db_brace_fy": "MLG left.DragBrace.Bielle Fy (N)",
    "mlg_left_db_brace_fz": "MLG left.DragBrace.Bielle Fz (N)",
    "mlg_left_tors_res_x": "MLG left.Torseur.Resultante X (N)",
    "mlg_left_tors_res_z": "MLG left.Torseur.Resultante Z (N)",
    "mlg_left_tors_res_norm": "MLG left.Torseur.Resultante norme (N)",
    "mlg_left_torsc_fx": "MLG left.Torseur@C.Fx (N)",
    "mlg_left_torsc_fz": "MLG left.Torseur@C.Fz (N)",
    "mlg_left_torsb_fx": "MLG left.Torseur@B.Fx (N)",
    "mlg_left_torsb_fz": "MLG left.Torseur@B.Fz (N)",
    "mlg_left_torsb_mx": "MLG left.Torseur@B.Mx (N.m)",
    "mlg_left_torsb_my": "MLG left.Torseur@B.My tangage (N.m)",
    "mlg_left_torsb_mz": "MLG left.Torseur@B.Mz (N.m)",
    "mlg_right_stroke": "MLG right.d (m)",
    "mlg_right_velocity": "MLG right.v (m/s)",
    "mlg_right_ftot": "MLG right.Ftot (N)",
    "mlg_right_fhyd": "MLG right.Fhyd (N)",
    "mlg_right_ffrijoi": "MLG right.FFriJoi (N)",
    "mlg_right_fgas": "MLG right.FGas (N)",
    "mlg_right_pg": "MLG right.Pg (bar)",
    "mlg_right_pc": "MLG right.Pc (bar)",
    "mlg_right_pd": "MLG right.Pd (bar)",
    "mlg_right_delta_pc": "MLG right.DeltaPc (bar)",
    "mlg_right_delta_pd": "MLG right.DeltaPd (bar)",
    "mlg_right_hyd_qc_total": "MLG right.Hyd.Qc total (m³/s)",
    "mlg_right_hyd_qc_bh": "MLG right.Hyd.Qc BH (m³/s)",
    "mlg_right_hyd_qc_leak": "MLG right.Hyd.Qc fuite (m³/s)",
    "mlg_right_hyd_leak_ratio": "MLG right.Hyd.Part fuite (-)",
    "mlg_right_hyd_re_leak": "MLG right.Hyd.Re fuite (-)",
    "mlg_right_hyd_conv_err": "MLG right.Hyd.Erreur conv (-)",
    "mlg_right_hyd_conv_iter": "MLG right.Hyd.Iter conv (-)",
    "mlg_right_secbh": "MLG right.Section BH (mm²)",
    "mlg_right_tyre_defl": "MLG right.TyreDefl (m)",
    "mlg_right_tyre_ftyre": "MLG right.Tyre.FTyre (N)",
    "mlg_right_tyre_mu": "MLG right.Tyre.Mu (-)",
    "mlg_right_tyre_slip": "MLG right.Tyre.Slip (-)",
    "mlg_right_tyre_omega": "MLG right.Tyre.Omega (rad/s)",
    "mlg_right_tyre_alpha": "MLG right.Tyre.Alpha (rad/s²)",
    "mlg_right_fx": "MLG right.Fx (N)",
    "mlg_right_reaction_h": "MLG right.Reaction H (N)",
    "mlg_right_reaction_v": "MLG right.Reaction V (N)",
    "mlg_right_accms": "MLG right.AccMs (m/s²)",
    "mlg_right_db_brace_T": "MLG right.DragBrace.Effort bielle (N)",
    "mlg_right_db_b1_fx": "MLG right.DragBrace.B1 Fx (N)",
    "mlg_right_db_b1_fy": "MLG right.DragBrace.B1 Fy (N)",
    "mlg_right_db_b1_fz": "MLG right.DragBrace.B1 Fz (N)",
    "mlg_right_db_b2_fx": "MLG right.DragBrace.B2 Fx (N)",
    "mlg_right_db_b2_fy": "MLG right.DragBrace.B2 Fy (N)",
    "mlg_right_db_b2_fz": "MLG right.DragBrace.B2 Fz (N)",
    "mlg_right_db_f1_fx": "MLG right.DragBrace.F1 Fx (N)",
    "mlg_right_db_f1_fy": "MLG right.DragBrace.F1 Fy (N)",
    "mlg_right_db_f1_fz": "MLG right.DragBrace.F1 Fz (N)",
    "mlg_right_db_f2_fx": "MLG right.DragBrace.F2 Fx (N)",
    "mlg_right_db_f2_fy": "MLG right.DragBrace.F2 Fy (N)",
    "mlg_right_db_f2_fz": "MLG right.DragBrace.F2 Fz (N)",
    "mlg_right_db_brace_fx": "MLG right.DragBrace.Bielle Fx (N)",
    "mlg_right_db_brace_fy": "MLG right.DragBrace.Bielle Fy (N)",
    "mlg_right_db_brace_fz": "MLG right.DragBrace.Bielle Fz (N)",
    "mlg_right_tors_res_x": "MLG right.Torseur.Resultante X (N)",
    "mlg_right_tors_res_z": "MLG right.Torseur.Resultante Z (N)",
    "mlg_right_tors_res_norm": "MLG right.Torseur.Resultante norme (N)",
    "mlg_right_torsc_fx": "MLG right.Torseur@C.Fx (N)",
    "mlg_right_torsc_fz": "MLG right.Torseur@C.Fz (N)",
    "mlg_right_torsb_fx": "MLG right.Torseur@B.Fx (N)",
    "mlg_right_torsb_fz": "MLG right.Torseur@B.Fz (N)",
    "mlg_right_torsb_mx": "MLG right.Torseur@B.Mx (N.m)",
    "mlg_right_torsb_my": "MLG right.Torseur@B.My tangage (N.m)",
    "mlg_right_torsb_mz": "MLG right.Torseur@B.Mz (N.m)",
}


GEOMETRY_KEYS_AC: tuple[str, ...] = (
    "cg_x",
    "cg_z",
    "ground_z",
    "nlg_bx",
    "nlg_bz",
    "nlg_gtx",
    "nlg_gtz",
    "nlg_gbx",
    "nlg_gbz",
    "nlg_rx",
    "nlg_rz",
    "nlg_wheel_radius",
    "nlg_b1x", "nlg_b1z", "nlg_b2x", "nlg_b2z",
    "nlg_cdbx", "nlg_cdbz", "nlg_ddbx", "nlg_ddbz",
    "nlg_f1x", "nlg_f1z", "nlg_f2x", "nlg_f2z",
    "nlg_jdx", "nlg_jdz", "nlg_jex", "nlg_jez",
    "mlg_left_ax",
    "mlg_left_az",
    "mlg_left_bx",
    "mlg_left_bz",
    "mlg_left_cx",
    "mlg_left_cz",
    "mlg_left_rx",
    "mlg_left_rz",
    "mlg_left_wheel_radius",
    "mlg_left_b1x", "mlg_left_b1z", "mlg_left_b2x", "mlg_left_b2z",
    "mlg_left_cdbx", "mlg_left_cdbz", "mlg_left_ddbx", "mlg_left_ddbz",
    "mlg_left_f1x", "mlg_left_f1z", "mlg_left_f2x", "mlg_left_f2z",
    "mlg_left_jdx", "mlg_left_jdz", "mlg_left_jex", "mlg_left_jez",
    "mlg_right_ax",
    "mlg_right_az",
    "mlg_right_bx",
    "mlg_right_bz",
    "mlg_right_cx",
    "mlg_right_cz",
    "mlg_right_rx",
    "mlg_right_rz",
    "mlg_right_wheel_radius",
    "mlg_right_b1x", "mlg_right_b1z", "mlg_right_b2x", "mlg_right_b2z",
    "mlg_right_cdbx", "mlg_right_cdbz", "mlg_right_ddbx", "mlg_right_ddbz",
    "mlg_right_f1x", "mlg_right_f1z", "mlg_right_f2x", "mlg_right_f2z",
    "mlg_right_jdx", "mlg_right_jdz", "mlg_right_jex", "mlg_right_jez",
)


@dataclass
class _TrailingRuntime:
    p: TrailingArmParamsSI
    gas: GasSpring
    tab_pos: np.ndarray
    tab_sec: np.ndarray
    tyre_defl: np.ndarray
    tyre_load: np.ndarray
    mu_x: np.ndarray
    mu_y: np.ndarray
    state: TrailingArmLocalState
    entraxe_init: float
    lg_ab: float
    lg_rb: float
    dy_ca: float
    fast_time_scale: float
    integrator_mode: str
    r0: np.ndarray


def _init_trailing_runtime(p: TrailingArmParamsSI) -> _TrailingRuntime:
    from .geometry import deter_pos_bal_a, deter_pos_bal_r, rotate_about

    gas = GasSpring(p)
    tab_pos, tab_sec = build_section_table(p)
    tyre_defl, tyre_load = build_tyre_tables(p)

    B = p.B.astype(float).copy()
    A = p.A.astype(float).copy()
    C = p.C.astype(float).copy()
    R = p.R.astype(float).copy()

    entraxe_init = float(np.linalg.norm(C - A))
    lg_ab = math.hypot(B[0] - A[0], B[2] - A[2])
    lg_rb = math.hypot(B[0] - R[0], B[2] - R[2])
    lg_ra = math.hypot(A[0] - R[0], A[2] - R[2])

    S = R.copy()
    S[2] = R[2] - p.unload_radius
    A = rotate_about(A, S, p.pitch, p.roll)
    B = rotate_about(B, S, p.pitch, p.roll)
    C = rotate_about(C, S, p.pitch, p.roll)
    R = rotate_about(R, S, p.pitch, p.roll)
    S = R.copy()
    S[2] = R[2] - p.unload_radius

    d = 0.0
    pgtamp = p.Pinitbp
    pg = gas.pressure(d, pgtamp)
    for _ in range(100000):
        d -= 1.0e-8
        pg = gas.pressure(d, pgtamp)
        ftot = p.St * pg
        if abs(ftot) < 1.0:
            break

    entraxe = entraxe_init - d
    deter_pos_bal_a(A, B, C, entraxe, lg_ab)
    deter_pos_bal_r(R, A, B, lg_ra, lg_rb)
    th_ry = math.atan((R[0] - B[0]) / (R[2] - B[2]))
    th_ay = math.atan((A[0] - B[0]) / (A[2] - B[2]))

    fast_time_scale = 1.8 if p.damper_core_solver == "auto_fast" else 1.0
    integrator_mode = "euler" if p.damper_core_solver == "auto_fast" else p.integrator

    state = TrailingArmLocalState(
        A=A,
        B=B,
        C=C,
        R=R,
        S=S,
        accms=0.0,
        vitms=-p.vz,
        depms=0.0,
        ta_x=0.0,
        ta_y=0.0,
        ta_z=0.0,
        tb_x=0.0,
        tb_y=0.0,
        tb_z=0.0,
        tr_x=0.0,
        tr_y=0.0,
        tr_z=0.0,
        al_y=0.0,
        om_y=0.0,
        omega=0.0,
        alpha=0.0,
        vitx=0.0,
        depx=0.0,
        defl=0.0,
        delta_pc=0.0,
        delta_pd=0.0,
        qc_total=0.0,
        qc_bh=0.0,
        qc_leak=0.0,
        leak_ratio=0.0,
        re_leak=0.0,
        hyd_conv_err=0.0,
        hyd_conv_iter=0.0,
        pg_prev=pg,
        ftot=p.St * pg,
        v_prev=0.0,
        entraxe=entraxe,
        th_ay=th_ay,
        th_ry=th_ry,
        d=0.0,
        v=0.0,
    )

    return _TrailingRuntime(
        p=p,
        gas=gas,
        tab_pos=tab_pos,
        tab_sec=tab_sec,
        tyre_defl=tyre_defl,
        tyre_load=tyre_load,
        mu_x=p.mu_x,
        mu_y=p.mu_y,
        state=state,
        entraxe_init=entraxe_init,
        lg_ab=lg_ab,
        lg_rb=lg_rb,
        dy_ca=float(C[1] - A[1]),
        fast_time_scale=fast_time_scale,
        integrator_mode=integrator_mode,
        r0=state.R.copy(),
    )


def _mirror_trailing_params_y(p: TrailingArmParamsSI) -> TrailingArmParamsSI:
    def _my(v):
        return np.array([v[0], -v[1], v[2]], dtype=float)

    jambe = None
    if getattr(p, "jambe", None) is not None:
        jambe = {k: _my(v) for k, v in p.jambe.items()}
    return replace(
        p,
        B=_my(p.B), A=_my(p.A), C=_my(p.C), R=_my(p.R), S=_my(p.S),
        jambe=jambe,
    )


# --------------------------------------------------------------------------- #
#  Helpers cinématiques corps rigide (repère sol/avion), partagés par les slots
# --------------------------------------------------------------------------- #
def _rigid_station(cg: np.ndarray, cg_z_val: float, theta_val: float, station: np.ndarray) -> tuple[float, float]:
    cg_x_val = float(cg[0])
    cg_z_val_abs = float(cg[2] + cg_z_val)
    rel_x = float(station[0] - cg[0])
    rel_z = float(station[2] - cg[2])
    cos_t = math.cos(theta_val)
    sin_t = math.sin(theta_val)
    return (
        cg_x_val + rel_x * cos_t - rel_z * sin_t,
        cg_z_val_abs + rel_x * sin_t + rel_z * cos_t,
    )


def _off_world_to_body(off_x: float, off_z: float, theta_ref: float) -> tuple[float, float]:
    cos_t = math.cos(theta_ref)
    sin_t = math.sin(theta_ref)
    return (off_x * cos_t + off_z * sin_t, -off_x * sin_t + off_z * cos_t)


def _off_body_to_world(body_x: float, body_z: float, theta_val: float) -> tuple[float, float]:
    cos_t = math.cos(theta_val)
    sin_t = math.sin(theta_val)
    return (body_x * cos_t - body_z * sin_t, body_x * sin_t + body_z * cos_t)


# --------------------------------------------------------------------------- #
#  Abstraction de slot de train générique
# --------------------------------------------------------------------------- #
@dataclass
class InterfaceContribution:
    """Effort d'interface d'un train sur la structure avion, en repère sol.

    ``my`` est le couple transmis autour de l'axe de tangage (Y), non nul
    seulement pour une liaison **encastrement** (StraitStrut au point B) : il est
    injecté dans le PFD du corps en plus du moment ``r x F`` de l'effort. Pour une
    rotule/pivot (TrailingArm en B et C), ``my`` reste nul.

    ``mx``/``mz`` (composantes du couple hors plan) sont conservés pour
    diagnostic et ne sont pas injectés dans le PFD 2 DDL (heave + tangage)."""

    px: float
    pz: float
    fx: float
    fz: float
    mx: float = 0.0
    my: float = 0.0
    mz: float = 0.0


@dataclass
class SlotStepResult:
    contributions: list  # list[InterfaceContribution]
    fz_slot: float
    diag: dict
    geom: dict


class StraitStrutSlot:
    """Slot de train de type StraitStrut (interface = point B unique)."""

    def __init__(self, *, prefix, params, strut_geom, station, cg, vx, pitch_init, ground_z=0.0):
        self.prefix = prefix
        self.model_kind = "strait_strut"
        self.p = params
        self.cg = cg
        self.vx = vx
        self.ground_z = ground_z
        self.station = station
        self.unload_radius = float(params.unload_radius)
        self.x_offset = float(station[0] - cg[0])
        self.drag_brace = getattr(strut_geom, "drag_brace", None)  # ancrage §5b (None = encastré)
        self.strut_pitch = strut_geom.strut_pitch
        self.strut_roll = strut_geom.strut_roll
        self.seal_precomp_pa = strut_geom.seal_precomp_pa
        self.bague_guide = strut_geom.bague_guide
        self.bague_piston = strut_geom.bague_piston

        self.gas = GasSpring(params)
        self.tab_pos, self.tab_sec = build_section_table(params)
        self.tyre_defl, self.tyre_load = build_tyre_tables(params)
        R_sol_to_lg_init = _rot_sol_to_lg(self.strut_pitch - pitch_init, self.strut_roll)
        self.R_lg_to_sol_init = R_sol_to_lg_init.T
        self.state = _init_strait_strut_local_state(
            params,
            self.gas,
            R_sol_to_lg_init,
            self.R_lg_to_sol_init,
            h_pivot_z_m=strut_geom.h_pivot_z,
            h_guide_top_z_m=strut_geom.h_guide_top_z,
            h_guide_bot_z_m=strut_geom.h_guide_bot_z,
            r_offset_m=getattr(strut_geom, "r_offset", (0.0, 0.0)),
            b_offset_m=getattr(strut_geom, "b_offset", (0.0, 0.0)),
        )
        self.r0_sol = self.R_lg_to_sol_init @ self.state.ptR_lg.copy()
        # Renseignés par finalize_reference().
        self.station_z_ref = 0.0
        self.b_body = (0.0, 0.0)
        self.gt_body = (0.0, 0.0)
        self.gb_body = (0.0, 0.0)

        # --- Bilan énergétique par train (convention travail, cf. engine_strait_strut)
        # On EXCLUT la masse suspendue (= fuselage, comptée au niveau avion) :
        # réservoirs = tige (Mns) + roue (spin + spring-back), ressorts, dissipations.
        self._e = dict(gas=0.0, tyre=0.0, hyd=0.0, fric=0.0, fribag=0.0,
                       damp_x=0.0, slip=0.0, endstop=0.0, fwd=0.0, grav=0.0)
        self._e_started = False
        self._e_kin_init = 0.0

    def reference_bottom_z(self, pitch_init: float) -> float:
        _, station_z0 = _rigid_station(self.cg, 0.0, pitch_init, self.station)
        r_sol_0 = self.R_lg_to_sol_init @ self.state.ptR_lg
        rz0 = station_z0 + float(r_sol_0[2] - self.r0_sol[2])
        return rz0 - self.unload_radius

    def apply_ground_gap(self, gap: float) -> None:
        """No-op : la déflexion pneu du StraitStrut est calculée en repère sol
        (monde), donc déjà correcte quand la roue est en l'air (déflexion < 0)."""
        return None

    def finalize_reference(self, z_cg: float, pitch_init: float) -> None:
        _, self.station_z_ref = _rigid_station(self.cg, z_cg, pitch_init, self.station)
        b_sol_ref = self.R_lg_to_sol_init @ self.state.ptB_lg
        gt_sol_ref = self.R_lg_to_sol_init @ self.state.ptGt_lg
        gb_sol_ref = self.R_lg_to_sol_init @ self.state.ptGb_lg
        b_off = b_sol_ref - self.r0_sol
        gt_off = gt_sol_ref - self.r0_sol
        gb_off = gb_sol_ref - self.r0_sol
        self.b_body = _off_world_to_body(float(b_off[0]), float(b_off[2]), pitch_init)
        self.gt_body = _off_world_to_body(float(gt_off[0]), float(gt_off[2]), pitch_init)
        self.gb_body = _off_world_to_body(float(gb_off[0]), float(gb_off[2]), pitch_init)
        self.state.z_ms = 0.0

    def step(self, *, station_x, station_z, zsup, vsup, asup, theta, dt) -> SlotStepResult:
        p = self.p
        R_sol_to_lg_step = _rot_sol_to_lg(self.strut_pitch - theta, self.strut_roll)
        R_lg_to_sol_step = R_sol_to_lg_step.T

        st = self.state
        st.z_ms = zsup
        st.vz_ms = vsup
        v_ms_lg_vec = R_sol_to_lg_step @ np.array([0.0, 0.0, vsup])
        st.v_damper = -(float(v_ms_lg_vec[2]) - st.vz_mns_lg)
        damp = _strait_strut_resolve_damper_step(p, self.gas, self.tab_pos, self.tab_sec, st)
        pg = damp["pg"]
        pc = damp["pc"]
        pd = damp["pd"]
        st.delta_pc = damp["delta_pc"]
        st.delta_pd = damp["delta_pd"]
        st.pg_prev = pg
        b_off_x_step, b_off_z_step = _off_body_to_world(self.b_body[0], self.b_body[1], theta)
        bx_step = station_x + b_off_x_step
        bz_step = station_z + b_off_z_step

        pt_b_sol_now = R_lg_to_sol_step @ st.ptB_lg
        pt_r_sol_now = R_lg_to_sol_step @ st.ptR_lg
        br_sol_now = pt_r_sol_now - pt_b_sol_now
        rz_world_now = bz_step + float(br_sol_now[2])
        defl_world = p.unload_radius - (rz_world_now - self.ground_z)
        if defl_world <= 0.0:
            st.tyre_defl_val = 0.0
        else:
            st.tyre_defl_val = defl_world
        tyre_defl_curr = st.tyre_defl_val
        tyre_ftyre = max(0.0, f_tyre(st.tyre_defl_val, self.tyre_defl, self.tyre_load))
        ffrijoi = _ffrijoi_nlg(st.v_damper, pd, p, self.seal_precomp_pa)
        fx_spring_wheel = -p.kx * st.tyre_depx - p.cx * st.tyre_vx
        tr_sol = np.array([fx_spring_wheel, 0.0, tyre_ftyre])
        tr_lg = R_sol_to_lg_step @ tr_sol
        r_eff_v = r_eff(p.unload_radius, st.tyre_defl_val)
        slip = 0.0
        if abs(self.vx) > 1.0e-9:
            slip = (self.vx - st.tyre_omega * r_eff_v) / abs(self.vx)
        mu_v = mu(slip, p.mu_x, p.mu_y)
        fspin = mu_v * tyre_ftyre * math.copysign(1.0, slip) if tyre_ftyre > 0 else 0.0
        tyre_alpha = (fspin * r_eff_v) / p.wheel_inertia if tyre_ftyre > 0 else 0.0
        xgt, xgb = _bushing_loads(tr_lg, st.ptR_lg, st.ptGt_lg, st.ptGb_lg)
        ffribag = _ffribag_nlg(st.v_damper, xgt, xgb, p.Dt, self.bague_guide, self.bague_piston)
        fendstop = _endstop(st.d, p.course, smooth_len=p.endstop_smooth)
        ftot = p.Sc * pc - p.Sd * pd + p.Sbh * pg + ffrijoi + ffribag + fendstop
        st.ftot = ftot
        # Ancrage drag brace (§5b) : efforts B1/B2/bielle (repère jambe), si configuré.
        db_T = db_b1 = db_b2 = db_brace = None
        if self.drag_brace is not None:
            _db = _drag_brace_step(p.course, st, ftot, tr_lg, self.drag_brace)
            if _db is not None:
                db_T, db_b1, db_b2, db_brace = _db
        tb_lg = np.array([tr_lg[0], 0.0, ftot])
        tb_sol_raw = R_lg_to_sol_step @ tb_lg
        in_contact = tyre_ftyre > 1.0e-9
        tb_sol = tb_sol_raw if in_contact else np.zeros(3)
        ptB_sol = R_lg_to_sol_step @ st.ptB_lg
        ptR_sol_cur = R_lg_to_sol_step @ st.ptR_lg
        mom_B = np.cross(ptR_sol_cur - ptB_sol, tr_sol) if in_contact else np.zeros(3)

        self.state = _strait_strut_advance_local_state(
            p,
            st,
            R_sol_to_lg_step,
            R_lg_to_sol_step,
            support_acc_ms_z=asup,
            ftot=ftot,
            tyre_ftyre_i=tyre_ftyre,
            dt=dt,
            method=p.integrator,
            contact_axial=float(tr_lg[2]),
        )
        adv = self.state

        # --- Accumulation énergétique du train (mêmes formules que le moteur NLG
        # standalone, convention travail ; masse suspendue exclue → fuselage). ---
        mns = p.unsprung_mass
        cosb = float(R_lg_to_sol_step[2, 2])
        if not self._e_started:
            self._e_kin_init = 0.5 * mns * st.vz_mns_lg ** 2
            self._d_prev = max(0.0, st.d)
            self._defl_prev = st.tyre_defl_val
            self._zms_prev = st.z_ms
            self._omega_prev = st.tyre_omega
            self._e_started = True
        dd = max(0.0, st.d) - self._d_prev
        ddefl = st.tyre_defl_val - self._defl_prev
        e = self._e
        e["gas"] += float(damp["fgas"]) * dd
        e["endstop"] += fendstop * dd
        e["tyre"] += tyre_ftyre * ddefl
        e["hyd"] += float(damp["fhyd"]) * dd
        e["fric"] += ffrijoi * dd
        e["fribag"] += ffribag * dd
        e["damp_x"] += p.cx * st.tyre_vx ** 2 * dt
        dke_spin = 0.5 * p.wheel_inertia * (st.tyre_omega ** 2 - self._omega_prev ** 2)
        if abs(self.vx) > 1.0e-9:
            e["fwd"] += fspin * self.vx * dt
            e["slip"] += fspin * (self.vx - st.tyre_vx) * dt - dke_spin
        # Couplage moyeu (R se déplace horizontalement avec le glissement axial).
        e["slip"] += (-fx_spring_wheel) * st.v_damper * float(R_lg_to_sol_step[0, 2]) * dt
        # Gravité de la tige (Mns) seule — déplacement vertical absolu.
        rod_vert_disp = (st.z_ms - self._zms_prev) + cosb * dd
        e["grav"] += -mns * G * rod_vert_disp
        self._d_prev = max(0.0, st.d)
        self._defl_prev = st.tyre_defl_val
        self._zms_prev = st.z_ms
        self._omega_prev = st.tyre_omega
        e_kin_train = (0.5 * mns * (st.vz_ms ** 2 + st.v_damper ** 2
                                   + 2.0 * st.vz_ms * st.v_damper * cosb)
                       + 0.5 * p.wheel_inertia * st.tyre_omega ** 2
                       + 0.5 * p.wheelmass * st.tyre_vx ** 2)
        e_stock_train = e["gas"] + e["tyre"] + 0.5 * p.kx * st.tyre_depx ** 2 + e["endstop"]
        e_diss_train = e["hyd"] + e["fric"] + e["fribag"] + e["damp_x"] + e["slip"]

        fz_slot = float(tb_sol[2])
        # Signe horizontal corrigé : effort transmis à la cellule dans la même
        # convention que ``reaction_h`` et que le TrailingArm (MLG), cf. PFD
        # (docs/PFD_trains.md §5.3, §7.5). Sert au report ET à l'injection dans le
        # moment de tangage (le code historique injectait +tb_sol[0]).
        fx_cell = -float(tb_sol[0])
        contributions = [
            InterfaceContribution(
                px=bx_step,
                pz=bz_step,
                fx=fx_cell,
                fz=float(tb_sol[2]),
                mx=float(mom_B[0]),
                my=float(mom_B[1]),
                mz=float(mom_B[2]),
            )
        ]

        diag = {
            "stroke": max(0.0, adv.d),
            "velocity": adv.v_damper,
            "ftot": ftot,
            "fhyd": float(damp["fhyd"]),
            "ffrijoi": ffrijoi,
            "ffribag": ffribag,
            "fgas": float(damp["fgas"]),
            "pg": pg / 1.0e5,
            "pc": pc / 1.0e5,
            "pd": pd / 1.0e5,
            "delta_pc": adv.delta_pc / 1.0e5,
            "delta_pd": adv.delta_pd / 1.0e5,
            "hyd_qc_total": float(damp["qc_total"]),
            "hyd_qc_bh": float(damp["qc_bh"]),
            "hyd_qc_leak": float(damp["qc_leak"]),
            "hyd_leak_ratio": float(damp["leak_ratio"]),
            "hyd_re_leak": float(damp["re_leak"]),
            "hyd_conv_err": float(damp["hyd_conv_err"]),
            "hyd_conv_iter": float(damp["hyd_conv_iter"]),
            "secbh": float(damp["sec"]) * 1.0e6,
            "tyre_defl": tyre_defl_curr,
            "tyre_ftyre": tyre_ftyre,
            "tyre_mu": mu_v,
            "tyre_slip": slip,
            "tyre_omega": adv.tyre_omega,
            "tyre_alpha": tyre_alpha,
            "tr_x": -fx_spring_wheel,
            "reaction_h": -fx_spring_wheel,
            "reaction_v": tyre_ftyre,
            "xgt": xgt,
            "xgb": xgb,
            "accms": asup,
            "accmns": (-ftot + tyre_ftyre - p.unsprung_mass * G) / p.unsprung_mass,
            "vitmns": adv.vz_mns_lg,
            "depmns": adv.z_mns_lg,
            "tors_res_x": fx_cell,
            "tors_res_z": float(tb_sol[2]),
            "tors_res_norm": math.hypot(float(tb_sol[0]), float(tb_sol[2])),
            "torsb_fx": fx_cell,
            "torsb_fz": float(tb_sol[2]),
            "torsb_mx": float(mom_B[0]),
            "torsb_my": float(mom_B[1]),
            "torsb_mz": float(mom_B[2]),
            "e_kin": e_kin_train,
            "e_stock": e_stock_train,
            "e_diss": e_diss_train,
            "e_fwd": e["fwd"],
            "e_grav": e["grav"],
            "e_kin_init": self._e_kin_init,
        }
        if db_T is not None:
            diag.update({
                "db_brace_T": db_T,
                "db_b1_fx": float(db_b1[0]), "db_b1_fy": float(db_b1[1]), "db_b1_fz": float(db_b1[2]),
                "db_b2_fx": float(db_b2[0]), "db_b2_fy": float(db_b2[1]), "db_b2_fz": float(db_b2[2]),
                "db_brace_fx": float(db_brace[0]), "db_brace_fy": float(db_brace[1]), "db_brace_fz": float(db_brace[2]),
            })

        b_sol = R_lg_to_sol_step @ adv.ptB_lg
        gt_sol = R_lg_to_sol_step @ adv.ptGt_lg
        gb_sol = R_lg_to_sol_step @ adv.ptGb_lg
        r_sol = R_lg_to_sol_step @ adv.ptR_lg
        # Gb : bague basse sur le fût (corps fixe) → offset corps figé.
        gb_off_x, gb_off_z = _off_body_to_world(self.gb_body[0], self.gb_body[1], theta)
        # Gt : bague haute sur la TIGE → suit la position vive (comme R, relatif à B).
        bgt_sol_x = float(gt_sol[0] - b_sol[0])
        bgt_sol_z = float(gt_sol[2] - b_sol[2])
        br_sol_x = float(r_sol[0] - b_sol[0])
        br_sol_z = float(r_sol[2] - b_sol[2])
        geom = {
            "bx": bx_step,
            "bz": bz_step,
            "gtx": bx_step + bgt_sol_x,
            "gtz": bz_step + bgt_sol_z,
            "gbx": station_x + gb_off_x,
            "gbz": station_z + gb_off_z,
            "rx": bx_step + br_sol_x,
            "rz": bz_step + br_sol_z,
            "wheel_radius": p.unload_radius,
        }
        # Ancrage drag brace (§5b) : points solidaires du corps/structure, placés
        # rigidement par rapport à Gb (positions jambe rel. Gb → monde vue de côté).
        if self.drag_brace is not None:
            for key, rel in (("b1", self.drag_brace["B1"]), ("b2", self.drag_brace["B2"]),
                             ("cdb", self.drag_brace["C"]), ("ddb", self.drag_brace["D"])):
                disp = R_lg_to_sol_step @ rel
                geom[key + "x"] = geom["gbx"] + float(disp[0])
                geom[key + "z"] = geom["gbz"] + float(disp[2])

        return SlotStepResult(contributions=contributions, fz_slot=fz_slot, diag=diag, geom=geom)


class TrailingArmSlot:
    """Slot de train de type TrailingArm (interfaces = points B et C)."""

    def __init__(self, *, prefix, params, station, cg, vx, pitch_init, arm_mass=0.0):
        self.prefix = prefix
        self.model_kind = "trailing_arm"
        self.p = params  # exposé comme StraitStrutSlot (gestion sur-enfoncement)
        self.cg = cg
        self.station = station
        self.unload_radius = float(params.unload_radius)
        self.x_offset = float(station[0] - cg[0])
        self.arm_mass = float(arm_mass)   # masse balancier active (PFD §6.7) ; 0 = historique
        self.rt = _init_trailing_runtime(params)
        self.station_z_ref = 0.0
        self.b_body = (0.0, 0.0)
        self.c_body = (0.0, 0.0)
        self.vx = float(vx)

        # --- Bilan énergétique par train (convention travail, cf. engine.py) ---
        # Masse suspendue exclue (= fuselage). Réservoirs = balancier (rotation),
        # roue (spin + spring-back). Trapézoïdal si intégrateur rk4, comme engine.py.
        self._e = dict(gas=0.0, tyre=0.0, hyd=0.0, fric=0.0, damp_x=0.0,
                       slip=0.0, endstop=0.0, fwd=0.0)
        self._e_started = False
        self._e_kin_init = 0.0

    def reference_bottom_z(self, pitch_init: float) -> float:
        _, station_z0 = _rigid_station(self.cg, 0.0, pitch_init, self.station)
        rz0 = station_z0 + float(self.rt.state.R[2] - self.rt.r0[2])
        return rz0 - self.unload_radius

    def apply_ground_gap(self, gap: float) -> None:
        """Décale le sol local de la jambe vers le bas de ``gap`` (hauteur de la
        roue au-dessus du sol réel à l'équilibre initial, due à l'assiette).

        Le noyau TrailingArm calcule la déflexion pneu contre un sol local fixé
        à l'initialisation (déflexion nulle au départ). Dans l'assemblage avion,
        un train soulevé par l'assiette doit rester en l'air tant que sa roue
        n'a pas descendu de ``gap`` ; on abaisse donc ``S`` d'autant.
        """
        if gap:
            self.rt.state.S[2] -= float(gap)

    def finalize_reference(self, z_cg: float, pitch_init: float) -> None:
        _, self.station_z_ref = _rigid_station(self.cg, z_cg, pitch_init, self.station)
        b_off = self.rt.state.B - self.rt.r0
        c_off = self.rt.state.C - self.rt.r0
        self.b_body = _off_world_to_body(float(b_off[0]), float(b_off[2]), pitch_init)
        self.c_body = _off_world_to_body(float(c_off[0]), float(c_off[2]), pitch_init)
        self.rt.state.depms = 0.0

    def step(self, *, station_x, station_z, zsup, vsup, asup, theta, dt) -> SlotStepResult:
        rt = self.rt
        st = rt.state

        # --- Balancier corps rigide (PFD §6.7) : accélération angulaire (6b) -----
        #     imposée au noyau via al_y_override (B décalé du support, comme
        #     l'historique). arm_mass = 0 ⇒ override None ⇒ comportement inchangé.
        al_y_override = None
        if self.arm_mass > 0.0:
            B_shift = st.B.copy()
            B_shift[2] += zsup - st.depms
            Gp = 0.5 * (B_shift + st.R)
            I_G = rt.p.jyy - self.arm_mass * ((Gp[0] - B_shift[0]) ** 2 + (Gp[2] - B_shift[2]) ** 2)
            TA = np.array([st.ta_x, st.ta_y, st.ta_z])
            TR = np.array([st.tr_x, st.tr_y, st.tr_z])
            TB = np.array([st.tb_x, st.tb_y, st.tb_z])
            moment_y = 0.0
            for P, T in ((st.A, TA), (st.R, TR), (B_shift, TB)):
                r = P - Gp
                moment_y += r[2] * T[0] - r[0] * T[2]
            al_y_override = moment_y / I_G

        step = _trailing_arm_local_step(
            rt.p,
            rt.gas,
            rt.tab_pos,
            rt.tab_sec,
            rt.tyre_defl,
            rt.tyre_load,
            rt.mu_x,
            rt.mu_y,
            rt.state,
            support_dz=zsup - rt.state.depms,
            support_vitms=vsup,
            support_accms=asup,
            entraxe_init=rt.entraxe_init,
            lg_ab=rt.lg_ab,
            lg_rb=rt.lg_rb,
            dy_ca=rt.dy_ca,
            fast_time_scale=rt.fast_time_scale,
            integrator_mode=rt.integrator_mode,
            It=dt * rt.fast_time_scale,
            al_y_override=al_y_override,
        )
        state = rt.state

        # --- Effort pivot rigide (6a) : T_B = m'·a_G' − T_A − T_R − P' ----------
        if self.arm_mass > 0.0:
            Gp = 0.5 * (state.B + state.R)
            rBG = Gp - state.B
            a_G = (np.array([0.0, 0.0, asup])
                   + al_y_override * np.array([rBG[2], 0.0, -rBG[0]])
                   - state.om_y ** 2 * rBG)
            TA = np.array([state.ta_x, state.ta_y, state.ta_z])
            TR = np.array([state.tr_x, state.tr_y, state.tr_z])
            TB = self.arm_mass * a_G - TA - TR - np.array([0.0, 0.0, -self.arm_mass * G])
            state.tb_x, state.tb_y, state.tb_z = float(TB[0]), float(TB[1]), float(TB[2])
            step = dict(step)
            step["fb_x"], step["fb_z"] = float(-TB[0]), float(-TB[2])

        b_off_x, b_off_z = _off_body_to_world(self.b_body[0], self.b_body[1], theta)
        c_off_x, c_off_z = _off_body_to_world(self.c_body[0], self.c_body[1], theta)
        bx = station_x + b_off_x
        bz = station_z + b_off_z
        cx = station_x + c_off_x
        cz = station_z + c_off_z

        fb_x = float(step["fb_x"])
        fb_z = float(step["fb_z"])
        fc_x = float(step["fc_x"])
        fc_z = float(step["fc_z"])

        # Ancrage « jambe + bielle » (§6b) : efforts F1/F2/bielle, si configuré.
        jb_T = jb_f1 = jb_f2 = jb_brace = None
        if getattr(rt.p, "jambe", None) is not None:
            _jb = _jambe_brace_step(
                [fb_x, float(step["fb_y"]), fb_z],
                [float(step["mb_x"]), 0.0, float(step["mb_z"])],
                [fc_x, float(step["fc_y"]), fc_z],
                rt.p.jambe, rt.p.pitch, rt.p.roll,
            )
            if _jb is not None:
                jb_T, jb_f1, jb_f2, jb_brace = _jb

        contributions = [
            InterfaceContribution(
                px=bx, pz=bz, fx=fb_x, fz=fb_z, mx=float(step["mb_x"]), mz=float(step["mb_z"])
            ),
            InterfaceContribution(px=cx, pz=cz, fx=fc_x, fz=fc_z),
        ]
        fz_slot = fb_z + fc_z

        # --- Accumulation énergétique du train (mêmes formules que le moteur MLG
        # engine.py, convention travail ; masse suspendue exclue → fuselage). ---
        pe = rt.p
        It = dt * rt.fast_time_scale
        rk4 = (getattr(pe, "integrator", "rk4") == "rk4")
        fgas_e = float(step["fgas"]); fhyd_e = float(step["fhyd"])
        ffrijoi_e = float(step["ffrijoi"]); ftyre_e = float(step["ftyre"])
        fspin_e = float(step["fspin"])
        d_e = max(0.0, state.d); defl_e = max(0.0, state.defl)
        endstop_cur = _endstop(state.d, pe.course, smooth_len=pe.endstop_smooth)
        omega_e = state.omega; vitx_e = state.vitx; depx_e = state.depx
        tr_x_e = state.tr_x; rx_e = float(state.R[0]); om_y_e = state.om_y
        e = self._e
        if not self._e_started:
            self._e_kin_init = 0.0  # balancier + roue au repos au départ
            self._d_prev = d_e; self._defl_prev = defl_e
            self._endstop_prev = endstop_cur; self._fgas_prev = fgas_e
            self._fhyd_prev = fhyd_e; self._ffrijoi_prev = ffrijoi_e
            self._ftyre_prev = ftyre_e; self._fspin_prev = fspin_e
            self._tr_x_prev = tr_x_e; self._vitx_prev = vitx_e
            self._omega_prev = omega_e; self._rx_prev = rx_e
            self._e_started = True
        dd = d_e - self._d_prev
        ddefl = defl_e - self._defl_prev
        if rk4:
            e["gas"] += 0.5 * (self._fgas_prev + fgas_e) * dd
            e["endstop"] += 0.5 * (self._endstop_prev + endstop_cur) * dd
            e["tyre"] += 0.5 * (self._ftyre_prev + ftyre_e) * ddefl
            e["hyd"] += 0.5 * (self._fhyd_prev + fhyd_e) * dd
            e["fric"] += 0.5 * (self._ffrijoi_prev + ffrijoi_e) * dd
            e["damp_x"] += 0.5 * pe.cx * (self._vitx_prev ** 2 + vitx_e ** 2) * It
        else:
            e["gas"] += fgas_e * dd
            e["endstop"] += endstop_cur * dd
            e["tyre"] += ftyre_e * ddefl
            e["hyd"] += fhyd_e * dd
            e["fric"] += ffrijoi_e * dd
            e["damp_x"] += pe.cx * vitx_e ** 2 * It
        vr_x = (rx_e - self._rx_prev) / It
        dke_spin = 0.5 * pe.wheel_inertia * (omega_e ** 2 - self._omega_prev ** 2)
        if abs(self.vx) > 1.0e-9:
            if rk4:
                fspin_avg = 0.5 * (self._fspin_prev + fspin_e)
                tr_x_avg = 0.5 * (self._tr_x_prev + tr_x_e)
                vitx_avg = 0.5 * (self._vitx_prev + vitx_e)
                e["fwd"] += fspin_avg * self.vx * It
                e["slip"] += fspin_avg * (self.vx - vitx_avg) * It - dke_spin - tr_x_avg * vr_x * It
            else:
                e["fwd"] += fspin_e * self.vx * It
                e["slip"] += fspin_e * (self.vx - vitx_e) * It - dke_spin - tr_x_e * vr_x * It
        self._d_prev = d_e; self._defl_prev = defl_e
        self._endstop_prev = endstop_cur; self._fgas_prev = fgas_e
        self._fhyd_prev = fhyd_e; self._ffrijoi_prev = ffrijoi_e
        self._ftyre_prev = ftyre_e; self._fspin_prev = fspin_e
        self._tr_x_prev = tr_x_e; self._vitx_prev = vitx_e
        self._omega_prev = omega_e; self._rx_prev = rx_e
        e_kin_train = (0.5 * pe.jyy * om_y_e ** 2
                       + 0.5 * pe.wheel_inertia * omega_e ** 2
                       + 0.5 * pe.wheelmass * vitx_e ** 2)
        e_stock_train = e["gas"] + e["tyre"] + 0.5 * pe.kx * depx_e ** 2 + e["endstop"]
        e_diss_train = e["hyd"] + e["fric"] + e["damp_x"] + e["slip"]

        diag = {
            "stroke": max(0.0, state.d),
            "velocity": state.v,
            "ftot": state.ftot,
            "fhyd": float(step["fhyd"]),
            "ffrijoi": float(step["ffrijoi"]),
            "fgas": float(step["fgas"]),
            "pg": float(step["pg"]) / 1.0e5,
            "pc": float(step["pc"]) / 1.0e5,
            "pd": float(step["pd"]) / 1.0e5,
            "delta_pc": state.delta_pc / 1.0e5,
            "delta_pd": state.delta_pd / 1.0e5,
            "hyd_qc_total": state.qc_total,
            "hyd_qc_bh": state.qc_bh,
            "hyd_qc_leak": state.qc_leak,
            "hyd_leak_ratio": state.leak_ratio,
            "hyd_re_leak": state.re_leak,
            "hyd_conv_err": state.hyd_conv_err,
            "hyd_conv_iter": state.hyd_conv_iter,
            "secbh": state.sec * 1.0e6,
            "tyre_defl": max(0.0, state.defl),
            "tyre_ftyre": float(step["ftyre"]),
            "tyre_mu": float(step["mu_val"]),
            "tyre_slip": float(step["slip"]),
            "tyre_omega": state.omega,
            "tyre_alpha": state.alpha,
            "fx": float(step["fb_x"] + step["fc_x"]),
            "reaction_h": float(step["fb_x"] + step["fc_x"]),
            "reaction_v": float(step["ftyre"]),
            "accms": asup,
            "tors_res_x": float(step["res_x"]),
            "tors_res_z": float(step["res_z"]),
            "tors_res_norm": float(step["res_norm"]),
            "torsc_fx": float(step["fc_x"]),
            "torsc_fz": float(step["fc_z"]),
            "torsb_fx": float(step["fb_x"]),
            "torsb_fz": float(step["fb_z"]),
            "torsb_mx": float(step["mb_x"]),
            "torsb_my": 0.0,  # B = pivot autour de Y -> aucun couple de tangage
            "torsb_mz": float(step["mb_z"]),
            "e_kin": e_kin_train,
            "e_stock": e_stock_train,
            "e_diss": e_diss_train,
            "e_fwd": e["fwd"],
            "e_grav": 0.0,  # masse suspendue exclue (fuselage) ; tige massless
            "e_kin_init": self._e_kin_init,
        }
        if jb_T is not None:
            diag.update({
                "db_brace_T": jb_T,
                "db_f1_fx": float(jb_f1[0]), "db_f1_fy": float(jb_f1[1]), "db_f1_fz": float(jb_f1[2]),
                "db_f2_fx": float(jb_f2[0]), "db_f2_fy": float(jb_f2[1]), "db_f2_fz": float(jb_f2[2]),
                "db_brace_fx": float(jb_brace[0]), "db_brace_fy": float(jb_brace[1]), "db_brace_fz": float(jb_brace[2]),
            })

        a_dx = float(state.A[0] - state.B[0])
        a_dz = float(state.A[2] - state.B[2])
        r_dx = float(state.R[0] - state.B[0])
        r_dz = float(state.R[2] - state.B[2])
        geom = {
            "ax": bx + a_dx,
            "az": bz + a_dz,
            "bx": bx,
            "bz": bz,
            "cx": cx,
            "cz": cz,
            "rx": bx + r_dx,
            "rz": bz + r_dz,
            "wheel_radius": rt.p.unload_radius,
        }
        # Ancrage « jambe + bielle » (§6b) : points solidaires de la structure,
        # placés rigidement par rapport à B (offsets repère corps → monde).
        if getattr(rt.p, "jambe", None) is not None:
            jb = rt.p.jambe
            B0 = jb["B"]
            for key, pt in (("f1", jb["F1"]), ("f2", jb["F2"]), ("jd", jb["Dbr"]), ("je", jb["Ebr"])):
                ox, oz = _off_body_to_world(float(pt[0] - B0[0]), float(pt[2] - B0[2]), theta)
                geom[key + "x"] = bx + ox
                geom[key + "z"] = bz + oz

        return SlotStepResult(contributions=contributions, fz_slot=fz_slot, diag=diag, geom=geom)


class LeafSpringSlot:
    """Slot « Train à lame » (leaf spring, PFD §6c) : ressort vertical (k) +
    amortisseur visqueux (c) entre l'encastrement B (structure) et la roue R.
    Interface avec la cellule = **encastrement** en B (effort + moment de tangage),
    comme le StraitStrut."""

    def __init__(self, *, prefix, params, leaf_geom, station, cg, vx, pitch_init, ground_z=0.0):
        self.prefix = prefix
        self.model_kind = "leaf_spring"
        self.p = params
        self.cg = cg
        self.vx = vx
        self.ground_z = ground_z
        self.station = station
        self.unload_radius = float(params.unload_radius)
        self.x_offset = float(station[0] - cg[0])
        self.k_leaf = float(leaf_geom.k_leaf)
        self.c_leaf = float(leaf_geom.c_leaf)
        # Offset géométrique de B par rapport à R (= station), repère avion (m).
        self._b_off_world = np.asarray(leaf_geom.B, float) - np.asarray(leaf_geom.R, float)
        self.tyre_defl_tbl, self.tyre_load_tbl = build_tyre_tables(params)
        # État roue (masse non suspendue).
        self.z_mns = 0.0
        self.vz_mns = -float(params.vz)
        self.tyre_omega = 0.0
        self.tyre_vx = 0.0
        self.tyre_depx = 0.0
        self.tyre_defl_val = 0.0
        self.d = 0.0
        self.v_damper = 0.0
        self.station_z_ref = 0.0
        self.rz_ref = 0.0
        self.b_body = (0.0, 0.0)
        self._e = dict(damp=0.0, damp_x=0.0, slip=0.0, tyre=0.0, fwd=0.0, grav=0.0)
        self._e_started = False
        self._e_kin_init = 0.0

    def reference_bottom_z(self, pitch_init):
        _, station_z0 = _rigid_station(self.cg, 0.0, pitch_init, self.station)
        return station_z0 - self.unload_radius

    def apply_ground_gap(self, gap):
        # Hauteur de roue encodée par station_z_ref (déflexion calculée en monde).
        return None

    def finalize_reference(self, z_cg, pitch_init):
        _, self.station_z_ref = _rigid_station(self.cg, z_cg, pitch_init, self.station)
        self.rz_ref = self.station_z_ref  # roue R au niveau de sa station
        self.b_body = _off_world_to_body(
            float(self._b_off_world[0]), float(self._b_off_world[2]), pitch_init
        )

    def step(self, *, station_x, station_z, zsup, vsup, asup, theta, dt):
        p = self.p
        mns = p.unsprung_mass
        # Position de l'encastrement B (structure) dans le monde.
        b_off_x, b_off_z = _off_body_to_world(self.b_body[0], self.b_body[1], theta)
        bx_step = station_x + b_off_x
        bz_step = station_z + b_off_z
        # Roue R : verticale = ref + déplacement propre ; horizontale = station.
        rz_world = self.rz_ref + self.z_mns
        rx_world = station_x
        # Compression de lame d et vitesse ḋ (rapprochement vertical B↔R).
        self.d = self.z_mns - zsup
        self.v_damper = self.vz_mns - vsup
        ftot, f_spring, f_damp = leaf_spring_step(self.d, self.v_damper, self.k_leaf, self.c_leaf)

        # Pneu : effort vertical, spin-up, spring-back.
        defl_world = p.unload_radius - (rz_world - self.ground_z)
        self.tyre_defl_val = defl_world if defl_world > 0.0 else 0.0
        tyre_ftyre = max(0.0, f_tyre(self.tyre_defl_val, self.tyre_defl_tbl, self.tyre_load_tbl))
        r_eff_v = r_eff(p.unload_radius, self.tyre_defl_val)
        slip = 0.0
        if abs(self.vx) > 1.0e-9:
            slip = (self.vx - self.tyre_omega * r_eff_v) / abs(self.vx)
        mu_v = mu(slip, p.mu_x, p.mu_y)
        fspin = mu_v * tyre_ftyre * math.copysign(1.0, slip) if tyre_ftyre > 0 else 0.0
        tyre_alpha = (fspin * r_eff_v) / p.wheel_inertia if tyre_ftyre > 0 else 0.0
        fx_spring_wheel = -p.kx * self.tyre_depx - p.cx * self.tyre_vx
        acc_tyre_x = (fx_spring_wheel + fspin) / p.wheelmass
        tr_sol = np.array([fx_spring_wheel, 0.0, tyre_ftyre])

        # Torseur d'encastrement transmis à la cellule en B (3D complet : BR × tr_sol).
        fx_cell = -float(fx_spring_wheel)
        fz_cell = float(ftot)
        br_x = rx_world - bx_step
        br_z = rz_world - bz_step
        br_y = -float(self._b_off_world[1])   # = R_y − B_y (figé, hors plan X-Z)
        mom_B = np.cross(np.array([br_x, br_y, br_z]), tr_sol)
        mom_B_y = float(mom_B[1])             # flexion de tangage (autour de Y)
        fz_slot = fz_cell

        # --- Énergie (exclut la masse suspendue = fuselage) --------------- #
        if not self._e_started:
            self._e_kin_init = 0.5 * mns * self.vz_mns ** 2
            self._d_prev = self.d
            self._defl_prev = self.tyre_defl_val
            self._zmns_prev = self.z_mns
            self._omega_prev = self.tyre_omega
            self._e_started = True
        dd = self.d - self._d_prev
        ddefl = self.tyre_defl_val - self._defl_prev
        e = self._e
        e["tyre"] += tyre_ftyre * ddefl
        e["damp"] += f_damp * dd
        e["damp_x"] += p.cx * self.tyre_vx ** 2 * dt
        dke_spin = 0.5 * p.wheel_inertia * (self.tyre_omega ** 2 - self._omega_prev ** 2)
        if abs(self.vx) > 1.0e-9:
            e["fwd"] += fspin * self.vx * dt
            e["slip"] += fspin * (self.vx - self.tyre_vx) * dt - dke_spin
        e["grav"] += -mns * G * (self.z_mns - self._zmns_prev)
        e_spring = 0.5 * self.k_leaf * self.d ** 2
        e_kin_train = (0.5 * mns * self.vz_mns ** 2
                       + 0.5 * p.wheel_inertia * self.tyre_omega ** 2
                       + 0.5 * p.wheelmass * self.tyre_vx ** 2)
        e_stock_train = e_spring + e["tyre"] + 0.5 * p.kx * self.tyre_depx ** 2
        e_diss_train = e["damp"] + e["damp_x"] + e["slip"]
        self._d_prev = self.d
        self._defl_prev = self.tyre_defl_val
        self._zmns_prev = self.z_mns
        self._omega_prev = self.tyre_omega

        contributions = [InterfaceContribution(
            px=bx_step, pz=bz_step, fx=fx_cell, fz=fz_cell,
            mx=float(mom_B[0]), my=mom_B_y, mz=float(mom_B[2]),
        )]
        diag = {
            "stroke": self.d,
            "velocity": self.v_damper,
            "ftot": ftot,
            "tyre_defl": self.tyre_defl_val,
            "tyre_ftyre": tyre_ftyre,
            "tyre_mu": mu_v,
            "tyre_slip": slip,
            "tyre_omega": self.tyre_omega,
            "tyre_alpha": tyre_alpha,
            "tr_x": -fx_spring_wheel,
            "reaction_h": -fx_spring_wheel,
            "reaction_v": tyre_ftyre,
            "accms": asup,
            "accmns": (-ftot + tyre_ftyre - mns * G) / mns,
            "vitmns": self.vz_mns,
            "depmns": self.z_mns,
            "tors_res_x": fx_cell,
            "tors_res_z": fz_cell,
            "tors_res_norm": math.hypot(fx_cell, fz_cell),
            "torsb_fx": fx_cell,
            "torsb_fz": fz_cell,
            "torsb_mx": float(mom_B[0]),
            "torsb_my": mom_B_y,
            "torsb_mz": float(mom_B[2]),
            "e_kin": e_kin_train,
            "e_stock": e_stock_train,
            "e_diss": e_diss_train,
            "e_fwd": e["fwd"],
            "e_grav": e["grav"],
            "e_kin_init": self._e_kin_init,
        }
        geom = {
            "bx": bx_step, "bz": bz_step,
            "gtx": bx_step, "gtz": bz_step,   # pas de bagues : Gt/Gb confondus avec B
            "gbx": bx_step, "gbz": bz_step,
            "rx": rx_world, "rz": rz_world,
            "wheel_radius": p.unload_radius,
        }

        # --- Intégration de la roue i → i+1 -------------------------------- #
        acc_mns = (-ftot + tyre_ftyre - mns * G) / mns
        self.z_mns, self.vz_mns = _integrate_const_acc(self.z_mns, self.vz_mns, acc_mns, dt, p.integrator)
        self.tyre_omega = self.tyre_omega + tyre_alpha * dt
        old_vx = self.tyre_vx
        self.tyre_vx = self.tyre_vx + acc_tyre_x * dt
        self.tyre_depx = self.tyre_depx + old_vx * dt

        return SlotStepResult(contributions=contributions, fz_slot=fz_slot, diag=diag, geom=geom)


def _build_slot(prefix, model_kind, params, strut_geom, station, cg, vx, pitch_init, arm_mass=0.0,
                leaf_geom=None):
    """Construit le slot adapté au type de train choisi pour la position."""
    if model_kind == "leaf_spring":
        if leaf_geom is None:
            from .inputs import _leaf_geom_si
            leaf_geom = _leaf_geom_si(params)
        return LeafSpringSlot(
            prefix=prefix, params=params, leaf_geom=leaf_geom,
            station=station, cg=cg, vx=vx, pitch_init=pitch_init,
        )
    if model_kind in ("strait_strut", "strait_strut_drag_brace"):
        if strut_geom is None:
            strut_geom = _strut_geom_si(params)
        return StraitStrutSlot(
            prefix=prefix,
            params=params,
            strut_geom=strut_geom,
            station=station,
            cg=cg,
            vx=vx,
            pitch_init=pitch_init,
        )
    return TrailingArmSlot(
        prefix=prefix, params=params, station=station, cg=cg, vx=vx,
        pitch_init=pitch_init, arm_mass=arm_mass,
    )


def run_aircraft(
    p: AircraftParamsSI,
    progress_callback: callable | None = None,
    *,
    mlg_arm_mass: float = 0.0,
) -> EngineOutput:
    dt = p.it
    n_steps = max(1, round(p.temps_simu / dt))
    n_out = n_steps + 1

    # Type de train par position (slot générique). Le slot droit reçoit des
    # paramètres miroir en Y lorsqu'il s'agit d'un TrailingArm.
    mlg_r_leaf = None
    if p.mlg_model_kind == "leaf_spring":
        mlg_r_params = p.mlg
        mlg_r_strut = None
        mlg_r_leaf = (
            replace(p.mlg_leaf, B=p.mlg_leaf.B * np.array([1.0, -1.0, 1.0]),
                    R=p.mlg_leaf.R * np.array([1.0, -1.0, 1.0]))
            if p.mlg_leaf is not None else None
        )
    elif p.mlg_model_kind in ("trailing_arm", "trailing_arm_drag_brace"):
        mlg_r_params = _mirror_trailing_params_y(p.mlg)
        mlg_r_strut = p.mlg_strut
    else:
        # StraitStrut au MLG : la géométrie de jambe est portée par le conteneur
        # strut ; on reflète le roll de jambe pour le train droit.
        mlg_r_params = p.mlg
        mlg_r_strut = (
            replace(p.mlg_strut, strut_roll=-p.mlg_strut.strut_roll)
            if p.mlg_strut is not None
            else None
        )

    nlg_slot = _build_slot(
        "nlg", p.nlg_model_kind, p.nlg, p.nlg_strut, p.nlg_station, p.cg, p.vx, p.pitch,
        leaf_geom=p.nlg_leaf,
    )
    mlg_l_slot = _build_slot(
        "mlg_left", p.mlg_model_kind, p.mlg, p.mlg_strut, p.mlg_left_station, p.cg, p.vx, p.pitch,
        arm_mass=mlg_arm_mass, leaf_geom=p.mlg_leaf,
    )
    mlg_r_slot = _build_slot(
        "mlg_right", p.mlg_model_kind, mlg_r_params, mlg_r_strut, p.mlg_right_station, p.cg, p.vx, p.pitch,
        arm_mass=mlg_arm_mass, leaf_geom=mlg_r_leaf,
    )
    slots = [nlg_slot, mlg_l_slot, mlg_r_slot]

    # Sol global (repère sol absolu) : z = 0.
    ground_z = 0.0

    # Position initiale avion imposée : roue la plus basse tangente au sol,
    # après équilibrage local de chaque train.
    bottoms = [slot.reference_bottom_z(p.pitch) for slot in slots]
    z_bottom_ref = min(bottoms)
    z_cg = -z_bottom_ref
    for slot, bottom in zip(slots, bottoms):
        slot.finalize_reference(z_cg, p.pitch)
        # Hauteur de la roue au-dessus du sol à l'équilibre initial (>= 0) : le
        # train le plus bas est tangent (gap 0), les autres sont en l'air.
        slot.apply_ground_gap(bottom - z_bottom_ref)

    vz_cg = -p.vz
    az_cg = 0.0
    theta = p.pitch
    theta_dot = p.pitch_rate
    theta_ddot = 0.0

    out = {k: np.zeros(n_out) for k in OUTPUT_COLUMNS_AC}
    geom = {k: np.zeros(n_out) for k in GEOMETRY_KEYS_AC}

    _GEAR_LABELS = {"nlg": "NLG", "mlg_left": "MLG gauche", "mlg_right": "MLG droite"}
    bottomed = None  # (i_fail, slot, exc) si un train atteint sa butée de compression

    # --- Bilan énergétique avion (3e calcul) : somme des bilans par train (convention
    # travail) + cinétique fuselage (heave + tangage) + gravité fuselage. Cf.
    # docs/Bilan_energetique.md §6. Réservoirs internes des trains = ressorts +
    # pièces en mouvement (hors masse suspendue, portée par le fuselage).
    weight_eff = p.masse * G * (1.0 - p.lift)
    e_grav_fuse = 0.0
    z_cg_prev = z_cg
    e_kin_init_total = None  # capturé au pas 0

    for i in range(n_out):
        t = i * dt

        # Résolution locale de chaque slot de train sous cinématique support
        # imposée (ordre [NLG, MLG gauche, MLG droite] préservé).
        results = []
        try:
            for slot in slots:
                station_x, station_z = _rigid_station(p.cg, z_cg, theta, slot.station)
                zsup = station_z - slot.station_z_ref
                vsup = vz_cg - slot.x_offset * theta_dot
                asup = az_cg - slot.x_offset * theta_ddot
                res = slot.step(
                    station_x=station_x,
                    station_z=station_z,
                    zsup=zsup,
                    vsup=vsup,
                    asup=asup,
                    theta=theta,
                    dt=dt,
                )
                results.append((slot, res))
        except SimError as exc:
            if exc.code in OVERSTROKE_CODES:
                bottomed = (i, slot, exc)
                break
            raise

        # PFD structure avion (2 DDL : translation Z + tangage). On isole le
        # fuselage : efforts entrants = poids+lift au CG et efforts d'interface
        # de chaque train. Le moment de tangage somme, pour chaque point
        # d'interface, le moment de l'effort (r x F) ET, pour une liaison
        # encastrement (StraitStrut en B), le couple de flexion transmis (c.my,
        # autour de l'axe de tangage Y). Convention : mpitch = -M_y standard, donc
        # le couple s'ajoute en -c.my, cohérent avec le terme d'effort.
        fz_total = sum(res.fz_slot for _, res in results)
        cg_x = float(p.cg[0])
        cg_z = float(p.cg[2] + z_cg)
        mpitch = 0.0
        for _, res in results:
            for c in res.contributions:
                mpitch += (c.px - cg_x) * c.fz - (c.pz - cg_z) * c.fx - c.my

        az_cg = (fz_total - weight_eff) / p.masse
        theta_ddot = mpitch / p.jyy

        # --- Bilan énergétique avion (état courant, avant intégration) ----------
        e_kin_fuse = 0.5 * p.masse * vz_cg ** 2 + 0.5 * p.jyy * theta_dot ** 2
        e_grav_fuse += -weight_eff * (z_cg - z_cg_prev)
        z_cg_prev = z_cg
        e_kin_tr = sum(res.diag.get("e_kin", 0.0) for _, res in results)
        e_stock_tr = sum(res.diag.get("e_stock", 0.0) for _, res in results)
        e_diss_tr = sum(res.diag.get("e_diss", 0.0) for _, res in results)
        e_fwd_tr = sum(res.diag.get("e_fwd", 0.0) for _, res in results)
        e_grav_tr = sum(res.diag.get("e_grav", 0.0) for _, res in results)
        e_kin_init_tr = sum(res.diag.get("e_kin_init", 0.0) for _, res in results)
        if e_kin_init_total is None:
            e_kin_init_total = e_kin_fuse + e_kin_init_tr
        e_input = e_kin_init_total + e_grav_fuse + e_grav_tr + e_fwd_tr
        e_cin = e_kin_fuse + e_kin_tr
        e_residual = e_input - (e_cin + e_stock_tr + e_diss_tr)
        out["aircraft_e_kin_fuse"][i] = e_kin_fuse
        out["aircraft_e_kin_trains"][i] = e_kin_tr
        out["aircraft_e_stock"][i] = e_stock_tr
        out["aircraft_e_diss"][i] = e_diss_tr
        out["aircraft_e_input"][i] = e_input
        out["aircraft_e_residual"][i] = e_residual

        z_cg, vz_cg = _integrate_const_acc(z_cg, vz_cg, az_cg, dt, p.integrator)
        theta, theta_dot = _integrate_const_acc(theta, theta_dot, theta_ddot, dt, p.integrator)

        out["temps"][i] = t
        out["aircraft_cg_z"][i] = z_cg
        out["aircraft_cg_vz"][i] = vz_cg
        out["aircraft_cg_az"][i] = az_cg
        out["aircraft_pitch"][i] = theta
        out["aircraft_pitch_rate"][i] = theta_dot
        out["aircraft_pitch_acc"][i] = theta_ddot
        out["aircraft_fz_total"][i] = fz_total
        out["aircraft_mx_total"][i] = mpitch

        geom["cg_x"][i] = cg_x
        geom["cg_z"][i] = cg_z
        geom["ground_z"][i] = ground_z

        # Sorties par train : chaque slot fournit les diagnostics/géométrie
        # propres à son type. Les colonnes non pertinentes (type opposé)
        # restent à zéro.
        for slot, res in results:
            fz_col = out.get("aircraft_fz_" + slot.prefix)
            if fz_col is not None:
                fz_col[i] = res.fz_slot
            for suffix, val in res.diag.items():
                col = out.get(slot.prefix + "_" + suffix)
                if col is not None:
                    col[i] = val
            for suffix, val in res.geom.items():
                gcol = geom.get(slot.prefix + "_" + suffix)
                if gcol is not None:
                    gcol[i] = val

        if progress_callback is not None and (i % 10 == 0 or i == n_steps):
            progress_callback(i, n_steps)

    warnings: list[SimError] = []
    if bottomed is not None:
        i_fail, slot_f, exc = bottomed
        # La butée raide peut diverger numériquement sur 1-2 pas avant que le
        # solveur de gaz n'échoue : on retient les pas réellement physiques, soit
        # jusqu'au premier dépassement de la course mécanique du train fautif.
        stroke_key = f"{slot_f.prefix}_stroke"
        course = float(slot_f.p.course)
        over = np.where(out[stroke_key][:i_fail] > course)[0]
        valid = int(over[0]) if over.size else i_fail
        if valid < 1:
            # Sur-enfoncement immédiat : on ne peut rien restituer d'exploitable.
            raise exc
        last_stroke = float(out[stroke_key][valid - 1])
        out = {k: v[:valid] for k, v in out.items()}
        geom = {k: v[:valid] for k, v in geom.items()}
        n_steps = valid - 1
        warnings.append(
            make_overstroke_warning(
                _GEAR_LABELS.get(slot_f.prefix, slot_f.prefix),
                valid * dt,
                last_stroke,
                course,
                exc,
            )
        )

    return EngineOutput(data=out, n_steps=n_steps, warnings=warnings, geometry=geom)


__all__ = ["run_aircraft", "OUTPUT_COLUMNS_AC", "GEOMETRY_KEYS_AC"]
