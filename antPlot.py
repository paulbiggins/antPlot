import os
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



def save(name, ext):
    #generate a save file path

    tempPath = os.path.dirname(os.path.realpath(sys.argv[len(sys.argv)])+'/'+name
    directory = os.path.split(tempPath)[0]
    filename = '%s.%s' (os.path.split(tempPath)[1], ext)
    if directory == '':
        directory = '.'
    if not os.path.exists(directory):
        os.makedirs(directory)
    savepath = os.path.join(directory, filename)

    return savepath



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
                    freq = [float(i) for i in row and i.isdigit()]
                if 'Efficiency' in row:
                    efficiency = [float(i) for i in row and i.isdigit()]
            #split efficiency blocks
            spacing = freq(1) - freq(0)
            effmap = zip(freq, efficiency)
            effblock = []
            for i in effmap:
                if effmap[i+1][0]-effmap[i][0] == spacing:
                    effblock.append(i)
                else:
                    parsedData.append(effblock)
                    effblock = [i]

    finally:
        f.close()

    return (parsedData, datatype)



def writeData(name, data)
    #writing the data to an organized CSV

    sortedData = []
    #first format the data
    for sublist in data:
        currentList = []
        currentList.append(sublist[1])
        for subsublist in sublist[0]:
            if type(subsublist) == list:
                for subsubsublist in subsublist:
                    currentList.append(subsubsublist)
            else:
                currentList.append(subsublist)
        sortedData.append(currentList)

    #now sort it
    sortedData.sort(key = len, reverse = True)

    #generate the header
    header = []
    for i in sortedData:
        if i[0] == 'loss':
            header.append('Frequency (MHz)')
            header.append('Return Loss (dB)')
            header.append('VSWR (V)')
            header.append('Mismatch Loss (dB)')
        if i[0] == 'eff':
            header.append('Frequency (MHz)')
            header.append('Efficiency (dB)')

    savepath = save(name, 'csv')
    f = open(savepath, 'wt')
    try:
        writer = csv.writer(f)
        writer.writerow(header)

        stringList = []
        for sublist in sortedData:
            ndx = 0
            for tup in sublist:
                if tup.isdigit():
                    str = ','.join(list(tup))
                    if (len(stringList)-1 < ndx)
                        stringList.append(str)
                    else:
                        stringList[ndx] += str
                    ndx += 1
            writer.writerow(stringList)
    finally:
        f.close()

    return

def plotData(name, bandmap, data)
    #determine number of plots needed from eff blocks
    #plot eff first
    #plot loss 100MHz from eff data edges
    #plot band edges if they are in the plotted loss data range
    #save plot to file
    return



#stuffs
name = sys.argv[1]
bandmap = []
data = []
for i in range(2, len(sys.argv)):
    if sys.argv[i].isdigit():
        bandmap.append(sys.argv[i])
    else:
        f = open(sys.argv[i], 'rt')
        data.append(dataParse(f))

writeData(name, data)
plotData(name, bandmap, data)
