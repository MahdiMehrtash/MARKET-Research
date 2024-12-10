import numpy as np
import pandas as pd
import argparse
from tqdm import tqdm
import pdb
import ast
import matplotlib.pyplot as plt

from genCo import getGenCos, plotResults
# from Market import Market, PFP
from main import getFutureData

def demandCurve(x):
    assert x >= 0.0
    cnt1x = 20.0
    cnt2x = 30.0
    maxPrice = 30

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
    
    plt.rcParams.update({'font.size': 15})

    p2 = 9.337
    # Get the GenCos and CSO
    genCos =  getGenCos(dfISO, esCharge=args.esCharge)
    for gen in genCos: gen.updateCSO(dfISO, 'FCA Qual', vreOut=args.vreOut);
    totalCSO = np.sum([gen.CapObl for gen in genCos])   

    # winds, solars = [], []
    # for gen in genCos:
    #     if gen.fuelType in ['Wind']:
    #         winds.append(gen.MaxCap)
    #     elif gen.fuelType in ['Solar']:
    #         solars.append(gen.MaxCap)

    # plt.hist(winds, bins=50, alpha=1, label='Wind')
    # plt.hist(solars, bins=50, alpha=0.5, label='Solar')
    # plt.legend()
    # plt.show()
        
    # for gen in genCos: gen.updateCSO(dfISO, 'Jan', vreOut=args.vreOut);
    # raise

    file_path = "./paymentsPFP_with_info.xlsx"
    df = pd.read_excel(file_path)

    # Apply a map to convert string lists like '[2.4]' to float values
    df_numeric = df.iloc[:, :-2].applymap(lambda x: ast.literal_eval(x)[0] if isinstance(x, str) else x)
    
    sumOfLoads = df_numeric.sum().sum()
    print('Sum of Loads: ', sumOfLoads)

    # Method 1: using the iteration on Demand Curve
    previousCSO = -1.0
    while True:
        priceP1 = demandCurve(totalCSO / 1000)
        print('--Price P1: ', priceP1, 'Total CSO: ', totalCSO)
        print('Critical point: ', (p2 / (priceP1 * 12)) * sumOfLoads - totalCSO)
        # Update CSO based on the current P1 price
        np.random.shuffle(genCos)
        for gen in genCos: 
            gen.updateCSOinFCA(dfISO, currentCSO=totalCSO, currentP1=priceP1, P2=p2, sumOfLoads=sumOfLoads, vreOut=args.vreOut);
            totalCSO = np.sum([gen.CapObl for gen in genCos])
            priceP1 = demandCurve(totalCSO / 1000)
            # print('----Price P1: ', priceP1, 'Total CSO: ', totalCSO)


        if np.abs(previousCSO - totalCSO) < 1:
            break
        else:
            previousCSO = totalCSO
        # print('Total CSO: ', totalCSO, 'FCA Price: ', demandCurve(totalCSO / 1000))


    # winds, solars = [], []
    # for gen in genCos:
    #     if gen.fuelType in ['Wind']:
    #         print(gen.fuelType, gen.CapObl, dfISO[dfISO['ID'] == gen.ID]['FCA Qual'].item())
    #     elif gen.fuelType in ['Solar']:
    #         print(gen.fuelType, gen.CapObl, dfISO[dfISO['ID'] == gen.ID]['FCA Qual'].item())



    CSObyFuelType = {}
    ICAPbyFuelType = {}
    for gen in genCos:
        if gen.fuelType not in CSObyFuelType:
            CSObyFuelType[gen.fuelType] = gen.CapObl
            ICAPbyFuelType[gen.fuelType] = gen.MaxCap
        else:
            CSObyFuelType[gen.fuelType] += gen.CapObl
            ICAPbyFuelType[gen.fuelType] += gen.MaxCap

    plt.bar(CSObyFuelType.keys(), CSObyFuelType.values(), label='CSO')
    plt.legend()
    plt.show()

    fuel_types = list(CSObyFuelType.keys())
    cso_values = [CSObyFuelType[fuel] for fuel in fuel_types]
    icap_values = [ICAPbyFuelType[fuel] for fuel in fuel_types]

    plt.bar(fuel_types, [cso / icap if icap != 0 else 0 for cso, icap in zip(cso_values, icap_values)], label='CSO/ICAP')
    plt.legend()
    plt.show()

    payment = []
    paymentsByFuel, csoByFuel = {}, {}
    print("P1", priceP1)
    br = df_numeric.iloc[:, :-2].sum(axis=0) / totalCSO
    # print(br)
    # raise
    for i in range(len(genCos)):
        genco = genCos[i]
        paid =  p2 * (df_numeric[df['id'] == genCos[i].ID].sum(axis=1) - br.sum() * genCos[i].CapObl)
        payment.append(paid.values[0])
        if genco.fuelType in paymentsByFuel:
            paymentsByFuel[genco.fuelType] += paid.item()
            csoByFuel[genco.fuelType] += genco.CapObl
        else:
            paymentsByFuel[genco.fuelType] = paid.item()
            csoByFuel[genco.fuelType] = genco.CapObl
            

    index = np.argsort(list(paymentsByFuel.values()))
    index = index[::-1]
    plt.figure(figsize=(10, 5))
    val = np.array(list(paymentsByFuel.values()))[index]  / 1000
    plt.bar(np.array(list(paymentsByFuel.keys()))[index], val, label='PfP Payments')
    plt.bar(np.array(list(csoByFuel.keys()))[index], np.array(list(csoByFuel.values()))[index] * priceP1 * 12 / 1000,alpha=0.5, label='FCA Payments')
    plt.legend()
    plt.xticks(rotation=45)  # Rotates x-axis labels by 45 degrees
    plt.ylabel('Payments M$')
    plt.tight_layout() 
    plt.savefig('tmp.pdf')
    plt.show()