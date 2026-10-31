function normal = fuzzy_mom_gains(error, delta_error, previous, mode)
%FUZZY_MOM_GAINS Mamdani min/max and mean-of-maxima (M-o-M), TCC Sec. 2.3.
% Assumed equally spaced membership peaks (not fully specified in the TCC).
% Nonnegative error input is interpreted as |r-y|; delta-error is signed.
if nargin < 3 || isempty(previous), previous = [.5, .5, .5]; end
if nargin < 4, mode = 'sparse'; end
R = fuzzy_rule_matrix(mode);
e = max(0,min(40,abs(error)));
de = max(-40,min(40,delta_error));
ce = linspace(0,40,7);
cd = linspace(-40,40,7);
mu_e = max(0,1-abs(e-ce)/(40/6));
mu_d = max(0,1-abs(de-cd)/(80/6));
heights = zeros(3,5);
for i = 1:7
    for j = 1:7
        fire = min(mu_d(i),mu_e(j));
        if fire <= 0, continue; end
        for k = 1:3
            out = R(i,j,k);
            if out > 0
                heights(k,out) = max(heights(k,out),fire);
            end
        end
    end
end
normal = previous;
xx = linspace(0,1,201);
for k = 1:3
    if max(heights(k,:)) == 0, continue; end
    agg = zeros(1,numel(xx));
    for v = 1:5
        mu = max(0,1-abs(xx-(v-1)/4)/.25);
        agg = max(agg,min(mu,heights(k,v)));
    end
    peak = max(agg);
    normal(k) = mean(xx(abs(agg-peak) <= 1.e-10));
end
end
