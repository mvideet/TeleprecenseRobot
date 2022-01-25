import numpy as np
from Tkinter import *
import tk as tk
import ts as ts

import struct
import sys, glob # for listing serial ports

try:
    import serial
except ImportError:
    tk.showerror('Import error', 'Please install required libraries.')
    raise

connection = None

TEXTWIDTH = 40 # window width, in characters
TEXTHEIGHT = 16 # window height, in lines

VELOCITYCHANGE = 150
ROTATIONCHANGE = 100

helpText = """\
Supported Keys:
E\tPassive
Q\tSafe
F\tFull
C\tClean
G\tDock
R\tReset
Space\tBeep
WASD\tMotion


"""

class TetheredDriveApp(Tk):
   
    callbackKeyUp = False
    callbackKeyDown = False
    callbackKeyLeft = False
    callbackKeyRight = False
    callbackKeyLastDriveCommand = ''

    def __init__(user):
        Tk.__init__(user)
        user.title("Teleprecense Robot")
        user.option_add('*tearOff', FALSE)

        user.menubar = Menu()
        user.configure(menu=user.menubar)

        menu = Menu(user.menubar, tearoff=False)
        user.menubar.add_cascade(label="Options", menu=menu)

        menu.add_command(label="Connect", command=user.onConnect)
        menu.add_command(label="Keybinds", command=user.onHelp)
        menu.add_command(label="Exit", command=user.onQuit)

        user.text = Text(user, height = TEXTHEIGHT, width = TEXTWIDTH, wrap = WORD)
        user.scroll = Scrollbar(user, command=user.text.yview)
        user.text.configure(yscrollcommand=user.scroll.set)
        user.text.pack(side=LEFT, fill=BOTH, expand=True)
        user.scroll.pack(side=RIGHT, fill=Y)

        user.text.insert(END, helpText)

        user.bind("<Key>", user.callbackKey)
        user.bind("<KeyRelease>", user.callbackKey)


    def sendCommandASCII(user, command):
        cmd = ""
        for v in command.split():
            cmd += chr(int(v))

        user.sendCommandRaw(cmd)

    
    def sendCommandRaw(user, command):
        global connection

        try:
            if connection is not None:
                connection.write(command)
            else:
                tk.showerror('Not connected!', 'Not connected to a robot!')
                print ("Not connected.")
        except serial.SerialException:
            print ("No connection")
            tk.showinfo("Connection Lost")
            connection = None

        print( ' '.join([ str(ord(c)) for c in command ]))
        user.text.insert(END, ' '.join([ str(ord(c)) for c in command ]))
        user.text.insert(END, '\n')
        user.text.see(END)

    
    def getDecodedBytes(user, n, fmt):
        global connection
        
        try:
            return struct.unpack(fmt, connection.read(n))[0]
        except serial.SerialException:
            print( "No connection")
            tk.showinfo("No connection")
            connection = None
            return None
        except struct.error:
            print ("Reconnect")
            return None

    # get8Unsigned returns an 8-bit unsigned value.
    def get8Unsigned(user):
        return getDecodedBytes(1, "B")

    # get8Signed returns an 8-bit signed value.
    def get8Signed(user):
        return getDecodedBytes(1, "b")

    # get16Unsigned returns a 16-bit unsigned value.
    def get16Unsigned(user):
        return getDecodedBytes(2, ">H")

    # get16Signed returns a 16-bit signed value.
    def get16Signed(user):
        return getDecodedBytes(2, ">h")

    # A handler for keyboard events. Feel free to add more!
    def callbackKey(user, event):
        k = event.keysym.upper()
        delta = False

        if event.type == '2': # KeyPress; need to figure out how to get constant
            if k == 'E':   # Passive
                user.sendCommandASCII('128')
            elif k == 'Q': # Safe
                user.sendCommandASCII('131')
            elif k == 'F': # Full
                user.sendCommandASCII('132')
            elif k == 'C': # Clean
                user.sendCommandASCII('135')
            elif k == 'G': # Dock
                user.sendCommandASCII('143')
            elif k == 'SPACE': # Beep
                user.sendCommandASCII('140 3 1 64 16 141 3')
            elif k == 'R': # Reset
                user.sendCommandASCII('7')
            elif k == 'W':
                user.callbackKeyUp = True
                delta = True
            elif k == 'S':
                user.callbackKeyDown = True
                delta = True
            elif k == 'A':
                user.callbackKeyLeft = True
                delta = True
            elif k == 'D':
                user.callbackKeyRight = True
                delta = True
            else:
                print (repr(k))
        elif event.type == '3': # KeyRelease; need to figure out how to get constant
            if k == 'W':
                user.callbackKeyUp = False
                delta = True
            elif k == 'S':
                user.callbackKeyDown = False
                delta = True
            elif k == 'A':
                user.callbackKeyLeft = False
                delta = True
            elif k == 'D':
                user.callbackKeyRight = False
                delta = True
            
        if delta == True:
            velocity = 0
            velocity += VELOCITYCHANGE if user.callbackKeyUp is True else 0
            velocity -= VELOCITYCHANGE if user.callbackKeyDown is True else 0
            rotation = 0
            rotation += ROTATIONCHANGE if user.callbackKeyLeft is True else 0
            rotation -= ROTATIONCHANGE if user.callbackKeyRight is True else 0

            # compute left and right wheel velocities
            vr = velocity + (rotation/2)
            vl = velocity - (rotation/2)

            # create drive command
            cmd = struct.pack(">Bhh", 145, vr, vl)
            if cmd != user.callbackKeyLastDriveCommand:
                user.sendCommandRaw(cmd)
                user.callbackKeyLastDriveCommand = cmd

    def onConnect(user):
        global connection

        try:
            ports = user.getSerialPorts()
            port = ts.askstring('Port?', 'Enter COM port to open.\nAvailable options:\n' + '\n'.join(ports))
        except EnvironmentError:
            port = ts.askstring('Port?', 'Enter COM port to open.')

        if port is not None:
            print ("Connecting to " + str(port))
            try:
                connection = serial.Serial(port, baudrate=115200, timeout=1)
                print ("You can start driving!")
                tk.showinfo( "Connection succeeded!")
            except:
                print( "Retry.")
                tk.showinfo('Failed', "Sorry, couldn't connect to " + str(port))


    def onHelp(user):
        tk.showinfo('Help', helpText)

    def onQuit(user):
        if tk.askyesno('Please confirm that you want to quit.'):
            user.destroy()

    def getSerialPorts(user):
        
        if sys.platform.startswith('win'):
            ports = ['COM' + str(i + 1) for i in range(256)]


        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result    

if __name__ == "__main__":
    app = TetheredDriveApp()
    app.mainloop()
