function T_hs = heat_source_temp(t, T0, b, di, beta_t)
% HEAT_SOURCE_DECLINE_HYPERRELU_ALLINONE
% All-in-one HyperReLU thermal decline model
%
% Usage:
%   T_hs = heat_source_decline_hyperrelu_allinone(t)
%   T_hs = heat_source_decline_hyperrelu_allinone(t, T0)
%   T_hs = heat_source_decline_hyperrelu_allinone(t, T0, b, di, beta_t)
%
% Default (EGS average):
%   T0     = 150 °C
%   b      = 3.44
%   di     = -1.76
%   beta_t = 17.01 year

    %% 默认参数
    if nargin < 2 || isempty(T0)
        T0 = 150;
    end
    if nargin < 3 || isempty(b)
        b = 3.44;
    end
    if nargin < 4 || isempty(di)
        di = -1.76;
    end
    if nargin < 5 || isempty(beta_t)
        beta_t = 17.01;
    end

    %% 输入检查（简单版）
    if any(t < 0)
        error('Time t must be non-negative');
    end

    %% 调用归一化函数
    H = hyperrelu_ratio(t, b, di, beta_t);

    %% 计算实际温度
    T_hs = T0 .* H;

end


%% ===== 子函数：归一化衰减函数 =====
function H = hyperrelu_ratio(t, b, di, beta_t)

    % ReLU：max(0, t - beta_t)
    relu_term = max(0, t - beta_t);

    % HyperReLU模型
    H = (1 + b .* 10.^di .* relu_term) .^ (-1 ./ b);

end
