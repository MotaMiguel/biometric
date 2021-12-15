import tkinter
from tkinter import messagebox
import cv2
from PIL import Image,ImageTk
import time 
import face_recognition
import threading
import pymongo
import logging
import time
import busio
from digitalio import DigitalInOut, Direction
import adafruit_fingerprint

import serial
logging.basicConfig(level=logging.DEBUG)

class Application:
    def __init__(self,window,window_title,video_source=0):
            self.window = window
            self.window.title(window_title)
            self.video_source = video_source
            self.video = VideoCapture(0)
            # Generate the frame layout
            self.leftFrame = tkinter.Frame(window)
            self.leftFrame.pack(side=tkinter.LEFT)
            self.rightFrame = tkinter.Frame(window)
            self.rightFrame.pack(side=tkinter.RIGHT)
            self.rightBottomFrame = tkinter.Frame(self.rightFrame)
            self.rightBottomFrame.pack(side=tkinter.BOTTOM)
            self.rightUpperFrame = tkinter.Frame(self.rightFrame)
            self.rightUpperFrame.pack(side=tkinter.TOP)
            # Add Video Canva
            self.canvas = tkinter.Canvas(self.leftFrame,width=self.video.width,height=self.video.height)
            self.canvas.pack()
             # Add Username Textbox
            self.usernameLabel = tkinter.Label(self.rightUpperFrame,text="Enter your companyID")
            self.usernameLabel.pack()
            self.companyID = tkinter.Entry(self.rightUpperFrame)
            self.companyID.focus_set()
            self.companyID.pack()
            # Database
            self.mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
            # Fingerprint reader
            self.uart = serial.Serial("/dev/ttyUSB0", baudrate=57600, timeout=1)
            self.finger = adafruit_fingerprint.Adafruit_Fingerprint(self.uart)
            # Add Register Bottom Canva
            self.btn_snapshot = tkinter.Button(self.rightBottomFrame,
                                               text="Start user registration",
                                               width=30,height=30,
                                               command = lambda: UserRegistration(frames=10,
                                                                              duration=10,
                                                                              video=self.video,
                                                                              database=self.mongoclient,
                                                                              companyID=self.companyID.get(),
                                                                              finger=self.finger,
                                                                              application=self).start())
            self.btn_snapshot.pack(expand=True)
            # Variables
            self.delay = 1
            self.listOfImages = {}
            self.currentImage = None
            self.timeForCurrentImage = 0
            self.continue_update = True
            self.update()
            self.window.mainloop()
            
    def update(self):
        if self.continue_update:
            if int(time.time())>self.timeForCurrentImage:
                ret, frame = self.video.get_frame()
                if ret:
                    self.photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
                    self.canvas.create_image(0,0,image=self.photo,anchor=tkinter.NW)
            else:
                self.canvas.create_image(0,0,image=self.currentImage,anchor=tkinter.NW)
        self.window.after(self.delay,self.update)
        
    
class VideoCapture:
    def __init__(self,video_source=0):
        self.video = cv2.VideoCapture(video_source)
        if not (self.video.isOpened()):
            raise ValueError("Unable to open video source",video_source)
        self.width = self.video.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.video.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
    def __del__(self):
        if self.video.isOpened():
            self.video.release()
                
    def get_frame(self):
        if self.video.isOpened():
            ret,frame = self.video.read()
            if ret:
                return (ret,cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
            else:
                return (ret,None) 

class UserRegistration(threading.Thread):
    def __init__(self,frames,duration,video,database,companyID,finger,application):
        super().__init__()
        self.duration = duration
        self.frames = frames
        self.video = video
        self.database = database
        self.companyID = companyID
        self.finger = finger
        self.fingerprint_text = None
        self.parent_application = application
        self.fingerprint_canva = None
        
    def run(self):
        '''
        Start Face Registration
        '''
        if self.companyID!="":
            #self.face_registration()
            self.reset_widgets()
            self.fingerprint_registration()
        else:
            messagebox.showerror(title="Error",message="CompanyID field must be filled")
    
    def face_registration(self):
        frames_counter = 0
        logging.info(f"Starting face retrieval for user with companyID: {self.companyID}")
        # Initialize user dictionary
        user_dict = {"companyID":self.companyID,"face_encodings":[]}
        while frames_counter<self.frames:
            ret, frame = self.video.get_frame() 
            # Mongodb "biometrics" database   
            database = self.database["biometrics"]
            # Mongodb "user" collection inside "biometrics" database
            face_collection = database["faces"]
            face_location = face_recognition.face_locations(frame)
            face_encoding = face_recognition.face_encodings(frame,face_location)
            # If no face was recognized
            if len(face_encoding) > 0:
                # Insert into list of face encodings
                # the return from the facerecognition lib comes in a list of numpy arrays
                user_dict["face_encodings"].append(list(face_encoding[0]))
                logging.info(f"Face encoding for user with companyID {self.companyID} added to list")
                frames_counter += 1
                # Tell thread to sleep to distribute the frames along the duration
                time.sleep(self.duration/self.frames)
        # Insert into collection after all frames have been captured
        face_collection.insert_one(user_dict)
    
    def fingerprint_registration(self,location=1):
        fingerprint_obtained = False
        while not fingerprint_obtained:
            """Take a 2 finger images and template it, then store in 'location'"""
            for finger_img in range(1, 3):
                if finger_img == 1:
                    self.setup_fingerprint_canva()
                else:
                    self.update_fingerprint_canva(text="Please set same finger once again.")

                while True:
                    i = self.finger.get_image()
                    if i == adafruit_fingerprint.OK:
                        logging.debug("Image taken")
                        break
                    if i == adafruit_fingerprint.NOFINGER:
                        logging.debug(".", end="", flush=True)
                    elif i == adafruit_fingerprint.IMAGEFAIL:
                        logging.debug("Imaging error")
                        return False
                    else:
                        logging.debug("Other error")
                        return False

                logging.debug("Templating...", end="", flush=True)
                i = self.finger.image_2_tz(finger_img)
                if i == adafruit_fingerprint.OK:
                    logging.debug("Templated")
                else:
                    if i == adafruit_fingerprint.IMAGEMESS:
                        logging.debug("Image too messy")
                    elif i == adafruit_fingerprint.FEATUREFAIL:
                        logging.debug("Could not identify features")
                    elif i == adafruit_fingerprint.INVALIDIMAGE:
                        logging.debug("Image invalid")
                    else:
                        logging.debug("Other error")
                    return False

                if finger_img == 1:
                    self.update_fingerprint_canva(text="Remove/Lift finger")
                    time.sleep(1)
                    while i != adafruit_fingerprint.NOFINGER:
                        i = self.finger.get_image()

            logging.debug("Creating model...", end="", flush=True)
            i = self.finger.create_model()
            if i == adafruit_fingerprint.OK:
                logging.debug("Created")
                fingerprint_obtained = True
            else:
                if i == adafruit_fingerprint.ENROLLMISMATCH:
                    logging.debug("Prints did not match")
                    self.update_fingerprint_canva(text="An error occurred restarting the registration process in 3 seconds")
                    time.sleep(3)
                    continue
                else:
                    logging.debug("Other error")

            logging.debug("Storing model #%d..." % location, end="", flush=True)
            i = self.finger.store_model(location)
            if i == adafruit_fingerprint.OK:
                logging.debug("Stored")
            else:
                if i == adafruit_fingerprint.BADLOCATION:
                    logging.debug("Bad storage location")
                elif i == adafruit_fingerprint.FLASHERR:
                    logging.debug("Flash storage error")
                else:
                    logging.debug("Other error")

        # TODO SEND TO DB


    def reset_widgets(self):
        self.parent_application.continue_update = False
        # Reset widget window
        for item in self.parent_application.window.winfo_children():
            item.forget()
    
    def setup_fingerprint_canva(self,height=1080,width=1920,text="Place finger on the sensor..."):
        self.fingerprint_canva = tkinter.Canvas(self.parent_application.window, 
                                       bg="white", 
                                       height=height, 
                                       width=width)
        self.fingerprint_text = self.fingerprint_canva.create_text(width//2,height//2,fill="black",font="50",text=text)
        self.fingerprint_canva.pack()

    def update_fingerprint_canva(self,text):
        self.fingerprint_canva.itemconfig(self.fingerprint_text,text=text)
        
Application(tkinter.Tk(),"Tkinter and OpenCV")
