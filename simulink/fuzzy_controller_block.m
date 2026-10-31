function [u,kp,ki,kd] = fuzzy_controller_block(reference, measured)
%#codegen
% Code-generation-compatible dense Fuzzy MOM scheduler and PID.
% 1-second sample period, gain smoothing gamma=0.18.
% Outputs correspond to original TCC Table 4 (independent gains).
persistent I filter_d last_y last_e normalized
if isempty(I)
    I=0; filter_d=0; last_y=measured;
    last_e=reference-measured; normalized=[.5 .5 .5];
end
e=reference-measured;
de=e-last_e;
% Dense rule base interpolated from TCC Fig. 15; 1=S,2=MS,3=M,4=MB,5=B.
R=zeros(7,7,3);
R(:,:,1)=[3 3 2 3 2 4 5;
          2 2 2 3 2 4 5;
          1 2 2 3 2 4 5;
          1 2 2 3 2 4 5;
          1 2 2 3 2 4 5;
          2 2 2 3 2 4 5;
          3 3 2 3 2 4 5];
R(:,:,2)=[5 3 1 1 1 1 1;
          4 3 1 1 1 1 1;
          3 2 1 1 1 1 1;
          1 1 1 1 1 1 1;
          1 1 1 1 1 1 1;
          4 3 1 1 1 1 1;
          5 3 1 1 1 1 1];
R(:,:,3)=[1 2 2 3 4 5 5;
          1 2 2 2 3 3 3;
          1 1 1 1 2 2 1;
          1 1 1 1 1 1 1;
          1 1 1 1 2 2 1;
          1 2 2 2 3 3 3;
          1 2 2 3 4 5 5];
mu_e=zeros(1,7); mu_d=zeros(1,7);
xe=max(0,min(40,abs(e))); xd=max(-40,min(40,de));
for j=1:7
    mu_e(j)=max(0,1-abs(xe-(j-1)*40/6)/(40/6));
    mu_d(j)=max(0,1-abs(xd-(-40+(j-1)*80/6))/(80/6));
end
h=zeros(3,5);
for i=1:7
    for j=1:7
        fire=min(mu_d(i),mu_e(j));
        for k=1:3
            id=R(i,j,k);
            if id>0
                h(k,id)=max(h(k,id),fire);
            end
        end
    end
end
want=normalized;
for k=1:3
    if max(h(k,:))>0
        maximum=-1; sum_positions=0; maxima_count=0;
        for q=0:200
            x=q/200;
            agg=0;
            for v=1:5
                mf=max(0,1-abs(x-(v-1)/4)/.25);
                agg=max(agg,min(mf,h(k,v)));
            end
            if agg>maximum+1.e-10
                maximum=agg; sum_positions=x; maxima_count=1;
            elseif abs(agg-maximum)<=1.e-10
                sum_positions=sum_positions+x;
                maxima_count=maxima_count+1;
            end
        end
        want(k)=sum_positions/maxima_count;
    end
end
normalized=normalized+.18*(want-normalized);
kp=.35+(.90-.35)*normalized(1);
ki=.0008+(.045-.0008)*normalized(2);
kd=2*normalized(3);
% Derivative on measurement; low-pass filter; conditional anti-windup.
alpha=8/9;
fd=alpha*filter_d+(1-alpha)*(measured-last_y);
proposal=I+ki*e;
trial=kp*e+proposal-kd*fd;
if ~((trial>10 && e>0) || (trial<0 && e<0))
    I=proposal;
end
u=min(10,max(0,kp*e+I-kd*fd));
filter_d=fd; last_y=measured; last_e=e;
end
