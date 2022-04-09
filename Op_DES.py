from multiprocessing import Pool
from numpy.random import default_rng
import repo.op_sampling as op_sampling
from repo.functions_for_des import Globals, HelperFunctions
from repo.monitoring import Monitoring
import simpy

class Var(object):
    """Contains several class variables used in the simpy processes. The first chunck creates lists and counters
    such as the waiting list = appo_list or the week counter. The second chunck creates list used to monitor the
    simulation. The lists are filled in the process."""

    # create class variables
    #The waiting list; generates one sublist per week
    appo_list = [[] for _ in range(Globals.SIM_HOR + Globals.sim_hor_ex)]
    #Patient list used within a week
    patient_list = [[] for _ in range(5)] #5 Tage in der Woche
    #Week Counter will be raised while the simulation is running
    week_counter = -1
    #Day Counter will be raised while a week is in progress
    day_counter = 0
    #Identifier for elective patients
    name = 1
    #Identifier for emergency patients
    em_name = 90000

    #List used for Monitoring
    #For postponed patients
    postponed_list = list()
    #For operated patients
    full_patient_list = list()
    #For patients which gets a provisonally date but no operation
    rest_list = list()

class Patient(object):
    """The Patient Class. Every Patient generated in the Simulation gets an instance. Helps trough nice properties of
    access on class variables"""

    def __init__(self, env, name, department, duration, pro_week, pro_day, room, post):

        # create instance variables
        self.env = env
        self.name = name
        self.department = department
        self.duration = duration
        self.pro_week = pro_week
        self.pro_day = pro_day
        self.room = room
        self.post = post


def waiter(env, Department_Rooms, OP_Rooms, rooms, sim_finished):
    """Starts with the initial amount of patients and then restarts a week once is has finished"""""

    #Create intial amount of patients
    for _ in range(Globals.init_patients):

        # generate elective Patient
        patient_generated = op_sampling.generate_samples(Globals.rng.integers(1, 100000, size=1), 1)

        # apply provisionally date function
        pro_date = HelperFunctions.provisonally_date(patient_generated["dur_typ"][0],
                                                     patient_generated["department"][0],
                                                     Var.week_counter,
                                                     Department_Rooms)

        # create instance of Patient class with attributes from generated patient and provisionally_date
        patient = Patient(env,
                          Var.name,
                          patient_generated["department"][0],
                          patient_generated["dur_typ"][0],
                          pro_date[0],  # First result is the week
                          pro_date[1],  # Second result is the day
                          pro_date[2],  # Third result is the room
                          0 #Marker which gets raised if patient got postponed
        )

        # get Department identifier
        Department_id = HelperFunctions.department_id(patient.department)

        #take time capacity from the room generated in provisionally_date
        Department_Rooms[Department_id][patient.pro_week][patient.pro_day][patient.room][0].get(patient.duration)

        #Add the planed duration to the room attribute which sums up the planed durations
        Department_Rooms[Department_id][patient.pro_week][patient.pro_day][patient.room][1] += patient.duration

        #Add patient to waiting list
        Var.appo_list[patient.pro_week].append(patient)

        #Add patient to full_patient_list; gets kicked out if he will not be operated
        Var.full_patient_list.append(
            [patient.name, patient.department, patient.duration, patient.pro_week, patient.pro_day, patient.room, 1,
             Var.week_counter, Var.day_counter, patient.post])  # 1 for elective

        # Raise the identifier for following patients
        Var.name += 1

    while True:

        # check if every patient got operated. If so then week is finished and next week is ready to start
        if not any(Var.patient_list) == True:

            # Raise week counter
            Var.week_counter += 1

            #If the week correspond to the simulation horizon then mark the sim_finished event as succeed; will lead to
            #the end of the simulation
            if Var.week_counter == Globals.SIM_HOR:
                sim_finished.succeed()

            # Fill patient lists for the upcoming week
            for day in range(5):
                Var.patient_list[day] = HelperFunctions.fill_and_sort_patient_list(Var.appo_list[Var.week_counter],
                                                                                   day=day)

            #start operation arrivals process with the patient list containing the patients for the 5 days
            arr = env.process(operation_arrivals(env, Department_Rooms, OP_Rooms, Var.patient_list, 1, rooms))

            #Wait for the process to finish
            yield arr


def appointment(env, Department_Rooms):
    """Generate appointments"""

    #Loop trough the amount of appointments per day
    for _ in range(int(Globals.rng.lognormal(Globals.location_appo, Globals.shape_appo))):

        #timeout simulation; see simpy docs
        inter = int(Globals.rng.exponential(Globals.inter_appo, 1))
        yield env.timeout(inter)

        # generate elective Patient
        patient_generated = op_sampling.generate_samples(Globals.rng.integers(1, 100000, size=1), 1)

        # apply provisionally date function
        pro_date = HelperFunctions.provisonally_date(patient_generated["dur_typ"][0],
                                                     patient_generated["department"][0],
                                                     Var.week_counter,
                                                     Department_Rooms)

        # create instance of Patient class with attributes from generated patient and provisionally_date
        patient = Patient(
            env,
            Var.name,
            patient_generated["department"][0],
            patient_generated["dur_typ"][0],
            pro_date[0],  # First result is the week
            pro_date[1],  # Second result is the day
            pro_date[2],  # Third result is the room
            0 #Marker which gets raised if patient got postponed
        )

        # get Department identifier
        Department_id = HelperFunctions.department_id(patient.department)

        #If the result of provisionally_date is unqueal None then add patient to waiting list
        if patient.pro_day != None:

            # take time capacity from the room generated in provisionally_date
            Department_Rooms[Department_id][patient.pro_week][patient.pro_day][patient.room][0].get(patient.duration)

            # Add the planed duration to the room attribute which sums up the planed durations
            Department_Rooms[Department_id][patient.pro_week][patient.pro_day][patient.room][1] += patient.duration

            # Add patient to waiting list
            Var.appo_list[patient.pro_week].append(patient)

            # Add patient to full_patient_list; gets kicked out if he will not be operated
            Var.full_patient_list.append(
                [patient.name, patient.department, patient.duration,
                 patient.pro_week, patient.pro_day, patient.room, 1,
                 Var.week_counter, Var.day_counter, patient.post])  # 1 for elective

        #If not then add patient to rest list
        else:
            Var.rest_list.append([patient.name, patient.department, patient.duration,
                                  patient.pro_week, patient.pro_day, patient.room, 1,
                                  Var.week_counter, Var.day_counter, 0])

        # Raise the identifier for following patients
        Var.name += 1


def emergency(env, OP_Rooms, rooms):
    """Generate emergency arrivals while the operations are in progress"""

    # Loop trough the amount of appointments per day
    for _ in range(int(Globals.rng.lognormal(Globals.location_eme, Globals.shape_eme))):

        #timeout simulation
        yield env.timeout(int(Globals.rng.exponential(Globals.inter_eme, 1)))

        # generate emergency patient
        em_patient_generated = op_sampling.generate_samples(Globals.rng.integers(1, 100000, size=1), 0)

        # create instance of Patient class with attributes from generated patient and apply emergency_room
        em_patient = Patient(
            env,
            Var.em_name,
            em_patient_generated["department"][0],
            em_patient_generated["dur_typ"][0],
            Var.week_counter,
            Var.day_counter,
            HelperFunctions.emergency_room(em_patient_generated["department"][0],
                                           Var.week_counter,
                                           Var.day_counter,
                                           OP_Rooms),
            0
        )

        # get Department identifier
        Department_id = HelperFunctions.department_id(em_patient.department)

        # Add patient to full_patient_list
        Var.full_patient_list.append([em_patient.name, em_patient.department,
                                      em_patient.duration, em_patient.pro_week,
                                      em_patient.pro_day, em_patient.room, 0, Var.week_counter,
                                      Var.day_counter, em_patient.post])  # 0 for emergency

        #start operate process
        env.process(operate(env, OP_Rooms, Var.em_name, 0, em_patient.duration, Department_id,
                    em_patient.pro_week, em_patient.pro_day, em_patient.room, rooms)
        )

        # Raise the identifier for following patients
        Var.em_name += 1


def operation_arrivals(env, Department_Rooms, OP_Rooms, patient_list, prio, rooms):
    """Loop trough every day of week and every patient of a day and postpone him or start the operate process"""

    #Copy the patient list as ongoing changes, would result in false access
    patient_list = patient_list.copy()

    #Day Counter
    Var.day_counter = -1

    #Loop trough every day
    for i in patient_list:

        #Raise day counter
        Var.day_counter += 1

        #Start appointment and emergency process; Emergencys and appointments dont run in the initial week = -1
        if Var.week_counter >= 0:
            env.process(emergency(env, OP_Rooms, rooms))
            ap = env.process(appointment(env, Department_Rooms))
            yield ap

        #Loop trough every patient at that day
        for t in i.copy():

            #Get department identifier
            Department_id = HelperFunctions.department_id(t.department)

            #Check Postponement rule
            if OP_Rooms[Department_id][t.pro_week][t.pro_day][t.room][0].level < t.duration * 0.25 and t.post < 1:

                #Check if the department operates at a day in the rest of the week
                if any(i >= Var.day_counter + 1 for i in Department_Rooms[Department_id][t.pro_week].keys()) == True:

                    #If so, then assign that day
                    next_day = [i for i in Department_Rooms[Department_id][t.pro_week].keys()
                                if i >= Var.day_counter + 1][0]

                    #if more than one room is available, choose with the biggest capacity
                    if len(Department_Rooms[Department_id][t.pro_week][next_day].keys()) > 1:

                        # Compare capacities of available rooms
                        cap = [i[0].level for i in Department_Rooms[Department_id][t.pro_week][next_day].values()]

                        #choose with biggest capacity
                        if cap[0] > cap[1]:
                            new_room = list(Department_Rooms[Department_id][t.pro_week][next_day].keys())[0]

                        else:
                            new_room = list(Department_Rooms[Department_id][t.pro_week][next_day].keys())[1]

                    else:
                        new_room = list(Department_Rooms[Department_id][t.pro_week][next_day].keys())[0]

                    #Move patient in patient list
                    patient_list[next_day].insert(0, t)

                    #Remove from Var.patient_list
                    Var.patient_list[t.pro_day].pop(Var.patient_list[t.pro_day].index(t))

                    #Add to postponed list
                    Var.postponed_list.append(
                        [t.name, t.department, t.duration, t.pro_week, t.pro_day, t.room, t.pro_week, next_day,
                         new_room, Var.week_counter])

                    #Change his pro_day to next_day, his room to new_room and raise postponement marker
                    t.pro_day = next_day
                    t.room = new_room
                    t.post += 1

                    #Alternate values in full patient list
                    for patient in Var.full_patient_list:
                        if patient[0] == t.name:
                            patient[3] = t.pro_week
                            patient[4] = t.pro_day
                            patient[5] = t.room
                            patient[9] = t.post

                #If the department doesnt operate in the rest of the week
                else:

                    #Then, first check if the new week exceeds the simulation horizon
                    if t.pro_week + 1 >= Globals.SIM_HOR:

                        #If so, then add to rest list
                        Var.rest_list.append(
                            [t.name, t.department, t.duration, t.pro_week, t.pro_day, t.room, 1, Var.week_counter,
                             Var.day_counter, 1])

                        #And remove from patient list
                        Var.patient_list[t.pro_day].pop(Var.patient_list[t.pro_day].index(t))

                        #And remove from full_patient_list
                        for i in Var.full_patient_list.copy():
                            if i[0] == t.name:
                                Var.full_patient_list.pop(Var.full_patient_list.index(i))

                    #If not
                    else:

                        #Move patient in the waiting list
                        Var.appo_list[t.pro_week + 1].insert(0, Var.appo_list[t.pro_week].pop(
                            Var.appo_list[t.pro_week].index(t)))

                        #Remove from Var.patient_list
                        Var.patient_list[t.pro_day].pop(Var.patient_list[t.pro_day].index(t))

                        #Assign his new_week as the current week + 1
                        new_week = t.pro_week + 1

                        #Search for next day in next week
                        next_day = list(Department_Rooms[Department_id][t.pro_week].keys())[0]

                        # if more than one room is available, choose the biggest capacity
                        if len(Department_Rooms[Department_id][new_week][next_day].keys()) > 1:

                            # Compare capacities of available rooms
                            cap = [i[0].level for i in Department_Rooms[Department_id][new_week][next_day].values()]

                            # choose biggest capacity
                            if cap[0] > cap[1]:
                                new_room = list(Department_Rooms[Department_id][new_week][next_day].keys())[0]

                            else:
                                new_room = list(Department_Rooms[Department_id][new_week][next_day].keys())[1]

                        else:
                            new_room = list(Department_Rooms[Department_id][new_week][next_day].keys())[0]


                        #Change his pro_week to new_week, pro_day to next_day,
                        # his room to new_room and raise postponement marker
                        t.pro_week = new_week
                        t.pro_day = next_day
                        t.room = new_room
                        t.post += 1

                        #alternate values in full patient list
                        for patient in Var.full_patient_list:
                            if patient[0] == t.name:
                                patient[3] = t.pro_week
                                patient[4] = t.pro_day
                                patient[5] = t.room
                                patient[9] = t.post


            # If patient will not be postponed
            else:

                #Then start operate process
                op = env.process(operate(env, OP_Rooms, t.name, prio, t.duration, Department_id,
                                         t.pro_week, t.pro_day, t.room, rooms)
                                 )

                #yield the operate process
                yield op

                #Remove operated patient from Var.patient_list
                Var.patient_list[t.pro_day].pop(Var.patient_list[t.pro_day].index(t))


def operate(env, OP_Rooms, name, prio, dur, Department_id, week, day, room, rooms):
    """Takes the patient and yield an op room"""


    with rooms.request(priority=prio) as request:

        #Sample duration
        dur = HelperFunctions.sample_duration(dur)

        # check if the patient is an emergency
        if prio == 0:

            #If so, then search for room which matches the emergency room,
            # in every Department which operates at that time
            for i in [depart for depart in range(len(OP_Rooms)) if day in OP_Rooms[depart][0].keys()]:

                #If the room matches the emergency room
                if room in OP_Rooms[i][week][day].keys():

                    #Then yield request
                    yield request

                    # Append measures to patients entry full patient list
                    for t in Var.full_patient_list:
                        if t[0] == name:
                            Var.full_patient_list[Var.full_patient_list.index(t)].append(Var.week_counter)
                            Var.full_patient_list[Var.full_patient_list.index(t)].append(Var.day_counter)
                            Var.full_patient_list[Var.full_patient_list.index(t)].append(room)
                            Var.full_patient_list[Var.full_patient_list.index(t)].append(dur)

                    #Update attributes of OP Room; Useful for monitoring
                    OP_Rooms[i][week][day][room][2] += dur
                    OP_Rooms[i][week][day][room][3] += 1

                    #If the duration does not exceed the room capacity
                    if dur < OP_Rooms[i][week][day][room][0].level:

                        #Then just reduce the capacity
                        yield OP_Rooms[i][week][day][room][0].get(dur)

                        # leave for loop
                        break

                    #If not,
                    else:

                        #then calculate the overtime
                        overtime = dur - OP_Rooms[i][week][day][room][0].level

                        #Add overtime value to room attribute
                        OP_Rooms[i][week][day][room][1] += overtime

                        # If room already has zero capactiy skip
                        if OP_Rooms[i][week][day][room][0].level == 0:
                            pass

                        # If not then reduce the room capacity in the amount of the remaining capacity
                        # Simpy does not allow negative capacities
                        else:
                            yield OP_Rooms[i][week][day][room][0].get(OP_Rooms[i][week][day][room][0].level)
                        
                        #leave for loop
                        break
                        
        #If patient is elective
        else:

            yield request

            # Append measures to patients entry full patient list
            for t in Var.full_patient_list:
                if t[0] == name:
                    Var.full_patient_list[Var.full_patient_list.index(t)].append(Var.week_counter)
                    Var.full_patient_list[Var.full_patient_list.index(t)].append(Var.day_counter)
                    Var.full_patient_list[Var.full_patient_list.index(t)].append(room)
                    Var.full_patient_list[Var.full_patient_list.index(t)].append(dur)

            #Update attributes of OP Room; Useful for monitoring
            OP_Rooms[Department_id][week][day][room][2] += dur
            OP_Rooms[Department_id][week][day][room][3] += 1

            # If the duration does not exceed the room capacity
            if dur < OP_Rooms[Department_id][week][day][room][0].level:
                
                # Then just reduce the capacity
                yield OP_Rooms[Department_id][week][day][room][0].get(dur)
                
            # If not,
            else:

                # then calculate the overtime
                overtime = dur - OP_Rooms[Department_id][week][day][room][0].level

                # Raise overtime attribute of Room
                OP_Rooms[Department_id][week][day][room][1] += overtime

                #If room already has zero capactiy skip
                if OP_Rooms[Department_id][week][day][room][0].level == 0:
                    pass

                #If not then reduce the room capacity in the amount of the remaining capacity
                # Simpy does not allow negative capacities
                else:
                    yield OP_Rooms[Department_id][week][day][room][0].get(OP_Rooms[Department_id][week]
                                                                          [day][room][0].level)
                
        #timeout simulation
        yield env.timeout(dur)


def run(r, seed, buffer):
    """Resets class variables, create new simpy objects and then execute the simulation for every run"""
    
    #Seeding Random Generator
    Globals.rng = default_rng(seed)

    #Room capacity in Appointment
    Globals.ROOM_TIME_P = int(Globals.ROOM_TIME - Globals.ROOM_TIME * buffer)

    #Calculate Buffer time
    Globals.BUFFER_TIME = int(Globals.ROOM_TIME * buffer)
    
    #Define simpy enviroment
    env = simpy.Environment()
    
    #Create room ressource
    rooms = simpy.PriorityResource(env, 6)

    #Reset class variables
    Var.appo_list = [[] for _ in range(Globals.SIM_HOR + Globals.sim_hor_ex)]  
    Var.patient_list = [[] for _ in range(5)] 
    Var.week_counter = -1
    Var.day_counter = 0
    Var.name = 1
    Var.em_name = 90000

    Var.postponed_list = list()
    Var.overtime_list = list()
    Var.full_patient_list = list()
    Var.room_patients = list()
    Var.rest_list = list()

    #Create Room Ressources used in appointment; First Key is the day; Second Key is the room number
    FA_1 = [{0: {2: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0],
                 4: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             1: {4: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             2: {4: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             3: {4: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             4: {4: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]}
             }
            for _ in range(Globals.SIM_HOR + Globals.sim_hor_ex)]

    FA_2 = [{1: {2: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             2: {2: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             3: {2: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             4: {2: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]}
             }
            for _ in range(Globals.SIM_HOR + Globals.sim_hor_ex)]

    FA_3 = [{0: {1: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             1: {1: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0],
                5: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             2: {1: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             3: {1: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             4: {5: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]}
             }
            for _ in range(Globals.SIM_HOR + Globals.sim_hor_ex)]

    FA_4 = [{0: {3: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0],
                 5: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             2: {3: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             3: {3: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]}
             }
            for _ in range(Globals.SIM_HOR + Globals.sim_hor_ex)]

    FA_5 = [{1: {3: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             2: {5: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             4: {3: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]}
             }
            for _ in range(Globals.SIM_HOR + Globals.sim_hor_ex)]

    FA_6 = [{0: {6: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             1: {6: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             2: {6: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             3: {5: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0],
                6: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]},
             4: {1: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0],
                6: [simpy.Container(env, init=Globals.ROOM_TIME_P, capacity=Globals.ROOM_TIME_P), 0]}
             }
            for _ in range(Globals.SIM_HOR + Globals.sim_hor_ex)]


    #Create Room Ressources used in operate; First Key is the day; Second Key is the room number
    FA_1_OP = [{0: {2: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0],
                    4: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                1: {4: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                2: {4: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                3: {4: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                4: {4: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]}
                }
               for _ in range(Globals.SIM_HOR)]

    FA_2_OP = [{1: {2: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                2: {2: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                3: {2: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                4: {2: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]}
                }
               for _ in range(Globals.SIM_HOR)]

    FA_3_OP = [{0: {1: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                1: {1: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0],
                   5: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                2: {1: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                3: {1: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                4: {5: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]}
                }
               for _ in range(Globals.SIM_HOR)]

    FA_4_OP = [{0: {3: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0],
                    5: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                2: {3: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                3: {3: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]}
                }
               for _ in range(Globals.SIM_HOR)]

    FA_5_OP = [{1: {3: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                2: {5: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                4: {3: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]}
                }
               for _ in range(Globals.SIM_HOR)]

    FA_6_OP = [{0: {6: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                1: {6: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                2: {6: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                3: {5: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0],
                   6: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]},
                4: {5: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0],
                   1: [simpy.Container(env, init=Globals.ROOM_TIME, capacity=Globals.ROOM_TIME), 0, 0, 0]}
                }
               for _ in range(Globals.SIM_HOR)]

    # Used in Appointment
    Department_Rooms = [FA_1, FA_2, FA_3, FA_4, FA_5, FA_6]

    # Used in Operate
    OP_Rooms = [FA_1_OP, FA_2_OP, FA_3_OP, FA_4_OP, FA_5_OP, FA_6_OP]

    # Event which marks the end of simulation
    sim_finished = env.event()

    #Start process
    env.process(waiter(env, Department_Rooms, OP_Rooms, rooms, sim_finished))

    #Execute!
    env.run(sim_finished)

    #Debugging function
    for pat in Var.full_patient_list.copy():
        if len(pat) < 13:
            Var.rest_list.append(pat)
            Var.full_patient_list.pop(Var.full_patient_list.index(pat))

    #Monitoring
    Monitoring.mon_seed = 3141
    Monitoring.data_folder = "data_local/buffer" + str(int(buffer * 100)) + "_" + str(Monitoring.mon_seed)

    Monitoring.postponed_list[r] = Monitoring.monitor(Var.postponed_list)
    Monitoring.full_patient_list[r] = Monitoring.monitor(Var.full_patient_list)
    Monitoring.rest_list[r] = Monitoring.monitor(Var.rest_list)
    Monitoring.util_list_appo[r] = Monitoring.utilisation_appo(Department_Rooms, r)
    Monitoring.util_list_op[r] = Monitoring.utilisation_op(OP_Rooms, r)

    Monitoring.save_objects(r)


if __name__ == '__main__':

    #Loop trough possible buffers
    for buffer in Globals.grid:
        #Apply multiprocessing tool
        with Pool(Globals.number_of_processor) as p:
            p.starmap(run, [[i, i + Monitoring.mon_seed, buffer] for i in range(Monitoring.runs)])