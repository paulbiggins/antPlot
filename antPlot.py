import sys
import csv
import math
import mmap
import matplotlib.pyplot as plt

csv.register_dialect('semicolon', delimiter=';')

def mathify(x,y):
    #do math and return data in different formats

    if y.isdigit(): #special case for R&S formatted data
        logmag = 20*math.log10(math.hypot(x,y))
    else:
        logmag = x

    swr = (1+10^(logmag/20))/(1-10^(logmag/20))
    mismatch = -10*math.log10(1-(10^(logmag/20))^2)

    return (logmag, swr, mismatch)



def dataParse(f):
    #parsing out the input files into useable data formats

    parsedData = []
    try:
        search = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

        #the R&S case, return loss
        if search.find('freq') != -1:
            datatype = 'loss'
            reader = csv.reader(f, dialect = 'semicolon')
            for row in reader:
                if 'freq' not in row and '#' not in row:
                    freq = float(row[0])/1000000
                    re = float(row[1])
                    im = float(row[2])
                    (logmag, swr, mismatch) = mathify(re, im)
                    parsedData.append(freq, logmag, swr, mismatch)


        #the Agilent case, return loss
        if search.find('Frequency') != -1 and search.find('Efficiency') = -1:
            datatype = 'loss'
            reader = csv.reader(f)
            for row in reader:
                if 'Frequency' not in row and '#' not in row:
                    freq = float(row[0])/1000000
                    logmag = float(row[1])
                    (logmag, swr, mismatch) = mathify(logmag, false)
                    parsedData.append(freq, logmag, swr, mismatch)


        #the Efficiency case
        if search.find('Efficiency') != -1:
            datatype = 'eff'
            reader = csv.reader(f)
            for row in reader:
                if 'Frequency' in row and row[2].isdigit():
                    freq = [float(i) for i in row and i isdigit()]
                if 'Efficiency' in row:
                    efficiency = [float(i) for i in row and i isdigit()]
            #split efficiency blocks
            spacing = freq(1) - freq(0)
            effblock = 0
            effmap = zip(freq, efficiency)
            for i in effmap:
                parsedData[effblock].append(effmap[i])
                if effmap[i+1][0]-effmap[i][0] > spacing:
                    effblock += 1

    finally:
        f.close()

    return (parsedData, datatype)



#stuffs
for i in range(1, len(sys.argv)):
    f = open(sys.argv[i], 'rt')
    data[i-1] = dataParse(f)
