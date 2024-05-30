import pandas as pd 
import requests
import time 
import json



def get_design_intensity(
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
    # basedir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy'
    # df = pd.read_csv('data/Building_Permits_Processed.csv', 
    #                 header = 0, index_col = None,
    #                 parse_dates = True, infer_datetime_format=True)
    # the dataframe had white spaces at the beginning and end of column name. Stripping the white spaces. 
    # df.columns = df.columns.str.strip()

    start1 = time.time()
    # Input lat, lng, riskCategory and siteClass & create arrays where seismicity parameters will be stored
    ss = []
    s1 = []
    site_modified_pga = []
    sdc = []
    ts = []
    t0 = []
    period_range = []
    design_spectrum = []
    MCEr_spectrum = []
    lat_arr = []
    lng_arr = []
    # riskCategory = "II"
    # siteClass = "D"

    # lat_all = df.Latitude.values
    # lng_all = df.Longitude.values
    # counter = 0

    version_typ = asce_ver_mapping[asce_version]
    # for i in range(5000,10000):
    # lat = lat_all[i]
    # lng = lng_all[i]
    ## using asce 7-22 to get the spectrum
    # url = f"https://earthquake.usgs.gov/ws/designmaps/asce7-22.json?latitude={lat}&longitude={lng}&riskCategory={riskCategory}&siteClass={siteClass}&title=Example"
    url = f"https://earthquake.usgs.gov/ws/designmaps/asce7-{version_typ}.json?latitude={latitude}&longitude={longitude}&riskCategory={risk_category}&siteClass={site_class}&title=Example"
    
    results = json.loads(requests.get(url).text)
    ss.append(results['response']['data']['ss'])
    s1.append(results['response']['data']['s1'])
    site_modified_pga.append(results['response']['data']['pgam'])
    sdc.append(results['response']['data']['sdc'])
    ts.append(results['response']['data']['ts'])
    t0.append(results['response']['data']['t0'])
    period_range.append(results['response']['data']['multiPeriodDesignSpectrum']['periods'])
    design_spectrum.append(results['response']['data']['multiPeriodDesignSpectrum']['ordinates'])
    MCEr_spectrum.append(results['response']['data']['multiPeriodMCErSpectrum']['ordinates'])


    ## asce 7-16 doesnot output spectrum
    # url = f"https://earthquake.usgs.gov/ws/designmaps/asce7-16.json?latitude={lat}&longitude={lng}&riskCategory={riskCategory}&siteClass={siteClass}&title=Example"
    # # Extract results to json format
    # results = json.loads(requests.get(url).text)
    # # Convert json type to pandas dataframe & extract SS and S1 seismicity parameters
    # df_scraped = pd.json_normalize(results['response'])
    # ss.append(df_scraped['data.ss'][0])
    # s1.append(df_scraped['data.s1'][0])


    # lat_arr.append(lat)
    # lng_arr.append(lng)

    # if i % 100 == 0:
    #     end = time.time()
    #     print(i)
    end = time.time()
    df_spatial = pd.DataFrame({'Latitude':lat_arr, 
                                'Longitude':lng_arr, 
                                'Ss(g)':ss, 
                                'S1(g)':s1,
                                'PGAm': site_modified_pga, 
                                'SDC':sdc,
                                'ts':ts,
                                't0':t0,
                                'period_range':period_range,
                                'Design_spectrum':design_spectrum,
                                'MCEr_spectrum':MCEr_spectrum
                                })
    # df_spatial['Ss(g)'] = ss
    # df['S1(g)'] = s1
    # df_spatial.to_csv('Spatial_Sa_values_5000to10000_test.csv')
    print('Total Runtime is {} minutes.'.format((end - start1)/60))