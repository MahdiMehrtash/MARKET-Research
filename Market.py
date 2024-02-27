import numpy as np

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
    