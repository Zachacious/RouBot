# ROUBOT 
# Author: Zach Moore - Zach@NerdVenture.net

from PIL import ImageGrab, ImageEnhance, ImageFilter, ImageOps
import PIL
import win32api, win32con, win32gui
import pytesseract
import keyboard
from easysettings import EasySettings
import datetime, time, json, os


# ------------- Globals ------------- #

# load the config
config = EasySettings('config.conf')

# true if we have a window handle
windowset = False 

# the windows api hwnd for the game window
activeWin = 0

# true if the bot is ready to start
initdone = False

reds = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]

colorLog = [] # stores previously drawn colors
lastdiff = 0 # the financial gain or loss from the last round
balance = 0
betAmount = 1

startTime = datetime.datetime.now()
maxbet = 1 # for keeping track of the maximum bet that has been placed for the session

startBalance = 0

streakThresh = 2 # the threshold for what is considered a streak -- ex: 2 reds in a row

# these are configured to hold the coords of the important places on the game board that
#the bot will use to read data and  play the game
spinBtnCoords = []
clearBtnCoords = []
redCoords = []
blackCoords = []
numblock = ()
balanceBlock = ()

# ------------- Windows Api ------------- #

def leftClick():
    ''' Simulate a mouse click '''
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
    time.sleep(.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)
    
def mousePos(coord):
    ''' move the mouse '''
    x,y = win32gui.ClientToScreen(activeWin, (coord[0], coord[1]))
    win32api.SetCursorPos((x, y))
     
def get_coords(e):
    ''' get the client coords '''
    x,y = win32api.GetCursorPos()
    x,y = win32gui.ScreenToClient(activeWin, (x, y))
    print (x,y)
    return x,y
  
# ------------- Functions to read data from the screen with PIL and Tesseract-OCR ------------- #

def sreenGrab(box):
    ''' grab a screenshot of the game - box is the area of the screen to capture '''
    global activeWin
    x1, y1 = win32gui.ClientToScreen(activeWin, (box[0], box[1]))
    x2, y2 = win32gui.ClientToScreen(activeWin, (box[2], box[3]))
    img = ImageGrab.grab((x1, y1, x2, y2)) 
    
    # These image manipulations are required to help tesseract read the data properly
    img = img.convert('L') # greyscale
    img = img.resize((img.size[0]*3, img.size[1]*3), 1)
    img = ImageEnhance.Contrast(img).enhance(5.0)
    img = ImageOps.equalize(img)
    img = ImageOps.invert(img)
    return img


def getNumber(e):
    ''' capture the last drawn number and convert it into a python int 
        some numbers require all 3 steps to get a readable number '''
    try:
        img = sreenGrab(numblock)
        img = img.filter(ImageFilter.MaxFilter(5))
        # img.save(os.getcwd() + '\\full_snap__' + str(int(time.time())) + '.png', 'PNG') # for debugging
        numStr = pytesseract.image_to_string(img, lang='eng', config='--psm 10 --oem 3 digits')
        print(numStr)
        return int(numStr)
    except:
        try:
            img = sreenGrab(numblock)
            img = img.filter(ImageFilter.MaxFilter(3))
            # img.save(os.getcwd() + '\\full_snap__' + str(int(time.time())) + '.png', 'PNG') # for debugging
            numStr = pytesseract.image_to_string(img, lang='eng', config='--psm 10 --oem 3 digits')
            print(numStr)
            return int(numStr)
        except:
            try:
                img = sreenGrab(numblock)
                img = img.filter(ImageFilter.MinFilter(1))
                # img.save(os.getcwd() + '\\full_snap__' + str(int(time.time())) + '.png', 'PNG') # for debugging
                numStr = pytesseract.image_to_string(img, lang='eng', config='--psm 10 --oem 3 digits')
                print(numStr)
                return int(numStr)
            except:
                return 0
        
    

def getBalance(e):
    ''' captures the balance and converts it into a Python float '''
    img = sreenGrab(balanceBlock)
    try:
        img = img.filter(ImageFilter.MaxFilter(5))
        # img.save(os.getcwd() + '\\full_snap__' + str(int(time.time())) + '.png', 'PNG') # for debugging
        numStr = pytesseract.image_to_string(img, lang='eng', config='--psm 10 --oem 3 digits')
        return float(numStr)
    except:
        # img.save(os.getcwd() + '\\full_snap__' + str(int(time.time())) + '.png', 'PNG') # for debugging
        numStr = pytesseract.image_to_string(img, lang='eng', config='--psm 10 --oem 3 digits')
        
        # handle edge case where multiple 1's read for instance 1,001.00 --> 1.001.00
        numparts = list(numStr) # each character in a list
        if len(numparts) > 6: # large enough number to matter
            del numparts[-7] # remove comma that is a dot
            numStr = ''.join(numparts) # recreate string
            
        return float(numStr)
    
# ------------- Functions used by the bot to place bets, hit buttons, and play the game ------------- #

def getLastDrawnColor(e):
    ''' returns the color of the last drawn number '''
    num = getNumber(e)
    if num == 0:
        return 'green'
    elif num in reds:
        return 'red'
    else:
        return 'black'
    
def getOppCol(col):
    ''' returns the opposite of the last drawn number '''
    if col == 'red':
        return 'black'
    return 'red'
    
def getStreak(e):
    ''' determine whether or not a streak is occuring or has just previously '''
    global streakThresh
    if len(colorLog) < streakThresh: # not enough data to determine if a streak has occured
        return False, False
    last5 = colorLog[-streakThresh:]
    prev5 = colorLog[-(streakThresh + 1):-1]
    # returns (is on a streak), (just had a streak)
    return (len(set(last5)) <= 1), (len(set(prev5)) <= 1)
    
    
def spin(e):
    ''' hit the spin button '''
    mousePos(spinBtnCoords)
    leftClick()
    
def clear(e):
    ''' hit the clear button '''
    mousePos(clearBtnCoords)
    leftClick()
    
def betRed(e):
    ''' bets red '''
    mousePos(redCoords)
    leftClick()
    
def betBlack(e):
    ''' bets black '''
    mousePos(blackCoords)
    leftClick()
    
def placeBets(col):
    ''' places (betAmount) of bets on the given color '''
    if col == 'red':
        for i in range(0, betAmount):
            betRed(0)
    else:
        for i in range(0, betAmount):
            betBlack(0)
            

# ------------- Functions for initializing ------------- #

def setWindow():
    ''' allow the user to select the game window '''
    global windowset
    global activeWin
    print('click the game window and press enter')
    keyboard.wait('Enter')
    hwnd = win32gui.GetForegroundWindow()
    activeWin = hwnd
    win32gui.MoveWindow(hwnd, 0, 0, 1920, 1080, True)
    windowset = True
    # exit()


def stopGame(e):
    ''' end the game '''
    quit()
    

def init():
    ''' make sure the game window is set,
    gives the user a chance to configure the game,
    bring the game window forward and sets the inital balance var '''
    global startBalance
    global initdone
    global spinBtnCoords
    global clearBtnCoords
    global redCoords
    global blackCoords
    global numblock
    global balanceBlock
    global config
    
    if initdone:
        return
    
    if not windowset:
        setWindow()
    
    # load in an existing config
    if config.has_option('spinBtnCoords'):
        spinBtnCoords = config.get('spinBtnCoords')
        clearBtnCoords = config.get('clearBtnCoords')
        redCoords = config.get('redCoords')
        blackCoords = config.get('blackCoords')
        numblock = config.get('numblock')
        balanceBlock = config.get('balanceBlock')
        
    doConfig = input('Would you like to configure? [y, n]')
    if doConfig == 'y':
        configure(0)
        
    # brings the window forward - TODO should be it's own function
    win32gui.BringWindowToTop(activeWin)
    win32gui.ShowWindow(activeWin, 3) # force maximize    
    win32gui.SetForegroundWindow(activeWin)
    win32gui.SetActiveWindow(activeWin)
    
    startBalance = getBalance(0)
    initdone = True
        
    
def configure(e):
    ''' walks the user through capturing the positions and bounding boxes of each
    of the relavent areas on the game screen - then saves them in a config file '''
    global spinBtnCoords
    global clearBtnCoords
    global redCoords
    global blackCoords
    global numblock
    global balanceBlock
    global config
    
    print('move mouse over left top corner of balance area and press enter')
    balancebox = []
    keyboard.wait('enter')
    x,y = get_coords(0)
    balancebox.append(x) 
    balancebox.append(y) 
    
    print('move mouse over bottom right corner of balance area and press enter')
    keyboard.wait('enter')
    x,y = get_coords(0)
    balancebox.append(x) 
    balancebox.append(y) 
    
    print('move mouse over left top corner of number area and press enter')
    numbox = []
    keyboard.wait('enter')
    x,y = get_coords(0)
    numbox.append(x) 
    numbox.append(y) 
    
    print('move mouse over bottom right corner of number area and press enter')
    keyboard.wait('enter')
    x,y = get_coords(0)
    numbox.append(x) 
    numbox.append(y) 
    
    print('move mouse over the spin button and press enter')
    keyboard.wait('enter')
    spinarea = get_coords(e)
    
    print('move mouse over the clear button and press enter')
    keyboard.wait('enter')
    cleararea = get_coords(e)
    
    print('move mouse over the red area and press enter')
    keyboard.wait('enter')
    redarea = get_coords(e)
    
    print('move mouse over the black area and press enter')
    keyboard.wait('enter')
    blackarea = get_coords(e)
    
    spinBtnCoords = spinarea
    clearBtnCoords = cleararea
    redCoords = redarea
    blackCoords = blackarea
    numblock = tuple(numbox)
    balanceBlock = tuple(balancebox)
    
    # save the new config
    config.set('spinBtnCoords', spinBtnCoords)
    config.set('clearBtnCoords', clearBtnCoords)
    config.set('redCoords', redCoords)
    config.set('blackCoords', blackCoords)
    config.set('numblock', numblock)
    config.set('balanceBlock', balanceBlock)
    config.save()    

 # ------------- Functions for playing the game ------------- #
 # TODO: it'd be nice to abstract the actual strategy in some way so that
 # multiple strategies could be play in one session or based on certain
 # conditions

def playGame(e):
    ''' called each loop to analyze the numbers and balance - then make bets and spin '''
    global windowset
    global lastdiff
    global balance
    global strategyIndex
    global strategy
    global betAmount
    global maxbet
    global startTime
    
    print('Started: ' + str(startTime))
    profit = getBalance(0) - startBalance
    print('Session Profit: $' + str(profit))
    print('max bet amount: ' + str(maxbet))
    
        
    clear(0)
    time.sleep(2) # TODO: need a way to know when it's time to clear rather than depending on timing
        
    # the net gain or loss from the last round
    lastdiff = getBalance(0) - balance
    
    balance = getBalance(0)
    print('Balance: $' + str(balance))
    
    # log num color
    colorLog.append(getLastDrawnColor(0))
    
    # if we took a loss last round, double the bet amount:
    if lastdiff < 0:
        betAmount *= 2
    else:
        betAmount = 1
    
    # check if betamount is greater than max bet and set
    if betAmount > maxbet:
        maxbet = betAmount # keep track of the maximum bet for the session
        
    # place bets
    # if streak - chase the streak - bet same color as last drawn
    if getStreak(0):
        print('STREAK')
        placeBets(getLastDrawnColor(0))
        time.sleep(1)
    else: # not on a streak
        placeBets(getOppCol(getLastDrawnColor(0))) # bet opposite
        time.sleep(1)
        
    # spin
    spin(0)
    print('Round complete \n\n')
    
    
 # ------------- Keyboard hooks for convinence and debugging ------------- #
keyboard.on_press_key('a', get_coords)  
keyboard.on_press_key('q', playGame) 
keyboard.on_press_key('w', stopGame)
keyboard.on_press_key('c', configure) 

def main():
    init()
    while 1:
        playGame(0) # comment out to use keyboard hooks for debugging
        time.sleep(13) # sleep to give the game time to be ready to accept a hit on the clear button 
 
if __name__ == '__main__':
    main()