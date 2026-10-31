function estimate = fit_first_order_arx(u,temperature,dt,m,ambient)
% FIT_FIRST_ORDER_ARX - Least-squares ARX for a first-order, known-delay plant.
% Equation for k = m+2,...,N in MATLAB one-based indexing:
% x(k) = a*x(k-1) + b*u(k-1-m), x = temperature - ambient.
% Assumptions: uniform sampling, integer input delay, known ambient level,
% excited input, stable positive-gain plant. This does NOT reconstruct the
% original System Identification Toolbox experiment or actual measurements.
if nargin < 5, ambient = 30; end
u = double(u(:));
temperature = double(temperature(:));
if dt <= 0 || m < 0 || m ~= floor(m) || numel(u) ~= numel(temperature)
    error('Specify positive dt, nonnegative integer m and matching series.');
end
if numel(u) - m - 1 < 5 || any(~isfinite(u)) || any(~isfinite(temperature))
    error('Insufficient or invalid samples.');
end
x = temperature - ambient;
k = (m+2):numel(u);
X = [x(k-1),u(k-1-m)];
if rank(X) < 2, error('Insufficient excitation for two regressors.'); end
ab = X\x(k);
a = ab(1); b = ab(2);
if a <= 0 || a >= 1 || b <= 0
    error('Identified model is not stable and positive-gain.');
end
residual = x(k)-X*ab;
estimate = struct('a',a,'b',b,'tau_s',-dt/log(a), ...
    'K',b/(1-a),'theta_s',m*dt,'rmse_c',sqrt(mean(residual.^2)));
end
