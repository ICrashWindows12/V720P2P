# V720P2P
A python script that will pull your V720 camera feed from the p2p servers


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

```
DEVICE_ID = ""

# This is the CAMERA/P2P token (tarPwd), NOT the V720 account JWT.
CAMERA_TOKEN = ""

SERVER_IP = ""
SERVER_PORT = ""

```

# Running the script
It requires websockets so run `
pip install websockets
`

Run with 
```
python v720wss.py
```
