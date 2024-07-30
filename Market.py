import numpy as np
from csv import DictWriter
from datetime import datetime


class Market:
    def __init__(self, MRR=1600):
        self.numberOfCSCs = 0
        self.MRR = MRR

        with open('Payments/log.csv', 'a') as f:
            f.write('Running a new code' + '\n')
            f.write( datetime.now().strftime("%d/%m/%Y %H:%M:%S ") + '\n')
        f.close()

    def getCurrentCap(self, genCos):
        totalAvailableCap = 0.
        for gen in genCos:
            if gen.fuelType in ['Solar', 'Wind']:
                pass
            elif gen.fuelType in ['ES']:
                tmp = gen.currentCap()
                if tmp > 0:
                    totalAvailableCap += np.minimum(gen.currentCap(), gen.MaxCap * gen.dischargeRate)
                    gen.hoursRemaining = np.maximum(0.0, gen.hoursRemaining - 1) #decharge the battery
            else:
                totalAvailableCap += gen.currentCap()
        return totalAvailableCap

    def getObligations(self, genCos):
        obligationsSum = 0
        for gen in genCos:
            obligationsSum += gen.CapObl
        return obligationsSum
    
    def run(self, numGen=100, genCos=[], totalCSO=0, load=-1, date=[], verbose=False):
        totalAvailableCap = self.getCurrentCap(genCos)
        hourlyLoad, hourlynegativeLoadSolar, hourlynegativeLoadWind = load
        if verbose:
            print('Total Available Capacity: ', totalAvailableCap, ' ,Load of the Day: ', load)
        if totalAvailableCap - hourlyLoad + hourlynegativeLoadSolar + hourlynegativeLoadWind  < self.MRR:
            self.numberOfCSCs += 1
            # open a csv file and append the date and time
            logDict = {'Date': date[0].strftime("%d/%m/%Y"),\
                       'hour': date[1],\
                        'totalAvailableCap': totalAvailableCap,\
                        'Hourly Load': hourlyLoad,\
                        'Hourly Negative Load Solar': hourlynegativeLoadSolar,\
                        'Hourly Negative Load Wind': hourlynegativeLoadWind, \
                        'MRR': self.MRR}
            with open('Payments/log.csv', 'a') as f_object:
                dictwriter_object = DictWriter(f_object, fieldnames=logDict.keys())
                if self.numberOfCSCs == 1:
                    dictwriter_object.writeheader()  # Write the header
                dictwriter_object.writerow(logDict)
                f_object.close()

            pfp = PFP(genCos)
            payments = pfp.calcPFP(hourlynegativeLoadSolar, hourlynegativeLoadWind, totalCSO)
            payments = np.array(payments)
            return payments
        else:
            # ReCharge the Batteries
            for gen in genCos:
                if gen.fuelType in ['ES']:
                    gen.hoursRemaining = np.minimum(gen.totalHours, gen.hoursRemaining + 1)

            return np.zeros((numGen, 1))
        
    def RA(self, genCos, load, verbose=False):
        totalAvailableCap = self.getCurrentCap(genCos)
        hourlyLoad, hourlynegativeLoadSolar, hourlynegativeLoadWind = load

        if totalAvailableCap - hourlyLoad + hourlynegativeLoadSolar + hourlynegativeLoadWind  < 0:
            return 1
        else:
            # ReCharge the Batteries
            for gen in genCos:
                if gen.fuelType in ['ES']:
                    gen.hoursRemaining = np.minimum(gen.totalHours, gen.hoursRemaining + 1)
            return 0

    


class PFP:
    def __init__(self, gencos=[], PRR=3.5, BPR=5.0):
        self.genCos = gencos
        #PRR is 3.5 K$ / MWh
        self.PRR = PRR
        # BPR is 5 K$/MW-month
        # self.BPR = BPR

    def calcPFP(self, hourlynegativeLoadSolar, hourlynegativeLoadWind, totalCSO):
        perfScores = []

        # balancingRatio = (hourlyLoad + self.MRR) / self.totalCSO
        balancingRatio = (sum([genCo.availableCap for genCo in self.genCos if genCo.fuelType not in ['Solar', 'Wind']]) +\
                                 hourlynegativeLoadWind + hourlynegativeLoadSolar) / totalCSO

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
    