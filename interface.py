import threading
import tkinter
import cv2
from PIL import Image,ImageTk
import time 
import face_recognition
import pymongo
import numpy
import logging
from concurrent.futures import ThreadPoolExecutor
import sys
import asyncio
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__) 

class Application:
    def __init__(self,window,window_title,video_source=0):
            self.window = window
            self.window.title(window_title)
            self.video_source = video_source
            self.video = VideoCapture(0)
            # Database and generation of known images
            self.mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
            self.known_encodings_collection = self.mongoclient["biometrics"]["faces"]
            self.list_user_companyID = []
            self.list_face_encodings = []
            self._reestablish_faces()
            self.executor = ThreadPoolExecutor(max_workers=2)
            self.identificator = PersonIdentification()
            self.leftFrame = tkinter.Frame(window)
            self.leftFrame.pack(side=tkinter.LEFT)
            self.rightFrame = tkinter.Frame(window)
            self.rightFrame.pack(side=tkinter.RIGHT)
            self.bottomFrame = tkinter.Frame(self.leftFrame)
            self.bottomFrame.pack(side=tkinter.BOTTOM)
            self.canvas = tkinter.Canvas(self.leftFrame,width=self.video.width,height=self.video.height)
            self.canvas.pack()
            self.testFrame = True
            self.delay = 1
            self.listOfImages = {}
            self.currentImage = None
            self.timeForCurrentImage = 0
            self.counter = 0
            self.update()
            self.window.mainloop()
            
    def update(self):
        if int(time.time())>self.timeForCurrentImage:
            ret, frame = self.video.get_frame()
            if ret:
                self.photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
                self.canvas.create_image(0,0,image=self.photo,anchor=tkinter.NW)
                # Test user against known encodings
                if self._test_face():
                    # Future executing
                    self.executor.submit(self.identificator.run,frame,self.list_user_companyID,self.list_face_encodings)
        else:
            self.canvas.create_image(0,0,image=self.currentImage,anchor=tkinter.NW)
        self.window.after(self.delay,self.update)
    
    def _reestablish_faces(self):
        # Obtain all users and concatenate their face encodings
        logger.info("Updating face model")
        collection_cursor = self.known_encodings_collection.find({})
        if collection_cursor:
            for user in collection_cursor:
                self.list_user_companyID.append(user["companyID"])
                for encoding in user["face_encodings"]:
                    self.list_face_encodings.append(encoding)
    
    def _test_face(self):
        # Test frame every 5 frames to avoid creating video lag
        if self.counter==5:
            self.counter=0
            return True
        else:
            self.counter+=1
            return False
            
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

class PersonIdentification:
    def run(self,unknown_face,list_user_companyID,list_face_encodings):
        unknown_face = face_recognition.face_encodings(unknown_face)
        logger.info(f"Image encoding {unknown_face}")
        if unknown_face:
            # Transform face encodings to ndarray
            known_encodings = numpy.array(list_face_encodings)
            matches = face_recognition.compare_faces(known_encodings,unknown_face,tolerance=0.54)
            companyID = "Unknown"
            face_distances = face_recognition.face_distance(known_encodings,unknown_face)
            best_match_index = numpy.argmin(face_distances)
            if matches[best_match_index]:
                # Each company user has 10 saved face encodings so we do a floor division to obtain the user index
                companyID = list_user_companyID[best_match_index//10]
                logger.info(f"Current face matches with user of companyID: {companyID}")
            else:
                logger.info(f"Current face doesn't match any user")
        else:
            logger.info("No face was currently detected")
        

Application(tkinter.Tk(),"Tkinter and Opencv")
