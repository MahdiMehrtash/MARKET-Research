echo "---------------------- Running Load Forecast ----------------------"
python3 loadForecast.py --ISO ISNE --load-rate high --verbose True
# echo "---------------------- Running Forecast Simulation ----------------------"
# python3 gen_data.py --ISO ISNE --load-rate low --vre-mix high --markov-cons 100 --verbose False
# echo "---------------------- Running PfP Simulation ----------------------"
# python3 run.py --ISO ISNE --load-rate low --vre-mix low --markov-cons 10 --verbose False