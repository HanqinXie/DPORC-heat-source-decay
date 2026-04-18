clear; clc;
% 定义参数
WF = 'R1234yf'; % 工作流体（R600a）
HS_fluid = 'water'; % 热源流体
cool_fluid = 'water'; % 冷却流体
overall_timer = tic;
setup_timer = tic;
fprintf('Script started at %s\n', char(datetime('now', 'Format', 'yyyy-MM-dd HH:mm:ss')));
fprintf('Initializing inputs and thermophysical properties...\n');
% 热源温度：以 150 C 为初始温度，按年调用衰减模型（在循环中更新 year_now）
year_now = 0;
T_HS_in_C = heat_source_temp(year_now, 150);
T_HS_in = T_HS_in_C + 273.15; % 热流体进口温度 [K]
m_HS = 100; % 热流体流量 [kg/s]
P_HS = 0.5 * 1e3; % 热流体压力 [kPa]
T_0 = 20 + 273.15; % 环境温度 [K]
delta_T_HAP_pp = 5; % 吸热夹点温差 [K]
delta_T_cond_pp = 5; % 冷凝夹点温差 [K]
T_cool_in = 20 + 273.15; % 冷凝水进口温度 [K]
delta_T_cool = 5; % 冷凝水温升 [K]
T_cool_out = T_cool_in + delta_T_cool; % 冷凝水出口温度 [K]
delta_T_subcool = 2; % 过冷度 [K]
P_cool = 0.101 * 1e3; % 冷凝水压力 [kPa]
H = 10; % 循环泵水头 [m]
g = 9.81; % 重力加速度 [m/s²]
eta_p = 0.75; % 给料泵效率
eta_T = 0.80; % 涡轮效率
eta_pw = 0.85; % 冷却水泵效率
% 计算冷凝温度和压力
T_cond = T_cool_out + delta_T_cond_pp; % 冷凝温度 [K]
P_cond = refpropm_cached('P', 'T', T_cond, 'Q', 0, WF); % 冷凝压力 [kPa]
T1 = T_cond - delta_T_subcool;
[h1, s1] = refpropm_cached('HS', 'T', T1, 'P', P_cond, WF);
[T12, h12, ~] = refpropm_cached('THS', 'P', P_cond, 'Q', 1, WF);
T_cw_12_req = T12 - delta_T_cond_pp;
h_cw_12_req = refpropm_cached('H', 'T', T_cw_12_req, 'P', P_cool, cool_fluid);

% 计算热流体关键焓熵
[h_HS_in, s_HS_in] = refpropm_cached('HS', 'T', T_HS_in, 'P', P_HS, HS_fluid); % 热流体进口焓熵 [J/kg]
[h_HS_0, s_HS_0] = refpropm_cached('HS', 'T', T_0, 'P', P_HS, HS_fluid); % 环境热流体出口焓熵
h_cool_in = refpropm_cached('H', 'T', T_cool_in, 'P', P_cool, cool_fluid); % 冷却水入口焓
h_cool_out = refpropm_cached('H', 'T', T_cool_out, 'P', P_cool, cool_fluid); % 冷却水出口焓
P_c = refpropm_cached('P', 'C', 0, ' ', 0, WF); % 临界压力 [kPa]
T_c = refpropm_cached('T', 'C', 0, ' ', 0, WF);
% 蒸发压力设定
P_e_lp1_max = 0.9*P_c - 100; % 初步假定低压蒸发压力上限 [kPa]
T_e_lp1_max = refpropm_cached('T', 'P', P_e_lp1_max, 'Q', 0, WF); % 初步假定低压蒸发温度上限 [K]
P_e_hp1_max = 0.9 * P_c; % 初步假定高压蒸发压力上限 [kPa]
T_e_hp1_max = refpropm_cached('T', 'P', P_e_hp1_max, 'Q', 0, WF); % 初步假定高压蒸发温度上限 [K]
if (T_HS_in - T_e_lp1_max) >= delta_T_HAP_pp
    P_e_lp_max = P_e_lp1_max;
else
    T_e_lp_max = T_HS_in - delta_T_HAP_pp; % 防止工质温度大于热源温度
    P_e_lp_max = refpropm_cached('P', 'T', T_e_lp_max, 'Q', 0, WF);
end
if (T_HS_in - T_e_hp1_max) >= delta_T_HAP_pp
    P_e_hp_max = P_e_hp1_max;
else
    T_e_hp_max = T_HS_in - delta_T_HAP_pp;
    P_e_hp_max = refpropm_cached('P', 'T', T_e_hp_max, 'Q', 0, WF);
end
P_e_lp_min = P_cond + 100; % 低压蒸发压力下限 [kPa]
P_e_hp_min = P_e_lp_min + 100; % 确保高压 > 低压
% 验证值
Ref.Pelp = 1590; % kPa
Ref.Pehp = 2280; % kPa
Ref.Tsat_lp = 331.55; % K
Ref.Tsat_hp = 348.35; % K
Ref.Wnet = 969.7; % kW
Ref.eta_th = 5.54; % %
Ref.eta_rec = 52.3; % %
Ref.eta_sys = 2.895; % %
Ref.mhp = 68.0; % kg/s
Ref.mlp = 46.1; % kg/s
% 计算输入㶲
Ein = m_HS * ((h_HS_in - h_HS_0) - T_0 * (s_HS_in - s_HS_0)); % 输入的㶲 W
Qav = m_HS * (h_HS_in - h_HS_0);
mw_denom = h_cw_12_req - h_cool_in;
eta_exergy_factor = 1000 * 100 / max(Ein, eps);
% 追寻最佳性能参数
num_steps_pressure = 401; % 每个压力循环的步数
num_steps_superheat = 21; % 每个过热循环的步数
P_lp_list = linspace(P_e_lp_min, P_e_lp_max, num_steps_pressure);
T8max_global = T_HS_in - delta_T_HAP_pp;
% 准备并行收集
best_sols = cell(1, num_steps_pressure);
% 外层循环：低压蒸发压力 (并行)
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
fprintf('Entering parfor loop with %d low-pressure steps and %d high-pressure steps.\n', num_steps_pressure, num_steps_pressure);
parfor_timer = tic;
parfor i_lp = 1:num_steps_pressure
    local_capacity = 4096;
    local_rows = zeros(local_capacity, 21);
    lc = 0;
    P_e_lp_local = P_lp_list(i_lp);
    % 计算低压相关状态
    T_e_lp_local = refpropm_cached('T', 'P', P_e_lp_local, 'Q', 0, WF);
    % 状态点1
    % 状态点2 (泵1出口)
    h2_ideal = refpropm_cached('H', 'P', P_e_lp_local, 'S', s1, WF);
    deltah_21 = (h2_ideal - h1) / eta_p;
    h2 = h1 + deltah_21;
    [s2, T2] = refpropm_cached('ST', 'P', P_e_lp_local, 'H', h2, WF);
    % 状态点3 (预热器1出口)
    T3 = T_e_lp_local;
    [h3, s3] = refpropm_cached('HS', 'T', T3, 'Q', 0, WF);
    % 状态点4'（低压蒸发器内，饱和蒸汽）
    P4p = P_e_lp_local;
    % 内层循环：高压蒸发压力
    T_HS_4_req = T3 + delta_T_HAP_pp;
    h_HS_4_req = refpropm_cached('H', 'T', T_HS_4_req, 'P', P_HS, HS_fluid);
    hp_min_local = max(P_e_hp_min, P_e_lp_local + 100);
    if hp_min_local > P_e_hp_max
        best_sols{i_lp} = zeros(0, 21);
        continue;
    end
    P_hp_list = linspace(hp_min_local, P_e_hp_max, num_steps_pressure);
    for i_hp = 1:numel(P_hp_list)
        P_e_hp_local = P_hp_list(i_hp);
        % 计算高压相关状态
        T_e_hp_local = refpropm_cached('T', 'P', P_e_hp_local, 'Q', 0, WF);
        % 状态点5 (泵2出口)
        h5_ideal = refpropm_cached('H', 'P', P_e_hp_local, 'S', s3, WF);
        deltah_53 = (h5_ideal - h3) / eta_p;
        h5 = h3 + deltah_53;
        [s5, T5] = refpropm_cached('ST', 'P', P_e_hp_local, 'H', h5, WF);
        % 状态点6 (预热器2出口)
        T6 = T_e_hp_local;
        [h6, s6] = refpropm_cached('HS', 'T', T6, 'Q', 0, WF);
        % 状态点7 (高压蒸发器出口, 饱和蒸汽)
        [T7, h7, s7] = refpropm_cached('THS', 'P', P_e_hp_local, 'Q', 1, WF);
        T8min = T7 + 2; % 最小过热温度2 K
        if T8min > T8max_global
            continue;
        end
        T8_list = linspace(T8min, T8max_global, num_steps_superheat);
        T_HS_6_req = T6 + delta_T_HAP_pp;
        h_HS_6_req = refpropm_cached('H', 'T', T_HS_6_req, 'P', P_HS, HS_fluid);
        for j_hp = 1:numel(T8_list)
            % 状态点8 (过热器出口)
            T8 = T8_list(j_hp);
            [h8, s8] = refpropm_cached('HS', 'T', T8, 'P', P_e_hp_local, WF);
            % 计算高压流量 m_O_HP
            m_O_HP = m_HS * (h_HS_in - h_HS_6_req) / (h8 - h6);
            if m_O_HP <= 0
                continue;
            end
            % 检查点5
            h_HS_3 = h_HS_6_req - m_O_HP * (h6 - h5) / m_HS;
            T_HS_3 = refpropm_cached('T', 'H', h_HS_3, 'P', P_HS, HS_fluid);
            if (T_HS_3 - T5) < delta_T_HAP_pp
                % 移位到点5
                T_HS_3 = T5 + delta_T_HAP_pp;
                h_HS_3 = refpropm_cached('H', 'T', T_HS_3, 'P', P_HS, HS_fluid);
                m_O_HP = m_HS * (h_HS_in - h_HS_3) / (h8 - h5);
                if m_O_HP <= 0
                    continue;
                end
            end
            T4max = T_HS_3 - delta_T_HAP_pp;
            T4min = T_e_lp_local + 0.01; % 最小过热温度0.01 K
            if T4min > T4max
                continue;
            end
            T4_list = linspace(T4min, T4max, num_steps_superheat);
            for j_lp = 1:numel(T4_list)
                % 状态点4 (低压蒸发器出口，过热蒸汽)
                P4 = P_e_lp_local;
                T4 = T4_list(j_lp);
                [h4, s4] = refpropm_cached('HS', 'T', T4, 'P', P_e_lp_local, WF);
                % 计算低压流量 m_O_LP
                m_O_LP = m_HS * (h_HS_3 - h_HS_4_req) / (h4 - h3);
                if m_O_LP <= 0
                    continue;
                end
                % 计算总流量
                m_f_temp = m_O_LP + m_O_HP;
                % 检查点2
                h_HS_out = h_HS_4_req - m_f_temp * (h3 - h2) / m_HS;
                [T_HS_out,s_HS_out] = refpropm_cached('Ts', 'H', h_HS_out, 'P', P_HS, HS_fluid);
                if (T_HS_out - T2) < delta_T_HAP_pp
                    % 移位到点2
                    T_HS_out = T2 + delta_T_HAP_pp;
                    h_HS_out = refpropm_cached('H', 'T', T_HS_out, 'P', P_HS, HS_fluid);
                    [~, s_HS_out] = refpropm_cached('Ts', 'H', h_HS_out, 'P', P_HS, HS_fluid);
                    m_O_LP = (m_HS * (h_HS_3 - h_HS_out) - m_O_HP * (h3 - h2)) / (h4 - h2);
                    if m_O_LP <= 0
                        continue;
                    end
                end
                % 更新总流量
                m_f = m_O_LP + m_O_HP;
                % 状态点9 (高压涡轮出口)
                h9s = refpropm_cached('H', 'P', P_e_lp_local, 'S', s8, WF);
                deltah_89 = (h8 - h9s) * eta_T;
                h9 = h8 - deltah_89;
                s9 = refpropm_cached('S', 'P', P_e_lp_local, 'H', h9, WF);
                % 状态点10 (混合点)
                h10 = (m_O_LP * h4 + m_O_HP * h9) / m_f;
                [T10, s10] = refpropm_cached('TS', 'P', P_e_lp_local, 'H', h10, WF);
                % 状态点11 (低压涡轮出口)
                h11s = refpropm_cached('H', 'P', P_cond, 'S', s10, WF);
                deltah_1011 = (h10 - h11s) * eta_T;
                h11 = h10 - deltah_1011;
                s11 = refpropm_cached('S', 'P', P_cond, 'H', h11, WF);
                T11 = refpropm_cached('T', 'P', P_cond, 'H', h11, WF);
                if h11 <= h1
                    continue;
                end
                mw = m_f * (h12 - h1) / mw_denom;
                if false
%{
                % 冷凝器状态点
                [T12, h12, s12] = refpropm_cached('THS', 'P', P_cond, 'Q', 1, WF); % 饱和汽
                [T13, h13, s13] = refpropm_cached('THS', 'P', P_cond, 'Q', 0, WF); % 饱和液
                % 计算冷却水流量
                if h11 <= h1
                    continue;
                end
                % 检查过冷夹点
                if (T1 - T_cool_in) < delta_T_cond_pp
                    continue;
                end
                % 计算冷却水流量
                T_cw_12_req = T12 - delta_T_cond_pp;
                h_cw_12_req = refpropm_cached('H', 'T', T_cw_12_req, 'P', P_cool, cool_fluid);
                mw = m_f * (h12 - h1) / (h_cw_12_req - h_cool_in);
%}
                end
                if mw <= 0 || isinf(mw)
                    continue;
                end
                % 检查入口点11
                if (T11 - T_cool_out) < delta_T_cond_pp
                    continue;
                end
                % 功率计算
                power_t_high = m_O_HP * deltah_89 / 1000;
                power_t_low = m_f * deltah_1011 / 1000;
                power_p1 = m_f * deltah_21 / 1000;
                power_p2 = m_O_HP * deltah_53 / 1000;
                power_w = m_f * (h11-h1) / (100 * 1000);
                output = power_t_high + power_t_low - power_p1 - power_p2 - power_w; % 系统净输出功 KW
                % 相关热性能评估参数
                Qin = m_HS * (h_HS_in - h_HS_out); % 热源向热力循环传递的热量
                % Qav is invariant for this fixed-source verification case.
                % 热效率
                eta_thermal = output * 1000 / Qin;
                % 热回收率
                fai_recovery = Qin / Qav;
                % 系统效率
                eta_sys = output * 1000 / Qav;
                % 蒸发器㶲损 (过热器 + 高压蒸发器 + 预热器2 + 低压蒸发器 + 预热器1) W
                Ede = m_HS * ((h_HS_in - h_HS_out) - T_0 * (s_HS_in - s_HS_out)) - ...
                      (m_O_HP * (h8 - h5) + m_O_LP * (h4 - h3) + m_f * (h3 - h2)) + ...
                      T_0 * (m_O_HP * (s8 - s5) + m_O_LP * (s4 - s3) + m_f * (s3 - s2));
                % 高压和低压涡轮机㶲损
                Edt_h = m_O_HP * T_0 * (s9 - s8); % 高压涡轮㶲损 W
                Edt_l = m_f * T_0 * (s11 - s10); % 低压涡轮㶲损 W
                Edt = Edt_h + Edt_l;
                % 泵㶲损
                Edp_1 = m_f * T_0 * (s2 - s1); % 泵1㶲损 W
                Edp_2 = m_O_HP * T_0 * (s5 - s3); % 泵2㶲损 W
                Edp = Edp_1 + Edp_2;
                % 混合㶲损
                Edmix = m_O_HP * (h9 - T_0 * s9) + m_O_LP * (h4 - T_0 * s4) - m_f * (h10 - T_0 * s10);
                % 冷凝器㶲损
                Edc = m_f * ((h11 - h1) - T_0 * (s11 - s1));
                Ed_total = Ede + Edt + Edp + Edmix + Edc;
                if ~(isfinite(Ed_total) && Ed_total > 0)
                    continue;
                end
                % 出口㶲损失
                Edeout = m_HS * ((h_HS_out - h_HS_0) - T_0 * (s_HS_out - s_HS_0));
                % 㶲平衡
                exerg_balance = Ein - Ede - Edt - Edp - Edc - Edmix - Edeout - output * 1000 - power_w * 1000;
                % 记录满足条件的结果
                if abs(exerg_balance) < 0.1 && output > 0
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

                    deltaT_hp_hot_in = T_HS_in - T8;
                    deltaT_hp_hot_out = T_HS_3 - T5;
                    deltaT_lp_hot_in = T_HS_3 - T4;
                    deltaT_lp_hot_out = T_HS_out - T2;
                    lmtd_hp = calc_lmtd(deltaT_hp_hot_in, deltaT_hp_hot_out);
                    lmtd_lp = calc_lmtd(deltaT_lp_hot_in, deltaT_lp_hot_out);
                    if ~(isfinite(lmtd_hp) && isfinite(lmtd_lp) && lmtd_hp > 0 && lmtd_lp > 0)
                        continue;
                    end

                    eta_ex_percent = output * eta_exergy_factor;

                    lc = lc + 1;
                    if lc > size(local_rows, 1)
                        grown_rows = zeros(size(local_rows, 1) * 2, 21);
                        grown_rows(1:lc-1, :) = local_rows;
                        local_rows = grown_rows;
                    end
                    local_rows(lc, :) = [ ...
                        year_now, T_HS_in, output, eta_ex_percent, Ed_total, ...
                        ratio_Ede, ratio_Edt, ratio_Edp, ratio_Edmix, ratio_Edc, ...
                        ratio_Edt_h, ratio_Edt_l, ratio_Edp_1, ratio_Edp_2, ...
                        ratio_Ede_pre, ratio_Ede_hp, ratio_Ede_lp, ...
                        lmtd_hp, lmtd_lp, P_e_lp_local, P_e_hp_local ];
                end
            end
        end
    end
    if lc == 0
        best_sols{i_lp} = zeros(0, 21);
    else
        best_sols{i_lp} = local_rows(1:lc, :);
    end
end
fprintf('parfor loop finished in %.2f s.\n', toc(parfor_timer));
% 合并结果
best_solutions = vertcat(best_sols{:});
best_solutions = best_solutions(all(isfinite(best_solutions), 2), :);
% 输出结果到CSV
if ~isempty(best_solutions)
    T = array2table(best_solutions, 'VariableNames', { ...
    'year', 'T_HS_in_K', 'net_output_kW', 'eta_ex_percent', 'Ed_total_W', ...
    'ratio_Ede_percent', 'ratio_Edt_percent', 'ratio_Edp_percent', 'ratio_Edmix_percent', 'ratio_Edc_percent', ...
    'ratio_Edt_h_percent', 'ratio_Edt_l_percent', 'ratio_Edp_1_percent', 'ratio_Edp_2_percent', ...
    'ratio_Ede_pre_percent', ...
    'ratio_Ede_hp_percent', 'ratio_Ede_lp_percent', ...
    'lmtd_hp_K', 'lmtd_lp_K', 'P_e_lp_kPa', 'P_e_hp_kPa'});
    % 添加时间戳到文件名
    timestamp = char(datetime('now', 'Format', 'yyyy-MM-dd_HH-mm-ss'));
    filename = sprintf('R1234yf_100C_verification_%s.csv', timestamp);
    % 保存到CSV
    writetable(T, filename);
    disp(['所有满足条件的最优解已保存到 ', filename]);
else
    disp('未找到满足条件的最优解。');
end
fprintf('Script finished in %.2f s.\n', toc(overall_timer));

function lmtd = calc_lmtd(delta_t_1, delta_t_2)
if delta_t_1 <= 0 || delta_t_2 <= 0
    lmtd = NaN;
elseif abs(delta_t_1 - delta_t_2) < 1e-9
    lmtd = delta_t_1;
else
    lmtd = (delta_t_1 - delta_t_2) / log(delta_t_1 / delta_t_2);
end
end
