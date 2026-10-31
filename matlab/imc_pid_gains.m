function gains = imc_pid_gains(p)
%IMC_PID_GAINS TCC Table 2; returns independent [Kp Ki Kd].
if nargin < 1, p = thesis_parameters(); end
Kp = (p.tau + .5*p.theta)/(p.K*(p.lambda+p.theta));
Ti = p.tau + .5*p.theta;
Td = p.tau*p.theta/(2*p.tau+p.theta);
gains = [Kp, Kp/Ti, Kp*Td];
end
