import json
import requests
import time
from pathlib import Path
from PilotClasses import Pilot, Round
import re
import shutil
import secret
import obsws_python as obs
# from  Websocket_MyRCM import *
from OBSAutomate import OBS_Auto
import pandas as pd
import generateHTML
from html2image import Html2Image
from ImgGenerator import *

def htmlToPng(html_string=None, html_file=None, css_file="Style.css", FilePath=None, size=(1300,1280)):
    try:
        hti = Html2Image(size=size, output_path=Path(FilePath).parent.as_posix(), disable_logging=True, browser="Edge")

        if html_string is not None:
            hti.screenshot(html_str=html_string, css_file=css_file, save_as=Path(FilePath).name)   
    except Exception as e:
        print(f"Failed to convert HTML to PNG: {e}")

LocalOnly = True
generateHTML_PNG = True
UseWebSocket = False
AutomateOBS = False
enableSevenSegDisplay = False

ReloadDataframe = False

if AutomateOBS:
    OBS = OBS_Auto(IP = 'localhost', Port=4455, PassWord=secret.OBSWebSocketPW, verbose=True, debug=True)
    

PublisherServer_IP = "192.168.1.136"
LiveBasePath = Path("C:/RCPARK_Live/Live Course 12/")
# LiveBasePath = Path("/Volumes/charlesmerlen/Sites/RC")
GdriveBasePath = Path("G:/Mon Drive/Affiches-Graphisme/Course/Course 12 - Sept 2024/YT LIVE")
# GdriveBasePath = Path("/Users/charlesmerlen/Library/CloudStorage/GoogleDrive-rcpark59193@gmail.com/Mon Drive/Affiches-Graphisme/Course/Course 12 - Sept 2024/YT LIVE")
LiveBasePath.mkdir(parents=True, exist_ok=True)

jsonFilePath =      Path(LiveBasePath, "Ranking.json")
htmlFilePath =      Path(LiveBasePath, "Ranking.html")
htmlTableFilePath = Path(LiveBasePath, "Table.html")
roundFilePath =     Path(LiveBasePath, "Round.txt")
raceTimeFilePath =  Path(LiveBasePath, "temps.txt")
TeamLogoPath =      Path(LiveBasePath, "LogoTeam")
RankingImagePath =  Path(LiveBasePath, "Ranking.png")
# RankingImagePath =  Path("Ranking.png")

shutil.copyfile("Tableau.css", Path(LiveBasePath, 'Tableau.css'))
shutil.copyfile("style.css", Path(LiveBasePath, 'style.css'))
shutil.copyfile("clock.html", Path(LiveBasePath, 'clock.html'))

if enableSevenSegDisplay:
    from displayDriver import Display
    disp = Display(numberOfLines=3, Port="/dev/ttyS0")

index = 0
with open("jsontemplate.txt", 'r', encoding="utf-8") as timefile:
    InputTestFile = timefile.readlines()
response = InputTestFile[0]
Tstart = time.time()

newRound = False
PreviousGroup = None
while (True):

    if Tstart + 5 < time.time():
        Tstart = time.time()
        index +=1
        try:
            response = InputTestFile[index]
        except IndexError:
            index = 0


    if AutomateOBS:
        OBS.updateScene()

    try:
        if not LocalOnly:
            if UseWebSocket:
                response = get_websocket_response()
            else:
                response = requests.get(f"http://{PublisherServer_IP}/1/StreamingData").text
            #print(response)
        js = json.loads(response)
    except ConnectionError:
        print("Cannot reach publisher server")
        continue

    # Check if we entered a new round to create new pilot list
    currentGroup = js['EVENT']['METADATA']['SECTION']+js['EVENT']['METADATA']['GROUP']

    if PreviousGroup != currentGroup:
        PreviousGroup = currentGroup
        currentRound = Round(**js['EVENT'])
        if ReloadDataframe:
            currentRound.ReloadDataFramesFromFile(LiveBasePath)
        newRound = True
        generateMainRankingImage(currentRound, backgroundImagePath=Path(GdriveBasePath,"ScreenStartLine-CMN.png"), buggyImagePath=Path(GdriveBasePath,"Buggy.png"), outputPath=Path(LiveBasePath, "MainRanking.png"))
        generateStartGridImage(currentRound, outputPath=Path(LiveBasePath, "StartGrid.png"))
        try:
            shutil.copyfile(Path(LiveBasePath,currentRound.picPath), Path(LiveBasePath, 'seriePic.JPG'))
            shutil.copyfile(Path(LiveBasePath,currentRound.bannerPath), Path(LiveBasePath, 'banner.JPG'))
        except:
            print("Cannot find the requested picture. Serie picture not updated.")
    else:
        newRound = False
        currentRound.update(**js['EVENT'])

    #add regular dataframeSave
    autoSaveDF=False
    if autoSaveDF:
        for pilot in currentRound.NewLap:
            currentRound.PilotDataFrameDict[pilot].to_csv(Path(LiveBasePath, pilot+".csv"))
        currentRound.NewLap = []

    # Gestion du TEMPS Restant
    RaceTime = currentRound.getRaceTime_pretty()
    print(f"RaceTime = {RaceTime}")
 
    
    pilotes = []
    
    rankingHtmlBody = generateHTML.getHeaderRanking(RaceTime, showBestLap=False)
    statTabHtmlBody = generateHTML.getHeaderStatTable(RaceTime)

    for pilot in currentRound.pilotList:
        rankingHtmlBody += generateHTML.getPilotRanking(pilot, showBestLap=False)
        statTabHtmlBody += generateHTML.getPilotStatTable(pilot, TeamLogoPath)
    
    rankingHtmlBody += '</tbody></table></body>'
    rankingHtmlBody += '</html>'

    try:
        #Save round file
        with open(roundFilePath, 'w',encoding='utf-8') as file:
            file.write(currentRound.round_pretty)
        
        #Save time file
        with open(raceTimeFilePath, 'w',encoding='utf-8') as file:
            file.write(RaceTime)

        #Save HTML file
        with open(htmlFilePath,'w', encoding='utf-8') as file: 
            file.write(rankingHtmlBody)

        if generateHTML_PNG:
            htmlToPng(html_string=rankingHtmlBody, css_file="Style.css", FilePath=RankingImagePath, size=(416,500))

        #Save HTML file
        with open(htmlTableFilePath,'w', encoding='utf-8') as file: 
            file.write(statTabHtmlBody)

    except FileNotFoundError:
        print("Problem writing files.\n{e}")
    except PermissionError as e:
        print(f"Permission error while writing files.\n{e}")

    time.sleep(5)