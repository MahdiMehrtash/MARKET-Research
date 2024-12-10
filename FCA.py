import numpy as np
import pandas as pd
import argparse
from tqdm import tqdm
import pdb

from genCo import getGenCos, plotResults
# from Market import Market, PFP
from main import getFutureData

def demandCurve(x):
    assert x >= 0.0
    cnt1x = 20.0
    cnt2x = 32.0
    maxPrice = 14.5

    if x <= cnt1x:
        return maxPrice #$/kW-month or k$/MW-month
    else:
        return np.maximum(maxPrice - maxPrice/(cnt2x-cnt1x) * (x - cnt1x), 0.0)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Run the Market Simulation and Calculate PfP.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--ISO', type=str, default='ISNE')
    parser.add_argument('--load-rate', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--vre-mix', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--sigma', type=float, default=0.1, help='VRE Variance.')
    parser.add_argument('--vreOut', action='store_true', help='VRE take no CSO.')
    parser.add_argument('--esCharge', type=float, default=1.0, help='ESs charge level @ CSCs.')
    parser.add_argument('--verbose', type=bool, default=False)

    args = parser.parse_args()

    # Get Future Load and Data
    __, __, __, dfISO, info = getFutureData(ISO=args.ISO, verbose=args.verbose, path='data/forecast/' , 
                                                                           load_rate=args.load_rate, vre_mix=args.vre_mix)
    
    __, totalCap, adjRatios, cap_rate, LOLE = info[0][0], info[1][0], info[2], info[3][0], info[4][0]
    numGenerators = len(dfISO.index)
    print('Total Capacity: ', totalCap, 'Number of Generators: ', numGenerators, 'LOLE: ', LOLE)
    print('Total Qualified Capacity: ', sum(dfISO['FCA Qual'].to_list()))
    print('Non-VRE QC: ', sum(dfISO[~dfISO['Fuel Type'].isin(['Wind', 'Solar', 'ES'])]['FCA Qual'].to_list()))
    print('----- \n')
    
    # Get the GenCos and CSO
    genCos =  getGenCos(dfISO, esCharge=args.esCharge)
    for gen in genCos: gen.updateCSO(dfISO, 'FCA Qual', vreOut=args.vreOut);
    totalCSO = np.sum([gen.CapObl for gen in genCos])
    sumOfLoads = 20000 * 40

    if True:
        # Method 1: using the iteration on Demand Curve
        previousCSO = -1.0
        while True:
            priceP1 = demandCurve(totalCSO / 1000)
            print('--Price P1: ', priceP1, 'Total CSO: ', totalCSO)
            print('Critical point: ', (3.5 / (priceP1 * 12)) * sumOfLoads - totalCSO)
            # Update CSO based on the current P1 price
            np.random.shuffle(genCos)
            for gen in genCos: 
                # print(gen.CapObl)
                gen.updateCSOinFCA(dfISO, currentCSO=totalCSO, currentP1=priceP1, P2=3.5, sumOfLoads=sumOfLoads, vreOut=args.vreOut);
                # print(gen.CapObl)
                totalCSO = np.sum([gen.CapObl for gen in genCos])
                priceP1 = demandCurve(totalCSO / 1000)
                # print('----Price P1: ', priceP1, 'Total CSO: ', totalCSO)


            if np.abs(previousCSO - totalCSO) < 1:
                break
            else:
                previousCSO = totalCSO
            # print('Total CSO: ', totalCSO, 'FCA Price: ', demandCurve(totalCSO / 1000))

    else:
        # Method 2: using the iteration on Demand Curve
        for i in range(1):
            # Get the bids
            biddingList = []
            for gen in genCos:
                bid = gen.getBid(dfISO, currentCSO=totalCSO, P2=3.5, sumOfLoads=sumOfLoads, vreOut=args.vreOut)
                fca_qual = dfISO[dfISO['ID'] == gen.ID]['FCA Qual'].item()
                biddingList.append((bid, fca_qual))
            
            print(sum([qc for bid, qc in biddingList]))
            print(max([bid for bid, qc in biddingList]))
            # print(demandCurve(sum([qc for bid, qc in biddingList]) / 1000))
            # print(biddingList)
            # raise
            # Clear the market
            # Sort the list by the first element of each tuple
            biddingList.sort(key=lambda x: x[0])
            totalPayments, totalCSOCleared = 0.0, 0.0
            for bid, qc in biddingList:
                # print(totalPayments, totalCSOCleared, bid, qc)
                totalPayments += bid
                totalCSOCleared += qc

                if bid > demandCurve(totalCSOCleared / 1000):
                    break
            totalCSO = totalCSOCleared
        print('Total CSO: ', totalCSO, 'FCA Price: ', demandCurve(totalCSO / 1000))



    CSObyFuelType = {}
    for gen in genCos:
        if gen.fuelType not in CSObyFuelType:
            CSObyFuelType[gen.fuelType] = gen.CapObl
        else:
            CSObyFuelType[gen.fuelType] += gen.CapObl

    import matplotlib.pyplot as plt
    plt.bar(CSObyFuelType.keys(), CSObyFuelType.values())
    plt.show()