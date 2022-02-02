import threading
import tkinter
import cv2
from PIL import Image,ImageTk
import time 
import face_recognition
import pymongo
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor
import sys
import asyncio
import adafruit_fingerprint
import serial 
import math
import random
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__) 

class Application:
    def __init__(self,window,window_title,video_source=0):
            self.window = window
            self.window.title(window_title)
            self.window.geometry("1920x1080")
            self.video_source = video_source
            self.video = VideoCapture(0)
            # Fingerprint reader
            self.uart = serial.Serial("/dev/ttyUSB0", baudrate=57600, timeout=1)
            self.finger = adafruit_fingerprint.Adafruit_Fingerprint(self.uart)
            # Mongo connection
            self.mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
            # Database of known encondings and fingerprints
            self.known_encodings_collection = self.mongoclient["biometrics"]["users"]
            # Thread executor
            self.executor = ThreadPoolExecutor(max_workers=2)
            # Initalize canvas
            self.canvas = None
            self.delay = 1
            self.validate()
            # Continue update is a variable responsible for stopping the recursive video loop without (sort of a callback from the child thread)
            self.continue_update = True
            self.window.mainloop()
            
    def update(self):
        if self.continue_update:
            ret, frame = self.video.get_frame()
            if ret:
                self.photo = cv2.resize(frame,(int(self.video.width*1.5),int(self.video.height*1.5)),interpolation=cv2.INTER_AREA)
                self.photo = ImageTk.PhotoImage(image=Image.fromarray(self.photo))
                self.videoFrame.create_image(0,0,image=self.photo,anchor=tkinter.NW)
            self.window.after(self.delay,self.update)
    
    def validate(self):
        validator = Biometric_Login(self.finger,self.known_encodings_collection,self.video,self)
        validator.start()
         
    def generate_simple_canva(self,text,color="#000000"):   
        """ Initial and final canva"""
        # Generate the frame layout
        logging.info("Starting fingerprint registration canva")
        self.fingerFrame = tkinter.Label(self.window,text=text,font=("Arial",40),fg=color)
        self.fingerFrame.place(relx=0.5,rely=0.5,relheight=1,relwidth=1,anchor=tkinter.CENTER)
        
    def generate_face_canva(self,text):
        logging.info("Starting face canva")
        self.topFrameLabel = tkinter.Label(self.window,text=text,font=("Arial",32))
        self.topFrameLabel.place(relx=0.5,rely=0.1,relheight=0.05,relwidth=1.0,anchor=tkinter.CENTER)
        
        self.videoFrame = tkinter.Canvas(self.window,width=self.video.width*1.5,height=self.video.height*1.5)
        self.videoFrame.place(relx=0.5,rely=0.5,relheight=0.5,relwidth=0.5,anchor=tkinter.CENTER)
        
    def reset_widgets(self):
        self.continue_update = False
        # Reset widget window
        for item in self.window.winfo_children():
          item.place_forget()
    
    
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

class Biometric_Login(threading.Thread):
    def __init__(self,finger,users,video,application):
        super().__init__()
        self.finger = finger
        self.users = users
        self.video = video
        self.parent_application = application
        
    def run(self):
        """Initial thread call calls another functions so that we can keep this thread alive and the tkinter pool running in the background"""
        self.cascade()
        
    
    def cascade(self):
        """Cascade from Fingerprint Identification to Facial Verification"""
        # Start fingerprint identification
        logging.info("Starting fingerprint identification")
        # Start fingerprint canva
        self.parent_application.generate_simple_canva("In order to login please place your registered finger in the sensor")
        finger_ret = self.get_fingerprint()
        if finger_ret:
            finger_id = self.finger.finger_id
            logging.info(f"Finger print with id {finger_id} found")
            possible_user = self.users.find_one({"finger_id":finger_id})
            # Start facial verification
            logging.info("Starting facial verification")
            self.parent_application.reset_widgets()
            if self.facial_verification(possible_user=possible_user):
                logging.info("User logged in successfully")
                # Open the door to the hobbit :D 
                self.parent_application.generate_simple_canva(text=f"Welcome user with companyID {possible_user['companyID']}",color="#0e5200")
            time.sleep(3)
        # change the state to reset and stop updating the function in the parent (i.e tkinter main window)
        self.parent_application.reset_widgets()
        self.cascade()
        
    def get_fingerprint(self):
        """Get a finger print image, template it, and see if it matches!"""
        logging.info("Waiting for image...")
        while self.finger.get_image() != adafruit_fingerprint.OK:
            pass
        logging.info("Templating...")
        if self.finger.image_2_tz(1) != adafruit_fingerprint.OK:
            return False
        logging.info("Searching...")
        if self.finger.finger_search() != adafruit_fingerprint.OK:
            return False
        return True
    
    def facial_verification(self,possible_user):
        images = []
        user_encodings = np.array(possible_user["face_encodings"])
        # Number of times we want the user to open his mouth
        desired_transitions = random.randint(1,5)
        logging.info(f"User will have to executed {desired_transitions} actions")
        # Start new canva for video capture
        self.parent_application.generate_face_canva(f"Please open and close your mouth {desired_transitions} times")
        # Start video showing function
        self.parent_application.continue_update = True
        self.parent_application.update()
        # Capture frames during 15 seconds
        end_capture = time.time()+15
        while time.time()<end_capture:
            ret,frame = self.video.get_frame()
            if ret:
                face_landmarks_list = face_recognition.face_landmarks(frame)
                if len(face_landmarks_list) > 1:
                    logging.info("More than one person detected stopping verification")
                    return False
                elif len(face_landmarks_list)==1:
                    mouth_open = self.check_mouth_open(face_landmarks_list[0]["top_lip"],face_landmarks_list[0]["bottom_lip"])
                    logging.info(f"User is currently with mouth open ? {mouth_open}")
                    images.append((frame,mouth_open))
                    
        try:
            # Add the first value to the transition
            # Calculate the transitions
            mouth_transitions_index=[1]+[n+1 for (n,(a,b)) in enumerate(zip(images,images[1:])) if a[1]!=b[1]]
            mouth_transitions = list(zip(*[images[i] for i in mouth_transitions_index]))
            logging.info(f"Number of actions {mouth_transitions[1]}")
            number_transitions = mouth_transitions[1].count(True)
            if number_transitions!=desired_transitions:
                logging.info("User did not perform the specified number of actions")
                self.parent_application.generate_simple_canva(text="User failed to perform the specified number of actions",color="#ff0000")
                return False
            # Validated the faces against the database
            all_results = []
            for image in mouth_transitions[0]:
                face_location = face_recognition.face_locations(image)
                face_encoding = face_recognition.face_encodings(image,face_location)
                # If it matches with one of the encodings we trust it because we will validate more images against all encodings
                result = face_recognition.compare_faces(user_encodings, face_encoding,tolerance=0.54).count(True)>0
                logging.info(result)
                # Save all resuts (since each image was different, some where with mouth open)
                all_results.append(result)
                
            # before returning remove the current canva
            self.parent_application.reset_widgets()
            # If all images match the same person (i.e mouth open-mouth closed-mouth open all the same person we validate his identity)
            result = all_results.count(False)==0
            if not result:
                self.parent_application.generate_simple_canva(text="Couldn't verify user",color="#ff0000")
            return result
        except IndexError:
            self.parent_application.generate_simple_canva(text="No faces were found",color="#ff0000")
            return False

    def _get_lip_height(self,lip):
        sum=0
        for i in [2,3,4]:
            # distance between two near points up and down
            distance = math.sqrt( (lip[i][0] - lip[12-i][0])**2 +
                                (lip[i][1] - lip[12-i][1])**2   )
            sum += distance
        return sum / 3

    def _get_mouth_height(self,top_lip, bottom_lip):
        sum=0
        for i in [8,9,10]:
            # distance between two near points up and down
            distance = math.sqrt( (top_lip[i][0] - bottom_lip[18-i][0])**2 + 
                                (top_lip[i][1] - bottom_lip[18-i][1])**2   )
            sum += distance
        return sum / 3

    def check_mouth_open(self,top_lip, bottom_lip):
        top_lip_height =    self._get_lip_height(top_lip)
        bottom_lip_height = self._get_lip_height(bottom_lip)
        mouth_height =      self._get_mouth_height(top_lip, bottom_lip)

        # if mouth is open more than lip height * ratio, return true.
        ratio = 0.8
        if mouth_height > min(top_lip_height, bottom_lip_height) * ratio:
            return True
        else:
            return False
        
    
Application(tkinter.Tk(),"Tkinter and Opencv")
