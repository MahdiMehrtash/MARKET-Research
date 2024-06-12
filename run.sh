#!/bin/bash

loads="high"
# vres="low medium high"
vres="medium"

# echo "---------------------- Running Load Forecast ----------------------"
# for load_rate in $loads; do 
#     echo "---------------------- Load Forecast with load rate: $load_rate"
#     python3 loadForecast.py --ISO ISNE --load-rate $load_rate --verbose False
# done

echo "---------------------- Running Forecast Simulation ----------------------"
loads="high"
for vre in $vres; do 
    for load_rate in $loads; do 
        echo "---------------------- Forecast Simulation with load rate: $load_rate and vre mix: $vre"
        python3 generationRA.py --ISO ISNE --load-rate $load_rate --vre-mix $vre --markov-cons 1 --verbose False
    done
done


echo "---------------------- Running PfP Simulation ----------------------"
loads="high"
vres="medium"
for vre in $vres; do 
    for load_rate in $loads; do 
        for es in 0.0 0.5 1.0; do
            echo "---------------------- Forecast Simulation with load rate: $load_rate and vre mix: $vre"
            python3 main.py --ISO ISNE --load-rate $load_rate --vre-mix $vre --markov-cons 1 --verbose False --vreOut --esCharge $es
        done
    done
done