#!/bin/bash

# loads="low medium high"
# vres="low medium high"

# echo "---------------------- Running Load Forecast ----------------------"
# for load_rate in $loads; do 
#     echo "---------------------- Load Forecast with load rate: $load_rate"
#     python3 loadForecast.py --ISO ISNE --load-rate $load_rate --verbose False
# done

# echo "---------------------- Running Forecast Simulation ----------------------"
# # loads="medium"
# # vres="high"
# for vre in $vres; do 
#     for load_rate in $loads; do 
#         echo "---------------------- Forecast Simulation with load rate: $load_rate and vre mix: $vre"
#         python3 generationRA.py --ISO ISNE --load-rate $load_rate --vre-mix $vre --markov-cons 5 --verbose False
#     done
# done


echo "---------------------- Running PfP Simulation ----------------------"
loads="medium"
vres="medium"
for vre in $vres; do 
    for load_rate in $loads; do 
        for es in 0.1; do
            echo "---------------------- Forecast Simulation with load rate: $load_rate and vre mix: $vre"
            python3 main.py --ISO ISNE --load-rate $load_rate --vre-mix $vre --markov-cons 1 --verbose False --esCharge $es --vreOut
        done
    done
done

# # loads="medium"
# # vres="medium"
# for vre in $vres; do 
#     for load_rate in $loads; do 
#         python3 FCA.py --ISO ISNE --load-rate $load_rate --vre-mix $vre --verbose False --esCharge 1 
#     done
# done


