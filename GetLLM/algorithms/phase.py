'''
Created on 27 May 2013

@author: ?, vimaier

@version: 0.0.1

GetLLM.algorithms.phase.py stores helper functions for phase calculations for GetLLM.
This module is not intended to be executed. It stores only functions.

Change history:
 - <version>, <author>, <date>:
    <description>
'''

import sys
import traceback
import math

import numpy as np

import Utilities.bpm
import compensate_ac_effect


DEBUG = sys.flags.debug # True with python option -d! ("python -d GetLLM.py...") (vimaier)

#===================================================================================================
# main part
#===================================================================================================

class PhaseData(object):
    ''' File for storing results from get_phases. 
        Storing results from getphases_tot are not needed since values not used again.
    '''
    
    def __init__(self):
        self.acphasex_ac2bpmac = None
        self.acphasey_ac2bpmac = None
        self.ph_x = None # horizontal phase
        self.x_f = None
        self.x_f2 = None
        self.ph_y = None # vertical phase
        self.y_f = None
        self.y_f2 = None
        

def calculate_phase(getllm_d, twiss_d, tune_d, mad_twiss, mad_ac, mad_elem, files_dict):
    '''
    Calculates phase and fills the following TfsFiles:
        getphasex.out        getphasex_free.out        getphasex_free2.out
        getphasey.out        getphasey_free.out        getphasey_free2.out
        
    :Parameters:
        'getllm_d': GetllmData (In-param, values will only be read)
            lhc_phase, accel and beam_direction are used.
        'twiss_d': TwissData (In-param, values will only be read)
            Holds twiss instances of the src files.
        'tune_d': TuneData (In/Out-param, values will be read and set)
            Holds tunes and phase advances
            
    :Return: PhaseData, _TuneData
        an instance of PhaseData with the result of this function
        the same instance as param tune_d to indicate changes in the instace.
    '''
    phase_d = PhaseData()
    
    print 'Calculating phase' 
    #---- Calling get_phases first to save tunes
            
    if twiss_d.has_zero_dpp_x(): 
        #-- Calculate temp value of tune
        q1_temp = []
        for twiss_file in twiss_d.zero_dpp_x:
            q1_temp.append(np.mean(twiss_file.TUNEX))        
        q1_temp = np.mean(q1_temp)

        [phase_d.ph_x, tune_d.q1, tune_d.mux, bpmsx] = get_phases(getllm_d, mad_ac, twiss_d.zero_dpp_x, q1_temp, 'H')
        if not twiss_d.has_zero_dpp_y():
            print 'liny missing and output x only ...'

            
    if twiss_d.has_zero_dpp_y(): 
        #-- Calculate temp value of tune
        q2_temp = []
        for twiss_file in twiss_d.zero_dpp_y:
            q2_temp.append(np.mean(twiss_file.TUNEY))        
        q2_temp = np.mean(q2_temp)
        
        [phase_d.ph_y, tune_d.q2, tune_d.muy, bpmsy] = get_phases(getllm_d, mad_ac, twiss_d.zero_dpp_y, q2_temp, 'V')
        if not twiss_d.has_zero_dpp_x():
            print 'linx missing and output y only ...'

    #---- Re-run GetPhase to fix the phase shift by Q for exp data of LHC
    if getllm_d.lhc_phase == "1":
        if twiss_d.has_zero_dpp_x():
            [phase_d.ph_x, tune_d.q1, tune_d.mux, bpmsx] = get_phases(getllm_d, mad_ac, twiss_d.zero_dpp_x, tune_d.q1, 'H')
        if twiss_d.has_zero_dpp_y():
            [phase_d.ph_y, tune_d.q2, tune_d.muy, bpmsy] = get_phases(getllm_d, mad_ac, twiss_d.zero_dpp_y, tune_d.q2, 'V')
            
    #---- ac to free phase from eq and the model
    if getllm_d.with_ac_calc:
        if twiss_d.has_zero_dpp_x():
            tune_d.q1f = tune_d.q1 - tune_d.delta1 #-- Free H-tune
            try:
                phase_d.acphasex_ac2bpmac = compensate_ac_effect.GetACPhase_AC2BPMAC(mad_elem, tune_d.q1, tune_d.q1f, 'H', getllm_d.accel)
            except AttributeError:
                phase_d.acphasex_ac2bpmac = compensate_ac_effect.GetACPhase_AC2BPMAC(mad_twiss, tune_d.q1, tune_d.q1f, 'H', getllm_d.accel)
            [phase_d.x_f, tune_d.muxf, bpmsxf] = compensate_ac_effect.get_free_phase_eq(mad_twiss, twiss_d.zero_dpp_x, tune_d.q1, tune_d.q1f, phase_d.acphasex_ac2bpmac, 'H', getllm_d.beam_direction, getllm_d.lhc_phase)
            [phase_d.x_f2, tune_d.muxf2, bpmsxf2] = _get_free_phase(phase_d.ph_x, tune_d.q1, tune_d.q1f, bpmsx, mad_ac, mad_twiss, "H")
        if twiss_d.has_zero_dpp_y():
            tune_d.q2f = tune_d.q2 - tune_d.delta2 #-- Free V-tune
            try:
                phase_d.acphasey_ac2bpmac = compensate_ac_effect.GetACPhase_AC2BPMAC(mad_elem, tune_d.q2, tune_d.q2f, 'V', getllm_d.accel)
            except AttributeError:
                phase_d.acphasey_ac2bpmac = compensate_ac_effect.GetACPhase_AC2BPMAC(mad_twiss, tune_d.q2, tune_d.q2f, 'V', getllm_d.accel)
            [phase_d.y_f, tune_d.muyf, bpmsyf] = compensate_ac_effect.get_free_phase_eq(mad_twiss, twiss_d.zero_dpp_y, tune_d.q2, tune_d.q2f, phase_d.acphasey_ac2bpmac, 'V', getllm_d.beam_direction, getllm_d.lhc_phase)
            [phase_d.y_f2, tune_d.muyf2, bpmsyf2] = _get_free_phase(phase_d.ph_y, tune_d.q2, tune_d.q2f, bpmsy, mad_ac, mad_twiss, "V")

    #---- H plane result
    if twiss_d.has_zero_dpp_x():
        phase_d.ph_x['DPP'] = 0.0
        tfs_file = files_dict['getphasex.out']
        tfs_file.add_descriptor("Q1", "%le", str(tune_d.q1))
        tfs_file.add_descriptor("MUX", "%le", str(tune_d.mux))
        tfs_file.add_descriptor("Q2", "%le", str(tune_d.q2))
        tfs_file.add_descriptor("MUY", "%le", str(tune_d.muy))
        tfs_file.add_column_names(["NAME", "NAME2", "S", "S1", "COUNT", "PHASEX", "STDPHX", "PHXMDL", "MUXMDL"])
        tfs_file.add_column_datatypes(["%s", "%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
        for i in range(len(bpmsx)):
            bn1 = str.upper(bpmsx[i][1])
            bns1 = bpmsx[i][0]
            phmdl = phase_d.ph_x[bn1][4]
            bn2 = str.upper(bpmsx[(i+1)%len(bpmsx)][1])
            bns2 = bpmsx[(i+1)%len(bpmsx)][0]
            list_row_entries = ['"' + bn1 + '"', '"' + bn2 + '"', bns1, bns2, len(twiss_d.zero_dpp_x), phase_d.ph_x[bn1][0], phase_d.ph_x[bn1][1], phmdl, mad_ac.MUX[mad_ac.indx[bn1]]]
            tfs_file.add_table_row(list_row_entries)
        
        #-- ac to free phase
        if getllm_d.with_ac_calc:
            #-- from eq
            try:
                tfs_file = files_dict['getphasex_free.out']
                tfs_file.add_descriptor("Q1", "%le", str(tune_d.q1f))
                tfs_file.add_descriptor("MUX", "%le", str(tune_d.muxf))
                tfs_file.add_descriptor("Q2", "%le", str(tune_d.q2f))
                tfs_file.add_descriptor("MUY", "%le", str(tune_d.muyf))
                tfs_file.add_column_names(["NAME", "NAME2", "S", "S1", "COUNT", "PHASEX", "STDPHX", "PHXMDL", "MUXMDL"])
                tfs_file.add_column_datatypes(["%s", "%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
                for i in range(len(bpmsxf)):
                    bn1 = str.upper(bpmsxf[i][1])
                    bns1 = bpmsxf[i][0]
                    phmdlf = phase_d.x_f[bn1][4]
                    bn2 = str.upper(bpmsxf[(i+1)%len(bpmsxf)][1])
                    bns2 = bpmsxf[(i+1)%len(bpmsxf)][0]
                    list_row_entries = ['"' + bn1 + '"', '"' + bn2 + '"', bns1, bns2, len(twiss_d.zero_dpp_x), phase_d.x_f[bn1][0], phase_d.x_f[bn1][1], phmdlf, mad_twiss.MUX[mad_twiss.indx[bn1]]]
                    tfs_file.add_table_row(list_row_entries)
            
            except Exception:
                traceback.print_exc()
                
            #-- from the model
            tfs_file = files_dict['getphasex_free2.out']
            tfs_file.add_descriptor("Q1", "%le", str(tune_d.q1f))
            tfs_file.add_descriptor("MUX", "%le", str(tune_d.muxf2))
            tfs_file.add_descriptor("Q2", "%le", str(tune_d.q2f))
            tfs_file.add_descriptor("MUY", "%le", str(tune_d.muyf2))
            tfs_file.add_column_names(["NAME", "NAME2", "S", "S1", "COUNT", "PHASEX", "STDPHX", "PHXMDL", "MUXMDL"])
            tfs_file.add_column_datatypes(["%s", "%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
            for i in range(0, len(bpmsxf2)):
                bn1 = str.upper(bpmsxf2[i][1])
                bns1 = bpmsxf2[i][0]
                phmdlf2 = phase_d.x_f2[bn1][2]
                bn2 = phase_d.x_f2[bn1][3]
                bns2 = phase_d.x_f2[bn1][4]
                list_row_entries = ['"' + bn1 + '"', '"' + bn2 + '"', bns1, bns2, len(twiss_d.zero_dpp_x), phase_d.x_f2[bn1][0], phase_d.x_f2[bn1][1], phmdlf2, mad_twiss.MUX[mad_twiss.indx[bn1]]]
                tfs_file.add_table_row(list_row_entries)
    
    #---- V plane result
    if twiss_d.has_zero_dpp_y():
        phase_d.ph_y['DPP'] = 0.0
        tfs_file = files_dict['getphasey.out']
        tfs_file.add_descriptor("Q1", "%le", str(tune_d.q1))
        tfs_file.add_descriptor("MUX", "%le", str(tune_d.mux))
        tfs_file.add_descriptor("Q2", "%le", str(tune_d.q2))
        tfs_file.add_descriptor("MUY", "%le", str(tune_d.muy))
        tfs_file.add_column_names(["NAME", "NAME2", "S", "S1", "COUNT", "PHASEY", "STDPHY", "PHYMDL", "MUYMDL"])
        tfs_file.add_column_datatypes(["%s", "%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
        for i in range(len(bpmsy)):
            bn1 = str.upper(bpmsy[i][1])
            bns1 = bpmsy[i][0]
            phmdl = phase_d.ph_y[bn1][4]
            bn2 = str.upper(bpmsy[(i+1)%len(bpmsy)][1])
            bns2 = bpmsy[(i+1)%len(bpmsy)][0]
            list_row_entries = ['"' + bn1 + '"', '"' + bn2 + '"', bns1, bns2, len(twiss_d.zero_dpp_y), phase_d.ph_y[bn1][0], phase_d.ph_y[bn1][1], phmdl, mad_ac.MUY[mad_ac.indx[bn1]]]
            tfs_file.add_table_row(list_row_entries)
        
        #-- ac to free phase
        if getllm_d.with_ac_calc:
            #-- from eq
            try:
                tfs_file = files_dict['getphasey_free.out']
                tfs_file.add_descriptor("Q1", "%le", str(tune_d.q1f))
                tfs_file.add_descriptor("MUX", "%le", str(tune_d.muxf))
                tfs_file.add_descriptor("Q2", "%le", str(tune_d.q2f))
                tfs_file.add_descriptor("MUY", "%le", str(tune_d.muyf))
                tfs_file.add_column_names(["NAME", "NAME2", "S", "S1", "COUNT", "PHASEY", "STDPHY", "PHYMDL", "MUYMDL"])
                tfs_file.add_column_datatypes(["%s", "%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
                for i in range(len(bpmsyf)):
                    bn1 = str.upper(bpmsyf[i][1])
                    bns1 = bpmsyf[i][0]
                    phmdlf = phase_d.y_f[bn1][4]
                    if i == len(bpmsyf) - 1:
                        bn2 = str.upper(bpmsyf[0][1])
                        bns2 = bpmsyf[0][0]
                    else:
                        bn2 = str.upper(bpmsyf[i + 1][1])
                        bns2 = bpmsyf[i + 1][0]
                    list_row_entries = ['"' + bn1 + '"', '"' + bn2 + '"', bns1, bns2, len(twiss_d.zero_dpp_y), phase_d.y_f[bn1][0], phase_d.y_f[bn1][1], phmdlf, mad_twiss.MUY[mad_twiss.indx[bn1]]]
                    tfs_file.add_table_row(list_row_entries)
            
            except Exception:
                traceback.print_exc()
                
            #-- from the model
            tfs_file = files_dict['getphasey_free2.out']
            tfs_file.add_descriptor("Q1", "%le", str(tune_d.q1f))
            tfs_file.add_descriptor("MUX", "%le", str(tune_d.muxf2))
            tfs_file.add_descriptor("Q2", "%le", str(tune_d.q2f))
            tfs_file.add_descriptor("MUY", "%le", str(tune_d.muyf2))
            tfs_file.add_column_names(["NAME", "NAME2", "S", "S1", "COUNT", "PHASEY", "STDPHY", "PHYMDL", "MUYMDL"])
            tfs_file.add_column_datatypes(["%s", "%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
            for i in range(0, len(bpmsyf2)):
                bn1 = str.upper(bpmsyf2[i][1])
                bns1 = bpmsyf2[i][0]
                phmdlf2 = phase_d.y_f2[bn1][2]
                bn2 = phase_d.y_f2[bn1][3]
                bns2 = phase_d.y_f2[bn1][4]
                list_row_entries = ['"' + bn1 + '"', '"' + bn2 + '"', bns1, bns2, len(twiss_d.zero_dpp_y), phase_d.y_f2[bn1][0], phase_d.y_f2[bn1][1], phmdlf2, mad_twiss.MUY[mad_twiss.indx[bn1]]]
                tfs_file.add_table_row(list_row_entries)
    
    return phase_d, tune_d
# END calculate_phase ------------------------------------------------------------------------------


def calculate_total_phase(getllm_d, twiss_d, tune_d, phase_d, mad_twiss, mad_ac, files_dict):
    '''
    Calculates total phase and fills the following TfsFiles:
        getphasetotx.out        getphasetotx_free.out        getphasetotx_free2.out
        getphasetoty.out        getphasetoty_free.out        getphasetoty_free2.out
        
    :Parameters:
        'getllm_d': GetllmData (In-param, values will only be read)
            lhc_phase, accel and beam_direction are used.
        'twiss_d': TwissData (In-param, values will only be read)
            Holds twiss instances of the src files.
        'tune_d': TuneData (In-param, values will only be read)
            Holds tunes and phase advances
    '''
    print 'Calculating total phase' 
    #---- H plane result
    if twiss_d.has_zero_dpp_x():
        [phase_x_tot, bpms_x_tot] = _get_phases_total(mad_ac, twiss_d.zero_dpp_x, tune_d.q1, 'H', getllm_d.beam_direction, getllm_d.accel, getllm_d.lhc_phase)
        tfs_file = files_dict['getphasetotx.out']
        tfs_file.add_descriptor("Q1", "%le", str(tune_d.q1))
        tfs_file.add_descriptor("MUX", "%le", str(tune_d.mux))
        tfs_file.add_descriptor("Q2", "%le", str(tune_d.q2))
        tfs_file.add_descriptor("MUY", "%le", str(tune_d.muy))
        tfs_file.add_column_names(["NAME", "NAME2", "S", "S1", "COUNT", "PHASEX", "STDPHX", "PHXMDL", "MUXMDL"])
        tfs_file.add_column_datatypes(["%s", "%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
        for i in range(0, len(bpms_x_tot)):
            bn1 = str.upper(bpms_x_tot[i][1])
            bns1 = bpms_x_tot[i][0]
            phmdl = phase_x_tot[bn1][2]
            bn2 = str.upper(bpms_x_tot[0][1])
            bns2 = bpms_x_tot[0][0]
            list_row_entries = ['"' + bn1 + '"', '"' + bn2 + '"', bns1, bns2, len(twiss_d.zero_dpp_x), phase_x_tot[bn1][0], phase_x_tot[bn1][1], phmdl, mad_ac.MUX[mad_ac.indx[bn1]]]
            tfs_file.add_table_row(list_row_entries)
        
        #-- ac to free total phase
        if getllm_d.with_ac_calc:
            #-- from eq
            try:
                [phase_x_tot_f, bpms_x_tot_f] = compensate_ac_effect.get_free_phase_total_eq(mad_twiss, twiss_d.zero_dpp_x, tune_d.q1, tune_d.q1f, phase_d.acphasex_ac2bpmac, 'H', getllm_d.beam_direction, getllm_d.lhc_phase)
                tfs_file = files_dict['getphasetotx_free.out']
                tfs_file.add_descriptor("Q1", "%le", str(tune_d.q1f))
                tfs_file.add_descriptor("MUX", "%le", str(tune_d.muxf))
                tfs_file.add_descriptor("Q2", "%le", str(tune_d.q2f))
                tfs_file.add_descriptor("MUY", "%le", str(tune_d.muyf))
                tfs_file.add_column_names(["NAME", "NAME2", "S", "S1", "COUNT", "PHASEX", "STDPHX", "PHXMDL", "MUXMDL"])
                tfs_file.add_column_datatypes(["%s", "%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
                for i in range(0, len(bpms_x_tot_f)):
                    bn1 = str.upper(bpms_x_tot_f[i][1])
                    bns1 = bpms_x_tot_f[i][0]
                    phmdlf = phase_x_tot_f[bn1][2]
                    bn2 = str.upper(bpms_x_tot_f[0][1])
                    bns2 = bpms_x_tot_f[0][0]
                    list_row_entries = ['"' + bn1 + '"', '"' + bn2 + '"', bns1, bns2, len(twiss_d.zero_dpp_x), phase_x_tot_f[bn1][0], phase_x_tot_f[bn1][1], phmdlf, mad_twiss.MUX[mad_twiss.indx[bn1]]]
                    tfs_file.add_table_row(list_row_entries)
            except:
                traceback.print_exc()
                
            #-- from the model
            [phase_x_tot_f2, bpms_x_tot_f2] = get_free_phase_total(phase_x_tot, bpms_x_tot, "H", mad_twiss, mad_ac)
            tfs_file = files_dict['getphasetotx_free2.out']
            tfs_file.add_descriptor("Q1", "%le", str(tune_d.q1f))
            tfs_file.add_descriptor("MUX", "%le", str(tune_d.muxf2))
            tfs_file.add_descriptor("Q2", "%le", str(tune_d.q2f))
            tfs_file.add_descriptor("MUY", "%le", str(tune_d.muyf2))
            tfs_file.add_column_names(["NAME", "NAME2", "S", "S1", "COUNT", "PHASEX", "STDPHX", "PHXMDL", "MUXMDL"])
            tfs_file.add_column_datatypes(["%s", "%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
            for i in range(0, len(bpms_x_tot_f2)):
                bn1 = str.upper(bpms_x_tot_f2[i][1])
                bns1 = bpms_x_tot_f2[i][0]
                phmdlf2 = phase_x_tot_f2[bn1][2]
                bn2 = str.upper(bpms_x_tot_f2[0][1])
                bns2 = bpms_x_tot_f2[0][0]
                list_row_entries = ['"' + bn1 + '"', '"' + bn2 + '"', bns1, bns2, len(twiss_d.zero_dpp_x), phase_x_tot_f2[bn1][0], phase_x_tot_f2[bn1][1], phmdlf2, mad_twiss.MUX[mad_twiss.indx[bn1]]]
                tfs_file.add_table_row(list_row_entries)
    
    #---- V plane result
    if twiss_d.has_zero_dpp_y():
        [phase_y_tot, bpms_y_tot] = _get_phases_total(mad_ac, twiss_d.zero_dpp_y, tune_d.q2, 'V', getllm_d.beam_direction, getllm_d.accel, getllm_d.lhc_phase)
        tfs_file = files_dict['getphasetoty.out']
        tfs_file.add_descriptor("Q1", "%le", str(tune_d.q1))
        tfs_file.add_descriptor("MUX", "%le", str(tune_d.mux))
        tfs_file.add_descriptor("Q2", "%le", str(tune_d.q2))
        tfs_file.add_descriptor("MUY", "%le", str(tune_d.muy))
        tfs_file.add_column_names(["NAME", "NAME2", "S", "S1", "COUNT", "PHASEY", "STDPHY", "PHYMDL", "MUYMDL"])
        tfs_file.add_column_datatypes(["%s", "%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
        for i in range(0, len(bpms_y_tot)):
            bn1 = str.upper(bpms_y_tot[i][1])
            bns1 = bpms_y_tot[i][0]
            phmdl = phase_y_tot[bn1][2]
            bn2 = str.upper(bpms_y_tot[0][1])
            bns2 = bpms_y_tot[0][0]
            list_row_entries = ['"' + bn1 + '"', '"' + bn2 + '"', bns1, bns2, len(twiss_d.zero_dpp_y), phase_y_tot[bn1][0], phase_y_tot[bn1][1], phmdl, mad_ac.MUY[mad_ac.indx[bn1]]]
            tfs_file.add_table_row(list_row_entries)
        
        #-- ac to free total phase
        if getllm_d.with_ac_calc:
            #-- from eq
            try:
                [phase_y_tot_f, bpms_y_tot_f] = compensate_ac_effect.get_free_phase_total_eq(mad_twiss, twiss_d.zero_dpp_y, tune_d.q2, tune_d.q2f, phase_d.acphasey_ac2bpmac, 'V', getllm_d.beam_direction, getllm_d.lhc_phase)
                tfs_file = files_dict['getphasetoty_free.out']
                tfs_file.add_descriptor("Q1", "%le", str(tune_d.q1f))
                tfs_file.add_descriptor("MUX", "%le", str(tune_d.muxf))
                tfs_file.add_descriptor("Q2", "%le", str(tune_d.q2f))
                tfs_file.add_descriptor("MUY", "%le", str(tune_d.muyf))
                tfs_file.add_column_names(["NAME", "NAME2", "S", "S1", "COUNT", "PHASEY", "STDPHY", "PHYMDL", "MUYMDL"])
                tfs_file.add_column_datatypes(["%s", "%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
                for i in range(0, len(bpms_y_tot_f)):
                    bn1 = str.upper(bpms_y_tot_f[i][1])
                    bns1 = bpms_y_tot_f[i][0]
                    phmdlf = phase_y_tot_f[bn1][2]
                    bn2 = str.upper(bpms_y_tot_f[0][1])
                    bns2 = bpms_y_tot_f[0][0]
                    list_row_entries = ['"' + bn1 + '"', '"' + bn2 + '"', bns1, bns2, len(twiss_d.zero_dpp_y), phase_y_tot_f[bn1][0], phase_y_tot_f[bn1][1], phmdlf, mad_twiss.MUY[mad_twiss.indx[bn1]]]
                    tfs_file.add_table_row(list_row_entries)
            except:
                traceback.print_exc()
            #-- from the model
            [phase_y_tot_f2, bpms_y_tot_f2] = get_free_phase_total(phase_y_tot, bpms_y_tot, "V", mad_twiss, mad_ac)
            tfs_file = files_dict['getphasetoty_free2.out']
            tfs_file.add_descriptor("Q1", "%le", str(tune_d.q1f))
            tfs_file.add_descriptor("MUX", "%le", str(tune_d.muxf2))
            tfs_file.add_descriptor("Q2", "%le", str(tune_d.q2f))
            tfs_file.add_descriptor("MUY", "%le", str(tune_d.muyf2))
            tfs_file.add_column_names(["NAME", "NAME2", "S", "S1", "COUNT", "PHASEY", "STDPHY", "PHYMDL", "MUYMDL"])
            tfs_file.add_column_datatypes(["%s", "%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
            for i in range(0, len(bpms_y_tot_f2)):
                bn1 = str.upper(bpms_y_tot_f2[i][1])
                bns1 = bpms_y_tot_f2[i][0]
                phmdlf2 = phase_y_tot_f2[bn1][2]
                bn2 = str.upper(bpms_y_tot_f2[0][1])
                bns2 = bpms_y_tot_f2[0][0]
                list_row_entries = ['"' + bn1 + '"', '"' + bn2 + '"', bns1, bns2, len(twiss_d.zero_dpp_y), phase_y_tot_f2[bn1][0], phase_y_tot_f2[bn1][1], phmdlf2, mad_twiss.MUY[mad_twiss.indx[bn1]]]
                tfs_file.add_table_row(list_row_entries)
# END calculate_total_phase ------------------------------------------------------------------------

#===================================================================================================
# helper-functions
#===================================================================================================
#TODO: awful name! what does this function??? (vimaier)
def _phi_last_and_last_but_one(phi, ftune):
    if ftune <= 0.0:
        ftune = 1.0 + ftune
    phit = phi+ftune
    if phit > 1.0:
        phit = phit-1.0
    return phit

def calc_phase_mean(phase0, norm):  
    ''' phases must be in [0,1) or [0,2*pi), norm = 1 or 2*pi '''
    phase0 = np.array(phase0)%norm
    phase1 = (phase0+0.5*norm)%norm - 0.5*norm
    phase0ave = np.mean(phase0)
    phase1ave = np.mean(phase1)
    # Since phase0std and phase1std are only used for comparing, I modified the expressions to avoid
    # math.sqrt(), np.mean() and **2. 
    # Old expressions:
    #     phase0std = math.sqrt(np.mean((phase0-phase0ave)**2))
    #     phase1std = math.sqrt(np.mean((phase1-phase1ave)**2))
    # -- vimaier 
    mod_phase0std = sum(abs(phase0-phase0ave))
    mod_phase1std = sum(abs(phase1-phase1ave))
    if mod_phase0std < mod_phase1std: 
        return phase0ave
    else: 
        return phase1ave % norm

def calc_phase_std(phase0, norm):
    ''' phases must be in [0,1) or [0,2*pi), norm = 1 or 2*pi '''
    phase0 = np.array(phase0)%norm
    phase1 = (phase0+0.5*norm)%norm-0.5*norm
    phase0ave = np.mean(phase0)
    phase1ave = np.mean(phase1)
    
    # Omitted unnecessary computations. Old expressions:
    #     phase0std=sqrt(mean((phase0-phase0ave)**2))
    #     phase1std=sqrt(mean((phase1-phase1ave)**2))
    #     return min(phase0std,phase1std)
    # -- vimaier 
    phase0std_sq = np.sum((phase0-phase0ave)**2)
    phase1std_sq = np.sum((phase1-phase1ave)**2)
    
    min_phase_std = min(phase0std_sq, phase1std_sq)
    phase_std = math.sqrt(min_phase_std/len(phase0))
    
    return phase_std


def _get_phases_total(mad_twiss, src_files, tune, plane, beam_direction, accel, lhc_phase):
    commonbpms = Utilities.bpm.intersect(src_files)
    commonbpms = Utilities.bpm.model_intersect(commonbpms, mad_twiss)
    #-- Last BPM on the same turn to fix the phase shift by tune for exp data of LHC
    s_lastbpm = None
    if lhc_phase == "1" and accel == "LHCB1": 
        s_lastbpm = mad_twiss.S[mad_twiss.indx['BPMSW.1L2.B1']]
    if lhc_phase == "1" and accel == "LHCB2": 
        s_lastbpm = mad_twiss.S[mad_twiss.indx['BPMSW.1L8.B2']]

    bn1 = str.upper(commonbpms[0][1])
    phase_t = {}
    if DEBUG:
        print "Reference BPM:", bn1, "Plane:", plane
    for i in range(0, len(commonbpms)):
        bn2 = str.upper(commonbpms[i][1])
        if plane == 'H':
            phmdl12 = (mad_twiss.MUX[mad_twiss.indx[bn2]]-mad_twiss.MUX[mad_twiss.indx[bn1]]) % 1
        if plane == 'V':
            phmdl12 = (mad_twiss.MUY[mad_twiss.indx[bn2]]-mad_twiss.MUY[mad_twiss.indx[bn1]]) % 1

        phi12 = []
        for twiss_file in src_files:
            # Phase is in units of 2pi
            if plane == 'H':
                phm12 = (twiss_file.MUX[twiss_file.indx[bn2]]-twiss_file.MUX[twiss_file.indx[bn1]]) % 1
            if plane == 'V':
                phm12 = (twiss_file.MUY[twiss_file.indx[bn2]]-twiss_file.MUY[twiss_file.indx[bn1]]) % 1
            #-- To fix the phase shift by tune in LHC
            try:
                if s_lastbpm is not None and commonbpms[i][0] > s_lastbpm:
                    phm12 += beam_direction*tune
            except: 
                traceback.print_exc()
            phi12.append(phm12)
        phi12 = np.array(phi12)
        # for the beam circulating reversely to the model
        if beam_direction == -1:
            phi12 = 1.0-phi12

        #phstd12=math.sqrt(np.average(phi12*phi12)-(np.average(phi12))**2.0+2.2e-15)
        #phi12=np.average(phi12)
        phstd12 = calc_phase_std(phi12, 1.0)
        phi12   = calc_phase_mean(phi12, 1.0)
        phase_t[bn2] = [phi12, phstd12, phmdl12, bn1]

    return [phase_t, commonbpms]


def get_phases(getllm_d, mad_twiss, ListOfFiles, tune_q, plane):
    """
    Calculates phase.
    tune_q will be used to fix the phase shift in LHC.
    For other accelerators use 'None'.
    """
    commonbpms = Utilities.bpm.intersect(ListOfFiles)
    commonbpms = Utilities.bpm.model_intersect(commonbpms, mad_twiss)
    length_commonbpms = len(commonbpms)
    
    if 3 > length_commonbpms:
        print >> sys.stderr, "get_phases: Less than three BPMs provided for plane", plane, "Please check input."
        return [{}, 0.0, 0.0, []]

    #-- Last BPM on the same turn to fix the phase shift by tune_q for exp data of LHC
    if getllm_d.lhc_phase == "1" and getllm_d.accel == "LHCB1": 
        s_lastbpm = mad_twiss.S[mad_twiss.indx['BPMSW.1L2.B1']]
    if getllm_d.lhc_phase == "1" and getllm_d.accel == "LHCB2": 
        s_lastbpm = mad_twiss.S[mad_twiss.indx['BPMSW.1L8.B2']]

    mu=0.0
    tunem=[]
    phase={} # Dictionary for the output containing [average phase, rms error]
    
        
    p_mdl_12 = 0.0 # phase model between BPM1 and BPM2
    p_mdl_13 = 0.0 # phase model between BPM1 and BPM3
    
    for i in range(0,length_commonbpms): # To find the integer part of tune as well, the loop is up to the last monitor
        bn1 = str.upper(commonbpms[i%length_commonbpms][1])
        bn2 = str.upper(commonbpms[(i+1)%length_commonbpms][1])
        bn3 = str.upper(commonbpms[(i+2)%length_commonbpms][1])
        
        if bn1 == bn2 :
            print >> sys.stderr, "There seem two lines with the same BPM name "+bn1+" in linx/y file."
            print >> sys.stderr, "Please check your input data....leaving GetLLM."
            sys.exit(1)
            
        if plane == 'H':
            p_mdl_12 = mad_twiss.MUX[mad_twiss.indx[bn2]] - mad_twiss.MUX[mad_twiss.indx[bn1]]
            p_mdl_13 = mad_twiss.MUX[mad_twiss.indx[bn3]] - mad_twiss.MUX[mad_twiss.indx[bn1]]
        elif plane == 'V':
            p_mdl_12 = mad_twiss.MUY[mad_twiss.indx[bn2]] - mad_twiss.MUY[mad_twiss.indx[bn1]]
            p_mdl_13 = mad_twiss.MUY[mad_twiss.indx[bn3]] - mad_twiss.MUY[mad_twiss.indx[bn1]]
            
        if i == length_commonbpms-2:
            if plane == 'H':
                madtune = mad_twiss.Q1 % 1.0
            elif plane == 'V':
                madtune = mad_twiss.Q2 % 1.0
            
            if madtune > 0.5:
                madtune -= 1.0
            
            p_mdl_13 = p_mdl_13 % 1.0
            p_mdl_13 = _phi_last_and_last_but_one(p_mdl_13,madtune)
        elif i == length_commonbpms-1:
            if plane == 'H':
                madtune = mad_twiss.Q1 % 1.0
            elif plane == 'V':
                madtune = mad_twiss.Q2 % 1.0
            
            if madtune>0.5:
                madtune -= 1.0
            
            p_mdl_12 = p_mdl_12 % 1.0
            p_mdl_13 = p_mdl_13 % 1.0
            p_mdl_12 = _phi_last_and_last_but_one(p_mdl_12,madtune)
            p_mdl_13 = _phi_last_and_last_but_one(p_mdl_13,madtune)




        p_i_12 = [] # list with phases between BPM1 and BPM2 from src files
        p_i_13 = [] # list with phases between BPM1 and BPM3 from src files
        tunemi=[]
        for src_twiss in ListOfFiles:
            # Phase is in units of 2pi
            if plane=='H':
                p_m_12=(src_twiss.MUX[src_twiss.indx[bn2]]-src_twiss.MUX[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM2
                p_m_13=(src_twiss.MUX[src_twiss.indx[bn3]]-src_twiss.MUX[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM3
                tunemi.append(src_twiss.TUNEX[src_twiss.indx[bn1]])
            elif plane=='V':
                p_m_12=(src_twiss.MUY[src_twiss.indx[bn2]]-src_twiss.MUY[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM2
                p_m_13=(src_twiss.MUY[src_twiss.indx[bn3]]-src_twiss.MUY[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM3
                tunemi.append(src_twiss.TUNEY[src_twiss.indx[bn1]])
            
            #-- To fix the phase shift by tune_q in LHC
            if tune_q is not None:
                try:
                    if mad_twiss.S[mad_twiss.indx[bn1]] <= s_lastbpm:
                        if mad_twiss.S[mad_twiss.indx[bn2]] > s_lastbpm: 
                            p_m_12 += getllm_d.beam_direction*tune_q
                        if mad_twiss.S[mad_twiss.indx[bn3]] > s_lastbpm: 
                            p_m_13 += getllm_d.beam_direction*tune_q
                    if mad_twiss.S[mad_twiss.indx[bn1]] > s_lastbpm:
                        if mad_twiss.S[mad_twiss.indx[bn2]] <= s_lastbpm: 
                            p_m_12 += -getllm_d.beam_direction*tune_q
                        if mad_twiss.S[mad_twiss.indx[bn3]] <= s_lastbpm: 
                            p_m_13 += -getllm_d.beam_direction*tune_q
                except UnboundLocalError: 
                    pass # s_lastbpm is not always defined
            
            if p_m_12<0: 
                p_m_12+=1
            if p_m_13<0: 
                p_m_13+=1
            p_i_12.append(p_m_12)
            p_i_13.append(p_m_13)

        p_i_12=np.array(p_i_12)
        p_i_13=np.array(p_i_13)
        if getllm_d.beam_direction==-1: # for the beam circulating reversely to the model
            p_i_12=1.0-p_i_12
            p_i_13=1.0-p_i_13

        #if any(p_i_12)>0.9 and i !=len(commonbpms): # Very small phase advance could result in larger than 0.9 due to measurement error
        #       print 'Warning: there seems too large phase advance! '+bn1+' to '+bn2+' = '+str(p_i_12)+'in plane '+plane+', recommended to check.'
        p_std_12 = calc_phase_std(p_i_12, 1.0)
        p_std_13 = calc_phase_std(p_i_13, 1.0)
        p_i_12 = calc_phase_mean(p_i_12, 1.0)
        p_i_13 = calc_phase_mean(p_i_13, 1.0)
        tunemi = np.array(tunemi)
        if i < length_commonbpms-1 :
            tunem.append(np.average(tunemi))

        # Note that the phase advance between the last monitor and the first monitor should be find by taking into account the fractional part of tune.
        if i == length_commonbpms-2:
            tunem = np.array(tunem)
            tune = np.average(tunem)
            p_i_13 = _phi_last_and_last_but_one(p_i_13, tune)
        elif i == length_commonbpms-1:
            p_i_12 = _phi_last_and_last_but_one(p_i_12, tune)
            p_i_13 = _phi_last_and_last_but_one(p_i_13, tune)
        mu = mu+p_i_12

        small=0.0000001
        if (abs(p_mdl_12) < small):
            p_mdl_12=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn2+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(p_mdl_13) < small):
            p_mdl_13=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn3+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(p_i_12) < small ):
            p_i_12 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn2+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(p_i_13) < small):
            p_i_13 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn3+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        phase[bn1]=[p_i_12,p_std_12,p_i_13,p_std_13,p_mdl_12,p_mdl_13,bn2]

    for i in range(0,length_commonbpms): # To find the integer part of tune as well, the loop is up to the last monitor

        bn1 = str.upper(commonbpms[i%len(commonbpms)][1])
        bn2 = str.upper(commonbpms[(i+1)%len(commonbpms)][1])
        bn3 = str.upper(commonbpms[(i+2)%len(commonbpms)][1])
        bn4 = str.upper(commonbpms[(i+3)%len(commonbpms)][1])
        bn5 = str.upper(commonbpms[(i+4)%len(commonbpms)][1])
        bn6 = str.upper(commonbpms[(i+5)%len(commonbpms)][1])
        bn7 = str.upper(commonbpms[(i+6)%len(commonbpms)][1])


        p_i_12=[]
        p_i_13=[]
        phi14=[]
        phi15=[]
        phi16=[]
        phi17=[]

        for src_twiss in ListOfFiles:
            # Phase is in units of 2pi
            if plane=='H':
                p_m_12=(src_twiss.MUX[src_twiss.indx[bn2]]-src_twiss.MUX[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM2
                p_m_13=(src_twiss.MUX[src_twiss.indx[bn3]]-src_twiss.MUX[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM3
                phm14=(src_twiss.MUX[src_twiss.indx[bn4]]-src_twiss.MUX[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM4
                phm15=(src_twiss.MUX[src_twiss.indx[bn5]]-src_twiss.MUX[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM5
                phm16=(src_twiss.MUX[src_twiss.indx[bn6]]-src_twiss.MUX[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM6
                phm17=(src_twiss.MUX[src_twiss.indx[bn7]]-src_twiss.MUX[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM7
            elif plane=='V':
                p_m_12=(src_twiss.MUY[src_twiss.indx[bn2]]-src_twiss.MUY[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM2
                p_m_13=(src_twiss.MUY[src_twiss.indx[bn3]]-src_twiss.MUY[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM3
                phm14=(src_twiss.MUY[src_twiss.indx[bn4]]-src_twiss.MUY[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM4
                phm15=(src_twiss.MUY[src_twiss.indx[bn5]]-src_twiss.MUY[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM5
                phm16=(src_twiss.MUY[src_twiss.indx[bn6]]-src_twiss.MUY[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM6
                phm17=(src_twiss.MUY[src_twiss.indx[bn7]]-src_twiss.MUY[src_twiss.indx[bn1]]) # the phase advance between BPM1 and BPM7
            #-- To fix the phase shift by tune_q in LHC
            if tune_q is not None:
                try:
                    if mad_twiss.S[mad_twiss.indx[bn1]]<=s_lastbpm and mad_twiss.S[mad_twiss.indx[bn2]] >s_lastbpm: p_m_12+= getllm_d.beam_direction*tune_q
                    if mad_twiss.S[mad_twiss.indx[bn1]]<=s_lastbpm and mad_twiss.S[mad_twiss.indx[bn3]] >s_lastbpm: p_m_13+= getllm_d.beam_direction*tune_q
                    if mad_twiss.S[mad_twiss.indx[bn1]]<=s_lastbpm and mad_twiss.S[mad_twiss.indx[bn4]] >s_lastbpm: phm14+= getllm_d.beam_direction*tune_q
                    if mad_twiss.S[mad_twiss.indx[bn1]]<=s_lastbpm and mad_twiss.S[mad_twiss.indx[bn5]] >s_lastbpm: phm15+= getllm_d.beam_direction*tune_q
                    if mad_twiss.S[mad_twiss.indx[bn1]]<=s_lastbpm and mad_twiss.S[mad_twiss.indx[bn6]] >s_lastbpm: phm16+= getllm_d.beam_direction*tune_q
                    if mad_twiss.S[mad_twiss.indx[bn1]]<=s_lastbpm and mad_twiss.S[mad_twiss.indx[bn7]] >s_lastbpm: phm17+= getllm_d.beam_direction*tune_q
                    if mad_twiss.S[mad_twiss.indx[bn1]] >s_lastbpm and mad_twiss.S[mad_twiss.indx[bn2]]<=s_lastbpm: p_m_12+=-getllm_d.beam_direction*tune_q
                    if mad_twiss.S[mad_twiss.indx[bn1]] >s_lastbpm and mad_twiss.S[mad_twiss.indx[bn3]]<=s_lastbpm: p_m_13+=-getllm_d.beam_direction*tune_q
                    if mad_twiss.S[mad_twiss.indx[bn1]] >s_lastbpm and mad_twiss.S[mad_twiss.indx[bn4]]<=s_lastbpm: phm14+=-getllm_d.beam_direction*tune_q
                    if mad_twiss.S[mad_twiss.indx[bn1]] >s_lastbpm and mad_twiss.S[mad_twiss.indx[bn5]]<=s_lastbpm: phm15+=-getllm_d.beam_direction*tune_q
                    if mad_twiss.S[mad_twiss.indx[bn1]] >s_lastbpm and mad_twiss.S[mad_twiss.indx[bn6]]<=s_lastbpm: phm16+=-getllm_d.beam_direction*tune_q
                    if mad_twiss.S[mad_twiss.indx[bn1]] >s_lastbpm and mad_twiss.S[mad_twiss.indx[bn7]]<=s_lastbpm: phm17+=-getllm_d.beam_direction*tune_q
                except: 
                    pass
            if p_m_12<0: p_m_12+=1
            if p_m_13<0: p_m_13+=1
            if phm14<0: phm14+=1
            if phm15<0: phm15+=1
            if phm16<0: phm16+=1
            if phm17<0: phm17+=1
            p_i_12.append(p_m_12)
            p_i_13.append(p_m_13)
            phi14.append(phm14)
            phi15.append(phm15)
            phi16.append(phm16)
            phi17.append(phm17)

        p_i_12 = np.array(p_i_12)
        p_i_13 = np.array(p_i_13)
        phi14 = np.array(phi14)
        phi15 = np.array(phi15)
        phi16 = np.array(phi16)
        phi17 = np.array(phi17)
        if getllm_d.beam_direction == -1: # for the beam circulating reversely to the model
            p_i_12 = 1.0-p_i_12
            p_i_13 = 1.0-p_i_13
            phi14 = 1.0-phi14
            phi15 = 1.0-phi15
            phi16 = 1.0-phi16
            phi17 = 1.0-phi17

        p_std_12 = calc_phase_std(p_i_12, 1.0)
        p_std_13 = calc_phase_std(p_i_13, 1.0)
        phstd14 = calc_phase_std(phi14, 1.0)
        phstd15 = calc_phase_std(phi15, 1.0)
        phstd16 = calc_phase_std(phi16, 1.0)
        phstd17 = calc_phase_std(phi17, 1.0)
        
        if plane=='H':
            p_std_12 = 0.00147
            p_std_13 = 0.00147
            phstd14 = 0.00147
            phstd15 = 0.00147
            phstd16 = 0.00147
            phstd17 = 0.00147
        elif plane=='V':
            p_std_12 = 0.0009
            p_std_13 = 0.0009
            phstd14 = 0.0009
            phstd15 = 0.0009
            phstd16 = 0.0009
            phstd17 = 0.0009
        
        
        p_i_12 = calc_phase_mean(p_i_12, 1.0)
        p_i_13 = calc_phase_mean(p_i_13, 1.0)
        phi14 = calc_phase_mean(phi14, 1.0)
        phi15 = calc_phase_mean(phi15, 1.0)
        phi16 = calc_phase_mean(phi16, 1.0)
        phi17 = calc_phase_mean(phi17, 1.0)
        
        if i >= length_commonbpms-6:
            phi17 = _phi_last_and_last_but_one(phi17, tune)
            if i >= length_commonbpms-5:
                phi16 = _phi_last_and_last_but_one(phi16, tune)
            if i >= length_commonbpms-4:
                phi15 = _phi_last_and_last_but_one(phi15, tune)
            if i >= length_commonbpms-3:
                phi14 = _phi_last_and_last_but_one(phi14, tune)                
            if i >= length_commonbpms-2:
                p_i_13 = _phi_last_and_last_but_one(p_i_13, tune)                
            if i >= length_commonbpms-1:
                p_i_12 = _phi_last_and_last_but_one(p_i_12, tune)                

        if plane=='H':
            p_mdl_12=mad_twiss.MUX[mad_twiss.indx[bn2]]-mad_twiss.MUX[mad_twiss.indx[bn1]]
            p_mdl_13=mad_twiss.MUX[mad_twiss.indx[bn3]]-mad_twiss.MUX[mad_twiss.indx[bn1]]
            phmdl14=mad_twiss.MUX[mad_twiss.indx[bn4]]-mad_twiss.MUX[mad_twiss.indx[bn1]]
            phmdl15=mad_twiss.MUX[mad_twiss.indx[bn5]]-mad_twiss.MUX[mad_twiss.indx[bn1]]
            phmdl16=mad_twiss.MUX[mad_twiss.indx[bn6]]-mad_twiss.MUX[mad_twiss.indx[bn1]]
            phmdl17=mad_twiss.MUX[mad_twiss.indx[bn7]]-mad_twiss.MUX[mad_twiss.indx[bn1]]
        elif plane=='V':
            p_mdl_12=mad_twiss.MUY[mad_twiss.indx[bn2]]-mad_twiss.MUY[mad_twiss.indx[bn1]]
            p_mdl_13=mad_twiss.MUY[mad_twiss.indx[bn3]]-mad_twiss.MUY[mad_twiss.indx[bn1]]
            phmdl14=mad_twiss.MUY[mad_twiss.indx[bn4]]-mad_twiss.MUY[mad_twiss.indx[bn1]]
            phmdl15=mad_twiss.MUY[mad_twiss.indx[bn5]]-mad_twiss.MUY[mad_twiss.indx[bn1]]
            phmdl16=mad_twiss.MUY[mad_twiss.indx[bn6]]-mad_twiss.MUY[mad_twiss.indx[bn1]]
            phmdl17=mad_twiss.MUY[mad_twiss.indx[bn7]]-mad_twiss.MUY[mad_twiss.indx[bn1]]
 
        if i >= length_commonbpms-6:
            if plane == 'H':
                madtune = mad_twiss.Q1 % 1.0
            elif plane == 'V':
                madtune = mad_twiss.Q2 % 1.0
            if madtune > 0.5:
                madtune -= 1.0

            phmdl17 = phmdl17 % 1.0
            phmdl17 = _phi_last_and_last_but_one(phmdl17,madtune)
            if i >= length_commonbpms-5:
                phmdl16 = phmdl16 % 1.0
                phmdl16 = _phi_last_and_last_but_one(phmdl16,madtune)                
            if i >= length_commonbpms-4:
                phmdl15 = phmdl15 % 1.0
                phmdl15 = _phi_last_and_last_but_one(phmdl15,madtune)                
            if i >= length_commonbpms-3:
                phmdl14 = phmdl14 % 1.0
                phmdl14 = _phi_last_and_last_but_one(phmdl14,madtune)                
            if i >= length_commonbpms-2:
                p_mdl_13 = p_mdl_13 % 1.0
                p_mdl_13 = _phi_last_and_last_but_one(p_mdl_13,madtune)                
            if i == length_commonbpms-1:
                p_mdl_12 = p_mdl_12 % 1.0
                p_mdl_12 = _phi_last_and_last_but_one(p_mdl_12,madtune)
                                        
        
        if (abs(p_mdl_12) < small):
            p_mdl_12=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn2+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(p_mdl_13) < small):
            p_mdl_13=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn3+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(p_i_12) < small ):
            p_i_12 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn2+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(p_i_13) < small):
            p_i_13 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn3+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phmdl14) < small):
            phmdl14=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn4+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phmdl15) < small):
            phmdl15=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn5+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phi14) < small ):
            phi14 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn4+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phi15) < small):
            phi15 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn5+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phmdl16) < small):
            phmdl16=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn6+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phmdl17) < small):
            phmdl17=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn7+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phi16) < small ):
            phi16 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn6+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phi17) < small):
            phi17 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn7+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
            
        if plane=='H':
            phase["".join(['H',bn1,bn2])] = [p_i_12,p_std_12,p_mdl_12]
            phase["".join(['H',bn1,bn3])] = [p_i_13,p_std_13,p_mdl_13]
            phase["".join(['H',bn1,bn4])] = [phi14,phstd14,phmdl14]
            phase["".join(['H',bn1,bn5])] = [phi15,phstd15,phmdl15]
            phase["".join(['H',bn1,bn6])] = [phi16,phstd16,phmdl16]
            phase["".join(['H',bn1,bn7])] = [phi17,phstd17,phmdl17]
        elif plane=='V':
            phase["".join(['V',bn1,bn2])] = [p_i_12,p_std_12,p_mdl_12]
            phase["".join(['V',bn1,bn3])] = [p_i_13,p_std_13,p_mdl_13]
            phase["".join(['V',bn1,bn4])] = [phi14,phstd14,phmdl14]
            phase["".join(['V',bn1,bn5])] = [phi15,phstd15,phmdl15]
            phase["".join(['V',bn1,bn6])] = [phi16,phstd16,phmdl16]
            phase["".join(['V',bn1,bn7])] = [phi17,phstd17,phmdl17]


    return [phase,tune,mu,commonbpms]


#===================================================================================================
# ac-dipole stuff
#===================================================================================================

def _get_free_phase(phase, tune_ac, tune, bpms, mad_ac, mad_twiss, plane):
    '''
    :Parameters:
        'phase': dict
            (bpm_name:string) --> (phase_list:[phi12,phstd12,phi13,phstd13,phmdl12,phmdl13,bn2])
            phi13, phstd13, phmdl12 and phmdl13 are note used.
        
    '''

    if DEBUG:
        print "Calculating free phase using model"

    phasef = {}
    phi = []

    for bpm in bpms:
        bn1 = bpm[1].upper()

        phase_list = phase[bn1]
        phi12 = phase_list[0]
        phstd12 = phase_list[1]
        bn2 = phase_list[6]
        bn2s = mad_twiss.S[mad_twiss.indx[bn2]]
        #model ac
        if plane == "H":
            ph_ac_m = mad_ac.MUX[mad_ac.indx[bn2]]-mad_ac.MUX[mad_ac.indx[bn1]]
            ph_m = mad_twiss.MUX[mad_twiss.indx[bn2]]-mad_twiss.MUX[mad_twiss.indx[bn1]]
        else:
            ph_ac_m = mad_ac.MUY[mad_ac.indx[bn2]]-mad_ac.MUY[mad_ac.indx[bn1]]
            ph_m = mad_twiss.MUY[mad_twiss.indx[bn2]]-mad_twiss.MUY[mad_twiss.indx[bn1]]

        # take care the last BPM
        if bn1 == bpms[-1][1].upper():
            ph_ac_m += tune_ac 
            ph_ac_m = ph_ac_m % 1
            ph_m += tune
            ph_m = ph_m % 1

        phi12f = phi12-(ph_ac_m-ph_m)
        phi.append(phi12f)
        phstd12f = phstd12
        phmdl12f = ph_m

        phasef[bn1] = phi12f, phstd12f, phmdl12f, bn2, bn2s

    mu = sum(phi)


    return phasef, mu, bpms


def get_free_phase_total(phase, bpms, plane, mad_twiss, mad_ac):
    '''
    :Parameters:
        'phase': dict
            (bpm_name:string) --> (phase_list:[phi12,phstd12,phmdl12,bn1])
            phmdl12 and bn1 are note used.
        
    '''
    if DEBUG:
        print "Calculating free total phase using model"

    first = bpms[0][1]

    phasef = {}

    for bpm in bpms:
        bn2 = bpm[1].upper()

        if plane == "H":

            ph_ac_m = (mad_ac.MUX[mad_ac.indx[bn2]]-mad_ac.MUX[mad_ac.indx[first]])%1
            ph_m = (mad_twiss.MUX[mad_twiss.indx[bn2]]-mad_twiss.MUX[mad_twiss.indx[first]])%1

        else:
            ph_ac_m = (mad_ac.MUY[mad_ac.indx[bn2]]-mad_ac.MUY[mad_ac.indx[first]])%1
            ph_m = (mad_twiss.MUY[mad_twiss.indx[bn2]]-mad_twiss.MUY[mad_twiss.indx[first]])%1

        phase_list = phase[bn2]
        phi12 = phase_list[0]
        phstd12 = phase_list[1]


        phi12 = phi12-(ph_ac_m-ph_m)
        phstd12 = phstd12

        phasef[bn2] = phi12, phstd12, ph_m

    return phasef, bpms