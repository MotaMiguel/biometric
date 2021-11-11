import tkinter
import cv2
from PIL import Image,ImageTk
import time 

class Application:
    def __init__(self,window,window_title,video_source=0):
            self.window = window
            self.window.title(window_title)
            self.video_source = video_source
            self.video = VideoCapture(0)
            self.leftFrame = tkinter.Frame(window)
            self.leftFrame.pack(side=tkinter.LEFT)
            self.rightFrame = tkinter.Frame(window)
            self.rightFrame.pack(side=tkinter.RIGHT)
            self.bottomFrame = tkinter.Frame(self.leftFrame)
            self.bottomFrame.pack(side=tkinter.BOTTOM)
            self.canvas = tkinter.Canvas(self.leftFrame,width=self.video.width,height=self.video.height)
            self.canvas.pack()
            #self.btn_snapshot = tkinter.Button(window,text="Snapshot",width=50,command=self.takeSnapshot)
            #self.btn_snapshot.pack(anchor=tkinter.CENTER,expand=True)
            self.btn_snapshot = tkinter.Button(self.bottomFrame,text="Take photo",width=50,command=self.takePicture)
            self.btn_snapshot.pack(expand=True)
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
    
    def takeSnapshot(self):
        ret, frame = self.video.get_frame()    
        if ret:
            cv2.imwrite("frame-" + time.strftime("%d-%m-%Y-%H-%M-%S") + ".jpg", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    
    def takePicture(self):
        ret, frame = self.video.get_frame()    
        if ret:
            numberOfCaptureImages = len(self.listOfImages.keys())
            btn_image = tkinter.Button(self.rightFrame,text=f"Image timestamp {str(int(time.time()))}",width=50,command = lambda: self.showImage(numberOfCaptureImages))
            btn_image.pack()
            self.listOfImages[numberOfCaptureImages] = frame
    
    def showImage(self,imageIndex):
        imageArray = self.listOfImages[imageIndex]
        self.currentImage = ImageTk.PhotoImage(image=Image.fromarray(imageArray))
        self.timeForCurrentImage = int(time.time())+5
            
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

Application(tkinter.Tk(),"Tkinter and Opencv")
