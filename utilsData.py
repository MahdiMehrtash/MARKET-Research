import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Constants
VRE_MIX = {'low':0.3, 'medium':0.5, 'high':0.7}
LOAD_ADJ = {'current': 1.00, 'low':1.05, 'medium':1.1, 'high':1.15}

def getISO(ISO='ISNE'):
    df = pd.read_excel('data/november_generator2023.xlsx', skiprows=0, index_col=0)
    df = df[1:]
    df.columns = df.iloc[0]
    df = df[1:]
    dfISO = df.loc[df['Balancing Authority Code'] == ISO]

    numGenerators = len(dfISO.index)
    totalCap = sum(dfISO['Nameplate Capacity (MW)'].to_list())
    totalCSO = 28660.0 #MWs from ISO-NE website

    feulDict = {'BIT':'Coal', 'NG':'Gas', 'WAT':'Hydro', 'NUC':'Nuclear', \
                'DFO':'Oil', 'RFO':'Oil', 'JF':'Oil', 'KER':'Oil', \
                'MSW':'Waste', 'SUN':'Solar', 'WND':'Wind', 'WDS':'Wood'}
    fuels = dfISO['Energy Source Code'].map(feulDict)
    fuels = fuels.fillna('Other')
    dfISO.insert(3, 'Fuel Type', fuels)
    print('Total Capacity: ', totalCap, ', CSO: ', totalCSO, ', of CSO% : ', totalCSO/totalCap*100)
    return dfISO, numGenerators, totalCap, totalCSO

def getHourlyLoad(ISO='ISNE', verbose=False, path='data/HourlyDemand2023.csv'):
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
        dfHourlySolar = pd.read_excel('data/HourlySolar2023.xlsx', sheet_name='HourlyData')
        dfHourlySolar.fillna(0, inplace=True)
        dfHourlySolar.drop('year', axis=1, inplace=True)
        # Wind
        dfHourlyWind = pd.read_excel('data/HourlyWind2023.xlsx', sheet_name='HourlyData')
        dfHourlyWind.fillna(0, inplace=True)
        dfHourlyWind.drop('year', axis=1, inplace=True)
        # Others
        dfDailyLoad = pd.read_excel('data/DailyGen2023.xlsx', skiprows=0, index_col=None, sheet_name='DAYGENBYFUEL')
    else:
        raise NotImplementedError
    return dfHourlySolar, dfHourlyWind


def getFutureGeneratorData(dfISO, totalCSO, cap_rate=1.00, vre_mix='low'):
    dfISOAdj = dfISO.copy()
    initTotalCap = sum(dfISOAdj['Nameplate Capacity (MW)'].to_list())
    initTotalVRE = sum(dfISOAdj['Nameplate Capacity (MW)'].loc[dfISOAdj['Fuel Type'].isin(['Solar', 'Wind'])].to_list())
    initTotalnonVRE = initTotalCap - initTotalVRE
    
    # if cap_rate != 'current':
    vre_coef = VRE_MIX[vre_mix]

    futureTotalCap = initTotalCap * cap_rate
    futureTotalVRE = futureTotalCap * vre_coef
    futureTotalNonVRE = futureTotalCap - futureTotalVRE

    dfISOAdj['Nameplate Capacity (MW)'].loc[dfISOAdj['Fuel Type'].isin(['Solar', 'Wind'])] *= futureTotalVRE / initTotalVRE
    dfISOAdj['Nameplate Capacity (MW)'].loc[~dfISOAdj['Fuel Type'].isin(['Solar', 'Wind'])] *= futureTotalNonVRE / initTotalnonVRE

    futureTotalCSO = totalCSO * cap_rate
    ratios = (futureTotalVRE / initTotalVRE, futureTotalNonVRE / initTotalnonVRE)
        
    return dfISOAdj, futureTotalCSO, futureTotalCap, ratios

def getFutureLoadData(dfHourlyLoad, load_rate='low'):
    load_coef = LOAD_ADJ[load_rate]
    dfHourlyLoad['Total Load'] *= load_coef
    return dfHourlyLoad

def getFutureGenerationData(dfHourlySolar, dfHourlyWind, adjRatios):
    dfHourlySolarAdj = dfHourlySolar.copy()
    dfHourlyWindAdj = dfHourlyWind.copy()
    dfHourlySolarAdj['tot_solar_mwh'] *= adjRatios[0]
    dfHourlyWindAdj['tot_wind_mwh'] *= adjRatios[0]
    return dfHourlySolarAdj, dfHourlyWindAdj