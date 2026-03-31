import csv

with open("results/panel/panel.csv") as f:
    rows = list(csv.DictReader(f))
print("Panel rows:", len(rows))