import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from tqdm import tqdm


from genCo import getGenCos, plotResults, plotData, plotGenData
from utilsData import getISO, getHourlyLoad, getHourlyGen, \
    getFutureGeneratorData, getFutureLoadData, getFutureGenerationData 
from Market import Market, PFP

# @TODO: 1) Fix MRR - Done
#        2) Add arg parser
#        3) Convex conmbination
#        4) Fix Balancing Ratio

if __name__ == "__main__":
    load_rate = 'low'
    vre_mix = 'low'
    verbose=False
    markovCons = 1

    dfISO, numGenerators, totalCap, totalCSO = getISO(ISO='ISNE')
    dfHourlyLoad = getHourlyLoad(ISO='ISNE', verbose=False)
    dfHourlySolar, dfHourlyWind = getHourlyGen(ISO='ISNE', verbose=False)

    if True:
        dfISOAdj, totalCSOAdj, totalCapAdj, adjRatios = getFutureGeneratorData(dfISO, totalCSO, load_rate=load_rate, vre_mix=vre_mix)
        dfHourlyLoadAdj = getFutureLoadData(dfHourlyLoad, load_rate)
        dfHourlySolarAdj, dfHourlyWindAdj = getFutureGenerationData(dfHourlySolar, dfHourlyWind, adjRatios)
    else:
        totalCapAdj = totalCap
        totalCSOAdj = totalCSO
        dfISOAdj = dfISO
        dfHourlySolarAdj = dfHourlySolar
        dfHourlyLoadAdj = dfHourlyLoad
        dfHourlyWindAdj = dfHourlyWind

    capacities = list(dfISOAdj['Nameplate Capacity (MW)'].sort_values(ascending=False))
    MRR = capacities[0] + 0.5 * capacities[1]
    
    genCos =  getGenCos(numGenerators, totalCSOAdj, dfISOAdj)

    payments = []
    market = Market(MRR=MRR)
    for __ in range(markovCons):
        for hour in tqdm(range(5000, dfHourlyLoadAdj.index.stop - dfHourlyLoadAdj.index.start)):
            # if market.numberOfCSCs > 0:
            #     break
            hourlyLoad = dfHourlyLoadAdj.iloc[hour]['Total Load']
            hourlynegativeLoadSolar = dfHourlySolarAdj.iloc[hour]['tot_solar_mwh']
            hourlynegativeLoadWind = dfHourlyWindAdj.iloc[hour]['tot_wind_mwh']

            loads = [hourlyLoad, hourlynegativeLoadSolar, hourlynegativeLoadWind]
            payment = market.run(numGen=numGenerators, genCos=genCos, load=loads, verbose=False)
            payments.append(payment)
    print(market.numberOfCSCs / markovCons)

    
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


