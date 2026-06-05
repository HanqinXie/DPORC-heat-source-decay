clear; clc;

overall_timer = tic;
setup_timer = tic;
fprintf('Script started at %s\n', char(datetime('now', 'Format', 'yyyy-MM-dd HH:mm:ss')));
fprintf('Initializing inputs and thermophysical properties...\n');

WF = 'ISOBUTANE';
HS_fluid = 'water';
cool_fluid = 'water';

source_temp_C = 150;
year_now = 0;
P_e_lp_fixed_kPa = 1250;
P_e_hp_fixed_kPa = 2530;
DT_sh_hp_fixed_K = 2;
DT_sh_lp_fixed_K = 0.01;
match_literature_targets = false;

literature.W_net_kW = 969.7;
literature.eta_thermal_percent = 5.54;
literature.eta_sys_percent = 2.895;
literature.m_HP_kg_s = 68.0;
literature.m_LP_kg_s = 46.1;

m_HS = 100;
P_HS = 0.5 * 1e3;
T_0 = 20 + 273.15;
delta_T_HAP_pp = 10;
delta_T_cond_pp = 10;
T_cool_in = 20 + 273.15;
T_cond = 35 + 273.15;
T_cool_out = T_cond - delta_T_cond_pp;
delta_T_cool = T_cool_out - T_cool_in;
delta_T_subcool = 2;
P_cool = 0.101 * 1e3;
eta_p = 0.70;
eta_T = 0.85;

P_cond = refpropm_cached('P', 'T', T_cond, 'Q', 0, WF);
T1 = T_cond - delta_T_subcool;
[h1, s1] = refpropm_cached('HS', 'T', T1, 'P', P_cond, WF);
[T12, h12, ~] = refpropm_cached('THS', 'P', P_cond, 'Q', 1, WF);
T_cw_12_req = T12 - delta_T_cond_pp;
h_cw_12_req = refpropm_cached('H', 'T', T_cw_12_req, 'P', P_cool, cool_fluid);

[h_HS_0, s_HS_0] = refpropm_cached('HS', 'T', T_0, 'P', P_HS, HS_fluid);
h_cool_in = refpropm_cached('H', 'T', T_cool_in, 'P', P_cool, cool_fluid);
P_c = refpropm_cached('P', 'C', 0, ' ', 0, WF);

P_e_lp1_max = P_c - 300;
T_e_lp1_max = refpropm_cached('T', 'P', P_e_lp1_max, 'Q', 0, WF);
P_e_hp1_max = P_c - 300;
T_e_hp1_max = refpropm_cached('T', 'P', P_e_hp1_max, 'Q', 0, WF);

P_e_lp_min = P_cond + 100;
P_e_hp_min = P_e_lp_min + 100;
mw_denom = h_cw_12_req - h_cool_in;

search.coarse.name = 'coarse';
search.coarse.lp_n = 1;
search.coarse.hp_n = 1;
search.coarse.sh_n = 1;
search.coarse.initial_capacity = 512;
search.coarse.fixed_DT_sh_hp_K = DT_sh_hp_fixed_K;
search.coarse.fixed_DT_sh_lp_K = DT_sh_lp_fixed_K;

search.fine.name = 'refined';
search.fine.lp_n_full = 1;
search.fine.hp_n_full = 1;
search.fine.sh_n_full = 1;
search.fine.initial_capacity = 2048;
search.fine.restrict_superheat = false;
search.fine.fixed_DT_sh_hp_K = DT_sh_hp_fixed_K;
search.fine.fixed_DT_sh_lp_K = DT_sh_lp_fixed_K;

search.refine.relative_output_band = 0.02;
search.refine.min_candidates = 24;
search.refine.max_candidates = 80;
search.refine.lp_margin_steps = 2;
search.refine.hp_margin_steps = 2;
search.refine.sh_margin_K = 6;
search.refine.min_lp_span_steps = 4;
search.refine.min_hp_span_steps = 4;
search.refine.min_sh_span_K = 4;
search.refine.expand_factor = 1.75;
search.refine.max_boxes = 6;
search.refine.anchor_lp_gap_steps = 3;
search.refine.anchor_hp_gap_steps = 3;
search.refine.anchor_sh_gap_K = 5;

base_const = struct();
base_const.WF = WF;
base_const.HS_fluid = HS_fluid;
base_const.cool_fluid = cool_fluid;
base_const.source_temp_C = source_temp_C;
base_const.P_e_lp_fixed_kPa = P_e_lp_fixed_kPa;
base_const.P_e_hp_fixed_kPa = P_e_hp_fixed_kPa;
base_const.DT_sh_hp_fixed_K = DT_sh_hp_fixed_K;
base_const.DT_sh_lp_fixed_K = DT_sh_lp_fixed_K;
base_const.match_literature_targets = match_literature_targets;
base_const.literature = literature;
base_const.m_HS = m_HS;
base_const.P_HS = P_HS;
base_const.T_0 = T_0;
base_const.delta_T_HAP_pp = delta_T_HAP_pp;
base_const.delta_T_cond_pp = delta_T_cond_pp;
base_const.T_cool_in = T_cool_in;
base_const.T_cool_out = T_cool_out;
base_const.P_cool = P_cool;
base_const.eta_p = eta_p;
base_const.eta_T = eta_T;
base_const.P_cond = P_cond;
base_const.h1 = h1;
base_const.s1 = s1;
base_const.T1 = T1;
base_const.T12 = T12;
base_const.h12 = h12;
base_const.h_HS_0 = h_HS_0;
base_const.s_HS_0 = s_HS_0;
base_const.P_e_lp_min = P_e_lp_min;
base_const.P_e_hp_min = P_e_hp_min;
base_const.P_e_lp1_max = P_e_lp1_max;
base_const.T_e_lp1_max = T_e_lp1_max;
base_const.P_e_hp1_max = P_e_hp1_max;
base_const.T_e_hp1_max = T_e_hp1_max;
base_const.mw_denom = mw_denom;

fprintf('Initialization finished in %.2f s.\n', toc(setup_timer));
pool = gcp('nocreate');
if isempty(pool)
    fprintf('Starting parallel pool (Processes)...\n');
    pool_timer = tic;
    pool = parpool('Processes');
    fprintf('Parallel pool ready with %d workers in %.2f s.\n', pool.NumWorkers, toc(pool_timer));
else
    fprintf('Reusing existing parallel pool with %d workers.\n', pool.NumWorkers);
end

variable_names = { ...
    'P_e_lp_kPa', 'P_e_hp_kPa', 'T_sat_lp_K', 'T_sat_hp_K', ...
    'W_net_kW', 'eta_thermal_percent', 'eta_sys_percent', ...
    'm_HP_kg_s', 'm_LP_kg_s'};

timestamp = char(datetime('now', 'Format', 'yyyy-MM-dd_HH-mm-ss'));
script_dir = fileparts(mfilename('fullpath'));
if isempty(script_dir)
    script_dir = pwd;
end
filename = fullfile(script_dir, sprintf('%s_%gC_Plp%g_Php%g_validation_%s.csv', ...
    WF, source_temp_C, P_e_lp_fixed_kPa, P_e_hp_fixed_kPa, timestamp));

fprintf('Validation result will be written to %s\n', filename);
run_timer = tic;
[year_rows, year_log] = run_year_optimization(year_now, search, base_const);

if isempty(year_rows)
    error('validate_R1234yf_150C_fixed:NoFeasibleSolution', ...
        'No feasible solution was found at %.2f C.', source_temp_C);
end

best_row = year_rows(1, :);
result_values = [ ...
    best_row(20), best_row(21), best_row(24), best_row(25), ...
    best_row(3), best_row(26), best_row(27), best_row(28), best_row(29)];
result_table = array2table(result_values, 'VariableNames', variable_names);

disp(result_table);
writetable(result_table, filename);

fprintf(['Fixed %.2f C validation finished with %d feasible rows. ' ...
         'Fixed P_lp = %.2f kPa, P_hp = %.2f kPa. ' ...
         'Selected W_net = %.3f kW, eta_thermal = %.3f%%, eta_sys = %.3f%%. Elapsed %.2f s.\n'], ...
    year_log.T_HS_in - 273.15, size(year_rows, 1), ...
    best_row(20), best_row(21), best_row(3), best_row(26), best_row(27), toc(run_timer));
fprintf('Selected superheat: LP = %.3f K, HP = %.3f K.\n', ...
    best_row(22) - best_row(24), best_row(23) - best_row(25));
fprintf(['Literature deltas: dW = %.3f kW, deta_thermal = %.3f%%, ' ...
         'deta_sys = %.3f%%, dm_HP = %.3f kg/s, dm_LP = %.3f kg/s.\n'], ...
    best_row(3) - literature.W_net_kW, ...
    best_row(26) - literature.eta_thermal_percent, ...
    best_row(27) - literature.eta_sys_percent, ...
    best_row(28) - literature.m_HP_kg_s, ...
    best_row(29) - literature.m_LP_kg_s);
fprintf('Validation results have been saved to %s\n', filename);

fprintf('Script finished in %.2f s.\n', toc(overall_timer));

function [year_rows, year_log] = run_year_optimization(year_now, search, base_const)
year_rows = zeros(0, 29);
year_log = struct('T_HS_in', NaN);

T_HS_in = base_const.source_temp_C + 273.15;
year_log.T_HS_in = T_HS_in;
fprintf('Fixed source temperature: %.2f C.\n', T_HS_in - 273.15);

[h_HS_in, s_HS_in] = refpropm_cached('HS', 'T', T_HS_in, 'P', base_const.P_HS, base_const.HS_fluid);
Ein = base_const.m_HS * ((h_HS_in - base_const.h_HS_0) - base_const.T_0 * (s_HS_in - base_const.s_HS_0));
eta_exergy_factor = 1000 * 100 / max(Ein, eps);

if (T_HS_in - base_const.T_e_lp1_max) >= base_const.delta_T_HAP_pp
    P_e_lp_max = base_const.P_e_lp1_max;
else
    P_e_lp_max = refpropm_cached('P', 'T', T_HS_in - base_const.delta_T_HAP_pp, 'Q', 0, base_const.WF);
end

if (T_HS_in - base_const.T_e_hp1_max) >= base_const.delta_T_HAP_pp
    P_e_hp_max = base_const.P_e_hp1_max;
else
    P_e_hp_max = refpropm_cached('P', 'T', T_HS_in - base_const.delta_T_HAP_pp, 'Q', 0, base_const.WF);
end

if ~(isfinite(P_e_lp_max) && isfinite(P_e_hp_max))
    fprintf('Pressure bounds are not finite.\n');
    return;
end

if P_e_lp_max <= base_const.P_e_lp_min || P_e_hp_max <= base_const.P_e_hp_min
    fprintf('Pressure bounds invalid for current heat source.\n');
    return;
end

P_e_lp_target = base_const.P_e_lp_fixed_kPa;
P_e_hp_target = base_const.P_e_hp_fixed_kPa;
if P_e_lp_target < base_const.P_e_lp_min || P_e_lp_target > P_e_lp_max || ...
        P_e_hp_target < base_const.P_e_hp_min || P_e_hp_target > P_e_hp_max || ...
        P_e_hp_target <= P_e_lp_target + 100
    fprintf(['Fixed pressure point is outside feasible pressure bounds: ' ...
             'P_lp = %.2f kPa, P_hp = %.2f kPa, ' ...
             'LP bounds = [%.2f, %.2f], HP bounds = [%.2f, %.2f].\n'], ...
        P_e_lp_target, P_e_hp_target, ...
        base_const.P_e_lp_min, P_e_lp_max, base_const.P_e_hp_min, P_e_hp_max);
    return;
end

const = base_const;
const.year_now = year_now;
const.T_HS_in = T_HS_in;
const.h_HS_in = h_HS_in;
const.s_HS_in = s_HS_in;
const.P_e_lp_min = P_e_lp_target;
const.P_e_lp_max = P_e_lp_target;
const.P_e_hp_min = P_e_hp_target;
const.P_e_hp_max = P_e_hp_target;
const.T8max_global = T_HS_in - base_const.delta_T_HAP_pp;
const.Ein = Ein;
const.eta_exergy_factor = eta_exergy_factor;

fprintf('Fixed pressure point: P_lp = %.2f kPa, P_hp = %.2f kPa.\n', ...
    P_e_lp_target, P_e_hp_target);
fprintf('Stage 1 coarse search: %d x %d pressure point, %d x %d superheat points.\n', ...
    search.coarse.lp_n, search.coarse.hp_n, search.coarse.sh_n, search.coarse.sh_n);
coarse_timer = tic;
coarse_candidates = run_search_stage(search.coarse, const, []);
fprintf('Stage 1 finished in %.2f s with %d feasible points.\n', toc(coarse_timer), size(coarse_candidates, 1));

if isempty(coarse_candidates)
    return;
end

refine_boxes = build_refine_boxes(coarse_candidates, search, const);
refine_boxes = deduplicate_refine_boxes(refine_boxes, search.fine);
fprintf('Stage 2 refined search will evaluate %d local windows.\n', numel(refine_boxes));
fine_lp_step = (const.P_e_lp_max - const.P_e_lp_min) / max(search.fine.lp_n_full - 1, 1);
fprintf('Stage 2 refined search: LP step <= %.3f kPa, HP/SH step targets matched to the original fine grid.\n', fine_lp_step);
fine_timer = tic;
fine_candidates = run_refined_windows(search.fine, const, refine_boxes);
fprintf('Stage 2 finished in %.2f s with %d feasible points.\n', toc(fine_timer), size(fine_candidates, 1));

if isempty(fine_candidates)
    fprintf('Refined windows returned no feasible points. Expanding each window once and retrying...\n');
    refine_boxes = expand_refine_boxes(refine_boxes, search, const);
    refine_boxes = deduplicate_refine_boxes(refine_boxes, search.fine);
    fine_timer = tic;
    fine_candidates = run_refined_windows(search.fine, const, refine_boxes);
    fprintf('Expanded stage 2 finished in %.2f s with %d feasible points.\n', toc(fine_timer), size(fine_candidates, 1));
end

if isempty(fine_candidates)
    fprintf('Falling back to the coarse feasible set because refined search stayed empty.\n');
    year_candidates = coarse_candidates;
else
    year_candidates = fine_candidates;
end

year_rows = sort_candidate_rows(year_candidates, const);
end

function candidate_rows = run_search_stage(stage, const, refine_box)
is_refined = ~isempty(refine_box);
restrict_superheat = is_refined && isfield(stage, 'restrict_superheat') && stage.restrict_superheat;
if is_refined
    lp_low = max(const.P_e_lp_min, refine_box.lp_low);
    lp_high = min(const.P_e_lp_max, refine_box.lp_high);
else
    lp_low = const.P_e_lp_min;
    lp_high = const.P_e_lp_max;
end

if lp_high < lp_low
    candidate_rows = zeros(0, 29);
    return;
end

if isfield(stage, 'lp_n')
    lp_list = linspace(lp_low, lp_high, stage.lp_n);
else
    lp_step = max((const.P_e_lp_max - const.P_e_lp_min) / max(stage.lp_n_full - 1, 1), 1e-6);
    lp_list = build_axis(lp_low, lp_high, lp_step);
end

if isempty(lp_list)
    candidate_rows = zeros(0, 29);
    return;
end

candidate_cells = cell(1, numel(lp_list));
parfor i_lp = 1:numel(lp_list)
    local_capacity = stage.initial_capacity;
    local_rows = zeros(local_capacity, 29);
    lc = 0;

    P_e_lp_local = lp_list(i_lp);
    T_e_lp_local = refpropm_cached('T', 'P', P_e_lp_local, 'Q', 0, const.WF);
    if ~isfinite(T_e_lp_local)
        candidate_cells{i_lp} = zeros(0, 29);
        continue;
    end

    h2_ideal = refpropm_cached('H', 'P', P_e_lp_local, 'S', const.s1, const.WF);
    deltah_21 = (h2_ideal - const.h1) / const.eta_p;
    h2 = const.h1 + deltah_21;
    [s2, T2] = refpropm_cached('ST', 'P', P_e_lp_local, 'H', h2, const.WF);

    T3 = T_e_lp_local;
    [h3, s3] = refpropm_cached('HS', 'T', T3, 'Q', 0, const.WF);
    T_HS_4_req = T3 + const.delta_T_HAP_pp;
    h_HS_4_req = refpropm_cached('H', 'T', T_HS_4_req, 'P', const.P_HS, const.HS_fluid);

    hp_min_local = max(const.P_e_hp_min, P_e_lp_local + 100);
    if is_refined
        hp_low = max(hp_min_local, refine_box.hp_low);
        hp_high = min(const.P_e_hp_max, refine_box.hp_high);
    else
        hp_low = hp_min_local;
        hp_high = const.P_e_hp_max;
    end

    if hp_high < hp_low
        candidate_cells{i_lp} = zeros(0, 29);
        continue;
    end

    if isfield(stage, 'hp_n')
        P_hp_list = linspace(hp_low, hp_high, stage.hp_n);
    else
        hp_step = max((const.P_e_hp_max - hp_min_local) / max(stage.hp_n_full - 1, 1), 1e-6);
        P_hp_list = build_axis(hp_low, hp_high, hp_step);
    end

    for i_hp = 1:numel(P_hp_list)
        P_e_hp_local = P_hp_list(i_hp);
        T_e_hp_local = refpropm_cached('T', 'P', P_e_hp_local, 'Q', 0, const.WF);
        if ~isfinite(T_e_hp_local)
            continue;
        end

        h5_ideal = refpropm_cached('H', 'P', P_e_hp_local, 'S', s3, const.WF);
        deltah_53 = (h5_ideal - h3) / const.eta_p;
        h5 = h3 + deltah_53;
        [s5, T5] = refpropm_cached('ST', 'P', P_e_hp_local, 'H', h5, const.WF);

        T6 = T_e_hp_local;
        [h6, ~] = refpropm_cached('HS', 'T', T6, 'Q', 0, const.WF);
        [T7, ~, ~] = refpropm_cached('THS', 'P', P_e_hp_local, 'Q', 1, const.WF);
        T8min = T7 + 2;
        T8max = const.T8max_global;
        if ~(isfinite(T8min) && isfinite(T8max) && T8max >= T8min)
            continue;
        end

        if isfield(stage, 'fixed_DT_sh_hp_K')
            T8_list = T7 + stage.fixed_DT_sh_hp_K;
            if T8_list < T8min - 1e-9 || T8_list > T8max + 1e-9
                continue;
            end
        else
            if restrict_superheat
                T8low = max(T8min, T7 + refine_box.sh_hp_low);
                T8high = min(T8max, T7 + refine_box.sh_hp_high);
            else
                T8low = T8min;
                T8high = T8max;
            end

            if T8high < T8low
                continue;
            end

            if isfield(stage, 'sh_n')
                T8_list = linspace(T8low, T8high, stage.sh_n);
            else
                T8_step = max((T8max - T8min) / max(stage.sh_n_full - 1, 1), 1e-6);
                T8_list = build_axis(T8low, T8high, T8_step);
            end
        end

        T_HS_6_req = T6 + const.delta_T_HAP_pp;
        h_HS_6_req = refpropm_cached('H', 'T', T_HS_6_req, 'P', const.P_HS, const.HS_fluid);

        for j_hp = 1:numel(T8_list)
            T8 = T8_list(j_hp);
            [h8, s8] = refpropm_cached('HS', 'T', T8, 'P', P_e_hp_local, const.WF);
            if ~(isfinite(h8) && isfinite(s8))
                continue;
            end

            m_O_HP = const.m_HS * (const.h_HS_in - h_HS_6_req) / (h8 - h6);
            if ~(isfinite(m_O_HP) && m_O_HP > 0)
                continue;
            end

            h_HS_3 = h_HS_6_req - m_O_HP * (h6 - h5) / const.m_HS;
            T_HS_3 = refpropm_cached('T', 'H', h_HS_3, 'P', const.P_HS, const.HS_fluid);
            if (T_HS_3 - T5) < const.delta_T_HAP_pp
                T_HS_3 = T5 + const.delta_T_HAP_pp;
                h_HS_3 = refpropm_cached('H', 'T', T_HS_3, 'P', const.P_HS, const.HS_fluid);
                m_O_HP = const.m_HS * (const.h_HS_in - h_HS_3) / (h8 - h5);
                if ~(isfinite(m_O_HP) && m_O_HP > 0)
                    continue;
                end
            end

            T4min = T_e_lp_local + 0.01;
            T4max = T_HS_3 - const.delta_T_HAP_pp;
            if ~(isfinite(T4min) && isfinite(T4max) && T4max >= T4min)
                continue;
            end

            if isfield(stage, 'fixed_DT_sh_lp_K')
                T4_list = T_e_lp_local + stage.fixed_DT_sh_lp_K;
                if T4_list < T4min - 1e-9 || T4_list > T4max + 1e-9
                    continue;
                end
            else
                if restrict_superheat
                    T4low = max(T4min, T_e_lp_local + refine_box.sh_lp_low);
                    T4high = min(T4max, T_e_lp_local + refine_box.sh_lp_high);
                else
                    T4low = T4min;
                    T4high = T4max;
                end

                if T4high < T4low
                    continue;
                end

                if isfield(stage, 'sh_n')
                    T4_list = linspace(T4low, T4high, stage.sh_n);
                else
                    T4_step = max((T4max - T4min) / max(stage.sh_n_full - 1, 1), 1e-6);
                    T4_list = build_axis(T4low, T4high, T4_step);
                end
            end

            for j_lp = 1:numel(T4_list)
                T4 = T4_list(j_lp);
                [h4, s4] = refpropm_cached('HS', 'T', T4, 'P', P_e_lp_local, const.WF);
                if ~(isfinite(h4) && isfinite(s4))
                    continue;
                end

                m_O_LP = const.m_HS * (h_HS_3 - h_HS_4_req) / (h4 - h3);
                if ~(isfinite(m_O_LP) && m_O_LP > 0)
                    continue;
                end

                m_f_temp = m_O_LP + m_O_HP;
                h_HS_out = h_HS_4_req - m_f_temp * (h3 - h2) / const.m_HS;
                [T_HS_out, s_HS_out] = refpropm_cached('Ts', 'H', h_HS_out, 'P', const.P_HS, const.HS_fluid);
                if (T_HS_out - T2) < const.delta_T_HAP_pp
                    T_HS_out = T2 + const.delta_T_HAP_pp;
                    h_HS_out = refpropm_cached('H', 'T', T_HS_out, 'P', const.P_HS, const.HS_fluid);
                    [~, s_HS_out] = refpropm_cached('Ts', 'H', h_HS_out, 'P', const.P_HS, const.HS_fluid);
                    m_O_LP = (const.m_HS * (h_HS_3 - h_HS_out) - m_O_HP * (h3 - h2)) / (h4 - h2);
                    if ~(isfinite(m_O_LP) && m_O_LP > 0)
                        continue;
                    end
                end

                m_f = m_O_LP + m_O_HP;
                h9s = refpropm_cached('H', 'P', P_e_lp_local, 'S', s8, const.WF);
                deltah_89 = (h8 - h9s) * const.eta_T;
                h9 = h8 - deltah_89;
                s9 = refpropm_cached('S', 'P', P_e_lp_local, 'H', h9, const.WF);

                h10 = (m_O_LP * h4 + m_O_HP * h9) / m_f;
                [~, s10] = refpropm_cached('TS', 'P', P_e_lp_local, 'H', h10, const.WF);

                h11s = refpropm_cached('H', 'P', const.P_cond, 'S', s10, const.WF);
                deltah_1011 = (h10 - h11s) * const.eta_T;
                h11 = h10 - deltah_1011;
                s11 = refpropm_cached('S', 'P', const.P_cond, 'H', h11, const.WF);
                T11 = refpropm_cached('T', 'P', const.P_cond, 'H', h11, const.WF);
                if h11 <= const.h1
                    continue;
                end

                mw = m_f * (const.h12 - const.h1) / const.mw_denom;
                if ~(isfinite(mw) && mw > 0)
                    continue;
                end

                if (T11 - const.T_cool_out) < const.delta_T_cond_pp
                    continue;
                end

                power_t_high = m_O_HP * deltah_89 / 1000;
                power_t_low = m_f * deltah_1011 / 1000;
                power_p1 = m_f * deltah_21 / 1000;
                power_p2 = m_O_HP * deltah_53 / 1000;
                power_w = m_f * (h11 - const.h1) / (100 * 1000);
                output = power_t_high + power_t_low - power_p1 - power_p2 - power_w;
                if ~(isfinite(output) && output > 0)
                    continue;
                end

                Ede = const.m_HS * ((const.h_HS_in - h_HS_out) - const.T_0 * (const.s_HS_in - s_HS_out)) - ...
                    (m_O_HP * (h8 - h5) + m_O_LP * (h4 - h3) + m_f * (h3 - h2)) + ...
                    const.T_0 * (m_O_HP * (s8 - s5) + m_O_LP * (s4 - s3) + m_f * (s3 - s2));
                Edt_h = m_O_HP * const.T_0 * (s9 - s8);
                Edt_l = m_f * const.T_0 * (s11 - s10);
                Edt = Edt_h + Edt_l;
                Edp_1 = m_f * const.T_0 * (s2 - const.s1);
                Edp_2 = m_O_HP * const.T_0 * (s5 - s3);
                Edp = Edp_1 + Edp_2;
                Edmix = m_O_HP * (h9 - const.T_0 * s9) + m_O_LP * (h4 - const.T_0 * s4) - m_f * (h10 - const.T_0 * s10);
                Edc = m_f * ((h11 - const.h1) - const.T_0 * (s11 - const.s1));
                Ed_total = Ede + Edt + Edp + Edmix + Edc;
                if ~(isfinite(Ed_total) && Ed_total > 0)
                    continue;
                end

                Edeout = const.m_HS * ((h_HS_out - const.h_HS_0) - const.T_0 * (s_HS_out - const.s_HS_0));
                exerg_balance = const.Ein - Ede - Edt - Edp - Edc - Edmix - Edeout - output * 1000 - power_w * 1000;
                if abs(exerg_balance) >= 0.1
                    continue;
                end

                ratio_Ede = Ede / Ed_total * 100;
                ratio_Edt = Edt / Ed_total * 100;
                ratio_Edp = Edp / Ed_total * 100;
                ratio_Edmix = Edmix / Ed_total * 100;
                ratio_Edc = Edc / Ed_total * 100;
                ratio_Edt_h = Edt_h / Ed_total * 100;
                ratio_Edt_l = Edt_l / Ed_total * 100;
                ratio_Edp_1 = Edp_1 / Ed_total * 100;
                ratio_Edp_2 = Edp_2 / Ed_total * 100;

                q_pre = max(m_f * (h3 - h2), 0);
                q_hp = max(m_O_HP * (h8 - h5), 0);
                q_lp = max(m_O_LP * (h4 - h3), 0);
                q_ehx = q_pre + q_hp + q_lp;
                if q_ehx > 0
                    ratio_Ede_pre = ratio_Ede * q_pre / q_ehx;
                    ratio_Ede_hp = ratio_Ede * q_hp / q_ehx;
                    ratio_Ede_lp = ratio_Ede * q_lp / q_ehx;
                else
                    ratio_Ede_pre = 0;
                    ratio_Ede_hp = 0;
                    ratio_Ede_lp = 0;
                end

                deltaT_hp_hot_in = const.T_HS_in - T8;
                deltaT_hp_hot_out = T_HS_3 - T5;
                deltaT_lp_hot_in = T_HS_3 - T4;
                deltaT_lp_hot_out = T_HS_out - T2;
                lmtd_hp = calc_lmtd(deltaT_hp_hot_in, deltaT_hp_hot_out);
                lmtd_lp = calc_lmtd(deltaT_lp_hot_in, deltaT_lp_hot_out);
                if ~(isfinite(lmtd_hp) && isfinite(lmtd_lp) && lmtd_hp > 0 && lmtd_lp > 0)
                    continue;
                end

                eta_ex_percent = output * const.eta_exergy_factor;
                eta_thermal_percent = output * 1000 / max(q_ehx, eps) * 100;
                % System efficiency uses heat-source enthalpy above the ambient state.
                source_heat_available = const.m_HS * (const.h_HS_in - const.h_HS_0);
                eta_sys_percent = output * 1000 / max(source_heat_available, eps) * 100;

                lc = lc + 1;
                if lc > size(local_rows, 1)
                    grown_rows = zeros(size(local_rows, 1) * 2, 29);
                    grown_rows(1:lc - 1, :) = local_rows;
                    local_rows = grown_rows;
                end

                local_rows(lc, :) = [ ...
                    const.year_now, const.T_HS_in, output, eta_ex_percent, Ed_total, ...
                    ratio_Ede, ratio_Edt, ratio_Edp, ratio_Edmix, ratio_Edc, ...
                    ratio_Edt_h, ratio_Edt_l, ratio_Edp_1, ratio_Edp_2, ...
                    ratio_Ede_pre, ratio_Ede_hp, ratio_Ede_lp, ...
                    lmtd_hp, lmtd_lp, P_e_lp_local, P_e_hp_local, ...
                    T4, T8, T_e_lp_local, T7, ...
                    eta_thermal_percent, eta_sys_percent, m_O_HP, m_O_LP ];
            end
        end
    end

    if lc == 0
        candidate_cells{i_lp} = zeros(0, 29);
    else
        candidate_cells{i_lp} = local_rows(1:lc, :);
    end
end

candidate_rows = vertcat(candidate_cells{:});
candidate_rows = candidate_rows(all(isfinite(candidate_rows), 2), :);
end

function fine_candidates = run_refined_windows(stage, const, refine_boxes)
fine_cells = cell(1, numel(refine_boxes));
for i_box = 1:numel(refine_boxes)
    refine_box = refine_boxes(i_box);
    if isfield(stage, 'restrict_superheat') && ~stage.restrict_superheat
        fprintf('  Window %d/%d: P_lp=[%.1f, %.1f] kPa, P_hp=[%.1f, %.1f] kPa, full original superheat range.\n', ...
            i_box, numel(refine_boxes), ...
            refine_box.lp_low, refine_box.lp_high, refine_box.hp_low, refine_box.hp_high);
    else
        fprintf(['  Window %d/%d: P_lp=[%.1f, %.1f] kPa, ' ...
                 'P_hp=[%.1f, %.1f] kPa, dT_hp=[%.2f, %.2f] K, dT_lp=[%.2f, %.2f] K.\n'], ...
            i_box, numel(refine_boxes), ...
            refine_box.lp_low, refine_box.lp_high, refine_box.hp_low, refine_box.hp_high, ...
            refine_box.sh_hp_low, refine_box.sh_hp_high, refine_box.sh_lp_low, refine_box.sh_lp_high);
    end
    fine_cells{i_box} = run_search_stage(stage, const, refine_box);
end

fine_candidates = vertcat(fine_cells{:});
if ~isempty(fine_candidates)
    fine_candidates = unique(fine_candidates, 'rows');
end
end

function sorted_rows = sort_candidate_rows(candidate_rows, const)
if isempty(candidate_rows)
    sorted_rows = candidate_rows;
    return;
end

if isfield(const, 'match_literature_targets') && const.match_literature_targets
    target = const.literature;
    values = [ ...
        candidate_rows(:, 3), ...
        candidate_rows(:, 26), ...
        candidate_rows(:, 27), ...
        candidate_rows(:, 28), ...
        candidate_rows(:, 29)];
    targets = [ ...
        target.W_net_kW, ...
        target.eta_thermal_percent, ...
        target.eta_sys_percent, ...
        target.m_HP_kg_s, ...
        target.m_LP_kg_s];
    scales = max(abs(targets), 1);
    scores = sum(((values - targets) ./ scales) .^ 2, 2);
    [~, order] = sort(scores, 'ascend');
else
    [~, order] = sort(candidate_rows(:, 3), 'descend');
end

sorted_rows = candidate_rows(order, :);
end

function refine_boxes = deduplicate_refine_boxes(refine_boxes, stage)
if isempty(refine_boxes)
    return;
end

if isfield(stage, 'restrict_superheat') && ~stage.restrict_superheat
    key_matrix = [ ...
        round([refine_boxes.lp_low]', 9), round([refine_boxes.lp_high]', 9), ...
        round([refine_boxes.hp_low]', 9), round([refine_boxes.hp_high]', 9)];
else
    key_matrix = [ ...
        round([refine_boxes.lp_low]', 9), round([refine_boxes.lp_high]', 9), ...
        round([refine_boxes.hp_low]', 9), round([refine_boxes.hp_high]', 9), ...
        round([refine_boxes.sh_hp_low]', 9), round([refine_boxes.sh_hp_high]', 9), ...
        round([refine_boxes.sh_lp_low]', 9), round([refine_boxes.sh_lp_high]', 9)];
end

[~, ia] = unique(key_matrix, 'rows', 'stable');
refine_boxes = refine_boxes(ia);
end

function refine_boxes = build_refine_boxes(candidate_rows, search, const)
[~, order] = sort(candidate_rows(:, 3), 'descend');
candidate_rows = candidate_rows(order, :);

coarse_lp_step = max((const.P_e_lp_max - const.P_e_lp_min) / max(search.coarse.lp_n - 1, 1), 1e-6);
coarse_hp_step = max((const.P_e_hp_max - const.P_e_hp_min) / max(search.coarse.hp_n - 1, 1), 1e-6);

anchor_rows = zeros(0, size(candidate_rows, 2));
for i_row = 1:size(candidate_rows, 1)
    row = candidate_rows(i_row, :);
    sh_hp = row(23) - row(25);
    sh_lp = row(22) - row(24);
    is_new_anchor = true;
    for i_anchor = 1:size(anchor_rows, 1)
        anchor = anchor_rows(i_anchor, :);
        anchor_sh_hp = anchor(23) - anchor(25);
        anchor_sh_lp = anchor(22) - anchor(24);
        same_lp_band = abs(row(20) - anchor(20)) <= search.refine.anchor_lp_gap_steps * coarse_lp_step;
        same_hp_band = abs(row(21) - anchor(21)) <= search.refine.anchor_hp_gap_steps * coarse_hp_step;
        same_sh_band = abs(sh_hp - anchor_sh_hp) <= search.refine.anchor_sh_gap_K && ...
            abs(sh_lp - anchor_sh_lp) <= search.refine.anchor_sh_gap_K;
        if same_lp_band && same_hp_band && same_sh_band
            is_new_anchor = false;
            break;
        end
    end

    if is_new_anchor
        anchor_rows(end + 1, :) = row; %#ok<AGROW>
    end

    if size(anchor_rows, 1) >= search.refine.max_boxes
        break;
    end
end

if isempty(anchor_rows)
    anchor_rows = candidate_rows(1, :);
end

refine_boxes = repmat(struct( ...
    'lp_low', 0, 'lp_high', 0, ...
    'hp_low', 0, 'hp_high', 0, ...
    'sh_hp_low', 0, 'sh_hp_high', 0, ...
    'sh_lp_low', 0, 'sh_lp_high', 0), 1, size(anchor_rows, 1));

for i_anchor = 1:size(anchor_rows, 1)
    row = anchor_rows(i_anchor, :);
    sh_hp = row(23) - row(25);
    sh_lp = row(22) - row(24);

    lp_low = row(20) - search.refine.lp_margin_steps * coarse_lp_step;
    lp_high = row(20) + search.refine.lp_margin_steps * coarse_lp_step;
    hp_low = row(21) - search.refine.hp_margin_steps * coarse_hp_step;
    hp_high = row(21) + search.refine.hp_margin_steps * coarse_hp_step;
    sh_hp_low = sh_hp - search.refine.sh_margin_K;
    sh_hp_high = sh_hp + search.refine.sh_margin_K;
    sh_lp_low = sh_lp - search.refine.sh_margin_K;
    sh_lp_high = sh_lp + search.refine.sh_margin_K;

    [lp_low, lp_high] = ensure_min_span(lp_low, lp_high, ...
        search.refine.min_lp_span_steps * coarse_lp_step, const.P_e_lp_min, const.P_e_lp_max);
    [hp_low, hp_high] = ensure_min_span(hp_low, hp_high, ...
        search.refine.min_hp_span_steps * coarse_hp_step, const.P_e_hp_min, const.P_e_hp_max);
    [sh_hp_low, sh_hp_high] = ensure_min_span(sh_hp_low, sh_hp_high, ...
        search.refine.min_sh_span_K, 2, const.T8max_global - 273.15);
    [sh_lp_low, sh_lp_high] = ensure_min_span(sh_lp_low, sh_lp_high, ...
        search.refine.min_sh_span_K, 0.01, const.T8max_global - 273.15);

    refine_boxes(i_anchor).lp_low = lp_low;
    refine_boxes(i_anchor).lp_high = lp_high;
    refine_boxes(i_anchor).hp_low = hp_low;
    refine_boxes(i_anchor).hp_high = hp_high;
    refine_boxes(i_anchor).sh_hp_low = sh_hp_low;
    refine_boxes(i_anchor).sh_hp_high = sh_hp_high;
    refine_boxes(i_anchor).sh_lp_low = sh_lp_low;
    refine_boxes(i_anchor).sh_lp_high = sh_lp_high;
end
end

function refine_boxes = expand_refine_boxes(refine_boxes, search, const)
coarse_lp_step = max((const.P_e_lp_max - const.P_e_lp_min) / max(search.coarse.lp_n - 1, 1), 1e-6);
coarse_hp_step = max((const.P_e_hp_max - const.P_e_hp_min) / max(search.coarse.hp_n - 1, 1), 1e-6);

for i_box = 1:numel(refine_boxes)
    lp_span = max((refine_boxes(i_box).lp_high - refine_boxes(i_box).lp_low) * search.refine.expand_factor, coarse_lp_step);
    hp_span = max((refine_boxes(i_box).hp_high - refine_boxes(i_box).hp_low) * search.refine.expand_factor, coarse_hp_step);
    sh_hp_span = max((refine_boxes(i_box).sh_hp_high - refine_boxes(i_box).sh_hp_low) * search.refine.expand_factor, search.refine.min_sh_span_K);
    sh_lp_span = max((refine_boxes(i_box).sh_lp_high - refine_boxes(i_box).sh_lp_low) * search.refine.expand_factor, search.refine.min_sh_span_K);

    [refine_boxes(i_box).lp_low, refine_boxes(i_box).lp_high] = ensure_min_span( ...
        mean([refine_boxes(i_box).lp_low, refine_boxes(i_box).lp_high]) - lp_span / 2, ...
        mean([refine_boxes(i_box).lp_low, refine_boxes(i_box).lp_high]) + lp_span / 2, ...
        lp_span, const.P_e_lp_min, const.P_e_lp_max);
    [refine_boxes(i_box).hp_low, refine_boxes(i_box).hp_high] = ensure_min_span( ...
        mean([refine_boxes(i_box).hp_low, refine_boxes(i_box).hp_high]) - hp_span / 2, ...
        mean([refine_boxes(i_box).hp_low, refine_boxes(i_box).hp_high]) + hp_span / 2, ...
        hp_span, const.P_e_hp_min, const.P_e_hp_max);
    [refine_boxes(i_box).sh_hp_low, refine_boxes(i_box).sh_hp_high] = ensure_min_span( ...
        mean([refine_boxes(i_box).sh_hp_low, refine_boxes(i_box).sh_hp_high]) - sh_hp_span / 2, ...
        mean([refine_boxes(i_box).sh_hp_low, refine_boxes(i_box).sh_hp_high]) + sh_hp_span / 2, ...
        sh_hp_span, 2, const.T8max_global - 273.15);
    [refine_boxes(i_box).sh_lp_low, refine_boxes(i_box).sh_lp_high] = ensure_min_span( ...
        mean([refine_boxes(i_box).sh_lp_low, refine_boxes(i_box).sh_lp_high]) - sh_lp_span / 2, ...
        mean([refine_boxes(i_box).sh_lp_low, refine_boxes(i_box).sh_lp_high]) + sh_lp_span / 2, ...
        sh_lp_span, 0.01, const.T8max_global - 273.15);
end
end

function [low_out, high_out] = ensure_min_span(low_in, high_in, min_span, hard_low, hard_high)
low_out = max(low_in, hard_low);
high_out = min(high_in, hard_high);
if high_out < low_out
    center = min(max((low_in + high_in) / 2, hard_low), hard_high);
    half_span = min_span / 2;
    low_out = center - half_span;
    high_out = center + half_span;
end

if (high_out - low_out) < min_span
    center = (low_out + high_out) / 2;
    half_span = min_span / 2;
    low_out = center - half_span;
    high_out = center + half_span;
    if low_out < hard_low
        high_out = min(hard_high, high_out + (hard_low - low_out));
        low_out = hard_low;
    end
    if high_out > hard_high
        low_out = max(hard_low, low_out - (high_out - hard_high));
        high_out = hard_high;
    end
end

low_out = max(low_out, hard_low);
high_out = min(high_out, hard_high);
end

function axis_values = build_axis(low_val, high_val, target_step)
if ~(isfinite(low_val) && isfinite(high_val) && isfinite(target_step)) || high_val < low_val
    axis_values = [];
    return;
end

if abs(high_val - low_val) < 1e-9
    axis_values = low_val;
    return;
end

n_points = max(2, ceil((high_val - low_val) / max(target_step, 1e-6)) + 1);
axis_values = linspace(low_val, high_val, n_points);
end

function lmtd = calc_lmtd(delta_t_1, delta_t_2)
if delta_t_1 <= 0 || delta_t_2 <= 0
    lmtd = NaN;
elseif abs(delta_t_1 - delta_t_2) < 1e-9
    lmtd = delta_t_1;
else
    lmtd = (delta_t_1 - delta_t_2) / log(delta_t_1 / delta_t_2);
end
end
