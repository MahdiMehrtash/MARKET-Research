import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
from tqdm import tqdm


from genCo import getGenCos, plotResults, plotData, plotGenData
from utilsData import getISO, getHourlyGen, \
    getFutureGeneratorData, getFutureLoadData, getFutureGenerationData, \
    getHourlyLoad
from Market import Market


def getRA(iter, market, genCos, dfLoad, dfSolar, dfWind):
    outageCount = 0
    for __ in range(iter):
        for hour in tqdm(range(dfLoad.index.stop - dfLoad.index.start)):
            hourlyLoad = dfLoad.iloc[hour]['Total Load']
            hourlynegativeLoadSolar = dfSolar.iloc[hour]['tot_solar_mwh']
            hourlynegativeLoadWind = dfWind.iloc[hour]['tot_wind_mwh']

            loads = [hourlyLoad, hourlynegativeLoadSolar, hourlynegativeLoadWind]
            outageCount += int(market.RA(genCos=genCos, load=loads, verbose=False))

    LOLE = outageCount * 10 / iter
    print(LOLE)
    if LOLE >= 24:
        return False, LOLE
    else:
        return True, LOLE
    

def getFutureLoad(ISO='ISNE', verbose=False, path='data/forecast/HourlyDemand2030-load_ratehigh.csv'):
    if ISO == 'ISNE':
        dfHourlyLoad = pd.read_csv(path)

        dfHourlyLoad = dfHourlyLoad.reset_index(drop=True)
        dfHourlyLoad['Total Load'] = pd.to_numeric(dfHourlyLoad['Total Load'], errors='coerce')
    else:
        raise NotImplementedError
    return dfHourlyLoad



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Run the Market Simulation and Calculate PfP.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--ISO', type=str, default='ISNE')
    parser.add_argument('--vre-mix', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--load-rate', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--markov-cons', type=int, default=1, help='Number of simulations to run.')
    parser.add_argument('--verbose', type=bool, default=False)

    args = parser.parse_args()

    # Get 2023 Gen Data
    dfISO, numGenerators, totalCap, totalCSO = getISO(ISO=args.ISO)
    dfHourlySolar, dfHourlyWind = getHourlyGen(ISO=args.ISO, verbose=args.verbose)

    if True:
        # Get 2030 Load
        dfHourlyLoadAdj = getFutureLoad(ISO=args.ISO, verbose=args.verbose, path='data/forecast/load_rate_' + args.load_rate + '/dfHourlyDemand2030.csv')
        # Build Future Data
        cap_rate = 1.00
        RA = False
        while RA is False:
            print('capacity increase rate:', cap_rate)
            dfISOAdj, totalCSOAdj, totalCapAdj, adjRatios = getFutureGeneratorData(dfISO, totalCSO, cap_rate=cap_rate, vre_mix=args.vre_mix)
            dfHourlySolarAdj, dfHourlyWindAdj = getFutureGenerationData(dfHourlySolar, dfHourlyWind, adjRatios)
            
            # Get the GenCos
            genCos =  getGenCos(numGenerators, totalCSOAdj, dfISOAdj)

            market = Market(MRR=[], totalCSO=totalCSOAdj)
            RA, __ = getRA(args.markov_cons, market, genCos, dfHourlyLoadAdj, dfHourlySolarAdj, dfHourlyWindAdj)
            if RA is False:
                cap_rate += 0.05

        # Save to CSV
        infoDict = {'numGenerators':numGenerators, 'totalCSO':totalCSOAdj, 'totalCap':totalCapAdj, 'adjRatios':adjRatios}
        dfinfo = pd.DataFrame.from_dict(infoDict)
        
        dfHourlySolarAdj.to_csv('data/forecast/load_rate_' + args.load_rate + '/vre_' + args.vre_mix +'/dfHourlySolar.csv', index=False)
        dfHourlyWindAdj.to_csv('data/forecast/load_rate_' + args.load_rate + '/vre_' + args.vre_mix +'/dfHourlyWind.csv', index=False)
        dfISOAdj.to_csv('data/forecast/load_rate_' + args.load_rate + '/vre_' + args.vre_mix +'/dfISO.csv', index=False)
        dfinfo.to_csv('data/forecast/load_rate_' + args.load_rate + '/vre_' + args.vre_mix +'/infoDict.csv', index=False)

    else:
        dfHoulyLoad = getHourlyLoad(ISO=args.ISO, verbose=args.verbose)
        # Get the GenCos
        genCos =  getGenCos(numGenerators, totalCSO, dfISO)

        market = Market(MRR=[], totalCSO=totalCSO)
        RA, LOLE = getRA(args.markov_cons, market, genCos, dfHoulyLoad, dfHourlySolar, dfHourlyWind)
        
    




