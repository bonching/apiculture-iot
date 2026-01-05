from picamzero import Camera
from datetime import datetime
import time
import requests
import os

URL = 'http://192.168.68.106:8081/api/images'
IMAGE_PATH = "/home/apiculture/Pictures/my_photo.jpg"


camera = Camera()
camera.still_size = (1536, 864)
# camera.flip_camera(hflip=True, vflip=True)
time.sleep(2)

while True:
    camera.take_photo(IMAGE_PATH)
    print("Photo has been captured")


    # Get current date and time in yyyyMMddhhmmss format
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Extract the base filename and extension
    filename = os.path.basename(IMAGE_PATH)
    base_name = filename.rsplit('.', 1)[0]
    extension = filename.rsplit('.', 1)[1] if '.' in IMAGE_PATH else ''

    # Create new filename with timestamp
    new_filename = f"{base_name}_{current_time}.{extension}"

    # Open the image file in binary mode
    with open(IMAGE_PATH, 'rb') as image_file:
        # Create a dictionary for the files to be sent, using the new filename
        files = {'image': (new_filename, image_file, 'image/jpeg')}
        
        try:
            # Send the POST request
            response = requests.post(URL, files=files)
            
            # Check the response
            if response.status_code == 200:
                print("Image uploaded successfully!")
                print("Response:", response.text)
            else:
                print(f"Failed to upload image. Status code: {response.status_code}")
                print("Response:", response.text)
                
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            
    time.sleep(60*5) # take photo every 5 minutes

