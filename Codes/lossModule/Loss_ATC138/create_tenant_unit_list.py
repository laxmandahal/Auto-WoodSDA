import numpy as np 
import pandas as pd 
import os 
from pathlib import Path


def create_tenant_unit_list(outputDir, numStory, floorArea, perimeterArea, occupancyID=7):
    '''This functions generates and saves (in the specified output directory), the tenant_unit_list.csv.
    The csv file is one of the input files needed to run ATC-138 analysis code

    Args:
        outputDir (str): Directory where the .CSV file will be saved
        numStory (int): Number of stories of the building of interest
        floorArea (list): Floor plan area of each story of the building. Dim: numStory x 1
        perimeterArea (list): Perimeter area of each story of the building. Dim: numStory x1
                             Computed as: perimeter of the floor plan * story height
        occupancyID (int, optional): Occupancy ID at story level. Defaults to 7 (residential).

    Returns:
        DataFrame: returns DataFrame but most importantly saves it as the .CSV file.
    '''
    #create a directory if it doesn't exists. Also creates parent directory if it does not exist
    Path(outputDir).mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame({'id': np.arange(1, numStory+1),
                        'story': np.arange(1, numStory+1),
                        'area': floorArea,
                        'perim_area': perimeterArea,
                        'occupancy_id': [occupancyID] * numStory
                        })
    
    df = df.set_index('id')
    df.to_csv(os.path.join(outputDir, 'tenant_unit_list.csv'))
    return df

if __name__ == '__main__':
    baselineID = 's4_96x48'
    ID = 's4_96x48_High_Stucco_GWB'
    baseDirectory = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/SurrogateModeling/DGP/woodSDA'
    # outputDir = os.path.join(baseDirectory, *['BuildingInfo', baselineID, 'ComponentsList'])
    outputDir = os.path.join(baseDirectory, *['BuildingModels', ID, 'LossAnalysis', 'ATC138Input'])
    df = create_tenant_unit_list(outputDir, numStory=4, floorArea=[1222, 1222, 1222, 1222], perimeterArea=[111, 111, 111, 111])