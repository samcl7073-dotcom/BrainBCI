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
#start of ai generated EEG stream implementation code (from line 3 to line 130); gemini is used to generate this code, and i implemented it into my game and cmu graphics

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
    if channelsNode.empty():
        return [str(idx) for idx in range(streamInfo.channel_count())]
    labels, channelNode = [], channelsNode.child("channel")
    for channelIndex in range(streamInfo.channel_count()):
        if channelNode.empty():
            labels.append(str(len(labels)))
        else:
            labelValue = channelNode.child_value("label") or str(len(labels))
            labels.append(labelValue)
        channelNode = channelNode.next_sibling()
    return labels


def openBandedInlet(streamInfo, waitSeconds):
    #The Handshake
    #checks if the stream found on the network is actually a brainwave stream
    try:
        inlet = StreamInlet(
            streamInfo, max_buflen=360, max_chunklen=0, recover=True
        )
        infoTimeout = max(10.0, min(waitSeconds, 22.0))
        channelLabels = labelsFromInfo(inlet.info(timeout=infoTimeout))
    except Exception:
        return None
    if not any(bandKey(labelStr) in bandSet for labelStr in channelLabels):
        return None
    return inlet, channelLabels


def connect(app, ts=None):
    #
    waitSeconds = float(initialResolveWait if ts is None else ts)
    resolved = resolve_streams(wait_time=waitSeconds)
    streamsById = {
        (streamInfo.name(), streamInfo.source_id()): streamInfo
        for streamInfo in resolved
    }
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


def applySample(app, sample):
    if len(sample) != len(app.labels):
        return
    sumByBand = {band: 0.0 for band in bandOrder}
    countByBand = {band: 0 for band in bandOrder}
    for channelLabel, value in zip(app.labels, sample):
        bandName = bandKey(channelLabel)
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
    app.bandsWithSample = frozenset(
    band for band in bandOrder if countByBand[band] > 0
)
def isIdle(app):
    bands = app.bandsWithSample 
    if not bands:
        return True
    return all(
        app.avg[band] <= idleThresholdUv2[band]
        for band in bands
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
            self.color = 'black'
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
        fillColor = None if self.type == 'bomb' else self.color
        borderLevel = None if self.type == 'bomb' else 'black'
        drawRect(self.cx, self.cy, self.size, self.size, 
             border=borderLevel, fill=fillColor, align='center')
        if self.type == 'bomb':
            drawImage('bomb.png', self.cx, self.cy, 
                    width=self.size, height=self.size, align='center')
        else:
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

#gemini assited me partially with writing respawning logic
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
        pointsOrBombs = ['pt1', 'pt1', 'pt2', 'bomb'] 
        chosenType = random.choice(pointsOrBombs)
        
        newSquare = SquareClass(cx, cy, direction, chosenType)
        app.squares.append(newSquare)

#gemini assisted with leaderboard and save score logic
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

def saveScore(name,score):
    scores = loadLeaderboard()
    scores.append({"name": name, "score": score})
    scores.sort(key=lambda x: x['score'], reverse=True)
    scores = scores[:100]
    with open('leaderboard.json', 'w') as f:
        json.dump({"topScores": scores}, f)


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
    
    if app.inlet is not None:
        while True:
            sample = app.inlet.pull_sample(timeout=0.0)[0]
            if sample is None: break
            applySample(app, sample)
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

    if app.inlet is not None:
        idle = isIdle(app)
    else:
        idle = not app.fPressed
    
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
    #end of ai code


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
