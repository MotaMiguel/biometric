from locale import currency
from telnetlib import LOGOUT
import tkinter
from tkinter import Frame, messagebox
from tkinter import font
from turtle import right, width
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
import numpy as np
import math

import serial
logging.basicConfig(level=logging.DEBUG)

class Application:
    def __init__(self,window,video_source=0):
            self.window = window
            self.window.title("Biometric Registration")
            self.window.geometry('1920x1080')
            self.video_source = video_source
            self.video = VideoCapture(0)
            # Database
            mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
            self.database = mongoclient["biometrics"]["users"]
            # Fingerprint reader
            self.uart = serial.Serial("/dev/ttyUSB0", baudrate=57600, timeout=1)
            self.finger = adafruit_fingerprint.Adafruit_Fingerprint(self.uart)
            #Initialize Canvas
            self.generate_initial_canva()
            # Variables
            self.delay = 1
            self.listOfImages = {}
            self.currentImage = None
            self.timeForCurrentImage = 0
            self.window.mainloop()
            
    def update(self):
        if self.continue_update:
            ret, frame = self.video.get_frame()
            if ret:
                fliped_frame = cv2.flip(frame,1)
                self.photo = ImageTk.PhotoImage(image=Image.fromarray(fliped_frame))
                self.videoFrame.create_image(0,0,image=self.photo,anchor=tkinter.NW)
        else:
            return
        self.window.after(self.delay,self.update)
    
    def generate_initial_canva(self):
         # Generate the frame layout
        logging.info("Starting initial canva")
        self.topFrameLabel = tkinter.Label(self.window,text="Enter your CompanyID",font=("Arial",22))
        self.topFrameLabel.place(relx=0.5,rely=0.3,relheight=1.0,relwidth=1.0,anchor=tkinter.CENTER)
        
        self.companyID = tkinter.Entry(self.window,font=("Arial",22))
        self.companyID.focus_set()
        self.companyID.place(relx=0.5,rely=0.35,relheight=0.05,relwidth=0.2,anchor=tkinter.CENTER)
        
        self.btn_start = tkinter.Button(self.window,
                                        text="Start user registration",
                                        width=30,
                                        height=30,
                                        font=("Arial",22),
                                        relief=tkinter.RAISED,
                                        command = lambda: [UserRegistration(frames=5,
                                                                        yaw=[(-42,42),(-47,-75),(46,76)],
                                                                        duration=8,
                                                                        video=self.video,
                                                                        database=self.database,
                                                                        companyID=self.companyID.get(),
                                                                        finger=self.finger,
                                                                        application=self).start(),
                                                           self._init_face_registration()])
        self.btn_start.place(relx=0.5,rely=0.45,relheight=0.05,relwidth=0.4,anchor=tkinter.CENTER)
        
    def _init_face_registration(self):
        logging.debug("Initializing face registration process")
        # Delete old canva
        self.reset_widgets()
        # Variable to avoid having the GUI continously request and feed video data
        self.continue_update = True
        # Setup new canva
        self.generate_face_canva()
        # Call update to start showing continous video feed
        self.update()
        
    def generate_face_canva(self):
         # Generate the frame layout
        logging.info("Starting facial registration canva")
        self.topFrameLabel = tkinter.Label(self.window,text="Please follow the instructions below:",font=("Arial",28))
        self.topFrameLabel.place(relx=0.5,rely=0.05,relheight=0.05,relwidth=1.0,anchor=tkinter.CENTER)
        
        self.topFrameLabel2 = tkinter.Label(self.window,text="Look directly into the camera",font=("Arial",28))
        self.topFrameLabel2.place(relx=0.5,rely=0.1,relheight=0.05,relwidth=1.0,anchor=tkinter.CENTER)

        self.topFrameLabel3 = tkinter.Label(self.window,font=("Arial",28),fg="#ff0000")
        self.topFrameLabel3.place(relx=0.5,rely=0.15,relheight=0.05,relwidth=1.0,anchor=tkinter.CENTER)

        # Current Video Image
        self.videoFrame = tkinter.Canvas(self.window,width=self.video.width,height=self.video.height)
        self.videoFrame.place(relx=0.35,rely=0.6,relheight=0.5,relwidth=0.5,anchor=tkinter.CENTER)
        
        self.videoFrameLabel = tkinter.Label(self.window,text="Current head position",font=("Arial",24))
        self.videoFrameLabel.place(relx=0.25,rely=0.3,relheight=0.05,relwidth=0.3,anchor=tkinter.CENTER)
        
        # Example Image
        
        self.exampleFrame = tkinter.Canvas(self.window,width=self.video.width,height=self.video.height)
        self.exampleFrame.place(relx=0.85,rely=0.6,relheight=0.5,relwidth=0.5,anchor=tkinter.CENTER)
        # Needs to be part of the class otherwise image garbage collector takes it away :'(
        self.examplePhoto = ImageTk.PhotoImage(image=Image.open("frontal_face.png"))
        self.exampleFrame.create_image(0,0,image=self.examplePhoto,anchor=tkinter.NW)
        
        self.exampleFrameLabel = tkinter.Label(self.window,text="Expected head position",font=("Arial",24))
        self.exampleFrameLabel.place(relx=0.70,rely=0.3,relheight=0.05,relwidth=0.3,anchor=tkinter.CENTER)

    
    def change_face_canva(self,position):
        # Change facial canva to stay accordingly to expected rotation
        if position==1:
            self.topFrameLabel2.config(text="Rotate your head slighty to the left")
            self.examplePhoto = ImageTk.PhotoImage(image=Image.open("left_face.png"))
            self.exampleFrame.create_image(0,0,image=self.examplePhoto,anchor=tkinter.NW)
        elif position==2:
            self.topFrameLabel2.config(text="Rotate your head slighty to the right")
            self.examplePhoto = ImageTk.PhotoImage(image=Image.open("right_face.png"))
            self.exampleFrame.create_image(0,0,image=self.examplePhoto,anchor=tkinter.NW)
        
    def rotation_warning(self,current):
        text=""
        if current=="UNDER":
            text="User's head is currently under rotated"
        elif current=="OVER":
            text="User's head is currently over rotated"
        elif current=="NOFACE":
            text="No face detected please adjust slighty"
        self.topFrameLabel3.config(text=text)
    
    def generate_fingerprint_canva(self):
         # Generate the frame layout
        logging.info("Starting fingerprint registration canva")
        self.fingerFrame = tkinter.Label(self.window,text="Place a finger on the sensor...",font=("Arial",50))
        self.fingerFrame.place(relx=0.5,rely=0.5,relheight=1,relwidth=1,anchor=tkinter.CENTER)
    
    def change_finger_canva(self,text):
        self.fingerFrame.config(text=text)
        
    def reset_widgets(self):
        self.continue_update = False
        # Reset widget window
        for item in self.window.winfo_children():
            item.place_forget()
            
    def restart_registration(self):
        self.change_finger_canva("Registration successful! Starting a new registration")
        time.sleep(3)
        self.reset_widgets()
        self.generate_initial_canva()
    
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
    def __init__(self,frames,yaw,duration,video,database,companyID,finger,application):
        super().__init__()
        self.duration = duration
        # Frames specifies how many frames per face position
        self.frames = frames
        # Yaw specifies the range of acceptable yaw values
        self.yaw = yaw
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
            facial_data = self.face_registration()
            self.parent_application.reset_widgets()
            self.parent_application.generate_fingerprint_canva()
            ret,finger_id = self.fingerprint_registration()
            if ret:
                self.finish_registration(facial_data,finger_id)
            self.parent_application.restart_registration()
        else:
            messagebox.showerror(title="Error",message="CompanyID field must be filled")
    
    def face_registration(self):
        frames_counter = 0
        logging.info(f"Starting face retrieval for user with companyID: {self.companyID}")
        # Initialize user dictionary
        user_dict = {"companyID":self.companyID,"face_encodings":[]}
        # Frames *3 due to taking frontal, lateral right and lateral left photos
        while frames_counter<self.frames*3:
            ret, frame = self.video.get_frame()
            face_location = face_recognition.face_locations(frame)
            face_encoding = face_recognition.face_encodings(frame,face_location)
            # If face was recognized
            if len(face_encoding) > 0:
                # Obtain current yaw
                ret_yaw,current = self.calculate_face_yaw(frame,self.yaw[frames_counter//self.frames])
                if ret_yaw:
                    # Insert into list of face encodings
                    # the return from the facerecognition lib comes in a list of numpy arrays
                    user_dict["face_encodings"].append(list(face_encoding[0]))
                    logging.info(f"Face encoding for user with companyID {self.companyID} added to list")
                    
                    frames_counter += 1
                    
                    # Check if user already finish current face position if so change image and text
                    if frames_counter in [5,10]:
                        self.parent_application.change_face_canva(position=frames_counter//5)
                    
                else:
                    # Add information that person was recognized but failed to comply with the expected rotation
                    logging.info(f"User failed to rotate or rotated too much")
                # Update rotation warning 
                # Rotation warning can be removed if last tested frame was valid
                self.parent_application.rotation_warning(current=current)
                # Tell thread to sleep to distribute the frames along the duration
                time.sleep(self.duration/self.frames)
            else:
                self.parent_application.rotation_warning(current="NOFACE")
        # Return company ID and face encoding
        # Data is only saved after fingerprint finishes correctly
        return user_dict
        
    def calculate_face_yaw(self,img,expected_yaw):    
        # Obtain landmarks from img
        landmarks = face_recognition.face_landmarks(img)
        if len(landmarks)>1:
            logging.debug("Multiple people detected please only allow one person")
            return False
        landmarks = landmarks[0]
        # Specify specific landmarks used for head yaw
        nose_tip = landmarks["nose_bridge"][-1]
        left_eye = landmarks["left_eye"][0]
        right_eye = landmarks["right_eye"][-3]
        chin = landmarks["chin"][8]
        left_lip = landmarks["top_lip"][0]
        right_lip = landmarks["bottom_lip"][-1]
        # Camera internals (following the github example)
        size = img.shape
        focal_length = size[1]
        center = (size[1]/2, size[0]/2)
        # 3D model points to be used for comparation
        model_points = np.array([
                            (0.0, 0.0, 0.0),             # Nose tip
                            (0.0, -330.0, -65.0),        # Chin
                            (-225.0, 170.0, -135.0),     # Left eye left corner
                            (225.0, 170.0, -135.0),      # Right eye right corne
                            (-150.0, -150.0, -125.0),    # Left Mouth corner
                            (150.0, -150.0, -125.0)      # Right mouth corner
                        ])
        
        camera_matrix = np.array(
                                [[focal_length, 0, center[0]],
                                [0, focal_length, center[1]],
                                [0, 0, 1]], dtype = "double"
                                )
        image_points = np.array([nose_tip,
                                 chin,
                                 left_eye,
                                 right_eye,
                                 left_lip,
                                 right_lip

                                ], dtype="double")
        dist_coeffs = np.zeros((4,1)) # Assuming no lens distortion
        
        (success, rotation_vector, translation_vector) = cv2.solvePnP(model_points, 
                                                                      image_points, 
                                                                      camera_matrix, 
                                                                      dist_coeffs, 
                                                                      flags=cv2.SOLVEPNP_UPNP)
        
        
        (nose_end_point2D, jacobian) = cv2.projectPoints(np.array([(0.0, 0.0, 1000.0)]), 
                                                         rotation_vector, 
                                                         translation_vector, 
                                                         camera_matrix, 
                                                         dist_coeffs)
        
        p1 = ( int(image_points[0][0]), int(image_points[0][1]))
        p2 = ( int(nose_end_point2D[0][0][0]), int(nose_end_point2D[0][0][1]))
        x1, x2 = self._head_pose_points(img, rotation_vector, translation_vector, camera_matrix)
        try:
            m = (x2[1] - x1[1])/(x2[0] - x1[0])
            yaw = int(math.degrees(math.atan(-1/m)))
        except:
            yaw = 90
        logging.info(f"Testing user for yaw in between {expected_yaw[0]} and {expected_yaw[1]}")
        logging.info(f"Current user yaw is {yaw}")
        
        # Validating yaw against expected yaw 
        max_expected_val = max(expected_yaw[0],expected_yaw[1])
        min_expected_val = min(expected_yaw[0],expected_yaw[1])
        current = ""
        # Abs can't be used here because of negative yaw
        if yaw in range(min_expected_val,max_expected_val):
            return (True,"")
        # If my rotation if bigger than the positive rotation I'm over rotation
        if yaw>max_expected_val and max_expected_val>0:
            current = "OVER"
         # If my rotation if bigger than the negative rotation I'm over rotation
        elif yaw<min_expected_val and min_expected_val<0:
            current = "OVER"
        elif yaw>max_expected_val and max_expected_val<0:
            current = "UNDER"
        elif yaw<min_expected_val and min_expected_val>0:
            current = "UNDER"
        return (False,current)
        
    def _head_pose_points(self,img, rotation_vector, translation_vector, camera_matrix):
        """
        Get the points to estimate head pose sideways    
        Parameters
        ----------
        img : np.unit8
        Original Image.
        rotation_vector : Array of float64
        Rotation Vector obtained from cv2.solvePnP
        translation_vector : Array of float64
        Translation Vector obtained from cv2.solvePnP
        camera_matrix : Array of float64
        The camera matrix
        Returns
        -------
        (x, y) : tuple
        Coordinates of line to estimate head pose
        """
        rear_size = 1
        rear_depth = 0
        front_size = img.shape[1]
        front_depth = front_size*2
        val = [rear_size, rear_depth, front_size, front_depth]
        point_2d = self._get_2d_points(img, rotation_vector, translation_vector, camera_matrix, val)
        y = (point_2d[5] + point_2d[8])//2
        x = point_2d[2]

        return (x, y)
        
    def _get_2d_points(self,img, rotation_vector, translation_vector, camera_matrix, val):
        """Return the 3D points present as 2D for making annotation box"""
        point_3d = []
        dist_coeffs = np.zeros((4,1))
        rear_size = val[0]
        rear_depth = val[1]
        point_3d.append((-rear_size, -rear_size, rear_depth))
        point_3d.append((-rear_size, rear_size, rear_depth))
        point_3d.append((rear_size, rear_size, rear_depth))
        point_3d.append((rear_size, -rear_size, rear_depth))
        point_3d.append((-rear_size, -rear_size, rear_depth))

        front_size = val[2]
        front_depth = val[3]
        point_3d.append((-front_size, -front_size, front_depth))
        point_3d.append((-front_size, front_size, front_depth))
        point_3d.append((front_size, front_size, front_depth))
        point_3d.append((front_size, -front_size, front_depth))
        point_3d.append((-front_size, -front_size, front_depth))
        point_3d = np.array(point_3d, dtype=np.float).reshape(-1, 3)

        # Map to 2d img points
        (point_2d, _) = cv2.projectPoints(point_3d,
                                        rotation_vector,
                                        translation_vector,
                                        camera_matrix,
                                        dist_coeffs)
        point_2d = np.int32(point_2d.reshape(-1, 2))
        return point_2d
        
    def fingerprint_registration(self):
        fingerprint_obtained = False
        if self.finger.read_templates() != adafruit_fingerprint.OK:
            raise RuntimeError("Failed to read templates")
        number_of_saved_users = len(self.finger.templates)
        logging.debug(f"System Currently has {number_of_saved_users} fingers saved")
        while not fingerprint_obtained:
            """Take a 2 finger images and template it, then store in 'location'"""
            for finger_img in range(1, 3):
                if finger_img == 2:
                    self.parent_application.change_finger_canva(text="Please set same finger in the sensor again")

                while True:
                    i = self.finger.get_image()
                    if i == adafruit_fingerprint.OK:
                        logging.debug("Image taken")
                        break
                    if i == adafruit_fingerprint.NOFINGER:
                        logging.debug("No finger detected")
                    elif i == adafruit_fingerprint.IMAGEFAIL:
                        logging.debug("Imaging error")
                    else:
                        logging.debug("Other error")

                logging.debug("Templating...")
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
                    return (False,)

                if finger_img == 1:
                    self.parent_application.change_finger_canva(text="Remove/Lift finger")
                    time.sleep(1)
                    while i != adafruit_fingerprint.NOFINGER:
                        i = self.finger.get_image()

            logging.debug("Creating model...")
            i = self.finger.create_model()
            if i == adafruit_fingerprint.OK:
                logging.debug("Created")
                fingerprint_obtained = True
            else:
                if i == adafruit_fingerprint.ENROLLMISMATCH:
                    logging.debug("Prints did not match")
                    self.parent_application.change_finger_canva(text="An error occurred restarting the registration process in 3 seconds")
                    time.sleep(3)
                    self.parent_application.change_finger_canva(text="Place a finger on the sensor...")
                    continue
                else:
                    logging.debug("Other error")

            logging.debug(f"Storing model {number_of_saved_users+1} ...")
            i = self.finger.store_model(number_of_saved_users+1)
            if i == adafruit_fingerprint.OK:
                logging.debug("Stored")
                return True,number_of_saved_users+1
            else:
                if i == adafruit_fingerprint.BADLOCATION:
                    logging.debug("Bad storage location")
                    return (False,)
                elif i == adafruit_fingerprint.FLASHERR:
                    logging.debug("Flash storage error")
                    return (False,)
                else:
                    logging.debug("Other error")
                    return (False,)

    def finish_registration(self,facial_data,finger_id):
        # Add the finger_id to facial_data 
        facial_data["finger_id"]=finger_id
        # Registar data into the database
        self.database.insert_one(facial_data)   
        logging.debug(f"Face and fingerprint data for user with companyID {self.companyID} successfully saved")
        
Application(tkinter.Tk())
