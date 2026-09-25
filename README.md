
# V720P2P
A python script that will pull your V720 camera feed from the naxclow p2p servers.
And the cameras I am referring to are https://naxclow.com

# Example
Running on macOS
<img width="964" height="624" alt="Screenshot 2026-09-26 at 1 03 33 am" src="https://github.com/user-attachments/assets/4391003d-a7f0-4789-bfca-221a7fd0839d" />

Running on termux (android) with openbox window manager, running on aterm terminal
<img width="1092" height="888" alt="Screenshot 2026-09-26 at 3 04 32 am" src="https://github.com/user-attachments/assets/d2b8c828-2dec-4c78-8161-d5eacb8c6728" />


# Editing the file
You can open this up in a text editor or a terminal text editor and paste everything

# How to get Device ID, token, server IP and Port (Try doing it on a mac with apple silicon or find another way to obtain)
1. Set up your camera using the app and verify you can reach the stream in the app
2. Go to h5v720app.naxclowyun.com and press the blue button labeled app, this should open a dialog box to open up the application.
3. It will open up the app, go back to your browser, then you can view your camera.
4. Open up devtools (press F12 or right click then inspect)
5. Go to network tab then reload the page
6. Press the funnel icon to show filters.
7. Press the Socket filter and find live2 and press on it
8. Click payload then you will see device ID, token, server IP and Port
9. Input into the v720wss.py in the blank fields

``
DEVICE_ID = ""
CAMERA_TOKEN = ""
SERVER_IP = ""
SERVER_PORT = ""
``

# Running the script
It requires websockets and ffmpeg so run 
```
pip install websockets
```
For macOS 
```
brew install ffmpeg
```

Linux
```
apt install ffmpeg
```

Run the script with
```
python v720wss.py
```
# NOTES
- Video works but audio does not, I am working on it
- This script may not work in the future so I will update it if it changes how they stream it anytime soon.
- This can probably use any user agent header so input as you wish, default is macOS.
- You cannot access any other cameras you don't have access to unless they share it with you.
