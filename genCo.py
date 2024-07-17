import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
# Based on https://www.iso-ne.com/static-assets/documents/genrtion_resrcs/gads/class_ave_2010.pdf
# and https://www.iso-ne.com/static-assets/documents/2023/05/a04_05312023_pspc_adcr_availabilities-fcff6c70.pdf
FOR_dict = {'Landfill Gas': 0.04, 'Gas': 0.04, 'Gas-Other': 0.04,
            'Oil': 0.13, 'Coal': 0.08, \
            'Hydro': 0.07, 'LD': 0.07, 'Nuclear': 0.01, \
            'Refuse/Woods': 0.09, 'Demand': 0.17,\
            'Solar': 0.07, 'Wind': 0.07, 'ES':0.07, 'Other': 0.08}

class GenCo:
    def __init__(self, ID, MaxCap, CapObl, fuelType, FOR=0.1, esCharge=1.0):
        self.MaxCap = MaxCap
        self.CapObl = CapObl
        self.FOR = FOR
        self.fuelType = fuelType
        self.ID = ID
        if self.fuelType in ['ES']:
            self.dischargeRate = 0.25
            self.totalHours = esCharge/self.dischargeRate
            self.hoursRemaining = self.totalHours

    def currentCap(self):
        self.availableCap = self.MaxCap * np.random.choice(2, 1, p=[self.FOR, 1-self.FOR])
        if self.fuelType in ['ES']:
            self.availableCap = np.maximum(0.0, np.minimum(1, self.hoursRemaining) * self.MaxCap * self.dischargeRate)
        return self.availableCap
    
    def updateCSO(self, dfISO, month, vreOut=False):
        if self.fuelType in ['Wind', 'Solar', 'ES'] and vreOut:
            self.CapObl = 0.0
            return
        if len(dfISO[dfISO['Fuel Type'] == self.fuelType]) > 0:
            self.CapObl = dfISO[dfISO['ID'] == self.ID][month].item()
            
            if self.CapObl > self.MaxCap:
                print(self.ID, self.fuelType, self.CapObl, self.MaxCap)
                raise ValueError
            assert self.CapObl >= 0.0
            assert self.CapObl <= self.MaxCap
        else:
            self.CapObl = 0.0


    def updateCSOinFCA(self, dfISO, currentCSO, currentP1, P2, vreOut=False):
        if self.fuelType in ['Wind', 'Solar', 'ES'] and vreOut:
            self.CapObl = 0.0
            return
        if self.ID in dfISO['ID'].to_list():
            xQC = dfISO[dfISO['ID'] == self.ID]['FCA Qual'].item()
            sumOfLoads = 20000 * 20
            # p1: $/kW-month or k$/MW-month
            # p2: 3.5 k$/MWh
            # print((P2 / (currentP1 * 12)) * sumOfLoads, currentCSO)
            # raise
            # print((P2 / (currentP1 * 12)) * sumOfLoads - currentCSO, xQC)
            print((P2 / (currentP1 * 12)) * sumOfLoads - currentCSO, (P2 / (currentP1 * 12)) * sumOfLoads >= currentCSO + xQC)
            if (P2 / (currentP1 * 12)) * sumOfLoads - currentCSO >= xQC:
                self.CapObl = 0.0
            else:
                self.CapObl = xQC
            
            if self.CapObl > self.MaxCap:
                print(self.ID, self.fuelType, self.CapObl, self.MaxCap)
                raise ValueError
            assert self.CapObl >= 0.0
            assert self.CapObl <= self.MaxCap
        else:
            self.CapObl = 0.0

def getGenCos(df=None, esCharge=None):
    genCos = []
    MaxCaps = df['Nameplate Capacity (MW)'].to_list()
    fuelTypes = df['Fuel Type'].to_list()
    IDs = df['ID'].to_list()


    for i in range(len(df)):
        MaxCap = MaxCaps[i] 
        fuelType = fuelTypes[i]
        obligation = -1
        FOR = FOR_dict[fuelType]
        id = IDs[i]

        genCos.append(GenCo(id, MaxCap, obligation, fuelType, FOR=FOR, esCharge=esCharge))
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

    # Edit Fix CSO calculation
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