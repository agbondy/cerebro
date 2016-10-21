#SETUP
from __future__ import print_function
import pandas as pd
from pandas import DataFrame, read_csv,to_timedelta
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import shutil


def parseMeterFile(sourceName):
    saveName = sourceName[:-4] #remove .txt
    index = saveName.find("LD")
    index2 = saveName.find("_")
    LD = saveName[index+2:index2]
    with open(sourceName,'r') as txtfile:
        txtlines = txtfile.readlines()[1:]
    vec = []
    for i in txtlines:
        start = i.find('\t')
        if i[start+1]=='-':
            a=1
        else:
            a=0
        val = 1000*float(i[start:start+6])*10**float(i[start+8+a:-3])
        vec.append(val)
    return LD,vec,saveName

def getPeaks(vec):
    #################################
    threshold = max(vec[:50])*4 ##
    #################################
    j=len(vec)-1
    indices = []
    vals = []
    while (j>1):
        if vec[j-10] - vec[j-80]<.02 and abs(vec[j]-vec[j-10])>threshold:
            indices.append(j-175)
            vals.append(vec[j-175])
            j-=1000
        j-=1
    return indices,vals,threshold



def getCalibration(desired,xVec,yVec):
    loop = 0
    for i in yVec:
        if i>desired:
            slope = (yVec[loop]-yVec[loop-1])/(xVec[loop]-xVec[loop-1])
            b = yVec[loop]-xVec[loop]*slope
            return int(round((desired-b)/slope))
        loop+=1

def rawGraph(vec,_peakIndices,_peakVals,LD):
    plt.subplot(2,1,1)
    plt.plot(vec)
    plt.scatter(_peakIndices,_peakVals,color='red')


    title = "LD{} Raw Power Meter Data".format(LD)
    ylabel = "Power (mW)"
    xlabel = 'Sample #'
    plt.title(title,fontsize=20)
    plt.ylabel(ylabel)
    plt.xlabel(xlabel)
    plt.ylim(0,45)
    plt.xlim(0,150000)

def calibrationCurve(_peakVals,wantedLevel,LD):
    fig = plt.gcf()
    ax1 = fig.add_subplot(212)
    fig.subplots_adjust(bottom=0.2)
    ax1.set_ylim(0,45)
    ax1.set_xlim(450,1050)
    #http://stackoverflow.com/questions/31803817/how-to-add-second-x-axis-at-the-bottom-of-the-first-one-in-matplotlib
    ax2 = ax1.twiny()
    new_tick_locations = np.array(ax1.get_xticks())/1023.0*4.2
    print (new_tick_locations)
    ax2.set_xticks(new_tick_locations)
    ax2.set_xticklabels(np.round(new_tick_locations,1))
    ax2.set_xlim(np.array(ax1.get_xlim())/1023.0*4.2)
    ax2.set_xlabel("Photocell Voltage (V)")
    # Move twinned axis ticks and label from top to bottom
    ax2.xaxis.set_ticks_position("bottom")
    ax2.xaxis.set_label_position("bottom")
    # Offset the twin axis below the host
    ax2.spines["bottom"].set_position(("axes", -0.15))


    lightOut = _peakVals[::-1]
    softVals = []
    for i in range(500,751,50):
        softVals.append(i)
    for i in range(760,901,10):
        softVals.append(i)
    for i in range(905,1026,5):
        softVals.append(i)

    trimmedSoftVals = softVals[:len(lightOut)]

    ax1.scatter(trimmedSoftVals,lightOut,s=50) #plot points
    ax1.plot(trimmedSoftVals,lightOut,'--')    #connect points with dashed line
    calibration =  getCalibration(wantedLevel,trimmedSoftVals,lightOut) #get calibrated value
    ax1.scatter(calibration,wantedLevel,color="red",s=50) #plot calibrated value
    ax1.set_title("LD{} Characterization Curve".format(LD),fontsize=20)
    ylabel = "Power (mW)"
    ax1.set_ylabel(ylabel)
    ax1.set_xlabel("powerLevel variable")
    plt.figtext(.5,0,
                "For {} mW the calibration value is {}".format(wantedLevel,calibration),
                fontsize=30,
                ha='center',
                va='bottom')
    return trimmedSoftVals,lightOut

def saveGraphs(_sourceName,_saveName,bokehGraph):
    # save graphs to local directory
    if not os.path.exists('Calibrations/{}'.format(_saveName)):
        os.makedirs('Calibrations/{}'.format(_saveName))
    plt.savefig("Calibrations/{0}/{0}_graph.png".format(_saveName),bbox_inches='tight')
    plt.savefig("Calibrations/Graphs/{0}_graph.png".format(_saveName),bbox_inches='tight')
    shutil.copy(_sourceName,'Calibrations/{}'.format(_saveName)) #put a copy of the .txt log file in the local folder

def saveSummary(_saveName,_wantedLevel,_trimmedSoftVals,lightOut,LD):
    ######### Write summary to file###################
    target = open("{0}_summary.txt".format(_saveName), 'w')
    for i in range(len(_trimmedSoftVals)):
        target.write("{},{}\n".format(_trimmedSoftVals[i],lightOut[i]))
    waveform = np.linspace(_wantedLevel,0,num=100)
    vals = [getCalibration(i,_trimmedSoftVals,lightOut) for i in waveform ]
    target.write("***\n")
    target.write("LD{} {}mW\n".format(LD,_wantedLevel))
    for i in range(len(vals)):
        target.write("{}".format(vals[i]))
        #if i != 0:
        if not((i+1)%5):
            target.write("\n")
        else:
            target.write(",")
    powerTable = range(_wantedLevel*10,-1,-1)
    vals = [getCalibration(i/10.0,_trimmedSoftVals,lightOut) for i in powerTable ]
    target.write("\n")
    for i in range(len(vals)):
    #     print powerTable[i]/10.0,vals[i]
        target.write("{},{}\n".format(powerTable[i]/10.0,vals[i]))
    target.close()

def fitLine2Graph(trimmedSoftVals,lightOut):
    coefficients = np.polyfit(trimmedSoftVals,lightOut,5)
    f = np.poly1d(coefficients)
    plt.plot(trimmedSoftVals,f(trimmedSoftVals),'r')
    print (coefficients)

def showCalVal(showVal):
    print ("For {} mW the calibration value is {}".format(showVal,getCalibration(showVal,trimmedInputs,lightout)))

def getCalVector(wantedLevel,LD,trimmedInputs,lightout):
	waveform = np.linspace(wantedLevel,0,num=100)
	vals = [getCalibration(i,trimmedInputs,lightout) for i in waveform ]

	for i in range(len(vals)):
		print (vals[i],end="")
		#if i != 0:
		if not((i+1)%5):
			print ("")
		else:
			print (",",end="")