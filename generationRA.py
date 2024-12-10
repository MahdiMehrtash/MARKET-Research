import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
from tqdm import tqdm
import time


from genCo import getGenCos
from utilsData import getISO, getHourlyGen, \
    getFutureGeneratorData, getFutureGenerationData, \
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
    print('LOLE: ', LOLE)
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
    parser.add_argument('--esCharge', type=float, default=1.0, help='ESs charge level @ CSCs.')
    parser.add_argument('--EStotalCap', type=float, default=2000.0, help='2000MW of Batteries.')
    parser.add_argument('--LDtotalCap', type=float, default=500.0, help='500MW of Batteries.')
    parser.add_argument('--verbose', type=bool, default=False)

    args = parser.parse_args()

    # Get 2023 Gen Data
    dfISO, numGenerators, totalCap, __ = getISO(ISO=args.ISO)
    dfHourlySolar, dfHourlyWind = getHourlyGen(ISO=args.ISO, verbose=args.verbose)

    # Get 2030 Load
    dfHourlyLoadAdj = getFutureLoad(ISO=args.ISO, verbose=args.verbose, path='data/forecast/load_rate_' + args.load_rate + '/dfHourlyDemand2030.csv')
    # Build Future Data
    cap_rate = 1.00
    RA = False
    while RA is False:
        print('capacity increase rate:', cap_rate)
        dfISOAdj, totalCapAdj, adjRatios = getFutureGeneratorData(dfISO, cap_rate=cap_rate, vre_mix=args.vre_mix,
                                                                     EStotalCap=args.EStotalCap, LDtotalCap=args.LDtotalCap)
        
        dfHourlySolarAdj, dfHourlyWindAdj = getFutureGenerationData(dfHourlySolar, dfHourlyWind, adjRatios)

        print('Total Capacity: ', totalCapAdj)

        # Get the GenCos
        genCos =  getGenCos(dfISOAdj, esCharge=args.esCharge)
        
        market = Market(MRR=[0, 0], load=args.load_rate)
        RA, lole = getRA(args.markov_cons, market, genCos, dfHourlyLoadAdj, dfHourlySolarAdj, dfHourlyWindAdj)
        if RA is False:
            cap_rate += 0.025

    # Save to CSV
    datentime = datetime.now().strftime("%Y/%m/%d-%H:%M:%S")
    infoDict = {'time': datentime, 'numGenerators':numGenerators, 'totalCap':totalCapAdj, 'adjRatios':adjRatios, 'cap_rate':cap_rate, 'LOLE': lole}
    dfinfo = pd.DataFrame.from_dict(infoDict)
    
    dfHourlySolarAdj.to_csv('data/forecast/load_rate_' + args.load_rate + '/vre_' + args.vre_mix +'/dfHourlySolar.csv', index=False)
    dfHourlyWindAdj.to_csv('data/forecast/load_rate_' + args.load_rate + '/vre_' + args.vre_mix +'/dfHourlyWind.csv', index=False)
    dfISOAdj.to_csv('data/forecast/load_rate_' + args.load_rate + '/vre_' + args.vre_mix +'/dfISO.csv', index=False)
    dfinfo.to_csv('data/forecast/load_rate_' + args.load_rate + '/vre_' + args.vre_mix +'/infoDict.csv', index=False)

        
    




