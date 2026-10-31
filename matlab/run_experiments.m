% RUN_EXPERIMENTS - MATLAB standalone reproducible examples.
% Run from the matlab/ directory, or add matlab/ to your path.
p=thesis_parameters();
display(imc_pid_gains(p));
A=simulate_burnin('imc',p);
B=simulate_burnin('fuzzy_sparse',p);
C=simulate_burnin('fuzzy_dense',p,.18);
figure('Color','white'); hold on;
plot(A.time_s,A.measurement_c,'LineWidth',1.5);
plot(B.time_s,B.measurement_c,'LineWidth',1.5);
plot(C.time_s,C.measurement_c,'LineWidth',1.5);
yline(p.reference,'--','Reference 65 C');
xlabel('Time (s)'); ylabel('Measured temperature (C)');
title('Synthetic Burn-in Controller Comparison (NOT measured data)');
legend('IMC','TCC sparse Fuzzy','New dense + smoothed Fuzzy','Location','best');
grid on;
if ~exist('outputs','dir'), mkdir('outputs'); end
writetable(A,fullfile('outputs','imc.csv'));
writetable(B,fullfile('outputs','fuzzy_sparse.csv'));
writetable(C,fullfile('outputs','fuzzy_dense.csv'));
saveas(gcf,fullfile('outputs','comparison.png'));
