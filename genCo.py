import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
# Based on https://www.iso-ne.com/static-assets/documents/genrtion_resrcs/gads/class_ave_2010.pdf
# and https://www.iso-ne.com/static-assets/documents/2023/05/a04_05312023_pspc_adcr_availabilities-fcff6c70.pdf
FOR_dict = {'Landfill Gas': 0.04, 'Gas': 0.04, 'Gas-Other': 0.04,
            'Oil': 0.13, 'Coal': 0.08, \
            'Hydro': 0.07, 'LD': 0.07, 'Nuclear': 0.01, \
            'Refuse/Woods': 0.09, 'Demand': 0.10,\
            'Solar': 0.07, 'Wind': 0.07, 'ES':0.07, 'Other': 0.08}

NoCSOList = ['Wind', 'Solar', 'ES']

class GenCo:
    def __init__(self, ID, MaxCap, CapObl, fuelType, FOR=0.1, esCharge=1.0):
        self.MaxCap = MaxCap
        self.CapObl = CapObl
        self.FOR = FOR
        self.fuelType = fuelType
        self.ID = ID
        self.availability = {}
        self.AAHs = {}
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
        if self.fuelType in NoCSOList and vreOut:
            self.CapObl = 0.0
            return
        # if self.fuelType in ['Wind'] and vreOut:
        #     print('??')
        #     self.CapObl = dfISO[dfISO['ID'] == self.ID][month].item() * 0.5
        #     return
        if len(dfISO[dfISO['Fuel Type'] == self.fuelType]) > 0:
            self.CapObl = dfISO[dfISO['ID'] == self.ID][month].item()
            
            if self.CapObl > self.MaxCap:
                print(self.ID, self.fuelType, self.CapObl, self.MaxCap)
                raise ValueError
            assert self.CapObl >= 0.0
            assert self.CapObl <= self.MaxCap
        else:
            self.CapObl = 0.0


    def updateCSOinFCA(self, dfISO, currentCSO, currentP1, P2, sumOfLoads, vreOut=False):
        lambdaCoef = 0.9
        if self.fuelType in NoCSOList and vreOut:
            self.CapObl = 0.0
            return
        if self.ID in dfISO['ID'].to_list():
            xQC = dfISO[dfISO['ID'] == self.ID]['FCA Qual'].item()
            # xQC = dfISO[dfISO['ID'] == self.ID]['Nameplate Capacity (MW)'].item()
            # p1: $/kW-month or k$/MW-month
            # p2: 9.337 k$/MWh
            # print((P2 / (currentP1 * 12)) * sumOfLoads - currentCSO, xQC)
            if (P2 / (currentP1 * 12)) * sumOfLoads - currentCSO >= xQC:
                self.CapObl = 0.0 * lambdaCoef + self.CapObl * (1 - lambdaCoef)
            else:
                self.CapObl = xQC * lambdaCoef + self.CapObl * (1 - lambdaCoef)
            
            if self.CapObl > self.MaxCap:
                print(self.ID, self.fuelType, self.CapObl, self.MaxCap)
                raise ValueError
            assert self.CapObl >= 0.0
            assert self.CapObl <= self.MaxCap
        else:
            self.CapObl = 0.0

    def getBid(self, dfISO, currentCSO, P2, sumOfLoads, vreOut=False):
        if self.fuelType in NoCSOList and vreOut:
            return 0.0
        
        return P2 * sumOfLoads / (currentCSO + dfISO[dfISO['ID'] == self.ID]['FCA Qual'].item())

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




def plotResults(payments, genCos, info, markov_cons=1, TotMaxCSO=-1):
    bins=50
    print(payments.shape)
    payed = payments.sum(axis=0)
    # print(payed.shape)
    plt.hist(payed / markov_cons, bins=bins)
    plt.xlabel('Payments k$')
    plt.ylabel('Frequency')
    plt.xticks(rotation=45)  # Rotates x-axis labels by 45 degrees
    plt.tight_layout() 
    plt.yscale('log')
    # plt.title('Average Payments Distribution over {} runs'.format(markov_cons))
    plt.savefig('Payments/Load-' + info[0] + '/paymentsdist' + '-' + info[1] + '-' + info[2] + info[3] + '.pdf')
    plt.show(block=False)
    # plt.pause(3)
    plt.close()

    paymentsByFuel = {}
    csoByFuel = {}
    # print(payments)
    for i in range(len(genCos)):
        genco = genCos[i]
        if genco.fuelType in paymentsByFuel:
            paymentsByFuel[genco.fuelType] += payments[:, i].sum()
            csoByFuel[genco.fuelType] += genco.CapObl
        else:
            paymentsByFuel[genco.fuelType]  = payments[:, i].sum()
            csoByFuel[genco.fuelType] = genco.CapObl

    # Edit Fix CSO calculation
    x = np.sum(list(genco.CapObl for genco in genCos))
    ICAP = np.sum(list(genco.MaxCap for genco in genCos))
    OGCSO = TotMaxCSO
    print('---------------------', info[1])
    a = 5
    alpha = a / (ICAP - OGCSO)
    BPR = - alpha * (x - ICAP)
    print("BPR", BPR)
    print(info[3] + ': ',  paymentsByFuel)
    # print(csoByFuel)
    index = np.argsort(list(paymentsByFuel.values()))
    index = index[::-1]
    plt.figure(figsize=(10, 5))
    val = np.array(list(paymentsByFuel.values()))[index] / markov_cons / 1000
    plt.bar(np.array(list(paymentsByFuel.keys()))[index], val, label=info[3] + ' Payments')
    plt.bar(np.array(list(csoByFuel.keys()))[index], np.array(list(csoByFuel.values()))[index] * BPR * 12 / 1000,alpha=0.5, label='FCA Payments')
            # bottom=val)
    # plt.xticks(fontsize = 8) 
    plt.ylabel('Payments M$')
    plt.xticks(rotation=45)  # Rotates x-axis labels by 45 degrees
    plt.tight_layout() 
    plt.legend()
    plt.savefig('Payments/Load-' + info[0] + '/paymentsByFuel' + '-' + info[1] + '-' + info[2] + info[3] + '.pdf')
    plt.show(block=False)
    plt.pause(3)
    plt.close()


def plotRAAIMResults(payments, genCos, info, markov_cons=1):
    bins=50
    print(payments.shape)
    payed = payments.sum(axis=0)
    # print(payed.shape)
    plt.hist(payed / markov_cons, bins=bins)
    plt.xlabel('Payments k$')
    plt.xticks(rotation=45)  # Rotates x-axis labels by 45 degrees
    plt.tight_layout() 
    plt.ylabel('Frequency')
    plt.yscale('log')
    # plt.title('Average Payments Distribution over {} runs'.format(markov_cons))
    plt.savefig('Payments/Load-' + info[0] + '/paymentsdist' + '-' + info[1] + '-' + info[2] + info[3] + '.pdf')
    plt.show(block=False)
    # plt.pause(3)
    plt.close()

    paymentsByFuel = {}
    csoByFuel = {}
    for i in range(len(genCos)):
        genco = genCos[i]
        if genco.fuelType in paymentsByFuel:
            paymentsByFuel[genco.fuelType] += payments[i].sum()
            csoByFuel[genco.fuelType] += genco.CapObl
        else:
            paymentsByFuel[genco.fuelType]  = payments[i].sum()
            csoByFuel[genco.fuelType] = genco.CapObl

    print(info[3] + ': ',  paymentsByFuel)
    index = np.argsort(list(paymentsByFuel.values()))
    index = index[::-1]
    plt.figure(figsize=(10, 5))
    plt.bar(np.array(list(paymentsByFuel.keys()))[index], np.array(list(paymentsByFuel.values()))[index] / markov_cons / 1000, label='RAAIM Payments')
    # plt.xticks(fontsize = 8) 
    plt.ylabel('Payments M$')
    plt.xticks(rotation=45)  # Rotates x-axis labels by 45 degrees
    plt.tight_layout() 
    plt.legend()
    plt.savefig('Payments/Load-' + info[0] + '/paymentsByFuel' + '-' + info[1] + '-' + info[2] + info[3] + '.pdf')
    plt.show(block=False)
    plt.pause(3)
    plt.close()