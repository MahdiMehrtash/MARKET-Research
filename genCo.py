import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd

class GenCo:
    def __init__(self, MaxCap, CapObl, fuelType, deratedCap, FOR=0.1):
        self.MaxCap = MaxCap
        self.CapObl = CapObl
        self.FOR = FOR
        self.fuelType = fuelType
        self.deratedCap = deratedCap
        self.deficit = False

    def currentCap(self, weatherCoef=1):
        self.availableCap = self.MaxCap * weatherCoef * np.random.choice(2, 1, p=[self.FOR, 1-self.FOR])
        if self.availableCap < self.CapObl:
            self.deficit = True
        # self.participateCap = np.minimum(self.availableCap, self.CapObl)
        return self.availableCap

def getGenCos(numGen, totalCSO, df=None):
    genCos = []
    MaxCaps = df['Nameplate Capacity (MW)'].to_list()
    fuelTypes = df['Fuel Type'].to_list()

    derateCnt = {'Coal': 1.0, 'Gas': 1.0, 'Hydro': 1.0, 'Nuclear': 1.0, \
                 'Oil': 1.0, 'Waste': 1.0, 'Wood': 1.0,\
                 'Solar': 0.3, 'Wind': 0.15, 'Other': 1.0}
    deratedCap = [MaxCaps[i] * derateCnt[fuelTypes[i]] for i in range(numGen)]
    totalDeratedCap = sum(deratedCap)
    obligations = deratedCap * np.array(totalCSO)/np.array(totalDeratedCap)

    for i in range(numGen):
        MaxCap = MaxCaps[i] 
        fuelType = fuelTypes[i]
        obligation = obligations[i]
        if fuelType in ['Solar', 'Wind']:
            FOR = np.min([1, np.max([0, np.random.exponential(0.05)])])
        else:
            FOR = np.min([1, np.max([0, np.random.exponential(0.15)])])
        
        genCos.append(GenCo(MaxCap, obligation, fuelType, deratedCap[i], FOR))
    return np.array(genCos)




def plotData(dfHourlyLoad, dfHourlySolar, dfHourlyWind, totalCap, totalCSO, yearPlot="2023"):
    month, day, year = map(int,dfHourlyLoad.loc[0]['Date'].split('/'))
    start = datetime(year, month, day, int(dfHourlyLoad.loc[0]['Hour Ending']) - 1)
    month, day, year = map(int,dfHourlyLoad.loc[len(dfHourlyLoad) - 1]['Date'].split('/'))
    end =  datetime(year, month, day, int(dfHourlyLoad.loc[len(dfHourlyLoad) - 1]['Hour Ending']) - 1)

    timeRange = pd.date_range(start, end, periods=len(dfHourlyLoad))


    plt.plot(timeRange, dfHourlyLoad['Total Load'], label='Total Load')
    plt.plot(timeRange, dfHourlySolar['tot_solar_mwh'], label='Solar')
    plt.plot(timeRange, dfHourlyWind['tot_wind_mwh'], label='Wind')
    plt.plot(timeRange, totalCap * np.ones(len(dfHourlyLoad)), 'k--', label='Total Capacity')
    plt.plot(timeRange, totalCSO * np.ones(len(dfHourlyLoad)), 'k--', label='Total CSO')

    plt.xlabel('Date')
    plt.ylabel('Load (MW)')
    plt.title('Hourly Load of ' + yearPlot)
    plt.legend()


def plotResults(payments, genCos, numGen):
    bins=50
    plt.figure(figsize=(10, 6))
    plt.subplot(2, 1, 1)
    plt.hist(payments.sum(axis=0), bins=bins)
    plt.xlabel('Payments')
    plt.ylabel('Frequency')
    plt.yscale('log')
    plt.title('Payments Distribution over {} runs'.format(len(payments)))
    print('Sum of payments: ', payments.sum())

    # plt.subplot(2, 1, 2)
    # VREslice, nonVREslice = [], []
    # for i in range(numGen):
    #     if genCos[i].isVRE:
    #         VREslice.append(i)
    #     else:
    #         nonVREslice.append(i)
    # plt.hist(payments[:, VREslice].sum(axis=0), bins=bins, alpha=0.5, label='VRE')
    # plt.hist(payments[:, nonVREslice].sum(axis=0), bins=bins, alpha=0.5, label='Others')
    # plt.xlabel('Payments')
    # plt.ylabel('Frequency')
    # plt.yscale('log')
    # plt.title('Payments Distribution over {} runs'.format(len(payments)))
    # plt.legend()
    plt.show()

def plotGenData(genCos, CSO=False):
    csoHist = {}
    for genco in genCos:
        if CSO:
            temp = genco.CapObl
        else:
            temp = genco.MaxCap

        if genco.fuelType in csoHist:
            csoHist[genco.fuelType] += temp
        else:
            csoHist[genco.fuelType] = temp
    print(csoHist)

    labels = list(csoHist.keys())
    weights = list(csoHist.values())

    plt.bar(labels, weights)
    plt.xlabel('Fuel Type')
    plt.ylabel(*['CSO' if CSO else 'Total Capacity'])
    # plt.title('CSO Distribution')
    # plt.show()