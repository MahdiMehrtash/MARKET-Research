import numpy as np

class Market:
    def __init__(self, MRR=1600):
        self.numberOfCSCs = 0
        self.MRR = MRR

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
            # raise
            # print('-- Total Available Capacity: ', self.totalAvailableCap, ' ,Load of the Day: ', load ,\
            #         ', obligationsSum: ', obligationsSum)
            # genCos = market.sortGenCos(genCos)
            # for gen in genCos:
            #     if not gen.deficit:
            #         tmp = np.minimum(obligationsSum - currentCapSum, gen.availableCap - gen.participateCap)
            #         currentCapSum +=  tmp
            #         gen.participateCap += tmp
            #     if np.allclose(currentCapSum, obligationsSum):
            #         break
            # if not np.allclose(currentCapSum, obligationsSum):
            #     print('Outage!')
            #     return None
            pfp = PFP(genCos)
            payments = pfp.calcPFP(hourlynegativeLoadSolar, hourlynegativeLoadWind)
            payments = np.array(payments)
            return payments
        else:
            # print(market.totalAvailableCap - load - MRR)
            # print(np.zeros((numGen)).shape)
            return np.zeros((numGen, ))

    


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
    