
import os 
from pathlib import Path

def create_optional_inputs(pathDir, inspection=True, financing=True, permitting=True, engineering=True, contractor=True,
                            long_lead_time=False, design_time_f=0.04, design_time_r=175, design_time_t=1.3, design_time_w=8, 
                            essential_facility=False, borp_equivalent=False, engineer_on_retainer=False, 
                            contractor_relationship='good', contractor_retainer_time=3, funding_source='private', 
                            capital_available_ratio=0.1, impeding_factors_beta=0.6, impedance_truncation=2, 
                            default_lead_time=182, scaffolding_lead_time=5, scaffolding_erect_time=2, 
                            max_workers_per_sqft_story=0.001, max_workers_per_sqft_story_temp_repair=0.005,
                            max_workers_per_sqft_building = 0.00025,
                            max_workers_building_min=20, max_workers_building_max=260, red_tag_clear_time=7, 
                            red_tag_clear_beta=0.6, door_racking_repair_day=3, egress_threshold=0.5, egress_threshold_wo_fs=0.75,
                            fire_watch=True, min_egress_paths=2, exterior_safety_threshold=0.1, interior_safety_threshold=0.25, 
                            door_access_width_ft=9, heat_utility='gas', surge_factor=1
                            ):
    #create a directory if it doesn't exists. Also creates parent directory if it does not exist
    Path(pathDir).mkdir(parents=True, exist_ok=True)

    with open(os.path.join(pathDir, 'optional_inputs.m'), 'w') as matlabfile:
        matlabfile.write('% Impedance Time Options \n')
        matlabfile.write('impedance_options.include_impedance.inspection = %s; \n'%str(inspection).lower())
        matlabfile.write('impedance_options.include_impedance.financing = %s; \n'%str(financing).lower())
        matlabfile.write('impedance_options.include_impedance.permitting = %s; \n'%str(permitting).lower())
        matlabfile.write('impedance_options.include_impedance.engineering = %s; \n'%str(engineering).lower())
        matlabfile.write('impedance_options.include_impedance.contractor = %s; \n'%str(contractor).lower())
        matlabfile.write('impedance_options.include_impedance.long_lead = %s; \n'%str(long_lead_time).lower())
        matlabfile.write('impedance_options.system_design_time.f = %s; \n'%str(design_time_f))
        matlabfile.write('impedance_options.system_design_time.r = %s; \n'%str(design_time_r))
        matlabfile.write('impedance_options.system_design_time.t = %s; \n'%str(design_time_t))
        matlabfile.write('impedance_options.system_design_time.w = %s; \n'%str(design_time_w))
        matlabfile.write('impedance_options.mitigation.is_essential_facility = %s; \n'%str(essential_facility).lower())
        matlabfile.write('impedance_options.mitigation.is_borp_equivalent = %s; \n'%str(borp_equivalent).lower())
        matlabfile.write('impedance_options.mitigation.is_engineer_on_retainer = %s; \n'%str(engineer_on_retainer).lower())
        matlabfile.write("impedance_options.mitigation.contractor_relationship = '%s'; \n"%str(contractor_relationship).lower())
        matlabfile.write('impedance_options.mitigation.contractor_retainer_time = %s; \n'%str(contractor_retainer_time))
        matlabfile.write("impedance_options.mitigation.funding_source = '%s'; \n"%str(funding_source).lower())
        matlabfile.write('impedance_options.mitigation.capital_available_ratio = %s; \n'%str(capital_available_ratio))
        matlabfile.write('impedance_options.impedance_beta = %s; \n'%str(impeding_factors_beta))
        matlabfile.write('impedance_options.impedance_truncation = %s; \n'%str(impedance_truncation))
        matlabfile.write('impedance_options.default_lead_time = %s; \n'%str(default_lead_time))
        matlabfile.write('impedance_options.scaffolding_lead_time = %s; \n'%str(scaffolding_lead_time))
        matlabfile.write('impedance_options.scaffolding_erect_time = %s; \n'%str(scaffolding_erect_time))
        matlabfile.write('\n')
        matlabfile.write('% Repair Schedule Options \n')
        matlabfile.write('repair_time_options.max_workers_per_sqft_story = %s; \n'%str(max_workers_per_sqft_story))
        matlabfile.write('repair_time_options.max_workers_per_sqft_story_temp_repair = %s; \n'%str(max_workers_per_sqft_story_temp_repair))
        matlabfile.write('repair_time_options.max_workers_per_sqft_building = %s; \n'%str(max_workers_per_sqft_building))
        matlabfile.write('repair_time_options.max_workers_building_min = %s; \n'%str(max_workers_building_min))
        matlabfile.write('repair_time_options.max_workers_building_max = %s; \n'%str(max_workers_building_max))
        matlabfile.write('\n')
        matlabfile.write('% Functionality Assessment Options \n')
        matlabfile.write('functionality_options.red_tag_clear_time = %s; \n'%str(red_tag_clear_time))
        matlabfile.write('functionality_options.red_tag_clear_beta = %s; \n'%str(red_tag_clear_beta))
        matlabfile.write('functionality_options.door_racking_repair_day = %s; \n'%str(door_racking_repair_day))
        matlabfile.write('functionality_options.egress_threshold = %s; \n'%str(egress_threshold))
        matlabfile.write('functionality_options.egress_threshold_wo_fs = %s; \n'%str(egress_threshold_wo_fs))
        matlabfile.write('functionality_options.fire_watch = %s; \n'%str(fire_watch).lower())
        matlabfile.write('functionality_options.min_egress_paths = %s; \n'%str(min_egress_paths))
        matlabfile.write('functionality_options.exterior_safety_threshold = %s; \n'%str(exterior_safety_threshold))
        matlabfile.write('functionality_options.interior_safety_threshold = %s; \n'%str(interior_safety_threshold))
        matlabfile.write('functionality_options.door_access_width_ft = %s; \n'%str(door_access_width_ft))
        matlabfile.write("functionality_options.heat_utility = '%s'; \n"%str(heat_utility).lower())
        matlabfile.write('\n')
        matlabfile.write('% Regional Impact \n')
        matlabfile.write('regional_impact.surge_factor = %s; \n'%str(surge_factor))
        


def create_optional_inputs_updated(
    pathDir, inspection=True, financing=True, permitting=True, engineering=True, contractor=True,
    long_lead_time=False, design_time_f=0.04, design_time_r=200, design_time_t=1.3, design_time_w=8,
    eng_design_min_days=14, eng_design_max_days=365, 
    essential_facility=False, borp_equivalent=False, engineer_on_retainer=False, 
    contractor_relationship='good', contractor_retainer_time=3, funding_source='private', 
    capital_available_ratio=0.1, impeding_factors_beta=0.6, impedance_truncation=2, 
    default_lead_time=182, include_surge=1, is_dense_urban_area=1, site_pga=1, pga_de=1,
    scaffolding_lead_time=5, scaffolding_erect_time=2,
    door_racking_repair_day=3, flooding_cleanup_day=5, flooding_repair_day=90,
    max_workers_per_sqft_story=0.001, max_workers_per_sqft_story_temp_repair=0.005,
    max_workers_per_sqft_building = 0.00025, max_workers_building_min=20, max_workers_building_max=260, 
    allow_tmp_repairs=True, allow_shoring=True,
    calculate_red_tag=True, red_tag_clear_time=7, red_tag_clear_beta=0.6, 
    include_local_stability_impact=True, flooding_impact=True, egress_threshold=0.5,fire_watch=True, 
    local_fire_damage_threshold=0.25, min_egress_paths=2, exterior_safety_threshold=0.1, interior_safety_threshold=0.25, 
    door_access_width_ft=9, heat_utility='gas', water_pressure_max_story=1, electrical=False, 
    water_potable=False, water_sanitary=False, hvac_ventilation=False, hvac_heating=False,
    hvac_cooling=False, hvac_exhaust=False
):
    #create a directory if it doesn't exists. Also creates parent directory if it does not exist
    Path(pathDir).mkdir(parents=True, exist_ok=True)

    with open(os.path.join(pathDir, 'optional_inputs.m'), 'w') as matlabfile:
        matlabfile.write('% Impedance Time Options \n')
        matlabfile.write('impedance_options.include_impedance.inspection = %s; \n'%str(inspection).lower())
        matlabfile.write('impedance_options.include_impedance.financing = %s; \n'%str(financing).lower())
        matlabfile.write('impedance_options.include_impedance.permitting = %s; \n'%str(permitting).lower())
        matlabfile.write('impedance_options.include_impedance.engineering = %s; \n'%str(engineering).lower())
        matlabfile.write('impedance_options.include_impedance.contractor = %s; \n'%str(contractor).lower())
        matlabfile.write('impedance_options.include_impedance.long_lead = %s; \n'%str(long_lead_time).lower())
        matlabfile.write('impedance_options.system_design_time.f = %s; \n'%str(design_time_f))
        matlabfile.write('impedance_options.system_design_time.r = %s; \n'%str(design_time_r))
        matlabfile.write('impedance_options.system_design_time.t = %s; \n'%str(design_time_t))
        matlabfile.write('impedance_options.system_design_time.w = %s; \n'%str(design_time_w))
        matlabfile.write('impedance_options.eng_design_min_days = %s; \n'%str(eng_design_min_days))
        matlabfile.write('impedance_options.eng_design_max_days = %s; \n'%str(eng_design_max_days))
        matlabfile.write('impedance_options.mitigation.is_essential_facility = %s; \n'%str(essential_facility).lower())
        matlabfile.write('impedance_options.mitigation.is_borp_equivalent = %s; \n'%str(borp_equivalent).lower())
        matlabfile.write('impedance_options.mitigation.is_engineer_on_retainer = %s; \n'%str(engineer_on_retainer).lower())
        matlabfile.write("impedance_options.mitigation.contractor_relationship = '%s'; \n"%str(contractor_relationship).lower())
        matlabfile.write('impedance_options.mitigation.contractor_retainer_time = %s; \n'%str(contractor_retainer_time))
        matlabfile.write("impedance_options.mitigation.funding_source = '%s'; \n"%str(funding_source).lower())
        matlabfile.write('impedance_options.mitigation.capital_available_ratio = %s; \n'%str(capital_available_ratio))
        matlabfile.write('impedance_options.impedance_beta = %s; \n'%str(impeding_factors_beta))
        matlabfile.write('impedance_options.impedance_truncation = %s; \n'%str(impedance_truncation))
        matlabfile.write('impedance_options.default_lead_time = %s; \n'%str(default_lead_time))
        matlabfile.write('impedance_options.demand_surge.include_surge = %s; \n'%str(include_surge))
        matlabfile.write('impedance_options.demand_surge.is_dense_urban_area = %s; \n'%str(is_dense_urban_area))
        matlabfile.write('impedance_options.demand_surge.site_pga = %s; \n'%str(site_pga))
        matlabfile.write('impedance_options.demand_surge.pga_de = %s; \n'%str(pga_de))
        matlabfile.write('impedance_options.scaffolding_lead_time = %s; \n'%str(scaffolding_lead_time))
        matlabfile.write('impedance_options.scaffolding_erect_time = %s; \n'%str(scaffolding_erect_time))
        matlabfile.write('impedance_options.door_racking_repair_day = %s; \n'%str(door_racking_repair_day))
        matlabfile.write('impedance_options.flooding_cleanup_day = %s; \n'%str(flooding_cleanup_day))
        matlabfile.write('impedance_options.flooding_repair_day = %s; \n'%str(flooding_repair_day))
        matlabfile.write('\n')
        matlabfile.write('% Repair Schedule Options \n')
        matlabfile.write('repair_time_options.max_workers_per_sqft_story = %s; \n'%str(max_workers_per_sqft_story))
        matlabfile.write('repair_time_options.max_workers_per_sqft_story_temp_repair = %s; \n'%str(max_workers_per_sqft_story_temp_repair))
        matlabfile.write('repair_time_options.max_workers_per_sqft_building = %s; \n'%str(max_workers_per_sqft_building))
        matlabfile.write('repair_time_options.max_workers_building_min = %s; \n'%str(max_workers_building_min))
        matlabfile.write('repair_time_options.max_workers_building_max = %s; \n'%str(max_workers_building_max))
        matlabfile.write('repair_time_options.allow_tmp_repairs = %s; \n'%str(allow_tmp_repairs).lower())
        matlabfile.write('repair_time_options.allow_shoring = %s; \n'%str(allow_shoring).lower())
        matlabfile.write('\n')
        matlabfile.write('% Functionality and Habitability Assessment Options \n')
        matlabfile.write('functionality_options.calculate_red_tag = %s; \n'%str(calculate_red_tag).lower())
        matlabfile.write('functionality_options.red_tag_clear_time = %s; \n'%str(red_tag_clear_time))
        matlabfile.write('functionality_options.red_tag_clear_beta = %s; \n'%str(red_tag_clear_beta))
        matlabfile.write('functionality_options.include_local_stability_impact = %s; \n'%str(include_local_stability_impact).lower())
        matlabfile.write('functionality_options.include_flooding_impact = %s; \n'%str(flooding_impact).lower())
        matlabfile.write('functionality_options.egress_threshold = %s; \n'%str(egress_threshold))
        matlabfile.write('functionality_options.fire_watch = %s; \n'%str(fire_watch).lower())
        matlabfile.write('functionality_options.local_fire_damage_threshold = %s; \n'%str(local_fire_damage_threshold))
        matlabfile.write('functionality_options.min_egress_paths = %s; \n'%str(min_egress_paths))
        matlabfile.write('functionality_options.exterior_safety_threshold = %s; \n'%str(exterior_safety_threshold))
        matlabfile.write('functionality_options.interior_safety_threshold = %s; \n'%str(interior_safety_threshold))
        matlabfile.write('functionality_options.door_access_width_ft = %s; \n'%str(door_access_width_ft))
        matlabfile.write("functionality_options.heat_utility = '%s'; \n"%str(heat_utility).lower())
        matlabfile.write('functionality_options.water_pressure_max_story = %s; \n'%str(water_pressure_max_story))
        matlabfile.write('functionality_options.habitability_requirements.electrical = %s; \n'%str(electrical).lower())
        matlabfile.write('functionality_options.habitability_requirements.water_potable = %s; \n'%str(water_potable).lower())
        matlabfile.write('functionality_options.habitability_requirements.water_sanitary = %s; \n'%str(water_sanitary).lower())
        matlabfile.write('functionality_options.habitability_requirements.hvac_ventilation = %s; \n'%str(hvac_ventilation).lower())
        matlabfile.write('functionality_options.habitability_requirements.hvac_heating = %s; \n'%str(hvac_heating).lower())
        matlabfile.write('functionality_options.habitability_requirements.hvac_cooling = %s; \n'%str(hvac_cooling).lower())
        matlabfile.write('functionality_options.habitability_requirements.hvac_exhaust = %s; \n'%str(hvac_exhaust).lower())

        


if __name__ == '__main__':
    baselineID = 's4_96x48'
    ID = 's4_96x48_High_Stucco_GWB'
    baseDirectory = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/SurrogateModeling/DGP/woodSDA'
    pathDir = os.path.join(baseDirectory, *['BuildingModels', ID, 'LossAnalysis', 'ATC138Input'])
    create_optional_inputs(pathDir)