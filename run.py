import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from genCo import getGenCos, Market, PFP, plotResults
from tqdm import tqdm

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

def getDailyLoad(ISO='ISNE'):
    if ISO == 'ISNE':
        dfDailyLoad = pd.read_excel('data/DailyGen2023-ISNE.xlsx', skiprows=0, index_col=None, sheet_name='DAYGENBYFUEL')
    else:
        raise NotImplementedError
    return dfDailyLoad


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
        
    



if __name__ == "__main__":
    dfISO, numGenerators, totalCap, totalCSO = getISO()
    dfDailyLoad = getDailyLoad()

    genCos = getGenCos(numGenerators, totalCSO, dfISO)

    print(dfDailyLoad)
    raise NotImplementedError('Adjust Production w.r.t. Load!!')



    # payments = []
    # for day in tqdm(range(dfDailyLoad.index.stop - dfDailyLoad.index.start)):
    #     dailyLoad = dfDailyLoad.iloc[day]
    #     for hours in range(24):
    #         load = dfDailyLoad.iloc[day]['TOTAL'] / 24 * (1.15) 
    #         payment = test(numGen=numGenerators, genCos=genCos, load=load, verbose=False)
    #         if payment is not None:
    #             payments.append(payment)
    #         else:
    #             print('Outage on day: ', day)
    #             break
    
    # payments = np.array(payments)
    # payments = payments.reshape(payments.shape[0], -1)
    # plotResults(payments, genCos, numGenerators)
