import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
from tqdm import tqdm


from genCo import getGenCos, plotResults, plotData, plotGenData
from utilsData import getISO, getHourlyLoad, getHourlyGen, \
    getFutureGeneratorData, getFutureLoadData, getFutureGenerationData 
from Market import Market


def getRA(iter, market, genCos):
    outageCount = 0
    for __ in range(iter):
        for hour in tqdm(range(dfHourlyLoadAdj.index.stop - dfHourlyLoadAdj.index.start)):
            hourlyLoad = dfHourlyLoadAdj.iloc[hour]['Total Load']
            hourlynegativeLoadSolar = dfHourlySolarAdj.iloc[hour]['tot_solar_mwh']
            hourlynegativeLoadWind = dfHourlyWindAdj.iloc[hour]['tot_wind_mwh']

            loads = [hourlyLoad, hourlynegativeLoadSolar, hourlynegativeLoadWind]
            outageCount += int(market.RA(genCos=genCos, load=loads, verbose=False))

    LOLE = outageCount * 10 / iter
    print(LOLE)
    if LOLE > 24:
        return False
    else:
        return True



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Run the Market Simulation and Calculate PfP.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--ISO', type=str, default='ISNE')
    parser.add_argument('--vre-mix', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--load-rate', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--markov-cons', type=int, default=1, help='Number of simulations to run.')
    parser.add_argument('--verbose', type=bool, default=False)

    args = parser.parse_args()

    # Get 2023 Data
    dfISO, numGenerators, totalCap, totalCSO = getISO(ISO=args.ISO)
    dfHourlyLoad = getHourlyLoad(ISO=args.ISO, verbose=args.verbose)
    dfHourlySolar, dfHourlyWind = getHourlyGen(ISO=args.ISO, verbose=args.verbose)

    # Build Future Data
    cap_rate = 1.00
    RA = False
    dfHourlyLoadAdj = getFutureLoadData(dfHourlyLoad, args.load_rate)
    while RA is False:
        print('capacity increase rate:', cap_rate)
        dfISOAdj, totalCSOAdj, totalCapAdj, adjRatios = getFutureGeneratorData(dfISO, totalCSO, cap_rate=cap_rate, vre_mix=args.vre_mix)
        dfHourlySolarAdj, dfHourlyWindAdj = getFutureGenerationData(dfHourlySolar, dfHourlyWind, adjRatios)

        # Get the Minimum Reserve Requirement for CSC
        capacities = list(dfISOAdj['Nameplate Capacity (MW)'].sort_values(ascending=False))
        MRR = capacities[0] + 0.5 * capacities[1]

        # Get the GenCos
        genCos =  getGenCos(numGenerators, totalCSOAdj, dfISOAdj)

        market = Market(MRR=MRR, totalCSO=totalCSOAdj)
        RA = getRA(args.markov_cons, market, genCos)
        if RA is False:
            cap_rate += 0.01
    
    




