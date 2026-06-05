function varargout = refpropm_cached(out, in1, val1, in2, val2, fluid)
%REFPROPM_CACHED  Cached wrapper for refpropm (keeps your logic/iterations unchanged).
%
% Usage is identical to refpropm:
%   x = refpropm_cached('H','T',T,'P',P,fluid);
%   [h,s] = refpropm_cached('HS','T',T,'P',P,fluid);
%   [T,h,s] = refpropm_cached('THS','P',P,'Q',Q,fluid);
%
% Notes:
% - Cache is per MATLAB worker (each parfor worker has its own cache), still very effective.
% - Quantization boosts cache hit rate; adjust tolerances below if you need stricter equality.

persistent M tol
if isempty(M)
    M = containers.Map('KeyType','char','ValueType','any');
    tol = struct();
    tol.P = 0.1;     % kPa
    tol.T = 0.01;    % K
    tol.H = 0.1;     % J/kg
    tol.S = 1e-3;    % J/kg-K
    tol.Q = 1e-8;    % quality
end

v1q = quantize_(in1, val1, tol);
v2q = quantize_(in2, val2, tol);

key = sprintf('%s|%s=%.12g|%s=%.12g|%s|nout=%d', out, in1, v1q, in2, v2q, fluid, nargout);

if isKey(M, key)
    cached = M(key);
    for k = 1:nargout
        varargout{k} = cached{k};
    end
    return;
end

tmp = cell(1, nargout);
[tmp{:}] = refpropm(out, in1, val1, in2, val2, fluid);

M(key) = tmp;
varargout = tmp;

end

function vq = quantize_(name, v, tol)
% Quantize scalar numeric inputs to improve cache hit rate.
if ~isnumeric(v) || isempty(v) || ~isscalar(v) || ~isfinite(v)
    vq = v;
    return;
end

switch upper(strtrim(name))
    case 'P'
        step = tol.P;
    case 'T'
        step = tol.T;
    case 'H'
        step = tol.H;
    case 'S'
        step = tol.S;
    case 'Q'
        step = tol.Q;
    otherwise
        step = 1e-6;
end

vq = round(v/step) * step;
end
