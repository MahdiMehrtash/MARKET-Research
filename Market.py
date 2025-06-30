import numpy as np
from csv import DictWriter
from datetime import datetime


class Market:
    def __init__(self, MRR, load=None):
        self.numberOfCSCs = 0
        self.numberOfPAIs = 0
        self.LOLE = 0
        self.MRR_PFP, self.MRR_CP = MRR[0], MRR[1]

        with open('Payments/log.csv', 'w') as f:
            f.write('Running a new code' + '\n')
            f.write( datetime.now().strftime("%d/%m/%Y %H:%M:%S ") + '\n')
            f.write( 'LoadRate' + str(load) + '\n')
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

        incentive = Incentive(genCos)
        realAvaialableCap = totalAvailableCap - hourlyLoad + hourlynegativeLoadSolar + hourlynegativeLoadWind

        if realAvaialableCap < 0:
            self.LOLE += 1

        # ISONE
        if realAvaialableCap < self.MRR_PFP:
            self.numberOfCSCs += 1
            # open a csv file and append the date and time
            logDict = {'Date': date[0].strftime("%d/%m/%Y"),\
                       'hour': date[1],\
                        'totalAvailableCap': totalAvailableCap,\
                        'Hourly Load': hourlyLoad,\
                        'Hourly Negative Load Solar': hourlynegativeLoadSolar,\
                        'Hourly Negative Load Wind': hourlynegativeLoadWind, \
                        'MRR': self.MRR_PFP}
            with open('Payments/log.csv', 'a') as f_object:
                dictwriter_object = DictWriter(f_object, fieldnames=logDict.keys())
                if self.numberOfCSCs == 1:
                    dictwriter_object.writeheader()  # Write the header
                dictwriter_object.writerow(logDict)
                f_object.close()

            paymentsPFP, avaialbility = incentive.calcPFP(hourlynegativeLoadSolar, hourlynegativeLoadWind, hourlyLoad, totalCSO)
            paymentsPFP = np.array(paymentsPFP)
            PfPAvaialbility = avaialbility
        else:
            paymentsPFP = np.zeros((numGen, 1))
            PfPAvaialbility = None



        # PJM   
        if realAvaialableCap  < self.MRR_CP:
            self.numberOfPAIs += 1
            paymentsCP = incentive.calcCP(hourlynegativeLoadSolar, hourlynegativeLoadWind, hourlyLoad, totalCSO)
            paymentsCP = np.array(paymentsCP)
        else:
            paymentsCP = np.zeros((numGen, 1))

        # # RAAIM
        # incentive.calcRAAIM(hourlynegativeLoadSolar, hourlynegativeLoadWind, hourlyLoad, date)
        

        if realAvaialableCap  >= np.maximum(self.MRR_PFP, self.MRR_CP):
            # ReCharge the Batteries
            for gen in genCos:
                if gen.fuelType in ['ES']:
                    gen.hoursRemaining = np.minimum(gen.totalHours, gen.hoursRemaining + 1)

        return paymentsPFP, paymentsCP, PfPAvaialbility
    
    def RAAIM(self, genCos):
        paymentsRAAIM = []
        self.RAAIM_PPR = 3.79  #$/kW-month

        for genCo in genCos:
            payment = []
            for month in range(1, 13):
                availabilityFactor = genCo.availability[month] / genCo.AAHs[month]
                if availabilityFactor <= 0.945:
                    shortfall = availabilityFactor - 0.945
                    payment.append(int(shortfall * self.RAAIM_PPR * genCo.MaxCap))
                elif availabilityFactor >= 0.985:
                    overperform = availabilityFactor - 0.985
                    payment.append(int(overperform * self.RAAIM_PPR * genCo.MaxCap))
                else:
                    payment.append(0)
            paymentsRAAIM.append(payment)
        return paymentsRAAIM 

    
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

    


class Incentive:
    def __init__(self, gencos=[], MRR=None):
        self.genCos = gencos
        # self.MRR = MRR


    def calcPFP(self, hourlynegativeLoadSolar, hourlynegativeLoadWind, hourlyLoad, totalCSO, PPR=9.337):
        perfScores = []
        avaialbility = []
        #PRR is 3.5 K$ / MWh
        self.PFP_PPR = PPR

        # balancingRatio = (hourlyLoad + self.MRR) / self.totalCSO
        totAv = (sum([genCo.availableCap for genCo in self.genCos if genCo.fuelType not in ['Solar', 'Wind']]) +\
                                 hourlynegativeLoadWind + hourlynegativeLoadSolar)
        balancingRatio =  totAv / totalCSO
        # print(balancingRatio)
        # balancingRatio = (hourlyLoad + self.MRR)/totalCSO

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
                avaialbility.append((hourlynegativeLoadSolar / numSolar).item())
            elif genCo.fuelType == 'Wind':
                perfScores.append(windScore / numWind)
                avaialbility.append((hourlynegativeLoadWind / numWind).item())
            else:
                perfScores.append((genCo.availableCap - balancingRatio * genCo.CapObl))
                avaialbility.append((genCo.availableCap).item())


        perfScores = np.array(perfScores)
        return perfScores * self.PFP_PPR, avaialbility
    
    def calcCP(self, hourlynegativeLoadSolar, hourlynegativeLoadWind, hourlyLoad, totalCSO, CONE=0.35):
        perfScores = []
        # CONE is 0.3 K$ / MW-day
        self.CP_PPR = CONE * 365 / 30 # K$/MWh

        # balancingRatio = (hourlyLoad + self.MRR) / self.totalCSO
        balancingRatio = (sum([genCo.availableCap for genCo in self.genCos if genCo.fuelType not in ['Solar', 'Wind']]) +\
                                 hourlynegativeLoadWind + hourlynegativeLoadSolar) / totalCSO
        balancingRatio = np.minimum(1, balancingRatio)


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
            elif genCo.fuelType == 'Demand':
                perfScores.append((genCo.availableCap - genCo.CapObl))
            elif genCo.fuelType == 'Import':
                perfScores.append((genCo.availableCap - 0))
            else:
                perfScores.append((genCo.availableCap - balancingRatio * genCo.CapObl))

        perfScores = np.array(perfScores)
        return perfScores * self.CP_PPR
    
    def calcRAAIM(self, hourlynegativeLoadSolar, hourlynegativeLoadWind, hourlyLoad, date):
        Availability_dict = {'Landfill Gas': 0.9, 'Gas': 0.9, 'Gas-Other': 0.9,
            'Oil': 0.92, 'Coal': 0.92, \
            'Hydro': 0.95, 'LD': 0.92, 'Nuclear': 1.00, \
            'Refuse/Woods': 0.92, 'Demand': 0.94,\
            'Solar': 0.98, 'Wind': 1.00, 'ES':0.92, 'Other': 0.93}
        
        genericFuelTypes = ['Landfill Gas', 'Gas', 'Gas-Other', 'Oil', 'Coal', 'Hydro', 'Nuclear', 'Refuse/Woods', 'Wind', 'Solar']
        # @TODO add gas  to peak 
        baseRampFuelType = ['LD', 'Demand']
        superRampFuelType = ['ES']
        

        def isAAH(type, date):
            if type == 'generic':
                try:
                    date[1] = int(date[1])
                except:
                    return False
                # print(date[1], list(range(0, 5)) ,date[1] in list(range(0, 5)))
                if date[0].month in [3, 4, 5]:
                    if date[1] in list(range(18, 23)): return True
                else:
                    if date[1] in list(range(17, 22)): return True
            elif type == 'baseRamp':
                if True:
                    if date[1] in list(range(5, 23)): return True
            elif type == 'superRamp':
                if date[0].weekday() >= 5: return False # Weekends
                if date[0].month in [3, 4, 5, 6, 7, 8]:
                    if date[1] in list(range(14, 20)): return True
                elif date[0].month in [9, 10]:
                    if date[1] in list(range(16, 22)): return True
                else:
                    if date[1] in list(range(15, 21)): return True
            return False

        for genCo in self.genCos:
            availability_prob = Availability_dict[genCo.fuelType]
            # print(genCo.fuelType, availability_prob)
            if ((genCo.fuelType in genericFuelTypes) and isAAH('generic', date)) or\
                ((genCo.fuelType in baseRampFuelType) and isAAH('baseRamp', date)) or\
                ((genCo.fuelType in superRampFuelType) and isAAH('superRamp', date)):
                    if date[0].month in genCo.availability.keys():
                        genCo.availability[date[0].month] += np.random.choice(2, 1, p=[1-availability_prob, availability_prob])
                        genCo.AAHs[date[0].month] += 1
                    else:
                        genCo.availability[date[0].month] = np.random.choice(2, 1, p=[1-availability_prob, availability_prob])
                        genCo.AAHs[date[0].month] = 1

    