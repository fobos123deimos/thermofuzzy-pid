function p = thesis_parameters()
%THESIS_PARAMETERS Reported FOPDT identification values, TCC Sec. 3.1.
% The 2021 TCC reported identification of the combined plant/sensor channel.
p = struct();
p.models.TH37 = [8.7135, 326.18, 13.677];
p.models.TH34 = [7.7473, 177.95, 13.064];
p.models.mean_temperature = [7.624, 151.6, 8.78];
p.models.mean_parameters  = [8.028, 186.5, 12.5];
p.K = 7.624;
p.tau = 151.6; % s
p.theta = 8.78; % s
p.ambient = 30.0; % Celsius: synthetic assumption
p.reference = 65.0; % Celsius: from TCC Sec. 3.4
p.u_max = 10.0; % effective heater units: synthetic assumption
p.dt = 1.0; % s: numerical choice
p.stop_time = 3750.0; % s: from TCC Sec. 3.1
p.lambda = 35.3273; % s: from TCC Sec. 4
p.doors = [2000, 2060, -5.0; 3000, 3300, -5.0];
% Door intensities/durations above illustrate Fig. 4/Sec. 3.4 and are NOT
% experimentally identified original data.
end
