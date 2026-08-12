# The image recognition model

In order to perform the image recognition in the mimicking demo, we use [trt_pose_hand](https://github.com/NVIDIA-AI-IOT/trt_pose_hand). The performance of this model seems to depend heavily on the lighting and background to the human hand. Here we provide examples of such dependence. All examples were filmed in the same room.

## Poor conditions
See [this](https://photos.google.com/share/AF1QipPl4sXyFtXnLex2OrEEDnnEpfn54b5AOxY8ps9SgIJNztRC3gQJs-jMQP8jEkJCeQ/photo/AF1QipP82zzmdx9cP7RCHvERTls9aMw2RZJRzn-dOAr4?key=OWJydThtWnZWQWFCVGp5TTVTeTRQYXlfbXU0Y21R) video for conditions where the model is struggling - it misidentifies the majority of poses. There is direct sunlight coming from behind the human hand and so it is almost a silhouette.

Part way though a screen is brought in behind the human hand and performance dramatically improves. Note how the screen blocks a lot of the light coming in from behind the human hand. Towards the end there is a bit of trouble distinguishing between peace and pan but repositioning the human hand seems to help.

## Moderate conditions
[Here](https://photos.google.com/share/AF1QipPl4sXyFtXnLex2OrEEDnnEpfn54b5AOxY8ps9SgIJNztRC3gQJs-jMQP8jEkJCeQ/photo/AF1QipP_-OhIFx3yjhLnSTvuOcroIqLPAR9h_PuwsBNM?key=OWJydThtWnZWQWFCVGp5TTVTeTRQYXlfbXU0Y21R) the model performs reasonably well. The sunlight is now striking the human hand side-on.

Towards the end it struggles a bit distinguishing between pan and peace. However, moving closer and centering the human hand seems to resolve this.

## Optimal condition
[Here](https://photos.google.com/u/1/share/AF1QipPl4sXyFtXnLex2OrEEDnnEpfn54b5AOxY8ps9SgIJNztRC3gQJs-jMQP8jEkJCeQ/photo/AF1QipNYcG-DdkiwKlr-JRCxFkvLGH9LdpQmM556nNZJ?key=OWJydThtWnZWQWFCVGp5TTVTeTRQYXlfbXU0Y21R) we show what is probably optimal conditions.

Natural light is shining from behind the camera directly onto the human hand. The recognition model is able to clearly distinguish between pan and peace (the problematic gestures).
