# Team Sysadmins
# Version 1.6
# Date: 12/8/2020
# Jayden Stipek
# Duncan Spani
# Steve Foote
# Lucas Bradley


import socket
import threading
import select

BUFFER_SIZE = 8
FORMAT = "utf-8"
PORT = 5050
#HOST = "64.227.48.38"
HOST = "localhost"
# usernames in use
usernames = []
# all connected sockets
sockets = []
# dictionary with key:sock value:name of clients
clients = {}
# dictionary with key:gamename value:game object
games = {}

"""
serverGUI.py handles the server side logic for the game - including the passing of messages between the Game threads 
and setting up the games.

Connects and communicates with class clientGUI.

Utilizes Class Game to handle the server side game instance logic 
"""

# Game class to track game info
class Game:
    def __init__(self, name, size):
        self.name = name
        self.maxSize = size
        self.running = False
        self.players = []
        self.playerCharacterChoices = {}
    # ensures the player requesting join meets criteria
    def allowJoin(self, sock):
        # game still waiting for players to join
        if self.running == False:
            self.players.append(sock)
            self.playerCharacterChoices[sock] = ""
            # if game is full then it is
            if len(self.players) == int(self.maxSize):
                self.running = True

# Get the other player from the Game
def getOtherPlayer(game, curPlayer):
    otherPlayer = game.players[0] if curPlayer == game.players[1] else game.players[1] 
    return otherPlayer

# Handle removing players and removing game from list
def gameObjectHandler(game, player):
    print("Entered Object Handler")
    del games[game]
    newlist = stringifyGames(games)
    print(newlist)
    broadcast(player, newlist, "newgame")

"""
Handles new client connections
This includes checking if the username already exists and modifying it
if it does, adding the client socket and username to appropriate dictionaries,
and sending the new client the current games list.
"""
def setNewClient(connection):
    clientName = connection.recv(BUFFER_SIZE).decode(FORMAT)
    sockets.append(connection)
    # modifying name if it is already in use
    if clientName in usernames:
        clientName = clientName + "1"
    usernames.append(clientName)
    clients[connection] = clientName
    # print server side that connection was made
    print(str(clientName)+" connected to the server")
    message = "message\n" + "CONNECTED TO THE SERVER"
    send(connection, message)
    # sending current game list
    gamesToSend = stringifyGames(games)
    if gamesToSend:
        send(connection, "newgame\n" + gamesToSend)

"""
All messages sent from the server pass using this function
Headers are prepended to the message before entering this function
Size of the following message is sent first to the client
"""
def send(connection, message):
    message = message.encode(FORMAT)
    message_length = len(message)
    send_length = str(message_length).encode(FORMAT)
    send_length += b' ' * (BUFFER_SIZE - len(send_length))
    connection.send(send_length)
    connection.send(message)

# Receive messages and handle length of messages
def receive(connection):
    message_length = connection.recv(BUFFER_SIZE).decode(FORMAT)
    print(str(message_length)+' received message length')
    if message_length:
        message_length = int(message_length)
        message = connection.recv(message_length).decode(FORMAT)
        print(str(message)+' received message')
        return message
    else:
        return ""
    raise Exception("Received empty message")
    
"""
Messages that must be received by all clients are sent through this function
The header is pre-pended bases on the type argument passed.
Two types of messages are passed to all clients:
    Chat messages
    Game list messages (new games added, current games change, game removed)
"""
def broadcast(sender, message, type):
    # if chat message add sender info
    if type == "message":
        msgToSend = type + "\n" + str(clients[sender] + ": ") + message
        for sock in sockets:
            if sock != sockets[0]:
                print(msgToSend)
                send(sock, msgToSend)
    # if game list changes - send just game info
    elif type == "newgame":
        gameString = type + "\n" + message
        for sock in sockets:
            if sock != sockets[0]:
                send(sock, gameString)
                print(gameString)
                 
# Parse incoming messages for header info
def messageParser(message):
    parsedMessage = message.split("\n")
    return parsedMessage[0], str(parsedMessage[1])

# Parse the new game info sent by client
def gameParser(message):
    # game name and players split by \t char
    parsedGame = message.split("\t")
    return parsedGame[0], parsedGame[1]

"""
This function turns the dictionary Games into a string format
that can be easily sent and parsed by the client
If Games is empty it just send a single argument "EMPTY" which is
interpreted by the client 
"""
def stringifyGames(gameslist):
    string = str()
    if gameslist:
        for name in gameslist:
            game = gameslist[name]
            status = "Waiting for players..." if game.running == False else "Game is Full"
            string += (name + "              " + str(len(game.players)) + "/" + 
                str(game.maxSize) + "               " + status + ";")
    else:
        string = "EMPTY"
    return string

# Start and run main thread of server
"""
This is the main function of the server side program
This runs on a continuous loop and utilizes other functions within this script to handle the message body 

Takes messages from the clientGUI class and decides what action to take based on the header
Headers available are message, newgame, joingame, sendstart, gamestats and gamecommand
Based on this information the server will decide what needs to be done with the message body
"""
def start():
    # Make connection
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    # Add server socket to lists of sockets
    sockets.append(server)

    print("Server has started on host:",HOST,"...")
    
    while True:
        # continually checks list of sockets for something to read, something to write, or error state
        clientSockets, writeSockets, errSockets = select.select(sockets, [], [], 1) # set T.O. to 1 sec
        
        # Iterate through clientSockets
        for sock in clientSockets:
            # If server socket then create new connection
            if sock == server:
                # Handle new connection with client
                client, clientAddress = server.accept()
                print(str(client)+' connected to the lobby...')
                setNewClient(client)
            else:
                try:
                    # receive any message
                    msg = receive(sock)
                    # if both header and message have data
                    if msg:
                        # parse for relevant info
                        header, message = messageParser(msg)
                        # if header is message (lobby chat message)
                        if header == "message":
                            # broadcast message to all clients in lobby
                            broadcast(sock, message, header)
                        # if header is new game creation
                        elif header == "newgame":
                            # parse game info for name and players
                            gameName, numPlayers = gameParser(message)
                            # create new game object
                            newGame = Game(gameName, numPlayers)
                            # add creator to game players list
                            newGame.allowJoin(sock)
                            # add game to game list
                            games[gameName] = newGame
                            # updated list of games stringified
                            updatedGameList = stringifyGames(games)
                            # send new game info to clients
                            broadcast(sock, updatedGameList, header)
                        # handles allowing a client to join a game and updating the game
                        elif header == "joingame":
                            games[message].allowJoin(sock)
                            otherPlayer = games[message].players[0]
                            joinedMessage = "message\n" + clients[sock] + " has joined your game!"
                            send(otherPlayer, joinedMessage)
                            # updated list of games stringified
                            updatedGameList = stringifyGames(games)
                            # send updated game info to clients
                            broadcast(sock, updatedGameList, "newgame")
                        # handles sending starting game state to other player in game
                        elif header == "sendstart":
                            # parse the game name and player choice from message
                            gameName = message.rsplit(None, 1)[0]
                            gameCharChoice = message.rsplit(None, 1)[1]
                            games[gameName].playerCharacterChoices[sock] = gameCharChoice
                            if games[gameName].running == True:
                                message = "sendstart\n" + gameCharChoice
                                otherPlayer = getOtherPlayer(games[gameName], sock)
                                send(otherPlayer, message)
                                message = "sendstart\n" + games[gameName].playerCharacterChoices[otherPlayer]
                                send(sock, message)
                        # handles sending game health info to other player
                        elif header == "gamestats":
                            gameName = message.rsplit(None, 1)[0]
                            gameMessage = message.rsplit(None, 1)[1]
                            message = "gamestats\n" + gameMessage
                            otherPlayer = getOtherPlayer(games[gameName], sock)
                            send(otherPlayer, message)
                        # handles sending game actions to other player
                        elif header == "gamecommand":
                            gameName = message.rsplit(None, 1)[0]
                            gameMessage = message.rsplit(None, 1)[1]
                            message = "gamecommand\n" + gameMessage
                            otherPlayer = getOtherPlayer(games[gameName], sock) 
                            send(otherPlayer, message)
                            # removes game from list and sends updated list
                            if gameMessage == "QUIT":
                                del games[gameName]
                                newlist = stringifyGames(games)
                                broadcast(sock, newlist, "newgame")
                    else:
                        print("Message on exit: " + msg)
                        # if select sees socket as readable, but gets EOF (no data)
                        # then the socket connection has closed. Remove and close.
                        sockets.remove(sock)
                        sock.close()
                        broadcast(sock, " DISCONNECTED FROM THE LOBBY", "message")
                        print(str(clients[sock])+' has disconnected from the server.')
                        del clients[sock]     
                except:        
                    continue
start()