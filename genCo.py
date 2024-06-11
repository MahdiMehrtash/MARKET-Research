import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
# Based on https://www.iso-ne.com/static-assets/documents/genrtion_resrcs/gads/class_ave_2010.pdf
FOR_dict = {'Landfill Gas': 0.04, 'Gas': 0.04, 'Gas-Other': 0.04,
            'Oil': 0.13, 'Coal': 0.08, \
            'Hydro': 0.07, 'PS': 0.07, 'Nuclear': 0.01, \
            'Refuse/Woods': 0.09,\
            'Solar': 0.07, 'Wind': 0.07, 'ES':0.07, 'Other': 0.08}

class GenCo:
    def __init__(self, MaxCap, CapObl, fuelType, FOR=0.1, esCharge=1.0):
        self.MaxCap = MaxCap
        self.CapObl = CapObl
        self.FOR = FOR
        self.fuelType = fuelType
        if self.fuelType in ['ES']:
            self.dischargeRate = 0.25
            self.totalHours = esCharge/self.dischargeRate
            self.hoursRemaining = self.totalHours

    def currentCap(self, weatherCoef=1):
        self.availableCap = self.MaxCap * weatherCoef * np.random.choice(2, 1, p=[self.FOR, 1-self.FOR])
        if self.fuelType in ['ES'] and self.hoursRemaining == 0:
            self.availableCap = 0
        return self.availableCap
    
    def updateCSO(self, dfCSO, dfISO, cap_rate, adj_rate, month, vreOut=False):
        if len(dfCSO[dfCSO['Fuel Type'] == self.fuelType]) > 0:
            totalCSObyFuel = dfCSO[dfCSO['Fuel Type'] ==  self.fuelType][month].sum()
            totalCapbyFuel = dfISO[dfISO['Fuel Type'] == self.fuelType]['Nameplate Capacity (MW)'].sum()
            if self.fuelType in ['Wind', 'Solar', 'ES']:
                if vreOut:
                    self.CapObl = 0.0
                else:
                    self.CapObl = self.MaxCap * (totalCSObyFuel * adj_rate[0])/ totalCapbyFuel
            else:
                self.CapObl = self.MaxCap * (totalCSObyFuel * adj_rate[1])/ totalCapbyFuel
            
            if self.CapObl > self.MaxCap:
                print(totalCSObyFuel * adj_rate[1], totalCapbyFuel)
                print('CapObl > MaxCap', self.CapObl, self.MaxCap, self.fuelType)
                print('totalCSObyFuel', totalCSObyFuel, 'totalCapbyFuel', totalCapbyFuel, 'adj_rate', adj_rate)
                raise ValueError
            assert self.CapObl >= 0.0
            assert self.CapObl <= self.MaxCap
        else:
            self.CapObl = 0.0

def getGenCos(numGen, df=None, esCharge=None):
    genCos = []
    MaxCaps = df['Nameplate Capacity (MW)'].to_list()
    fuelTypes = df['Fuel Type'].to_list()


    for i in range(numGen):
        MaxCap = MaxCaps[i] 
        fuelType = fuelTypes[i]
        obligation = -1
        FOR = FOR_dict[fuelType]

        genCos.append(GenCo(MaxCap, obligation, fuelType, FOR=FOR, esCharge=esCharge))
    return np.array(genCos)




def plotResults(payments, genCos, numGen, info, markov_cons=1):
    bins=50
    print(payments.shape)
    payed = payments.sum(axis=0)
    print(payed.shape)
    plt.hist(payed / markov_cons, bins=bins)
    plt.xlabel('Payments K$')
    plt.ylabel('Frequency')
    plt.yscale('log')
    plt.title('Average Payments Distribution over {} runs'.format(markov_cons))
    plt.savefig('Payments/Load-' + info[0] + '/paymentsdist' + '-' + info[1] + '-' + info[2] + '.pdf')
    plt.show(block=False)
    plt.pause(3)
    plt.close()

    paymentsByFuel = {}
    csoByFuel = {}
    for i in range(len(genCos)):
        genco = genCos[i]
        if genco.fuelType in paymentsByFuel:
            paymentsByFuel[genco.fuelType] += payments[:, i].sum()
            csoByFuel[genco.fuelType] += genco.CapObl
        else:
            paymentsByFuel[genco.fuelType]  = payments[:, i].sum()
            csoByFuel[genco.fuelType] = genco.CapObl

    BPR = 3
    print(paymentsByFuel)
    print(csoByFuel)
    index = np.argsort(list(paymentsByFuel.values()))
    index = index[::-1]
    plt.figure(figsize=(15, 5))
    plt.bar(np.array(list(paymentsByFuel.keys()))[index], np.array(list(paymentsByFuel.values()))[index] / markov_cons / 1000, label='PfP Payments')
    plt.bar(np.array(list(csoByFuel.keys()))[index], np.array(list(csoByFuel.values()))[index] * BPR * 12 / 1000, alpha=0.5, label='FCA Payments')
    # plt.xticks(fontsize = 8) 
    plt.ylabel('Payments M$')
    plt.legend()
    plt.savefig('Payments/Load-' + info[0] + '/paymentsByFuel' + '-' + info[1] + '-' + info[2] + '.pdf')
    plt.show(block=False)
    plt.pause(3)
    plt.close()