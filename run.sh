#!/bin/bash

loads="low medium high"
vres="low medium high"

# echo "---------------------- Running Load Forecast ----------------------"
# for load_rate in $loads; do 
#     echo "---------------------- Load Forecast with load rate: $load_rate"
#     python3 loadForecast.py --ISO ISNE --load-rate $load_rate --verbose False
# done

# echo "---------------------- Running Forecast Simulation ----------------------"
# loads="high"
# for vre in $vres; do 
#     for load_rate in $loads; do 
#         echo "---------------------- Forecast Simulation with load rate: $load_rate and vre mix: $vre"
#         python3 generationRA.py --ISO ISNE --load-rate $load_rate --vre-mix $vre --markov-cons 5 --verbose False
#     done
# done
# # python3 generationRA.py --ISO ISNE --load-rate high --vre-mix low --markov-cons 1 --verbose False


echo "---------------------- Running PfP Simulation ----------------------"
python3 main.py --ISO ISNE --load-rate high --vre-mix medium --markov-cons 10 --verbose False 
python3 main.py --ISO ISNE --load-rate high --vre-mix high --markov-cons 10 --verbose False 
loads="high"
# vres="high"
# for vre in $vres; do 
#     for load_rate in $loads; do 
#         echo "---------------------- Forecast Simulation with load rate: $load_rate and vre mix: $vre"
#         python3 main.py --ISO ISNE --load-rate $load_rate --vre-mix $vre --markov-cons 10 --verbose False 
#     done
# done