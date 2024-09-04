import re
import serial
import json

class DisplayLine:
    def __init__(self, id:int, size=11, pattern="\d{2}[-.']\d{2}[-.']\d{2}[-.']\d{4}") -> None:
        self.pattern = re.compile(pattern)
        self.displaySize = size
        self.event = "r"
        try:
            self._value = self.checkFormat("00-00.00-0000")
        except ValueError as e:
            print(e)
            self._value = None

    def checkFormat(self, string):
        if (self.pattern.match(string) is not None) and (len(string) == self.displaySize):
            return string
        raise ValueError('Value is not compatible with display format')
        
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, string):
        try:
            self._value = self.checkFormat(string)
        except ValueError as e:
            print(e)

class color:
    def __init__(self, r, g, b) -> None:
        self.r = r
        self.g = g
        self.b = b

class Display:
    def __init__(self, numberOfLines:int, Port=None, TextColor=color(1,0,0)) -> None:
        self.numberOfLines = numberOfLines
        self.Port = Port
        try:
            self.serial = serial.Serial(self.Port, 115200)
        except FileNotFoundError:
            print("Cannot open serial connection")
            self.serial = None
        
        self.TextColor = TextColor
        self.content = [DisplayLine(lineID, size=13) for lineID in range(numberOfLines)]
    
    def setLines(self, stringList:list):
        for i in range(self.numberOfLines):
            self.content[i].value, self.content[i].event = stringList[i]

    def updateDisplay(self):
        if self.serial is None or not self.serial.is_open:
            raise ConnectionError("Display is not connected.")
        elif all(l.value is not None for l in self.content):
            self.serial.flush()
            for i,line in enumerate(self.content):
                data = ''
                data += str(json.dumps({"line":i, "content":line.value, "event":line.event}))
                data = bytearray(data+'\n', encoding='ascii')
                print(f"sending ==> {data}")
                self.serial.write(data)
        else:
            print("Invalid data, display not udpated.")
        
