from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from .engine import (
    EngineOutput,
    _endstop,
    _integrate_const_acc,
    _trailing_arm_local_step,
    TrailingArmLocalState,
)
from .engine_strait_strut import (
    _init_strait_strut_local_state,
    _rot_sol_to_lg,
    _strait_strut_advance_local_state,
    _strait_strut_resolve_damper_step,
    _ffrijoi_nlg,
    _ffribag_nlg,
    StraitStrutLocalState,
)
from .gas import GasSpring
from .inputs import AircraftParamsSI, TrailingArmParamsSI
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
    "mlg_left_tors_res_x": "MLG left.Torseur.Resultante X (N)",
    "mlg_left_tors_res_z": "MLG left.Torseur.Resultante Z (N)",
    "mlg_left_tors_res_norm": "MLG left.Torseur.Resultante norme (N)",
    "mlg_left_torsc_fx": "MLG left.Torseur@C.Fx (N)",
    "mlg_left_torsc_fz": "MLG left.Torseur@C.Fz (N)",
    "mlg_left_torsb_fx": "MLG left.Torseur@B.Fx (N)",
    "mlg_left_torsb_fz": "MLG left.Torseur@B.Fz (N)",
    "mlg_left_torsb_mx": "MLG left.Torseur@B.Mx (N.m)",
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
    "mlg_right_tors_res_x": "MLG right.Torseur.Resultante X (N)",
    "mlg_right_tors_res_z": "MLG right.Torseur.Resultante Z (N)",
    "mlg_right_tors_res_norm": "MLG right.Torseur.Resultante norme (N)",
    "mlg_right_torsc_fx": "MLG right.Torseur@C.Fx (N)",
    "mlg_right_torsc_fz": "MLG right.Torseur@C.Fz (N)",
    "mlg_right_torsb_fx": "MLG right.Torseur@B.Fx (N)",
    "mlg_right_torsb_fz": "MLG right.Torseur@B.Fz (N)",
    "mlg_right_torsb_mx": "MLG right.Torseur@B.Mx (N.m)",
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
    "mlg_left_ax",
    "mlg_left_az",
    "mlg_left_bx",
    "mlg_left_bz",
    "mlg_left_cx",
    "mlg_left_cz",
    "mlg_left_rx",
    "mlg_left_rz",
    "mlg_left_wheel_radius",
    "mlg_right_ax",
    "mlg_right_az",
    "mlg_right_bx",
    "mlg_right_bz",
    "mlg_right_cx",
    "mlg_right_cz",
    "mlg_right_rx",
    "mlg_right_rz",
    "mlg_right_wheel_radius",
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
    return replace(
        p,
        B=np.array([p.B[0], -p.B[1], p.B[2]], dtype=float),
        A=np.array([p.A[0], -p.A[1], p.A[2]], dtype=float),
        C=np.array([p.C[0], -p.C[1], p.C[2]], dtype=float),
        R=np.array([p.R[0], -p.R[1], p.R[2]], dtype=float),
        S=np.array([p.S[0], -p.S[1], p.S[2]], dtype=float),
    )


def run_aircraft(p: AircraftParamsSI, progress_callback: callable | None = None) -> EngineOutput:
    dt = p.it
    n_steps = max(1, round(p.temps_simu / dt))
    n_out = n_steps + 1

    nlg_p = p.nlg
    mlg_l_p = p.mlg
    mlg_r_p = _mirror_trailing_params_y(p.mlg)

    nlg_gas = GasSpring(nlg_p)
    nlg_tab_pos, nlg_tab_sec = build_section_table(nlg_p)
    nlg_tyre_defl, nlg_tyre_load = build_tyre_tables(nlg_p)
    nlg_R_sol_to_lg = _rot_sol_to_lg(p.nlg_strut_pitch - p.pitch, p.nlg_strut_roll)
    nlg_R_lg_to_sol = nlg_R_sol_to_lg.T
    nlg_state: StraitStrutLocalState = _init_strait_strut_local_state(
        nlg_p,
        nlg_gas,
        nlg_R_sol_to_lg,
        nlg_R_lg_to_sol,
        h_pivot_z_m=p.nlg_h_pivot_z,
        h_guide_top_z_m=p.nlg_h_guide_top_z,
        h_guide_bot_z_m=p.nlg_h_guide_bot_z,
    )
    nlg_r0_sol = nlg_R_lg_to_sol @ nlg_state.ptR_lg.copy()

    mlg_l = _init_trailing_runtime(mlg_l_p)
    mlg_r = _init_trailing_runtime(mlg_r_p)

    z_cg = 0.0
    vz_cg = -p.vz
    az_cg = 0.0
    theta = p.pitch
    theta_dot = p.pitch_rate
    theta_ddot = 0.0

    x_nlg = float(p.nlg_station[0] - p.cg[0])
    x_mlg_l = float(p.mlg_left_station[0] - p.cg[0])
    x_mlg_r = float(p.mlg_right_station[0] - p.cg[0])

    def _rigid_station(cg_z_val: float, theta_val: float, station: np.ndarray) -> tuple[float, float]:
        cg_x_val = float(p.cg[0])
        cg_z_val_abs = float(p.cg[2] + cg_z_val)
        rel_x = float(station[0] - p.cg[0])
        rel_z = float(station[2] - p.cg[2])
        cos_t = math.cos(theta_val)
        sin_t = math.sin(theta_val)
        return (
            cg_x_val + rel_x * cos_t - rel_z * sin_t,
            cg_z_val_abs + rel_x * sin_t + rel_z * cos_t,
        )

    def _shift_from_reference(station_x: float, station_z: float, point: np.ndarray, ref: np.ndarray) -> tuple[float, float]:
        return (
            station_x + float(point[0] - ref[0]),
            station_z + float(point[2] - ref[2]),
        )

    def _off_world_to_body(off_x: float, off_z: float, theta_ref: float) -> tuple[float, float]:
        cos_t = math.cos(theta_ref)
        sin_t = math.sin(theta_ref)
        return (
            off_x * cos_t + off_z * sin_t,
            -off_x * sin_t + off_z * cos_t,
        )

    def _off_body_to_world(body_x: float, body_z: float, theta_val: float) -> tuple[float, float]:
        cos_t = math.cos(theta_val)
        sin_t = math.sin(theta_val)
        return (
            body_x * cos_t - body_z * sin_t,
            body_x * sin_t + body_z * cos_t,
        )

    # Sol global (repère sol absolu) : z = 0.
    ground_z = 0.0

    # Géométrie initiale avec z_cg=0 pour le bornage du solveur d'équilibre.
    nlg_station_x0, nlg_station_z0 = _rigid_station(z_cg, theta, p.nlg_station)
    mlg_l_station_x0, mlg_l_station_z0 = _rigid_station(z_cg, theta, p.mlg_left_station)
    mlg_r_station_x0, mlg_r_station_z0 = _rigid_station(z_cg, theta, p.mlg_right_station)

    nlg_r_sol_0 = nlg_R_lg_to_sol @ nlg_state.ptR_lg
    nlg_rx0, nlg_rz0 = _shift_from_reference(nlg_station_x0, nlg_station_z0, nlg_r_sol_0, nlg_r0_sol)
    mlg_l_rx0, mlg_l_rz0 = _shift_from_reference(mlg_l_station_x0, mlg_l_station_z0, mlg_l.state.R, mlg_l.r0)
    mlg_r_rx0, mlg_r_rz0 = _shift_from_reference(mlg_r_station_x0, mlg_r_station_z0, mlg_r.state.R, mlg_r.r0)

    z_bottom_ref = min(
        nlg_rz0 - float(p.nlg.unload_radius),
        mlg_l_rz0 - float(p.mlg.unload_radius),
        mlg_r_rz0 - float(p.mlg.unload_radius),
    )

    def _fz_total_for_zcg(z_cg_trial: float) -> tuple[float, float, float, float]:
        nlg_station_x_t, nlg_station_z_t = _rigid_station(z_cg_trial, theta, p.nlg_station)
        mlg_l_station_x_t, mlg_l_station_z_t = _rigid_station(z_cg_trial, theta, p.mlg_left_station)
        mlg_r_station_x_t, mlg_r_station_z_t = _rigid_station(z_cg_trial, theta, p.mlg_right_station)

        nlg_rz_t = nlg_station_z_t + float(nlg_r_sol_0[2] - nlg_r0_sol[2])
        mlg_l_rz_t = mlg_l_station_z_t + float(mlg_l.state.R[2] - mlg_l.r0[2])
        mlg_r_rz_t = mlg_r_station_z_t + float(mlg_r.state.R[2] - mlg_r.r0[2])

        nlg_defl_t = max(0.0, float(p.nlg.unload_radius) - (nlg_rz_t - ground_z))
        mlg_l_defl_t = max(0.0, float(p.mlg.unload_radius) - (mlg_l_rz_t - ground_z))
        mlg_r_defl_t = max(0.0, float(p.mlg.unload_radius) - (mlg_r_rz_t - ground_z))

        fz_nlg_t = max(0.0, float(f_tyre(nlg_defl_t, nlg_tyre_defl, nlg_tyre_load)))
        fz_mlg_l_t = max(0.0, float(f_tyre(mlg_l_defl_t, mlg_l.tyre_defl, mlg_l.tyre_load)))
        fz_mlg_r_t = max(0.0, float(f_tyre(mlg_r_defl_t, mlg_r.tyre_defl, mlg_r.tyre_load)))
        return fz_nlg_t + fz_mlg_l_t + fz_mlg_r_t, fz_nlg_t, fz_mlg_l_t, fz_mlg_r_t

    # Position initiale avion imposée: roue la plus basse tangente au sol,
    # après équilibrage local de chaque train.
    z_cg = -z_bottom_ref

    nlg_station_x_ref, nlg_station_z_ref = _rigid_station(z_cg, p.pitch, p.nlg_station)
    mlg_l_station_x_ref, mlg_l_station_z_ref = _rigid_station(z_cg, p.pitch, p.mlg_left_station)
    mlg_r_station_x_ref, mlg_r_station_z_ref = _rigid_station(z_cg, p.pitch, p.mlg_right_station)

    # Offsets rigides des points attachés à la structure avion, mesurés au repos.
    nlg_b_sol_ref = nlg_R_lg_to_sol @ nlg_state.ptB_lg
    nlg_gt_sol_ref = nlg_R_lg_to_sol @ nlg_state.ptGt_lg
    nlg_gb_sol_ref = nlg_R_lg_to_sol @ nlg_state.ptGb_lg
    nlg_b_off = nlg_b_sol_ref - nlg_r0_sol
    nlg_gt_off = nlg_gt_sol_ref - nlg_r0_sol
    nlg_gb_off = nlg_gb_sol_ref - nlg_r0_sol
    mlg_l_b_off = mlg_l.state.B - mlg_l.r0
    mlg_l_c_off = mlg_l.state.C - mlg_l.r0
    mlg_r_b_off = mlg_r.state.B - mlg_r.r0
    mlg_r_c_off = mlg_r.state.C - mlg_r.r0
    nlg_b_body = _off_world_to_body(float(nlg_b_off[0]), float(nlg_b_off[2]), p.pitch)
    nlg_gt_body = _off_world_to_body(float(nlg_gt_off[0]), float(nlg_gt_off[2]), p.pitch)
    nlg_gb_body = _off_world_to_body(float(nlg_gb_off[0]), float(nlg_gb_off[2]), p.pitch)
    mlg_l_b_body = _off_world_to_body(float(mlg_l_b_off[0]), float(mlg_l_b_off[2]), p.pitch)
    mlg_l_c_body = _off_world_to_body(float(mlg_l_c_off[0]), float(mlg_l_c_off[2]), p.pitch)
    mlg_r_b_body = _off_world_to_body(float(mlg_r_b_off[0]), float(mlg_r_b_off[2]), p.pitch)
    mlg_r_c_body = _off_world_to_body(float(mlg_r_c_off[0]), float(mlg_r_c_off[2]), p.pitch)

    nlg_state.z_ms = 0.0
    mlg_l.state.depms = 0.0
    mlg_r.state.depms = 0.0

    out = {k: np.zeros(n_out) for k in OUTPUT_COLUMNS_AC}
    geom = {k: np.zeros(n_out) for k in GEOMETRY_KEYS_AC}

    for i in range(n_out):
        t = i * dt

        nlg_R_sol_to_lg_step = _rot_sol_to_lg(p.nlg_strut_pitch - theta, p.nlg_strut_roll)
        nlg_R_lg_to_sol_step = nlg_R_sol_to_lg_step.T

        nlg_station_x, nlg_station_z = _rigid_station(z_cg, theta, p.nlg_station)
        mlg_l_station_x, mlg_l_station_z = _rigid_station(z_cg, theta, p.mlg_left_station)
        mlg_r_station_x, mlg_r_station_z = _rigid_station(z_cg, theta, p.mlg_right_station)

        zsup_nlg = nlg_station_z - nlg_station_z_ref
        vsup_nlg = vz_cg - x_nlg * theta_dot
        asup_nlg = az_cg - x_nlg * theta_ddot

        zsup_mlg_l = mlg_l_station_z - mlg_l_station_z_ref
        zsup_mlg_r = mlg_r_station_z - mlg_r_station_z_ref
        vsup_mlg_l = vz_cg - x_mlg_l * theta_dot
        vsup_mlg_r = vz_cg - x_mlg_r * theta_dot
        asup_mlg_l = az_cg - x_mlg_l * theta_ddot
        asup_mlg_r = az_cg - x_mlg_r * theta_ddot

        # Keep local ground reference fixed for trailing-arm local dynamics.
        # Support motion is already imposed through support_dz; moving S here would
        # double-count relative wheel/ground motion and inflate tyre forces.

        # NLG local resolution
        nlg_state.z_ms = zsup_nlg
        nlg_state.vz_ms = vsup_nlg
        v_ms_lg_vec = nlg_R_sol_to_lg_step @ np.array([0.0, 0.0, vsup_nlg])
        nlg_state.v_damper = -(float(v_ms_lg_vec[2]) - nlg_state.vz_mns_lg)
        damp_nlg = _strait_strut_resolve_damper_step(nlg_p, nlg_gas, nlg_tab_pos, nlg_tab_sec, nlg_state)
        pg = damp_nlg["pg"]
        pc = damp_nlg["pc"]
        pd = damp_nlg["pd"]
        nlg_state.delta_pc = damp_nlg["delta_pc"]
        nlg_state.delta_pd = damp_nlg["delta_pd"]
        nlg_state.pg_prev = pg
        nlg_b_off_x_step, nlg_b_off_z_step = _off_body_to_world(nlg_b_body[0], nlg_b_body[1], theta)
        nlg_bx_step = nlg_station_x + nlg_b_off_x_step
        nlg_bz_step = nlg_station_z + nlg_b_off_z_step

        pt_b_sol_now = nlg_R_lg_to_sol_step @ nlg_state.ptB_lg
        pt_r_sol_now = nlg_R_lg_to_sol_step @ nlg_state.ptR_lg
        br_sol_now = pt_r_sol_now - pt_b_sol_now
        # Deflection calculation: use world-frame geometry exclusively.
        # Wheel center position R in world frame (using rigid attachment point B).
        nlg_rz_world_now = nlg_bz_step + float(br_sol_now[2])
        # Tyre deflection: gap between unload radius and actual wheel-ground distance.
        nlg_defl_world = nlg_p.unload_radius - (nlg_rz_world_now - ground_z)
        if nlg_defl_world <= 0.0:
            nlg_state.tyre_defl_val = 0.0
        else:
            nlg_state.tyre_defl_val = nlg_defl_world
        nlg_tyre_defl_curr = nlg_state.tyre_defl_val
        tyre_ftyre_nlg = max(0.0, f_tyre(nlg_state.tyre_defl_val, nlg_tyre_defl, nlg_tyre_load))
        ffrijoi = _ffrijoi_nlg(nlg_state.v_damper, pd, nlg_p, p.nlg_seal_precomp_pa)
        fx_spring_wheel = -nlg_p.kx * nlg_state.tyre_depx - nlg_p.cx * nlg_state.tyre_vx
        tr_sol = np.array([fx_spring_wheel, 0.0, tyre_ftyre_nlg])
        tr_lg = nlg_R_sol_to_lg_step @ tr_sol
        r_eff_nlg = r_eff(nlg_p.unload_radius, nlg_state.tyre_defl_val)
        slip_nlg = 0.0
        if abs(p.vx) > 1.0e-9:
            slip_nlg = (p.vx - nlg_state.tyre_omega * r_eff_nlg) / abs(p.vx)
        mu_nlg = mu(slip_nlg, nlg_p.mu_x, nlg_p.mu_y)
        fspin_nlg = mu_nlg * tyre_ftyre_nlg * math.copysign(1.0, slip_nlg) if tyre_ftyre_nlg > 0 else 0.0
        tyre_alpha_nlg = (fspin_nlg * r_eff_nlg) / nlg_p.wheel_inertia if tyre_ftyre_nlg > 0 else 0.0
        xr = abs(float(tr_lg[0]))
        z_r_lg = float(nlg_state.ptR_lg[2])
        z_gt_lg = float(nlg_state.ptGt_lg[2])
        z_gb_lg = float(nlg_state.ptGb_lg[2])
        if abs(z_gb_lg - z_gt_lg) > 1.0e-9:
            xgb = -(z_r_lg - z_gt_lg) * xr / (z_gb_lg - z_gt_lg)
        else:
            xgb = 0.0
        xgt = -xgb - xr
        ffribag = _ffribag_nlg(
            nlg_state.v_damper,
            xgt,
            xgb,
            nlg_p.Dt,
            p.nlg_bague_guide,
            p.nlg_bague_piston,
        )
        fendstop_nlg = _endstop(nlg_state.d, nlg_p.course, smooth_len=nlg_p.endstop_smooth)
        ftot_nlg = nlg_p.Sc * pc - nlg_p.Sd * pd + nlg_p.Sbh * pg + ffrijoi + ffribag + fendstop_nlg
        nlg_state.ftot = ftot_nlg
        tb_lg = np.array([tr_lg[0], 0.0, ftot_nlg])
        tb_sol_raw = nlg_R_lg_to_sol_step @ tb_lg
        nlg_in_contact = tyre_ftyre_nlg > 1.0e-9
        # In aircraft-mode PFD, only ground-contact loads should be injected.
        # Internal strut preload must not excite the aircraft when the wheel is airborne.
        tb_sol = tb_sol_raw if nlg_in_contact else np.zeros(3)
        ptB_sol = nlg_R_lg_to_sol_step @ nlg_state.ptB_lg
        ptR_sol_cur = nlg_R_lg_to_sol_step @ nlg_state.ptR_lg
        mom_B_nlg = np.cross(ptR_sol_cur - ptB_sol, tr_sol) if nlg_in_contact else np.zeros(3)
        nlg_state = _strait_strut_advance_local_state(
            nlg_p,
            nlg_state,
            nlg_R_sol_to_lg_step,
            nlg_R_lg_to_sol_step,
            support_acc_ms_z=asup_nlg,
            ftot=ftot_nlg,
            tyre_ftyre_i=tyre_ftyre_nlg,
            dt=dt,
            method=nlg_p.integrator,
        )
        # MLG locals resolution
        step_l = _trailing_arm_local_step(
            mlg_l.p,
            mlg_l.gas,
            mlg_l.tab_pos,
            mlg_l.tab_sec,
            mlg_l.tyre_defl,
            mlg_l.tyre_load,
            mlg_l.mu_x,
            mlg_l.mu_y,
            mlg_l.state,
            support_dz=zsup_mlg_l - mlg_l.state.depms,
            support_vitms=vsup_mlg_l,
            support_accms=asup_mlg_l,
            entraxe_init=mlg_l.entraxe_init,
            lg_ab=mlg_l.lg_ab,
            lg_rb=mlg_l.lg_rb,
            dy_ca=mlg_l.dy_ca,
            fast_time_scale=mlg_l.fast_time_scale,
            integrator_mode=mlg_l.integrator_mode,
            It=dt * mlg_l.fast_time_scale,
        )
        step_r = _trailing_arm_local_step(
            mlg_r.p,
            mlg_r.gas,
            mlg_r.tab_pos,
            mlg_r.tab_sec,
            mlg_r.tyre_defl,
            mlg_r.tyre_load,
            mlg_r.mu_x,
            mlg_r.mu_y,
            mlg_r.state,
            support_dz=zsup_mlg_r - mlg_r.state.depms,
            support_vitms=vsup_mlg_r,
            support_accms=asup_mlg_r,
            entraxe_init=mlg_r.entraxe_init,
            lg_ab=mlg_r.lg_ab,
            lg_rb=mlg_r.lg_rb,
            dy_ca=mlg_r.dy_ca,
            fast_time_scale=mlg_r.fast_time_scale,
            integrator_mode=mlg_r.integrator_mode,
            It=dt * mlg_r.fast_time_scale,
        )

        # PFD structure avion (2 DDL: translation Z + tangage) :
        # efforts entrants = NLG@B + MLG gauche@B/C + MLG droite@B/C.
        fx_nlg_b = float(tb_sol[0])
        fz_nlg_b = float(tb_sol[2])
        fx_mlg_l_b = float(step_l["fb_x"])
        fz_mlg_l_b = float(step_l["fb_z"])
        fx_mlg_l_c = float(step_l["fc_x"])
        fz_mlg_l_c = float(step_l["fc_z"])
        fx_mlg_r_b = float(step_r["fb_x"])
        fz_mlg_r_b = float(step_r["fb_z"])
        fx_mlg_r_c = float(step_r["fc_x"])
        fz_mlg_r_c = float(step_r["fc_z"])

        fz_nlg = fz_nlg_b
        fz_mlg_l = fz_mlg_l_b + fz_mlg_l_c
        fz_mlg_r = fz_mlg_r_b + fz_mlg_r_c
        fz_total = fz_nlg + fz_mlg_l + fz_mlg_r

        cg_x = float(p.cg[0])
        cg_z = float(p.cg[2] + z_cg)

        nlg_b_off_x, nlg_b_off_z = _off_body_to_world(nlg_b_body[0], nlg_b_body[1], theta)
        mlg_l_b_off_x, mlg_l_b_off_z = _off_body_to_world(mlg_l_b_body[0], mlg_l_b_body[1], theta)
        mlg_l_c_off_x, mlg_l_c_off_z = _off_body_to_world(mlg_l_c_body[0], mlg_l_c_body[1], theta)
        mlg_r_b_off_x, mlg_r_b_off_z = _off_body_to_world(mlg_r_b_body[0], mlg_r_b_body[1], theta)
        mlg_r_c_off_x, mlg_r_c_off_z = _off_body_to_world(mlg_r_c_body[0], mlg_r_c_body[1], theta)

        nlg_bx = nlg_station_x + nlg_b_off_x
        nlg_bz = nlg_station_z + nlg_b_off_z
        mlg_l_bx = mlg_l_station_x + mlg_l_b_off_x
        mlg_l_bz = mlg_l_station_z + mlg_l_b_off_z
        mlg_l_cx = mlg_l_station_x + mlg_l_c_off_x
        mlg_l_cz = mlg_l_station_z + mlg_l_c_off_z
        mlg_r_bx = mlg_r_station_x + mlg_r_b_off_x
        mlg_r_bz = mlg_r_station_z + mlg_r_b_off_z
        mlg_r_cx = mlg_r_station_x + mlg_r_c_off_x
        mlg_r_cz = mlg_r_station_z + mlg_r_c_off_z

        def _my(px: float, pz: float, fx: float, fz: float) -> float:
            rx = px - cg_x
            rz = pz - cg_z
            return rx * fz - rz * fx

        mpitch = (
            _my(nlg_bx, nlg_bz, fx_nlg_b, fz_nlg_b)
            + _my(mlg_l_bx, mlg_l_bz, fx_mlg_l_b, fz_mlg_l_b)
            + _my(mlg_l_cx, mlg_l_cz, fx_mlg_l_c, fz_mlg_l_c)
            + _my(mlg_r_bx, mlg_r_bz, fx_mlg_r_b, fz_mlg_r_b)
            + _my(mlg_r_cx, mlg_r_cz, fx_mlg_r_c, fz_mlg_r_c)
        )

        az_cg = (fz_total - p.masse * G * (1.0 - p.lift)) / p.masse
        theta_ddot = mpitch / p.jyy

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
        out["aircraft_fz_nlg"][i] = fz_nlg
        out["aircraft_fz_mlg_left"][i] = fz_mlg_l
        out["aircraft_fz_mlg_right"][i] = fz_mlg_r
        out["aircraft_mx_total"][i] = mpitch
        out["nlg_stroke"][i] = max(0.0, nlg_state.d)
        out["nlg_velocity"][i] = nlg_state.v_damper
        out["nlg_ftot"][i] = ftot_nlg
        out["nlg_fhyd"][i] = float(damp_nlg["fhyd"])
        out["nlg_ffrijoi"][i] = ffrijoi
        out["nlg_ffribag"][i] = ffribag
        out["nlg_fgas"][i] = float(damp_nlg["fgas"])
        out["nlg_pg"][i] = pg / 1.0e5
        out["nlg_pc"][i] = pc / 1.0e5
        out["nlg_pd"][i] = pd / 1.0e5
        out["nlg_delta_pc"][i] = nlg_state.delta_pc / 1.0e5
        out["nlg_delta_pd"][i] = nlg_state.delta_pd / 1.0e5
        out["nlg_hyd_qc_total"][i] = float(damp_nlg["qc_total"])
        out["nlg_hyd_qc_bh"][i] = float(damp_nlg["qc_bh"])
        out["nlg_hyd_qc_leak"][i] = float(damp_nlg["qc_leak"])
        out["nlg_hyd_leak_ratio"][i] = float(damp_nlg["leak_ratio"])
        out["nlg_hyd_re_leak"][i] = float(damp_nlg["re_leak"])
        out["nlg_hyd_conv_err"][i] = float(damp_nlg["hyd_conv_err"])
        out["nlg_hyd_conv_iter"][i] = float(damp_nlg["hyd_conv_iter"])
        out["nlg_secbh"][i] = float(damp_nlg["sec"]) * 1.0e6
        out["nlg_tyre_defl"][i] = nlg_tyre_defl_curr
        out["nlg_tyre_ftyre"][i] = tyre_ftyre_nlg
        out["nlg_tyre_mu"][i] = mu_nlg
        out["nlg_tyre_slip"][i] = slip_nlg
        out["nlg_tyre_omega"][i] = nlg_state.tyre_omega
        out["nlg_tyre_alpha"][i] = tyre_alpha_nlg
        out["nlg_tr_x"][i] = -fx_spring_wheel
        out["nlg_reaction_h"][i] = -fx_spring_wheel
        out["nlg_reaction_v"][i] = tyre_ftyre_nlg
        out["nlg_xgt"][i] = xgt
        out["nlg_xgb"][i] = xgb
        out["nlg_accms"][i] = asup_nlg
        out["nlg_accmns"][i] = (-ftot_nlg + tyre_ftyre_nlg - nlg_p.unsprung_mass * G) / nlg_p.unsprung_mass
        out["nlg_vitmns"][i] = nlg_state.vz_mns_lg
        out["nlg_depmns"][i] = nlg_state.z_mns_lg
        out["nlg_tors_res_x"][i] = float(tb_sol[0])
        out["nlg_tors_res_z"][i] = float(tb_sol[2])
        out["nlg_tors_res_norm"][i] = math.hypot(float(tb_sol[0]), float(tb_sol[2]))
        out["nlg_torsb_fx"][i] = float(tb_sol[0])
        out["nlg_torsb_fz"][i] = float(tb_sol[2])
        out["nlg_torsb_mx"][i] = float(mom_B_nlg[0])
        out["nlg_torsb_mz"][i] = float(mom_B_nlg[2])
        out["mlg_left_stroke"][i] = max(0.0, mlg_l.state.d)
        out["mlg_left_velocity"][i] = mlg_l.state.v
        out["mlg_left_ftot"][i] = mlg_l.state.ftot
        out["mlg_left_fhyd"][i] = float(step_l["fhyd"])
        out["mlg_left_ffrijoi"][i] = float(step_l["ffrijoi"])
        out["mlg_left_fgas"][i] = float(step_l["fgas"])
        out["mlg_left_pg"][i] = float(step_l["pg"]) / 1.0e5
        out["mlg_left_pc"][i] = float(step_l["pc"]) / 1.0e5
        out["mlg_left_pd"][i] = float(step_l["pd"]) / 1.0e5
        out["mlg_left_delta_pc"][i] = mlg_l.state.delta_pc / 1.0e5
        out["mlg_left_delta_pd"][i] = mlg_l.state.delta_pd / 1.0e5
        out["mlg_left_hyd_qc_total"][i] = mlg_l.state.qc_total
        out["mlg_left_hyd_qc_bh"][i] = mlg_l.state.qc_bh
        out["mlg_left_hyd_qc_leak"][i] = mlg_l.state.qc_leak
        out["mlg_left_hyd_leak_ratio"][i] = mlg_l.state.leak_ratio
        out["mlg_left_hyd_re_leak"][i] = mlg_l.state.re_leak
        out["mlg_left_hyd_conv_err"][i] = mlg_l.state.hyd_conv_err
        out["mlg_left_hyd_conv_iter"][i] = mlg_l.state.hyd_conv_iter
        out["mlg_left_secbh"][i] = mlg_l.state.sec * 1.0e6
        out["mlg_left_tyre_defl"][i] = max(0.0, mlg_l.state.defl)
        out["mlg_left_tyre_ftyre"][i] = float(step_l["ftyre"])
        out["mlg_left_tyre_mu"][i] = float(step_l["mu_val"])
        out["mlg_left_tyre_slip"][i] = float(step_l["slip"])
        out["mlg_left_tyre_omega"][i] = mlg_l.state.omega
        out["mlg_left_tyre_alpha"][i] = mlg_l.state.alpha
        out["mlg_left_fx"][i] = float(step_l["fb_x"] + step_l["fc_x"])
        out["mlg_left_reaction_h"][i] = float(step_l["fb_x"] + step_l["fc_x"])
        out["mlg_left_reaction_v"][i] = float(step_l["ftyre"])
        out["mlg_left_accms"][i] = asup_mlg_l
        out["mlg_left_tors_res_x"][i] = float(step_l["res_x"])
        out["mlg_left_tors_res_z"][i] = float(step_l["res_z"])
        out["mlg_left_tors_res_norm"][i] = float(step_l["res_norm"])
        out["mlg_left_torsc_fx"][i] = float(step_l["fc_x"])
        out["mlg_left_torsc_fz"][i] = float(step_l["fc_z"])
        out["mlg_left_torsb_fx"][i] = float(step_l["fb_x"])
        out["mlg_left_torsb_fz"][i] = float(step_l["fb_z"])
        out["mlg_left_torsb_mx"][i] = float(step_l["mb_x"])
        out["mlg_left_torsb_mz"][i] = float(step_l["mb_z"])
        out["mlg_right_stroke"][i] = max(0.0, mlg_r.state.d)
        out["mlg_right_velocity"][i] = mlg_r.state.v
        out["mlg_right_ftot"][i] = mlg_r.state.ftot
        out["mlg_right_fhyd"][i] = float(step_r["fhyd"])
        out["mlg_right_ffrijoi"][i] = float(step_r["ffrijoi"])
        out["mlg_right_fgas"][i] = float(step_r["fgas"])
        out["mlg_right_pg"][i] = float(step_r["pg"]) / 1.0e5
        out["mlg_right_pc"][i] = float(step_r["pc"]) / 1.0e5
        out["mlg_right_pd"][i] = float(step_r["pd"]) / 1.0e5
        out["mlg_right_delta_pc"][i] = mlg_r.state.delta_pc / 1.0e5
        out["mlg_right_delta_pd"][i] = mlg_r.state.delta_pd / 1.0e5
        out["mlg_right_hyd_qc_total"][i] = mlg_r.state.qc_total
        out["mlg_right_hyd_qc_bh"][i] = mlg_r.state.qc_bh
        out["mlg_right_hyd_qc_leak"][i] = mlg_r.state.qc_leak
        out["mlg_right_hyd_leak_ratio"][i] = mlg_r.state.leak_ratio
        out["mlg_right_hyd_re_leak"][i] = mlg_r.state.re_leak
        out["mlg_right_hyd_conv_err"][i] = mlg_r.state.hyd_conv_err
        out["mlg_right_hyd_conv_iter"][i] = mlg_r.state.hyd_conv_iter
        out["mlg_right_secbh"][i] = mlg_r.state.sec * 1.0e6
        out["mlg_right_tyre_defl"][i] = max(0.0, mlg_r.state.defl)
        out["mlg_right_tyre_ftyre"][i] = float(step_r["ftyre"])
        out["mlg_right_tyre_mu"][i] = float(step_r["mu_val"])
        out["mlg_right_tyre_slip"][i] = float(step_r["slip"])
        out["mlg_right_tyre_omega"][i] = mlg_r.state.omega
        out["mlg_right_tyre_alpha"][i] = mlg_r.state.alpha
        out["mlg_right_fx"][i] = float(step_r["fb_x"] + step_r["fc_x"])
        out["mlg_right_reaction_h"][i] = float(step_r["fb_x"] + step_r["fc_x"])
        out["mlg_right_reaction_v"][i] = float(step_r["ftyre"])
        out["mlg_right_accms"][i] = asup_mlg_r
        out["mlg_right_tors_res_x"][i] = float(step_r["res_x"])
        out["mlg_right_tors_res_z"][i] = float(step_r["res_z"])
        out["mlg_right_tors_res_norm"][i] = float(step_r["res_norm"])
        out["mlg_right_torsc_fx"][i] = float(step_r["fc_x"])
        out["mlg_right_torsc_fz"][i] = float(step_r["fc_z"])
        out["mlg_right_torsb_fx"][i] = float(step_r["fb_x"])
        out["mlg_right_torsb_fz"][i] = float(step_r["fb_z"])
        out["mlg_right_torsb_mx"][i] = float(step_r["mb_x"])
        out["mlg_right_torsb_mz"][i] = float(step_r["mb_z"])

        # Géométrie avion + points caractéristiques trains (repère X-Z avion, m).

        nlg_b_sol = nlg_R_lg_to_sol_step @ nlg_state.ptB_lg
        nlg_gt_sol = nlg_R_lg_to_sol_step @ nlg_state.ptGt_lg
        nlg_gb_sol = nlg_R_lg_to_sol_step @ nlg_state.ptGb_lg
        nlg_r_sol = nlg_R_lg_to_sol_step @ nlg_state.ptR_lg

        geom["cg_x"][i] = cg_x
        geom["cg_z"][i] = cg_z
        geom["ground_z"][i] = ground_z
        nlg_gt_off_x, nlg_gt_off_z = _off_body_to_world(nlg_gt_body[0], nlg_gt_body[1], theta)
        nlg_gb_off_x, nlg_gb_off_z = _off_body_to_world(nlg_gb_body[0], nlg_gb_body[1], theta)
        geom["nlg_bx"][i] = nlg_bx
        geom["nlg_bz"][i] = nlg_bz
        geom["nlg_gtx"][i] = nlg_station_x + nlg_gt_off_x
        geom["nlg_gtz"][i] = nlg_station_z + nlg_gt_off_z
        geom["nlg_gbx"][i] = nlg_station_x + nlg_gb_off_x
        geom["nlg_gbz"][i] = nlg_station_z + nlg_gb_off_z
        nlg_br_sol_x = float(nlg_r_sol[0] - nlg_b_sol[0])
        nlg_br_sol_z = float(nlg_r_sol[2] - nlg_b_sol[2])
        geom["nlg_rx"][i] = nlg_bx + nlg_br_sol_x
        geom["nlg_rz"][i] = nlg_bz + nlg_br_sol_z
        geom["nlg_wheel_radius"][i] = p.nlg.unload_radius

        # Rebuild A/R from rigid B anchor and local arm vectors to keep B-R-A rigid in animation export.
        mlg_l_a_dx = float(mlg_l.state.A[0] - mlg_l.state.B[0])
        mlg_l_a_dz = float(mlg_l.state.A[2] - mlg_l.state.B[2])
        mlg_l_r_dx = float(mlg_l.state.R[0] - mlg_l.state.B[0])
        mlg_l_r_dz = float(mlg_l.state.R[2] - mlg_l.state.B[2])
        geom["mlg_left_ax"][i] = mlg_l_bx + mlg_l_a_dx
        geom["mlg_left_az"][i] = mlg_l_bz + mlg_l_a_dz
        geom["mlg_left_bx"][i] = mlg_l_bx
        geom["mlg_left_bz"][i] = mlg_l_bz
        geom["mlg_left_cx"][i] = mlg_l_cx
        geom["mlg_left_cz"][i] = mlg_l_cz
        geom["mlg_left_rx"][i] = mlg_l_bx + mlg_l_r_dx
        geom["mlg_left_rz"][i] = mlg_l_bz + mlg_l_r_dz
        geom["mlg_left_wheel_radius"][i] = p.mlg.unload_radius

        mlg_r_a_dx = float(mlg_r.state.A[0] - mlg_r.state.B[0])
        mlg_r_a_dz = float(mlg_r.state.A[2] - mlg_r.state.B[2])
        mlg_r_r_dx = float(mlg_r.state.R[0] - mlg_r.state.B[0])
        mlg_r_r_dz = float(mlg_r.state.R[2] - mlg_r.state.B[2])
        geom["mlg_right_ax"][i] = mlg_r_bx + mlg_r_a_dx
        geom["mlg_right_az"][i] = mlg_r_bz + mlg_r_a_dz
        geom["mlg_right_bx"][i] = mlg_r_bx
        geom["mlg_right_bz"][i] = mlg_r_bz
        geom["mlg_right_cx"][i] = mlg_r_cx
        geom["mlg_right_cz"][i] = mlg_r_cz
        geom["mlg_right_rx"][i] = mlg_r_bx + mlg_r_r_dx
        geom["mlg_right_rz"][i] = mlg_r_bz + mlg_r_r_dz
        geom["mlg_right_wheel_radius"][i] = p.mlg.unload_radius

        if progress_callback is not None and (i % 10 == 0 or i == n_steps):
            progress_callback(i, n_steps)

    return EngineOutput(data=out, n_steps=n_steps, geometry=geom)


__all__ = ["run_aircraft", "OUTPUT_COLUMNS_AC", "GEOMETRY_KEYS_AC"]
