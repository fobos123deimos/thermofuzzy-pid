function metrics = assess_fixed_pid_robustness(p, derivativeFilterTime)
% ASSESS_FIXED_PID_ROBUSTNESS - Fixed linear IMC-PID, no actuator saturation.
% Derived from the PI/PID partial report's GM/PM/Ms robustness discussion.
% Requires MATLAB Control System Toolbox. The dead time is retained exactly
% in the transfer function object; frequency results depend on the grid.
% derivativeFilterTime here is a derivative FILTER time constant in seconds, not
% the back-calculation anti-windup tracking time (which is distinct).
if nargin < 1, p = thesis_parameters(); end
if nargin < 2, derivativeFilterTime = 8; end
if derivativeFilterTime <= 0
    error('Filter time must be positive');
end
g = imc_pid_gains(p);
s = tf('s');
plant = tf(p.K, [p.tau 1], 'InputDelay', p.theta);
controller = g(1) + g(2)/s + g(3)*s/(derivativeFilterTime*s+1);
loop = controller*plant;
[gm, pm, wcg, wcp] = margin(loop);
w = logspace(-6,1,5000);
sens = feedback(1,loop);
response = squeeze(freqresp(sens,w));
ms = max(abs(response));
metrics = struct('gain_margin',gm,'phase_margin_deg',pm, ...
    'max_sensitivity',ms,'phase_crossing_rad_s',wcg,'gain_crossing_rad_s',wcp);
fprintf('GM=%g, PM=%g deg, Ms=%g (fixed linear model only)\n',gm,pm,ms);
end
