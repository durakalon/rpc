#!/bin/bash

# Tester le solveur CP-SAT sur les 3 leagues
python3 cp-sat/run.py -i testsuite/instances/bronze/bronze_likely_sat_01.txt -o bronze_test.out
python3 visualize.py bronze_test.out --truck-dimensions "200x150x150"

python3 cp-sat/run.py -i testsuite/instances/silver/silver_likely_sat_01.txt -o silver_test.out
python3 visualize.py silver_test.out --truck-dimensions "350x250x250"

python3 cp-sat/run.py -i testsuite/instances/gold/gold_manual_check.txt -o gold_test.out
python3 visualize.py gold_test.out --truck-dimensions "300x250x200" --order-file testsuite/instances/gold/gold_manual_check.txt --show-order --colormap plasma

# cleaner entre les deux tests
rm bronze_test.out silver_test.out gold_test.out

python3 ad-hoc/run.py -i testsuite/instances/bronze/bronze_likely_sat_01.txt -o bronze_test.out
python3 visualize.py bronze_test.out --truck-dimensions "200x150x150" --order-file testsuite/instances/bronze/bronze_likely_sat_01.txt

python3 ad-hoc/run.py -i testsuite/instances/silver/silver_likely_sat_01.txt -o silver_test.out
python3 visualize.py silver_test.out --truck-dimensions "350x250x250" --order-file testsuite/instances/silver/silver_likely_sat_01.txt

python3 ad-hoc/run.py -i testsuite/instances/gold/gold_manual_check.txt -o gold_test.out
python3 visualize.py gold_test.out --truck-dimensions "300x250x200" --order-file testsuite/instances/gold/gold_manual_check.txt --show-order --colormap plasma

# # cleaner entre les deux tests
rm bronze_test.out silver_test.out gold_test.out

# python3 milp/run.py -i testsuite/instances/bronze/bronze_likely_sat_01.txt -o bronze_test.out
# python3 visualize.py bronze_test.out --truck-dimensions "200x150x150" --order-file testsuite/instances/bronze/bronze_likely_sat_01.txt

# python3 milp/run.py -i testsuite/instances/silver/silver_likely_sat_01.txt -o silver_test.out
# python3 visualize.py silver_test.out --truck-dimensions "350x250x250" --order-file testsuite/instances/silver/silver_likely_sat_01.txt

# python3 milp/run.py -i testsuite/instances/gold/gold_manual_check.txt -o gold_test.out
# python3 visualize.py gold_test.out --truck-dimensions "300x250x200" --order-file testsuite/instances/gold/gold_manual_check.txt --show-order --colormap plasma

# # cleaner
# rm bronze_test.out silver_test.out gold_test.out