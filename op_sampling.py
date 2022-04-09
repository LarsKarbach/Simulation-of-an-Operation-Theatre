from numpy.random import default_rng
import pandas as pd
from repo.functions_for_des import HelperFunctions

#Relative frequencies
relative_freq_department = [0.3, 0.2, 0.17, 0.12, 0.10, 0.08]
relative_freq_department_em = [0.3, 0.2, 0.17, 0.12, 0.10, 0.08]

relative_freq_department = pd.DataFrame(relative_freq_department,
                                        columns=["FA_1", "FA_2", "FA_3", "FA_4", "FA_5", "FA_6"])

relative_freq_department_em = pd.DataFrame(relative_freq_department_em,
                                           columns=["FA_1", "FA_2", "FA_3", "FA_4", "FA_5", "FA_6"])

#OP duration categories
op_durations = [30, 45, 90, 120, 180, 300]

#Relative frequencies of op duration categories
FA_1 = [0.36, 0.19, 0.22, 0.10, 0.08, 0.05]
FA_2 = [0.21, 0.12, 0.36, 0.10, 0.14, 0.07]
FA_3 = [0.08, 0.12, 0.23, 0.10, 0.36, 0.11]
FA_4 = [0.11, 0.17, 0.47, 0.12, 0.10, 0.03]
FA_5 = [0.04, 0.07, 0.25, 0.04, 0.11, 0.49]
FA_6 = [0.11, 0.15, 0.37, 0.16, 0.16, 0.05]

relative_freq_dur_typ = [FA_1, FA_6, FA_5, FA_2, FA_3, FA_4]


def generate_samples(random_seed, prio):
    """Takes number random Seed and prio and generates patient"""
    rng = default_rng(seed=random_seed)

    #If prio == 1 an elective patient is generated
    if prio == 1:

        #Sample department from multionomial distribution
        department_tally = rng.multinomial(1, relative_freq_department)

        department_samples = []

        #Loop trough every department and append the department to department_samples
        # as often as the equivalent occurence in the tally
        for i in range(len(relative_freq_department.axes[0])):
            for j in range(department_tally[i]):
                department_samples.append(relative_freq_department.axes[0][i])

        #Get department identifier
        Department_id = HelperFunctions.department_id(department_samples[0])

        #Sample duration category from multinomial
        dur_typ_tally = rng.multinomial(1, relative_freq_dur_typ[Department_id])

        dur_typ_samples = []

        # go trough every op duration and append the duration to op_typ_samples as often as the equivalent occurence in the tally
        for t in range(len(op_durations)):
            for u in range(dur_typ_tally[t]):
                dur_typ_samples.append(int(op_durations[t]))

        # merge the lists to data frame
        op_samples = pd.DataFrame(list(zip(department_samples, dur_typ_samples)),
                                  columns=['department', 'dur_typ'])

        # return the samples
        return (op_samples)

    else:

        # Sample department from multionomial distribution
        department_tally = rng.multinomial(1, relative_freq_department_em)

        department_samples = []

        # Loop trough every department and append the department to department_samples
        # as often as the equivalent occurence in the tally
        for i in range(len(relative_freq_department_em.axes[0])):
            for j in range(department_tally[i]):
                department_samples.append(relative_freq_department_em.axes[0][i])

        # Get department identifier
        Department_id = HelperFunctions.department_id(department_samples[0])

        # Sample duration category from multinomial
        dur_typ_tally = rng.multinomial(1, relative_freq_dur_typ[Department_id])

        dur_typ_samples = []

        # go trough every op duration and append the duration to op_typ_samples
        # as often as the equivalent occurence in the tally
        for t in range(len(op_durations)):
            for u in range(dur_typ_tally[t]):
                dur_typ_samples.append(int(op_durations[t]))

        # merge the lists to data frame
        op_samples = pd.DataFrame(list(zip(department_samples, dur_typ_samples)),
                                  columns=['department', 'dur_typ'])

        # return the samples
        return (op_samples)