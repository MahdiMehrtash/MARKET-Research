import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import argparse

from utilsData import getHourlyLoad

LOAD_ADJ = {'low':0.95, 'medium':1.0, 'high':1.05}
# Summer and Winter Peaks
PeakGrowths = [1.09, 1.206]

def getFutureLoadData(dfHourlyLoad, load_rate='low'):
    dfHourlyLoadAdj = dfHourlyLoad.copy()
    if load_rate == 'current':
        return dfHourlyLoadAdj
    
    load_coef = LOAD_ADJ[load_rate]

    summerPeakIndex = dfHourlyLoad['Total Load'].argmax()
    linComb = np.linspace(PeakGrowths[0], PeakGrowths[1], num=8760//2)
    linComb = np.concatenate((linComb, linComb[::-1]))
    linComb = np.roll(linComb, summerPeakIndex)

    adjustedLoads = np.array(dfHourlyLoad['Total Load'].to_list())
    adjustedLoads = adjustedLoads * linComb
    dfHourlyLoadAdj['Total Load'] = adjustedLoads * load_coef
    return dfHourlyLoadAdj


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Run the Market Simulation and Calculate PfP.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--ISO', type=str, default='ISNE')
    parser.add_argument('--load-rate', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--verbose', type=bool, default=False)

    args = parser.parse_args()

    # Get 2023 Load
    dfHourlyLoad = getHourlyLoad(ISO=args.ISO, verbose=args.verbose)

    # Build Future Load
    dfHourlyLoadAdj = getFutureLoadData(dfHourlyLoad, args.load_rate)
    
    # Save to CSV
    dfHourlyLoadAdj.to_csv('data/forecast/load_rate_' + args.load_rate + '/dfHourlyDemand2030.csv', index=False)


    if args.verbose:
        month, day, year = map(int,dfHourlyLoad.loc[0]['Date'].split('/'))
        start = datetime(year, month, day, int(dfHourlyLoad.loc[0]['Hour Ending']) - 1)
        month, day, year = map(int,dfHourlyLoad.loc[len(dfHourlyLoad) - 1]['Date'].split('/'))
        end =  datetime(year, month, day, int(dfHourlyLoad.loc[len(dfHourlyLoad) - 1]['Hour Ending']) - 1)

        timeRange = pd.date_range(start, end, periods=len(dfHourlyLoad))

        plt.figure(figsize=(15, 5))
        plt.plot(timeRange, dfHourlyLoad['Total Load'], label='Total Load 2023', alpha=0.5)
        plt.plot(timeRange, dfHourlyLoadAdj['Total Load'], label='Total Load 2030', alpha=0.5)
        plt.ylim(0, 30000)
        plt.xlabel('Date')
        plt.ylabel('Load (MW)')
        plt.legend()
        plt.show(block=False)
        plt.pause(3)
        plt.close()


    




