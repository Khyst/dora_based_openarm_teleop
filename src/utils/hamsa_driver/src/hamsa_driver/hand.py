import os
import configparser
import warnings
import threading
from . import firmware

# Thread lock to prevent concurrent serial port write/read packet corruption
serial_lock = threading.Lock()

# Robust configuration file resolution
possible_paths = [
    # 1. Package source root (for editable install with config in root)
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'hamsa.config')),
    
    # 2. Current working directory
    os.path.abspath(os.path.join(os.getcwd(), 'src', 'openarm_research', 'hamsa', 'hamsa.config')),
    os.path.abspath(os.path.join(os.getcwd(), 'hamsa.config'))
]

# 3. Search upwards from this file's path for the project workspace root
curr_dir = os.path.dirname(os.path.abspath(__file__))
for _ in range(10): # search up to 10 levels
    candidate = os.path.join(curr_dir, 'src', 'openarm_research', 'hamsa', 'hamsa.config')
    if os.path.exists(candidate):
        possible_paths.append(os.path.abspath(candidate))
    candidate_alt = os.path.join(curr_dir, 'hamsa.config')
    if os.path.exists(candidate_alt):
        possible_paths.append(os.path.abspath(candidate_alt))
    
    parent_dir = os.path.dirname(curr_dir)
    if parent_dir == curr_dir:
        break
    curr_dir = parent_dir

# 4. Standard fallbacks using HOME directory
home_dir = os.getenv('HOME')
if home_dir:
    possible_paths.append(os.path.join(home_dir, 'workspace', 'src', 'openarm_research', 'hamsa', 'hamsa.config'))
    possible_paths.append(os.path.join(home_dir, 'workspace', 'src', 'hamsa', 'hamsa.config'))
    possible_paths.append(os.path.join(home_dir, 'robothand', 'hamsa', 'hamsa.config'))

# 5. Package directory (fallback for standard installs running outside workspace)
possible_paths.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'hamsa.config')))

# Clean duplicate paths and check existence
hamsa_config = None
for path in possible_paths:
    if os.path.exists(path):
        hamsa_config = path
        break

if not hamsa_config:
    hamsa_config = possible_paths[0]

config = configparser.ConfigParser()
config.read(hamsa_config)


class HamsaHand:
    def __init__(self, side, config_parser, shared_hand_firmware):
        self.side = side # 'left' or 'right'
        self.config = config_parser
        self.robo_hand = shared_hand_firmware

    def _get_params(self, joint_name, param_keys):
        section = f"{self.side}_{joint_name}"
        if not self.config.has_section(section):
            # Fallback for backwards compatibility if the section is not prefixed
            section = joint_name
            if not self.config.has_section(section):
                raise KeyError(f"Configuration section '{self.side}_{joint_name}' not found in '{hamsa_config}'.")
        
        sec_data = self.config[section]
        return [sec_data.getint(k) for k in param_keys]

    # Curling functions
    def curl_pinky(self, position, time):
        params = self._get_params("pinky curl", ["in", "out", "id"])
        with serial_lock:
            self.robo_hand.curl(position, time, *params)

    def curl_ring(self, position, time):
        params = self._get_params("ring curl", ["in", "out", "id"])
        with serial_lock:
            self.robo_hand.curl(position, time, *params)

    def curl_middle(self, position, time):
        params = self._get_params("middle curl", ["in", "out", "id"])
        with serial_lock:
            self.robo_hand.curl(position, time, *params)

    def curl_index(self, position, time):
        params = self._get_params("index curl", ["in", "out", "id"])
        with serial_lock:
            self.robo_hand.curl(position, time, *params)

    def curl_thumb(self, position, time):
        params = self._get_params("thumb curl", ["in", "out", "id"])
        with serial_lock:
            self.robo_hand.curl(position, time, *params)

    def curl_wrist(self, position, time):
        # Wrist is physically removed/not present in actual hardware
        try:
            params = self._get_params("wrist", ["forwards", "backwards", "id"])
            with serial_lock:
                self.robo_hand.curl(position, time, *params)
        except KeyError:
            warnings.warn(f"Wrist control called on {self.side} hand, but wrist section is not configured.")

    # Position querying
    def curl_pinky_pos(self):
        params = self._get_params("pinky curl", ["in", "out", "id"])
        with serial_lock:
            return self.robo_hand.curl_position(*params)

    def curl_ring_pos(self):
        params = self._get_params("ring curl", ["in", "out", "id"])
        with serial_lock:
            return self.robo_hand.curl_position(*params)

    def curl_middle_pos(self):
        params = self._get_params("middle curl", ["in", "out", "id"])
        with serial_lock:
            return self.robo_hand.curl_position(*params)

    def curl_index_pos(self):
        params = self._get_params("index curl", ["in", "out", "id"])
        with serial_lock:
            return self.robo_hand.curl_position(*params)

    def curl_thumb_pos(self):
        params = self._get_params("thumb curl", ["in", "out", "id"])
        with serial_lock:
            return self.robo_hand.curl_position(*params)

    def curl_wrist_pos(self):
        try:
            params = self._get_params("wrist", ["forwards", "backwards", "id"])
            with serial_lock:
                return self.robo_hand.curl_position(*params)
        except KeyError:
            warnings.warn(f"Wrist position queried on {self.side} hand, but wrist section is not configured.")
            return 0.0

    # Wiggling functions
    def wiggle_pinky(self, position, time):
        params = self._get_params("pinky wiggle", ["left", "right", "id"])
        with serial_lock:
            self.robo_hand.wiggle(position, time, *params)

    def wiggle_ring(self, position, time):
        params = self._get_params("ring wiggle", ["left", "right", "id"])
        with serial_lock:
            self.robo_hand.wiggle(position, time, *params)

    def wiggle_middle(self, position, time):
        params = self._get_params("middle wiggle", ["left", "right", "id"])
        with serial_lock:
            self.robo_hand.wiggle(position, time, *params)

    def wiggle_index(self, position, time):
        params = self._get_params("index wiggle", ["left", "right", "id"])
        with serial_lock:
            self.robo_hand.wiggle(position, time, *params)

    def wiggle_thumb(self, position, time):
        params = self._get_params("thumb wiggle", ["left", "right", "id"])
        with serial_lock:
            self.robo_hand.wiggle(position, time, *params)

    # Position querying
    def wiggle_pinky_pos(self):
        params = self._get_params("pinky wiggle", ["left", "right", "id"])
        with serial_lock:
            return self.robo_hand.wiggle_position(*params)

    def wiggle_ring_pos(self):
        params = self._get_params("ring wiggle", ["left", "right", "id"])
        with serial_lock:
            return self.robo_hand.wiggle_position(*params)

    def wiggle_middle_pos(self):
        params = self._get_params("middle wiggle", ["left", "right", "id"])
        with serial_lock:
            return self.robo_hand.wiggle_position(*params)

    def wiggle_index_pos(self):
        params = self._get_params("index wiggle", ["left", "right", "id"])
        with serial_lock:
            return self.robo_hand.wiggle_position(*params)

    def wiggle_thumb_pos(self):
        params = self._get_params("thumb wiggle", ["left", "right", "id"])
        with serial_lock:
            return self.robo_hand.wiggle_position(*params)


# Single C++ hardware communication object
robo_hand = firmware.Hand()

# High-level Hand objects sharing the single serial interface
right = HamsaHand('right', config, robo_hand)
left = HamsaHand('left', config, robo_hand)


# ---------------------------------------------------------
# Backwards compatibility module-level API (delegates to Right Hand)
# ---------------------------------------------------------

def curl_pinky(position, time):
    right.curl_pinky(position, time)

def curl_ring(position, time):
    right.curl_ring(position, time)

def curl_middle(position, time):
    right.curl_middle(position, time)

def curl_index(position, time):
    right.curl_index(position, time)

def curl_thumb(position, time):
    right.curl_thumb(position, time)

def curl_wrist(position, time):
    right.curl_wrist(position, time)

def curl_pinky_pos():
    return right.curl_pinky_pos()

def curl_ring_pos():
    return right.curl_ring_pos()

def curl_middle_pos():
    return right.curl_middle_pos()

def curl_index_pos():
    return right.curl_index_pos()

def curl_thumb_pos():
    return right.curl_thumb_pos()

def curl_wrist_pos():
    return right.curl_wrist_pos()

def wiggle_pinky(position, time):
    right.wiggle_pinky(position, time)

def wiggle_ring(position, time):
    right.wiggle_ring(position, time)

def wiggle_middle(position, time):
    right.wiggle_middle(position, time)

def wiggle_index(position, time):
    right.wiggle_index(position, time)

def wiggle_thumb(position, time):
    right.wiggle_thumb(position, time)

def wiggle_pinky_pos():
    return right.wiggle_pinky_pos()

def wiggle_ring_pos():
    return right.wiggle_ring_pos()

def wiggle_middle_pos():
    return right.wiggle_middle_pos()

def wiggle_index_pos():
    return right.wiggle_index_pos()

def wiggle_thumb_pos():
    return right.wiggle_thumb_pos()
