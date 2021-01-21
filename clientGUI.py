# Team Sysadmins
# Version 0.6
# Date: 12/8/2020
# Jayden Stipek
# Duncan Spani
# Steve Foote
# Lucas Bradley


import socket
from threading import Thread
from tkinter import *
import pygame
from pygame.locals import *
import platform
import os
import sys
from subprocess import call
import queue
import random

FORMAT = 'utf-8'
BUFFER_SIZE = 8

# Used by Pygame thread right now
count = 0

"""
Class ClientGUI handles the client side logic for the game - including the 
game lobby GUI and logic along with the Game thread and logic.

Connects and communicates with class ServerGUI. Must have connection in order
to launch Lobby and play the game.
"""

# Set GUI for client-side lobby
class ClientGUI:

    # Setting up functionality
    def __init__(self):
        # Set up Networking Base
        self.port = 5050
        self.host = "localhost"
        # remote server IP
        # self.host = "64.227.48.38"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(1)
        # default name
        self.name = "Anonymous"
        # name of current active game
        self.activeGame = "" 
        # name of games that can be joined
        self.availableGames = []
        # checks that the gameslist is populated with something
        self.gamesInList = False
        # checks if player is currently in a game
        self.inActiveGame = False
        # queues used by active game for receiving messages
        self.startGameQueue = queue.Queue()
        self.gameEndQueue = queue.Queue()
        self.gameActionQueue = queue.Queue()
        self.gameStatsQueue = queue.Queue()

        # root window - hidden until sign-in and connection 
        self.window = Tk()
        self.window.protocol('WM_DELETE_WINDOW', self.onExit)
        self.window.title("Fight Game Lobby")
        self.window.configure(width = 500, height = 600)

        # Game List Box holds list of created games
        self.gameListLabel = Label(self.window, text = "Game List", pady = 5)
        self.gameListLabel.place(relwidth = 1)
        self.gameList = Listbox(self.window, font = ('Arial', 14, 'bold'), selectmode = SINGLE, width = 20, height = 2)
        self.gameList.place(relwidth = 1, relheight = .3, rely = .05)
        self.gameListScroll = Scrollbar(self.gameList)
        self.gameListScroll.pack(side = RIGHT, fill = Y)

        # Join Game Button joins available selected game
        self.joinBtn = Button(self.window, text = "Join Game", command = self.joinGame)
        self.joinBtn.place(relx = .44, rely = .36)

        # Create Game Button launch - launches the create game window
        self.createBtn = Button(self.window, text = "Create New Game", command = self.createWindow)
        self.createBtn.place(relx = .75, rely = .36)

        # Chat room area
        self.gameListLabel = Label(self.window, text = "Chat Room")
        self.gameListLabel.place(relwidth = 1, rely = .43)
        self.chatRoomTxt = Text(self.window,  font = ('System', 14, 'bold'), width = 20, height = 2)
        self.chatRoomTxt.place(relwidth = 1, relheight = .3, rely = .48)
        self.chatRoomTxt.config(state=DISABLED)
        self.chatScroll = Scrollbar(self.chatRoomTxt)
        self.chatScroll.pack(side = RIGHT, fill = Y)

        # Message bar for entering chat messages
        self.messageBar = Entry(self.window)
        self.messageBar.place(relwidth = .7, relx =.04, rely = .81)
        self.messageBar.focus()

        # Send chat Message Button
        self.sendBtn = Button(self.window, text = "Send Message", command = lambda: self.sendMessage(self.messageBar.get()))
        self.sendBtn.place(relx = .8, rely = .8)
        
        # Welcome label with Name
        self.welcomeLabel = Label(self.window, text = "", font = ('Arial', 14, 'bold'))
        self.welcomeLabel.place(relwidth = 1, rely = .9)

        # Hide main lobby window until login
        self.window.withdraw()

        # Set up log-in window
        self.login = Toplevel()
        self.login.protocol('WM_DELETE_WINDOW', self.onExit)
        self.login.title("Welcome to the Fight Game")
        self.login.configure(width=300, height=100)
        self.userLoginMSG = Label(self.login, text = "Enter User Name to Connect", justify = CENTER)
        self.userLoginMSG.place(relx = .24, rely = .05)

        # Text input for user name
        self.userName = Entry(self.login)
        self.userName.place(relheight = .2, relwidth = .5, relx = .25, rely = .3)
        self.userName.focus()

        # Login Button - which will initialize connect
        self.loginBtn = Button(self.login, text = "Login", command = self.loginConnect)
        self.loginBtn.place(relx = .45, rely = .6)
        
        self.window.mainloop()

    # Logging in and connecting to server
    def loginConnect(self):
        userName = self.userName.get()[0:8]
        self.name = userName.strip()
        # Make server connection
        self.sock.connect((self.host, self.port))
        # send username
        userName = userName.encode(FORMAT)
        self.sock.send(userName)
        self.welcomeLabel.config(text = "Welcome to Elemental Fighters " + str(self.name))
        # Remove login window
        self.login.destroy()
        # Reveal main window
        self.window.deiconify()
        # Set thread for receiving message from server
        receiveThread = Thread(target=self.receive)
        receiveThread.start()
    
    # Create the window for a specific Game 
    def createWindow(self):
        # Create Game window
        self.createGame = Toplevel()
        self.createGame.title("Create a New Game")
        self.createGame.configure(width=300, height=100)
        # game name
        self.newgameNameLbl = Label(self.createGame, text = "Game name: ", justify = LEFT)
        self.newgameNameLbl.place(relx = .1, rely = .05)
        self.gameName = Entry(self.createGame)
        self.gameName.place(relheight = .2, relwidth = .3, relx = .1, rely = .25)
        self.gameName.focus()
        # Number of Players
        self.newgameNumberLbl = Label(self.createGame, text = "Players: ", justify = RIGHT)
        self.newgameNumberLbl.place(relx = .7, rely = .05)
        self.numPlayers = IntVar(self.createGame)
        self.numPlayers.set(2)
        self.playerNumOption = OptionMenu(self.createGame, self.numPlayers, 2)
        self.playerNumOption.place(relx = .7, rely = .25)
        # create Game - passes game name and number of players to server
        self.createNewGameBtn = Button(self.createGame, text = "Create Game", 
                                       command = lambda: self.createNewGame(self.gameName.get(), self.numPlayers.get()))
        self.createNewGameBtn.place(relx = .1, rely = .62)

    # function called by Join button - used to spawn new thread for game
    def gameWindow(self):
        # launches gam GUI in new thread
        gameThread = Thread(target=self.launchGameThread)
        gameThread.start()

    """
    All game GUI related logic is launched from this function
    Game loop logic is handled by another function
    Messages are received into this function through Queues
    Messages are sent utilizing self.send...
    """
    # Launches game in separate window
    def launchGameThread(self):
        # set current client to an active game
        self.inActiveGame = True
        # disables the join / create game buttons
        self.disableButtons()
        pygame.init()

        # Sprite location directories
        sp1 = "sprites/sp1/"  # sprite 1
        sp2 = "sprites/sp2/"  # sprite 2
        sp3 = "sprites/sp3/"  # sprite 3
        sp4 = "sprites/sp4/"  # sprite 4
        sp5 = "sprites/sp5/"  # sprite 5
        BACKGROUND = "sprites/bg.png"  # background
        # set main pygame window and size
        colors = {"white" : (255,255,255), "red" : (255,40,40), "yellow" : (255,255,0), "green" : (0,255,0), "black" : (0,0,0), "blue" : (0,0,255)}
        tile = 'tile'
        end = '.png'
        win = pygame.display.set_mode((500,500))
        pygame.display.set_caption("Elemental Fighters")
        pygame.event.set_blocked(pygame.MOUSEMOTION)

        # player frames corresponding to move
        Drax = {"Idle": ["000"],
            "attack": ["016","017","010","004","005","006","007","008","009"],
            "dodge": ["010","011"],
            "block": ["017"],
            "special": ["016","017","010","004","005","006","007","008","009"],
            "death": ["016","015","013","012"],
            "health": 13,
            "damage": 2,
            "speed": 3,
            "magic": "fire"
                }
        Scorpio = {"Idle": ["000"],
            "attack": ["000","001","002","003","004","005","006","007","008","009","010"],
            "dodge": ["000","005","006","007","000"],
            "block": ["009","010"],
            "special": ["011","012","013","014","015","016","017","018"],
            "death": [],
            "health": 14,
            "damage": 1,
            "speed": 4,
            "magic": "earth"
                }
        Xion = {"Idle": ["022"],
            "attack": ["000","001","002","003","004","005","006","007","008","009","010","011","012","013","014","015","016","017","018","019","020","021","022","023","024"],
            "dodge": ["000","001","002","003","011","012","013","014"],
            "block": ["016","017","018","019","020","021","022","024"],
            "special": ["000","001","002","003","004","005","006","007","008","009","010","011","012","013","014","015","016","017","018","019","020","021","022","023","024","016","017","018","019","020","021","022","024"],
            "death": [],
            "health": 13,
            "damage": 1,
            "speed": 5,
            "magic": "water"
                }
        Abdul = {"Idle": ["022"],
            "attack": ["001","002","003","004","005","006","007","008"],
            "dodge": ["003","004","005","006","007","008"],
            "block": ["010","021"],
            "special": ["014","015","016","017","018"],
            "death": ["011","008","012"],
            "health": 12,
            "damage": 3,
            "speed": 2,
            "magic": "water"
                }
        Link = {"Idle": ["000"],
            "attack": ["005","006","007","008","009","010","011"],
            "dodge": ["003"],
            "block": ["005","006","007","008"],
            "special": ["008","009","010","005","006","007","008","009","010","005","006","007"],
            "death": [],
            "health": 15,
            "damage": 1,
            "speed": 1,
            "magic": "fire"
                }
        global fighters
        fighters = {
            "Drax": Drax,
            "Abdul": Abdul,
            "Link": Link,
            "Xion": Xion,
            "Scorpio": Scorpio
        }


        # load png of attack for char 1
        attack1 = [pygame.image.load(sp1+'tile000.png'), pygame.image.load(sp1+'tile001.png'), pygame.image.load(sp1+'tile002.png'), pygame.image.load(sp1+'tile003.png'), pygame.image.load(sp1+'tile004.png'), pygame.image.load(sp1+'tile005.png'), pygame.image.load(sp1+'tile006.png'), pygame.image.load(sp1+'tile007.png'), pygame.image.load(sp1+'tile008.png'), pygame.image.load(sp1+'tile009.png'), pygame.image.load(sp1+'tile010.png'), pygame.image.load(sp1+'tile011.png'), pygame.image.load(sp1+'tile012.png'), pygame.image.load(sp1+'tile013.png'), pygame.image.load(sp1+'tile014.png'), pygame.image.load(sp1+'tile015.png'), pygame.image.load(sp1+'tile016.png'), pygame.image.load(sp1+'tile017.png'), pygame.image.load(sp1+'tile018.png'), pygame.image.load(sp1+'tile019.png'), pygame.image.load(sp1+'tile020.png'), pygame.image.load(sp1+'tile021.png'), pygame.image.load(sp1+'tile022.png'), pygame.image.load(sp1+'tile023.png'), pygame.image.load(sp1+'tile024.png'),]
        # load png of attack for char 2
        attack2 = [pygame.image.load(sp2+'tile000.png'), pygame.image.load(sp2+'tile001.png'), pygame.image.load(sp2+'tile002.png'), pygame.image.load(sp2+'tile002.png'), pygame.image.load(sp2+'tile004.png'), pygame.image.load(sp2+'tile005.png'), pygame.image.load(sp2+'tile006.png'), pygame.image.load(sp2+'tile007.png'), pygame.image.load(sp2+'tile008.png'), pygame.image.load(sp2+'tile009.png'), pygame.image.load(sp2+'tile010.png'), pygame.image.load(sp2+'tile011.png'), pygame.image.load(sp2+'tile012.png'), pygame.image.load(sp2+'tile013.png'), pygame.image.load(sp2+'tile014.png'), pygame.image.load(sp2+'tile015.png'), pygame.image.load(sp2+'tile016.png'), pygame.image.load(sp2+'tile017.png'), pygame.image.load(sp2+'tile018.png'), pygame.image.load(sp2+'tile019.png'), pygame.image.load(sp2+'tile020.png'), pygame.image.load(sp2+'tile021.png'), pygame.image.load(sp2+'tile022.png'), pygame.image.load(sp2+'tile023.png'), pygame.image.load(sp2+'tile024.png'),]
        # load png of attack for char 3
        attack3 = [pygame.image.load(sp3+'tile000.png'), pygame.image.load(sp3+'tile001.png'), pygame.image.load(sp3+'tile002.png'), pygame.image.load(sp3+'tile003.png'), pygame.image.load(sp3+'tile004.png'), pygame.image.load(sp3+'tile005.png'), pygame.image.load(sp3+'tile006.png'), pygame.image.load(sp3+'tile007.png'), pygame.image.load(sp3+'tile008.png'), pygame.image.load(sp3+'tile009.png'), pygame.image.load(sp3+'tile010.png'), pygame.image.load(sp3+'tile011.png'), pygame.image.load(sp3+'tile012.png'), pygame.image.load(sp3+'tile013.png'), pygame.image.load(sp3+'tile014.png'), pygame.image.load(sp3+'tile015.png'), pygame.image.load(sp3+'tile016.png'), pygame.image.load(sp3+'tile017.png'), pygame.image.load(sp3+'tile018.png'), pygame.image.load(sp3+'tile019.png'), pygame.image.load(sp3+'tile020.png'), pygame.image.load(sp3+'tile021.png'), pygame.image.load(sp3+'tile022.png'), pygame.image.load(sp3+'tile023.png'), pygame.image.load(sp3+'tile024.png'),]
        # load png of attack for char 4
        attack4 = [pygame.image.load(sp4+'tile000.png'), pygame.image.load(sp4+'tile001.png'), pygame.image.load(sp4+'tile002.png'), pygame.image.load(sp4+'tile003.png'), pygame.image.load(sp4+'tile004.png'), pygame.image.load(sp4+'tile005.png'), pygame.image.load(sp4+'tile006.png'), pygame.image.load(sp4+'tile007.png'), pygame.image.load(sp4+'tile008.png'), pygame.image.load(sp4+'tile009.png'), pygame.image.load(sp4+'tile010.png'), pygame.image.load(sp4+'tile011.png'), pygame.image.load(sp4+'tile012.png'), pygame.image.load(sp4+'tile013.png'), pygame.image.load(sp4+'tile014.png'), pygame.image.load(sp4+'tile015.png'), pygame.image.load(sp4+'tile016.png'), pygame.image.load(sp4+'tile017.png'), pygame.image.load(sp4+'tile018.png'), pygame.image.load(sp4+'tile019.png'), pygame.image.load(sp4+'tile020.png'), pygame.image.load(sp4+'tile021.png'), pygame.image.load(sp4+'tile022.png'), pygame.image.load(sp4+'tile023.png'), pygame.image.load(sp4+'tile024.png'),]
        # load png of attack for char 5
        attack5 = [pygame.image.load(sp5+'tile000.png'), pygame.image.load(sp5+'tile001.png'), pygame.image.load(sp5+'tile002.png'), pygame.image.load(sp5+'tile003.png'), pygame.image.load(sp5+'tile004.png'), pygame.image.load(sp5+'tile005.png'), pygame.image.load(sp5+'tile006.png'), pygame.image.load(sp5+'tile007.png'), pygame.image.load(sp5+'tile008.png'), pygame.image.load(sp5+'tile009.png'), pygame.image.load(sp5+'tile010.png'), pygame.image.load(sp5+'tile011.png'), pygame.image.load(sp5+'tile012.png'), pygame.image.load(sp5+'tile013.png'), pygame.image.load(sp5+'tile014.png'), pygame.image.load(sp5+'tile015.png'), pygame.image.load(sp5+'tile016.png'), pygame.image.load(sp5+'tile017.png'), pygame.image.load(sp5+'tile018.png'), pygame.image.load(sp5+'tile019.png'), pygame.image.load(sp5+'tile020.png'), pygame.image.load(sp5+'tile021.png'), pygame.image.load(sp5+'tile022.png'), pygame.image.load(sp5+'tile023.png'), pygame.image.load(sp5+'tile024.png'),]

        char1 = pygame.image.load(sp1+'tile024.png')
        char2 = pygame.image.load(sp2+'tile001.png')
        char3 = pygame.image.load(sp3+'tile024.png')
        char4 = pygame.image.load(sp4+'tile024.png')
        char5 = pygame.image.load(sp5+'tile001.png')

        background = pygame.image.load(BACKGROUND)
        win.blit(background, (0, 0))

        clock = pygame.time.Clock()

        # starting pos for characters
        p1_x = 000
        p1_y = 400
        p2_x = 400
        p2_y = 400

        width = 96
        height = 96

        MAX_HEALTH = 100
        TEXT_COLOR = (20,20,20)
        FONT = pygame.font.Font(None, 30)
        ACTION_FONT = pygame.font.Font(None, 20)

        # Flips the sprite for player two 
        def flip_sprite(sprite, character):
            f_character = pygame.transform.flip(character, True, False)
            new_sprite = []
            for image in sprite:
                new_sprite.append(pygame.transform.flip(image, True, False))
            return new_sprite, f_character

        # Shows the health of the players
        def show_health(health1, health2):
            p1_color = "green"
            p2_color = "green"
            if health1/p1_MAX_HEALTH > .50:
                p1_color = "green"
            elif 50 >= health1/p1_MAX_HEALTH > .25:
                p1_color = "yellow"
            elif health1/p1_MAX_HEALTH <= .25:
                p1_color = "red"
            if health2/p2_MAX_HEALTH > .50:
                p2_color = "green"
            elif 50 >= health2/p2_MAX_HEALTH > .25:
                p2_color = "yellow"
            elif health2/p2_MAX_HEALTH <= .25:
                p2_color = "red"
            pygame.draw.rect(win, colors["white"], pygame.Rect(0, 0, 200, 20))
            pygame.draw.rect(win, colors["black"], pygame.Rect(2, 2, 196, 16))
            pygame.draw.rect(win, colors[p1_color], pygame.Rect(2, 2, (health1/p1_MAX_HEALTH)*196, 16))
            pygame.draw.rect(win, colors["white"], pygame.Rect(300, 0, 200, 20))
            pygame.draw.rect(win, colors["black"], pygame.Rect(302, 2, 196, 16))
            pygame.draw.rect(win, colors[p2_color], pygame.Rect(302, 2, (health2/p2_MAX_HEALTH)*196, 16))
            pygame.display.flip()
            
        # Selecting Character from the list of 5 different characters
        def character_select():
            win.blit(background,(0,0))
            pos = [(0,50),(100,50),(200,50),(300,50),(400,50)]  # x,y positions for character select
            characters = [char1, char2, char3, char4, char5]  # idle characters
            names = ["Drax", "Scorpio", "Xion", "Abdul", "Link"]  # character names
            for i in range(5):
                win.blit(characters[i],pos[i])
                pygame.display.update()
                text = FONT.render(str(i + 1), True, TEXT_COLOR)
                textR = text.get_rect()
                textR.center = (pos[i][0] + 50, pos[i][1] + 110)
                name = FONT.render(names[i], True, TEXT_COLOR)
                nameR = name.get_rect()
                nameR.center = (pos[i][0] + 50, pos[i][1] - 10)
                win.blit(name, nameR)
                win.blit(text, textR)
            text = FONT.render("PRESS KEY TO SELECT FIGHTER", True, TEXT_COLOR)
            textR = text.get_rect()
            textR.center = (250, 250)
            win.blit(text, textR)
            pygame.display.update()
            while True:
                event = pygame.event.wait()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        pygame.draw.rect(win, colors["red"], pygame.Rect(0, 50, 100, 150), 3)
                        pygame.display.flip()
                        player = attack1
                        player_idle = char1
                        name = names[0]
                        break
                    elif event.key == pygame.K_2:
                        pygame.draw.rect(win, colors["red"], pygame.Rect(100, 50, 100, 150), 3)
                        pygame.display.flip()
                        player = attack2
                        player_idle = char2
                        name = names[1]
                        break
                    elif event.key == pygame.K_3:
                        pygame.draw.rect(win, colors["red"], pygame.Rect(200, 50, 100, 150), 3)
                        pygame.display.flip()
                        player = attack3
                        player_idle = char3
                        name = names[2]
                        break
                    elif event.key == pygame.K_4:
                        pygame.draw.rect(win, colors["red"], pygame.Rect(300, 50, 100, 150), 3)
                        pygame.display.flip()
                        player = attack4
                        player_idle = char4
                        name = names[3]
                        break
                    elif event.key == pygame.K_5:
                        pygame.draw.rect(win, colors["red"], pygame.Rect(400, 50, 100, 150), 3)
                        pygame.display.flip()
                        player = attack5
                        player_idle = char5
                        name = names[4]
                        break
            # send necessary information to server for starting the game
            self.sendStartGame(name)
            new_player, new_player_idle = flip_sprite(player, player_idle)
            return new_player, new_player_idle, name

        # What happens when you choose your attack 
        def attack(player, player2, name, animation):
            if name == "Drax":
                frames = Drax[animation]
                if len(frames) != 0:
                    timing = (500 / len(frames))
                else:
                    timing = 1000
                path = sp1
                for frame in frames:
                    win.blit(background, (0, 0))
                    win.blit(player2, (p2_x, p2_y))
                    show_health(player_health, player2_health)
                    pygame.display.update()
                    f = pygame.image.load(path + tile + frame + end)
                    win.blit(pygame.transform.flip(f, True, False), (p1_x, p1_y))
                    pygame.display.update()
                    pygame.time.wait(int(timing))
            elif name == "Scorpio":
                frames = Scorpio[animation]
                if len(frames) != 0:
                    timing = (500 / len(frames))
                else:
                    timing = 1000
                path = sp2
                for frame in frames:
                    win.blit(background, (0, 0))
                    win.blit(player2, (p2_x, p2_y))
                    show_health(player_health, player2_health)
                    pygame.display.update()
                    f = pygame.image.load(path + tile + frame + end)
                    win.blit(pygame.transform.flip(f, True, False), (p1_x, p1_y))
                    pygame.display.update()
                    pygame.time.wait(int(timing))
            elif name == "Xion":
                frames = Xion[animation]
                if len(frames) != 0:
                    timing = (500 / len(frames))
                else:
                    timing = 1000
                path = sp3
                for frame in frames:
                    win.blit(background, (0, 0))
                    win.blit(player2, (p2_x, p2_y))
                    show_health(player_health, player2_health)
                    pygame.display.update()
                    f = pygame.image.load(path + tile + frame + end)
                    win.blit(pygame.transform.flip(f, True, False), (p1_x, p1_y))
                    pygame.display.update()
                    pygame.time.wait(int(timing))
            elif name == "Abdul":
                frames = Abdul[animation]
                if len(frames) != 0:
                    timing = (500 / len(frames))
                else:
                    timing = 1000
                path = sp4
                for frame in frames:
                    win.blit(background, (0, 0))
                    win.blit(player2, (p2_x, p2_y))
                    show_health(player_health, player2_health)
                    pygame.display.update()
                    f = pygame.image.load(path + tile + frame + end)
                    win.blit(pygame.transform.flip(f, True, False), (p1_x, p1_y))
                    pygame.display.update()
                    pygame.time.wait(int(timing))
            elif name == "Link":
                frames = Link[animation]
                if len(frames) != 0:
                    timing = (500 / len(frames))
                else:
                    timing = 1000
                path = sp5
                for frame in frames:
                    win.blit(background, (0, 0))
                    win.blit(player2, (p2_x, p2_y))
                    show_health(player_health, player2_health)
                    pygame.display.update()
                    f = pygame.image.load(path + tile + frame + end)
                    win.blit(pygame.transform.flip(f, True, False), (p1_x, p1_y))
                    pygame.display.update()
                    pygame.time.wait(int(timing))

        # What happens when you get the opponents attack from the server
        def p2_attack(player2, player, name, animation):
            # keep idle frame p1_x, p1_y
            # keep animation frame p2_x, p2_y
            if animation == "":
                return
            if name == "Drax":
                frames = Drax[animation]
                if len(frames) != 0:
                    timing = (500 / len(frames))
                else:
                    timing = 1000
                path = sp1
                for frame in frames:
                    # idle
                    win.blit(background, (0, 0))
                    win.blit(player, (p1_x, p1_y))
                    show_health(player_health, player2_health)
                    pygame.display.update()
                    # animation
                    f = pygame.image.load(path + tile + frame + end)
                    win.blit(f, (p2_x, p2_y))
                    pygame.display.update()
                    pygame.time.wait(int(timing))
            elif name == "Scorpio":
                frames = Scorpio[animation]
                if len(frames) != 0:
                    timing = (500 / len(frames))
                else:
                    timing = 1000
                path = sp2
                for frame in frames:
                    win.blit(background, (0, 0))
                    win.blit(player, (p1_x, p1_y))
                    show_health(player_health, player2_health)
                    pygame.display.update()
                    f = pygame.image.load(path + tile + frame + end)
                    win.blit(f, (p2_x, p2_y))
                    pygame.display.update()
                    pygame.time.wait(int(timing))
            elif name == "Xion":
                frames = Xion[animation]
                if len(frames) != 0:
                    timing = (500 / len(frames))
                else:
                    timing = 1000
                path = sp3
                for frame in frames:
                    win.blit(background, (0, 0))
                    win.blit(player, (p1_x, p1_y))
                    show_health(player_health, player2_health)
                    pygame.display.update()
                    f = pygame.image.load(path + tile + frame + end)
                    win.blit(f, (p2_x, p2_y))
                    pygame.display.update()
                    pygame.time.wait(int(timing))
            elif name == "Abdul":
                frames = Abdul[animation]
                if len(frames) != 0:
                    timing = (500 / len(frames))
                else:
                    timing = 1000
                path = sp4
                for frame in frames:
                    win.blit(background, (0, 0))
                    win.blit(player, (p1_x, p1_y))
                    show_health(player_health, player2_health)
                    pygame.display.update()
                    f = pygame.image.load(path + tile + frame + end)
                    win.blit(f, (p2_x, p2_y))
                    pygame.display.update()
                    pygame.time.wait(int(timing))
            elif name == "Link":
                frames = Link[animation]
                if len(frames) != 0:
                    timing = (500 / len(frames))
                else:
                    timing = 1000
                path = sp5
                for frame in frames:
                    win.blit(background, (0, 0))
                    win.blit(player, (p1_x, p1_y))
                    show_health(player_health, player2_health)
                    pygame.display.update()
                    f = pygame.image.load(path + tile + frame + end)
                    win.blit(f, (p2_x, p2_y))
                    pygame.display.update()
                    pygame.time.wait(int(timing))
        
        # Displaying Wait 
        def display_wait():
            name = FONT.render("Waiting for other player...", True, TEXT_COLOR)
            nameR = name.get_rect()
            nameR.center = (250, 250)
            win.blit(name, nameR)
            pygame.display.update()

        # Displaying Lose
        def display_lose():
            win.blit(background,(0,0))
            name = FONT.render("You Lose!", True, TEXT_COLOR)
            nameR = name.get_rect()
            nameR.center = (250, 250)
            win.blit(name, nameR)
            pygame.display.update()

        # Displaying Win
        def display_win():
            win.blit(background,(0,0))
            name = FONT.render("You Win!", True, TEXT_COLOR)
            nameR = name.get_rect()
            nameR.center = (250, 250)
            win.blit(name, nameR)
            pygame.display.update()

        # Displaying Actions
        def display_actions():
            box_pos = [(20, 80, 70, 40), (120, 80, 70, 40), (20, 160, 70, 40), (120, 160, 70, 40), (65, 240, 80, 40)]
            action_cen = [(55, 100), (155, 100), (55, 185), (155, 185), (105, 260)]
            key_pos = [(80, 140), (180, 140), (80, 220), (180, 220), (95, 300)]
            actions = ['Attack', 'Dodge', 'Block', 'Magic', 'Quit']
            keys = ['Q', 'W', 'E', 'R', 'ENTER']
            for i in range(5):
                if actions[i] == "Quit":
                    pygame.draw.rect(win, colors["red"], pygame.Rect(box_pos[i]), 2)
                    name = FONT.render(actions[i], True, colors["red"])
                    nameR = name.get_rect()
                    nameR.center = action_cen[i]
                    key = FONT.render(keys[i], True, colors["red"])
                    keyR = name.get_rect()
                    keyR.center = key_pos[i]
                    win.blit(name, nameR)
                    win.blit(key, keyR)
                else:
                    pygame.draw.rect(win, colors["black"], pygame.Rect(box_pos[i]), 2)
                    name = FONT.render(actions[i], True, TEXT_COLOR)
                    nameR = name.get_rect()
                    nameR.center = action_cen[i]
                    key = FONT.render(keys[i], True, TEXT_COLOR)
                    keyR = name.get_rect()
                    keyR.center = key_pos[i]
                    win.blit(name, nameR)
                    win.blit(key, keyR)
            pygame.display.flip()
        def display_magic(name,p1):
            if p1:
                coor = (p1_x, p1_y)
            else:
                coor = (p2_x, p2_y)

            radius = [0,100,200,300,400,500,600,700]
            color = "red"
            if name == "Drax":
                color = "red"
            elif name == "Scorpio":
                color = "green"
            elif name == "Xion":
                color = "blue"
            elif name ==  "Abdul":
                color = "blue"
            elif name == "Link":
                color = "red"
            for i in range(8):
                pygame.draw.circle(win, colors[color],coor, radius[i])
                pygame.display.flip()
                pygame.time.wait(100)

        # Obtaining the players health from the dictonary
        def get_player_health(name):
            if name == "Drax":
                return Drax["health"]
            elif name == "Scorpio":
                return Scorpio["health"]
            elif name == "Xion":
                return Xion["health"]
            elif name ==  "Abdul":
                return Abdul["health"]
            elif name == "Link":
                return Link["health"]

        # Obtaining Opponent players health from the dictonary
        def getOtherPlayerInfo(name):
            if name == "Drax":
                return attack1, char1
            elif name == "Scorpio":
                return attack2, char2
            elif name == "Xion":
                return attack3, char3
            elif name ==  "Abdul":
                return attack4, char4
            elif name == "Link":
                return attack5, char5
                
        def display_draw():
            win.blit(background, (0, 0))
            name = FONT.render("Draw!", True, TEXT_COLOR)
            nameR = name.get_rect()
            nameR.center = (250, 250)
            win.blit(name, nameR)
            pygame.display.update()

        def display_action_text(p1_name, players_move, p2_name, action):
            p2text = FONT.render(p2_name+" used "+action, True, TEXT_COLOR)
            p2textr = p2text.get_rect()
            p2textr.center = (350, 250)
            win.blit(p2text, p2textr)
            p1text = FONT.render(p1_name+" used "+players_move, True, TEXT_COLOR)
            p1textr = p1text.get_rect()
            p1textr.center = (350, 200)
            win.blit(p1text, p1textr)
            pygame.display.update()
            
        pygame.time.wait(500)
        # DEFAULT PLAYER ANIMATIONS AND NAME FOR FUNCTIONS
        p1_player, p1_player_idle, p1_name = character_select()
        # wait to receive message from other player
        waitingForOtherPlayerChoices = True 
        while waitingForOtherPlayerChoices:
            if not self.startGameQueue.empty():
                # receive player 2 default information
                p2_name = self.startGameQueue.get()
                p2_player, p2_player_idle = getOtherPlayerInfo(p2_name)
                waitingForOtherPlayerChoices = False

        p1_MAX_HEALTH = get_player_health(p1_name)
        player_health = p1_MAX_HEALTH
        p2_MAX_HEALTH = get_player_health(p2_name)
        player2_health = p2_MAX_HEALTH  # subject to change

        win.blit(background,(0,0))
        # send/recieve player choice
        run = True
        turn = True
        
        players_move = ""
        
        while run:
            for event in pygame.event.get():
                # end game tasks
                if event.type == QUIT:
                    # notify other player of quit
                    self.sendGameActions("QUIT")
                    self.exitGameTasks()
                    run = False
                    pygame.quit()
                    sys.exit()
            # show initial screen
            show_health(player_health, player2_health)  # change to local and opponent health values
            win.blit(p1_player_idle, (p1_x, p1_y))
            win.blit(p2_player_idle, (p2_x, p2_y))
            display_actions()
            pygame.display.update()
            # make sure other player has not quit
            if not self.gameEndQueue.empty():
                p2_attack(p1_player, p2_player_idle, p1_name, "death")
                display_win()
                pygame.time.wait(5000)
                self.exitGameTasks()
                run = False
                pygame.quit()
                sys.exit()
            # wait for message to be received
            while self.gameActionQueue.empty() and turn == False:
                if not self.gameEndQueue.empty(): 
                    break
                pygame.time.wait(1000)
            # retrieve message regarding game actions
            if not self.gameActionQueue.empty() and turn == False:
                # setup custom event type
                eventTest = pygame.event.Event(pygame.USEREVENT, {"action": self.gameActionQueue.get()})
                pygame.event.post(eventTest)
                playerMove = pygame.event.poll()
                # display move on screen
                display_action_text(p1_name, players_move, p2_name, playerMove.action)
                pygame.time.wait(1000)
                # perform player 2 animations
                p2_attack(p2_player, p1_player_idle, p2_name, playerMove.action)
                # perform player 1 animations
                attack(p1_player, p2_player_idle, p1_name, players_move)
                # make sure proper magic animation performed
                if playerMove.action == "special":
                    display_magic(p2_name, False)
                if players_move == "special":
                    display_magic(p1_name, True)
                # calculate new payer health
                player_health -= gameLoop(p1_name, p2_name, players_move, playerMove.action)
                # send new health to server for 2nd player
                self.sendGameStats(str(player_health))
                pygame.time.wait(2000)
                # receive player 2 new health
                if not self.gameStatsQueue.empty():
                    otherHealth = self.gameStatsQueue.get()
                    player2_health = float(otherHealth)
                # modify health bar with new health
                show_health(player_health, player2_health)
                turn = True

            if turn == True: 
                event = pygame.event.wait()
                # retrieve keypress and associate it with player move
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        self.sendGameActions("attack")
                        players_move = "attack"
                        turn = False
                    elif event.key == pygame.K_w:
                        self.sendGameActions("dodge")
                        
                        players_move = "dodge"
                        turn = False
                    elif event.key == pygame.K_e:
                        self.sendGameActions("block")
                        players_move = "block"
                        
                        turn = False
                    elif event.key == pygame.K_r:
                        self.sendGameActions("special")
                        players_move = "special"
                        turn = False
                    elif event.key == pygame.K_RETURN:
                        # handle death animations
                        attack(p1_player, p2_player_idle, p1_name, "death")
                        # show game lost message
                        display_lose()
                        self.sendGameActions("QUIT")
                        pygame.time.wait(2000)
                        self.exitGameTasks()
                        run = False
                        pygame.quit()
                        sys.exit()

            win.blit(background, (0, 0))
            pygame.display.update()
            # calculate who wins based on players health
            if player_health <= 0 and player2_health <= 0:
                attack(p1_player, p2_player_idle, p1_name, "death")
                p2_attack(p2_player, p1_player_idle, p2_name, "death")
                display_draw()
                pygame.time.wait(5000)
                self.sendGameActions("QUIT")
                self.exitGameTasks()
                run = False
                pygame.quit()
                sys.exit()
            elif player_health <= 0:
                attack(p1_player, p2_player_idle, p1_name, "death")
                display_lose()
                pygame.time.wait(5000)
                self.sendGameActions("QUIT")
                self.exitGameTasks()
                run = False
                pygame.quit()
                sys.exit()   
            elif player2_health <= 0:
                display_win()
                pygame.time.wait(5000)
                self.sendGameActions("QUIT")
                self.exitGameTasks()
                run = False
                pygame.quit()
                sys.exit()
                
            clock.tick(30)  # fps of game

    # parse incoming messages for header info and message body
    def messageParser(self, message):
        if message:
            print("Here is the message:\n " + message)
            parsedMessage = message.split("\n")
            return parsedMessage[0], parsedMessage[1]
        return

    """
    Check if game is available to join
    If it is available add the name to the list
    of available games
    """
    def isGameAvailable(self, gameString):
        parsedGame = gameString.split()
        print(parsedGame)
        if parsedGame: 
            if parsedGame[2] == "Waiting":
                self.availableGames.append(parsedGame[0])
    
    """
    Parse stringified game list received from server
    Update displayed game list in the lobby
    Send games to isGameAvailable to check if they can be joined
    """
    def gameParser(self, message):
        self.availableGames.clear()
        self.gameList.delete(0, END)
        self.joinBtn.config(state=DISABLED)
        self.gamesInList = False
        if message != "EMPTY":
            self.gamesInList = True
            if self.inActiveGame == False:
                self.joinBtn.config(state=NORMAL)
            parsedGames = message.split(";")
            for game in parsedGames:
                self.gameList.insert(END, game)
                self.isGameAvailable(game)        
    
    """
    Receives messages from server and uses messageParser to
    determine where to send the body of the message.
    """ 
    def receive(self):
        while True:
            try:
                msg = self.receiveMessages()
                # parse for relevant info
                header, message = self.messageParser(msg)
                if message and header:
                    # chat messages
                    if header == "message":
                        # insert message into lobby chat
                        self.chatRoomTxt.config(state=NORMAL)
                        self.chatRoomTxt.insert(END, message + "\n")
                        self.chatRoomTxt.config(state=DISABLED)
                        self.chatRoomTxt.see(END)
                    # stringified game list
                    elif header == "newgame":
                        # insert new game info into game list
                        self.gameParser(message)
                    # starting game information for player 2
                    elif header == "sendstart":
                        self.startGameQueue.put(message)
                    # game health information
                    elif header == "gamestats":
                        self.gameStatsQueue.put(message)
                    # game actions
                    elif header == "gamecommand":
                        # insert game command into queue
                        if message == "QUIT":
                            self.gameEndQueue.put(message)
                        else:
                            self.gameActionQueue.put(message)
            except socket.timeout:
                continue
            except IOError:
                self.sock.close()
                sys.exit(0)
    
    # send chat message
    def sendMessage(self, message):
        if message:
            self.messageBar.delete(0, END)
            message = "message\n" + message
            self.send(message)

    # send starting game information
    def sendStartGame(self, message):
        message = "sendstart\n" + self.activeGame + " " + message
        self.send(message)

    # send game actions to server
    def sendGameActions(self, message):
        message = "gamecommand\n" + self.activeGame + " " + message
        self.send(message)

    # send game stats (AKA health)
    def sendGameStats(self, message):
        message = "gamestats\n" + self.activeGame + " " + message
        self.send(message)

    # send join game info to server
    def sendJoinGame(self, message):
        message = "joingame\n" + message
        self.send(message)

    # join a selected Game
    def joinGame(self):
        selectedGame = self.gameList.get(self.gameList.curselection())
        gameParsed = selectedGame.strip().split()
        if gameParsed:
            # ensure game is available to accept players
            if gameParsed[0] in self.availableGames:
                self.activeGame = gameParsed[0]
                self.sendJoinGame(self.activeGame)
                self.gameWindow()

    """
    All messages are sent with this function
    Messages are pre-pended with header by other functions
    and then sent with this send function
    Sends the receive the size of the message first
    """
    def send(self, message):
        message = message.encode(FORMAT)
        message_length = len(message)
        send_length = str(message_length).encode(FORMAT)
        send_length += b' ' * (BUFFER_SIZE - len(send_length))
        self.sock.send(send_length)
        self.sock.send(message)

    """
    All received messages utilize this function though are handled
    within the receive thread
    This function checks the size of the message to receive first
    """
    def receiveMessages(self):
        message_length = self.sock.recv(BUFFER_SIZE).decode(FORMAT)
        if message_length:
            message_length = int(message_length)
            message = self.sock.recv(message_length).decode(FORMAT)
            return message
        raise Exception("Received empty message")
    
    """
    Send newly created game info to server
    Set this new name to current active game
    Launch a new game
    """
    def createNewGame(self, game, num):
        # destroy the create game window
        self.createGame.destroy()
        message = "newgame\n" + game + "\t" + str(num)
        self.send(message)
        self.activeGame = game
        self.gameWindow()
        
    # disable some functionality when in game
    def disableButtons(self):
        if self.inActiveGame == True:
            self.joinBtn.config(state=DISABLED)
            self.createBtn.config(state=DISABLED)
        else:
            self.createBtn.config(state=ACTIVE)
            if self.gamesInList == True:
                self.joinBtn.config(state=ACTIVE)

    # exit game and clear all queues, activegame
    def exitGameTasks(self):
        self.activeGame = ""
        self.inActiveGame = False
        self.disableButtons()
        self.gameActionQueue.queue.clear()
        self.startGameQueue.queue.clear()
        self.gameEndQueue.queue.clear()
        
    # set up exit behavior
    def onExit(self):
        self.sock.close()
        self.window.destroy()

"""
 A function to calculate Magic damage to keep it clean in the loop
 Magic Works as follows
 fire does double damage to Earth and half to Water
 Earth does double damage to Water and half to Fire
 Water does double damage to Fire and half to Earth
"""
def calculateMagic(fighter,opponentFighter):
    if(fighters[opponentFighter]["magic"] == "fire"): #Fire Case
        if(fighters[fighter]["magic"] == "earth"):
            return fighters[opponentFighter]["damage"] * 2 # 2X the damage
        elif(fighters[fighter]["magic"] == "water"):
            return fighters[opponentFighter]["damage"] / 2 # 1/2 the damage
        else:
            return fighters[opponentFighter]["damage"] # regular damage
    elif(fighters[opponentFighter]["magic"] == "water"): #Water Case
        if(fighters[fighter]["magic"] == "fire"):
            return fighters[opponentFighter]["damage"] * 2 # 2x the damage
        elif(fighters[fighter]["magic"] == "earth"):
            return fighters[opponentFighter]["damage"] / 2 # 1/2 the damage
        else:
            return fighters[opponentFighter]["damage"] # regular damage
    elif(fighters[opponentFighter]["magic"] == "earth"): #Earth Case
        if(fighters[fighter]["magic"] == "water"):
            return fighters[opponentFighter]["damage"] * 2
        elif(fighters[fighter]["magic"] == "fire"):
            return fighters[opponentFighter]["damage"] / 2
        else:
            return fighters[opponentFighter]["damage"] 

"""
 This is where the calculations are done on how much 
 damage is taken from this client. Also takes in 
 opponenet fighter adn move so to be able to calculate damage
 easier
"""
def gameLoop(fighter, opponentFighter, move, opponentMove):
    
# ------------------------------------Attack Logic----------------------------------------------------
    if(opponentMove == "attack"):
        if(move == "dodge"):
            if(random.randint(1,10) > 5): 
                print("You Dodged Successfully - No Damage")
            else:
                print("Dodge Failed!")
                print("Opponent Attacked, you take " + str(fighters[opponentFighter]["damage"]) + " Damage\n")
                return fighters[opponentFighter]["damage"] 
        elif(move == "block"):
            print("You Blocked their attack!")
            print("You Take " + str(fighters[opponentFighter]["damage"]/2) + " Damage\n")
            return (fighters[opponentFighter]["damage"]/2)
        else:
            print("Opponent Attacked, you take " + str(fighters[opponentFighter]["damage"]) + " Damage\n")
            return fighters[opponentFighter]["damage"] 
# ------------------------------------Magic Logic----------------------------------------------------
    elif(opponentMove == "special"): 
        print("You opponent used Magic")
        if(move == "dodge"):
            if(random.randint(1,10) > 5): 
                print("You Dodged Successfully - No Damage")
                return 0
            else:
                print("Dodge Failed!")
    
        magicDamage = calculateMagic(fighter,opponentFighter) #Calculates damage 
        if(move == "block"):
            magicDamage /= 2
        print("Opponent used Magic you take " + str(magicDamage) + " Damage\n")
        return magicDamage
    return 0

app = ClientGUI()
mainloop()