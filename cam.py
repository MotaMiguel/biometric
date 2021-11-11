import cv2

cap = cv2.VideoCapture(1)

if not (cap.isOpened()):
    print("Could not open video device")

while(True): 
    # Capture frame-by-frame
    ret, frame = cap.read()
    # Display the resulting frame
    frame = cv2.resize(frame,(1920,1080))
    cv2.imshow("preview",frame)
    #Waits for a user input to quit the application
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
