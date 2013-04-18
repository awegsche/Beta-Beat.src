#!/usr/bin/env pythonafs

from Numeric import *
from LinearAlgebra import *
import sys
from os import system
import math
from Numeric import *
#from pymadtable import madtable
from metaclass import twiss
from AllLists import *


#########################
def writeparams(deltafamilie):
#########################
    global variables
    g = open ('changeparameters', 'w')
    i=0
    for var in variables:
        g.write(var+' ='+ var+'+ ('+str(deltafamilie[i])+');\n')
        i +=1
    g.close()
    return



#########################
def justtwiss(deltafamilies):
#########################
    global dictionary
    print deltafamilies
    writeparams(deltafamilies)
    system('madx < job.iterate_couple.madx > scum')
    x=twiss('twiss_couple.dat', dictionary)
    x.Cmatrix()
    return x




dictionary={}
execfile('../mydictionary.py')
FullResponse={}   #Initialize FullResponse
variables=["v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23", "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31", "v32", "v33", "v34", "v35", "v36", "v37", "v38", "v39", "v40", "v41", "v42", "v43", "v44", "v45", "v46", "v47", "v48", "v49", "v50", "v51", "v52", "v53", "v54", "v55", "v56", "v57", "v58", "v59", "v60", "v61", "v62", "v63", "v64", "v65", "v66", "v67", "v68", "v69", "v70", "v71", "v72", "v73", "v74", "v75", "v76", "v77", "v78", "v79", "v80", "v81", "v82", "v83", "v84", "v85", "v86", "v87", "v88", "v89", "v90", "v91", "v92", "v93", "v94", "v95", "v96", "v97", "v98", "v99", "v100", "v101", "v102", "v103", "v104", "v105", "v106", "v107"]

delta1=zeros(len(variables))*1.0   #Zero^th of the variables
incr=ones(len(variables))*0.000022  #increment of variables (10mm bump)

FullResponse['incr']=incr           #Store this info for future use
FullResponse['delta1']=delta1       #"     "     "


for i in range(0,len(delta1)) : #Loop over variables
        delta=array(delta1)
        delta[i]=delta[i]+incr[i]
        FullResponse[variables[i]]=justtwiss(delta)

FullResponse['delta1']=delta1       #"     "     "
FullResponse['0']=justtwiss(delta1) #Response to Zero, base , nominal


pickle.dump(FullResponse,open('FullResponse_couple.Numeric','w'),-1)



