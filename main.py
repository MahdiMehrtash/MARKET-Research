import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
from tqdm import tqdm
import pdb

from genCo import getGenCos, plotResults
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
        info = [dfinfo['numGenerators'], dfinfo['totalCap'], dfinfo['adjRatios'], dfinfo['cap_rate'], dfinfo['LOLE']]
    else:
        raise NotImplementedError
    return dfHourlyLoad, dfHourlySolar, dfHourlyWind, dfISO, info


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Run the Market Simulation and Calculate PfP.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--ISO', type=str, default='ISNE')
    parser.add_argument('--load-rate', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--vre-mix', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--markov-cons', type=int, default=1, help='Number of simulations to run.')
    parser.add_argument('--sigma', type=float, default=0.1, help='VRE Variance.')
    parser.add_argument('--vreOut', action='store_true', help='VRE take no CSO.')
    parser.add_argument('--esCharge', type=float, default=1.0, help='ESs charge level @ CSCs.')
    parser.add_argument('--verbose', type=bool, default=False)

    args = parser.parse_args()

    # Get Future Load and Data
    dfHourlyLoad, dfHourlySolar, dfHourlyWind, dfISO, info = getFutureData(ISO=args.ISO, verbose=args.verbose, path='data/forecast/' , 
                                                                           load_rate=args.load_rate, vre_mix=args.vre_mix)
    
    __, totalCap, adjRatios, cap_rate, LOLE = info[0][0], info[1][0], info[2], info[3][0], info[4][0]
    numGenerators = len(dfISO.index)
    print('Total Capacity: ', totalCap, 'Number of Generators: ', numGenerators, 'LOLE: ', LOLE)

    # Get the Minimum Reserve Requirement for CSC
    capacities = list(dfISO['Nameplate Capacity (MW)'].sort_values(ascending=False))
    MRR = capacities[0] + 0.5 * capacities[1]
    
    # Get the GenCos and CSO
    genCos =  getGenCos(numGenerators, dfISO, esCharge=args.esCharge)

    # Run the Market Simulation
    payments = []
    market = Market(MRR=MRR)
    last_month = None
    totalCSO = -1
    for __ in range(args.markov_cons):
        for hour in tqdm(range(dfHourlyLoad.index.stop - dfHourlyLoad.index.start)):
            hourlyLoad = dfHourlyLoad.iloc[hour]['Total Load']
            hourlynegativeLoadSolar = np.random.normal(dfHourlySolar.iloc[hour]['tot_solar_mwh'], args.sigma, 1)
            hourlynegativeLoadWind = np.random.normal(dfHourlyWind.iloc[hour]['tot_wind_mwh'], args.sigma, 1)

            date = pd.to_datetime(dfHourlyLoad.iloc[hour]['Date'])
            hourEnding = dfHourlyLoad.iloc[hour]['Hour Ending']
            month = date.strftime('%B')
            if last_month != month:
                for gen in genCos: gen.updateCSO(dfISO, cap_rate, adjRatios, month, vreOut=args.vreOut);
                last_month = month
                totalCSO = sum([gen.CapObl for gen in genCos])

            loads = [hourlyLoad, hourlynegativeLoadSolar, hourlynegativeLoadWind]
            payment = market.run(numGen=numGenerators, genCos=genCos, totalCSO=totalCSO, load=loads, date=[date,hourEnding] , verbose=False)
            payment = np.concatenate([x if isinstance(x, np.ndarray) else [x] for x in payment])
            payments.append(payment)
            # break


            
    print('Average CSC: ', market.numberOfCSCs / args.markov_cons)
    
    payments = np.array(payments)
    print('Total Payments:', payments.sum())
    plotResults(payments, genCos, numGenerators, [args.load_rate, args.vre_mix, str(args.esCharge)], markov_cons=args.markov_cons)


