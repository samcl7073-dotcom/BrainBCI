# KEY FEATURES FOR GRADING:
# 1. Brain-Computer Interface (BCI) Integration: Real-time EEG data processing 
#    using Lab Streaming Layer (LSL). The game calculates mean band powers 
#    to determine 'Focus' or 'Idle' states, allowing the ball to be controlled 
#    via brain activity.
# 2. Object-Oriented Obstacles: Squares are managed via a class hierarchy. 
#    A base 'Square' class handles physics and collision, while subclasses 
#    (LevelOneSquare, LevelTwoSquare, LevelThreeSquare) define specific 
#    behaviors like size and speed.
# 3. Dynamic Level Generation: The 'generateLevel' function handles 
#    the vertical spacing and instantiation of squares based on a 'count' parameter.
# 4. UI & Level Progression: The game moves through 3 levels of increasing difficulty, 
#    with the background watermark UI updating dynamically.

# INSTRUCTIONS:
# - To use EEG: Ensure an LSL stream is active, then press 's' in-game to toggle 
#   the stream connection. 
# - To use Keyboard: Hold 'f' to move the ball up.
# - Objective: Gain the most points in throughout 3 levels without hitting the bombs 
# before timer runs out on each level.

# grading shortcuts:
# 1.  the preset input is keyboard, press s to switch to eeg stream input
# 2. press n to skip to the next level, (there are 3 in total), 
# 3. press r once you finish the game to reset

from cmu_graphics import *
from pylsl import StreamInlet, resolve_streams
import random
import json
import ast
#start of ai generated EEG stream implementation code (from line 42 to line 267; gemini is used to generate this code, and i implemented it into my game and cmu graphics

#def band key, def labelsFromInfo,def OpenBandInlet,def connect,def applySample, def isIdle are all exmept code
#The functions mentiond in exempt code are written by AI in order to get the EEG stream working

#resolve_streams: scans local network (WiFi or Bluetooth) for active data streams. 
#Returns a list of every device found

#StreamInlet:creates the connection that allows script to read data

bandOrder = ("theta", "alpha", "betaL", "betaH", "gamma")
#brainwave categories

#configuration constants
initialResolveWait = 12.0
#number of seconds the script will wait at appstart to find a brainwave stream. 
#EEG devices often have a bit of lag when connecting
retryResolveWait = 6.0
# If the initial connection fails, the script becomes slightly more aggressive.
# When it tries again later, it only waits 6 seconds for a response to keep the app 
# from freezing for too long.
connectRetryInterval = 40
# measured in frames (steps). 
# Since the app runs at 60 frames per second, 
# this tells the script to try reconnecting roughly every 0.66 seconds if the connection is lost.

bandSet = frozenset(bandOrder)
#converts list of brainwaves (theta, alpha, etc.) into a unchangable set


def bandKey(labelText):
    # finds bandKey from labelText from stream
    # e.g. "EEG/Alpha": extracts just the word "alpha"

    stripped = (labelText or "").strip()
    if "/" not in stripped:
        return None
    #a stream might send labels formatted like this:EEG/Alpha
    tail = stripped.split("/", 1)[1].strip()
    # tail=the part after the first slash. 
    # If it finds EEG/Alpha, it splits the string to grab Alpha. 
    # If there is no slash, the split("/", 1)[1] command on the next line would crash 
    # the program because there would be no "second part" to grab.
    for name in bandOrder:
        if name.lower() == tail.lower():
            return name  # Found a match, exit the function early   
    return tail

def labelsFromInfo(streamInfo):
    channelsNode = streamInfo.desc().child("channels")
    #LSL (Lab Streaming Layer) streams carry "metadata" (info about the data). 
    #This line looks for a specific section in that metadata called "channels."
    if channelsNode.empty():
        return [str(idx) for idx in range(streamInfo.channel_count())]
    #If that "channels" section is missing entirely, the function doesn't give up. 
    # It uses a List Comprehension to create a list of numbers based on how many 
    # wires are plugged in. If there are 8 wires, it returns ['0', '1', '2', '3', '4', '5', '6', '7'].
    labels, channelNode = [], channelsNode.child("channel")
    for channelIndex in range(streamInfo.channel_count()):
        if channelNode.empty():
            labels.append(str(len(labels)))
        else:
            labelValue = channelNode.child_value("label") or str(len(labels))
            labels.append(labelValue)
        channelNode = channelNode.next_sibling()
    return labels
#The Retrieval LoopLIf the info does exist, the function starts a loop to visit each channel one by one.
#channelNode.child_value("label"): It tries to grab the actual name (e.g., "Alpha").
# or str(len(labels)): This is a clever "OR" trick. If the label is empty or None, 
# it defaults to the current count (the index number).
# channelNode.next_sibling(): This is how you navigate an XML-style tree. 
# It tells Python, "I'm done with Channel 1, now move the pointer to Channel 2."

def openBandedInlet(streamInfo, waitSeconds):
    #checks if the stream found on the network is actually a brainwave stream
    try:
        inlet = StreamInlet(
            streamInfo, max_buflen=360, max_chunklen=0, recover=True
        )
        #This line attempts to open the connection to the EEG stream.
        # max_buflen=360: It keeps 360 seconds (6 minutes) of data in a temporary buffer.
        # recover=True: This is a "Resilience" flag. If the headset briefly disconnects, 
        # the code will try to automatically reconnect without crashing the game.
        infoTimeout = max(10.0, min(waitSeconds, 22.0))
        #The code needs to fetch the names of the channels (using the labelsFromInfo 
        # function we discussed earlier).max/min Logic: This is a "clamping" trick. 
        # It ensures the computer waits at least 10 seconds but no more than 22 seconds for 
        # the stream info. It prevents the game from hanging forever if the headset isn't 
        # sending metadata.
        channelLabels = labelsFromInfo(inlet.info(timeout=infoTimeout))
        #This is the most critical check. Even if a stream is found, 
        #it might be the "wrong" kind of data (like raw electrical signals instead
        #of processed brainwaves).
    except Exception:
        return None
    if not any(bandKey(labelStr) in bandSet for labelStr in channelLabels):
        return None
     # bandKey(labelStr): It takes a channel name (like "Alpha_Power") 
        # and cleans it up.in bandSet: It checks if that name exists in  
        # pre-defined list of important bands (like Alpha, Beta, etc.).
        # any(...):
        #  This checks the whole list. If none of the incoming channels match the 
        # brainwaves your game is looking for, it returns None.
    return inlet, channelLabels
    #If the stream is open and it contains the right brainwave data, 
    #the function returns both the inlet (the data pipe) and
    #the channelLabels (the names of the sensors).

#Summary: Why write it this way?
# This function prevents your takeStep function from trying to process garbage data.
#  It ensures that if the game starts, it has a valid "Banded" (processed) EEG stream ready to go.
# A quick tip for your EEG setup: Since this function returns None if the bands aren't found, 
# you should make sure your EEG software (like Petal, BlueMuse, or OpenBCI GUI) is configured 
# to output "Band Power" specifically, rather than just "Raw" data!


def connect(app, ts=None):
    #the "Handshake" between your code and the outside world.
    #  Its job is to scan the airwaves for EEG signals, filter through them 
    # to find the right one, and then set up the "Memory" (app.avg, app.labels) your game needs to run.
    waitSeconds = float(initialResolveWait if ts is None else ts)
    resolved = resolve_streams(wait_time=waitSeconds)
    #1. The Search Party (resolve_streams)
    #First, it determines how long it should wait for a signal (usually around 10–20 seconds). 
    # resolve_streams is an LSL function that shouts into the local network: 
    # "Is anyone broadcasting data?" It collects every stream it finds into a list called resolved.
    streamsById = {
        (streamInfo.name(), streamInfo.source_id()): streamInfo
        for streamInfo in resolved
    }
    #This is a Dictionary Comprehension. It takes the messy list of streams and organizes them by
    #their name and ID. This prevents the computer from getting confused if there are two headsets
    #in the same room.
    for streamInfo in list(streamsById.values())[:24]:
        pair = openBandedInlet(streamInfo, waitSeconds)
        if pair is None:
            continue
        inlet, channelLabels = pair
        app.inlet = inlet
        app.labels = channelLabels
        app.order = list(bandOrder)
        app.avg = {}
        return
    #The code starts "auditioning" the first 24 streams it found. 
    # It uses your openBandedInlet function (the one we discussed earlier) to check each one.
    # if pair is None: continue: If a stream is just raw noise or doesn't have the Alpha/Beta bands 
    # your game needs, it says "Next!" and moves to the next stream.

# 4. Setting up the Game's Brain (app variables)
# If openBandedInlet actually returns something, the code finally stops searching and populates
#  your app object:
# app.inlet = inlet: This is the open "pipe" that data will flow through.
# app.labels = channelLabels: Saves the sensor names (e.g., "AF7", "TP10").
# app.order = list(bandOrder): Sets the priority for which brainwaves to look at first.
# app.avg = {}: This initializes a dictionary where your takeStep function will eventually 
# store the smoothed-out brain activity numbers.
# 5. The "Early Exit" (return)
# The return at the very end is crucial. It means "As soon as you find ONE good headset, 
# stop looking and start the game." It prevents the code from trying to connect to multiple headsets 
# at once.

# Summary: What is the "Connect" flow?
# Scan: Look for all active LSL streams.
# Sort: Organize them so we can check them one by one.
# Test: Use openBandedInlet to see if the stream has the specific brainwave data we need.
# Assign: If it's a match, save the connection to app and stop searching.

# Tip: If game is stuck on a "Searching for Stream" screen, it usually means this 
# function is looping through the streamsById but every single one is returning None 
# because they aren't formatted as "Banded" data.


def applySample(app, sample):
#This function is the "Processor." It takes a raw slice of data from the EEG 
# (a sample) and turns it into a clean dictionary of averages (app.avg)
    if len(sample) != len(app.labels):
        return
#This ensures the data coming in matches the data we expect. If the EEG sends 8 numbers 
# but we only have 4 labels, the function stops immediately to prevent a crash.
    sumByBand = {band: 0.0 for band in bandOrder}
    countByBand = {band: 0 for band in bandOrder}
#The code creates two empty "ledger" dictionaries. One keeps track of the total energy (sum),
#and the other keeps track of how many sensors contributed to that energy (count).
    for channelLabel, value in zip(app.labels, sample):
        bandName = bandKey(channelLabel)
#zip(app.labels, sample): This pairs each label with its corresponding number 
# (e.g., "Alpha_1" with "12.5").
# bandKey: It cleans the label so it knows that "Alpha_Front" and "Alpha_Back" 
# both belong to the Alpha band.
# The Logic: If it finds an Alpha signal, it adds the value to the Alpha sum 
# and increments the Alpha count.
        if bandName in bandSet:
            sumByBand[bandName] += float(value)
            countByBand[bandName] += 1
    #calculates average for each band
    app.avg = {
        band: sumByBand[band] / countByBand[band]
        if countByBand[band]
        else 0.0
        for band in bandOrder
    }
# his updates the main variable your game uses. It divides the total sum by the number of sensors.
# The if/else: This is a safety check to prevent "Division by Zero" if no data was found for a 
# specific band.
    app.bandsWithSample = frozenset(
    band for band in bandOrder if countByBand[band] > 0
)
    #Finally, it creates a frozenset (an unchangeable list) of only the bands that actually received data.
    #Your isIdle function uses this to know which frequencies are "awake" right now.

#Summary: The Flow
# Verify: Is the data packet the right size?
# Collect: Group all "Alpha" values together, all "Beta" values together, etc.
# Average: Find the middle-ground power for each frequency.
# Publish: Save those averages to app.avg so the player can move.
# Tip: Because this function runs every time a new sample arrives 
# (which can be many times per second), it's very efficient. It effectively
#  "smooths out" the data from multiple sensors so ball movement isn't too jittery!
    
def isIdle(app):
    bands = app.bandsWithSample 
    if not bands:
        return True
    #guard clause. If the EEG headset isn't sending any data (the list is empty),
    # the function assumes the user is "Idle" by default. This prevents the program 
    # from crashing if the stream disconnects.
    return all(
    #a "strict" operator. It only returns True if the test is successful for EVERY single band.
        app.avg[band] <= idleThresholdUv2[band]
        #compares the current average power of that brainwave
        #to a pre-defined "Idle Threshold" (measured in microvolts squared, $uV^2$).
        for band in bands
        #loops through every brainwave range you are tracking 
        # (e.g., first it looks at Alpha, then Beta).
    )
#end of Ai generated code

#Gemini assisted me in writing the inheritence class and collision logic
class Square:
    def __init__(self, cx, cy, size, direction, speed, type):
        self.cx = cx
        self.cy = cy
        self.size = size
        self.direction = direction
        self.speed = speed
        self.type = type # 'bomb', 'pt1', or 'pt2'
        
        if type == 'bomb':
            self.value = -5 
            self.color = None
        elif type == 'pt1':
            self.value = 1
            self.color = 'lightGreen'
        elif type == 'pt2':
            self.value = 2
            self.color = 'gold'

    def move(self, appWidth):
        self.cx += self.speed * self.direction
        if self.cx - self.size/2 > appWidth:
            self.cx = -self.size/2
        elif self.cx + self.size/2 < 0:
            self.cx = appWidth + self.size/2

    def collidesWith(self, ballX, ballY, ballR):
        sLeft, sRight = self.cx - self.size/2, self.cx + self.size/2
        sTop, sBottom = self.cy - self.size/2, self.cy + self.size/2
        return (ballX + ballR > sLeft and ballX - ballR < sRight and
                ballY + ballR > sTop and ballY - ballR < sBottom)

    def draw(self):
        if self.type == 'bomb':
            drawImage('bomb.png', self.cx, self.cy, 
                    width=self.size, height=self.size, align='center')
        else:
            drawRect(self.cx, self.cy, self.size, self.size, 
                    fill=self.color, align='center')
            label = f"+{self.value}"
            drawLabel(label, self.cx, self.cy, fill='black', 
                    bold=True, size=self.size//2)

class LevelOneSquare(Square):
    COUNT=5
    def __init__(self, cx, cy, direction, type):
        super().__init__(cx, cy, 40, direction, 2, type)

class LevelTwoSquare(Square):
    COUNT=10
    def __init__(self, cx, cy, direction, type):
        super().__init__(cx, cy, 30, direction, 5, type)

class LevelThreeSquare(Square):
    COUNT=15
    def __init__(self, cx, cy, direction, type):
        super().__init__(cx, cy, 20, direction, 5, type)
        
# Midpoint cutoffs (µV²): mean ≤ threshold → Idle; above → not Idle.
# I had used data from my previous attention study and got a 60% accuracy 
# rate from using these thresholds to distinguish between idle and non-idle states
idleThresholdUv2 = {
    "theta": 4.521,
    "alpha": 1.354,
    "betaL": 0.877,
    "betaH": 0.542,
    "gamma": 0.409,
}


def onAppStart(app):
    app.stepsPerSecond = 60
    app.searchForStream = False

    #app variables in relation to EEG Stream
    app.inlet = None
    app.labels = []
    app.order = list(bandOrder)
    app.avg = {}
    app.stepCount = 0
    app.bandsWithSample = frozenset()


    #app variables for UI
    app.labelSpace=70

    #app variables for ball
    app.cx=app.width/2
    app.cy=app.height/2
    app.r=20

    #level app variables
    app.gameStarted = False
    app.squares = []
    app.levelTwo = False
    app.levelThree = False
    app.gameWon = False
    app.highScore = 0
    app.score = 0
    app.leaderboard = loadLeaderboard()
    app.gameOver = False
    app.timerSeconds = 30 
    

    app.currentLevelName = "Level 1"
    
    # Start the game with Level One
    generateLevel(app, LevelOneSquare, LevelOneSquare.COUNT)

    #app variables used for alternative keyboard control
    app.fPressed = False

#gemini assited me with writing respawning logic
def generateLevel(app, SquareClass,count):
    topPadding, bottomPadding = 70, app.height - app.labelSpace - 70
    totalRange = bottomPadding - topPadding
    
    for i in range(count):
        if count > 1:
            gaps = max(1, count - 1)
            cy = topPadding + (totalRange / gaps) * i
            cx = (app.width / (count + 1)) * (i + 1)
        else:
            cy = random.randint(topPadding, bottomPadding)
            cx = -20 if random.choice([True, False]) else app.width + 20
        
        direction = random.choice([-1, 1])
        pointsOrBombs = ['pt1', 'pt2', 'bomb'] 
        chosenType = random.choice(pointsOrBombs)
        
        newSquare = SquareClass(cx, cy, direction, chosenType)
        app.squares.append(newSquare)

#gemini assisted with functions leaderboard and save score/getscore logic
def loadLeaderboard():
    try:
        with open('leaderboard.json', 'r') as f:
            data = json.load(f)
            scores = data.get("topScores", [])
            if isinstance(scores, str):
                scores = ast.literal_eval(scores)
            return scores
    except (FileNotFoundError, json.JSONDecodeError):
        return []
#loadLeaderboard(): The Reader
#This function’s job is to safely grab the existing scores from your leaderboard.json file.
# try / except: This is a "safety net." If the file doesn't exist yet (like the first time you play),
# it would normally crash the game. This block catches that error and just returns an empty list []
# instead.

# json.load(f): This converts the text inside the .json file back into a Python dictionary.
# ast.literal_eval(scores): This is an extra safety check. Sometimes JSON data gets saved as a
#  "string that looks like a list." This line ensures it is converted into an actual Python list
#  so you can use .append() on it later.

def saveScore(name,score):
    scores = loadLeaderboard()
    scores.append({"name": name, "score": score})
    scores.sort(key=getScore, reverse=True)
    scores = scores[:100]
    with open('leaderboard.json', 'w') as f:
        json.dump({"topScores": scores}, f)

def getScore(x):
    return x['score']
#saveScore(name, score): The Updater
# This is the "Middleman" that manages the logic of adding a new score.
# Load: It calls loadLeaderboard() to see what the scores currently are.
# Append: It creates a new dictionary {"name": name, "score": score} and pushes it into the list.
# Sort: It uses your getScore helper (and that reverse=True we talked about) to put the 
# biggest numbers at the top.
# Slice ([:100]): This keeps the file from growing forever. It only keeps the 
# top 100 entries and "throws away" the rest.
# Write ('w'): It opens the file in "Write" mode (which wipes the old version) 
# and saves the brand-new, sorted list.

# 3. getScore(x): The Key
# This is a "Helper Function" specifically for the sorting process.
# x: Represents one single entry (a dictionary) from your list.
# return x['score']: It tells the sort() method, "Ignore the player's 
# name for a second and just look at the number inside the 'score' key."


def onKeyPress(app,key):
    if key == 'p' and not app.gameStarted:
        app.gameStarted = True
    if key == 's':
        app.searchForStream = not app.searchForStream
    if app.gameOver and key == 'r':
        onAppStart(app)
    if key == 'n' and app.gameStarted and not app.gameOver:
        app.timerSeconds = 0
        takeStep(app)

def onKeyHold(app,keys):
    if 'f' in keys:
        app.fPressed = True

def onKeyRelease(app,key):
    if key == 'f':
        app.fPressed = False

def onStep(app):
    # --- EEG / Stream Logic, generated by gemini and intergrated by me ---
    app.stepCount += 1
    if app.searchForStream and not app.inlet and (
        app.stepCount == 1 or app.stepCount % connectRetryInterval == 0
    ):
        connect(app, retryResolveWait if app.stepCount > 1 else None)
 #The Problem: Searching for an EEG headset takes a lot of processing power.
 #If the game tried to find a headset 30 times every second, the screen would freeze.
# The Solution: This uses a Modulo (%) check. It only runs the connect function on 
# the very first frame or every connectRetryInterval (global variable set at every 40 steps). 
# This lets the game run smoothly while "quietly" looking for a headset in the background.
    if app.inlet is not None:
        while True:
            sample = app.inlet.pull_sample(timeout=0.0)[0]
            if sample is None: break
            applySample(app, sample)
# #This is the most critical part of handling real-time data.
# The "Buffer" Problem: Your EEG headset sends hundreds of samples per second, 
# but your game only updates 30 times per second. If you only took one sample per frame, 
# the data would "pile up" in a backlog, and your game's brain-control would feel "delayed" 
# by several seconds.
# The while True Solution: This tells the computer: "Quickly drain the entire pipe! 
# Take every single sample that has arrived since the last frame and process it immediately."
# timeout=0.0: This tells the code: "Don't wait for a new sample. If the pipe is empty, just move on."
# applySample(app, sample): This sends the data to your processing function to update the 
# Alpha/Beta averages.

#3. Summary of RolesLine/VariablePurpose
# app.stepCountActs as a timer to manage how often we search for hardware.
# app.searchForStreamA "Master Switch" you can toggle (likely with the 's' key) to turn EEG on/off.
# app.inletThe active connection. If it exists, we are "plugged in."
# pull_sampleReaches out to the LSL stream to grab a piece of brainwave data.

# Why this is "Good" Code:This structure prevents the "Stuttering" effect common in beginner BCI games. 
# By isolating the Connection logic to a timer and using a Drain loop for the data, 
# you ensure that the ball responds to the player's current brain state, not what they were thinking 
# 5 seconds ago.One quick thing to check: In your onStep or takeStep, make sure app.stepCountis actually 
# being incremented! If it stays at 0, the retry logic might not trigger.

    # --- End of AI generated Code ---

    # Call the actual game mechanics
    takeStep(app)

def takeStep(app):
    #gameplay movement, tallying points and collision logic  
    # gemini assisted with level, score, timer logic
    if not app.gameStarted or app.gameOver: 
        return
    
    app.timerSeconds -= 1/60

    for square in app.squares[:]:
        square.move(app.width)
        if square.collidesWith(app.cx, app.cy, app.r):
            app.score += square.value
            app.squares.remove(square)
            if app.levelThree: currentClass = LevelThreeSquare
            elif app.levelTwo: currentClass = LevelTwoSquare
            else: currentClass = LevelOneSquare
            generateLevel(app, currentClass, 1)

    if app.timerSeconds <= 0:
        if not app.levelTwo:
            app.levelTwo = True
            app.currentLevelName = "Level 2"
            app.timerSeconds = 45 
            app.squares = [] 
            generateLevel(app, LevelTwoSquare, LevelTwoSquare.COUNT)
        elif not app.levelThree:
            app.levelThree = True
            app.currentLevelName = "Level 3"
            app.timerSeconds = 60 
            app.squares = []
            generateLevel(app, LevelThreeSquare, LevelThreeSquare.COUNT)
        else:
            if not app.gameOver:
                app.gameOver = True
                userName = app.getTextInput("Enter your name:") or "Anonymous"
                saveScore(userName, app.score)
                app.leaderboard = loadLeaderboard()
    

    #the following is gemini generated code used to detect EEG stream
    app.stepCount += 1
    if app.searchForStream and not app.inlet and (
        app.stepCount == 1 or app.stepCount % connectRetryInterval == 0
    ):
        connect(app, retryResolveWait if app.stepCount > 1 else None)
    if app.inlet is not None:
        while True:
            sample = app.inlet.pull_sample(timeout=0.0)[0]
            if sample is None: break
            applySample(app, sample)
 #This block is the "Connection Engine" of your project.
 #  It’s designed to solve two major problems: preventing the game from freezing
 #  while searching for hardware and ensuring the brain-control doesn't have a "lag" or "delay."

# Here is the breakdown of how the logic works:
# 1. The Throttled Connection (Background Search)
# Searching for an EEG stream (connect) is a "heavy" task for a computer. 
# If you did it every single frame, your frame rate would drop to almost zero.

# app.stepCount % connectRetryInterval == 0: This uses Modulo math. If your interval is 40, 
# it only tries to connect every 40 steps (about once every 1.3 seconds).

# The "First Try" Logic: app.stepCount == 1 ensures that the second you start the game, 
# it makes an immediate attempt to find the headset rather than waiting for the first interval to pass.

# The Switch: if app.searchForStream and not app.inlet ensures that once a connection is found, 
# the computer stops wasting resources looking for one.

# 2. The Data "Drain" (Real-Time Response)
# This while True loop is the most important part of a BCI (Brain-Computer Interface).

# The Backlog Problem: Your EEG headset might send 250 data points per second, 
# but takeStep only runs 30 times per second. If you only took one sample per step,
#  you would quickly fall behind. Within a minute, your ball would be reacting to what you 
# thought 40 seconds ago!

# pull_sample(timeout=0.0): This tells the computer: "Check the 'mailbox.' If there is a letter, 
# take it. If there isn't, don't wait around—just keep moving."

# while True / if sample is None: break: This tells the code to keep "draining the mailbox" 
# until it is completely empty. It processes 10, 20, or even 50 samples in a single frame 
# to make sure the app.avg used to move the ball is based on your current brain state.

# 3. Summary of the Flow
# Count the frame (stepCount).
# Look for a headset ONLY if it's "Search Day" (the interval).
# If Connected, empty the entire data buffer immediately.
# Update the brainwave averages (applySample) so the ball knows whether to move.

# Asynchronous Data Handling. 
# You aren't just taking data; you're managing a high-speed data stream in a way 
# that respects the game's performance.
# Tip: If you want to see this working in real-time, you could add a print
# ("Data Drained!") inside that while loop. You'll see it triggers many times per second
#  whenever the EEG is active!

 

    if app.inlet is not None:
        idle = isIdle(app)
    else:
        idle = not app.fPressed

   #end of ai code 

    if idle: 
        if app.cy + app.r < (app.height - app.labelSpace):
            app.cy += 5
        else:
            app.cy = app.height - app.labelSpace - app.r
    else:
        if app.cy - app.r > 0:
            app.cy -= 5
        else:
            app.cy = app.r
 


def redrawAll(app):
    if not app.gameStarted:
        drawImage('openingUI.png', 0, 0, width=app.width, height=app.height)
    
    else:
        drawLabel("press s to switch to EEG stream",app.width-100,app.height-20,size=12,font='arial')
        drawLabel("press f to move ball up",app.width-100,app.height-40,size=12,font='arial')
        drawLabel(app.currentLevelName, app.width/2, app.height/2, 
                size=60, font='arial', fill='pink', bold=True, opacity=30)
        drawLabel(f"Score: {app.score}", 20, 30, 
                size=20, font='arial', align='left', bold=True, fill='darkCyan')
        displaySeconds = max(0, int(app.timerSeconds))
        mins = displaySeconds // 60
        secs = displaySeconds % 60
        timeText = f"Timer: {mins:02d}:{secs:02d}"
        drawLabel(timeText, app.width/2, 30, size=24, font='arial', bold=True, 
                fill='red' if displaySeconds < 10 else 'black')
        for square in app.squares:
            square.draw()

        if app.gameOver:
            drawRect(app.width - 100, 30, 100,100,fill='white')
            drawLabel("Game Over!", app.width/2, app.height/2 - 40, 
                    size=40, font='arial', fill='red', bold=True)
            drawLabel("Press 'r' to Replay", app.width/2, app.height/2 + 20, 
                    size=20, font='arial', fill='darkGray')
            drawLabel("TOP SCORES", app.width - 20, 30, size=16, align='right', bold=True)
        
            for i in range(len(app.leaderboard)):
                entry = app.leaderboard[i]
                name = entry['name']
                val = entry['score']
                displayText = f"{i+1}. {name}: {val}" 
                drawLabel(displayText, app.width - 20, 55 + (i * 20), 
                        size=14, align='right', font='arial')

        

        drawCircle(app.cx, app.cy, app.r, fill='cyan', border='black')

runApp(1024, 576)
