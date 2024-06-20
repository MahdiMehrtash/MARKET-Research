import numpy as np
import pandas as pd
import argparse
from tqdm import tqdm
import pdb

from genCo import getGenCos, plotResults
from Market import Market, PFP
from main import getFutureData

def demandCurve(x):
    assert x >= 0.0
    cnt1x = 28.0
    cnt2x = 35.0

    if x <= cnt1x:
        return 14.5 #$/kW-month
    else:
        return np.maximum(14.5 - 14.5/(cnt2x-cnt1x) * (x - cnt1x), 0.0)

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

    
    # Get the GenCos and CSO
    genCos =  getGenCos(numGenerators, dfISO, esCharge=args.esCharge)
    for gen in genCos: gen.updateCSO(dfISO, 'FCA Qual', vreOut=args.vreOut);

    previousCSO = -1.0
    while True:
        priceP1 = demandCurve(totalCSO / 1000)
        print('--Price P1: ', priceP1, 'Total CSO: ', totalCSO)
        # Update CSO based on the current P1 price
        for gen in genCos: gen.updateCSOinFCA(dfISO, currentCSO=totalCSO, currentP1=priceP1, P2=3.5, vreOut=args.vreOut);
        totalCSO = np.sum([gen.CapObl for gen in genCos])


        if previousCSO == totalCSO:
            break
        else:
            previousCSO = totalCSO




