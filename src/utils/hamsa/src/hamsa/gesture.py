from jetcam.utils import bgr8_to_jpeg
from os.path import expandvars

image_path = expandvars("$HOME/robothand/hamsa/jetcam.jpeg")

def get_gesture(recognition_model, camera_and_container):
    image = camera_and_container["camera"].value
    data = recognition_model.preprocess(image)
    cmap, paf = recognition_model.model_trt(data)
    cmap, paf = cmap.detach().cpu(), paf.detach().cpu()
    counts, objects, peaks = recognition_model.parse_objects(cmap, paf)
    joints = recognition_model.preprocess_data.joints_inference(image, counts, objects, peaks)
    recognition_model.draw_joints(image, joints)
    #recognition_model.draw_objects(image, counts, objects, peaks)
    dist_bn_joints = recognition_model.preprocess_data.find_distance(joints)
    gesture = recognition_model.clf.predict([dist_bn_joints,[0]*recognition_model.num_parts*recognition_model.num_parts])
    gesture_joints = gesture[0]
    recognition_model.preprocess_data.prev_queue.append(gesture_joints)
    recognition_model.preprocess_data.prev_queue.pop(0)
    recognition_model.preprocess_data.print_label(image, recognition_model.preprocess_data.prev_queue, recognition_model.gesture_type)
    camera_and_container["image_w"].value = bgr8_to_jpeg(image)
    ## write image to file (used for debugging, perfectly safe to comment out the bellow 2 lines)
    with open(image_path, 'wb') as f:
        f.write(camera_and_container["image_w"].value)
    return recognition_model.gesture_type[gesture_joints-1]
