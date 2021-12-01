import tkinter
from tkinter import messagebox
import cv2
from PIL import Image,ImageTk
import time 
import face_recognition
import threading
import pymongo
import logging
logging.basicConfig(level=logging.INFO)

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
             # Database
            self.mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
            # Add Username Textbox
            self.usernameLabel = tkinter.Label(self.rightUpperFrame,text="Enter your companyID")
            self.usernameLabel.pack()
            self.companyID = tkinter.Entry(self.rightUpperFrame)
            self.companyID.focus_set()
            self.companyID.pack()
            # Add Register Bottom Canva
            self.btn_snapshot = tkinter.Button(self.rightBottomFrame,
                                               text="Start user registration",
                                               width=30,height=30,
                                               command = lambda: FaceRegistration(frames=10,
                                                                              duration=10,
                                                                              video=self.video,
                                                                              database=self.mongoclient,
                                                                              companyID=self.companyID.get()).start())
            self.btn_snapshot.pack(expand=True)
            # Variables
            self.delay = 1
            self.listOfImages = {}
            self.currentImage = None
            self.timeForCurrentImage = 0
            self.update()
            self.window.mainloop()
            
    def update(self):
        if int(time.time())>self.timeForCurrentImage:
            ret, frame = self.video.get_frame()
            if ret:
                self.photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
                self.canvas.create_image(0,0,image=self.photo,anchor=tkinter.NW)
        else:
            self.canvas.create_image(0,0,image=self.currentImage,anchor=tkinter.NW)
        self.window.after(self.delay,self.update)
    
    def registerUser(self):
        ret, frame = self.video.get_frame()    
        if ret:
            cv2.imwrite("frame-" + time.strftime("%d-%m-%Y-%H-%M-%S") + ".jpg", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        
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

class FaceRegistration(threading.Thread):
    def __init__(self,frames,duration,video,database,companyID):
        super().__init__()
        self.duration = duration
        self.frames = frames
        self.video = video
        self.database = database
        self.companyID = companyID
        
    def run(self):
        if self.companyID!="":
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
                    
        else:
            messagebox.showerror(title="Error",message="CompanyID field must be filled")
            
Application(tkinter.Tk(),"Tkinter and OpenCV")
