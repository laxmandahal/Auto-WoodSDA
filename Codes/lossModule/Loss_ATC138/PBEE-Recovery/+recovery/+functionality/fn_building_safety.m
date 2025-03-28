function [ recovery_day, comp_breakdowns ] = fn_building_safety( ...
    damage, building_model, damage_consequences, utilities, ...
    functionality_options, impeding_temp_repairs )
% Check damage that would cause the whole building to be shut down due to
% issues of safety
%
% Parameters
% ----------
% damage: struct
%   contains per damage state damage, loss, and repair time data for each 
%   component in the building
% damage_consequences: struct
%   data structure containing simulated building consequences, such as red
%   tags and repair costs ratios
% building_model: struct
%   general attributes of the building model
% utilities: struct
%   data structure containing simulated utility downtimes
% functionality_options: struct
%   recovery time optional inputs such as various damage thresholds
% impeding_temp_repairs: struct
%   contains simulated temporary repairs the impede occuapancy and function
%   but are calulated in parallel with the temp repair schedule
%
% Returns
% -------
% recovery_day: struct
%   simulation of the number of days each fault tree event is affecting building
%   safety
% comp_breakdowns: struct
%   simulation of each components contributions to each of the fault tree events 

%% Initial Setup
num_reals = length(damage_consequences.red_tag);
num_units = length(damage.tenant_units);
num_comps = height(damage.comp_ds_table);

% Initialize parameters
recovery_day.red_tag = zeros(num_reals, 1);
recovery_day.shoring = zeros(num_reals, 1);
recovery_day.hazardous_material = zeros(num_reals, 1);
recovery_day.fire_suppression = zeros(num_reals, 1);

% check if building has fire supprsion system
fs_exists = any(damage.fnc_filters.fire_building);

%% Check damage throughout the building that can affect the entire building
for tu = 1:num_units
    % Grab tenant and damage info for this tenant unit
    repair_complete_day = damage.tenant_units{tu}.recovery.repair_complete_day;
    repair_complete_day_w_tmp = damage.tenant_units{tu}.recovery.repair_complete_day_w_tmp;
    
    is_damaged = damage.tenant_units{tu}.qnt_damaged > 0 & damage.tenant_units{tu}.worker_days > 0;
    
    %% Red Tags
    % The day the red tag is resolved is the day when all damage (anywhere in building) that has
    % the potentail to cause a red tag is fixed (ie max day)
    if any(damage.fnc_filters.red_tag)
        recovery_day.red_tag = max(recovery_day.red_tag, ...
            damage_consequences.red_tag .* max(repair_complete_day(:,damage.fnc_filters.red_tag),[],2)); 
    end
    
    % Componet Breakdowns
    comp_breakdowns.red_tag(:,:,tu) = recovery_day.red_tag .* damage_consequences.red_tag_impact;
    
    %% Local Shoring
    if any(damage.fnc_filters.requires_shoring) && functionality_options.include_local_stability_impact
        % Any unresolved damage (temporary or otherwise) that requires shoring,
        % blocks occupancy to the whole building
        recovery_day.shoring = max(recovery_day.shoring, ...
            max(repair_complete_day_w_tmp(:,damage.fnc_filters.requires_shoring),[],2)); 
    
        % Componet Breakdowns (the time it takes to shore or fully repair each
        % component is the time it blocks occupancy for)
        comp_breakdowns.shoring(:,:,tu) = damage.fnc_filters.requires_shoring .* repair_complete_day_w_tmp .* is_damaged;
    end
    
    %% Day the fire suppression system is operating again (for the whole building)
    if ~functionality_options.fire_watch && fs_exists
        % any major damage fails the system for the whole building so take the max
        recovery_day.fire_suppression = max(recovery_day.fire_suppression,max(repair_complete_day(:,damage.fnc_filters.fire_building),[],2));
    
        % Consider utilities (assume no backup water supply)
        recovery_day.fire_suppression = max(recovery_day.fire_suppression,utilities.water); 

        % Componet Breakdowns
        comp_breakdowns.fire_suppression(:,:,tu) = damage.fnc_filters.fire_building .* repair_complete_day;
    end

    %% Hazardous Materials
    % note: hazardous materials are accounted for in building functional
    % assessment here, but are not currently quantified in the component
    % breakdowns
    if any(damage.fnc_filters.global_hazardous_material)
        % Any global hazardous material shuts down the entire building
        recovery_day.hazardous_material = max(recovery_day.hazardous_material, max(repair_complete_day(:,damage.fnc_filters.global_hazardous_material),[],2)); 
    end
end

%% Building Egress
% Calculate when falling hazards or racking of doors affects the building
% safety due to limited entrance and exit door access

% Simulate a random location of the doors on two sides of the building for
% each realization. Location is defined at the center of the door as a
% fraction of the building width on that side
% This is acting a random p value to determine if the unknown location of
% the door is within the falling hazard zone
door_location = rand(num_reals,building_model.num_entry_doors);

% Assign odd doors to side 1 and even doors to side two
door_numbers = 1:building_model.num_entry_doors;
door_side = ones(1,building_model.num_entry_doors);
door_side(rem(door_numbers, 2) == 0) = 2;

% Determine the quantity of falling hazard damage and when it will be
% resolved
day_repair_fall_haz = zeros(num_reals,building_model.num_entry_doors);
fall_haz_comps_day_rep = zeros(num_reals,num_comps,num_units,building_model.num_entry_doors);
comp_affected_area = zeros(num_reals,num_comps,num_units);
scaffold_filt = logical(damage.comp_ds_table.resolved_by_scaffolding');
for tu = 1:num_units
    tmp_or_full_complete_day = damage.tenant_units{tu}.recovery.repair_complete_day_w_tmp;
    
    % Effect of falling hazards on building safety are resolved either by
    % full repair, local temp repair, or erecting scaffolding. Whatever
    % occurs first
    isdamaged = 1*(damage.tenant_units{tu}.qnt_damaged > 0);
    isdamaged(isdamaged == 0) = NaN; % mark undamaged cases as NaN to help combine factors below
    scaffold_day = impeding_temp_repairs.scaffold_day .*  isdamaged(:,scaffold_filt);
    complete_day_w_scaffold = tmp_or_full_complete_day;
    complete_day_w_scaffold(:,scaffold_filt) = ...
        min(tmp_or_full_complete_day(:,scaffold_filt),scaffold_day);
    repair_complete_day_w_tmp(:,:,tu) = complete_day_w_scaffold;
end

% Loop through component repair times to determine the day it stops affecting re-occupancy
num_repair_time_increments = sum(damage.fnc_filters.ext_fall_haz_all)*num_units; % possible unique number of loop increments
%%% changes made by Laxman on 03/21/2023:
%%% added a conditional statement to ensure edge_lengths are
%%% properly parsed in one-story buildings
if num_units == 1
    edge_lengths = [building_model.edge_lengths, building_model.edge_lengths];
else
    edge_lengths = [building_model.edge_lengths; building_model.edge_lengths];
end
% edge_lengths = [building_model.edge_lengths; building_model.edge_lengths];
for i = 1:num_repair_time_increments 
    % Calculate the falling hazards per side
    for tu = 1:num_units
        for side = 1:4 % assumes there are 4 sides
            area_affected_lf_all_comps = damage.comp_ds_table.fraction_area_affected' .* ...
                damage.comp_ds_table.unit_qty' .* building_model.ht_per_story_ft(tu) .* damage.tenant_units{tu}.(['qnt_damaged_side_' num2str(side)]);
            area_affected_sf_all_comps = damage.comp_ds_table.fraction_area_affected' .* ...
                damage.comp_ds_table.unit_qty' .* damage.tenant_units{tu}.(['qnt_damaged_side_' num2str(side)]);

            comp_affected_area(:,damage.fnc_filters.ext_fall_haz_lf,tu) = area_affected_lf_all_comps(:,damage.fnc_filters.ext_fall_haz_lf);
            comp_affected_area(:,damage.fnc_filters.ext_fall_haz_sf,tu) = area_affected_sf_all_comps(:,damage.fnc_filters.ext_fall_haz_sf);

            comp_affected_ft_this_story = comp_affected_area(:,:,tu) ./ building_model.ht_per_story_ft(tu);
            affected_ft_this_story = sum(comp_affected_ft_this_story,2); % Assumes cladding components do not occupy the same perimeter space
            %%% changes made by Laxman on 03/21/2023:
            %%% added a conditional statement to ensure edge_lengths are
            %%% properly parsed in one-story buildings
            if num_units == 1
                affected_ratio.(['side_' num2str(side)])(:,tu) = min((affected_ft_this_story) ./ edge_lengths(side),1);
            else
                affected_ratio.(['side_' num2str(side)])(:,tu) = min((affected_ft_this_story) ./ edge_lengths(side,tu),1);
            end
%             affected_ratio.(['side_' num2str(side)])(:,tu) = min((affected_ft_this_story) ./ edge_lengths(side,tu),1);
        end
    end

    % Calculate the time increment for this loop
    delta_day = min(min(repair_complete_day_w_tmp(:,damage.fnc_filters.ext_fall_haz_all,:),[],3),[],2);
    delta_day(isnan(delta_day)) = 0;
    if sum(delta_day) == 0
        break % everything has been fixed
    end
    
    % Go through each door to determine which is affected by falling hazards
    for d = 1:building_model.num_entry_doors
        % Combine affected areas of all stories above the first using SRSS
        % HARDCODED ASSUMPTIONS: DOORS ONLY ON TWO SIDES
        fall_haz_zone = min(sqrt(sum(affected_ratio.(['side_' num2str(door_side(d))])(:,2:end) .^2,2)),1);

        % Augment the falling hazard zone with the door access zone
        % add the door access width to the width of falling hazards to account
        % for the width of the door (ie if any part of the door access zone is
        % under the falling hazard, its a problem)
        door_access_zone = functionality_options.door_access_width_ft / building_model.edge_lengths(door_side(d),1); 
        total_fall_haz_zone = fall_haz_zone + 2*door_access_zone; % this is approximating the probability the door is within the falling hazard zone

        % Determine if current damage affects occupancy
        % if the randonmly simulated door location is with falling hazard zone
        affects_door = door_location(:,door_side(d)) < total_fall_haz_zone;

        % Add days in this increment to the tally
        day_repair_fall_haz(:,d) = day_repair_fall_haz(:,d) + affects_door .* delta_day;

        % Add days to components that are affecting occupancy
        fall_haz_comps_day_rep(:,:,:,d) = fall_haz_comps_day_rep(:,:,:,d) + comp_affected_area .* damage.fnc_filters.ext_fall_haz_all .* affects_door .* delta_day;
    end
    
    % Change the comps for the next increment
    repair_complete_day_w_tmp = repair_complete_day_w_tmp - delta_day;
    repair_complete_day_w_tmp(repair_complete_day_w_tmp <= 0) = NaN;
end

% Determine when racked doors are resolved
day_repair_racked = zeros(num_reals, building_model.num_entry_doors);
side_1_count = 0;
side_2_count = 0;
for d = 1:building_model.num_entry_doors
    if door_side(d) == 1
        side_1_count = side_1_count + 1;
        day_repair_racked(:,d) = impeding_temp_repairs.door_racking_repair_day .* (damage_consequences.racked_entry_doors_side_1 >= side_1_count);
    else 
        side_2_count = side_2_count + 1;
        day_repair_racked(:,d) = impeding_temp_repairs.door_racking_repair_day .* (damage_consequences.racked_entry_doors_side_2 >= side_2_count);
    end
end
door_access_day = max(day_repair_racked,day_repair_fall_haz);

% Find the days until door egress is regained from resolution of both
% falling hazards or door racking
cum_days = 0;
entry_door_access_day = zeros(num_reals,1);
door_access_day_nan = door_access_day;
door_access_day_nan(door_access_day_nan == 0) = NaN;
num_repair_time_increments = building_model.num_entry_doors; % possible unique number of loop increments
for i = 1:num_repair_time_increments
    num_accessible_doors = sum(door_access_day <= cum_days,2);
    entry_door_accessible = num_accessible_doors >= max(functionality_options.min_egress_paths,functionality_options.egress_threshold*building_model.num_entry_doors); 
            
    % Bean counting for this iteration
    delta_day = min(door_access_day_nan,[],2);
    delta_day(isnan(delta_day)) = 0;
    door_access_day_nan = door_access_day_nan - delta_day;
    cum_days = cum_days + delta_day;
    
    % Save recovery time increments
    entry_door_access_day = entry_door_access_day + delta_day .* ~entry_door_accessible;
end

% Save recovery day values
recovery_day.entry_door_access = entry_door_access_day;

% Determine when Exterior Falling Hazards or doors actually contribute to re-occupancy
recovery_day.falling_hazard = min(recovery_day.entry_door_access,max(day_repair_fall_haz,[],2));
recovery_day.entry_door_racking = min(recovery_day.entry_door_access,max(day_repair_racked,[],2));

% Component Breakdown
comp_breakdowns.falling_hazard = min(recovery_day.entry_door_access, max(fall_haz_comps_day_rep,[],4));

%% Fire Safety
if ~functionality_options.fire_watch && fs_exists
    comp_breakdowns_local_fire = zeros(num_reals,num_comps,num_units);
    fire_safety_day = zeros(num_reals,num_units); % Day the local fire sprinkler system becomes operational
    filt_fs_drop = damage.fnc_filters.fire_drops;
    filt_fs_branch = damage.fnc_filters.fire_unit;
    for tu = 1:num_units
        repair_complete_day = damage.tenant_units{tu}.recovery.repair_complete_day;
        repair_complete_day(repair_complete_day == 0) = NaN; % Make sure zero repair days are NaN
        damaged_comps = damage.tenant_units{tu}.qnt_damaged;
        num_drops = max(damage.tenant_units{tu}.num_comps .* filt_fs_drop,[],2); % Assumes drops are all in one performance group
        num_branches = max(damage.tenant_units{tu}.num_comps .* filt_fs_branch,[],2); % Assumes branches are all in one performance group
        if sum([num_drops,num_branches]) > 0 % If there are any of these components on in this tenant unit
            % Loop through component repair times to determine the day it stops affecting re-occupanc
            num_repair_time_increments = sum(filt_fs_drop | filt_fs_branch); % possible unique number of loop increments
            for i = 1:num_repair_time_increments 
                % Calculate the ratio of damaged drops and branches on this story
                ratio_damaged_drop = sum(damaged_comps .* filt_fs_drop,2) ./ num_drops; % assumes comps are not simeltaneous
                ratio_damaged_branch = sum(damaged_comps .* filt_fs_branch,2) ./ num_drops; % assumes comps are not simeltaneous

                % Determine if fire drops and branches are adequately operating
                fire_drop_operational = functionality_options.local_fire_damamge_threshold >= ratio_damaged_drop;
                fire_branch_operational = functionality_options.local_fire_damamge_threshold >= ratio_damaged_branch;
                local_fire_operational = fire_drop_operational & fire_drop_operational;
                
                % Add days in this increment to the tally
                delta_day = min(repair_complete_day(:,filt_fs_drop),[],2);
                delta_day(isnan(delta_day)) = 0;
                fire_safety_day(:,tu) = fire_safety_day(:,tu) + ~local_fire_operational .* delta_day;

                % Add days to components that are affecting occupancy
                contributing_drops = ((damaged_comps .* filt_fs_drop) > 0)  .* ~fire_drop_operational; % count all components that contributed to non operational fire drops
                contributing_branches = ((damaged_comps .* filt_fs_drop) > 0)  .* ~fire_branch_operational; % count all components that contributed to non operational fire drops
                contributing_comps = max(contributing_drops,contributing_branches);
                comp_breakdowns_local_fire(:,:,tu) = comp_breakdowns_local_fire(:,:,tu) + contributing_comps .* delta_day;

                % Change the comps for the next increment
                repair_complete_day = repair_complete_day - delta_day;
                repair_complete_day(repair_complete_day <= 0) = NaN;
                fixed_comps_filt = isnan(repair_complete_day);
                damaged_comps(fixed_comps_filt) = 0;
            end
        end
    end

    % Inoperable fire drips on any story shuts down entire building
    fire_safety_day_building = max(fire_safety_day,[],2);
    
    % Combine parts of fire suppression system
    recovery_day.fire_suppression = max(recovery_day.fire_suppression,fire_safety_day_building);
    comp_breakdowns.fire_suppression = max(comp_breakdowns.fire_suppression,comp_breakdowns_local_fire);
end

%% Delay Red Tag recovery by the time it takes to clear the tag
sim_red_tag_clear_time = ceil(lognrnd(log(functionality_options.red_tag_clear_time),...
                                 functionality_options.red_tag_clear_beta,num_reals,1));
recovery_day.red_tag = recovery_day.red_tag + sim_red_tag_clear_time .* damage_consequences.red_tag;
comp_breakdowns.red_tag = comp_breakdowns.red_tag + sim_red_tag_clear_time .* (comp_breakdowns.red_tag > 0);

end

