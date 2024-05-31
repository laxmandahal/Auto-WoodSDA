import pandas as pd
import requests
import json



def get_ASCE_design_intensity(
    latitude:float,
    longitude:float,
    asce_version:int = 2016,
    risk_category:str = 'II',
    site_class:str = 'D'
):
    asce_ver_mapping = {
        2016: 16,
        2022: 22
    }
    version_typ = asce_ver_mapping[asce_version]

    url = f"https://earthquake.usgs.gov/ws/designmaps/asce7-{version_typ}.json?latitude={latitude}&longitude={longitude}&riskCategory={risk_category}&siteClass={site_class}&title=Example"
    
    results = json.loads(requests.get(url).text)
    ss = results['response']['data']['ss']
    s1 = results['response']['data']['s1']

    return ss, s1



def check_and_complete_inputs(
    input_df: pd.DataFrame
)->pd.DataFrame:
    '''
    This utility function takes in input dataframe of a particular building ID and outputs complete input df.
    If some inputs are missing, it is replaced with an arbitrary default values.
    

    Args:
        input_df (pd.DataFrame): input dataframe of a specific builiding ID

    Raises:
        ValueError: If `Layout Type` is not defined.  
        ValueError: If either Latitude/Longitude or design intensities (Ss, S1) is not defined.
        ValueError: If either Latitude/Longitude and design intensities (Ss, S1) is not defined.

    Returns:
        pd.DataFrame: Complete input dataframe 
    '''
    empty_columns = input_df.columns[input_df.isna().all()].tolist()

    if 'Layout Type' in empty_columns:
        raise ValueError('Missing Input: Please assign a corresponding layout type to the inputted building ID')
    if 'SiteID' in empty_columns:
        input_df['SiteID'] = 1
        print('Missing SiteID detected. Assigned 1 as the default site ID')
    if (('Latitude' in empty_columns) or ('Longitude' in empty_columns)) and (('Ss(g)' in empty_columns) or ('S1(g)' in empty_columns)):
        raise ValueError('Missing Input: Please specify either the geo-location or design intensities.')
    if 'Site Class' in empty_columns:
        input_df['Site Class'] = 'D'
        print('Missing Site Class detected. Assigned "D" as the default site class')
    if 'Risk Category' in empty_columns:
        input_df['Risk Category'] = 'II'
        print('Missing Risk Category detected. Assigned "II" as the default risk category')
    if 'R' in empty_columns:
        input_df['R'] = 6.5
        print('Missing response modification factor (R) detected. Assigned 6.5 as the default R value')
    if 'Cd' in empty_columns:
        input_df['Cd'] = 4.0
        print('Missing deflection amplification factor (Cd) detected. Assigned 4 as the default Cd value')
    if 'Ie' in empty_columns:
        input_df['Ie'] = 1.0
        print('Missing design importance factor (Ie) detected. Assigned 1.0 as the default Ie value')
    if 'Design Year' in empty_columns:
        input_df['Design Year'] = 2020
        print('Missing design year detected. Assigned 2020 as the default design year')
    
    if ('Ss(g)' in empty_columns) or ('S1(g)' in empty_columns):
        if (('Latitude' in empty_columns) or ('Longitude' in empty_columns)):
            raise ValueError('Missing Input: Please specify either the geo-location or design intensities.')

        print('Missing design intensities')
        if input_df['Design Year'].values[0] >= 2022:
            asce_version = 2022
        else:
            asce_version = 2016
        ss, s1 = get_ASCE_design_intensity(latitude=input_df['Latitude'].values[0],
                                      longitude=input_df['Longitude'].values[0],
                                      asce_version=asce_version,
                                      risk_category=input_df['Risk Category'].values[0],
                                      site_class=input_df['Site Class'].values[0])
        input_df['Ss(g)'] = ss
        input_df['S1(g)'] = s1
        print('Parsed design intensities from USGS/ASCE Hazard API')
    
    ## return the complete input df
    return input_df






   