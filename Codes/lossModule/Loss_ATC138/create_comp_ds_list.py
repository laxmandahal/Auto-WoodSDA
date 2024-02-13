import numpy as np 
import pandas as pd 
import os 
from pathlib import Path


def create_comp_ds_from_DMG(baseDir, ID, hazard_level):
    dmg = pd.read_csv(os.path.join(baseDir, *['BuildingModels', ID,
                                            'LossAnalysis', 'PelicunOutput', 
                                            f'IL_{hazard_level}',
                                            'DMG.csv']), 
                        header=[0, 1, 2], skipinitialspace=True, index_col=0)
    cols = dmg.columns
    uniq_cmp = dmg.columns._levels[0].unique()

    all_cmps = []
    all_pgs = []
    all_dss = []

    for i in range(len(cols)):
        all_cmps.append(cols[i][0])
        all_pgs.append(cols[i][1])
        all_dss.append(cols[i][2])

    comp_id = []
    ds_seq_id = []
    ds_sub_id = []

    for i in range(len(uniq_cmp)):
        cmp_type_str = uniq_cmp[i]
        idices_of_comp = [i for i, x in enumerate(all_cmps) if x == cmp_type_str]
        uniq_ds_for_cmp = np.unique(np.array(all_dss)[idices_of_comp])
        for j in range(len(uniq_ds_for_cmp)):
            comp_id.append(cmp_type_str)
            ds_seq_id.append(int(np.unique(np.array(all_dss)[idices_of_comp])[j].split('_')[0]))
            ds_sub_id.append(int(np.unique(np.array(all_dss)[idices_of_comp])[j].split('_')[1]))
    
    d = {
        'comp_id': comp_id,
        'ds_seq_id': ds_seq_id,
        'ds_sub_id': ds_sub_id
        }
    df = pd.DataFrame(d)
    df = df.set_index('comp_id')
    output_fp = os.path.join(baseDir, *['BuildingModels', ID, 'LossAnalysis',
                                        'ATC138Input', f'IL_{hazard_level}'])
    Path(output_fp).mkdir(parents=True, exist_ok=True)
    df.to_csv(os.path.join(output_fp, 'comp_ds_list.csv'))
    return df

if __name__ == '__main__':
    # baselineID = 's4_96x48'
    ID = 's4_96x48_High_Stucco_GWB'
    baseDirectory = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/SurrogateModeling/DGP/woodSDA'

    df = create_comp_ds_from_DMG(baseDirectory, ID)