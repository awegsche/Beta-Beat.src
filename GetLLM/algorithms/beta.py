'''
Created on 27 May 2013

@author: ?, vimaier

@version: 0.0.1

GetLLM.algorithms.beta.py stores helper functions for phase calculations for GetLLM.
This module is not intended to be executed. It stores only functions.

Change history:
 - <version>, <author>, <date>:
    <description>
'''

import sys
import math
import traceback

import numpy as np
from numpy import sin, cos, tan

import Utilities.bpm
import compensate_ac_effect
import os


DEBUG = sys.flags.debug  # True with python option -d! ("python -d GetLLM.py...") (vimaier)
DEFAULT_WRONG_BETA = 1000


#===================================================================================================
# main part
#===================================================================================================
class BetaData(object):
    """ File for storing results from beta computations. """

    def __init__(self):
        self.x_phase = None  # beta x from phase
        self.x_phase_f = None  # beta x from phase free
        self.y_phase = None  # beta y from phase
        self.y_phase_f = None  # beta y from phase free

        self.x_amp = None  # beta x from amplitude
        self.y_amp = None  # beta y from amplitude

        self.x_ratio = None  # beta x ratio
        self.x_ratio_f = None  # beta x ratio free
        self.y_ratio = None  # beta x ratio
        self.y_ratio_f = None  # beta x ratio free


def calculate_beta_from_phase(getllm_d, twiss_d, tune_d, phase_d, mad_twiss, mad_ac, mad_best_knowledge,
                              mad_ac_best_knowledge, files_dict, use_only_three_bpms_for_beta_from_phase):
    '''
    Calculates beta and fills the following TfsFiles:
        getbetax.out        getbetax_free.out        getbetax_free2.out
        getbetay.out        getbetay_free.out        getbetay_free2.out

    :Parameters:
        'getllm_d': _GetllmData (In-param, values will only be read)
            lhc_phase, accel and beam_direction are used.
        'twiss_d': _TwissData (In-param, values will only be read)
            Holds twiss instances of the src files.
        'tune_d': _TuneData (In-param, values will only be read)
            Holds tunes and phase advances
        'phase_d': _PhaseData (In-param, values will only be read)
            Holds results from get_phases
    '''
    beta_d = BetaData()

    print 'Calculating beta'
    #---- H plane
    if twiss_d.has_zero_dpp_x():
        [beta_d.x_phase, rmsbbx, alfax, bpms] = beta_from_phase(mad_ac_best_knowledge, twiss_d.zero_dpp_x, phase_d.ph_x, 'H', use_only_three_bpms_for_beta_from_phase)
        beta_d.x_phase['DPP'] = 0
        tfs_file = files_dict['getbetax.out']
        tfs_file.add_float_descriptor("Q1", tune_d.q1)
        tfs_file.add_float_descriptor("Q2", tune_d.q2)
        tfs_file.add_float_descriptor("RMSbetabeat", rmsbbx)
        tfs_file.add_column_names(["NAME", "S", "COUNT", "BETX", "ERRBETX", "STDBETX", "ALFX", "ERRALFX", "STDALFX", "BETXMDL", "ALFXMDL", "MUXMDL"])
        tfs_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
        for i in range(0, len(bpms)):
            bn1 = str.upper(bpms[i][1])
            bns1 = bpms[i][0]
            list_row_entries = ['"' + bn1 + '"', bns1, len(twiss_d.zero_dpp_x), beta_d.x_phase[bn1][0], beta_d.x_phase[bn1][1], beta_d.x_phase[bn1][2], alfax[bn1][0], alfax[bn1][1], alfax[bn1][2], mad_ac.BETX[mad_ac.indx[bn1]], mad_ac.ALFX[mad_ac.indx[bn1]], mad_ac.MUX[mad_ac.indx[bn1]]]
            tfs_file.add_table_row(list_row_entries)

        #-- ac to free beta
        if getllm_d.with_ac_calc:
            #-- from eq
            try:
                [beta_d.x_phase_f, rmsbbxf, alfaxf, bpmsf] = beta_from_phase(mad_best_knowledge, twiss_d.zero_dpp_x, phase_d.x_f, 'H', use_only_three_bpms_for_beta_from_phase)
                tfs_file = files_dict['getbetax_free.out']
                tfs_file.add_float_descriptor("Q1", tune_d.q1f)
                tfs_file.add_float_descriptor("Q2", tune_d.q2f)
                tfs_file.add_float_descriptor("RMSbetabeat", rmsbbxf)
                tfs_file.add_column_names(["NAME", "S", "COUNT", "BETX", "ERRBETX", "STDBETX", "ALFX", "ERRALFX", "STDALFX", "BETXMDL", "ALFXMDL", "MUXMDL"])
                tfs_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
                for i in range(0, len(bpmsf)):
                    bn1 = str.upper(bpmsf[i][1])
                    bns1 = bpmsf[i][0]
                    list_row_entries = ['"' + bn1 + '"', bns1, len(twiss_d.zero_dpp_x), beta_d.x_phase_f[bn1][0], beta_d.x_phase_f[bn1][1], beta_d.x_phase_f[bn1][2], alfaxf[bn1][0], alfaxf[bn1][1], alfaxf[bn1][2], mad_twiss.BETX[mad_twiss.indx[bn1]], mad_twiss.ALFX[mad_twiss.indx[bn1]], mad_twiss.MUX[mad_twiss.indx[bn1]]]
                    tfs_file.add_table_row(list_row_entries)
            except:
                traceback.print_exc()

            #-- from the model
            [betaxf2, rmsbbxf2, alfaxf2, bpmsf2] = _get_free_beta(mad_ac, mad_twiss, beta_d.x_phase, rmsbbx, alfax, bpms, 'H')
            tfs_file = files_dict['getbetax_free2.out']
            tfs_file.add_float_descriptor("Q1", tune_d.q1f)
            tfs_file.add_float_descriptor("Q2", tune_d.q2f)
            tfs_file.add_float_descriptor("RMSbetabeat", rmsbbxf2)
            tfs_file.add_column_names(["NAME", "S", "COUNT", "BETX", "ERRBETX", "STDBETX", "ALFX", "ERRALFX", "STDALFX", "BETXMDL", "ALFXMDL", "MUXMDL"])
            tfs_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
            for i in range(0, len(bpmsf2)):
                bn1 = str.upper(bpmsf2[i][1])
                bns1 = bpmsf2[i][0]
                list_row_entries = ['"' + bn1 + '"', bns1, len(twiss_d.zero_dpp_x), betaxf2[bn1][0], betaxf2[bn1][1], betaxf2[bn1][2], alfaxf2[bn1][0], alfaxf2[bn1][1], alfaxf2[bn1][2], mad_twiss.BETX[mad_twiss.indx[bn1]], mad_twiss.ALFX[mad_twiss.indx[bn1]], mad_twiss.MUX[mad_twiss.indx[bn1]]]
                tfs_file.add_table_row(list_row_entries)

    #---- V plane
    if twiss_d.has_zero_dpp_y():
        [beta_d.y_phase, rmsbby, alfay, bpms] = beta_from_phase(mad_ac_best_knowledge, twiss_d.zero_dpp_y, phase_d.ph_y, 'V', use_only_three_bpms_for_beta_from_phase)
        beta_d.y_phase['DPP'] = 0
        tfs_file = files_dict['getbetay.out']
        tfs_file.add_float_descriptor("Q1", tune_d.q1)
        tfs_file.add_float_descriptor("Q2", tune_d.q2)
        tfs_file.add_float_descriptor("RMSbetabeat", rmsbby)
        tfs_file.add_column_names(["NAME", "S", "COUNT", "BETY", "ERRBETY", "STDBETY", "ALFY", "ERRALFY", "STDALFY", "BETYMDL", "ALFYMDL", "MUYMDL"])
        tfs_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
        for i in range(0, len(bpms)):
            bn1 = str.upper(bpms[i][1])
            bns1 = bpms[i][0]
            list_row_entries = ['"' + bn1 + '"', bns1, len(twiss_d.zero_dpp_y), beta_d.y_phase[bn1][0], beta_d.y_phase[bn1][1], beta_d.y_phase[bn1][2], alfay[bn1][0], alfay[bn1][1], alfay[bn1][2], mad_ac.BETY[mad_ac.indx[bn1]], mad_ac.ALFY[mad_ac.indx[bn1]], mad_ac.MUY[mad_ac.indx[bn1]]]
            tfs_file.add_table_row(list_row_entries)

        #-- ac to free beta
        if getllm_d.with_ac_calc:
            #-- from eq
            try:
                [beta_d.y_phase_f, rmsbbyf, alfayf, bpmsf] = beta_from_phase(mad_best_knowledge, twiss_d.zero_dpp_y, phase_d.y_f, 'V', use_only_three_bpms_for_beta_from_phase)
                tfs_file = files_dict['getbetay_free.out']
                tfs_file.add_float_descriptor("Q1", tune_d.q1f)
                tfs_file.add_float_descriptor("Q2", tune_d.q2f)
                tfs_file.add_float_descriptor("RMSbetabeat", rmsbbyf)
                tfs_file.add_column_names(["NAME", "S", "COUNT", "BETY", "ERRBETY", "STDBETY", "ALFY", "ERRALFY", "STDALFY", "BETYMDL", "ALFYMDL", "MUYMDL"])
                tfs_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
                for i in range(0, len(bpmsf)):
                    bn1 = str.upper(bpmsf[i][1])
                    bns1 = bpmsf[i][0]
                    list_row_entries = ['"' + bn1 + '"', bns1, len(twiss_d.zero_dpp_y), beta_d.y_phase_f[bn1][0], beta_d.y_phase_f[bn1][1], beta_d.y_phase_f[bn1][2], alfayf[bn1][0], alfayf[bn1][1], alfayf[bn1][2], mad_twiss.BETY[mad_twiss.indx[bn1]], mad_twiss.ALFY[mad_twiss.indx[bn1]], mad_twiss.MUY[mad_twiss.indx[bn1]]]
                    tfs_file.add_table_row(list_row_entries)
            except:
                traceback.print_exc()

            #-- from the model
            [betayf2, rmsbbyf2, alfayf2, bpmsf2] = _get_free_beta(mad_ac, mad_twiss, beta_d.y_phase, rmsbby, alfay, bpms, 'V')
            tfs_file = files_dict['getbetay_free2.out']
            tfs_file.add_float_descriptor("Q1", tune_d.q1f)
            tfs_file.add_float_descriptor("Q2", tune_d.q2f)
            tfs_file.add_float_descriptor("RMSbetabeat", rmsbbyf2)
            tfs_file.add_column_names(["NAME", "S", "COUNT", "BETY", "ERRBETY", "STDBETY", "ALFY", "ERRALFY", "STDALFY", "BETYMDL", "ALFYMDL", "MUYMDL"])
            tfs_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
            for i in range(0, len(bpmsf2)):
                bn1 = str.upper(bpmsf2[i][1])
                bns1 = bpmsf2[i][0]
                list_row_entries = ['"' + bn1 + '"', bns1, len(twiss_d.zero_dpp_y), betayf2[bn1][0], betayf2[bn1][1], betayf2[bn1][2], alfayf2[bn1][0], alfayf2[bn1][1], alfayf2[bn1][2], mad_twiss.BETY[mad_twiss.indx[bn1]], mad_twiss.ALFY[mad_twiss.indx[bn1]], mad_twiss.MUY[mad_twiss.indx[bn1]]]
                tfs_file.add_table_row(list_row_entries)

    return beta_d
# END calculate_beta_from_phase -------------------------------------------------------------------------------


def calculate_beta_from_amplitude(getllm_d, twiss_d, tune_d, phase_d, beta_d, mad_twiss, mad_ac, files_dict):
    '''
    Calculates beta and fills the following TfsFiles:
        getampbetax.out        getampbetax_free.out        getampbetax_free2.out
        getampbetay.out        getampbetay_free.out        getampbetay_free2.out

    :Parameters:
        'getllm_d': _GetllmData (In-param, values will only be read)
            accel and beam_direction are used.
        'twiss_d': _TwissData (In-param, values will only be read)
            Holds twiss instances of the src files.
        'tune_d': _TuneData (In-param, values will only be read)
            Holds tunes and phase advances
        'phase_d': _PhaseData (In-param, values will only be read)
            Holds results from get_phases
        'beta_d': _BetaData (In/Out-param, values will be read and set)
            Holds results from get_beta. Beta from amp and ratios will be set.

    :Return: _BetaData
        the same instance as param beta_d to indicate that x_amp,y_amp and ratios were set.
    '''
    print 'Calculating beta from amplitude'

    #---- H plane
    if twiss_d.has_zero_dpp_x():
        [beta_d.x_amp, rmsbbx, bpms, inv_jx] = beta_from_amplitude(mad_ac, twiss_d.zero_dpp_x, 'H')
        beta_d.x_amp['DPP'] = 0
        #-- Rescaling
        beta_d.x_ratio = 0
        skipped_bpmx = []
        arcbpms = Utilities.bpm.filterbpm(bpms)
        for bpm in arcbpms:
            name = str.upper(bpm[1])  # second entry is the name
        #Skip BPM with strange data
            if abs(beta_d.x_phase[name][0] / beta_d.x_amp[name][0]) > 100:
                skipped_bpmx.append(name)
            elif (beta_d.x_amp[name][0] < 0 or beta_d.x_phase[name][0] < 0):
                skipped_bpmx.append(name)
            else:
                beta_d.x_ratio = beta_d.x_ratio + (beta_d.x_phase[name][0] / beta_d.x_amp[name][0])

        try:
            beta_d.x_ratio = beta_d.x_ratio / (len(arcbpms) - len(skipped_bpmx))
        except ZeroDivisionError:
            beta_d.x_ratio = 1
        except:
            traceback.print_exc()
            beta_d.x_ratio = 1

        betax_rescale = {}

        for bpm in bpms:
            name = str.upper(bpm[1])
            betax_rescale[name] = [beta_d.x_ratio * beta_d.x_amp[name][0], beta_d.x_ratio * beta_d.x_amp[name][1], beta_d.x_amp[name][2]]

        tfs_file = files_dict['getampbetax.out']
        tfs_file.add_float_descriptor("Q1", tune_d.q1)
        tfs_file.add_float_descriptor("Q2", tune_d.q2)
        tfs_file.add_float_descriptor("RMSbetabeat", rmsbbx)
        tfs_file.add_float_descriptor("RescalingFactor", beta_d.x_ratio)
        tfs_file.add_column_names(["NAME", "S", "COUNT", "BETX", "BETXSTD", "BETXMDL", "MUXMDL", "BETXRES", "BETXSTDRES"])
        tfs_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
        for i in range(0, len(bpms)):
            bn1 = str.upper(bpms[i][1])
            bns1 = bpms[i][0]
            list_row_entries = ['"' + bn1 + '"', bns1, len(twiss_d.zero_dpp_x), beta_d.x_amp[bn1][0], beta_d.x_amp[bn1][1], mad_ac.BETX[mad_ac.indx[bn1]], mad_ac.MUX[mad_ac.indx[bn1]], betax_rescale[bn1][0], betax_rescale[bn1][1]]
            tfs_file.add_table_row(list_row_entries)

        #-- ac to free amp beta
        if getllm_d.with_ac_calc:
            #-- from eq
            try:
                betaxf, rmsbbxf, bpmsf, _ = compensate_ac_effect.get_free_beta_from_amp_eq(mad_ac, twiss_d.zero_dpp_x, tune_d.q1, tune_d.q1f, phase_d.acphasex_ac2bpmac, 'H', getllm_d.beam_direction, getllm_d.lhc_phase)
                #-- Rescaling
                beta_d.x_ratio_f = 0
                skipped_bpmxf = []
                arcbpms = Utilities.bpm.filterbpm(bpmsf)
                for bpm in arcbpms:
                    name = str.upper(bpm[1])  # second entry is the name
                #Skip BPM with strange data
                    if abs(beta_d.x_phase_f[name][0] / betaxf[name][0]) > 10:
                        skipped_bpmxf.append(name)
                    elif abs(beta_d.x_phase_f[name][0] / betaxf[name][0]) < 0.1:
                        skipped_bpmxf.append(name)
                    elif (betaxf[name][0] < 0 or beta_d.x_phase_f[name][0] < 0):
                        skipped_bpmxf.append(name)
                    else:
                        beta_d.x_ratio_f = beta_d.x_ratio_f + (beta_d.x_phase_f[name][0] / betaxf[name][0])

                try:
                    beta_d.x_ratio_f = beta_d.x_ratio_f / (len(arcbpms) - len(skipped_bpmxf))
                except:
                    traceback.print_exc()
                    beta_d.x_ratio_f = 1
                tfs_file = files_dict['getampbetax_free.out']
                tfs_file.add_float_descriptor("Q1", tune_d.q1f)
                tfs_file.add_float_descriptor("Q2", tune_d.q2f)
                tfs_file.add_float_descriptor("RMSbetabeat", rmsbbxf)
                tfs_file.add_float_descriptor("RescalingFactor", beta_d.x_ratio_f)
                tfs_file.add_column_names(["NAME", "S", "COUNT", "BETX", "BETXSTD", "BETXMDL", "MUXMDL", "BETXRES", "BETXSTDRES"])
                tfs_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
                for i in range(0, len(bpmsf)):
                    bn1 = str.upper(bpmsf[i][1])
                    bns1 = bpmsf[i][0]
                    list_row_entries = ['"' + bn1 + '"', bns1, len(twiss_d.zero_dpp_x), betaxf[bn1][0], betaxf[bn1][1], mad_twiss.BETX[mad_twiss.indx[bn1]], mad_twiss.MUX[mad_twiss.indx[bn1]], beta_d.x_ratio_f * betaxf[bn1][0], beta_d.x_ratio_f * betaxf[bn1][1]]
                    tfs_file.add_table_row(list_row_entries)

            except:
                traceback.print_exc()
            #-- from the model
            # Since invJxf2(return_value[3]) is not used, slice the return value([:3]) (vimaier)
            [betaxf2, rmsbbxf2, bpmsf2] = _get_free_amp_beta(beta_d.x_amp, rmsbbx, bpms, inv_jx, mad_ac, mad_twiss, 'H')[:3]
            betaxf2_rescale = _get_free_amp_beta(betax_rescale, rmsbbx, bpms, inv_jx, mad_ac, mad_twiss, 'H')[0]
            tfs_file = files_dict['getampbetax_free2.out']
            tfs_file.add_float_descriptor("Q1", tune_d.q1f)
            tfs_file.add_float_descriptor("Q2", tune_d.q2f)
            tfs_file.add_float_descriptor("RMSbetabeat", rmsbbxf2)
            tfs_file.add_float_descriptor("RescalingFactor", beta_d.x_ratio)
            tfs_file.add_column_names(["NAME", "S", "COUNT", "BETX", "BETXSTD", "BETXMDL", "MUXMDL", "BETXRES", "BETXSTDRES"])
            tfs_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
            for i in range(0, len(bpmsf2)):
                bn1 = str.upper(bpmsf2[i][1])
                bns1 = bpmsf2[i][0]
                list_row_entries = ['"' + bn1 + '"', bns1, len(twiss_d.zero_dpp_x), betaxf2[bn1][0], betaxf2[bn1][1], mad_twiss.BETX[mad_twiss.indx[bn1]], mad_twiss.MUX[mad_twiss.indx[bn1]], betaxf2_rescale[bn1][0], betaxf2_rescale[bn1][1]]
                tfs_file.add_table_row(list_row_entries)  # V plane

    if twiss_d.has_zero_dpp_y():
        [beta_d.y_amp, rmsbby, bpms, inv_jy] = beta_from_amplitude(mad_ac, twiss_d.zero_dpp_y, 'V')
        beta_d.y_amp['DPP'] = 0
        #-- Rescaling
        beta_d.y_ratio = 0
        skipped_bpmy = []
        arcbpms = Utilities.bpm.filterbpm(bpms)
        for bpm in arcbpms:
            name = str.upper(bpm[1])  # second entry is the name
            #Skip BPM with strange data
            if name in beta_d.y_phase:
                if abs(beta_d.y_phase[name][0] / beta_d.y_amp[name][0]) > 100:
                    skipped_bpmy.append(name)
                elif (beta_d.y_amp[name][0] < 0 or beta_d.y_phase[name][0] < 0):
                    skipped_bpmy.append(name)
                else:
                    beta_d.y_ratio = beta_d.y_ratio + (beta_d.y_phase[name][0] / beta_d.y_amp[name][0])

        try:
            beta_d.y_ratio = beta_d.y_ratio / (len(arcbpms) - len(skipped_bpmy))
        except ZeroDivisionError:
            beta_d.y_ratio = 1
        betay_rescale = {}

        for bpm in bpms:
            name = str.upper(bpm[1])
            betay_rescale[name] = [beta_d.y_ratio * beta_d.y_amp[name][0], beta_d.y_ratio * beta_d.y_amp[name][1], beta_d.y_amp[name][2]]

        tfs_file = files_dict['getampbetay.out']
        tfs_file.add_float_descriptor("Q1", tune_d.q1)
        tfs_file.add_float_descriptor("Q2", tune_d.q2)
        tfs_file.add_float_descriptor("RMSbetabeat", rmsbby)
        tfs_file.add_float_descriptor("RescalingFactor", beta_d.y_ratio)
        tfs_file.add_column_names(["NAME", "S", "COUNT", "BETY", "BETYSTD", "BETYMDL", "MUYMDL", "BETYRES", "BETYSTDRES"])
        tfs_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
        for i in range(0, len(bpms)):
            bn1 = str.upper(bpms[i][1])
            bns1 = bpms[i][0]
            list_row_entries = ['"' + bn1 + '"', bns1, len(twiss_d.zero_dpp_y), beta_d.y_amp[bn1][0], beta_d.y_amp[bn1][1], mad_ac.BETY[mad_ac.indx[bn1]], mad_ac.MUY[mad_ac.indx[bn1]], betay_rescale[bn1][0], betay_rescale[bn1][1]]
            tfs_file.add_table_row(list_row_entries)  # ac to free amp beta

        if getllm_d.with_ac_calc:  # from eq
            try:
                betayf, rmsbbyf, bpmsf, _ = compensate_ac_effect.get_free_beta_from_amp_eq(mad_ac, twiss_d.zero_dpp_y, tune_d.q2, tune_d.q2f, phase_d.acphasey_ac2bpmac, 'V', getllm_d.beam_direction, getllm_d.accel)  # Rescaling
                beta_d.y_ratio_f = 0
                skipped_bpmyf = []
                arcbpms = Utilities.bpm.filterbpm(bpmsf)
                for bpm in arcbpms:
                    name = str.upper(bpm[1])  # second entry is the name
                    #Skip BPM with strange data
                    if abs(beta_d.y_phase_f[name][0] / betayf[name][0]) > 10:
                        skipped_bpmyf.append(name)
                    elif (betayf[name][0] < 0 or beta_d.y_phase_f[name][0] < 0):
                        skipped_bpmyf.append(name)
                    elif abs(beta_d.y_phase_f[name][0] / betayf[name][0]) < 0.1:
                        skipped_bpmyf.append(name)
                    else:
                        beta_d.y_ratio_f = beta_d.y_ratio_f + (beta_d.y_phase_f[name][0] / betayf[name][0])

                try:
                    beta_d.y_ratio_f = beta_d.y_ratio_f / (len(arcbpms) - len(skipped_bpmyf))
                except ZeroDivisionError:
                    beta_d.y_ratio_f = 1
                tfs_file = files_dict['getampbetay_free.out']
                tfs_file.add_float_descriptor("Q1", tune_d.q1f)
                tfs_file.add_float_descriptor("Q2", tune_d.q2f)
                tfs_file.add_float_descriptor("RMSbetabeat", rmsbbyf)
                tfs_file.add_float_descriptor("RescalingFactor", beta_d.y_ratio_f)
                tfs_file.add_column_names(["NAME", "S", "COUNT", "BETY", "BETYSTD", "BETYMDL", "MUYMDL", "BETYRES", "BETYSTDRES"])
                tfs_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
                for i in range(0, len(bpmsf)):
                    bn1 = str.upper(bpmsf[i][1])
                    bns1 = bpmsf[i][0]
                    list_row_entries = ['"' + bn1 + '"', bns1, len(twiss_d.zero_dpp_y), betayf[bn1][0], betayf[bn1][1], mad_twiss.BETY[mad_twiss.indx[bn1]], mad_twiss.MUY[mad_twiss.indx[bn1]], (beta_d.y_ratio_f * betayf[bn1][0]), (beta_d.y_ratio_f * betayf[bn1][1])]
                    tfs_file.add_table_row(list_row_entries)  # 'except ALL' catched a SystemExit from filterbpm().(vimaier)

            except SystemExit:
                traceback.print_exc()
                sys.exit(1)
            except:
                #-- from the model
                traceback.print_exc()
            # Since invJyf2(return_value[3]) is not used, slice the return value([:3]) (vimaier)
            [betayf2, rmsbbyf2, bpmsf2] = _get_free_amp_beta(beta_d.y_amp, rmsbby, bpms, inv_jy, mad_ac, mad_twiss, 'V')[:3]
            betayf2_rescale = _get_free_amp_beta(betay_rescale, rmsbby, bpms, inv_jy, mad_ac, mad_twiss, 'V')[0]
            tfs_file = files_dict['getampbetay_free2.out']
            tfs_file.add_float_descriptor("Q1", tune_d.q1f)
            tfs_file.add_float_descriptor("Q2", tune_d.q2f)
            tfs_file.add_float_descriptor("RMSbetabeat", rmsbbyf2)
            tfs_file.add_float_descriptor("RescalingFactor", beta_d.y_ratio)
            tfs_file.add_column_names(["NAME", "S", "COUNT", "BETY", "BETYSTD", "BETYMDL", "MUYMDL", "BETYRES", "BETYSTDRES"])
            tfs_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le", "%le", "%le", "%le", "%le"])
            for i in range(0, len(bpmsf2)):
                bn1 = str.upper(bpmsf2[i][1])
                bns1 = bpmsf2[i][0]
                list_row_entries = ['"' + bn1 + '"', bns1, len(twiss_d.zero_dpp_y), betayf2[bn1][0], betayf2[bn1][1], mad_twiss.BETY[mad_twiss.indx[bn1]], mad_twiss.MUY[mad_twiss.indx[bn1]], betayf2_rescale[bn1][0], betayf2_rescale[bn1][1]]
                tfs_file.add_table_row(list_row_entries)

    return beta_d
# END calculate_beta_from_amplitude ----------------------------------------------------------------


#===================================================================================================
# helper-functions
#===================================================================================================


def get_best_three_bpms_with_beta_and_alfa(MADTwiss, phase, plane, commonbpms, i, use_only_three_bpms_for_beta_from_phase):
    '''
    Chooses three BPM sets for the beta calculation from combinations of 7 BPMs.
    If less than 7 BPMs are available it will fall back to using only next neighbours.
    :Parameters:
        'MADTwiss':twiss
            model twiss file
        'phase':dict
            measured phase advances
        'plane':string
            'H' or 'V'
        'commonbpms':list
            intersection of common BPMs in measurement files and model
        'i': integer
            current iterator in the loop of all BPMs
    :Return: tupel(candidate1, candidate2, candidate3, bn4)
        'candidate1-3':list
            contains calculated beta and alfa
        'bn4':string
            name of the probed BPM
    '''

    NUM_BPM_COMBOS = 3
    RANGE = 7
    probed_index = int((RANGE-1)/2.)

    if 7 > len(commonbpms):
        bn1 = str.upper(commonbpms[i % len(commonbpms)][1])
        bn2 = str.upper(commonbpms[(i + 1) % len(commonbpms)][1])
        bn3 = str.upper(commonbpms[(i + 2) % len(commonbpms)][1])
        bn4 = str.upper(commonbpms[(i + 3) % len(commonbpms)][1])
        bn5 = str.upper(commonbpms[(i + 4) % len(commonbpms)][1])
        candidates = []
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_right(bn1, bn2, bn3, MADTwiss, phase, plane)
        candidates.append([tbetstd, tbet, talfstd, talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_mid(bn2, bn3, bn4, MADTwiss, phase, plane)
        candidates.append([tbetstd, tbet, talfstd, talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_left(bn3, bn4, bn5, MADTwiss, phase, plane)
        candidates.append([tbetstd, tbet, talfstd, talf])
        return candidates[0], candidates[1], candidates[2], bn3

    bpm_name = {}
    for n in range(RANGE):
        bpm_name[n] = str.upper(commonbpms[(i + n) % len(commonbpms)][1])
    # bn1 = str.upper(commonbpms[i % len(commonbpms)][1])
    # bn2 = str.upper(commonbpms[(i + 1) % len(commonbpms)][1])
    # bn3 = str.upper(commonbpms[(i + 2) % len(commonbpms)][1])
    # bn4 = str.upper(commonbpms[(i + 3) % len(commonbpms)][1])
    # bn5 = str.upper(commonbpms[(i + 4) % len(commonbpms)][1])
    # bn6 = str.upper(commonbpms[(i + 5) % len(commonbpms)][1])
    # bn7 = str.upper(commonbpms[(i + 6) % len(commonbpms)][1])
    # bn8 = str.upper(commonbpms[(i + 7) % len(commonbpms)][1])
    # bn9 = str.upper(commonbpms[(i + 8) % len(commonbpms)][1])
    # bn10 = str.upper(commonbpms[(i + 9) % len(commonbpms)][1])
    # bn11 = str.upper(commonbpms[(i + 10) % len(commonbpms)][1])
    phase_err = {}
    if plane == 'H':
        for i in range(RANGE):
            if i < probed_index:
                phase_err[i] = phase["".join([plane, bpm_name[i], bpm_name[probed_index]])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bpm_name[i]]] / MADTwiss.BETX[MADTwiss.indx[bpm_name[probed_index]]])
            elif i > probed_index:
                phase_err[i] = phase["".join([plane, bpm_name[probed_index], bpm_name[i]])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bpm_name[i]]] / MADTwiss.BETX[MADTwiss.indx[bpm_name[probed_index]]])
        phase_err[probed_index] = min([phase["".join([plane, bpm_name[i], bpm_name[probed_index]])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bpm_name[probed_index]]] / MADTwiss.BETX[MADTwiss.indx[bpm_name[i]]]) for i in range(probed_index)] + [phase["".join([plane, bpm_name[probed_index], bpm_name[probed_index + 1 + i]])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bpm_name[probed_index]]] / MADTwiss.BETX[MADTwiss.indx[bpm_name[probed_index + 1 + i]]]) for i in range(probed_index)])
    if plane == 'V':
        for i in range(RANGE):
            if i < probed_index:
                phase_err[i] = phase["".join([plane, bpm_name[i], bpm_name[probed_index]])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bpm_name[i]]] / MADTwiss.BETY[MADTwiss.indx[bpm_name[probed_index]]])
            if i > probed_index:
                phase_err[i] = phase["".join([plane, bpm_name[probed_index], bpm_name[i]])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bpm_name[i]]] / MADTwiss.BETY[MADTwiss.indx[bpm_name[probed_index]]])
        phase_err[probed_index] = min([phase["".join([plane, bpm_name[i], bpm_name[probed_index]])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bpm_name[probed_index]]] / MADTwiss.BETY[MADTwiss.indx[bpm_name[i]]]) for i in range(probed_index)] + [phase["".join([plane, bpm_name[probed_index], bpm_name[probed_index + 1 + i]])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bpm_name[probed_index]]] / MADTwiss.BETY[MADTwiss.indx[bpm_name[probed_index + 1 + i]]]) for i in range(probed_index)])
    # if plane == 'H':

    #     p6 = min([phase["".join([plane, bn1, bn6])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn6]] / MADTwiss.BETX[MADTwiss.indx[bn1]]), phase["".join([plane, bn2, bn6])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn6]] / MADTwiss.BETX[MADTwiss.indx[bn2]]), phase["".join([plane, bn3, bn6])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn6]] / MADTwiss.BETX[MADTwiss.indx[bn3]]), phase["".join([plane, bn4, bn6])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn6]] / MADTwiss.BETX[MADTwiss.indx[bn4]]), phase["".join([plane, bn5, bn6])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn6]] / MADTwiss.BETX[MADTwiss.indx[bn5]]), phase["".join([plane, bn6, bn7])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn6]] / MADTwiss.BETX[MADTwiss.indx[bn7]]), phase["".join([plane, bn6, bn8])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn6]] / MADTwiss.BETX[MADTwiss.indx[bn8]]), phase["".join([plane, bn6, bn9])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn6]] / MADTwiss.BETX[MADTwiss.indx[bn9]]), phase["".join([plane, bn6, bn10])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn6]] / MADTwiss.BETX[MADTwiss.indx[bn10]]), phase["".join([plane, bn6, bn11])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn6]] / MADTwiss.BETX[MADTwiss.indx[bn11]])])
    #     p1 = phase["".join([plane, bn1, bn6])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn1]] / MADTwiss.BETX[MADTwiss.indx[bn6]])
    #     p2 = phase["".join([plane, bn2, bn6])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn2]] / MADTwiss.BETX[MADTwiss.indx[bn6]])
    #     p3 = phase["".join([plane, bn3, bn6])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn3]] / MADTwiss.BETX[MADTwiss.indx[bn6]])
    #     p4 = phase["".join([plane, bn4, bn6])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn4]] / MADTwiss.BETX[MADTwiss.indx[bn6]])
    #     p5 = phase["".join([plane, bn5, bn6])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn5]] / MADTwiss.BETX[MADTwiss.indx[bn6]])
    #     p7 = phase["".join([plane, bn6, bn7])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn7]] / MADTwiss.BETX[MADTwiss.indx[bn6]])
    #     p8 = phase["".join([plane, bn6, bn8])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn8]] / MADTwiss.BETX[MADTwiss.indx[bn6]])
    #     p9 = phase["".join([plane, bn6, bn9])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn9]] / MADTwiss.BETX[MADTwiss.indx[bn6]])
    #     p10 = phase["".join([plane, bn6, bn10])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn10]] / MADTwiss.BETX[MADTwiss.indx[bn6]])
    #     p11 = phase["".join([plane, bn6, bn11])][1] / np.sqrt(1 + MADTwiss.BETX[MADTwiss.indx[bn11]] / MADTwiss.BETX[MADTwiss.indx[bn6]])

    # if plane == 'V':
    #     p4 = min([phase["".join([plane, bn1, bn6])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bn6]] / MADTwiss.BETY[MADTwiss.indx[bn1]]), phase["".join([plane, bn2, bn6])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bn6]] / MADTwiss.BETY[MADTwiss.indx[bn2]]), phase["".join([plane, bn3, bn6])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bn6]] / MADTwiss.BETY[MADTwiss.indx[bn3]]), phase["".join([plane, bn6, bn5])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bn6]] / MADTwiss.BETY[MADTwiss.indx[bn5]]), phase["".join([plane, bn6, bn6])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bn6]] / MADTwiss.BETY[MADTwiss.indx[bn6]]), phase["".join([plane, bn6, bn7])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bn6]] / MADTwiss.BETY[MADTwiss.indx[bn7]])])
    #     p1 = phase["".join([plane, bn1, bn6])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bn1]] / MADTwiss.BETY[MADTwiss.indx[bn6]])
    #     p2 = phase["".join([plane, bn2, bn6])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bn2]] / MADTwiss.BETY[MADTwiss.indx[bn6]])
    #     p3 = phase["".join([plane, bn3, bn6])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bn3]] / MADTwiss.BETY[MADTwiss.indx[bn6]])
    #     p5 = phase["".join([plane, bn6, bn5])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bn5]] / MADTwiss.BETY[MADTwiss.indx[bn6]])
    #     p6 = phase["".join([plane, bn6, bn6])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bn6]] / MADTwiss.BETY[MADTwiss.indx[bn6]])
    #     p7 = phase["".join([plane, bn6, bn7])][1] / np.sqrt(1 + MADTwiss.BETY[MADTwiss.indx[bn7]] / MADTwiss.BETY[MADTwiss.indx[bn6]])
    M = np.zeros([RANGE - 1, RANGE - 1])
    for k in range(RANGE - 1):
        for l in range(RANGE - 1):
            if k == l and k < probed_index:
                M[k][l] = phase["".join([plane, bpm_name[probed_index], bpm_name[probed_index + k + 1]])][1]**2
            elif k == l and k >= probed_index:
                M[k][l] = phase["".join([plane, bpm_name[RANGE - 2 - k], bpm_name[probed_index]])][1]**2
    #        elif (k < probed_index and l >= probed_index) or (k >= probed_index and l < probed_index):
     #           M[k][l] = - phase_err[probed_index]**2
            else:
                M[k][l] = phase_err[probed_index]**2

    # M = (2*np.pi)**2 * np.matrix([[phase["".join([plane, bn6, bn5])][1]**2, p4**2, p4**2, p4**2, p4**2, p4**2],
    #                               [p4**2, phase["".join([plane, bn4, bn6])][1]**2, p4**2, p4**2, p4**2, p4**2],
    #                               [p4**2, p4**2, phase["".join([plane, bn4, bn7])][1]**2, p4**2, p4**2, p4**2],
    #                               [p4**2, p4**2, p4**2, phase["".join([plane, bn3, bn4])][1]**2, p4**2, p4**2],
    #                               [p4**2, p4**2, p4**2, p4**2, phase["".join([plane, bn2, bn4])][1]**2, p4**2],
    #                               [p4**2, p4**2, p4**2, p4**2, p4**2, phase["".join([plane, bn1, bn4])][1]**2]])
    candidates = []
    left_bpm = range(probed_index)
    right_bpm = range(probed_index + 1, RANGE)
    left_combo = [[x, y] for x in left_bpm for y in left_bpm if x < y]
    right_combo = [[x, y] for x in right_bpm for y in right_bpm if x < y]
    mid_combo = [[x, y] for x in left_bpm for y in right_bpm]

    for n in left_combo:
        tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_right(bpm_name[n[0]], bpm_name[n[1]], bpm_name[probed_index], MADTwiss, phase, plane, phase_err[n[0]], phase_err[n[1]], phase_err[probed_index])
        t_matrix_row = [0] * (RANGE-1)
        t_matrix_row[RANGE-2 - n[0]] = t1
        t_matrix_row[RANGE-2 - n[1]] = t2
        candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[n[0]], bpm_name[n[1]], t_matrix_row])
 
    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_right(bpm_name[0], bpm_name[1], bpm_name[probed_index], MADTwiss, phase, plane, phase_err[0], phase_err[1], phase_err[probed_index])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[0], bpm_name[1], [0, 0, 0, 0, t2, t1]])
    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_right(bpm_name[0], bpm_name[2], bpm_name[probed_index], MADTwiss, phase, plane, phase_err[0], phase_err[2], phase_err[probed_index])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[0], bpm_name[2], [0, 0, 0, t2, 0, t1]])
    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_right(bpm_name[1], bpm_name[2], bpm_name[probed_index], MADTwiss, phase, plane, phase_err[1], phase_err[2], phase_err[probed_index])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[1], bpm_name[2], [0, 0, 0, t2, t1, 0]])

    for n in mid_combo:
        tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_mid(bpm_name[n[0]], bpm_name[probed_index], bpm_name[n[1]], MADTwiss, phase, plane, phase_err[n[0]], phase_err[probed_index], phase_err[n[1]])
        t_matrix_row = [0] * (RANGE-1)
        t_matrix_row[RANGE-2 - n[0]] = t1
        t_matrix_row[n[1] - 1 - probed_index] = t2
        candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[n[0]], bpm_name[n[1]], t_matrix_row])

    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_mid(bpm_name[0], bpm_name[probed_index], bpm_name[4], MADTwiss, phase, plane, phase_err[0], phase_err[probed_index], phase_err[4])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[0], bpm_name[4], [t2, 0, 0, 0, 0, t1]])
    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_mid(bpm_name[1], bpm_name[probed_index], bpm_name[4], MADTwiss, phase, plane, phase_err[1], phase_err[probed_index], phase_err[4])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[1], bpm_name[4], [t2, 0, 0, 0, t1, 0]])
    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_mid(bpm_name[2], bpm_name[probed_index], bpm_name[4], MADTwiss, phase, plane, phase_err[2], phase_err[probed_index], phase_err[4])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[2], bpm_name[4], [t2, 0, 0, t1, 0, 0]])
    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_mid(bpm_name[0], bpm_name[probed_index], bpm_name[5], MADTwiss, phase, plane, phase_err[0], phase_err[probed_index], phase_err[5])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[0], bpm_name[5], [0, t2, 0, 0, 0, t1]])
    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_mid(bpm_name[1], bpm_name[probed_index], bpm_name[5], MADTwiss, phase, plane, phase_err[1], phase_err[probed_index], phase_err[5])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[1], bpm_name[5], [0, t2, 0, 0, t1, 0]])
    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_mid(bpm_name[2], bpm_name[probed_index], bpm_name[5], MADTwiss, phase, plane, phase_err[2], phase_err[probed_index], phase_err[5])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[2], bpm_name[5], [0, t2, 0, t1, 0, 0]])
    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_mid(bpm_name[0], bpm_name[probed_index], bpm_name[6], MADTwiss, phase, plane, phase_err[0], phase_err[probed_index], phase_err[6])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[0], bpm_name[6], [0, 0, t2, 0, 0, t1]])
    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_mid(bpm_name[1], bpm_name[probed_index], bpm_name[6], MADTwiss, phase, plane, phase_err[1], phase_err[probed_index], phase_err[6])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[1], bpm_name[6], [0, 0, t2, 0, t1, 0]])
    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_mid(bpm_name[2], bpm_name[probed_index], bpm_name[6], MADTwiss, phase, plane, phase_err[2], phase_err[probed_index], phase_err[6])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[2], bpm_name[6], [0, 0, t2, t1, 0, 0]])

    for n in right_combo:
        tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_left(bpm_name[probed_index], bpm_name[n[0]], bpm_name[n[1]], MADTwiss, phase, plane, phase_err[probed_index], phase_err[n[0]], phase_err[n[1]])
        t_matrix_row = [0] * (RANGE-1)
        t_matrix_row[n[0] - 1 - probed_index] = t1
        t_matrix_row[n[1] - 1 - probed_index] = t2
        candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[n[0]], bpm_name[n[1]], t_matrix_row])

    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_left(bpm_name[probed_index], bpm_name[4], bpm_name[5], MADTwiss, phase, plane, phase_err[probed_index], phase_err[4], phase_err[5])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[4], bpm_name[5], [t1, t2, 0, 0, 0, 0]])
    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_left(bpm_name[probed_index], bpm_name[4], bpm_name[6], MADTwiss, phase, plane, phase_err[probed_index], phase_err[4], phase_err[6])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[4], bpm_name[6], [t1, 0, t2, 0, 0, 0]])
    # tbet, tbetstd, talf, talfstd, mdlerr, t1, t2 = BetaFromPhase_BPM_left(bpm_name[probed_index], bpm_name[5], bpm_name[6], MADTwiss, phase, plane, phase_err[probed_index], phase_err[5], phase_err[6])
    # candidates.append([tbetstd, tbet, talfstd, talf, mdlerr, bpm_name[5], bpm_name[6], [0, t1, t2, 0, 0, 0]])

    sort_cand = sorted(candidates, key=lambda x: x[4])
    if sort_cand[0][0] > 0 and  not use_only_three_bpms_for_beta_from_phase:  # TODO: Check if sort_cand condition can be removed
        return [sort_cand[i] for i in range(NUM_BPM_COMBOS)], bpm_name[probed_index], M
    else:
        return candidates[2], candidates[5], candidates[12], bpm_name[probed_index], M


def beta_from_phase(MADTwiss, ListOfFiles, phase, plane, use_only_three_bpms_for_beta_from_phase):
    '''
    Uses 3 BPM left and right of a probed BPM and calculates the beta/alfa from the
    phase advances (15 combinations of 3 BPM stes -> 15 betas).
    The 3 betas with the lowest errors are chosen, and averaged for the final beta.
    :Parameters:
        'MADTwiss':twiss
            model twiss file
        'ListOfFiles':twiss
            measurement files
        'phase':dict
            measured phase advances
        'plane':string
            'H' or 'V'
    :Return:tupel (beta,rmsbb,alfa,commonbpms)
        'beta':dict
            calculated beta function for all BPMs
        'rmsbb':float
            rms beta-beating
        'alfa':dict
            calculated alfa function for all BPMs
        'commonbpms':list
            intersection of common BPMs in measurement files and model
    '''
    if phase == {}:
        return [{}, 0.0, {}, []]
    alfa = {}
    beta = {}

    commonbpms = Utilities.bpm.intersect(ListOfFiles)
    commonbpms = Utilities.bpm.model_intersect(commonbpms, MADTwiss)

    if 3 > len(commonbpms):
        print "beta_from_phase: Less than three BPMs for plane", plane + ". Returning empty values."
        return ({}, 0.0, {}, [])

    if 7 > len(commonbpms):
        print "beta_from_phase: Less than seven BPMs for plane", plane + ". Can not use optimised algorithm."

    systematic_errors_found = False
    systematics_error_path = os.path.join(os.path.dirname(os.path.abspath(MADTwiss.filename)), "bet_deviations.npy")
    systematic_errors = None
    if os.path.isfile(systematics_error_path):
        systematic_errors = np.load(systematics_error_path)
        systematic_errors_found = True
    elif not use_only_three_bpms_for_beta_from_phase:
        print >> sys.stderr, "WARNING: Cannot find bet_deviations.npy file!"

    delbeta = []
    for i in range(0, len(commonbpms)):

        alfa_beta, probed_bpm_name, M = get_best_three_bpms_with_beta_and_alfa(MADTwiss, phase, plane, commonbpms, i, use_only_three_bpms_for_beta_from_phase)

        beti = sum([alfa_beta[i][1] for i in range(len(alfa_beta))]) / len(alfa_beta)
        alfi = 0 #(alfa_beta_b1[3] + alfa_beta_b2[3] + alfa_beta_b3[3]) / 3.

        alfstd = 0 #math.sqrt(alfa_beta_b1[2]**2 + alfa_beta_b2[2]**2 + alfa_beta_b3[2]**2)/math.sqrt(3.)
        betstd = 0 #math.sqrt(sum([alfa_beta[i][0]**2 for i in range(len(alfa_beta))])) / math.sqrt(len(alfa_beta))

        # try:
        #     beterr = math.sqrt((alfa_beta_b1[1]**2 + alfa_beta_b2[1]**2 + alfa_beta_b3[1]**2)/len(alfa_beta) - beti**2.)
        # except ValueError:
        #     beterr = 0

        try:
            alferr = 0 #math.sqrt((alfa_beta_b1[3]**2 + alfa_beta_b2[3]**2 + alfa_beta_b3[3]**2)/3.-alfi**2.)
        except ValueError:
            alferr = 0

        if not use_only_three_bpms_for_beta_from_phase:
        # Use the systematic error file to get the beta errors

            T = np.transpose(np.matrix([alfa_beta[i][7] for i in range(len(alfa_beta))]))
            V1 = M * T
            V2 = np.transpose(T) * V1

            try:
                V = np.linalg.pinv(V2)
            except:
                V = np.zeros([len(alfa_beta), len(alfa_beta)])

            w = np.zeros(len(alfa_beta))
            V_row_sum = V.sum(axis=1, dtype='float')
            V_sum = V.sum(dtype='float')
            betstd = 0
            if V_sum != 0:
                for i in range(len(w)):
                    w[i] = V_row_sum[i] / V_sum
                beti = float(sum([w[i] * alfa_beta[i][1] for i in range(len(alfa_beta))]))

                for i in range(len(alfa_beta)):
                    for j in range(len(alfa_beta)):
                        betstd = betstd + w[i] * w[j] * V2.item(i, j)
                        if probed_bpm_name == 'BPM.20L1.B1':
                            print betstd 
                betstd = np.sqrt(float(betstd))
            else:
                betstd = DEFAULT_WRONG_BETA

            if systematic_errors_found:
                syserr = np.zeros(len(alfa_beta))
                for i in range(len(alfa_beta)):
                # e1 = 0
                # e2 = 0
                # e3 = 0
                    if plane == 'H':
                        if probed_bpm_name + alfa_beta[i][5] + alfa_beta[i][6] in systematic_errors[0]:
                            syserr[i] = systematic_errors[0][probed_bpm_name + alfa_beta[i][5] + alfa_beta[i][6]]
                        elif probed_bpm_name + alfa_beta[i][6] + alfa_beta[i][5] in systematic_errors[0]:
                            syserr[i] = systematic_errors[0][probed_bpm_name + alfa_beta[i][6] + alfa_beta[i][5]]
                        else:
                            print 'Error, bpms for systematic error not found ->', probed_bpm_name, alfa_beta[i][5], alfa_beta[i][6]
                        # if probed_bpm_name + alfa_beta_b2[5] + alfa_beta_b2[6] in systematic_errors[0]:
                        #     e2 = systematic_errors[0][probed_bpm_name + alfa_beta_b2[5] + alfa_beta_b2[6]]
                        # elif probed_bpm_name + alfa_beta_b2[6] + alfa_beta_b2[5] in systematic_errors[0]:
                        #     e2 = systematic_errors[0][probed_bpm_name + alfa_beta_b2[6] + alfa_beta_b2[5]]
                        # else:
                        #     print 'Error, bpms for systematic error not found ->', probed_bpm_name, alfa_beta_b2[5], alfa_beta_b2[6]
                        # if probed_bpm_name + alfa_beta_b3[5] + alfa_beta_b3[6] in systematic_errors[0]:
                        #     e3 = systematic_errors[0][probed_bpm_name + alfa_beta_b3[5] + alfa_beta_b3[6]]
                        # elif probed_bpm_name + alfa_beta_b3[6] + alfa_beta_b3[5] in systematic_errors[0]:
                        #     e3 = systematic_errors[0][probed_bpm_name + alfa_beta_b3[6] + alfa_beta_b3[5]]
                        # else:
                        #     print 'Error, bpms for systematic error not found ->', probed_bpm_name, alfa_beta_b3[5], alfa_beta_b3[6]
                    if plane == 'V':
                        if probed_bpm_name + alfa_beta[i][5] + alfa_beta[i][6] in systematic_errors[1]:
                            syserr[i] = systematic_errors[1][probed_bpm_name + alfa_beta[i][5] + alfa_beta[i][6]]
                        elif probed_bpm_name + alfa_beta[i][6] + alfa_beta[i][5] in systematic_errors[1]:
                            syserr[i] = systematic_errors[1][probed_bpm_name + alfa_beta[i][6] + alfa_beta[i][5]]
                        else:
                            print 'Error, bpms for systematic error not found ->', probed_bpm_name, alfa_beta[i][5], alfa_beta[i][6]
                        # if probed_bpm_name + alfa_beta_b2[5] + alfa_beta_b2[6] in systematic_errors[1]:
                        #     e2 = systematic_errors[1][probed_bpm_name + alfa_beta_b2[5] + alfa_beta_b2[6]]
                        # elif probed_bpm_name + alfa_beta_b2[6] + alfa_beta_b2[5] in systematic_errors[1]:
                        #     e2 = systematic_errors[1][probed_bpm_name + alfa_beta_b2[6] + alfa_beta_b2[5]]
                        # else:
                        #     print 'Error, bpms for systematic error not found ->', probed_bpm_name, alfa_beta_b2[5], alfa_beta_b2[6]
                        # if probed_bpm_name + alfa_beta_b3[5] + alfa_beta_b3[6] in systematic_errors[1]:
                        #     e3 = systematic_errors[1][probed_bpm_name + alfa_beta_b3[5] + alfa_beta_b3[6]]
                        # elif probed_bpm_name + alfa_beta_b3[6] + alfa_beta_b3[5] in systematic_errors[1]:
                        #     e3 = systematic_errors[1][probed_bpm_name + alfa_beta_b3[6] + alfa_beta_b3[5]]
                        # else:
                        #     print 'Error, bpms for systematic error not found ->', probed_bpm_name, alfa_beta_b3[5], alfa_beta_b3[6]
                # if e1 != 0 and e2 != 0 and e3 != 0:
                if not 0 in syserr:
                    # if w[0] != 0 and w[1] != 0 and w[2] != 0:
                    if not 0 in w:
                        beterr = float(np.sqrt(sum([(w[i]*syserr[i]*alfa_beta[i][1])**2 for i in range(len(alfa_beta))])))
                    else:
                        beterr = float((1/len(alfa_beta))*np.sqrt(sum([(syserr[i]*alfa_beta[i][1])**2 for i in range(len(alfa_beta))])))
                else:
                    beterr = DEFAULT_WRONG_BETA
            else:
                beterr = DEFAULT_WRONG_BETA

        beta[probed_bpm_name] = (beti, beterr, betstd)
        alfa[probed_bpm_name] = (alfi, alferr, alfstd)
        if plane == 'H':
            betmdl1 = MADTwiss.BETX[MADTwiss.indx[probed_bpm_name]]
        elif plane == 'V':
            betmdl1 = MADTwiss.BETY[MADTwiss.indx[probed_bpm_name]]
        delbeta.append((beti - betmdl1) / betmdl1)

    delbeta = np.array(delbeta)
    rmsbb = math.sqrt(np.average(delbeta * delbeta))

    return [beta, rmsbb, alfa, commonbpms]


def beta_from_amplitude(mad_twiss, list_of_files, plane):

    beta = {}
    root2j = []
    commonbpms = Utilities.bpm.intersect(list_of_files)
    commonbpms = Utilities.bpm.model_intersect(commonbpms, mad_twiss)
    sum_a = 0.0
    amp = []
    amp2 = []
    kick2 = []
    for i in range(0, len(commonbpms)):  # this loop have become complicated after modifications... anybody simplify?
        bn1 = str.upper(commonbpms[i][1])
        if plane == 'H':
            tembeta = mad_twiss.BETX[mad_twiss.indx[bn1]]
        elif plane == 'V':
            tembeta = mad_twiss.BETY[mad_twiss.indx[bn1]]
        amp_i = 0.0
        amp_j2 = []
        root2j_i = 0.0
        counter = 0
        for tw_file in list_of_files:
            if i == 0:
                kick2.append(0)
            if plane == 'H':
                amp_i += tw_file.AMPX[tw_file.indx[bn1]]
                amp_j2.append(tw_file.AMPX[tw_file.indx[bn1]]**2)
                root2j_i += tw_file.PK2PK[tw_file.indx[bn1]] / 2.
            elif plane == 'V':
                amp_i += tw_file.AMPY[tw_file.indx[bn1]]
                amp_j2.append(tw_file.AMPY[tw_file.indx[bn1]]**2)
                root2j_i += tw_file.PK2PK[tw_file.indx[bn1]] / 2.

            kick2[counter] += amp_j2[counter] / tembeta
            counter += 1

        amp_i = amp_i / len(list_of_files)
        root2j_i = root2j_i / len(list_of_files)
        amp.append(amp_i)
        amp2.append(amp_j2)

        sum_a += amp_i**2 / tembeta
        root2j.append(root2j_i / math.sqrt(tembeta))

    kick = sum_a / len(commonbpms)  # Assuming the average of beta is constant
    kick2 = np.array(kick2)
    kick2 = kick2 / len(commonbpms)
    amp2 = np.array(amp2)
    root2j = np.array(root2j)
    root2j_ave = np.average(root2j)
    root2j_rms = math.sqrt(np.average(root2j * root2j) - root2j_ave**2 + 2.2e-16)

    delbeta = []
    for i in range(0, len(commonbpms)):
        bn1 = str.upper(commonbpms[i][1])
        location = commonbpms[i][0]
        for j in range(0, len(list_of_files)):
            amp2[i][j] = amp2[i][j] / kick2[j]
        #print np.average(amp2[i]*amp2[i]),np.average(amp2[i])**2
        try:
            betstd = math.sqrt(np.average(amp2[i] * amp2[i]) - np.average(amp2[i])**2 + 2.2e-16)
        except:
            betstd = 0

        beta[bn1] = [amp[i]**2 / kick, betstd, location]
        if plane == 'H':
            betmdl = mad_twiss.BETX[mad_twiss.indx[bn1]]
        elif plane == 'V':
            betmdl = mad_twiss.BETY[mad_twiss.indx[bn1]]
        delbeta.append((beta[bn1][0] - betmdl) / betmdl)

    invariant_j = [root2j_ave, root2j_rms]

    delbeta = np.array(delbeta)
    rmsbb = math.sqrt(np.average(delbeta * delbeta))
    return [beta, rmsbb, commonbpms, invariant_j]


#===================================================================================================
# ac-dipole stuff
#===================================================================================================
def _get_free_beta(modelfree, modelac, betal, rmsbb, alfal, bpms, plane):  # to check "+"
    if DEBUG:
        print "Calculating free beta using model"
    bpms = Utilities.bpm.model_intersect(bpms, modelfree)
    bpms = Utilities.bpm.model_intersect(bpms, modelac)
    betan = {}
    alfan = {}
    for bpma in bpms:
        bpm = bpma[1].upper()
        beta, beterr, betstd = betal[bpm]
        alfa, alferr, alfstd = alfal[bpm]

        if plane == "H":
            betmf = modelfree.BETX[modelfree.indx[bpm]]
            betma = modelac.BETX[modelac.indx[bpm]]
            bb = (betma - betmf) / betmf
            alfmf = modelfree.ALFX[modelfree.indx[bpm]]
            alfma = modelac.ALFX[modelac.indx[bpm]]
            aa = (alfma - alfmf) / alfmf
        else:
            betmf = modelfree.BETY[modelfree.indx[bpm]]
            betma = modelac.BETY[modelac.indx[bpm]]
            alfmf = modelfree.ALFY[modelfree.indx[bpm]]
            alfma = modelac.ALFY[modelac.indx[bpm]]
            bb = (betma - betmf) / betmf
            aa = (alfma - alfmf) / alfmf

        betan[bpm] = beta * (1 + bb), beterr, betstd  # has to be plus!
        alfan[bpm] = alfa * (1 + aa), alferr, alfstd

    return betan, rmsbb, alfan, bpms


def BetaFromPhase_BPM_left(bn1, bn2, bn3, MADTwiss, phase, plane, p1, p2, p3):
    '''
    Calculates the beta/alfa function and their errors using the
    phase advance between three BPMs for the case that the probed BPM is left of the other two BPMs
    :Parameters:
        'bn1':string
            Name of probed BPM
        'bn2':string
            Name of first BPM right of the probed BPM
        'bn3':string
            Name of second BPM right of the probed BPM
        'MADTwiss':twiss
            model twiss file
        'phase':dict
            measured phase advances
        'plane':string
            'H' or 'V'
    :Return:tupel (bet,betstd,alf,alfstd)
        'bet':float
            calculated beta function at probed BPM
        'betstd':float
            calculated error on beta function at probed BPM
        'alf':float
            calculated alfa function at probed BPM
        'alfstd':float
            calculated error on alfa function at probed BPM
    '''
    ph2pi12=2.*np.pi*phase["".join([plane,bn1,bn2])][0]
    ph2pi13=2.*np.pi*phase["".join([plane,bn1,bn3])][0]

    # Find the model transfer matrices for beta1
    phmdl12 = 2.*np.pi*phase["".join([plane,bn1,bn2])][2]
    phmdl13=2.*np.pi*phase["".join([plane,bn1,bn3])][2]
    if plane=='H':
        betmdl1=MADTwiss.BETX[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETX[MADTwiss.indx[bn2]]
        betmdl3=MADTwiss.BETX[MADTwiss.indx[bn3]]
        alpmdl1=MADTwiss.ALFX[MADTwiss.indx[bn1]]
    elif plane=='V':
        betmdl1=MADTwiss.BETY[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETY[MADTwiss.indx[bn2]]
        betmdl3=MADTwiss.BETY[MADTwiss.indx[bn3]]
        alpmdl1=MADTwiss.ALFY[MADTwiss.indx[bn1]]
    if betmdl3 < 0 or betmdl2<0 or betmdl1<0:
        print >> sys.stderr, "Some of the off-momentum betas are negative, change the dpp unit"
        sys.exit(1)

    # Find beta1 and alpha1 from phases assuming model transfer matrix
    # Matrix M: BPM1-> BPM2
    # Matrix N: BPM1-> BPM3
    M11=math.sqrt(betmdl2/betmdl1)*(cos(phmdl12)+alpmdl1*sin(phmdl12))
    M12=math.sqrt(betmdl1*betmdl2)*sin(phmdl12)
    N11=math.sqrt(betmdl3/betmdl1)*(cos(phmdl13)+alpmdl1*sin(phmdl13))
    N12=math.sqrt(betmdl1*betmdl3)*sin(phmdl13)

    denom=M11/M12-N11/N12+1e-16
    numer=1/tan(ph2pi12)-1/tan(ph2pi13)
    bet=numer/denom

    betstd=        (2*np.pi*phase["".join([plane,bn1,bn2])][1]/sin(ph2pi12)**2)**2
    betstd=betstd+(2*np.pi*phase["".join([plane,bn1,bn3])][1]/sin(ph2pi13)**2)**2
    betstd=math.sqrt(betstd)/abs(denom)

    mdlerr=        (2*np.pi*0.001/sin(phmdl12)**2)**2
    mdlerr=mdlerr+(2*np.pi*0.001/sin(phmdl13)**2)**2
    mdlerr=math.sqrt(mdlerr)/abs(denom)    

    term1 = 1/sin(phmdl12)**2/denom
    term2 = -1/sin(phmdl13)**2/denom

    denom=M12/M11-N12/N11+1e-16
    numer=-M12/M11/tan(ph2pi12)+N12/N11/tan(ph2pi13)
    alf=numer/denom

    alfstd=        (M12/M11*2*np.pi*phase["".join([plane,bn1,bn2])][1]/sin(ph2pi12)**2)**2
    alfstd=alfstd+(N12/N11*2*np.pi*phase["".join([plane,bn1,bn3])][1]/sin(ph2pi13)**2)**2
    alfstd=math.sqrt(alfstd)/denom

    return bet, betstd, alf, alfstd, mdlerr, term1, term2

def BetaFromPhase_BPM_mid(bn1,bn2,bn3,MADTwiss,phase,plane,p1,p2,p3):
    '''
    Calculates the beta/alfa function and their errors using the
    phase advance between three BPMs for the case that the probed BPM is between the other two BPMs
    :Parameters:
        'bn1':string
            Name of BPM left of the probed BPM
        'bn2':string
            Name of probed BPM
        'bn3':string
            Name of BPM right of the probed BPM
        'MADTwiss':twiss
            model twiss file
        'phase':dict
            measured phase advances
        'plane':string
            'H' or 'V'
    :Return:tupel (bet,betstd,alf,alfstd)
        'bet':float
            calculated beta function at probed BPM
        'betstd':float
            calculated error on beta function at probed BPM
        'alf':float
            calculated alfa function at probed BPM
        'alfstd':float
            calculated error on alfa function at probed BPM
    '''
    ph2pi12=2.*np.pi*phase["".join([plane,bn1,bn2])][0]
    ph2pi23=2.*np.pi*phase["".join([plane,bn2,bn3])][0]

    # Find the model transfer matrices for beta1
    phmdl12=2.*np.pi*phase["".join([plane,bn1,bn2])][2]
    phmdl23=2.*np.pi*phase["".join([plane,bn2,bn3])][2]
    if plane=='H':
        betmdl1=MADTwiss.BETX[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETX[MADTwiss.indx[bn2]]
        betmdl3=MADTwiss.BETX[MADTwiss.indx[bn3]]
        alpmdl2=MADTwiss.ALFX[MADTwiss.indx[bn2]]
    elif plane=='V':
        betmdl1=MADTwiss.BETY[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETY[MADTwiss.indx[bn2]]
        betmdl3=MADTwiss.BETY[MADTwiss.indx[bn3]]
        alpmdl2=MADTwiss.ALFY[MADTwiss.indx[bn2]]
    if betmdl3 < 0 or betmdl2<0 or betmdl1<0:
        print >> sys.stderr, "Some of the off-momentum betas are negative, change the dpp unit"
        sys.exit(1)

    # Find beta2 and alpha2 from phases assuming model transfer matrix
    # Matrix M: BPM1-> BPM2
    # Matrix N: BPM2-> BPM3
    M22=math.sqrt(betmdl1/betmdl2)*(cos(phmdl12)-alpmdl2*sin(phmdl12))
    M12=math.sqrt(betmdl1*betmdl2)*sin(phmdl12)
    N11=math.sqrt(betmdl3/betmdl2)*(cos(phmdl23)+alpmdl2*sin(phmdl23))
    N12=math.sqrt(betmdl2*betmdl3)*sin(phmdl23)

    denom=M22/M12+N11/N12+1e-16
    numer=1/tan(ph2pi12)+1/tan(ph2pi23)
    bet=numer/denom

    betstd=        (2*np.pi*phase["".join([plane,bn1,bn2])][1]/sin(ph2pi12)**2)**2
    betstd=betstd+(2*np.pi*phase["".join([plane,bn2,bn3])][1]/sin(ph2pi23)**2)**2
    betstd=math.sqrt(betstd)/abs(denom)

    mdlerr=        (2*np.pi*0.001/sin(phmdl12)**2)**2
    mdlerr=mdlerr+(2*np.pi*0.001/sin(phmdl23)**2)**2
    mdlerr=math.sqrt(mdlerr)/abs(denom)

    term2 = 1/sin(phmdl23)**2/denom  #sign
    term1 = -1/sin(phmdl12)**2/denom  #sign

    denom=M12/M22+N12/N11+1e-16
    numer=M12/M22/tan(ph2pi12)-N12/N11/tan(ph2pi23)
    alf=numer/denom

    alfstd=        (M12/M22*2*np.pi*phase["".join([plane,bn1,bn2])][1]/sin(ph2pi12)**2)**2
    alfstd=alfstd+(N12/N11*2*np.pi*phase["".join([plane,bn2,bn3])][1]/sin(ph2pi23)**2)**2
    alfstd=math.sqrt(alfstd)/abs(denom)

    return bet, betstd, alf, alfstd, mdlerr, term1, term2

def BetaFromPhase_BPM_right(bn1,bn2,bn3,MADTwiss,phase,plane,p1,p2,p3):
    '''
    Calculates the beta/alfa function and their errors using the
    phase advance between three BPMs for the case that the probed BPM is right the other two BPMs
    :Parameters:
        'bn1':string
            Name of second BPM left of the probed BPM
        'bn2':string
            Name of first BPM left of the probed BPM
        'bn3':string
            Name of probed BPM
        'MADTwiss':twiss
            model twiss file
        'phase':dict
            measured phase advances
        'plane':string
            'H' or 'V'
    :Return:tupel (bet,betstd,alf,alfstd)
        'bet':float
            calculated beta function at probed BPM
        'betstd':float
            calculated error on beta function at probed BPM
        'alf':float
            calculated alfa function at probed BPM
        'alfstd':float
            calculated error on alfa function at probed BPM
    '''
    ph2pi23=2.*np.pi*phase["".join([plane,bn2,bn3])][0]
    ph2pi13=2.*np.pi*phase["".join([plane,bn1,bn3])][0]

    # Find the model transfer matrices for beta1
    phmdl13=2.*np.pi*phase["".join([plane,bn1,bn3])][2]
    phmdl23=2.*np.pi*phase["".join([plane,bn2,bn3])][2]
    if plane=='H':
        betmdl1=MADTwiss.BETX[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETX[MADTwiss.indx[bn2]]
        betmdl3=MADTwiss.BETX[MADTwiss.indx[bn3]]
        alpmdl3=MADTwiss.ALFX[MADTwiss.indx[bn3]]
    elif plane=='V':
        betmdl1=MADTwiss.BETY[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETY[MADTwiss.indx[bn2]]
        betmdl3=MADTwiss.BETY[MADTwiss.indx[bn3]]
        alpmdl3=MADTwiss.ALFY[MADTwiss.indx[bn3]]
    if betmdl3 < 0 or betmdl2<0 or betmdl1<0:
        print >> sys.stderr, "Some of the off-momentum betas are negative, change the dpp unit"
        sys.exit(1)

    # Find beta3 and alpha3 from phases assuming model transfer matrix
    # Matrix M: BPM2-> BPM3
    # Matrix N: BPM1-> BPM3
    M22=math.sqrt(betmdl2/betmdl3)*(cos(phmdl23)-alpmdl3*sin(phmdl23))
    M12=math.sqrt(betmdl2*betmdl3)*sin(phmdl23)
    N22=math.sqrt(betmdl1/betmdl3)*(cos(phmdl13)-alpmdl3*sin(phmdl13))
    N12=math.sqrt(betmdl1*betmdl3)*sin(phmdl13)

    denom=M22/M12-N22/N12+1e-16
    numer=1/tan(ph2pi23)-1/tan(ph2pi13)
    bet=numer/denom

    betstd=        (2*np.pi*phase["".join([plane,bn2,bn3])][1]/sin(ph2pi23)**2)**2
    betstd=betstd+(2*np.pi*phase["".join([plane,bn1,bn3])][1]/sin(ph2pi13)**2)**2
    betstd=math.sqrt(betstd)/abs(denom)

    mdlerr=        (2*np.pi*0.001/sin(phmdl23)**2)**2
    mdlerr=mdlerr+(2*np.pi*0.001/sin(phmdl13)**2)**2
    mdlerr=math.sqrt(mdlerr)/abs(denom)

    term2 = -1/sin(phmdl23)**2/denom  #sign
    term1 = 1/sin(phmdl13)**2/denom  #sign

    denom=M12/M22-N12/N22+1e-16
    numer=M12/M22/tan(ph2pi23)-N12/N22/tan(ph2pi13)
    alf=numer/denom

    alfstd=        (M12/M22*2*np.pi*phase["".join([plane,bn2,bn3])][1]/sin(ph2pi23)**2)**2
    alfstd=alfstd+(N12/N22*2*np.pi*phase["".join([plane,bn1,bn3])][1]/sin(ph2pi13)**2)**2
    alfstd=math.sqrt(alfstd)/abs(denom)


    return bet, betstd, alf, alfstd, mdlerr, term1, term2



def _get_free_amp_beta(betai, rmsbb, bpms, inv_j, mad_ac, mad_twiss, plane):
    #
    # Why difference in betabeta calculation ??
    #
    #
    betas = {}

    if DEBUG:
        print "Calculating free beta from amplitude using model"

    for bpm in bpms:
        bpmm = bpm[1].upper()
        beta = betai[bpmm][0]

        if plane == "H":
            betmf = mad_twiss.BETX[mad_twiss.indx[bpmm]]
            betma = mad_ac.BETX[mad_ac.indx[bpmm]]
            bb = (betmf-betma)/betma
        else:
            betmf = mad_twiss.BETY[mad_twiss.indx[bpmm]]
            betma = mad_ac.BETY[mad_ac.indx[bpmm]]
            bb = (betmf-betma)/betma

        betas[bpmm] = [beta*(1+bb), betai[bpmm][1], betai[bpmm][2]]

    return betas, rmsbb, bpms, inv_j
