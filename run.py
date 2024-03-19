import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
from tqdm import tqdm


from genCo import getGenCos, plotResults, plotData, plotGenData
from utilsData import getISO, getHourlyLoad, getHourlyGen, \
    getFutureGeneratorData, getFutureLoadData, getFutureGenerationData 
from Market import Market, PFP

# @TODO: 1) Fix MRR - Done
#        2) Convex conmbination
#        3) Fix Balancing Ratio - Done

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Run the Market Simulation and Calculate PfP.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--ISO', type=str, default='ISNE')
    parser.add_argument('--load-rate', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--vre-mix', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--markov-cons', type=int, default=1, help='Number of simulations to run.')
    parser.add_argument('--verbose', type=bool, default=False)

    args = parser.parse_args()

    # Get 2023 Data
    dfISO, numGenerators, totalCap, totalCSO = getISO(ISO=args.ISO)
    dfHourlyLoad = getHourlyLoad(ISO=args.ISO, verbose=args.verbose)
    dfHourlySolar, dfHourlyWind = getHourlyGen(ISO=args.ISO, verbose=args.verbose)

    # Build Future Data
    dfISOAdj, totalCSOAdj, totalCapAdj, adjRatios = getFutureGeneratorData(dfISO, totalCSO, load_rate=args.load_rate, vre_mix=args.vre_mix)
    dfHourlyLoadAdj = getFutureLoadData(dfHourlyLoad, args.load_rate)
    dfHourlySolarAdj, dfHourlyWindAdj = getFutureGenerationData(dfHourlySolar, dfHourlyWind, adjRatios)

    # Get the Minimum Reserve Requirement for CSC
    capacities = list(dfISOAdj['Nameplate Capacity (MW)'].sort_values(ascending=False))
    MRR = capacities[0] + 0.5 * capacities[1]
    
    # Get the GenCos
    genCos =  getGenCos(numGenerators, totalCSOAdj, dfISOAdj)

    # Run the Market Simulation
    payments = []
    market = Market(MRR=MRR, totalCSO=totalCSOAdj)
    for __ in range(args.markov_cons):
        for hour in tqdm(range(dfHourlyLoadAdj.index.stop - dfHourlyLoadAdj.index.start)):
            hourlyLoad = dfHourlyLoadAdj.iloc[hour]['Total Load']
            hourlynegativeLoadSolar = dfHourlySolarAdj.iloc[hour]['tot_solar_mwh']
            hourlynegativeLoadWind = dfHourlyWindAdj.iloc[hour]['tot_wind_mwh']

            loads = [hourlyLoad, hourlynegativeLoadSolar, hourlynegativeLoadWind]
            payment = market.run(numGen=numGenerators, genCos=genCos, load=loads, verbose=False)
            payments.append(payment)
    print('Average CSC: ', market.numberOfCSCs / args.markov_cons)

    
    payments = np.array(payments)
    plotResults(payments, genCos, numGenerators)



# if __name__ == "__main__":
#     load_rate = 'low'
#     vre_mix = 'low'
#     verbose=False

#     dfISO, numGenerators, totalCap, totalCSO = getISO(ISO='ISNE')
#     dfHourlyLoad = getHourlyLoad(ISO='ISNE', verbose=False)
#     dfHourlySolar, dfHourlyWind = getHourlyGen(ISO='ISNE', verbose=False)

#     if verbose:
#         plt.figure(figsize=(15, 5))
#         plt.subplot(1, 2, 1)
#         plotData(dfHourlyLoad, dfHourlySolar, dfHourlyWind, totalCap, totalCSO, yearPlot='2023')
#         plt.ylim(0, 45000)


#     dfISOAdj, totalCSOAdj, totalCapAdj, adjRatios = getFutureGeneratorData(dfISO, totalCSO, load_rate=load_rate, vre_mix=vre_mix)
#     dfHourlyLoadAdj = getFutureLoadData(dfHourlyLoad)
#     dfHourlySolarAdj, dfHourlyWindAdj = getFutureGenerationData(dfHourlySolar, dfHourlyWind, adjRatios)

#     if verbose:
#         plt.subplot(1, 2, 2)
#         plotData(dfHourlyLoadAdj, dfHourlySolarAdj, dfHourlyWindAdj, totalCapAdj, totalCSOAdj, yearPlot='Future')
#         plt.ylim(0, 45000)
#         plt.show()


#     genCos =  getGenCos(numGenerators, totalCSO, dfISO)
#     if True:
#         plt.subplot(1, 2, 1)
#         plotGenData(genCos, CSO=True)

#     genCos =  getGenCos(numGenerators, totalCSOAdj, dfISOAdj)
#     if True:
#         plt.subplot(1, 2, 2)
#         plotGenData(genCos, CSO=True)
#         plt.show()


