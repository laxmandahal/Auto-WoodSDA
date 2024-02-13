function fn_driver_recovery(ID, haz_level, baseDirectory)
%FN_DRIVER_RECOVERY Summary of this function goes here
%   Detailed explanation goes here
% clear
close all
clc 
rehash


% %% Define User Inputs
% REGIONAL_STRATEGY = 'EA-VaFi';
% ID = 's4_60x32_Stucco_GWB_Normal_Vs82';
% haz_level = 'IL_1';
% baseDirectory = '/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy/woodSDPA' ;
% baseDirectory = '/u/home/l/laxmanda/project-hvburton/Regional_study/woodSDPA';

loss_modelDir = fullfile(baseDirectory, 'Results', ID, 'LossAnalysis');
static_data_dir = fullfile(baseDirectory, 'Codes', 'lossModule', 'Loss_ATC138','PBEE-Recovery', 'static_tables');
output_dir = fullfile(loss_modelDir, 'ATC138Output', haz_level);
% 
% model_name = 'ICSB'; % Name of the model;
%                      % inputs are expected to be in a directory with this name
%                      % outputs will save to a directory with this name
% model_dir = ['inputs' filesep 'example_inputs']; % Directory where the simulated inputs are located
% outputs_dir = ['outputs' filesep model_name]; % Directory where the assessment outputs are saved

%% Load FEMA P-58 performance model data and simulated damage and loss
% load([model_dir filesep model_name filesep 'simulated_inputs.mat'])
load(fullfile(loss_modelDir, 'ATC138Input', haz_level, 'simulated_inputs.mat'))
%% Load required static data
% systems = readtable(['static_tables' filesep 'systems.csv']);
% subsystems = readtable(['static_tables' filesep 'subsystems.csv']);
% impeding_factor_medians = readtable(['static_tables' filesep 'impeding_factors.csv']);
% tmp_repair_class = readtable(['static_tables' filesep 'temp_repair_class.csv']);

systems = readtable(fullfile(static_data_dir, 'systems.csv'), 'Format','auto');
subsystems = readtable(fullfile(static_data_dir, 'subsystems.csv'), 'Format','auto');
impeding_factor_medians = readtable(fullfile(static_data_dir, 'impeding_factors.csv'), 'Format','auto');
tmp_repair_class = readtable(fullfile(static_data_dir, 'temp_repair_class.csv'), 'Format','auto');

%% Run Recovery Method
[functionality, damage_consequences] = main_PBEErecovery(damage, damage_consequences, ...
    building_model, tenant_units, systems, subsystems, tmp_repair_class, ...
    impedance_options, impeding_factor_medians, repair_time_options, ...
    functionality, functionality_options);

%% Save Outputs
if ~exist(output_dir,'dir')
    mkdir(output_dir)
end
fprintf('Recovery assessment of model %s complete: %s\n',ID, haz_level)
% Write file
fileID = fopen(fullfile(loss_modelDir, 'ATC138Output', haz_level, 'recovery_outputs.json'),'w');
fprintf(fileID,'%s',jsonencode(functionality));
fclose(fileID);

end

