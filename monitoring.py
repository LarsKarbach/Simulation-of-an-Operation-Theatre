import os
import pickle
from repo.functions_for_des import Globals

class Monitoring(object):

    #Number of runs
    runs = 30

    #Mother seed
    mon_seed = 3141

    data_folder = "data_local/buffer"+str(Globals.BUFFER_TIME)+"_"+str(mon_seed)

    postponed_list = [[] for _ in range(runs)]
    overtime_list = [[] for _ in range(runs)]
    full_patient_list = [[] for _ in range(runs)]
    room_patients_list = [[] for _ in range(runs)]
    rest_list = [[] for _ in range(runs)]
    util_list_appo = [[] for _ in range(runs)]
    util_list_op = [[] for _ in range(runs)]

    #Cannot pickle generator objects, so this function will just copy the list
    @staticmethod
    def monitor(list):
        monitor_list = [t for t in list]

        return monitor_list

    #Save the list objects to pickle files
    @staticmethod
    def save_objects(run):
        if not os.path.exists(Monitoring.data_folder):
            os.makedirs(Monitoring.data_folder)

        with open(Monitoring.data_folder+"/postponed"+str(run)+".pkl", "wb") as f:
            pickle.dump(list(Monitoring.postponed_list[run]), f)

        with open(Monitoring.data_folder+"/util_appo"+str(run)+".pkl", "wb") as f:
            pickle.dump(list(Monitoring.util_list_appo[run]), f)

        with open(Monitoring.data_folder+"/util_op"+str(run)+".pkl", "wb") as f:
            pickle.dump(list(Monitoring.util_list_op[run]), f)

        with open(Monitoring.data_folder+"/full_patient_list"+str(run)+".pkl", "wb") as f:
            pickle.dump(list(Monitoring.full_patient_list[run]), f)

        with open(Monitoring.data_folder+"/rest_list"+str(run)+".pkl", "wb") as f:
            pickle.dump(list(Monitoring.rest_list[run]), f)

    #Loop trough the Rooms used in the appointment process recursively to collect their data
    @staticmethod
    def utilisation_appo(Department_Rooms, run):
        depart = ["FA_1", "FA_2", "FA_3", "FA_4", "FA_5", "FA_6"]
        for Department in range(len(Department_Rooms)):
            for week in range(Globals.SIM_HOR):
                for i in Department_Rooms[Department][week].items():
                    for t in i[1].items():
                        Monitoring.util_list_appo[run].append([t[1][0].level, #ROOM_LEVEL
                                                               t[1][1], #Sum dur
                                                               t[0], #ROOM
                                                               depart[Department], #Department
                                                               week, #Week
                                                               i[0]]) #Day

        return (Monitoring.util_list_appo[run])

    #Loop trough the Rooms used in the operate process recursively to collect their data
    @staticmethod
    def utilisation_op(OP_Rooms, run):
        depart = ["FA_1", "FA_2", "FA_3", "FA_4", "FA_5", "FA_6"]
        for Department in range(len(OP_Rooms)):
            for week in range(Globals.SIM_HOR):
                for i in OP_Rooms[Department][week].items():
                    for t in i[1].items():
                        Monitoring.util_list_op[run].append([t[1][0].level, #ROOM_LEVEL
                                                               t[0],  #ROOM
                                                               depart[Department], #Department
                                                               week, #Week
                                                               i[0], #Day
                                                               t[1][1], #Overtime
                                                               t[1][2], #sum dur
                                                               t[1][3]]) #sum patients

        return (Monitoring.util_list_op[run])