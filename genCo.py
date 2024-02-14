import numpy as np
import matplotlib.pyplot as plt

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
        self.participateCap = np.minimum(self.availableCap, self.CapObl)
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


class Market:
    def __init__(self, numGen):
        self.numGen = numGen

    def getCurrentCap(self, genCos):
        currentCapSum = 0.
        self.totalAvailableCap = 0.
        for gen in genCos:
            weatherCoef = 1.
            if gen.fuelType in ['Solar', 'Wind']:
                weatherCoef = np.random.uniform(0.8, 1)
            tmpp = gen.currentCap(weatherCoef)
            currentCapSum += gen.participateCap
            self.totalAvailableCap += tmpp
        return currentCapSum

    def getObligations(self, genCos):
        obligationsSum = 0
        for gen in genCos:
            obligationsSum += gen.CapObl
        return obligationsSum
    
    def sortGenCos(self, genCos):
        # np.random.shuffle(genCos)
        return genCos


class PFP:
    def __init__(self, gencos=[], PRR=3.5, BPR=5.0):
        self.genCos = gencos
        #PRR is 3.5 K$ / MWh
        self.PRR = PRR
        # BPR is 5 K$/MW-month
        self.BPR = BPR

    def calcPFP(self, balancingRatio=1.0):
        perfScores = []
        for genCo in self.genCos:
            perfScores.append(genCo.participateCap - balancingRatio * genCo.CapObl)
        perfScores = np.array(perfScores)
        return perfScores * self.PRR
    


def plotResults(payments, genCos, numGen):
    bins=50
    plt.figure(figsize=(10, 6))
    plt.subplot(2, 1, 1)
    plt.hist(payments.sum(axis=0), bins=bins)
    plt.xlabel('Payments')
    plt.ylabel('Frequency')
    plt.yscale('log')
    plt.title('Payments Distribution over {} runs'.format(len(payments)))
    print('Sum of payments: ', payments.sum(axis=0).sum())

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