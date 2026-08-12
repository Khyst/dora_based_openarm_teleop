import poses as Poses
import gesture as Gesture


def scissors(hand, time):
    Poses.peace(hand, time)

def rock(hand, time):
    Poses.fist(hand, time)

def paper(hand, time):
    Poses.idle(hand, time)


def one_two_three(hand, time):
    rock(hand, time)
    delay = 1
    sleep(delay)
    Poses.one(hand, time)
    sleep(delay)
    Poses.two(hand, time)
    sleep(delay)
    Poses.three(hand, delay)
    sleep(delay)

def win(time):
    ok(time)

def lost(hand, time):
    poses.paper(hand, time)
    hand.curl_wrist(0.05, time)

def draw(time):
    # Couldn't think of a good pose to show a draw, so just start a new run
    run_rock_paper_scissors(hand, recognition_model, camera_and_container)

def run_rock_paper_scissors(hand, recognition_model, camera_and_container):
    choice = Random.randint(1, 3)
    one_two_three(hand, 1000)
    if choice == 1:
        rock(hand, 1000)
    elif choice == 2:
        paper(hand, 1000)
    elif choice == 3:
        scissors(hand, 1000)
    
    ## check humans move
    camera.running = True
    print(f'Possible gestures: {recognition_model.gesture_type}')
    this_gesture = ''
    current_gesture = ''
    last_change = dt.datetime.now()
    read = True
    while read:
        last_gesture = this_gesture
        this_gesture =  Gesture.get_gesture(recognition_model, camera_and_container)
        if this_gesture is not last_gesture:
            last_change = dt.datetime.now()
        long_enough = (dt.datetime.now()-last_change).total_seconds() > .7
        if long_enough and (this_gesture is not current_gesture):
            print(f'Current gesture: {this_gesture}'.ljust(30), end='\r')
            
            if this_gesture == 'fist' and choice == 1:
                draw(hand, recognition_model, camera_and_container)
            elif this_gesture == 'fist' and choice == 2:
                win(1000)
            elif this_gesture == 'fist' and choice == 3:
                lost(1000)
            elif this_gesture == 'stop' and choice == 1:
                lost(1000)
            elif this_gesture == 'stop' and choice == 2:
                draw(hand, recognition_model, camera_and_container)
            elif this_gesture == 'stop' and choice == 3:
                win(1000)
            elif this_gesture == 'peace' and choice == 1:
                win(1000)
            elif this_gesture == 'peace' and choice == 2:
                lost(1000)
            elif this_gesture == 'peace' and choice == 3:
                draw(hand, recognition_model, camera_and_container)
    
            if this_gesture == 'fist' or this_gesture == 'stop' or this_gesture == 'peace':
                read = False
    
    camera.running = False
