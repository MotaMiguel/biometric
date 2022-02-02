import adafruit_fingerprint
import serial
import pymongo

# Fingerprint reader
uart = serial.Serial("/dev/ttyUSB0", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

if finger.read_templates() != adafruit_fingerprint.OK:
        raise RuntimeError("Failed to read templates")
templates = finger.templates
for i in templates:
    finger.delete_model(i)

# Mongo connection
mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
# Database of known encondings and fingerprints
known_encodings_collection = mongoclient["biometrics"]["users"]
known_encodings_collection.drop()