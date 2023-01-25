#altura del laberinto [ X= 20, y= 15]
import random
import readchar
import os

POS_X = 0
POS_Y = 1

NUM_OF_MAP_OBJECTS = 11

obstacle_definition = """\
#############################
                             
     #######         ####    
                             
 ########     #####          
                         ####
                             
####      ############       
                             
#############                 
                      ###### 
                             
                   ####      
                             
#############################\
"""

my_position = [0, 1]


map_objects = []

end_game = False
died = False
battle = False

#create obstacle map
obstacle_definition = [list(row) for row in obstacle_definition.split("\n")]

MAP_WIDTH = len(obstacle_definition[0])
MAP_HEIGHT = len(obstacle_definition)
#POKEMONS
INICIAL_HP_CHARMANDER = 120
INICIAL_HP_MACHOP = 100
HP_BAR_SIZE = 20

actual_hp_charmander = INICIAL_HP_CHARMANDER
actual_hp_machop = INICIAL_HP_MACHOP

#main loop
while not end_game:

    # generate random objects on the map

    while len(map_objects) < NUM_OF_MAP_OBJECTS:
        new_position = [random.randint(0, MAP_WIDTH - 1), random.randint(0, MAP_HEIGHT -1 )]

        if new_position not in map_objects and new_position != my_position and\
                obstacle_definition[new_position[POS_Y]][new_position[POS_X]] != "#":
            map_objects.append(new_position)

    print("+" + "-" * MAP_WIDTH * 3 + "+")

    for cordinate_y in range(MAP_HEIGHT):
        print("|", end="")

        for cordinate_x in range(MAP_WIDTH):

            char_to_draw = "   "
            object_in_cell = None
            tail_in_cell = None

            for map_object in map_objects:
                if map_object[POS_X] == cordinate_x and map_object[POS_Y] == cordinate_y:
                    char_to_draw = " * "
                    object_in_cell = map_object

            if my_position[POS_X] == cordinate_x and my_position[POS_Y] == cordinate_y:
                char_to_draw = " @ "

                if object_in_cell:
                    map_objects.remove(object_in_cell)
                    #Pokemon fight starts
                    battle = True
                    actual_hp_machop = INICIAL_HP_MACHOP
                    actual_hp_charmander = INICIAL_HP_CHARMANDER




            if obstacle_definition[cordinate_y][cordinate_x] == "#":
                char_to_draw = "###"

            print("{}".format(char_to_draw), end="")
        print("|")

    print("+" + "-" * MAP_WIDTH * 3 + "+")


    #ask user where to go
    #direction = input("¿Dónde te quieres mover? [WASD]: ")
    direction = readchar.readchar().encode().decode()
    new_position = None

    if direction == "w":
        new_position = [my_position[POS_X], (my_position[POS_Y] - 1) % MAP_WIDTH]

    elif direction == "s":
        new_position = [my_position[POS_X], (my_position[POS_Y] + 1) % MAP_WIDTH]

    elif direction == "a":
        new_position = [(my_position[POS_X] - 1) % MAP_WIDTH, my_position[POS_Y] ]

    elif direction == "d":
        new_position = [(my_position[POS_X] + 1) % MAP_WIDTH, my_position[POS_Y] ]

    elif direction == "q":
        break

    if new_position:
        if obstacle_definition[new_position[POS_Y]][new_position[POS_X]] != "#":
            #ail.insert(0, my_position.copy())
            #tail = tail[:tail_length]
            my_position = new_position



    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")

    #Pokemon Battle
    if battle == True:

            print("empieza la batalla")



            while actual_hp_machop > 0 and actual_hp_charmander > 0:
                #combat starts in turns
                print("¡Turno del enemigo!\n¡Envía a Machop")
                machop_attack = random.randint(1, 2)
                if machop_attack == "1":
                    #golpe kárate
                    print("Machop ha utilizado: 'golpe kárate'")
                    actual_hp_charmander -= 10
                else:
                    #patada baja
                    print("Machop ha utilizado: 'patada baja' ")
                    actual_hp_charmander -= 12

                if actual_hp_charmander < 0:
                    actual_hp_charmander = 0
                if actual_hp_machop < 0:
                    actual_hp_machop = 0

                #generates life bars
                life_bar_charmander = int(actual_hp_charmander * HP_BAR_SIZE / INICIAL_HP_CHARMANDER)
                print("Charmander:    [{}{}] ({}/{})".format("*" * life_bar_charmander,
                                                             " " * (HP_BAR_SIZE - life_bar_charmander),
                                                             actual_hp_charmander, INICIAL_HP_CHARMANDER))
                life_bar_machop = int(actual_hp_machop * HP_BAR_SIZE / INICIAL_HP_MACHOP)
                print("Machop:    [{}{}] ({}/{})".format("*" * life_bar_machop,
                                                         " " * (HP_BAR_SIZE - life_bar_machop),
                                                         actual_hp_machop, INICIAL_HP_MACHOP))

                input("ENTER")
                if os.name == "nt":
                    os.system("cls")
                else:
                    os.system("clear")

                if actual_hp_machop > 0 and actual_hp_charmander <= 0:
                    actual_hp_charmander = 0
                    print("Has perdido!")
                    battle = False
                    end_game = True
                    died = True
                elif actual_hp_charmander > 0 and actual_hp_machop <= 0:
                    actual_hp_machop = 0
                    print("¡Has ganado!")
                    battle = False
                    end_game = True
                    died = True

                #player's turn
                print("¡Turno de Charmander!")
                charmander_attack = None
                #ataques de charmander [A]scuas y [L]anzallamas
                while charmander_attack not in ["A", "L", "N"]:
                    charmander_attack = input("\n ¿Qué ataque usará charmander? \n"
                                              "[A]scuas (-10PS)\n"
                                              "[L]anzallamas (-12ps)\n"
                                              "[N]ada\n")

                if charmander_attack == "A":
                    print("¡Charmarnder ha usado ascuas!")
                    actual_hp_machop -= 10

                elif charmander_attack == "L":
                    print("¡Charmander ha usado Lanzallamas")
                    actual_hp_machop -= 12
                elif charmander_attack == "N":
                    print("Charmander no hace nada")

                if actual_hp_charmander < 0:
                    actual_hp_charmander = 0
                if actual_hp_machop < 0:
                    actual_hp_machop = 0

                #generates life bars
                life_bar_charmander = int(actual_hp_charmander * HP_BAR_SIZE / INICIAL_HP_CHARMANDER)
                print("Charmander:    [{}{}] ({}/{})".format("*" * life_bar_charmander,
                                                             " " * (HP_BAR_SIZE - life_bar_charmander),
                                                             actual_hp_charmander, INICIAL_HP_CHARMANDER))
                life_bar_machop = int(actual_hp_machop * HP_BAR_SIZE / INICIAL_HP_MACHOP)
                print("Machop:    [{}{}] ({}/{})".format("*" * life_bar_machop,
                                                         " " * (HP_BAR_SIZE - life_bar_machop),
                                                         actual_hp_machop, INICIAL_HP_MACHOP))
                input("ENTER")
                if os.name == "nt":
                    os.system("cls")
                else:
                    os.system("clear")

                if actual_hp_machop > 0 and actual_hp_charmander <= 0:
                    actual_hp_charmander = 0
                    print("Has perdido!")
                    battle = False
                    end_game = True
                    died = True
                elif actual_hp_charmander > 0 and actual_hp_machop <= 0:
                    actual_hp_machop = 0
                    print("¡Has ganado!")
                    battle = False

    if died == True:
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")

        print("Estás muerto")

