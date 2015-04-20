import os
import sys
import csv
import math
import mmap
import datetime
import smithplot
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.gridspec as gridspec
from PIL import Image
from numpy import array

plt.rcParams['font.family'] = 'AkkuratPro'
csv.register_dialect('semicolon', delimiter=';')
csv.register_dialect('touchstone', delimiter='\t')
colorMap = ['#0066cc', '#ff0000', '#f2b111', '#78aa42', '#833083', '#ff6600', '#7c757f']
             #blue      #red       #yellow    #green     #purple    #orange    #grey


def mathify(x,y):
#do math and return data in different formats

    if y != False: #special case for R&S formatted data
        logmag = 20*math.log10(math.hypot(x,y))
        reNormZ = (1-x**2-y**2)/((1-x)**2+y**2)
        imNormZ = 2*y/((1-x)**2+y**2)
    else:
        logmag = x
        reNormZ = None
        imNormZ = None

    swr = (1+pow(10,(logmag/20)))/(1-pow(10,(logmag/20)))
    mismatch = 10*math.log10(1-pow(pow(10,(logmag/20)),2))

    return (logmag, swr, mismatch, reNormZ, imNormZ)



def statify(x):
#do stats yo
    spacemap = []
    for i in range(0, len(x)-1):
        spacing = x[i+1] - x[i]
        spacemap.append(spacing)
    spacing = sum(spacemap)/len(spacemap)
    average = lambda y: sum(y) * 1.0 / len(y)
    variance = lambda y: map(lambda z: (z - average(y)) ** 2, y)
    stdev = math.sqrt(average(variance(spacemap)))

    return spacing, stdev



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
    numbertype = None
    try:
        search = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

        #the .sNp case, return loss
        if search.find('# Hz') != -1:
            datatype = 'loss'
            numbertype = 'complex'
            reader = csv.reader(f, dialect = 'touchstone')
            for row in reader:
                if not any('!' in s for s in row) and not any('#' in s for s in row):
                    freq = float(row[0])/1000000
                    re = float(row[1])
                    im = float(row[2])
                    (logmag, swr, mismatch, reNormZ, imNormZ) = mathify(re, im)
                    rawdata = (freq, logmag, swr, mismatch, reNormZ, imNormZ)
                    parsedData.append(rawdata)


        #the R&S case, return loss
        if search.find('freq') != -1:
            datatype = 'loss'
            numbertype = 'complex'
            reader = csv.reader(f, dialect = 'semicolon')
            for row in reader:
                if not any('freq' in s for s in row) and not any('#' in s for s in row):
                    freq = float(row[0])/1000000
                    re = float(row[1])
                    im = float(row[2])
                    (logmag, swr, mismatch, reNormZ, imNormZ) = mathify(re, im)
                    rawdata = (freq, logmag, swr, mismatch, reNormZ, imNormZ)
                    parsedData.append(rawdata)


        #the Agilent case, return loss
        if search.find('Frequency') != -1 and search.find('Efficiency') == -1:
            datatype = 'loss'
            reader = csv.reader(f)
            for row in reader:
                if not any('Frequency' in s for s in row) and not any('#' in s for s in row):
                    freq = float(row[0])/1000000
                    logmag = float(row[1])
                    (logmag, swr, mismatch, reNormZ, imNormZ) = mathify(logmag, False)
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
                    efficiency = 0
                #special case for data from ETS
                if any('Frequency  ' in s for s in row) and any('Total' in s for s in row):
                    row.remove('')
                    row.remove('Total')
                    row.remove('Frequency  (MHz)') #yeah, that's 2 spaces...
                    freq = [float(i) for i in row]
                    efficiency = 1
                if any('Efficiency (dB)' in s for s in row):
                    row.remove('')
                    row.remove('Efficiency (dB)')
                    if efficiency == 1:
                        row.remove('')
                    efficiency = [float(i) for i in row]
            #split efficiency blocks
            spacing, stdev = statify(freq)
            effmap = zip(freq, efficiency)
            effblock = []
            for i in range(0, len(effmap)-2):
                if effmap[i+1][0]-effmap[i][0] <= spacing+stdev:
                    effblock.append(effmap[i])
                else:
                    parsedData.append(effblock)
                    effblock = []
            effblock.append(effmap[len(effmap)-1])
            parsedData.append(effblock)

    finally:
        f.close()

    return (parsedData, datatype, numbertype)



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

    f = open(save(name + '_parsedData', 'csv'), 'wt')
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

def plotData(name, bandmap, data, sbs):
#use matplotlib to spit out data

    bandmap.sort()
    ncolors = len(colorMap)
    badData = ['', 'eff', 'loss']
    dataFlag = sbs

    plt.style.use('fivethirtyeight')
    fig1 = plt.figure(num = None, figsize = (12 * (sbs+1),9), dpi = 80, facecolor = 'w', edgecolor = 'k')
    fig1.suptitle(name, fontsize = 20)
    #fig1.suptitle(name + ' Isolation', fontsize = 20)
    if sbs > 0:
        fig1.text(0.28, 0.92, 'Return Loss', horizontalalignment = 'center', fontsize = 18)
        fig1.text(0.75, 0.92, 'Efficiency', horizontalalignment = 'center', fontsize = 18)
        fig1.text(0.28, 0.11, 'Frequency (MHz)', horizontalalignment = 'center', verticalalignment = 'top',  fontsize = 16)
        fig1.text(0.75, 0.11, 'Frequency (MHz)', horizontalalignment = 'center', verticalalignment = 'top',  fontsize = 16)
    else:
        fig1.text(0.5, 0.11, 'Frequency (MHz)', horizontalalignment = 'center', verticalalignment = 'top',  fontsize = 16)
    gs0 = gridspec.GridSpec(1, sbs+1, bottom = 0.15)

    if len(bandmap) > 2:
    #CASE1: the case where we have bandedges to plot
        numSubplots = len(bandmap)/2
        gs00 = gridspec.GridSpecFromSubplotSpec(1, numSubplots, gs0[0, 0])

        for figs in range(0, sbs+1):
            ndx = 0
            axs = [None] * numSubplots
            for plots in data:
                if plots[1] == 'loss' and plots[1] != badData[dataFlag]:
                    x = [point[0] for point in plots[0]] #point[0] is frequency values
                    y = [point[1] for point in plots[0]] #point[1] is return loss values
                    for i in range(0, numSubplots):
                        if i > 0:
                            axs[i] = plt.subplot(gs00[0, i], sharey = axs[0])
                            plt.setp(axs[i].get_yticklabels(), visible=False)
                        else:
                            axs[i] = plt.subplot(gs00[0, i])
                            if sbs > 0:
                                axs[i].set_ylabel('Return Loss (dB)')
                        axs[i].plot(x, y, color = colorMap[ndx])
                    ndx = (ndx + 1) % ncolors #shift to next color, but make sure it's in range
                if plots[1] == 'eff' and plots [1] != badData[dataFlag]:
                    for blocks in plots[0]:
                        x = [point[0] for point in blocks]
                        y = [point[1] for point in blocks]
                        for i in range(0, numSubplots):
                            if i > 0:
                                axs[i] = plt.subplot(gs00[0, i], sharey = axs[0])
                                plt.setp(axs[i].get_yticklabels(), visible=False)
                            else:
                                axs[i] = plt.subplot(gs00[0, i])
                                if sbs > 0:
                                    axs[i].set_ylabel('Efficiency (dB)')
                            axs[i].plot(x,y, color = colorMap[ndx])
                    ndx = (ndx + 1) % ncolors #shift to next color, but make sure it's in range

            #plot the bandedges and set the subplot limits
            ndx = 0
            for i in range(0, numSubplots):
                axs[i].axvline(bandmap[ndx], color = '#000000', linewidth = 2, linestyle = ':')
                axs[i].axvline(bandmap[ndx+1], color = '#000000', linewidth = 2, linestyle = ':')
                axs[i].set_xlim(bandmap[ndx]-100, bandmap[ndx+1]+100)
                x1, x2, y1, y2 = axs[i].axis()
                axs[i].axis([x1, x2, -18, 0])
                axs[i].grid(True)
                ndx += 2

            if sbs > 0:
                gs00 = gridspec.GridSpecFromSubplotSpec(1, numSubplots, gs0[0, 1])
                dataFlag += 1
            else:
                axs[0].set_ylabel('Return Loss/Efficiency (dB)')


    else:
    #CASE2: the case where there are 2 bandedges or they are undefined, just plot everything

        for figs in range(0, sbs+1):
            ndx = 0
            for plots in data:
                if plots[1] == 'loss' and plots[1] != badData[dataFlag]:
                    x = [point[0] for point in plots[0]] #point[0] is frequency values
                    y = [point[1] for point in plots[0]] #point[1] is return loss values
                    ax = plt.subplot(gs0[0, 0])
                    ax.plot(x, y, color = colorMap[ndx])
                    ax.set_ylabel('Return Loss (dB)')
                    ndx = (ndx + 1) % ncolors #shift to next color, but make sure it's in range
                if plots[1] == 'eff' and plots[1] != badData[dataFlag]:
                    for blocks in plots[0]:
                        x = [point[0] for point in blocks]
                        y = [point[1] for point in blocks]
                        ax = plt.subplot(gs0[0,sbs])
                        ax.plot(x, y, color = colorMap[ndx])
                        ax.set_ylabel('Efficiency (dB)')
                    ndx = (ndx + 1) % ncolors #shift to next color, but make sure it's in range

            if len(bandmap) > 1: #just in case there's 2 bandedges to plot
                plt.axvline(bandmap[0], color = '#000000', linewidth = 2, linestyle = ':')
                plt.axvline(bandmap[1], color = '#000000', linewidth = 2, linestyle = ':')
                ax.set_xlim(bandmap[0]-100, bandmap[1]+100)
            x1, x2, y1, y2 = plt.axis()
            plt.axis([x1, x2, -18, 0])
            plt.grid(True)

            if sbs > 0:
                dataFlag += 1
            else:
                ax.set_ylabel('Return Loss/Efficiency (dB)')


    #grey bottom bar
    bottomBar = patches.Rectangle((0,0), 1, 0.04, color = '#666666', transform = fig1.transFigure) #, zorder = 2)
    fig1.patches.append(bottomBar)
    today = str(datetime.datetime.now().date())
    fig1.text(0.99, 0.015, 'Nest Labs Condfidential, ' + today, horizontalalignment = 'right', fontsize = 12, color = '#cccccc')
    logo = Image.open('logo.png')
    logoHeight = int(round(fig1.get_figheight() * fig1.dpi * 0.038))
    logoWidth = int(round(logo.size[0] * logoHeight / logo.size[1]))
    logoOffsetW = fig1.get_figwidth() * fig1.dpi * 0.007
    logoOffsetH = fig1.get_figheight() * fig1.dpi * 0.004
    logo = logo.resize((logoWidth, logoHeight))
    fig1.figimage(logo, logoOffsetW, logoOffsetH, zorder = 1)

    #save plot to file
    plt.savefig(save(name, 'png'))
    plt.show()
    return



def plotSmith(name, bandmap, data):
#use matplotlib and smithplot to spit out data

    bandmap.sort()
    ncolors = len(colorMap)

    fig1 = plt.figure(num = None, figsize = (9, 9), dpi = 80, facecolor = 'w', edgecolor = 'k')
    fig1.suptitle(name, fontsize = 20)
    ax = plt.subplot(1, 1, 1, projection = 'smith', plot_hacklines = False)
    plt.gca().update_scParams(plot_startmarker = None, plot_endmarker = None)

    ndx = 0
    for plots in data:
        if plots[1] == 'loss' and plots[2] == 'complex':
            markers = []
            complexnums = array([(point[4] + point[5] * 1j) for point in plots[0]])
            plt.plot(complexnums, marker=None, color = colorMap[ndx])
            if len(bandmap) > 0:
                for bandpoint in bandmap:
                    previous = None
                    for point in range(0, len(plots[0])):
                        if plots[0][point][0] <= bandpoint:
                            previous = plots[0][point][4] + plots[0][point][5] * 1j
                        else:
                            break
                    markers.append(previous)
                markers = array(markers)
                plt.plot(markers, marker='o', linewidth = 0, color = colorMap[ndx])
            ndx = (ndx + 1) % ncolors #shift to next color, but make sure it's in range

    #save plot to file
    plt.savefig(save(name, 'png'))
    plt.show()
    return



#stuffs
name = sys.argv[1]
bandmap = []
data = []
sbs = 0
smith = 0

for i in range(2, len(sys.argv)):
    if sys.argv[i].isdigit():
        bandmap.append(sys.argv[i])
    elif sys.argv[i] == '-sbs' or sys.argv[i] == '--sidebyside':
        sbs = 1
    elif (sys.argv[i] == '-s' or sys.argv[i] == '--smith') and sbs == 0:
        smith = 1
    else:
        #if i > 2 and i % 2 != 1:
        #    raise Exception("ENTERED AN ODD NUMBER OF BAND EDGES!!!")
        f = open(sys.argv[i], 'rt')
        data.append(dataParse(f))

bandmap = map(int, bandmap)
writeData(name, data)
if smith == 0:
    plotData(name, bandmap, data, sbs)
else:
    plotSmith(name, bandmap, data)
