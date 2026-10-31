function R = fuzzy_rule_matrix(mode)
%FUZZY_RULE_MATRIX Consequents from Figure 15 (undergraduate thesis printed page 36).
% Shape: rows d(error), columns |error|, pages Kp, Ki, Kd.
% Labels: S=1, MS=2, M=3, MB=4, B=5; zero means unspecified.
% Whole NM and PM columns are missing in the original undergraduate thesis.
% With 'dense', zeros are filled by a novel interpolation assumption.
if nargin < 1, mode = 'sparse'; end
R = zeros(7,7,3);
R(:,:,1) = [3 0 2 3 2 0 5;
            2 0 2 3 2 0 5;
            1 0 2 3 2 0 5;
            1 0 2 3 2 0 5;
            1 0 2 3 2 0 5;
            2 0 2 3 2 0 5;
            3 0 2 3 2 0 5];
R(:,:,2) = [5 0 1 1 0 0 1;
            4 0 1 1 1 0 1;
            3 0 1 1 1 0 1;
            1 0 1 1 1 0 1;
            1 0 1 1 1 0 1;
            4 0 1 1 1 0 1;
            5 0 1 1 0 0 1];
R(:,:,3) = [1 0 2 3 4 0 5;
            1 0 2 2 3 0 3;
            1 0 1 1 2 0 1;
            1 0 1 1 1 0 1;
            1 0 1 1 2 0 1;
            1 0 2 2 3 0 3;
            1 0 2 3 4 0 5];
if strcmpi(mode,'dense')
    for i = 1:7
        for k = 1:3
            row = squeeze(R(i,:,k));
            present = find(row > 0);
            R(i,:,k) = round(interp1(present,row(present),1:7,'linear','extrap'));
        end
    end
elseif ~strcmpi(mode,'sparse')
    error('mode must be sparse or dense');
end
end
