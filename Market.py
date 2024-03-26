import numpy as np

class Market:
    def __init__(self, MRR=1600, totalCSO=-1):
        self.numberOfCSCs = 0
        self.MRR = MRR
        self.totalCSO = totalCSO

    def getCurrentCap(self, genCos):
        totalAvailableCap = 0.
        for gen in genCos:
            if gen.fuelType in ['Solar', 'Wind']:
                pass
            else:
                totalAvailableCap += gen.currentCap()
        return totalAvailableCap

    def getObligations(self, genCos):
        obligationsSum = 0
        for gen in genCos:
            obligationsSum += gen.CapObl
        return obligationsSum
    
    def run(self, numGen=100, genCos=[], load=-1, verbose=False):
        totalAvailableCap = self.getCurrentCap(genCos)
        obligationsSum = self.getObligations(genCos)
        hourlyLoad, hourlynegativeLoadSolar, hourlynegativeLoadWind = load
        if verbose:
            print('Total Available Capacity: ', totalAvailableCap, ' ,Load of the Day: ', load ,\
                    ', obligationsSum: ', obligationsSum)
        if totalAvailableCap - hourlyLoad + hourlynegativeLoadSolar + hourlynegativeLoadWind  < self.MRR:
            self.numberOfCSCs += 1

            pfp = PFP(genCos)
            balanceRatio = (hourlyLoad + self.MRR) / self.totalCSO
            payments = pfp.calcPFP(hourlynegativeLoadSolar, hourlynegativeLoadWind, balancingRatio=balanceRatio)
            payments = np.array(payments)
            return payments
        else:
            return np.zeros((numGen, ))
        
    def RA(self, genCos, load, verbose=False):
        totalAvailableCap = self.getCurrentCap(genCos)
        obligationsSum = self.getObligations(genCos)
        hourlyLoad, hourlynegativeLoadSolar, hourlynegativeLoadWind = load

        if totalAvailableCap - hourlyLoad + hourlynegativeLoadSolar + hourlynegativeLoadWind  < 0:
            return 1
        else:
            return 0

    


class PFP:
    def __init__(self, gencos=[], PRR=3.5, BPR=5.0):
        self.genCos = gencos
        #PRR is 3.5 K$ / MWh
        self.PRR = PRR
        # BPR is 5 K$/MW-month
        # self.BPR = BPR

    def calcPFP(self, hourlynegativeLoadSolar, hourlynegativeLoadWind, balancingRatio=1.0):
        perfScores = []
        # Calculate Wind and Solar separately
        solarCSO = sum([genCo.CapObl for genCo in self.genCos if genCo.fuelType == 'Solar'])
        windCSO = sum([genCo.CapObl for genCo in self.genCos if genCo.fuelType == 'Wind'])

        solarScore = hourlynegativeLoadSolar - balancingRatio * solarCSO
        windScore = hourlynegativeLoadWind - balancingRatio * windCSO

        numSolar = len([genCo for genCo in self.genCos if genCo.fuelType == 'Solar'])
        numWind = len([genCo for genCo in self.genCos if genCo.fuelType == 'Wind'])
        # Calculate the rest of the generators
        for genCo in self.genCos:
            if genCo.fuelType == 'Solar':
                perfScores.append(solarScore / numSolar)
            elif genCo.fuelType == 'Wind':
                perfScores.append(windScore / numWind)
            else:
                perfScores.append((genCo.availableCap - balancingRatio * genCo.CapObl)[0])


        perfScores = np.array(perfScores)
        return perfScores * self.PRR
    