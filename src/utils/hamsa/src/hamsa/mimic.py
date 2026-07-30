from os.path import expandvars
import sys
trt_hand_dir = expandvars("$HOME/robothand/trt_pose_hand")
sys.path.append(trt_hand_dir)

from hamsa import poses as Poses
from hamsa import gesture as Gesture
from hamsa import trt_pose_hand
from preprocessdata import preprocessdata
import datetime as dt
from jetcam.usb_camera import USBCamera
from jetcam.csi_camera import CSICamera
from jetcam.utils import bgr8_to_jpeg
import ipywidgets
from IPython.display import display

def get_pose_model():
    hand_model = trt_pose_hand.Model()
    hand_model.setup(trt_hand_dir, preprocessdata)
    return hand_model


## Load camera and image container
## We use camera to pull the frames from the CSI camera
## image_w is used as a container for said frames
def get_camera_and_container(hand_model):
    camera =  CSICamera(width=hand_model.WIDTH, height=hand_model.HEIGHT, capture_fps=30)
    image_w = ipywidgets.Image(format='jpeg', width=224, height=224)
    # display(image_w)
    
    return {"camera": camera, "image_w": image_w}



def run_mimic(recognition_model, camera_and_container):
    try:
        camera_and_container["camera"].running = True
        print(f'Possible gestures: {recognition_model.gesture_type}')
        this_gesture = ''
        current_gesture = ''
        last_change = dt.datetime.now()
        
        while True:
            last_gesture = this_gesture
            this_gesture = Gesture.get_gesture(recognition_model, camera_and_container)
            if this_gesture is not last_gesture:
                last_change = dt.datetime.now()
            long_enough = (dt.datetime.now()-last_change).total_seconds() > .7
            if long_enough and (this_gesture is not current_gesture):
                print(f'Current gesture: {this_gesture}'.ljust(30), end='\r')
                if this_gesture == 'fist':
                    Poses.fist(700)
                    current_gesture = this_gesture
                if this_gesture == 'stop':
                    Poses.idle(700)
                    current_gesture = this_gesture
                if this_gesture == 'ok':
                    Poses.ok(700)
                    current_gesture = this_gesture
                if this_gesture == 'peace':
                    Poses.peace(700)
                    current_gesture = this_gesture
                if this_gesture == 'pan':
                    Poses.pan(700)
                    current_gesture = this_gesture
    except KeyboardInterrupt:
        Poses.idle(700)
        camera_and_container["camera"].running = False
        print('Camera off'.ljust(30))


