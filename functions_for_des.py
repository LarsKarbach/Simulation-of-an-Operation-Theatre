import math
import numpy as np
from numpy.random import default_rng

class Globals(object):
    #Default generator for random numbers
    rng = default_rng()
    #Buffer time
    BUFFER_TIME = 0
    # Available time per room in operate
    ROOM_TIME = 450
    # Available time in planing
    ROOM_TIME_P = ROOM_TIME - BUFFER_TIME
    # Simulation horizon in weeks
    SIM_HOR = 31
    #Extended simulation horizon used for assigning dates to patients exceeding the simulation horizon
    #Choose sufficent high number; Should grow with SIM_HOR
    sim_hor_ex = 100

    grid = np.arange(-0.1, 0.2, 0.05)

    #Appointments per day
    appointments_per_day, appointments_standard_deviation = 25, 3

    #Reparametrize the mean and and standard deviation
    location_appo = np.log(appointments_per_day ** 2 / math.sqrt(10 ** 2 + appointments_per_day ** 2))
    shape_appo = math.sqrt(np.log(1 + (appointments_standard_deviation ** 2 / appointments_per_day ** 2)))

    #Emergencys per day
    emergencys_per_day, emergencys_standard_deviation = 5, 2

    #Reparametrize the mean and and standard deviation
    location_eme = np.log(emergencys_per_day ** 2 / math.sqrt(10 ** 2 + emergencys_per_day ** 2))
    shape_eme = math.sqrt(np.log(1 + (emergencys_standard_deviation ** 2 / emergencys_per_day ** 2)))

    #Interarrival Appointments
    inter_appo = 45
    #Interarrival Emergencys
    inter_eme = 175

    #Number of processor
    number_of_processor = 5

    #Inital number of patiens
    init_patients = 175


class HelperFunctions(object):
    """Functions used in Op_DES"""

    #Get Department Identifier from string
    @staticmethod
    def department_id(department):
        counter = 0
        identifier = None
        for i in ["FA_1", "FA_2", "FA_3", "FA_4", "FA_5", "FA_6"]:
            if department == i:
                identifier = counter

            counter += 1

        return identifier

    #Get provisionally date of operation
    @staticmethod
    def provisonally_date(duration, department, week_counter, Department_Rooms):
        """takes duration, department, the current week and then finds the next date for patient"""
        #Get department identifier
        Department_id = HelperFunctions.department_id(department)
        #Loop trough every still forthcoming week
        for week in range(week_counter + 1, Globals.SIM_HOR + Globals.sim_hor_ex):
            #Loop trough every day at that week
            for day in Department_Rooms[Department_id][week].keys():
                #For any room present at that day, check if the duration fits in the capacity
                for room in Department_Rooms[Department_id][week][day].items():
                    if duration < room[1][0].level:
                        pro_week = week
                        pro_day = day
                        room = room[0]

                        #If so, then return the week, day and room
                        return (pro_week, pro_day, room)

        return (None, None, None)\

    #Get the room for emergency cases
    @staticmethod
    def emergency_room(department, week_counter, day_counter, OP_Rooms):
        """takes department and current week and day from emergencys to find an emergency room"""

        # Get department identifier
        Department_id = HelperFunctions.department_id(department)

        #Check if the department is present at that day
        if day_counter in OP_Rooms[Department_id][week_counter].keys():
            room = list(OP_Rooms[Department_id][week_counter][day_counter].keys())[0]

            #If so, then return the corresponding room
            return room

        #If not, then check in which rooms the department otherwise operates
        else:
            #Available Rooms
            available_rooms_list = [list(i.keys()) for i in OP_Rooms[Department_id][0].values()]

            #Flatten the list
            available_rooms = [item for sublist in available_rooms_list for item in sublist]

            #Extract room data
            rooms_per_depart = [list(OP_Rooms[depart][0][day_counter].items()) for depart in range(len(OP_Rooms))
                                if day_counter
                                in OP_Rooms[depart][0].keys()]

            #Search in room data for a possible room
            rooms_data = list()
            for room in rooms_per_depart:

                for i in range(len(room)):
                    if room[i][0] in available_rooms:
                        rooms_data.append(room[i])

            #If there are two rooms available, choose the room with the highest available capacity
            if len(rooms_data) > 1:
                if rooms_data[0][1][0].level > rooms_data[1][1][0].level:
                    room = rooms_data[0][0]

                else:
                    room = rooms_data[1][0]

            else:
                room = rooms_data[0][0]

            return room

    #Used in beginning of a week, to fill and sort the days patient list
    @staticmethod
    def fill_and_sort_patient_list(appo_list, day):
        """fill the patient list with patients from appo_list (waiting list) and sort them (postponed; duration)"""

        #Loop trough the waiting list (appo_list) and add every patient with the corresponding provisionally date
        patient_list_day = [appo_list[appo_list.index(t)] for t in appo_list if t.pro_day == day]

        #Sort patient list with priority when patient got postponed and then duration
        patient_list_day.sort(key=lambda x: (x.post, x.duration), reverse=True)

        return patient_list_day

    @staticmethod
    def sample_duration(dur):
        """takes planed duration from patient to, sample actual duration from lognormal"""

        # Reparametrize
        location = np.log(dur ** 2 / math.sqrt(10 ** 2 + dur ** 2))
        shape = math.sqrt(np.log(1 + ((dur * 0.15) ** 2 / dur ** 2)))

        # Draw samples from lognormal with location and shape
        dur = int(Globals.rng.lognormal(mean=location, sigma=shape))

        return dur