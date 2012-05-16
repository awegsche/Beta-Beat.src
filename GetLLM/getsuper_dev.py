
###### imports
from optparse import OptionParser
from metaclass import twiss
import os,sys,shutil,commands
from math import sqrt,cos,sin,pi,atan2
from datetime import date
from linreg import *

##
# YIL changes v 3.1:
#  - Cleaned macro writer in madcreator
#  - modifiers.madx should be in options.output
#


def parse_args():
    ###### optionparser
    usage = "usage: %prog [options] sdds-file1 [sdds-file2 ...]"
    parser = OptionParser(usage)
    # general
    parser.add_option("-m", "--twiss",
            help="twiss files to use",
            metavar="twiss", default="./", dest="twiss")
    parser.add_option("-o", "--output",
            help="output path, where to store the results",
            metavar="<path>", default="./", dest="output")
    parser.add_option("-b", "--beta",
            help="where beta-beat is stored",
            metavar="<path>", default="/afs/cern.ch/eng/sl/lintrack/Beta-Beat.src/", dest="brc")
    parser.add_option("-t", "--algorithm",
            help="Which algorithm to use (SUSSIX/SVD)",
            metavar="ALGORITHM", default="SUSSIX", dest="technique")
    parser.add_option("-a", "--accel",
            help="Which accelerator: LHCB1 LHCB2 SPS RHIC",
            metavar="ACCEL", default="LHCB1",dest="accel")
    parser.add_option("", "--qx",
        help="Fractional horizontal tune",
        metavar="<value>", type="float", default="0.31",dest="qx")
    parser.add_option("", "--qy",
            help="Fractional vertical tune",
            metavar="<value>", type="float", default="0.32",dest="qy")
    parser.add_option("", "--qdx",
            help="AC dipole driven horizontal tune",
            metavar="<value>", type="float", default="0.304",dest="qdx")
    parser.add_option("", "--qdy",
            help="AC dipole driven vertical tune",
            metavar="<value>", type="float", default="0.326",dest="qdy")
    parser.add_option("", "--llm_version",
            help="Run with specific version of GetLLM.py",
            metavar="<version>", default=None,dest="llm_version")

    return parser.parse_args()



def check_input(options,args):
    if len(args)==0:
        raise SyntaxError("You need to define at least one file input")
    for f in args:
        if not os.path.isfile(f):
            raise ValueError(f+' does not exist')


## ############
#functions
## ############


#####
def madcreator(dpps,options):

    madfile=options.brc+"/MODEL/LHCB/model/"

    linesmad=open(madfile+"/job.twiss_chrom.madx.macro","r").read()


    # creating the DPP
    dppstring=''
    dppstring_ac=''
    for dpp in dpps:
        if (os.path.exists(options.output+'/twiss_'+str(dpp)+'.dat')==False):
            dppstring=dppstring+'twiss, chrom,sequence='+options.accel+', deltap='+str(dpp)+', file="'+options.output+'/twiss_'+str(dpp)+'.dat";\n'
            dppstring_ac=dppstring_ac+'twiss, chrom,sequence='+options.accel+', deltap='+str(dpp)+', file="'+options.output+'/twiss_'+str(dpp)+'_ac.dat";\n'
    
    if not dppstring:
        print "No need to run madx"
        return 0

    DPP=dppstring
    DP_AC_P=dppstring_ac
    ACCEL=options.accel
    if options.accel=='LHCB1':
        BEAM='B1'
    elif options.accel=='LHCB2':
        BEAM='B2'
    else:
        print "WARNING: Could not decide what BEAM should be"
    QX=options.qx
    QY=options.qy
    QDX=options.qdx
    QDY=options.qdy
    QMX=int(options.qx*100)
    QMY=int(options.qy*100)
    STOP='!'

    for testpath in [options.output,options.twiss]:
        _tmpmod=os.path.join(testpath,'modifiers.madx')
        if os.path.isfile(_tmpmod):
            print "INFO: Using",_tmpmod
            MODIFIERS=_tmpmod
            break

    print "Creating madx"
    filetoprint=open(options.output+"/job.chrom.madx","w")


    #changing variables
    filetoprint.write(linesmad % locals())

    filetoprint.close()
    print "Running madx"
    if os.system('madx < '+options.output+'/job.chrom.madx'):
        raise ValueError("Mad-X failed")

###running getllm
def append(files):
    filestring="empty"

    for filee in files:
        filestring=filestring+","+filee

    return filestring.replace("empty,","")

def rungetllm(twissfile,accel,technique,files,options,dpp):
    if options.llm_version:
        print "GetLLM_V"+options.llm_version+" as GetLLM"
        exec("import GetLLM_V"+options.llm_version+" as GetLLM")
    else:
        if __file__.split('.')[-2][-4:]=='_dev':
            import GetLLM_dev as GetLLM
        else:
            import GetLLM

    print "Will run getllm for ",dpp #, command
    
    GetLLM.main(outputpath=options.output,
                files_to_analyse=append(files),
                twiss_model_file=twissfile,
                accel=accel,
                TBTana=technique)
    print "GetLLM finished"

    for var in ['betax','betay','ampbetax','ampbetay','couple','betax_free','betay_free','couple_free']:
        shutil.copy(options.output+'/get'+var+'.out',options.output+'/get'+var+'_'+str(dpp)+'.out')


##### for chromatic
# model intersect
def modelIntersect(expbpms, model):

    bpmsin=[]
    for bpm in expbpms:
        try:
            check=model.indx[bpm[1].upper()]
            bpmsin.append(bpm)
        except:
            print bpm, "Not in Model"
    if len(bpmsin)==0:
        print "Zero intersection of Exp and Model"
        print "Please, provide a good Dictionary"
        print "Now we better leave!"
        sys.exit()
    return bpmsin


#intersect
def intersect(ListOfFile):
    '''Pure intersection of all bpm names in all files '''
    if len(ListOfFile)==0:
        print "Nothing to intersect!!!!"
        sys.exit()
    z=ListOfFile[0].NAME
    for b in ListOfFile:
        z=filter(lambda x: x in z   , b.NAME)
    #SORT by S
    result=[]
    x0=ListOfFile[0]
    for bpm in z:
        result.append((x0.S[x0.indx[bpm]], bpm))

    result.sort()
    return result

#linreg
def dolinregbet(filetoprint,listx,listy,bpms,plane,value,zero,twiss):
    for bpm in bpms:
        el=bpm[1]
        sloc=bpm[0]
        indx=[]
        b=[]
        a=[]
        bm=[]
        am=[]
        if "H" in plane:
            beta0=zero.BETX[zero.indx[el]]
            alfa0=zero.ALFX[zero.indx[el]]
            alfa0err=zero.STDALFX[zero.indx[el]]

            beta0m=twiss.BETX[twiss.indx[el]]
            alfa0m=twiss.ALFX[twiss.indx[el]]

            wmo=twiss.WX[twiss.indx[el]]
            pmo=twiss.PHIX[twiss.indx[el]]
        else:

            beta0=zero.BETY[zero.indx[el]]
            alfa0=zero.ALFY[zero.indx[el]]
            alfa0err=zero.STDALFY[zero.indx[el]]

            beta0m=twiss.BETY[twiss.indx[el]]
            alfa0m=twiss.ALFY[twiss.indx[el]]

            wmo=twiss.WY[twiss.indx[el]]
            pmo=twiss.PHIY[twiss.indx[el]]
        for dpp in listx:
            file=listy[dpp]
            ix=file.indx[el]
            indx.append(ix)
            if "H" in plane:
                b.append(file.BETX[ix])
                a.append(file.ALFX[ix])

                bm.append(file.BETXMDL[file.indx[el]])
                am.append(file.ALFXMDL[file.indx[el]])
            else:
                b.append(file.BETY[ix])
                a.append(file.ALFY[ix])

                bm.append(file.BETYMDL[file.indx[el]])
                am.append(file.ALFYMDL[file.indx[el]])

        bfit=linreg(listx, b)
        afit=linreg(listx, a)

        bfitm=linreg(listx, bm)
        afitm=linreg(listx, am)

        # measurement
        dbb=bfit[0]/beta0
        dbberr=bfit[3]/beta0
        da=afit[0]
        daerr=afit[3]
        A=dbb
        Aerr=dbberr
        B=da-alfa0*dbb
        Berr=sqrt(daerr**2 + (alfa0err*dbb)**2 + (alfa0*dbberr)**2)
        w=sqrt(A**2+B**2)
        werr=sqrt( (Aerr*A/w)**2 + (Berr*B/w)**2  )
        phi=atan2(B,A)/2./pi
        phierr=1./(1.+(A/B)**2)*sqrt( (Aerr/B)**2 + (A/B**2*Berr)**2)/2./pi

        #model
        dbbm=bfitm[0]/beta0m
        dbberrm=bfitm[3]/beta0m
        dam=afitm[0]
        daerrm=afitm[3]
        Am=dbbm
        Aerrm=dbberrm
        Bm=dam-alfa0m*dbbm
        Berrm=sqrt(daerrm**2 + (alfa0m*dbberrm)**2)
        wm=sqrt(Am**2+Bm**2)
        werrm=sqrt( (Aerrm*Am/wm)**2 + (Berrm*Bm/wm)**2  )
        phim=atan2(Bm,Am)/2./pi
        phierrm=1./(1.+(Am/Bm)**2)*sqrt( (Aerrm/Bm)**2 + (Am/Bm**2*Berrm)**2)/2./pi


        print >>filetoprint, el, sloc,  dbb, dbberr, da, daerr, w, werr, wmo,phi, phierr,pmo, dbbm,dbberrm,dam,daerrm,wm, werrm,phim,phierrm
    filetoprint.close()

### for coupling
# get det(C)
def getC(couplefile,name):


    f1001R=couplefile.F1001R[couplefile.indx[name]]
    f1001I=couplefile.F1001I[couplefile.indx[name]]
    f1010R=couplefile.F1010R[couplefile.indx[name]]
    f1010I=couplefile.F1010I[couplefile.indx[name]]

    down=4*((complex(f1001R,f1001I))-(complex(f1010R,f1010I)))
    c=1-(1/(1+down))

    cr=c.real
    ci=c.imag

    return cr,ci

# linreg for coupling
def dolinregCoupling(couplelist,bpms,dpplist,filetoprint,model):


    for bpm in bpms:

        name=bpm[1]
        s=bpm[0]

        a=[]
        br=[]
        bi=[]

        for dpp in dpplist:

            cr,ci=getC(couplelist[dpp],name)

            a.append(dpp)
            br.append(cr)
            bi.append(ci)
            
        fitr=linreg(a,br)
        fiti=linreg(a,bi)

        c=abs(complex(fitr[0],fiti[0]))
        e=abs(complex(fitr[3],fiti[3]))

        print >> filetoprint,name,s,c,e,"0"


def main(options,args):

    ## ##############
    #   main
    ## ##############

    files=args[:]

    if not os.path.isdir(options.output):
        os.makedirs(options.output)
    accel=options.accel
    technique=options.technique

    fileslist={}

    for f in files:

        datax=twiss(f+"_linx")
        datay=twiss(f+"_liny")
        dppx=datax.DPP
        dppy=datay.DPP

        if dppx!=dppy:
            raise ValueError("Discrepancy between horizontal and vertical => "+str(dppx)+" "+str(dppy))
        else:
            dpp=dppx/1.0

        if dpp not in fileslist:
            print "Adding dpp",dpp
            fileslist[dpp]=[f]
        else:
            fileslist[dpp].append(f)


    if 0 not in fileslist:
        raise ValueError("NO DPP=0.0")

    madcreator(fileslist.keys(),options)
    print "All models are created"
    for dpp in fileslist:
        files=fileslist[dpp]
        rungetllm(options.output+"/twiss_"+str(dpp)+".dat",accel,technique,files,options,dpp)


    ##adding data
    betalistx={}
    betalisty={}
    couplelist={}
    betalistxf={}
    betalistyf={}
    couplelistf={}

    listx=[]
    listxf=[]
    listy=[]
    listyf=[]
    listc=[]
    listcf=[]

    try:
        twiss(options.output+'/getbetax_free_'+str(dpp)+'.out')
        freeswitch=1
    except:
        freeswitch=0


    for dpp in fileslist.keys():
        print "Loading driven data for ",dpp
        betx=twiss(options.output+'/getbetax_'+str(dpp)+'.out')
        bety=twiss(options.output+'/getbetay_'+str(dpp)+'.out')
        couple=twiss(options.output+'/getcouple_'+str(dpp)+'.out')
        #couple=twiss(options.output+'/getbetay_'+str(dpp)+'.out')
        betalistx[dpp]=betx
        betalisty[dpp]=bety
        couplelist[dpp]=couple

        if float(dpp)==0.0:
            zerobx=betx
            zeroby=bety

        listx.append(betx)
        listy.append(bety)
        listc.append(couple)
        modeld=twiss(options.twiss+"/twiss.dat")

        #try:
        if freeswitch==1:
            print "Loading free data"
            freeswitch=1
            print 'getbetax_free_'+str(dpp)+'.out'
            betxf=twiss(options.output+'/getbetax_free_'+str(dpp)+'.out')
            betyf=twiss(options.output+'/getbetay_free_'+str(dpp)+'.out')
            couplef=twiss(options.output+'/getcouple_free_'+str(dpp)+'.out')
            betalistxf[dpp]=betxf
            betalistyf[dpp]=betyf
            couplelistf[dpp]=couplef
            listxf.append(betxf)
            listyf.append(betyf)
            listcf.append(couplef)
            modeld=twiss(options.twiss+"/twiss_ac.dat")
            modelf=twiss(options.twiss+"/twiss.dat")
            if float(dpp)==0.0:
                zerobxf=betalistxf[dpp]
                zerobyf=betalistyf[dpp]


        #except:
         #       print "No free data"

    #
    # driven beta
    #

    print "Driven beta"

    #H
    filefile=open(options.output+"/chrombetax.out","w")
    print >>filefile, "* NAME", "S",  "dbb", "dbberr", "dalfa", "daerr", "WX","WXERR","WMO","PHIX", "PHIXERR","PHIM", "dbbR", "dbberrR", "dalfaR", "daerr","WXR","WXERRR","PHIXR", "PHIXERRR"
    print >>filefile, "$ %s  %le  %le  %le  %le  %le %le %le %le  %le %le  %le %le  %le %le  %le %le %le  %le %le  %le"

    bpms=intersect(listx)
    bpms=modelIntersect(bpms,modeld)
    dolinregbet(filefile,fileslist.keys(),betalistx,bpms,"H","beta",zerobx,modeld)
    filefile.close()

    #V
    filefile=open(options.output+"/chrombetay.out","w")
    print >>filefile, "* NAME", "S",  "dbb", "dbberr", "dalfa", "daerr", "WY", "WYERR","WYM","PHIY",  "dbbR", "dbberrR", "dalfaR", "daerr","PHIYERR","PHIM", "WYR","WYERRR","PHIYR", "PHIYERRR"
    print >>filefile, "$ %s  %le  %le  %le  %le  %le %le %le %le  %le %le %le %le  %le %le %le %le  %le %le %le"

    bpms=intersect(listy)
    bpms=modelIntersect(bpms,modeld)
    dolinregbet(filefile,fileslist.keys(),betalisty,bpms,"V","beta",zeroby,modeld)
    filefile.close()

    print "Driven beta finished"

    #
    # driven coupling
    #
    print "Driven coupling"

    filefile=open(options.output+"/chromcoupling.out","w")
    print >>filefile,"NAME S CHROMCOUPLE  CHROMe  CHROMMDL"
    print >>filefile,"%s   %le  %le       %le     %le"

    bpms=intersect(listc)
    bpms=modelIntersect(bpms,modeld)

    dolinregCoupling(couplelist,bpms,fileslist.keys(),filefile,modeld)
    filefile.close()


    print "Driven coupling finished"
    filefile.close()

    if freeswitch==1:
      #
      # free beta
      #
      print "Free beta"
      #H
      filefile=open(options.output+"/chrombetax_free.out","w")
      print >>filefile, "* NAME", "S",  "dbb", "dbberr", "dalfa", "daerr", "WX","WXERR","WMO","PHIX", "PHIXERR","PHIM",  "dbbR", "dbberrR", "dalfaR", "daerr","WXR","WXERRR","PHIXR", "PHIXERRR"
      print >>filefile, "$ %s  %le  %le  %le  %le  %le %le %le %le  %le %le %le %le  %le %le %le %le  %le"

      bpms=intersect(listxf)
      bpms=modelIntersect(bpms,modelf)
      dolinregbet(filefile,fileslist.keys(),betalistxf,bpms,"H","beta",zerobxf,modelf)
      filefile.close()

      #V
      filefile=open(options.output+"/chrombetay_free.out","w")
      print >>filefile, "* NAME", "S",  "dbb", "dbberr", "dalfa", "daerr", "WY", "WYERR","WYM","PHIY", "PHIYERR","PHIM",  "dbbR", "dbberrR", "dalfaR", "daerr","WYR","WYERRR","PHIYR", "PHIYERRR"
      print >>filefile, "$ %s  %le  %le  %le  %le  %le %le %le %le  %le %le %le %le  %le %le %le %le  %le"

      bpms=intersect(listyf)
      bpms=modelIntersect(bpms,modelf)
      dolinregbet(filefile,fileslist.keys(),betalistyf,bpms,"V","beta",zerobyf,modelf)
      filefile.close()

      print "Free beta finished"

      #
      # free coupling
      #
      print "Free coupling"

      filefile=open(options.output+"/chromcoupling_free.out","w")
      print >>filefile,"NAME S CHROMCOUPLE  CHROMe  CHROMMDL"
      print >>filefile,"%s   %le  %le       %le     %le"

      bpms=intersect(listcf)
      bpms=modelIntersect(bpms,modelf)

      dolinregCoupling(couplelistf,bpms,fileslist.keys(),filefile,modelf)
      filefile.close()


      print "Free coupling finished"
      filefile.close()


if __name__=="__main__":
    sys.path.append('/afs/cern.ch/eng/sl/lintrack/Python_Classes4MAD/')

    options,args=parse_args()
    check_input(options,args)
    main(options,args)