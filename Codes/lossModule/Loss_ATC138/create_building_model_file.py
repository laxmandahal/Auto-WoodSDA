import numpy as np 
import pandas as pd 
import os 
import json
from pathlib import Path

def create_building_model(baseDir, 
                          ID, num_story, total_area, area_per_story, height_per_story, edge_lengths, 
                            struct_bay_area_per_story, stairs_per_story, 
                            building_value = 54000000, 
                            num_entry_doors=2, 
                            num_elevators=1, 
                            peak_occupancy_rate = 3.1/1000):
    
    
    building_data = {
                    "building_value": building_value,
                    "num_stories": num_story,
                    "total_area_sf": total_area,
                    "area_per_story_sf": area_per_story,
                    "ht_per_story_ft": height_per_story, 
                    "edge_lengths": edge_lengths, 
                    "struct_bay_area_per_story": struct_bay_area_per_story, 
                    "num_entry_doors": [1 if num_story ==1 else num_entry_doors][0], 
                    "num_elevators": num_elevators, 
                    "stairs_per_story": stairs_per_story, 
                    "occupants_per_story": list(peak_occupancy_rate * np.array(area_per_story))
                    }
    
    # output_fp = os.path.join(baseDir, *['BuildingModels', regional_strategy, ID, 'LossAnalysis', 'ATC138Input'])
    output_fp = os.path.join(baseDir, *['Results', ID, 'LossAnalysis', 'ATC138Input'])
    Path(output_fp).mkdir(parents=True, exist_ok=True)
    ## Note: Looks like JSON doesn't recognize Numpy data types. Have to convert to python int before serializing the object
    ## workaround solution:
    with open(os.path.join(output_fp, 'building_model.json'), 'w') as f:
        json.dump(building_data, f, indent=4, sort_keys=False)#,
                #   separators=(', ', ': '), ensure_ascii=False)
    

if __name__ == '__main__':
    # baselineID = 's4_96x48'
    ID = 's4_96x48_High_Stucco_GWB'
    baseDirectory = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/SurrogateModeling/DGP/woodSDA'

    df = create_building_model(baseDirectory, ID, num_story=4, total_area=96*48*4, area_per_story=[96*48]*4, 
                                height_per_story=[10]*4, edge_lengths=[[100,100], [100,100], [100,100], [100,100]], 
                                struct_bay_area_per_story=[100]*4, stairs_per_story=[2]*4)