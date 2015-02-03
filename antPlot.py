import os
import sys
import csv
import math
import mmap
import matplotlib.pyplot as plt

csv.register_dialect('semicolon', delimiter=';')
plt.style.use('fivethirtyeight')
plt.rcParams['font.family'] = 'AkkuratPro'



def mathify(x,y):
#do math and return data in different formats

    if y != False: #special case for R&S formatted data
        logmag = 20*math.log10(math.hypot(x,y))
    else:
        logmag = x

    swr = (1+pow(10,(logmag/20)))/(1-pow(10,(logmag/20)))
    mismatch = 10*math.log10(1-pow(pow(10,(logmag/20)),2))

    return (logmag, swr, mismatch)



def save(name, ext):
#generate a save file path

    tempPath = os.path.dirname(os.path.realpath(sys.argv[len(sys.argv)-1]))+'/'+name
    directory = os.path.split(tempPath)[0]
    filename = '%s.%s' % (os.path.split(tempPath)[1], ext)
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
                if not any('freq' in s for s in row) and not any('#' in s for s in row):
                    freq = float(row[0])/1000000
                    re = float(row[1])
                    im = float(row[2])
                    (logmag, swr, mismatch) = mathify(re, im)
                    rawdata = (freq, logmag, swr, mismatch)
                    parsedData.append(rawdata)


        #the Agilent case, return loss
        if search.find('Frequency') != -1 and search.find('Efficiency') == -1:
            datatype = 'loss'
            reader = csv.reader(f)
            for row in reader:
                if not any('Frequency' in s for s in row) and not any('#' in s for s in row):
                    freq = float(row[0])/1000000
                    logmag = float(row[1])
                    (logmag, swr, mismatch) = mathify(logmag, False)
                    rawdata = (freq, logmag, swr, mismatch)
                    parsedData.append(rawdata)


        #the Efficiency case
        if search.find('Efficiency') != -1:
            datatype = 'eff'
            reader = csv.reader(f)
            for row in reader:
                if any('Frequency' in s for s in row) and any('Point' in s for s in row):
                    row.remove('Point Values')
                    row.remove('Frequency (MHz)')
                    freq = [float(i) for i in row]
                if any('Efficiency (dB)' in s for s in row):
                    row.remove('')
                    row.remove('Efficiency (dB)')
                    efficiency = [float(i) for i in row]
            #split efficiency blocks
            spacing = freq[1] - freq[0]
            effmap = zip(freq, efficiency)
            effblock = []
            for i in range(0, len(effmap)-2):
                if effmap[i+1][0]-effmap[i][0] == spacing:
                    effblock.append(effmap[i])
                else:
                    parsedData.append(effblock)
                    effblock = []
            effblock.append(effmap[len(effmap)-1])
            parsedData.append(effblock)

    finally:
        f.close()

    return (parsedData, datatype)



def writeData(name, data):
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

    f = open(save(name, 'csv'), 'wt')
    try:
        writer = csv.writer(f)
        writer.writerow(header)

        stringList = []
        for sublist in sortedData:
            ndx = 0
            for tup in sublist:
                if 'eff' not in tup and 'loss' not in tup:
                    rowstr = map(str, list(tup))
                    if (len(stringList)-1 < ndx):
                        stringList.append(rowstr)
                    else:
                        stringList[ndx] += rowstr
                    ndx += 1
        for row in stringList:
            writer.writerow(row)
    finally:
        f.close()

    return

def plotData(name, bandmap, data):
#use matplotlib to spit out data

    bandmap.sort()
    ncolors = len(plt.rcParams['axes.color_cycle'])

    if len(bandmap) > 1:
    #the case where we have bandedges to plot
        numSubplots = len(bandmap)/2

        fig1, axs = plt.subplots(1, numSubplots, sharey = True, figsize = (12,9), dpi = 80, facecolor = 'w', edgecolor = 'k')
        fig1.suptitle(name + ' Return Loss and Efficiency', fontsize = 20)
        axs[0].set_ylabel('Return Loss/Efficiency (dB)')
        fig1.text(0.5, 0.03, 'Frequency (MHz)', horizontalalignment = 'center', verticalalignment = 'top',  fontsize = 16)


        ndx = 0
        for plots in data:
            if plots[1] == 'loss':
                x = [point[0] for point in plots[0]] #point[0] is frequency values
                y = [point[1] for point in plots[0]] #point[1] is return loss values
                for i in range(0, numSubplots):
                    axs[i].plot(x, y, color = plt.rcParams['axes.color_cycle'][ndx])
                ndx = (ndx + 1) % ncolors #shift to next color, but make sure it's in range
            if plots[1] == 'eff':
                for blocks in plots[0]:
                    x = [point[0] for point in blocks]
                    y = [point[1] for point in blocks]
                    for i in range(0, numSubplots):
                        axs[i].plot(x,y, color = plt.rcParams['axes.color_cycle'][ndx])
                ndx = (ndx + 1) % ncolors #shift to next color, but make sure it's in range

        #plot the bandedges and set the subplot limits
        ndx = 0
        for i in range(0, numSubplots):
            axs[i].axvline(bandmap[ndx], color = '#808080', linewidth = 2, linestyle = ':')
            axs[i].axvline(bandmap[ndx+1], color = '#808080', linewidth = 2, linestyle = ':')
            axs[i].set_xlim(bandmap[ndx]-100, bandmap[ndx+1]+100)
            x1, x2, y1, y2 = axs[i].axis()
            axs[i].axis([x1, x2, -18, 0])
            axs[i].grid(True)
            ndx += 2


    else:
    #the case where bandedges are undefined, just plot everything
        fig1 = plt.figure(num = None, figsize = (12,9), dpi = 80, facecolor = 'w', edgecolor = 'k')
        plt.title(name + ' Return Loss and Efficiency', fontsize = 20)
        plt.xlabel('Frequency (dB)')
        plt.ylabel('Return Loss/Efficiency (dB)')


        ndx = 0
        for plots in data:
            if plots[1] == 'loss':
                x = [point[0] for point in plots[0]] #point[0] is frequency values
                y = [point[1] for point in plots[0]] #point[1] is return loss values
                plt.plot(x, y, color = plt.rcParams['axes.color_cycle'][ndx])
                ndx = (ndx + 1) % ncolors #shift to next color, but make sure it's in range
            if plots[1] == 'eff':
                for blocks in plots[0]:
                    x = [point[0] for point in blocks]
                    y = [point[1] for point in blocks]
                    plt.plot(x,y)
                ndx = (ndx + 1) % ncolors #shift to next color, but make sure it's in range

        x1, x2, y1, y2 = plt.axis()
        plt.axis([x1, x2, -18, 0])
        plt.grid(True)


    #print plt.rcParams['axes.color_cycle']
    #save plot to file
    plt.savefig(save(name, 'png'))
    plt.show()
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

bandmap = map(int, bandmap)
writeData(name, data)
plotData(name, bandmap, data)
