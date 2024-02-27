import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from tqdm import tqdm


from genCo import getGenCos, plotResults, plotData
from Market import Market, PFP

# Constants
VRE_MIX = {'low':0.3, 'medium':0.5, 'high':0.7}
LOAD_ADJ = {'low':1.05, 'medium':1.1, 'high':1.15}
RESERVE = 0.15
MRR = 1600 #MWs

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

def getHourlyLoad(ISO='ISNE', verbose=False):
    if ISO == 'ISNE':
        # url = 'https://www.iso-ne.com/transform/csv/hourlysystemdemand?start=20230101&end=20231231'
        dfHourlyLoad = pd.read_csv('data/HourlyDemand2023.csv', skiprows=1)
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


def test(numGen=100, genCos=[], load=-1, verbose=False):
    market = Market(numGen)
    currentCapSum = market.getCurrentCap(genCos)
    obligationsSum = market.getObligations(genCos)
    if verbose:
        print('Total Available Capacity: ', market.totalAvailableCap, ' ,Load of the Day: ', load ,\
                ', obligationsSum: ', obligationsSum)
    # print(market.totalAvailableCap - load - MRR)
    # print(market.totalAvailableCap, load, totalCSO ,MRR )
    # print(currentCapSum)
    # raise
    if market.totalAvailableCap - load < MRR:
        print('Total Available Capacity: ', market.totalAvailableCap, ' ,Load of the Day: ', load ,\
                ', obligationsSum: ', obligationsSum)
        genCos = market.sortGenCos(genCos)
        for gen in genCos:
            if not gen.deficit:
                tmp = np.minimum(obligationsSum - currentCapSum, gen.availableCap - gen.participateCap)
                currentCapSum +=  tmp
                gen.participateCap += tmp
            if np.allclose(currentCapSum, obligationsSum):
                break
        if not np.allclose(currentCapSum, obligationsSum):
            print('Outage!')
            return None
        pfp = PFP(genCos)
        payments = pfp.calcPFP()
        payments = np.array(payments)
        return payments
    else:
        return np.zeros(numGen)
        
def getFutureGeneratorData(dfISO, totalCSO, load_rate='low', vre_mix='low'):
    load_coef = LOAD_ADJ[load_rate]
    vre_coef = VRE_MIX[vre_mix]

    initTotalCap = sum(dfISO['Nameplate Capacity (MW)'].to_list())
    futureTotalCap = initTotalCap * load_coef
    initTotalVRE = sum(dfISO['Nameplate Capacity (MW)'].loc[dfISO['Fuel Type'].isin(['Solar', 'Wind'])].to_list())
    futureTotalVRE = futureTotalCap * vre_coef
    futureTotalNonVRE = futureTotalCap - futureTotalVRE

    dfISO['Nameplate Capacity (MW)'].loc[dfISO['Fuel Type'].isin(['Solar', 'Wind'])] *= futureTotalVRE / initTotalVRE
    dfISO['Nameplate Capacity (MW)'].loc[~dfISO['Fuel Type'].isin(['Solar', 'Wind'])] *= futureTotalNonVRE / (initTotalCap - initTotalVRE)

    futureTotalCSO = totalCSO * load_coef
    return dfISO, futureTotalCSO, futureTotalCap, (futureTotalVRE / initTotalVRE, futureTotalNonVRE / (initTotalCap - initTotalVRE))

def getFutureLoadData(dfHourlyLoad):
    load_coef = LOAD_ADJ[load_rate]
    dfHourlyLoad['Total Load'] *= load_coef
    return dfHourlyLoad

def getFutureGenerationData(dfHourlySolar, dfHourlyWind, adjRatios):
    dfHourlySolar['tot_solar_mwh'] *= adjRatios[0]
    dfHourlyWind['tot_wind_mwh'] *= adjRatios[0]
    return dfHourlySolar, dfHourlyWind


if __name__ == "__main__":
    load_rate = 'low'
    vre_mix = 'low'
    verbose=True

    dfISO, numGenerators, totalCap, totalCSO = getISO(ISO='ISNE')
    dfHourlyLoad = getHourlyLoad(ISO='ISNE', verbose=False)
    dfHourlySolar, dfHourlyWind = getHourlyGen(ISO='ISNE', verbose=False)

    if verbose:
        plt.figure(figsize=(15, 5))
        plt.subplot(1, 2, 1)
        plotData(dfHourlyLoad, dfHourlySolar, dfHourlyWind, totalCap, totalCSO, yearPlot='2023')
        plt.ylim(0, 45000)


    dfISOAdj, totalCSOAdj, totalCapAdj, adjRatios = getFutureGeneratorData(dfISO, totalCSO, load_rate=load_rate, vre_mix=vre_mix)
    dfHourlyLoadAdj = getFutureLoadData(dfHourlyLoad)
    dfHourlySolarAdj, dfHourlyWindAdj = getFutureGenerationData(dfHourlySolar, dfHourlyWind, adjRatios)

    if verbose:
        plt.subplot(1, 2, 2)
        plotData(dfHourlyLoadAdj, dfHourlySolarAdj, dfHourlyWindAdj, totalCapAdj, totalCSOAdj, yearPlot='Future')
        plt.ylim(0, 45000)
        plt.show()


    # genCos =  getGenCos(numGenerators, totalCSOAdj, dfISOAdj)
    # payments = []
    # for hour in tqdm(range(dfHourlyLoadAdj.index.stop - dfHourlyLoadAdj.index.start)):
    #     if hour > 100:
    #         break
    #     hourlyLoad = dfHourlyLoadAdj.iloc[hour]['Total Load']
    #     payment = test(numGen=numGenerators, genCos=genCos, load=hourlyLoad, verbose=False)
    #     payments.append(payment)

    
    # payments = np.array(payments)
    # payments = payments.reshape(payments.shape[0], -1)
    # print(payments)
    # plotResults(payments, genCos, numGenerators)
