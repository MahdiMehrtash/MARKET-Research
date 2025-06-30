import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
from tqdm import tqdm
import pdb

from genCo import getGenCos, plotResults, plotRAAIMResults
from Market import Market, Incentive

def getFutureData(ISO='ISNE', verbose=False, path='data/forecast/', load_rate='high', vre_mix='high'):
    if ISO == 'ISNE':
        dfHourlyLoad = pd.read_csv(path + 'load_rate_' + load_rate + '/dfHourlyDemand2030.csv')
        dfHourlyLoad = dfHourlyLoad.reset_index(drop=True)

        dfHourlySolar = pd.read_csv(path + 'load_rate_' + load_rate + '/vre_' + vre_mix + '/dfHourlySolar.csv')
        dfHourlySolar = dfHourlySolar.reset_index(drop=True)

        dfHourlyWind = pd.read_csv(path + 'load_rate_' + load_rate + '/vre_' + vre_mix + '/dfHourlyWind.csv')
        dfHourlyWind = dfHourlyWind.reset_index(drop=True)

        dfISO = pd.read_csv(path + 'load_rate_' + load_rate + '/vre_' + vre_mix + '/dfISO.csv')
        dfISO = dfISO.reset_index(drop=True)

        dfinfo = pd.read_csv(path + 'load_rate_' + load_rate + '/vre_' + vre_mix + '/infoDict.csv')
        dfinfo = dfinfo.reset_index(drop=True)
        info = [dfinfo['numGenerators'], dfinfo['totalCap'], dfinfo['adjRatios'], dfinfo['cap_rate'], dfinfo['LOLE']]
    else:
        raise NotImplementedError
    return dfHourlyLoad, dfHourlySolar, dfHourlyWind, dfISO, info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the Market Simulation and Calculate PfP.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--ISO', type=str, default='ISNE')
    parser.add_argument('--load-rate', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--vre-mix', type=str, choices=['current', 'low', 'medium' , 'high'], default='low')
    parser.add_argument('--markov-cons', type=int, default=1, help='Number of simulations to run.')
    parser.add_argument('--sigma', type=float, default=0.1, help='VRE Variance.')
    parser.add_argument('--vreOut', action='store_true', help='VRE take no CSO.')
    parser.add_argument('--esCharge', type=float, default=1.0, help='ESs charge level @ CSCs.')
    parser.add_argument('--verbose', type=bool, default=False)

    args = parser.parse_args()
    plt.rcParams.update({'font.size': 15})

    # Get Future Load and Data
    dfHourlyLoad, dfHourlySolar, dfHourlyWind, dfISO, info = getFutureData(ISO=args.ISO, verbose=args.verbose, path='data/forecast/' , 
                                                                           load_rate=args.load_rate, vre_mix=args.vre_mix)
    
    __, totalCap, __, __, LOLE = info[0][0], info[1][0], info[2], info[3][0], info[4][0]
    numGenerators = len(dfISO.index)
    TotMaxCSO = sum(dfISO['June'].to_list())
    print('Total Capacity: ', totalCap, 'Number of Generators: ', numGenerators, 'LOLE: ', LOLE, 'Total CSO: ', TotMaxCSO)

    # Get the Minimum Reserve Requirement for CSC
    capacities = list(dfISO['Nameplate Capacity (MW)'].sort_values(ascending=False))
    MRR_PfP = capacities[0] + 0.5 * capacities[1]
    MRR_CP = 1.5 * capacities[0] 
    print('MRR PfP: ', MRR_PfP, ' vs. MRR CP: ', MRR_CP)
    # Get the GenCos and CSO
    genCos =  getGenCos(dfISO, esCharge=args.esCharge)

    # Run the Market Simulation
    paymentsPFP, paymentsCP = [], []
    PfPavailabilitys = []
    market = Market(MRR=[MRR_PfP, MRR_CP], load=args.load_rate)
    last_month = None; totalCSO = -1
    for __ in range(args.markov_cons):
        for hour in tqdm(range(dfHourlyLoad.index.stop - dfHourlyLoad.index.start)):
            hourlyLoad = dfHourlyLoad.iloc[hour]['Total Load']
            hourlynegativeLoadSolar = np.random.normal(dfHourlySolar.iloc[hour]['tot_solar_mwh'], args.sigma, 1)
            hourlynegativeLoadWind = np.random.normal(dfHourlyWind.iloc[hour]['tot_wind_mwh'], args.sigma, 1)

            date = pd.to_datetime(dfHourlyLoad.iloc[hour]['Date'])
            hourEnding = dfHourlyLoad.iloc[hour]['Hour Ending']
            month = date.strftime('%B')
            if last_month != month:
                # Update CSO for the new month
                for gen in genCos: gen.updateCSO(dfISO, month, vreOut=args.vreOut);
                last_month = month
                totalCSO = sum([gen.CapObl for gen in genCos])

            loads = [hourlyLoad, hourlynegativeLoadSolar, hourlynegativeLoadWind]
            paymentPFP, paymentCP, PfPavailability = market.run(numGen=numGenerators, genCos=genCos, totalCSO=totalCSO, load=loads, date=[date,hourEnding] , verbose=False)
            paymentPFP = np.concatenate([x if isinstance(x, np.ndarray) else [x] for x in paymentPFP])
            paymentCP = np.concatenate([x if isinstance(x, np.ndarray) else [x] for x in paymentCP])
            paymentsPFP.append(paymentPFP); paymentsCP.append(paymentCP); 
            if PfPavailability is not None:    
                PfPavailabilitys.append(PfPavailability)
            # if market.numberOfCSCs > 1:
            #     break

    # paymentRAAIM = market.RAAIM(genCos=genCos)
    paymentsPFP = np.array(paymentsPFP); 
    PfPavailabilitys = np.array(PfPavailabilitys).reshape(numGenerators, -1)
    # paymentsCP = np.array(paymentsCP); 
    # paymentRAAIM = np.array(paymentRAAIM)

    # # Save ISONE Payments ------------
    # Convert NumPy array to DataFrame
    df = pd.DataFrame(PfPavailabilitys)
    df['id'] = [gen.ID for gen in genCos]
    df['type'] = [gen.fuelType for gen in genCos]
    column_names = [f"CSC#_{i+1}" for i in range(df.shape[1] - 2)]  # Exclude the 'id' column
    df.columns = column_names + ['id', 'type']
    df.to_excel("./run_data/paymentsPFP_with_info-" + args.load_rate + args.vre_mix + ".xlsx", index=False)
    # -------------------------------

        
    print('Average LOLE: ', market.LOLE / args.markov_cons, 'Average CSC: ', market.numberOfCSCs / args.markov_cons, 
          'Average PAI: ', market.numberOfPAIs / args.markov_cons)
    # print('Total PFP Payments:', paymentsPFP.sum(), 'Total CP Payments:', paymentsCP.sum())
    # , 'Total RAAIM Payments:', paymentRAAIM.sum())

    # plotResults(paymentsPFP, genCos, [args.load_rate, args.vre_mix, str(args.esCharge), 'PfP'], markov_cons=args.markov_cons, TotMaxCSO=TotMaxCSO)
    # plotResults(paymentsCP, genCos, [args.load_rate, args.vre_mix, str(args.esCharge), 'CP'], markov_cons=args.markov_cons)
    # plotRAAIMResults(paymentRAAIM, genCos, [args.load_rate, args.vre_mix, str(args.esCharge), 'RAAIM'], markov_cons=args.markov_cons)


