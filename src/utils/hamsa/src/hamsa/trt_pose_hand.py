import json
import cv2
import matplotlib.pyplot as plt
import matplotlib.image as mpimg 
import trt_pose.coco
import math
import os
import numpy as np
import traitlets
import pickle 

import trt_pose.models

import torch

import torch2trt
from torch2trt import TRTModule

from trt_pose.draw_objects import DrawObjects
from trt_pose.parse_objects import ParseObjects

import torchvision.transforms as transforms
import PIL.Image

from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

class Model():
    def __init__(self, *args):
        self.WIDTH = 0
        self.HEIGHT = 0
        self.num_parts = 0

        self.hand_pose = dict()
        self.gesture = dict()

        self.gesture_type = []

        self.device = None
        self.mean = None
        self.std = None
        self.parse_objects = None
        self.draw_objects = None
        self.clf = None
        self.predicted = None
        self.preprocess_data = None
        self.model_trt = None
        
    def preprocess(self, image):
        # global device
        self.device = torch.device('cuda')
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = PIL.Image.fromarray(image)
        image = transforms.functional.to_tensor(image).to(self.device)
        image.sub_(self.mean[:, None, None]).div_(self.std[:, None, None])
        return image[None, ...]

    def draw_joints(self, image, joints):
        count = 0
        for i in joints:
            if i==[0,0]:
                count+=1
        if count>= 3:
            return 
        for i in joints:
            cv2.circle(image, (i[0],i[1]), 2, (0,0,255), 1)
        cv2.circle(image, (joints[0][0],joints[0][1]), 2, (255,0,255), 1)
        for i in self.hand_pose['skeleton']:
            if joints[i[0]-1][0]==0 or joints[i[1]-1][0] == 0:
                break
            cv2.line(image, (joints[i[0]-1][0],joints[i[0]-1][1]), (joints[i[1]-1][0],joints[i[1]-1][1]), (0,255,0), 1)

    def setup(self, pose_hand_dir, preprocessdata):
        
        with open(f'{pose_hand_dir}/preprocess/hand_pose.json', 'r') as f:
            self.hand_pose = json.load(f)

        topology = trt_pose.coco.coco_category_to_topology(self.hand_pose)

        self.num_parts = len(self.hand_pose['keypoints'])
        num_links = len(self.hand_pose['skeleton'])

        model = trt_pose.models.resnet18_baseline_att(self.num_parts, 2 * num_links).cuda().eval()

        self.WIDTH = 224
        self.HEIGHT = 224
        data = torch.zeros((1, 3, self.HEIGHT, self.WIDTH)).cuda()

        if not os.path.exists(f'{pose_hand_dir}/model/hand_pose_resnet18_att_244_244_trt.pth'):
            MODEL_WEIGHTS = f'{pose_hand_dir}/model/hand_pose_resnet18_att_244_244.pth'
            model.load_state_dict(torch.load(MODEL_WEIGHTS))
            self.model_trt = torch2trt.torch2trt(model, [data], fp16_mode=True, max_workspace_size=1<<25)
            OPTIMIZED_MODEL = f'{pose_hand_dir}/model/hand_pose_resnet18_att_244_244_trt.pth'
            torch.save(self.model_trt.state_dict(), OPTIMIZED_MODEL)


        OPTIMIZED_MODEL = f'{pose_hand_dir}/model/hand_pose_resnet18_att_244_244_trt.pth'

        self.model_trt = TRTModule()
        self.model_trt.load_state_dict(torch.load(OPTIMIZED_MODEL))


        self.parse_objects = ParseObjects(topology,cmap_threshold=0.12, link_threshold=0.15)
        self.draw_objects = DrawObjects(topology)


        self.mean = torch.Tensor([0.485, 0.456, 0.406]).cuda()
        self.std = torch.Tensor([0.229, 0.224, 0.225]).cuda()
        self.device = torch.device('cuda')

        self.clf = make_pipeline(StandardScaler(), SVC(gamma='auto', kernel='rbf'))

        # 😠 
        self.preprocess_data = preprocessdata(topology, self.num_parts)

        svm_train = False
        if svm_train:
            self.clf, self.predicted = self.preprocess_data.trainsvm(self.clf, joints_train, joints_test, hand.labels_train, hand.labels_test)
            filename = f'{pose_hand_dir}/svmmodel.sav'
            pickle.dump(self.clf, open(filename, 'wb'))
        else:
            filename = f'{pose_hand_dir}/svmmodel.sav'
            self.clf = pickle.load(open(filename, 'rb'))

        with open(f'{pose_hand_dir}/preprocess/gesture.json', 'r') as f:
            self.gesture = json.load(f)
        self.gesture_type = self.gesture["classes"]
