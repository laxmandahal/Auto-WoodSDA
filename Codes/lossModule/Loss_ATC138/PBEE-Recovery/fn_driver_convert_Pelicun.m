function fn_driver_convert_Pelicun(ID, haz_level, baseDirectory)
%FN_DRIVER_CONVERT_PELICUN Summary of this function goes here
%   Detailed explanation goes here


% % close all
% % clc
rehash
warning('off', 'all')



%% Define Inputs
% model_dir = ['inputs' filesep 'example_pelicun_inputs' filesep model_name]; % Directory where the simulated inputs are located
% fprintf('Archetype ID is: %s \n', ID);
loss_modelDir = fullfile(baseDirectory, 'Results', ID, 'LossAnalysis');
%% Load Pelicun Outputs
pelicun_results_dir = fullfile(loss_modelDir, 'PelicunOutput');

% Pull basic model info from Pelicun Inputs
fileID = fopen(fullfile(loss_modelDir, 'PelicunInput', 'model_config.json'), 'r');
pelicun_inputs = jsondecode(fscanf(fileID,'%s'));
fclose(fileID);
num_stories = str2double(pelicun_inputs.DL.Asset.NumberOfStories);
% total_cost = str2double(pelicun_inputs.DL.Losses.BldgRepair.ReplacementCost.Median);
% plan_area = str2double(pelicun_inputs.DL.Asset.PlanArea);

% Pull components from DL_model.json
comps = readtable(fullfile(pelicun_inputs.DL.Asset.ComponentAssignmentFile),...
    'Format','auto');

% Pull repair cost realizations
DV_rec_cost_agg = readtable(fullfile(pelicun_results_dir, haz_level, 'DL_summary.csv'));

% Pull realizations of damaged components
DMG = readtable(fullfile(pelicun_results_dir, haz_level, 'DMG_sample.csv'));
frag_col_filt = ~cellfun(@isempty,regexp(DMG.Properties.VariableNames,'^B_')) | ...
                ~cellfun(@isempty,regexp(DMG.Properties.VariableNames,'^C_')) | ...
                ~cellfun(@isempty,regexp(DMG.Properties.VariableNames,'^D_')) | ...
                ~cellfun(@isempty,regexp(DMG.Properties.VariableNames,'^E_')) | ...
                ~cellfun(@isempty,regexp(DMG.Properties.VariableNames,'^F_'));
DMG = DMG(:,frag_col_filt); % Filt to only component level damage
DMG_ids = DMG.Properties.VariableNames;

% Pull realization of repair time per componentDS
DV = readtable(fullfile(pelicun_results_dir, haz_level, 'DV_bldg_repair_sample.csv'));
rec_time_filt = ~cellfun(@isempty,regexp(DV.Properties.VariableNames,'^TIME'));
DV_time = DV(:,rec_time_filt); % Filt to only component level damage
repair_cost_filt = ~cellfun(@isempty,regexp(DV.Properties.VariableNames,'^COST'));
DV_cost = DV(:,repair_cost_filt); % Filt to only component level damage

%% Load ATC 138 model input data
% tenant_unit_list = readtable(fullfile(loss_modelDir, 'ATC138Input', 'tenant_unit_list.csv'));

static_data_dir = fullfile(baseDirectory, 'Codes', 'lossModule', 'Loss_ATC138','PBEE-Recovery', 'static_tables');

ds_attributes = readtable(fullfile(static_data_dir, 'damage_state_attribute_mapping.csv'));


fileID = fopen(fullfile(loss_modelDir, 'ATC138Input', 'building_model.json'), 'r');
building_model = jsondecode(fscanf(fileID,'%s'));
fclose(fileID);
%% Develop damage_consequences.json
% Pull data from Pelicun structure 
sim_repair_cost = DV_rec_cost_agg.repair_cost_;
sim_replacement_time = NaN(height(DV_rec_cost_agg),1);
sim_replacement_filt = DV_rec_cost_agg.collapse | DV_rec_cost_agg.irreparable;
sim_replacement_time(sim_replacement_filt) = ...
    mean([DV_rec_cost_agg.repair_time_parallel(sim_replacement_filt),...
    DV_rec_cost_agg.repair_time_parallel(sim_replacement_filt)],2); % Take the average of parallel and series rep times (they should be the same)

% Set Variables
damage_consequences.repair_cost_ratio_total = sim_repair_cost / building_model.building_value;  % array, num real x 1
damage_consequences.simulated_replacement_time = sim_replacement_time;

% Write file
% fileID = fopen([model_dir filesep 'damage_consequences.json'],'w');
fileID = fopen(fullfile(loss_modelDir, 'ATC138Input', haz_level, 'damage_consequences.json'),'w');
fprintf(fileID,'%s',jsonencode(damage_consequences));
fclose(fileID);

%% Build comp_population.csv
comp_population.story = zeros(num_stories*3,1);
comp_population.dir = zeros(num_stories*3,1);
for c = 1:height(comps)-3
    idx = 1;
    comp = comps(c,:);            
    frag_id = comp.ID{1};
    frag_id([2,5]) = []; % Remove extra periods
    frag_id = strrep(frag_id,'.','_');
    comp_population.(frag_id) = zeros(num_stories*3,1);
    loc = comp.Location{1};
    dir = comp.Direction{1};
    for s = 1:num_stories
        if  strcmp(loc,'all')
            is_story = true;
        elseif  strcmp(loc,'roof')
            is_story = s == num_stories;
        elseif  contains(loc,'--')
            is_story = s >= str2double(loc(1)) & s<= str2double(loc(end));
        else
            loc_vec = str2double(strsplit(loc));
            is_story = ismember(s,loc_vec);
        end
        
        for d = 1:3
            comp_population.story(idx) = s;
            comp_population.dir(idx) = d;
            dir_str = strrep(dir,'0','3'); % replace nondirection identifier
            dir_vec = str2double(strsplit(dir_str,','));
            is_dir = ismember(d,dir_vec);

            if is_story && is_dir
                % Assign to component population table (add duplicates)
                comp_population.(frag_id)(idx) = comp_population.(frag_id)(idx) + comp.Theta_0;
            end

            idx = idx + 1;
        end
    end
end

% Convert to table and save
comp_population = struct2table(comp_population);
writetable(comp_population, fullfile(loss_modelDir, 'ATC138Input', 'comp_population.csv'));

%% Build comp_ds_list.csv
idx = 0;
unique_comps = unique(comps.ID); % Only one entry per unique component id
for c = 1:length(unique_comps)
    frag_id = unique_comps{c};
    frag_id([2,5]) = []; % Remove extra periods
    ds_filt = ~cellfun(@isempty,regexp(frag_id,ds_attributes.fragility_id_regex));
    ds_match = ds_attributes(ds_filt,:);
    for ds = 1:height(ds_match)
        idx = idx + 1;
        comp_ds_list.comp_id{idx,1} = frag_id;
        comp_ds_list.ds_seq_id(idx,1) = ds_match.ds_index(ds);
        if strcmp(ds_match.sub_ds_index{ds},'NA')
            comp_ds_list.ds_sub_id(idx,1) = 1;
        else
            comp_ds_list.ds_sub_id(idx,1) = str2double(ds_match.sub_ds_index{ds});
        end
    end
end

% Convert to table and save
comp_ds_list = struct2table(comp_ds_list);
writetable(comp_ds_list, fullfile(loss_modelDir, 'ATC138Input', haz_level, 'comp_ds_list.csv'));

%% Develop simulated damage.json
[num_reals,~] = size(DMG(:,2:end));

% Set Variables
count = 0;
for s = 1:num_stories
    % Initialize variables
    simulated_damage.story(s).qnt_damaged = zeros(num_reals,height(comp_ds_list));
    simulated_damage.story(s).worker_days = zeros(num_reals,height(comp_ds_list));
    simulated_damage.story(s).repair_cost = zeros(num_reals,height(comp_ds_list));
    simulated_damage.story(s).qnt_damaged_dir_1 = zeros(num_reals,height(comp_ds_list));
    simulated_damage.story(s).qnt_damaged_dir_2 = zeros(num_reals,height(comp_ds_list));
    simulated_damage.story(s).qnt_damaged_dir_3 = zeros(num_reals,height(comp_ds_list));
    simulated_damage.story(s).num_comps = zeros(height(comp_ds_list),1);
       
    % Go through each ds in PELICUN outputs and assign to simualated damage
    % data structure
    for c = 1:length(DMG_ids)
        % Identify attributes of column IDS
        DMG_id = strsplit(DMG_ids{c},'_');
        frag_id = [DMG_id{1} DMG_id{2} DMG_id{3} '.' DMG_id{4}];
        frag_filt = strcmp(comp_ds_list.comp_id,frag_id);
        loc_id = str2double(DMG_id{end-2});
        dir_id = str2double(DMG_id{end-1});
        if dir_id == 0
            dir_id = 3; % Change nondirection indexing
        end
        ds_id = str2double(DMG_id{end});
        
        % Find the associated column in the repair time table
        frag_id_DV = [DMG_id{1} '_' DMG_id{2} '_' DMG_id{3} '_' DMG_id{4} '_' num2str(ds_id) '_' DMG_id{5} '_' DMG_id{6}];
        DV_filt = contains(DV_time.Properties.VariableNames,frag_id_DV);
        
        % Assign simulated damage to new structure
        if loc_id == s  && ds_id > 0 && any(frag_filt) % Only if there are components on this story
            comp_ds = comp_ds_list(frag_filt,:);
            seq_ds_filt = comp_ds_list.ds_seq_id == comp_ds.ds_seq_id(ds_id);
            sub_ds_filt = comp_ds_list.ds_sub_id == comp_ds.ds_sub_id(ds_id);
            sim_dmg_idx_filt = (frag_filt & seq_ds_filt & sub_ds_filt)';
            if sum(sim_dmg_idx_filt) == 1 && sum(DV_filt) == 1 % if you find matching components
                % Assign Damage data
                dmg_data = DMG{:,c};
                dmg_data(isnan(dmg_data)) = 0; % Change blank cases to no damage
                simulated_damage.story(s).qnt_damaged(:,sim_dmg_idx_filt) = ...
                    simulated_damage.story(s).qnt_damaged(:,sim_dmg_idx_filt) + dmg_data; % add number of damaged component amongst directions and multiple comps of the same frag id
                
                % Assign Repair time data
                repair_time_data = DV_time{:,DV_filt};
                repair_time_data(isnan(repair_time_data)) = 0; % Change blank cases to no damage
                simulated_damage.story(s).worker_days(:,sim_dmg_idx_filt) = ...
                    simulated_damage.story(s).worker_days(:,sim_dmg_idx_filt) + repair_time_data; % add the repair time amongst directions and multiple comps of the same frag id
                
                % Assign Repair Cost data
                repair_cost_data = DV_cost{:,DV_filt};
                repair_cost_data(isnan(repair_cost_data)) = 0; % Change blank cases to no damage
                simulated_damage.story(s).repair_cost(:,sim_dmg_idx_filt) = ...
                    simulated_damage.story(s).repair_cost(:,sim_dmg_idx_filt) + repair_cost_data; % add the repair time amongst directions and multiple comps of the same frag id
                
                % Assign Damage Data Per Direction
                for dir = 1:3
                    if dir_id == dir % only for the direction associated with this DMG column
                        simulated_damage.story(s).(['qnt_damaged_dir_' num2str(dir)])(:,sim_dmg_idx_filt) = ...
                        simulated_damage.story(s).(['qnt_damaged_dir_' num2str(dir)])(:,sim_dmg_idx_filt) + dmg_data; % add number of damaged component amongst directions and multiple comps of the same frag id
                    end
                end
            else
                error('Location in new damage state structure could not be found for this compoennt DS')
            end
        end
    end
    
    % Assign component quantities
    for c = 1:height(comps)
        comp = comps(c,:);
        loc = comp.Location{1};
        if  strcmp(loc,'all')
            is_story = true;
        elseif  strcmp(loc,'roof')
            is_story = s == num_stories;
        elseif  contains(loc,'--')
            is_story = s >= str2double(loc(1)) & s<= str2double(loc(end));
        else
            loc_vec = str2double(strsplit(loc));
            is_story = ismember(s,loc_vec);
        end
        
        if is_story
            frag_id = comp.ID{1};
            frag_id([2,5]) = []; % Remove extra periods
            frag_filt = strcmp(comp_ds_list.comp_id,frag_id)';
            simulated_damage.story(s).num_comps(frag_filt) = ...
                simulated_damage.story(s).num_comps(frag_filt) + comp.Theta_0;
        end
    end
end
            
% Write file
% fileID = fopen([model_dir filesep 'simulated_damage.json'],'w');
fileID = fopen(fullfile(loss_modelDir, 'ATC138Input', haz_level, 'simulated_damage.json'),'w');
fprintf(fileID,'%s',jsonencode(simulated_damage));
fclose(fileID);

fprintf('Pelicun Results Converted for ID: %s at %s \n', ID, haz_level);

end

