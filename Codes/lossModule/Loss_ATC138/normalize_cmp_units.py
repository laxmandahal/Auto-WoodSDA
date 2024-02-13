import os
import pandas as pd


def to_fema_cmp_id(pelicun_id):
    pelicun_str = str(pelicun_id.split('-')[0]).replace('.', "")
    return pelicun_str[:5]+'.'+pelicun_str[5:]


def normalize_comp_units(
    pelicun_results_fp: str, 
    cmp_lib_fp: str
):
    df_dmg = pd.read_csv(os.path.join(pelicun_results_fp, 'DMG_sample.csv'), index_col=0)

    components_lib = pd.read_csv(os.path.join(cmp_lib_fp, 'static_tables', 'component_attributes.csv'))

    cols_to_modify = [word for word in df_dmg.columns if word[0] in ('A', 'B', 'C', 'D', 'E', 'F')]
    for cmp_name in cols_to_modify:
        df_dmg[cmp_name] = df_dmg[cmp_name] / components_lib[components_lib['fragility_id']==to_fema_cmp_id(cmp_name)]['unit_qty'].values
    
    df_dmg.to_csv(os.path.join(pelicun_results_fp, 'DMG_sample.csv'))


if __name__ == "__main__":
    REGIONAL_STRATEGY = 'EA-VaFi'
    ID = 's1_40x30_HWS_GWB_Heavy_Vs11'
    hazard_level = 4
    cwd = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy/woodSDPA'
    static_table_fp = os.path.join(cwd, 'Codes', 'lossModule', 'Loss_ATC138', 'PBEE-Recovery')

    for hazard_level in range(10, 14):
        print(hazard_level)
        pelicun_output_dir = os.path.join(cwd, *['Results', REGIONAL_STRATEGY, ID, 'LossAnalysis', 'PelicunOutput', f'IL_{hazard_level}'])
        normalize_comp_units(pelicun_output_dir, static_table_fp)

