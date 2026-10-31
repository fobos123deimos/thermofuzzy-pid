function result = simulate_burnin(mode,p,smoothing)
%SIMULATE_BURNIN Reproducible synthetic FOPDT closed-loop simulation.
% mode: 'imc', 'fuzzy_sparse', 'fuzzy_dense'.
% No original thermal measurements are included.
if nargin < 1, mode='imc'; end
if nargin < 2, p=thesis_parameters(); end
if nargin < 3, smoothing=.18; end
n = round(p.stop_time/p.dt)+1;
t = (0:n-1)'*p.dt;
T = nan(n,1); T(1) = p.ambient;
y = nan(n,1); u = nan(n,1);
d = zeros(n,1); gains = nan(n,3);
for event = 1:size(p.doors,1)
    mask = t >= p.doors(event,1) & t < p.doors(event,2);
    d(mask) = d(mask) + p.doors(event,3);
end
integ=0; fd=0; last_y=NaN; last_e=NaN; normal=[.5 .5 .5];
imc = imc_pid_gains(p);
a = exp(-p.dt/p.tau);
for k=1:n
    shifted=(t(k)-p.theta)/p.dt;
    if shifted <= 0
        sensed=T(1);
    else
        lo = min(floor(shifted)+1,k);
        hi = min(lo+1,k);
        fraction = shifted - floor(shifted);
        if hi==lo, fraction=0; end
        sensed = (1-fraction)*T(lo) + fraction*T(hi);
    end
    y(k)=sensed;
    e=p.reference-y(k);
    de=0;
    if ~isnan(last_e), de=e-last_e; end
    if strcmpi(mode,'imc')
        g=imc;
    elseif strcmpi(mode,'fuzzy_sparse') || strcmpi(mode,'fuzzy_dense')
        if strcmpi(mode,'fuzzy_sparse'), rules='sparse'; else, rules='dense'; end
        target = fuzzy_mom_gains(e,de,normal,rules);
        if strcmpi(mode,'fuzzy_sparse'), gamma=1; else, gamma=smoothing; end
        normal = normal + gamma*(target-normal);
        g = [.35 .0008 0] + ([.90 .045 2]-[.35 .0008 0]).*normal;
    else
        error('Unknown controller mode');
    end
    gains(k,:)=g;
    dm=0;
    if ~isnan(last_y), dm=(y(k)-last_y)/p.dt; end
    alpha_d=8/(8+p.dt);
    fd=alpha_d*fd+(1-alpha_d)*dm;
    prop=g(1)*e; deriv=-g(3)*fd;
    proposed=integ+g(2)*p.dt*e;
    trial=prop+proposed+deriv;
    if ~((trial > p.u_max && e > 0) || (trial < 0 && e < 0))
        integ=proposed;
    end
    u(k)=min(p.u_max,max(0,prop+integ+deriv));
    last_y=y(k); last_e=e;
    if k<n
        T(k+1) = p.ambient + (T(k)-p.ambient)*a + ...
                 p.K*(u(k)+d(k))*(1-a);
    end
end
result=table(t,T,y,u,d,gains(:,1),gains(:,2),gains(:,3),...
  'VariableNames',{'time_s','temperature_c','measurement_c','control',...
                   'disturbance','kp','ki','kd'});
end
