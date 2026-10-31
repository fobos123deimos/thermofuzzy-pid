function build_burnin_simulink()
%BUILD_BURNIN_SIMULINK Programmatically generate TWO closed-loop .slx models.
% Requirements: MATLAB, Simulink, MATLAB Function block/Stateflow integration.
% These .slx models were NOT prebuilt/verified without a MATLAB runtime.
% MATLAB R2021b+ recommended; check block paths on your release.
root = fileparts(mfilename('fullpath'));
models = {'burnin_imc','burnin_fuzzy_dense'};
functions = {'imc_controller_block.m','fuzzy_controller_block.m'};
for idx = 1:2
    model = models{idx};
    if bdIsLoaded(model), close_system(model,0); end
    new_system(model); load_system(model);
    set_param(model,'Solver','ode1','FixedStep','1','StopTime','3750');
    add_block('simulink/Sources/Constant',[model '/Reference 65 C'],...
        'Value','65','Position',[35 90 95 120]);
    add_block('simulink/User-Defined Functions/MATLAB Function',...
        [model '/Adaptive PID'], 'Position',[155 70 325 155]);
    % Set the exact controller code; all gains are internal and reproducible.
    chart=find(sfroot,'-isa','Stateflow.EMChart','Path',[model '/Adaptive PID']);
    assert(~isempty(chart),'Could not locate Stateflow.EMChart');
    chart.Script=fileread(fullfile(root,functions{idx}));
    add_block('simulink/Math Operations/Sum',[model '/Heat and Door'],...
        'Inputs','++','Position',[405 90 425 145]);
    add_block('simulink/Continuous/Transfer Fcn',[model '/Thermal FOPDT'],...
        'Numerator','7.624','Denominator','[151.6 1]',...
        'Position',[480 90 580 130]);
    add_block('simulink/Sources/Constant',[model '/Ambient 30 C'],...
        'Value','30','Position',[480 205 550 240]);
    add_block('simulink/Math Operations/Sum',[model '/Temperature + Ambient'],...
        'Inputs','++','Position',[635 105 655 160]);
    add_block('simulink/Continuous/Transport Delay',[model '/Sensor deadtime'],...
        'DelayTime','8.78','InitialOutput','30','Position',[715 95 815 135]);
    add_block('simulink/Sinks/To Workspace',[model '/Temperature'],...
        'VariableName','measured_temperature','SaveFormat','Array',...
        'Position',[865 90 965 125]);
    add_block('simulink/Sinks/To Workspace',[model '/Heater'],...
        'VariableName','heater_signal','SaveFormat','Array',...
        'Position',[365 205 460 240]);
    % Door openings at 2000 s (1 min) and 3000 s (5 min):
    % intensities are explicitly assumed, not measured.
    profile=[0 0; 1999 0; 2000 -5; 2059 -5; 2060 0;...
             2999 0; 3000 -5; 3299 -5; 3300 0; 3750 0];
    assignin('base','door_profile',profile);
    add_block('simulink/Sources/From Workspace',[model '/Synthetic doors'],...
        'VariableName','door_profile','Interpolate','off',...
        'Position',[250 280 365 320]);
    add_line(model,'Reference 65 C/1','Adaptive PID/1','autorouting','on');
    add_line(model,'Adaptive PID/1','Heat and Door/1','autorouting','on');
    add_line(model,'Adaptive PID/1','Heater/1','autorouting','on');
    add_line(model,'Synthetic doors/1','Heat and Door/2','autorouting','on');
    add_line(model,'Heat and Door/1','Thermal FOPDT/1','autorouting','on');
    add_line(model,'Thermal FOPDT/1','Temperature + Ambient/1','autorouting','on');
    add_line(model,'Ambient 30 C/1','Temperature + Ambient/2','autorouting','on');
    add_line(model,'Temperature + Ambient/1','Sensor deadtime/1','autorouting','on');
    add_line(model,'Sensor deadtime/1','Temperature/1','autorouting','on');
    add_line(model,'Sensor deadtime/1','Adaptive PID/2','autorouting','on');
    % Remaining Kp/Ki/Kd outputs are intentionally optional analysis ports.
    try
        Simulink.BlockDiagram.arrangeSystem(model);
    catch
        % Automatic layout may be missing in older releases.
    end
    output=fullfile(root,[model '.slx']);
    save_system(model,output);
    fprintf('Created %s\n',output);
    close_system(model);
end
end
