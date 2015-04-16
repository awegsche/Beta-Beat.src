import os


#os.system("rm f_cminusimag_b2*dat f_cminusreal_b2*dat twiss.C.dat coupling_cminusimag_b2*dat* coupling_cminusreal_b2*dat* coupling_cminusimag_b2*knob coupling_cminusreal_b2*knob")
#os.system("rm used.c-real.b2*.dat used.c-imag.b2*.dat")


beams = ["b1", "b2"]

for B in beams:
    for IP in ['IP1', 'IP2','IP3', 'IP4','IP5', 'IP6','IP7', 'IP8' ]:
    # for IP in ['IP1']:
        
        

        strcom="sed 's/IP5/"+IP+"/g' job.coupl.coeff_"+B+".mask > tt.madx"
        print strcom
        os.system(strcom)
        os.system("madx < tt.madx")

        
        strcom="sed 's/IP5/"+IP+"/g' job.testing."+B+".mask > tt.madx"
        print strcom
        os.system(strcom)
        os.system("madx < tt.madx")



#os.system('rm tt.madx twiss.C.dat')
  
    