
clear all;
% clc;
close all

%REGIONAL_STRATEGY = 'EA-VaFi';
% ID = 's1_40x30_HWS_GWB_Heavy_Vs11';
ID = 'MFD6B';

% % haz_level = 'IL_1';
baseDirectory = '/Users/laxmandahal/Desktop/UCLA/Phd/Research/woodSDA/autoWoodSDA_public' ;
% baseDirectory = '/u/home/l/laxmanda/project-hvburton/autoWoodSDA';
codeDir = fullfile(baseDirectory, 'Codes', 'lossModule', 'Loss_ATC138', 'PBEE-Recovery');


for i = 1:18
    haz_level = ['IL_' num2str(i)];
%     haz_level = 'IL_1';
    fn_driver_convert_Pelicun(ID, haz_level, baseDirectory);
    fn_build_inputs(ID, haz_level, baseDirectory);
    cd(codeDir)
    fn_driver_recovery(ID, haz_level, baseDirectory);
end