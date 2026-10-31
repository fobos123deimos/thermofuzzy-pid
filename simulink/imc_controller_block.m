function [u,kp,ki,kd] = imc_controller_block(reference, measured)
%#codegen
% Independent-form IMC PID: derivatives act on measured signal.
persistent integral_state filter_derivative prior_y
if isempty(integral_state)
    integral_state=0; filter_derivative=0; prior_y=measured;
end
K=7.624; tau=151.6; theta=8.78; lambda=35.3273;
kp=(tau+0.5*theta)/(K*(lambda+theta));
ti=tau+0.5*theta;
td=tau*theta/(2*tau+theta);
ki=kp/ti; kd=kp*td;
e=reference-measured;
fd=8/9*filter_derivative+1/9*(measured-prior_y);
proposal=integral_state+ki*e;
trial=kp*e+proposal-kd*fd;
if ~((trial>10 && e>0) || (trial<0 && e<0))
    integral_state=proposal;
end
u=min(10,max(0,kp*e+integral_state-kd*fd));
filter_derivative=fd; prior_y=measured;
end
