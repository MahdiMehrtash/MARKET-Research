import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
from tqdm import tqdm
from generationRA import getFutureLoad
import pdb


from genCo import getGenCos, plotResults, plotData, plotGenData
# from utilsData import getISO, getHourlyLoad, getHourlyGen, \
#     getFutureGeneratorData, getFutureLoadData, getFutureGenerationData 
from Market import Market, PFP

def getFutureData(ISO='ISNE', verbose=False, path='data/forecast/', load_rate='high', vre_mix='high'):
    if ISO == 'ISNE':
        dfHourlyLoad = pd.read_csv(path + 'load_rate_' + load_rate + '/dfHourlyDemand2030.csv')
        dfHourlyLoad = dfHourlyLoad.reset_index(drop=True)

        dfHourlySolar = pd.read_csv(path + 'load_rate_' + load_rate + '/vre_' + vre_mix + '/dfHourlySolar.csv')
        dfHourlySolar = dfHourlySolar.reset_index(drop=True)

        dfHourlyWind = pd.read_csv(path + 'load_rate_' + load_rate + '/vre_' + vre_mix + '/dfHourlyWind.csv')
        dfHourlyWind = dfHourlyWind.reset_index(drop=True)

        dfISO = pd.read_csv(path + 'load_rate_' + load_rate + '/vre_' + vre_mix + '/dfISO.csv')
        dfISO = dfISO.reset_index(drop=True)

        dfinfo = pd.read_csv(path + 'load_rate_' + load_rate + '/vre_' + vre_mix + '/infoDict.csv')
        dfinfo = dfinfo.reset_index(drop=True)
        info = [dfinfo['numGenerators'], dfinfo['totalCSO'], dfinfo['totalCap'], dfinfo['adjRatios']]
    else:
        raise NotImplementedError
    return dfHourlyLoad, dfHourlySolar, dfHourlyWind, dfISO, info

# @TODO: 1) Random renewable generation!

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Run the Market Simulation and Calculate PfP.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--ISO', type=str, default='ISNE')
    parser.add_argument('--load-rate', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--vre-mix', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--markov-cons', type=int, default=1, help='Number of simulations to run.')
    parser.add_argument('--sigma', type=float, default=0.1, help='Number of simulations to run.')
    parser.add_argument('--verbose', type=bool, default=False)

    args = parser.parse_args()

    # Get Future Load and Data
    dfHourlyLoad, dfHourlySolar, dfHourlyWind, dfISO, info = getFutureData(ISO=args.ISO, verbose=args.verbose, path='data/forecast/' , load_rate=args.load_rate)
    numGenerators, totalCSO, totalCap, adjRatios = info[0][0], info[1][0], info[2][0], info[3][0]

    # Get the Minimum Reserve Requirement for CSC
    capacities = list(dfISO['Nameplate Capacity (MW)'].sort_values(ascending=False))
    MRR = capacities[0] + 0.5 * capacities[1]
    
    # Get the GenCos
    genCos =  getGenCos(numGenerators, totalCSO, dfISO)
    # pdb.set_trace()
    # Run the Market Simulation
    payments = []
    market = Market(MRR=MRR, totalCSO=totalCSO)
    for __ in range(args.markov_cons):
        for hour in tqdm(range(dfHourlyLoad.index.stop - dfHourlyLoad.index.start)):
            hourlyLoad = dfHourlyLoad.iloc[hour]['Total Load']
            hourlynegativeLoadSolar = np.random.normal(dfHourlySolar.iloc[hour]['tot_solar_mwh'], args.sigma, 1)
            hourlynegativeLoadWind = np.random.normal(dfHourlyWind.iloc[hour]['tot_wind_mwh'], args.sigma, 1)

            loads = [hourlyLoad, hourlynegativeLoadSolar, hourlynegativeLoadWind]
            payment = market.run(numGen=numGenerators, genCos=genCos, load=loads, verbose=False)
            payment = np.concatenate([x if isinstance(x, np.ndarray) else [x] for x in payment])
            payments.append(payment)

            
    print('Average CSC: ', market.numberOfCSCs / args.markov_cons)
    
    payments = np.array(payments)
    print('Total Payments:', payments.sum())
    plotResults(payments, genCos, numGenerators, [args.load_rate, args.vre_mix], markov_cons=args.markov_cons)



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


