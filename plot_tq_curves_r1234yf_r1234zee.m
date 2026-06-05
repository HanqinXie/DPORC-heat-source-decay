function plot_tq_curves_r1234yf_r1234zee(year_value)
% Plot dual-pressure ORC T-Q curves for R1234yf and R600A (isobutane).
%
% The script reads the best-by-year summary CSV, recovers the missing
% superheat settings by matching the recorded net output and LMTD values,
% and then plots the hot-source line together with the working-fluid
% composite T-Q curve.

if nargin < 1 || isempty(year_value)
    year_value = 0;
end

script_dir = fileparts(mfilename('fullpath'));
code_root = fileparts(script_dir);
addpath(genpath(fullfile(code_root, 'bin1', 'Optimized')));

input_csv = fullfile(script_dir, 'figures_9fluids_comparison', 'all_fluids_best_by_net_output.csv');
outdir = fullfile(script_dir, 'figures_tq_curves_r1234yf_r600a');
if ~exist(outdir, 'dir')
    mkdir(outdir);
end

source_tbl = readtable(input_csv, 'TextType', 'string');
target_fluids = ["R1234YF", "R600A"];

results = repmat(struct( ...
    'fluid', "", ...
    'year', year_value, ...
    'target_row', table(), ...
    'recovered', struct(), ...
    'details', struct(), ...
    'single_outpath', ""), numel(target_fluids), 1);

for idx = 1:numel(target_fluids)
    fluid = target_fluids(idx);
    display_fluid = format_display_fluid(fluid);
    row = select_target_row(source_tbl, fluid, year_value);
    params = build_default_params(map_refprop_fluid(fluid));
    recovered = recover_superheat_settings(row, params);
    details = evaluate_point_details(row.T_HS_in_K, ...
        [row.P_e_lp_kPa, row.P_e_hp_kPa, recovered.DT_sh_lp_K, recovered.DT_sh_hp_K], params);

    if ~details.feasible
        error('plot_tq_curves:%sInfeasible', fluid, ...
            'Recovered point for %s at year %.3f is infeasible: %s', ...
            fluid, year_value, details.fail_reason);
    end

    single_outpath = fullfile(outdir, sprintf('%s_tq_curve_year_%s.png', fluid, format_year_for_filename(year_value)));
    plot_single_tq_curve(details, display_fluid, year_value, single_outpath);

    results(idx).fluid = fluid;
    results(idx).year = year_value;
    results(idx).target_row = row;
    results(idx).recovered = recovered;
    results(idx).details = details;
    results(idx).single_outpath = string(single_outpath);

    fprintf(['%s year %.3f recovered: DT_sh_lp = %.4f K, DT_sh_hp = %.4f K, ' ...
             'score = %.6f, net_output = %.4f kW.\n'], ...
        fluid, year_value, recovered.DT_sh_lp_K, recovered.DT_sh_hp_K, ...
        recovered.match_score, details.net_output_kW);
end

combined_outpath = fullfile(outdir, ...
    sprintf('R1234YF_R600A_tq_curves_year_%s.png', format_year_for_filename(year_value)));
plot_combined_tq_curves(results, year_value, combined_outpath);

summary_tbl = build_summary_table(results);
summary_outpath = fullfile(outdir, ...
    sprintf('R1234YF_R600A_tq_summary_year_%s.csv', format_year_for_filename(year_value)));
writetable(summary_tbl, summary_outpath);

fprintf('Input CSV: %s\n', input_csv);
fprintf('Output directory: %s\n', outdir);
for idx = 1:numel(results)
    fprintf('Generated single figure: %s\n', results(idx).single_outpath);
end
fprintf('Generated combined figure: %s\n', combined_outpath);
fprintf('Generated summary CSV: %s\n', summary_outpath);
end


function row = select_target_row(source_tbl, fluid, year_value)
fluid_mask = upper(string(source_tbl.fluid)) == upper(fluid);
year_mask = abs(source_tbl.year - year_value) < 1e-9;
subset = source_tbl(fluid_mask & year_mask, :);
if isempty(subset)
    error('plot_tq_curves:RowNotFound', ...
        'No row found for fluid %s at year %.3f.', fluid, year_value);
end
if height(subset) > 1
    [~, best_idx] = max(subset.net_output_kW);
    subset = subset(best_idx, :);
end
row = subset(1, :);
end


function params = build_default_params(wf_name)
params = struct();
params.WF = wf_name;
params.HS_fluid = 'water';
params.cool_fluid = 'water';

params.T_0 = 20 + 273.15;
params.m_HS = 100;
params.P_HS = 0.5 * 1e3;

params.delta_T_HAP_pp = 5;
params.delta_T_cond_pp = 5;
params.delta_T_subcool = 2;

params.T_cool_in = 20 + 273.15;
params.delta_T_cool = 5;
params.T_cool_out = params.T_cool_in + params.delta_T_cool;
params.P_cool = 0.101 * 1e3;

params.eta_p = 0.75;
params.eta_T = 0.80;
params.eta_pw = 0.85;

params.T_cond = params.T_cool_out + params.delta_T_cond_pp;
params.P_cond = refpropm('P', 'T', params.T_cond, 'Q', 0, params.WF);

    [params.h_HS_0, params.s_HS_0] = refpropm('HS', 'T', params.T_0, ...
        'P', params.P_HS, params.HS_fluid);

params.h_cool_in = refpropm('H', 'T', params.T_cool_in, 'P', params.P_cool, params.cool_fluid);
params.h_cool_out = refpropm('H', 'T', params.T_cool_out, 'P', params.P_cool, params.cool_fluid);

params.T1_base = params.T_cond - params.delta_T_subcool;
params.P1_base = params.P_cond;
    [params.h1_base, params.s1_base] = refpropm('HS', 'T', params.T1_base, ...
        'P', params.P1_base, params.WF);
    [params.T12_base, params.h12_base, params.s12_base] = refpropm('THS', ...
        'P', params.P_cond, 'Q', 1, params.WF);
end


function refprop_name = map_refprop_fluid(fluid_label)
switch upper(string(fluid_label))
    case "R1234YF"
        refprop_name = 'R1234yf';
    case "R600A"
        refprop_name = 'ISOBUTANE';
    otherwise
        error('plot_tq_curves:UnsupportedFluid', 'Unsupported fluid label %s.', fluid_label);
end
end


function display_label = format_display_fluid(fluid_label)
switch upper(string(fluid_label))
    case "R1234YF"
        display_label = 'R1234YF';
    case "R600A"
        display_label = 'R600A';
    otherwise
        display_label = char(string(fluid_label));
end
end


function best = recover_superheat_settings(row, params)
T_HS_in = row.T_HS_in_K;
P_lp = row.P_e_lp_kPa;
P_hp = row.P_e_hp_kPa;

T7 = refpropm('T', 'P', P_hp, 'Q', 1, params.WF);
T_e_lp = refpropm('T', 'P', P_lp, 'Q', 0, params.WF);

dt_hp_min = 2.0;
dt_hp_max = T_HS_in - params.delta_T_HAP_pp - T7;
dt_lp_min = 0.01;
dt_lp_max = T_HS_in - 2.0 * params.delta_T_HAP_pp - T_e_lp;

if ~(isfinite(dt_hp_max) && dt_hp_max >= dt_hp_min)
    error('plot_tq_curves:InvalidHPRange', ...
        'No feasible HP superheat range for %s at year %.3f.', row.fluid, row.year);
end
if ~(isfinite(dt_lp_max) && dt_lp_max >= dt_lp_min)
    error('plot_tq_curves:InvalidLPRange', ...
        'No feasible LP superheat range for %s at year %.3f.', row.fluid, row.year);
end

coarse_hp = linspace(dt_hp_min, dt_hp_max, 21);
coarse_lp = linspace(dt_lp_min, dt_lp_max, 21);
best = run_superheat_grid_search(row, params, coarse_lp, coarse_hp);

hp_step = max((dt_hp_max - dt_hp_min) / max(numel(coarse_hp) - 1, 1), 1e-6);
lp_step = max((dt_lp_max - dt_lp_min) / max(numel(coarse_lp) - 1, 1), 1e-6);

refine_hp = linspace(max(dt_hp_min, best.DT_sh_hp_K - hp_step), ...
    min(dt_hp_max, best.DT_sh_hp_K + hp_step), 31);
refine_lp = linspace(max(dt_lp_min, best.DT_sh_lp_K - lp_step), ...
    min(dt_lp_max, best.DT_sh_lp_K + lp_step), 31);
best = run_superheat_grid_search(row, params, refine_lp, refine_hp, best);
end


function best = run_superheat_grid_search(row, params, dt_lp_values, dt_hp_values, seed_best)
if nargin < 5 || isempty(seed_best)
    best = struct( ...
        'DT_sh_lp_K', NaN, ...
        'DT_sh_hp_K', NaN, ...
        'match_score', inf, ...
        'details', struct(), ...
        'target_row', row);
else
    best = seed_best;
end

T_HS_in = row.T_HS_in_K;
P_lp = row.P_e_lp_kPa;
P_hp = row.P_e_hp_kPa;

for dt_hp = dt_hp_values
    for dt_lp = dt_lp_values
        details = evaluate_point_details(T_HS_in, [P_lp, P_hp, dt_lp, dt_hp], params);
        if ~details.feasible
            continue;
        end

        score = compute_match_score(details, row);
        if score < best.match_score
            best.DT_sh_lp_K = dt_lp;
            best.DT_sh_hp_K = dt_hp;
            best.match_score = score;
            best.details = details;
        end
    end
end

if ~isfinite(best.match_score)
    error('plot_tq_curves:SearchFailed', ...
        'Could not recover a feasible superheat pair for %s at year %.3f.', ...
        row.fluid, row.year);
end
end


function score = compute_match_score(details, row)
target_eta_ex_percent = row.eta_ex_percent;
score = ...
    abs(details.net_output_kW - row.net_output_kW) / max(abs(row.net_output_kW), 1.0) + ...
    abs(details.eta_ex_percent - target_eta_ex_percent) / max(abs(target_eta_ex_percent), 1.0) + ...
    abs(details.DT_hp_lmtd_K - row.lmtd_hp_K) / max(abs(row.lmtd_hp_K), 1.0) + ...
    abs(details.DT_lp_lmtd_K - row.lmtd_lp_K) / max(abs(row.lmtd_lp_K), 1.0);
end


function details = evaluate_point_details(T_HS_in, x, params)
details = struct( ...
    'feasible', false, ...
    'fail_reason', "unknown", ...
    'net_output_kW', NaN, ...
    'eta_ex_percent', NaN, ...
    'DT_hp_lmtd_K', NaN, ...
    'DT_lp_lmtd_K', NaN, ...
    'T_HS_in', T_HS_in, ...
    'T_HS_3', NaN, ...
    'T_HS_4_req', NaN, ...
    'T_HS_out', NaN, ...
    'h_HS_in', NaN, ...
    'h_HS_3', NaN, ...
    'h_HS_4_req', NaN, ...
    'h_HS_out', NaN, ...
    'm_O_HP', NaN, ...
    'm_O_LP', NaN, ...
    'm_f', NaN, ...
    'T2', NaN, ...
    'T3', NaN, ...
    'T4p', NaN, ...
    'T4', NaN, ...
    'T5', NaN, ...
    'T6', NaN, ...
    'T7', NaN, ...
    'T8', NaN, ...
    'h2', NaN, ...
    'h3', NaN, ...
    'h4p', NaN, ...
    'h4', NaN, ...
    'h5', NaN, ...
    'h6', NaN, ...
    'h7', NaN, ...
    'h8', NaN, ...
    'q_pre_W', NaN, ...
    'q_lp_evap_W', NaN, ...
    'q_lp_sh_W', NaN, ...
    'q_hp_pre_W', NaN, ...
    'q_hp_evap_W', NaN, ...
    'q_hp_sh_W', NaN, ...
    'Qin_W', NaN, ...
    'P_e_lp_kPa', x(1), ...
    'P_e_hp_kPa', x(2), ...
    'DT_sh_lp_K', x(3), ...
    'DT_sh_hp_K', x(4));

WF = params.WF;
HS_fluid = params.HS_fluid;
cool_fluid = params.cool_fluid;

T_0 = params.T_0;
m_HS = params.m_HS;
P_HS = params.P_HS;
delta_T_HAP_pp = params.delta_T_HAP_pp;
delta_T_cond_pp = params.delta_T_cond_pp;
eta_p = params.eta_p;
eta_T = params.eta_T;
P_cond = params.P_cond;

h_HS_0 = params.h_HS_0;
s_HS_0 = params.s_HS_0;
h_cool_in = params.h_cool_in;

T_cool_in = params.T_cool_in;
T_cool_out = params.T_cool_out;
P_cool = params.P_cool;

T1 = params.T1_base;
P1 = params.P1_base;
h1 = params.h1_base;
s1 = params.s1_base;

T12 = params.T12_base;
h12 = params.h12_base;

P_e_lp = x(1);
P_e_hp = x(2);
DT_sh_lp = x(3);
DT_sh_hp = x(4);

if P_e_hp <= P_e_lp + 50
    details.fail_reason = "P_e_hp <= P_e_lp + 50";
    return;
end

if P_e_lp <= P_cond + 1
    details.fail_reason = "P_e_lp too low";
    return;
end

try
    [h_HS_in, s_HS_in] = refpropm('HS', 'T', T_HS_in, 'P', P_HS, HS_fluid);
    Ein = m_HS * ((h_HS_in - h_HS_0) - T_0 * (s_HS_in - s_HS_0));

    T_e_lp = refpropm('T', 'P', P_e_lp, 'Q', 0, WF);

    P2 = P_e_lp;
    h2_ideal = refpropm('H', 'P', P2, 'S', s1, WF);
    deltah_21 = (h2_ideal - h1) / eta_p;
    h2 = h1 + deltah_21;
    [s2, T2] = refpropm('ST', 'P', P2, 'H', h2, WF);

    P3 = P_e_lp;
    T3 = T_e_lp;
    [h3, s3] = refpropm('HS', 'T', T3, 'Q', 0, WF);

    [T4p, h4p, ~] = refpropm('THS', 'P', P_e_lp, 'Q', 1, WF);

    T_e_hp = refpropm('T', 'P', P_e_hp, 'Q', 0, WF);

    P5 = P_e_hp;
    h5_ideal = refpropm('H', 'P', P5, 'S', refpropm('S', 'T', T3, 'Q', 0, WF), WF);
    deltah_53 = (h5_ideal - h3) / eta_p;
    h5 = h3 + deltah_53;
    [s5, T5] = refpropm('ST', 'P', P5, 'H', h5, WF);

    P6 = P_e_hp;
    T6 = T_e_hp;
    [h6, ~] = refpropm('HS', 'T', T6, 'Q', 0, WF);

    [T7, h7, s7] = refpropm('THS', 'P', P_e_hp, 'Q', 1, WF);

    P8 = P_e_hp;
    T8 = T7 + DT_sh_hp;

    if T_HS_in < (T8 + delta_T_HAP_pp)
        details.fail_reason = "T_HS_in < T8 + pinch";
        return;
    end

    [h8, s8] = refpropm('HS', 'T', T8, 'P', P8, WF);

    T_HS_6_req = T6 + delta_T_HAP_pp;
    h_HS_6_req = refpropm('H', 'T', T_HS_6_req, 'P', P_HS, HS_fluid);

    m_O_HP = m_HS * (h_HS_in - h_HS_6_req) / (h8 - h6);
    if m_O_HP <= 0 || ~isfinite(m_O_HP)
        details.fail_reason = "m_O_HP invalid @ state 6 pinch";
        return;
    end

    h_HS_3 = h_HS_6_req - m_O_HP * (h6 - h5) / m_HS;
    T_HS_3 = refpropm('T', 'H', h_HS_3, 'P', P_HS, HS_fluid);
    if (T_HS_3 - T5) < delta_T_HAP_pp
        T_HS_3 = T5 + delta_T_HAP_pp;
        h_HS_3 = refpropm('H', 'T', T_HS_3, 'P', P_HS, HS_fluid);
        m_O_HP = m_HS * (h_HS_in - h_HS_3) / (h8 - h5);
        if m_O_HP <= 0 || ~isfinite(m_O_HP)
            details.fail_reason = "m_O_HP invalid @ state 5 correction";
            return;
        end
    end

    P4 = P_e_lp;
    T4 = T4p + DT_sh_lp;
    if T_HS_3 < (T4 + delta_T_HAP_pp)
        details.fail_reason = "T_HS_3 < T4 + pinch";
        return;
    end

    [h4, s4] = refpropm('HS', 'T', T4, 'P', P4, WF);

    T_HS_4_req = T3 + delta_T_HAP_pp;
    h_HS_4_req = refpropm('H', 'T', T_HS_4_req, 'P', P_HS, HS_fluid);

    m_O_LP = m_HS * (h_HS_3 - h_HS_4_req) / (h4 - h3);
    if m_O_LP <= 0 || ~isfinite(m_O_LP)
        details.fail_reason = "m_O_LP invalid @ LP evaporator";
        return;
    end

    m_f = m_O_LP + m_O_HP;
    h_HS_out = h_HS_4_req - m_f * (h3 - h2) / m_HS;
    [T_HS_out, s_HS_out] = refpropm('TS', 'H', h_HS_out, 'P', P_HS, HS_fluid);

    if (T_HS_out - T2) < delta_T_HAP_pp
        T_HS_out = T2 + delta_T_HAP_pp;
        h_HS_out = refpropm('H', 'T', T_HS_out, 'P', P_HS, HS_fluid);
        m_O_LP = (m_HS * (h_HS_3 - h_HS_out) - m_O_HP * (h3 - h2)) / (h4 - h2);
        m_f = m_O_LP + m_O_HP;
        if m_O_LP <= 0 || ~isfinite(m_O_LP)
            details.fail_reason = "m_O_LP invalid @ preheater correction";
            return;
        end
    end

    P9 = P_e_lp;
    h9s = refpropm('H', 'P', P9, 'S', s8, WF);
    deltah_89 = (h8 - h9s) * eta_T;
    h9 = h8 - deltah_89;
    s9 = refpropm('S', 'P', P9, 'H', h9, WF);

    P10 = P_e_lp;
    h10 = (m_O_LP * h4 + m_O_HP * h9) / m_f;
    [~, s10] = refpropm('TS', 'P', P10, 'H', h10, WF);

    P11 = P_cond;
    h11s = refpropm('H', 'P', P11, 'S', s10, WF);
    deltah_1011 = (h10 - h11s) * eta_T;
    h11 = h10 - deltah_1011;
    [s11, T11] = refpropm('ST', 'P', P11, 'H', h11, WF);

    if h11 <= h1
        details.fail_reason = "h11 <= h1";
        return;
    end

    if (T1 - T_cool_in) < delta_T_cond_pp
        details.fail_reason = "T1 - T_cool_in < delta_T_cond_pp";
        return;
    end

    T_cw_12_req = T12 - delta_T_cond_pp;
    h_cw_12_req = refpropm('H', 'T', T_cw_12_req, 'P', P_cool, cool_fluid);
    mw = m_f * (h12 - h1) / (h_cw_12_req - h_cool_in);
    if mw <= 0 || ~isfinite(mw)
        details.fail_reason = "mw invalid";
        return;
    end

    if (T11 - T_cool_out) < delta_T_cond_pp
        details.fail_reason = "T11 - T_cool_out < delta_T_cond_pp";
        return;
    end

    power_t_high = m_O_HP * deltah_89 / 1000;
    power_t_low = m_f * deltah_1011 / 1000;
    power_p1 = m_f * deltah_21 / 1000;
    power_p2 = m_O_HP * deltah_53 / 1000;
    power_w = m_f * (h11 - h1) / (100 * 1000);
    output_kW = power_t_high + power_t_low - power_p1 - power_p2 - power_w;

    Ede = m_HS * ((h_HS_in - h_HS_out) - T_0 * (s_HS_in - s_HS_out)) ...
        - (m_O_HP * (h8 - h5) + m_O_LP * (h4 - h3) + m_f * (h3 - h2)) ...
        + T_0 * (m_O_HP * (s8 - s5) + m_O_LP * (s4 - s3) + m_f * (s3 - s2));
    Edt_h = m_O_HP * T_0 * (s9 - s8);
    Edt_l = m_f * T_0 * (s11 - s10);
    Edt = Edt_h + Edt_l;
    Edp_1 = m_f * T_0 * (s2 - s1);
    Edp_2 = m_O_HP * T_0 * (s5 - s3);
    Edp = Edp_1 + Edp_2;
    Edmix = m_O_HP * (h9 - T_0 * s9) + m_O_LP * (h4 - T_0 * s4) - m_f * (h10 - T_0 * s10);
    Edc = m_f * ((h11 - h1) - T_0 * (s11 - s1));
    Edeout = m_HS * ((h_HS_out - h_HS_0) - T_0 * (s_HS_out - s_HS_0));
    exerg_balance = Ein - Ede - Edt - Edp - Edc - Edmix - Edeout - output_kW * 1000 - power_w * 1000;

    if abs(exerg_balance) >= 0.1
        details.fail_reason = "exergy balance not closed";
        return;
    end

    Qin_W = m_HS * (h_HS_in - h_HS_out);
    eta_ex_percent = output_kW * 1000 / max(Ein, eps) * 100;

    DT_hp_inlet = T_HS_in - T8;
    DT_hp_outlet = T_HS_3 - T5;
    DT_hp_lmtd = calc_lmtd(DT_hp_inlet, DT_hp_outlet);

    DT_lp_inlet = T_HS_3 - T4;
    DT_lp_outlet = T_HS_out - T2;
    DT_lp_lmtd = calc_lmtd(DT_lp_inlet, DT_lp_outlet);

    q_pre = m_f * (h3 - h2);
    q_lp_evap = m_O_LP * (h4p - h3);
    q_lp_sh = m_O_LP * (h4 - h4p);
    q_hp_pre = m_O_HP * (h6 - h5);
    q_hp_evap = m_O_HP * (h7 - h6);
    q_hp_sh = m_O_HP * (h8 - h7);

    details.feasible = true;
    details.fail_reason = "ok";
    details.net_output_kW = output_kW;
    details.eta_ex_percent = eta_ex_percent;
    details.DT_hp_lmtd_K = DT_hp_lmtd;
    details.DT_lp_lmtd_K = DT_lp_lmtd;
    details.T_HS_3 = T_HS_3;
    details.T_HS_4_req = T_HS_4_req;
    details.T_HS_out = T_HS_out;
    details.h_HS_in = h_HS_in;
    details.h_HS_3 = h_HS_3;
    details.h_HS_4_req = h_HS_4_req;
    details.h_HS_out = h_HS_out;
    details.m_O_HP = m_O_HP;
    details.m_O_LP = m_O_LP;
    details.m_f = m_f;
    details.T2 = T2;
    details.T3 = T3;
    details.T4p = T4p;
    details.T4 = T4;
    details.T5 = T5;
    details.T6 = T6;
    details.T7 = T7;
    details.T8 = T8;
    details.h2 = h2;
    details.h3 = h3;
    details.h4p = h4p;
    details.h4 = h4;
    details.h5 = h5;
    details.h6 = h6;
    details.h7 = h7;
    details.h8 = h8;
    details.q_pre_W = q_pre;
    details.q_lp_evap_W = q_lp_evap;
    details.q_lp_sh_W = q_lp_sh;
    details.q_hp_pre_W = q_hp_pre;
    details.q_hp_evap_W = q_hp_evap;
    details.q_hp_sh_W = q_hp_sh;
    details.Qin_W = Qin_W;

catch ME
    details.feasible = false;
    details.fail_reason = "exception: " + string(ME.message);
end
end


function plot_single_tq_curve(details, fluid, year_value, outpath)
[q_hot_MW, t_hot_C, q_cold_MW, t_cold_C, state_labels] = build_plot_series(details);

fig = figure('Color', 'w', 'Position', [120, 120, 860, 700]);
ax = axes(fig);
set(ax, 'Position', [0.10, 0.16, 0.86, 0.77]);
hold(ax, 'on');

plot(ax, q_hot_MW, t_hot_C, '-o', ...
    'Color', [0.20, 0.20, 0.20], ...
    'LineWidth', 2.2, ...
    'MarkerSize', 6.5, ...
    'MarkerFaceColor', [0.20, 0.20, 0.20], ...
    'DisplayName', '热源流体');

plot(ax, q_cold_MW, t_cold_C, '-s', ...
    'Color', [0.00, 0.45, 0.74], ...
    'LineWidth', 2.2, ...
    'MarkerSize', 6.0, ...
    'MarkerFaceColor', [0.00, 0.45, 0.74], ...
    'DisplayName', '工质');

 style_tq_axes_cn_v2(ax, fluid, year_value);
 add_cn_axis_text_v5(ax, fluid, year_value);
annotate_cold_states(ax, q_cold_MW, t_cold_C, state_labels);
annotate_hot_states(ax, q_hot_MW, t_hot_C);
lgd = legend(ax, 'Location', 'northwest', 'Box', 'off');
set(lgd, 'FontName', 'Microsoft YaHei UI', 'FontSize', 11);
add_bottom_xlabel_annotation(fig, ax);

exportgraphics(fig, outpath, 'Resolution', 300);
close(fig);
end


function plot_combined_tq_curves(results, year_value, outpath)
fig = figure('Color', 'w', 'Position', [80, 80, 1380, 740]);
tiledlayout(fig, 1, numel(results), 'Padding', 'loose', 'TileSpacing', 'loose');

for idx = 1:numel(results)
    nexttile;
    ax = gca;
    hold(ax, 'on');

    [q_hot_MW, t_hot_C, q_cold_MW, t_cold_C, state_labels] = build_plot_series(results(idx).details);
    plot(ax, q_hot_MW, t_hot_C, '-o', ...
        'Color', [0.20, 0.20, 0.20], ...
        'LineWidth', 2.1, ...
        'MarkerSize', 5.8, ...
        'MarkerFaceColor', [0.20, 0.20, 0.20], ...
        'DisplayName', '热源流体');
    plot(ax, q_cold_MW, t_cold_C, '-s', ...
        'Color', [0.00, 0.45, 0.74], ...
        'LineWidth', 2.1, ...
        'MarkerSize', 5.5, ...
        'MarkerFaceColor', [0.00, 0.45, 0.74], ...
        'DisplayName', '工质');

    style_tq_axes_cn_v2(ax, format_display_fluid(results(idx).fluid), year_value);
    add_cn_axis_text_v5(ax, format_display_fluid(results(idx).fluid), year_value);
    annotate_cold_states(ax, q_cold_MW, t_cold_C, state_labels);
    annotate_hot_states(ax, q_hot_MW, t_hot_C);
    if idx == 1
        lgd = legend(ax, 'Location', 'northwest', 'Box', 'off');
        set(lgd, 'FontName', 'Microsoft YaHei UI', 'FontSize', 11);
    end
    add_bottom_xlabel_annotation(fig, ax);
end

exportgraphics(fig, outpath, 'Resolution', 300);
close(fig);
end


function [q_hot_MW, t_hot_C, q_cold_MW, t_cold_C, state_labels] = build_plot_series(details)
q_pre = details.q_pre_W / 1e6;
q_lp_evap = details.q_lp_evap_W / 1e6;
q_lp_sh = details.q_lp_sh_W / 1e6;
q_hp_pre = details.q_hp_pre_W / 1e6;
q_hp_evap = details.q_hp_evap_W / 1e6;
q_hp_sh = details.q_hp_sh_W / 1e6;

q_hot_MW = [ ...
    0, ...
    q_pre, ...
    q_pre + q_lp_evap + q_lp_sh, ...
    q_pre + q_lp_evap + q_lp_sh + q_hp_pre + q_hp_evap + q_hp_sh];

t_hot_C = [ ...
    details.T_HS_out, ...
    details.T_HS_4_req, ...
    details.T_HS_3, ...
    details.T_HS_in] - 273.15;

q_cold_MW = [ ...
    0, ...
    q_pre, ...
    q_pre + q_lp_evap, ...
    q_pre + q_lp_evap + q_lp_sh, ...
    q_pre + q_lp_evap + q_lp_sh, ...
    q_pre + q_lp_evap + q_lp_sh + q_hp_pre, ...
    q_pre + q_lp_evap + q_lp_sh + q_hp_pre + q_hp_evap, ...
    q_pre + q_lp_evap + q_lp_sh + q_hp_pre + q_hp_evap + q_hp_sh];

t_cold_C = [ ...
    details.T2, ...
    details.T3, ...
    details.T4p, ...
    details.T4, ...
    details.T5, ...
    details.T6, ...
    details.T7, ...
    details.T8] - 273.15;

state_labels = {'2', '3', '4''', '4', '5', '6', '7', '8'};
end


function annotate_cold_states(ax, q_cold_MW, t_cold_C, state_labels)
q_span = max(q_cold_MW) - min(q_cold_MW);
t_span = max(t_cold_C) - min(t_cold_C);
dx = max(q_span * 0.012, 0.03);
dy = max(t_span * 0.020, 0.6);
x_limits = xlim(ax);
y_limits = ylim(ax);

for idx = 1:numel(state_labels)
    x = q_cold_MW(idx);
    y = t_cold_C(idx);
    if x < x_limits(1) || x > x_limits(2) || y < y_limits(1) || y > y_limits(2)
        continue;
    end

    if idx == 1
        tx = x + dx;
        ty = y - dy * 1.1;
    elseif idx == 2
        tx = x + dx * 0.7;
        ty = y - dy * 1.1;
    elseif idx == 3
        tx = x + dx * 0.7;
        ty = y - dy * 2.2;
    elseif idx == 4
        tx = x + dx * 0.3;
        ty = y - dy * 3.2;
    elseif idx == 5
        tx = x + dx * 0.3;
        ty = y + dy * 0.8;
    elseif idx == 6
        tx = x + dx * 0.8;
        ty = y - dy * 0.9;
    elseif idx == numel(state_labels)
        tx = x - dx * 1.7;
        ty = y + dy * 0.6;
    else
        tx = x + dx;
        ty = y - dy;
    end

    text(ax, tx, ty, state_labels{idx}, ...
        'FontName', 'Times New Roman', ...
        'FontSize', 11, ...
        'Color', [0.00, 0.45, 0.74], ...
        'Clipping', 'on');
end
end


function annotate_hot_states(ax, q_hot_MW, t_hot_C)
q_span = max(q_hot_MW) - min(q_hot_MW);
t_span = max(t_hot_C) - min(t_hot_C);
dx = max(q_span * 0.012, 0.03);
dy = max(t_span * 0.020, 0.6);
x_limits = xlim(ax);
y_limits = ylim(ax);

labels = {'T_{HS,out}', 'T_{HS,4}', 'T_{HS,3}', 'T_{HS,in}'};
offsets = [ ...
    dx,         dy * 0.5; ...
   -dx * 1.5,  dy * 1.5; ...
    dx * 0.7,  dy * 1.3; ...
   -dx * 2.6, -dy * 0.8];

for idx = 1:numel(labels)
    if q_hot_MW(idx) < x_limits(1) || q_hot_MW(idx) > x_limits(2) || ...
            t_hot_C(idx) < y_limits(1) || t_hot_C(idx) > y_limits(2)
        continue;
    end
    text(ax, q_hot_MW(idx) + offsets(idx, 1), t_hot_C(idx) + offsets(idx, 2), labels{idx}, ...
        'Interpreter', 'tex', ...
        'FontName', 'Times New Roman', ...
        'FontSize', 11.5, ...
        'Color', [0.20, 0.20, 0.20], ...
        'Clipping', 'on');
end
end


function style_tq_axes(ax, fluid, year_value)
title(ax, sprintf('%s, year = %.0f', fluid, year_value), ...
    'FontName', 'Times New Roman', 'FontSize', 15, 'FontWeight', 'bold');
xlabel(ax, 'Heat transfer rate Q (MW)', 'FontName', 'Times New Roman', 'FontSize', 13);
ylabel(ax, 'Temperature T (°C)', 'FontName', 'Times New Roman', 'FontSize', 13);
set(ax, 'FontName', 'Times New Roman', 'FontSize', 11, 'LineWidth', 1.2, 'Box', 'on');
set(ax.Title, 'FontName', 'Microsoft YaHei UI', 'FontWeight', 'bold', 'Interpreter', 'none');
set(ax.XLabel, 'FontName', 'Microsoft YaHei UI', 'Interpreter', 'none');
set(ax.YLabel, 'FontName', 'Microsoft YaHei UI', 'Interpreter', 'none');
grid(ax, 'off');
end


function style_tq_axes_cn(ax, fluid, year_value)
title(ax, sprintf('%s，%.0f 年', fluid, year_value), ...
    'FontName', 'Microsoft YaHei UI', 'FontSize', 15, 'FontWeight', 'bold', 'Interpreter', 'none');
xlabel(ax, '热流率 Q (MW)', 'FontName', 'Microsoft YaHei UI', 'FontSize', 13);
ylabel(ax, '温度 T (°C)', 'FontName', 'Microsoft YaHei UI', 'FontSize', 13);
xlim(ax, [0.0, 50.0]);
ylim(ax, [110.0, 150.0]);
set(ax, 'FontName', 'Times New Roman', 'FontSize', 11, 'LineWidth', 1.2, 'Box', 'on');
title(ax, '');
xlabel(ax, '');
ylabel(ax, '');
grid(ax, 'off');
end


function add_cn_axis_text(ax, fluid, year_value)
text(ax, 0.5, 1.015, sprintf('%s，%.0f 年', fluid, year_value), ...
    'Units', 'normalized', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'bottom', ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 15, ...
    'FontWeight', 'bold', ...
    'Interpreter', 'none', ...
    'Clipping', 'off');
text(ax, 0.5, -0.020, '热流率 Q (MW)', ...
    'Units', 'normalized', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'top', ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 13, ...
    'Interpreter', 'none', ...
    'Clipping', 'off');
text(ax, -0.065, 0.5, '温度 T (°C)', ...
    'Units', 'normalized', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'middle', ...
    'Rotation', 90, ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 13, ...
    'Interpreter', 'none', ...
    'Clipping', 'off');
end


function style_tq_axes_cn_v2(ax, fluid, year_value)
title(ax, '');
xlabel(ax, '');
ylabel(ax, '');
xlim(ax, [0.0, 50.0]);
ylim(ax, [0.0, 150.0]);
set(ax, 'FontName', 'Times New Roman', 'FontSize', 11, 'LineWidth', 1.2, 'Box', 'on');
grid(ax, 'off');
end


function add_cn_axis_text_v2(ax, fluid, year_value)
text(ax, 0.5, 0.992, sprintf('%s，%.0f 年', fluid, year_value), ...
    'Units', 'normalized', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'top', ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 15, ...
    'FontWeight', 'bold', ...
    'Interpreter', 'none', ...
    'BackgroundColor', 'white', ...
    'Margin', 1, ...
    'Clipping', 'off');
text(ax, 0.5, -0.020, '热流率 Q (MW)', ...
    'Units', 'normalized', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'top', ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 13, ...
    'Interpreter', 'none', ...
    'Clipping', 'off');
text(ax, -0.065, 0.5, '温度 T (°C)', ...
    'Units', 'normalized', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'middle', ...
    'Rotation', 90, ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 13, ...
    'Interpreter', 'none', ...
    'Clipping', 'off');
end


function add_cn_axis_text_v3(ax, fluid, year_value)
text(ax, 0.5, 0.992, sprintf('%s，%.0f 年', fluid, year_value), ...
    'Units', 'normalized', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'top', ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 15, ...
    'FontWeight', 'bold', ...
    'Interpreter', 'none', ...
    'BackgroundColor', 'white', ...
    'Margin', 1, ...
    'Clipping', 'off');
text(ax, 0.5, -0.006, '热流率 Q (MW)', ...
    'Units', 'normalized', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'top', ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 13, ...
    'Interpreter', 'none', ...
    'Clipping', 'off');
text(ax, -0.065, 0.5, '温度 T (°C)', ...
    'Units', 'normalized', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'middle', ...
    'Rotation', 90, ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 13, ...
    'Interpreter', 'none', ...
    'Clipping', 'off');
end


function add_bottom_xlabel_annotation(fig, ax)
pos = get(ax, 'Position');
h_xlabel = annotation(fig, 'textbox', [pos(1), max(0.020, pos(2) - 0.036), pos(3), 0.050], ...
    'String', '热流率 Q (MW)', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'middle', ...
    'LineStyle', 'none', ...
    'BackgroundColor', 'white', ...
    'FitBoxToText', 'off', ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 13, ...
    'Interpreter', 'none');
set(h_xlabel, 'String', cn_label_x());
end

%{
function add_cn_axis_text_v4(ax, fluid, year_value)
text(ax, 0.5, 0.985, sprintf('%s锛?.0f 骞?, fluid, year_value), ...
    'Units', 'normalized', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'top', ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 15, ...
    'FontWeight', 'bold', ...
    'Interpreter', 'none', ...
    'BackgroundColor', 'white', ...
    'Margin', 1, ...
    'Clipping', 'off');
text(ax, -0.065, 0.5, '娓╁害 T (掳C)', ...
    'Units', 'normalized', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'middle', ...
    'Rotation', 90, ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 13, ...
    'Interpreter', 'none', ...
    'Clipping', 'off');
end

%}

function add_cn_axis_text_v5(ax, fluid, year_value)
text(ax, 0.5, 0.985, cn_title(fluid, year_value), ...
    'Units', 'normalized', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'top', ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 15, ...
    'FontWeight', 'bold', ...
    'Interpreter', 'none', ...
    'BackgroundColor', 'white', ...
    'Margin', 1, ...
    'Clipping', 'off');
text(ax, -0.065, 0.5, cn_label_y(), ...
    'Units', 'normalized', ...
    'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'middle', ...
    'Rotation', 90, ...
    'FontName', 'Microsoft YaHei UI', ...
    'FontSize', 13, ...
    'Interpreter', 'none', ...
    'Clipping', 'off');
end


function out = cn_title(fluid, year_value)
out = sprintf('%s, %.0f %s', fluid, year_value, char(24180));
end


function out = cn_label_x()
out = [char([28909, 27969, 29575]), ' Q (MW)'];
end


function out = cn_label_y()
out = [char([28201, 24230]), ' T (', char(176), 'C)'];
end


function summary_tbl = build_summary_table(results)
n = numel(results);
fluid = strings(n, 1);
year = zeros(n, 1);
T_HS_in_K = zeros(n, 1);
P_e_lp_kPa = zeros(n, 1);
P_e_hp_kPa = zeros(n, 1);
DT_sh_lp_K = zeros(n, 1);
DT_sh_hp_K = zeros(n, 1);
match_score = zeros(n, 1);
net_output_target_kW = zeros(n, 1);
net_output_recovered_kW = zeros(n, 1);
lmtd_hp_target_K = zeros(n, 1);
lmtd_hp_recovered_K = zeros(n, 1);
lmtd_lp_target_K = zeros(n, 1);
lmtd_lp_recovered_K = zeros(n, 1);
single_figure = strings(n, 1);

for idx = 1:n
    fluid(idx) = string(results(idx).fluid);
    year(idx) = results(idx).year;
    T_HS_in_K(idx) = results(idx).target_row.T_HS_in_K;
    P_e_lp_kPa(idx) = results(idx).target_row.P_e_lp_kPa;
    P_e_hp_kPa(idx) = results(idx).target_row.P_e_hp_kPa;
    DT_sh_lp_K(idx) = results(idx).recovered.DT_sh_lp_K;
    DT_sh_hp_K(idx) = results(idx).recovered.DT_sh_hp_K;
    match_score(idx) = results(idx).recovered.match_score;
    net_output_target_kW(idx) = results(idx).target_row.net_output_kW;
    net_output_recovered_kW(idx) = results(idx).details.net_output_kW;
    lmtd_hp_target_K(idx) = results(idx).target_row.lmtd_hp_K;
    lmtd_hp_recovered_K(idx) = results(idx).details.DT_hp_lmtd_K;
    lmtd_lp_target_K(idx) = results(idx).target_row.lmtd_lp_K;
    lmtd_lp_recovered_K(idx) = results(idx).details.DT_lp_lmtd_K;
    single_figure(idx) = results(idx).single_outpath;
end

summary_tbl = table( ...
    fluid, year, T_HS_in_K, P_e_lp_kPa, P_e_hp_kPa, ...
    DT_sh_lp_K, DT_sh_hp_K, match_score, ...
    net_output_target_kW, net_output_recovered_kW, ...
    lmtd_hp_target_K, lmtd_hp_recovered_K, ...
    lmtd_lp_target_K, lmtd_lp_recovered_K, ...
    single_figure);
end


function out = format_year_for_filename(year_value)
if abs(year_value - round(year_value)) < 1e-9
    out = sprintf('%d', round(year_value));
else
    out = strrep(sprintf('%.3f', year_value), '.', 'p');
end
end


function dt_avg = calc_lmtd(dt1, dt2)
if ~isfinite(dt1) || ~isfinite(dt2) || dt1 <= 0 || dt2 <= 0
    dt_avg = NaN;
elseif abs(dt1 - dt2) < 1e-9
    dt_avg = dt1;
else
    dt_avg = (dt1 - dt2) / log(dt1 / dt2);
end
end
