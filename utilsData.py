import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Constants
VRE_MIX = {'low':0.3, 'medium':0.5, 'high':0.7}
LOAD_ADJ = {'low':0.95, 'medium':1.0, 'high':1.05}

# fuelDict = {'LFG': 'Gas', 'NG': 'Gas', 'DFO': 'Gas', 'KER': 'Gas',\
#             'WDS':'Waste', 'BIT':'Coal', 'MSW' : 'Waste', \
#             'JF':'Oil', 'RFO' : 'Oil',
#             'WAT':'Hydro', 'NUC':'Nuclear', 'WND':'Wind', 'SUN':'Solar',\
#             'OBG': 'Other', 'MWH': 'Other'}
fuelDict = {'LFG': 'Landfill Gas', 'NG': 'Gas', 'DFO': 'Oil', 'KER': 'Oil',\
            'WDS':'Refuse/Woods', 'BIT':'Coal', 'MSW' : 'Refuse/Woods', \
            'JF':'Oil', 'RFO' : 'Oil',
            'WAT':'Hydro', 'NUC':'Nuclear', 'WND':'Wind', 'SUN':'Solar',\
            'OBG': 'Gas-Other', 'MWH': 'ES'}

def getISO(ISO='ISNE'):
    if ISO != 'ISNE':
        raise NotImplementedError
    dfISO = pd.read_csv('data/CELT2023.csv')
    numGenerators = len(dfISO.index)
    totalCap = sum(dfISO['Nameplate Capacity (MW)'].to_list())
    totalCSO = 28660.0 #MWs from ISO-NE website

    print('Total Capacity: ', totalCap, 'Number of Generators: ', numGenerators)
    return dfISO, numGenerators, totalCap, totalCSO

def getHourlyLoad(ISO='ISNE', verbose=False, path='data/Demand&Generation/HourlyDemand2023.csv'):
    if ISO == 'ISNE':
        # url = 'https://www.iso-ne.com/transform/csv/hourlysystemdemand?start=20230101&end=20231231'
        dfHourlyLoad = pd.read_csv(path, skiprows=1)
        dfHourlyLoad.drop('H', axis=1, inplace=True)

        dfHourlyLoad = dfHourlyLoad.reset_index(drop=True)
        dfHourlyLoad['Total Load'] = pd.to_numeric(dfHourlyLoad['Total Load'], errors='coerce')
    else:
        raise NotImplementedError
    return dfHourlyLoad

def getHourlyGen(ISO='ISNE', verbose=False):
    if ISO == 'ISNE':
        # url = https://www.iso-ne.com/isoexpress/web/reports/operations/-/tree/daily-gen-fuel-type
        # Solar
        dfHourlySolar = pd.read_excel('data/Demand&Generation/HourlySolar2023.xlsx', sheet_name='HourlyData')
        dfHourlySolar.fillna(0, inplace=True)
        dfHourlySolar.drop('year', axis=1, inplace=True)
        # Wind
        dfHourlyWind = pd.read_excel('data/Demand&Generation/HourlyWind2023.xlsx', sheet_name='HourlyData')
        dfHourlyWind.fillna(0, inplace=True)
        dfHourlyWind.drop('year', axis=1, inplace=True)
    else:
        raise NotImplementedError
    return dfHourlySolar, dfHourlyWind


def getFutureGeneratorData(dfISO, cap_rate=1.00, vre_mix='low'):
    dfISOAdj = dfISO.copy()
    initTotalCap = sum(dfISOAdj['Nameplate Capacity (MW)'].to_list())
    initTotalVRE = sum(dfISOAdj['Nameplate Capacity (MW)'].loc[dfISOAdj['Fuel Type'].isin(['Solar', 'Wind', 'ES'])].to_list())
    initTotalnonVRE = initTotalCap - initTotalVRE

    if vre_mix == 'current':
        return dfISOAdj, initTotalCap, (1.0, 1.0)
    
    vre_coef = VRE_MIX[vre_mix]

    futureTotalCap = initTotalCap * cap_rate
    futureTotalVRE = futureTotalCap * vre_coef
    futureTotalNonVRE = futureTotalCap - futureTotalVRE

    dfISOAdj['Nameplate Capacity (MW)'].loc[dfISOAdj['Fuel Type'].isin(['Solar', 'Wind', 'ES'])] *= (futureTotalVRE / initTotalVRE)
    dfISOAdj['Nameplate Capacity (MW)'].loc[~dfISOAdj['Fuel Type'].isin(['Solar', 'Wind', 'ES'])] *= (futureTotalNonVRE / initTotalnonVRE)

    ratios = (futureTotalVRE / initTotalVRE, futureTotalNonVRE / initTotalnonVRE)
        
    return dfISOAdj, futureTotalCap, ratios


def getFutureGenerationData(dfHourlySolar, dfHourlyWind, adjRatios):
    dfHourlySolarAdj = dfHourlySolar.copy()
    dfHourlyWindAdj = dfHourlyWind.copy()
    dfHourlySolarAdj['tot_solar_mwh'] *= adjRatios[0]
    dfHourlyWindAdj['tot_wind_mwh'] *= adjRatios[0]
    return dfHourlySolarAdj, dfHourlyWindAdj