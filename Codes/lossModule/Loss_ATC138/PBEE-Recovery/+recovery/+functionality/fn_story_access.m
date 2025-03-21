function [ recovery_day, comp_breakdowns ] = fn_story_access(damage, ...
    building_model, damage_consequences, functionality_options, impeding_temp_repairs )
% Check each story for damage that would cause that story to be shut down due to
% issues of access
%
% Parameters
% ----------
% damage: struct
%   contains per damage state damage, loss, and repair time data for each 
%   component in the building
% building_model: struct
%   general attributes of the building model
% damage_consequences: struct
%   data structure containing simulated building consequences, such as red
%   tags and repair costs ratios
% functionality_options: struct
%   recovery time optional inputs such as various damage thresholds
% impeding_temp_repairs: struct
%   contains simulated temporary repairs the impede occuapancy and function
%   but are calulated in parallel with the temp repair schedule
%
% Returns
% -------
% recovery_day: struct
%   simulation of the number of days each fault tree event is affecting access
%   in each story
% comp_breakdowns: struct
%   simulation of each components contributions to each of the fault tree events 

%% Initial Setup
num_reals = length(damage_consequences.red_tag);
num_units = length(damage.tenant_units);
num_stories = length(damage.tenant_units);
num_comps = height(damage.comp_ds_table);

% Pre-allocate data
recovery_day.stairs = zeros(num_reals,num_units);
recovery_day.stair_doors = zeros(num_reals,num_units);
recovery_day.flooding = zeros(num_reals,num_units);
recovery_day.horizontal_egress = zeros(num_reals,num_units);
comp_breakdowns.stairs = zeros(num_reals,num_comps,num_units);
comp_breakdowns.horizontal_egress = zeros(num_reals,num_comps,num_units);

%% Horizontal Egress - Fire breaks
if any(damage.fnc_filters.fire_break)
    for tu = 1:num_stories
        % Grab tenant and damage info for this tenant unit
        repair_complete_day_w_tmp = damage.tenant_units{tu}.recovery.repair_complete_day_w_tmp;

        % Any significant damage to fire breaks in the story impairs the horizontal egress
        recovery_day.horizontal_egress(:,tu) = ...
            max(recovery_day.horizontal_egress(:,tu),...
                max(repair_complete_day_w_tmp(:,damage.fnc_filters.fire_break),[],2)); 

        % Componet Breakdowns
        comp_breakdowns.horizontal_egress(:,:,tu) = damage.fnc_filters.fire_break .* repair_complete_day_w_tmp;
    end
end

%% STORY FLOODING
for tu = flip(1:num_stories) % Go from top to bottom
    is_damaged = damage.tenant_units{tu}.qnt_damaged > 0;
    flooding_this_story = any(is_damaged(:,damage.fnc_filters.causes_flooding),2); % Any major piping damage causes interior flooding
    flooding_cleanup_day = flooding_this_story .* impeding_temp_repairs.flooding_cleanup_day;

    % Save clean up time per component causing flooding
    comp_breakdowns.flooding(:,:,tu) = damage.fnc_filters.causes_flooding .* is_damaged .* flooding_cleanup_day;

    % This story is not accessible if any story above has flooding
    recovery_day.flooding(:,tu) = max([flooding_cleanup_day,recovery_day.flooding(:,(tu+1):end)],[],2);
end

%% STAIRS AND STAIRDOORS
if num_stories == 1 
    return % Re-occupancy of one story buildigns is not affected by stairway access
end

% Augment damage filters with door data
damage.fnc_filters.stairs = logical([damage.fnc_filters.stairs, 0]);
damage.fnc_filters.stair_doors = logical([zeros(1,num_comps), 1]);

%% Go through each story and check if there is sufficient story access (stairs and stairdoors)
% if stairs don't exist on a story, this will assume they are rugged (along with the stair doors)
for tu = 1:num_stories
    % Augment damage matrix with door data
    racked_stair_doors = min(damage_consequences.racked_stair_doors_per_story(:,tu),building_model.stairs_per_story(tu));
    damage.tenant_units{tu}.qnt_damaged = [damage.tenant_units{tu}.qnt_damaged, racked_stair_doors];
    door_repair_day = (racked_stair_doors > 0) .* impeding_temp_repairs.door_racking_repair_day;
    damage.tenant_units{tu}.recovery.repair_complete_day = [damage.tenant_units{tu}.recovery.repair_complete_day, door_repair_day];

    % Quantify damaged stairs on this story
    repair_complete_day = damage.tenant_units{tu}.recovery.repair_complete_day;
    damaged_comps = damage.tenant_units{tu}.qnt_damaged;

    % Make sure zero repair days are NaN
    repair_complete_day(repair_complete_day == 0) = NaN;

    % Step through each unique component repair time and determine when
    % stairs stop affecting story access
    stair_access_day = zeros(num_reals,1); % day story becomes accessible from repair of stairs
    stairdoor_access_day = zeros(num_reals,1); % day story becomes accessible from repair of doors
    filt_all = damage.fnc_filters.stairs | damage.fnc_filters.stair_doors;
    num_repair_time_increments = sum(filt_all); % possible unique number of loop increments
    for i = 1:num_repair_time_increments
        % number of functioning stairs
        num_dam_stairs = sum(damaged_comps .* damage.fnc_filters.stairs,2); % assumes comps are not simeltaneous
        num_racked_doors = sum(damaged_comps .* damage.fnc_filters.stair_doors,2); % assumes comps are not simeltaneous
        functioning_stairs = building_model.stairs_per_story(tu) - num_dam_stairs;
        functioning_stairdoors = building_model.stairs_per_story(tu) - num_racked_doors;

        % Required egress with and without operational fire suppression system
        required_stairs = max(functionality_options.min_egress_paths,functionality_options.egress_threshold .* building_model.stairs_per_story(tu));

        % Determine Stair Access
        sufficient_stair_access  = functioning_stairs >= required_stairs;

        % Determine Stair Door Acces
        sufficient_stairdoor_access  = functioning_stairdoors >= required_stairs;

        % Add days in this increment to the tally
        delta_day = min(repair_complete_day(:,filt_all),[],2);
        delta_day(isnan(delta_day)) = 0;
        stair_access_day = stair_access_day + ~sufficient_stair_access .* delta_day;
        stairdoor_access_day = stairdoor_access_day + ~sufficient_stairdoor_access .* delta_day;

        % Add days to components that are affecting occupancy
        contributing_stairs = ((damaged_comps .* damage.fnc_filters.stairs) > 0)  .* ~sufficient_stair_access; % Count any damaged stairs for realization that have loss of story access
        contributing_stairs(:,end) = []; % remove added door column
        comp_breakdowns.stairs(:,:,tu) = comp_breakdowns.stairs(:,:,tu) + contributing_stairs .* delta_day;

        % Change the comps for the next increment
        repair_complete_day = repair_complete_day - delta_day;
        repair_complete_day(repair_complete_day <= 0) = NaN;
        fixed_comps_filt = isnan(repair_complete_day);
        damaged_comps(fixed_comps_filt) = 0;
    end

    % This story is not accessible if this or any story below has insufficient stair egress
    recovery_day.stairs(:,tu) = max([stair_access_day,recovery_day.stairs(:,1:(tu-1))],[],2);
    
    % For the third story and above, the story below is not accessible if
    % there is insufficient stair egress at this story
    if tu >= 3
        recovery_day.stairs(:,(tu-1)) = max([stair_access_day,recovery_day.stairs(:,(tu-1))],[],2);
    end
    
    % Damage to doors only affects this story
    recovery_day.stair_doors(:,tu) = stairdoor_access_day;
end

end % end function

