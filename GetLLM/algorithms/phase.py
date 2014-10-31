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
from scipy.special import erfinv


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
        tfs_file.add_float_descriptor("Q1", tune_d.q1)
        tfs_file.add_float_descriptor("MUX", tune_d.mux)
        tfs_file.add_float_descriptor("Q2", tune_d.q2)
        tfs_file.add_float_descriptor("MUY", tune_d.muy)
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
                tfs_file.add_float_descriptor("Q1", tune_d.q1f)
                tfs_file.add_float_descriptor("MUX", tune_d.muxf)
                tfs_file.add_float_descriptor("Q2", tune_d.q2f)
                tfs_file.add_float_descriptor("MUY", tune_d.muyf)
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
            tfs_file.add_float_descriptor("Q1", tune_d.q1f)
            tfs_file.add_float_descriptor("MUX", tune_d.muxf2)
            tfs_file.add_float_descriptor("Q2", tune_d.q2f)
            tfs_file.add_float_descriptor("MUY", tune_d.muyf2)
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
        tfs_file.add_float_descriptor("Q1", tune_d.q1)
        tfs_file.add_float_descriptor("MUX", tune_d.mux)
        tfs_file.add_float_descriptor("Q2", tune_d.q2)
        tfs_file.add_float_descriptor("MUY", tune_d.muy)
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
                tfs_file.add_float_descriptor("Q1", tune_d.q1f)
                tfs_file.add_float_descriptor("MUX", tune_d.muxf)
                tfs_file.add_float_descriptor("Q2", tune_d.q2f)
                tfs_file.add_float_descriptor("MUY", tune_d.muyf)
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
            tfs_file.add_float_descriptor("Q1", tune_d.q1f)
            tfs_file.add_float_descriptor("MUX", tune_d.muxf2)
            tfs_file.add_float_descriptor("Q2", tune_d.q2f)
            tfs_file.add_float_descriptor("MUY", tune_d.muyf2)
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
        tfs_file.add_float_descriptor("Q1", tune_d.q1)
        tfs_file.add_float_descriptor("MUX", tune_d.mux)
        tfs_file.add_float_descriptor("Q2", tune_d.q2)
        tfs_file.add_float_descriptor("MUY", tune_d.muy)
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
                tfs_file.add_float_descriptor("Q1", tune_d.q1f)
                tfs_file.add_float_descriptor("MUX", tune_d.muxf)
                tfs_file.add_float_descriptor("Q2", tune_d.q2f)
                tfs_file.add_float_descriptor("MUY", tune_d.muyf)
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
            tfs_file.add_float_descriptor("Q1", tune_d.q1f)
            tfs_file.add_float_descriptor("MUX", tune_d.muxf2)
            tfs_file.add_float_descriptor("Q2", tune_d.q2f)
            tfs_file.add_float_descriptor("MUY", tune_d.muyf2)
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
        tfs_file.add_float_descriptor("Q1", tune_d.q1)
        tfs_file.add_float_descriptor("MUX", tune_d.mux)
        tfs_file.add_float_descriptor("Q2",tune_d.q2)
        tfs_file.add_float_descriptor("MUY", tune_d.muy)
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
                tfs_file.add_float_descriptor("Q1", tune_d.q1f)
                tfs_file.add_float_descriptor("MUX", tune_d.muxf)
                tfs_file.add_float_descriptor("Q2", tune_d.q2f)
                tfs_file.add_float_descriptor("MUY", tune_d.muyf)
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
            tfs_file.add_float_descriptor("Q1", tune_d.q1f)
            tfs_file.add_float_descriptor("MUX", tune_d.muxf2)
            tfs_file.add_float_descriptor("Q2", tune_d.q2f)
            tfs_file.add_float_descriptor("MUY", tune_d.muyf2)
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
    if ftune <= 0:
        ftune += 1
    phi += ftune
    if phi > 1:
        phi -= 1
    return phi


def qnorm(probability):
    """
    A reimplementation of R's qnorm() function.

    This function calculates the quantile function of the normal
    distributition.
    (http://en.wikipedia.org/wiki/Normal_distribution#Quantile_function)

    Required is the erfinv() function, the inverse error function.
    (http://en.wikipedia.org/wiki/Error_function#Inverse_function)
    """
    if probability > 1 or probability <= 0:
        raise ValueError("Probability has to be between 0 and 1")
    else:
        return np.sqrt(2) * erfinv(2 * probability - 1)


def qt(probability, degrees_of_freedom):
    """
    A reimplementation of R's qt() function.
    
    This function calculates the quantile function of the student's t
    distribution.
    (http://en.wikipedia.org/wiki/Quantile_function#The_Student.27s_t-distribution)
    
    This algorithm has been taken (line-by-line) from Hill, G. W. (1970)
    Algorithm 396: Student's t-quantiles. Communications of the ACM, 
    13(10), 619-620.
    
    Currently unimplemented are the improvements to Algorithm 396 from
    Hill, G. W. (1981) Remark on Algorithm 396, ACM Transactions on 
    Mathematical Software, 7, 250-1.
    """
    n = degrees_of_freedom
    P = probability
    t = 0
    if (n < 1 or P > 1.0 or P <= 0.0 ):
        raise BaseException #TODO: raise a standard/helpful error
    elif (n == 2):
        t = np.sqrt(2.0/(P*(2.0-P)) - 2.0)
    elif (n == 1):
        P = P * np.pi/2
        t = np.cos(P)/np.sin(P)
    else:
        a = 1.0/(n-0.5)
        b = 48.0/(a**2.0)
        c = (((20700.0*a)/b - 98.0)*a - 16.0)*a + 96.36
        d = ((94.5/(b+c) - 3.0)/b + 1.0)*np.sqrt((a*np.pi)/2.0)*float(n)
        x = d*P
        y = x**(2.0/float(n))
    
        if (y > 0.05 + a):
            x = qnorm(P*0.5)
            y = x**2.0
            
            if (n < 5):
                c = c + 0.3*(float(n)-4.5)*(x+0.6)

            #c = (((0.05*d*x-5.0)*x-7.0)*x-2.0)*x+b+c
            c1 = (0.05*d*x) - 5.0
            c2 = c1*x - 7.0
            c3 = c2*x - 2.0
            c4 = c3*x + b + c
            c = c4
            #y = (((((0.4*y+6.3)*y+36.0)*y+94.5)/c-y-3.0)/b+1.0)*x
            y1 = (0.4*y+6.3)*y + 36.0
            y2 = y1*y + 94.5
            y3 = y2/c - y - 3.0
            y4 = y3/b + 1.0
            y5 = y4*x
            y = y5
            
            y = a*(y**2.0)
            
            if (y > 0.002):
                y = np.exp(y) - 1.0
            else:
                y = 0.5*(y**2.0) + y

        else:
            #y = ((1.0/(((float(n)+6.0)/(float(n)*y)-0.089*d-0.822)
            #*(float(n)+2.0)*3.0)+0.5/(float(n)+4.0))*y-1.0)*(float(n)+1.0)
            #/(float(n)+2.0)+1.0/y
            y1 = float(n)+6.0
            y2 = y1/(float(n)*y)
            y3 = y2 - 0.089*d - 0.822
            y4 = y3 * (float(n)+2.0) * 3.0
            y5 = 1.0 / y4
            y6 = y5 + 0.5/(float(n)+4.0)
            y7 = y6*y - 1.0
            y8 = y7 * (float(n)+1.0) 
            y9 = y8 / (float(n)+2.0) 
            y10 = y9 + 1.0/y
            y= y10
        
        t = np.sqrt(float(n)*y)
    
    return t

def calc_phase_mean(phase0, norm):
    ''' phases must be in [0,1) or [0,2*pi), norm = 1 or 2*pi '''
    phase0 = np.array(phase0)%norm
    phase1 = (phase0 + .5*norm) % norm - .5*norm
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
    phase1 = (phase0 + .5*norm) % norm - .5*norm
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
    if len(phase0) > 1:
        phase_std = math.sqrt(min_phase_std/(len(phase0)-1))
        phase_std = phase_std * qt(0.317, len(phase0)-1)
    else:
        phase_std = 0
    return phase_std

def _get_phases_total(mad_twiss, src_files, tune, plane, beam_direction, accel, lhc_phase):
    commonbpms = Utilities.bpm.intersect(src_files)
    commonbpms = Utilities.bpm.model_intersect(commonbpms, mad_twiss)
    #-- Last BPM on the same turn to fix the phase shift by tune for exp data of LHC
    s_lastbpm = None
    if lhc_phase == "1":
        if accel == "LHCB1":
            s_lastbpm = mad_twiss.S[mad_twiss.indx['BPMSW.1L2.B1']]
        elif accel == "LHCB2":
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
            phi12 = 1 - phi12

        #phstd12=math.sqrt(np.average(phi12*phi12)-(np.average(phi12))**2.0+2.2e-15)
        #phi12=np.average(phi12)
        phstd12 = calc_phase_std(phi12, 1.)
        phi12   = calc_phase_mean(phi12, 1.)
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

    if length_commonbpms < 3:
        print >> sys.stderr, "get_phases: Less than three BPMs provided for plane " + plane + ". Please check input."
        return [{}, 0, 0, []]

    #-- Last BPM on the same turn to fix the phase shift by tune_q for exp data of LHC
    if getllm_d.lhc_phase == "1" and getllm_d.accel == "LHCB1":
        s_lastbpm = mad_twiss.S[mad_twiss.indx['BPMSW.1L2.B1']]
    if getllm_d.lhc_phase == "1" and getllm_d.accel == "LHCB2":
        s_lastbpm = mad_twiss.S[mad_twiss.indx['BPMSW.1L8.B2']]

    mu = 0.
    tunem = []
    phase = {} # Dictionary for the output containing [average phase, rms error]

    for i in range(length_commonbpms): # To calculate the tune
        bpm = str.upper(commonbpms[i % length_commonbpms][1])

        tunemi = []
        for src_twiss in ListOfFiles:
            # Phase is in units of 2pi
            if plane == 'H':
                src_twiss_tune_column = src_twiss.TUNEX
            elif plane == 'V':
                src_twiss_tune_column = src_twiss.TUNEY
            tunemi.append(src_twiss_tune_column[src_twiss.indx[bpm]])

        tunemi = np.array(tunemi)
        if i < length_commonbpms-1:
            tunem.append(np.average(tunemi))

        # Note that the phase advance between the last monitor and the first monitor should be find by taking into account the fractional part of tune.
        if i == length_commonbpms-2:
            tunem = np.array(tunem)
            tune = np.average(tunem)

    for i in range(length_commonbpms): # To find the integer part of tune as well, the loop is up to the last monitor
        bpms = [str.upper(commonbpms[j % length_commonbpms][1]) for j in range(i, i+11)] # seven consecutive monitors
        p_i = {1:[], 2:[], 3:[], 4:[], 5:[], 6:[], 7:[], 8:[], 9:[], 10:[]} # dict for the six bpm pairs i.e. p_i[1] is for pair bpm[0], bpm[1]

        for src_twiss in ListOfFiles:
            # Phase is in units of 2pi
            p_m = {}
            if plane == 'H':
                twiss_column = src_twiss.MUX
            elif plane == 'V':
                twiss_column = src_twiss.MUY
            for bpm_pair in p_i:
                p_m[bpm_pair] = twiss_column[src_twiss.indx[bpms[bpm_pair]]] - twiss_column[src_twiss.indx[bpms[0]]]

            #-- To fix the phase shift by tune_q in LHC
            if tune_q is not None:
                try:
                    for bpm_pair in p_m:
                        if mad_twiss.S[mad_twiss.indx[bpms[0]]] <= s_lastbpm and mad_twiss.S[mad_twiss.indx[bpms[bpm_pair]]] > s_lastbpm:
                            p_m[bpm_pair] += getllm_d.beam_direction*tune_q
                        if mad_twiss.S[mad_twiss.indx[bpms[0]]] > s_lastbpm and mad_twiss.S[mad_twiss.indx[bpms[bpm_pair]]]<=s_lastbpm:
                            p_m[bpm_pair] += -getllm_d.beam_direction*tune_q
                except:
                    pass
            for bpm_pair in p_i:
                if p_m[bpm_pair] < 0:
                    p_m[bpm_pair] += 1
                p_i[bpm_pair].append(p_m[bpm_pair])

        for bpm_pair in p_i:
            p_i[bpm_pair] = np.array(p_i[bpm_pair])

        if getllm_d.beam_direction == -1: # for the beam circulating reversely to the model
            for bpm_pair in p_i:
                p_i[bpm_pair] = 1 - p_i[bpm_pair]

        p_std = {}
        for bpm_pair in p_i:
            p_std[bpm_pair] = calc_phase_std(p_i[bpm_pair], 1.)
            p_i[bpm_pair] = calc_phase_mean(p_i[bpm_pair], 1.)

        if i >= length_commonbpms-10:
            p_i[10] = _phi_last_and_last_but_one(p_i[10], tune)
            for j in range(1,10):
                if i >= length_commonbpms-j:
                    p_i[j] = _phi_last_and_last_but_one(p_i[j], tune)

        p_mdl = {}
        if plane == 'H':
            twiss_column = mad_twiss.MUX
        elif plane == 'V':
            twiss_column = mad_twiss.MUY
        for bpm_pair in p_i:
            p_mdl[bpm_pair] = twiss_column[mad_twiss.indx[bpms[bpm_pair]]] - twiss_column[mad_twiss.indx[bpms[0]]]

        if i >= length_commonbpms-10:
            if plane == 'H':
                madtune = mad_twiss.Q1 % 1
            elif plane == 'V':
                madtune = mad_twiss.Q2 % 1
            if madtune > .5:
                madtune -= 1

            p_mdl[10] = p_mdl[10] % 1
            p_mdl[10] = _phi_last_and_last_but_one(p_mdl[10], madtune)
            for j in range(1, len(p_i)): # iterate only over the first 5 bpm pairs
                if i >= length_commonbpms-j:
                    p_mdl[j] = p_mdl[j] % 1
                    p_mdl[j] = _phi_last_and_last_but_one(p_mdl[j], madtune)

        small = 1e-7
        for bpm_pair in p_i:
            if abs(p_mdl[bpm_pair]) < small:
                p_mdl[bpm_pair] = small
                print "Note: Phase advance (Plane" + plane + ") between " + bpms[0] + " and " + bpms[bpm_pair] + " in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
                print "Beta from amplitude around this monitor will be slightly varied."
            if abs(p_i[bpm_pair]) < small:
                p_i[bpm_pair] = small
                print "Note: Phase advance (Plane" + plane + ") between " + bpms[0] + " and " + bpms[bpm_pair] + " in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
                print "Beta from amplitude around this monitor will be slightly varied."
            phase["".join([plane,bpms[0],bpms[bpm_pair]])] = [p_i[bpm_pair], p_std[bpm_pair], p_mdl[bpm_pair]]

        phase[bpms[0]] = [p_i[1], p_std[1], p_i[2], p_std[2], p_mdl[1], p_mdl[2], bpms[1]]

    return [phase, tune, mu, commonbpms]

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
            ph_ac_m = (mad_ac.MUX[mad_ac.indx[bn2]] - mad_ac.MUX[mad_ac.indx[first]]) % 1
            ph_m = (mad_twiss.MUX[mad_twiss.indx[bn2]] - mad_twiss.MUX[mad_twiss.indx[first]]) % 1
        else:
            ph_ac_m = (mad_ac.MUY[mad_ac.indx[bn2]] - mad_ac.MUY[mad_ac.indx[first]]) % 1
            ph_m = (mad_twiss.MUY[mad_twiss.indx[bn2]] - mad_twiss.MUY[mad_twiss.indx[first]]) % 1

        phase_list = phase[bn2]
        phi12 = phase_list[0]
        phstd12 = phase_list[1]

        phi12 = phi12-(ph_ac_m-ph_m)
        phstd12 = phstd12

        phasef[bn2] = phi12, phstd12, ph_m

    return phasef, bpms