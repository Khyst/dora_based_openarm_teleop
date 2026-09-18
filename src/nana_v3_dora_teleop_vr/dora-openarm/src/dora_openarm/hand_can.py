# Copyright 2026 Enactic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""CAN FD driver module for dexterous hand control."""

import logging
import socket
import struct
import numpy as np

logger = logging.getLogger(__name__)

CANFD_BRS = 0x01  # Bit Rate Switch flag for CAN FD


class HandCanController:
    """Controller for transmitting dexterous hand control frames via SocketCAN (CAN FD)."""

    def __init__(self, interface: str | None = "can0", can_id: int = 0x008, enabled: bool = True, step_size: int = 25):
        self.interface = interface
        self.can_id = can_id
        self.enabled = enabled and bool(interface)
        self._socket: socket.socket | None = None
        self._current_val_int: int = 0
        self._last_sent_val_int: int | None = None
        self._step_size: int = step_size  # 25% step per frame for 5-level smooth stepping

        if self.enabled and self.interface:
            self._init_socket()

    def _init_socket(self) -> None:
        try:
            sock = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
            sock.setsockopt(socket.SOL_CAN_RAW, socket.CAN_RAW_FD_FRAMES, 1)
            sock.bind((self.interface,))
            self._socket = sock
            logger.info("[HandCanController] Bound to SocketCAN FD interface: %s", self.interface)
            print(f"[HandCanController] Successfully bound to SocketCAN FD interface: {self.interface} (CAN ID: 0x{self.can_id:03X})")
        except Exception as e:
            logger.warning("[HandCanController] Failed to bind SocketCAN interface '%s': %s", self.interface, e)
            print(f"[HandCanController] WARNING: Failed to bind SocketCAN interface '{self.interface}': {e}")
            self._socket = None

    def send_trigger(self, trigger_val: float) -> None:
        """Step smoothly towards target trigger value frame by frame.

        0.0 -> 0x00 (0%, all fingers open)
        1.0 -> 0x64 (100%, all fingers closed)

        CAN FD Frame structure:
          Header (6 bytes): 0x00 0x32 0x32 0x32 0x32 0x32
          Fingers (5 bytes): [val_int] * 5
          Tail (2 bytes): 0x00 0xC8
          Flags: CANFD_BRS (0x01)
        """
        if not self.enabled or not self.interface:
            return

        clamped = float(np.clip(trigger_val, 0.0, 1.0))
        target_val_int = int(round(clamped * 100))

        # Step current level towards target_val_int frame by frame (1 level step per frame)
        if self._current_val_int < target_val_int:
            self._current_val_int = min(self._current_val_int + self._step_size, target_val_int)
        elif self._current_val_int > target_val_int:
            self._current_val_int = max(self._current_val_int - self._step_size, target_val_int)

        val_int = self._current_val_int
        if val_int == self._last_sent_val_int:
            return
        self._last_sent_val_int = val_int

        val_hex = f"{val_int:02X}"
        cansend_str = f"cansend {self.interface} {self.can_id:03X}##1003232323232{val_hex * 5}00C8"

        if self._socket is None:
            logger.warning("[HandCanController] Cannot send trigger: SocketCAN interface '%s' not connected", self.interface)
            print(f"[HandCanController] WARNING: Interface '{self.interface}' not connected. Would send: {cansend_str}")
            return

        try:
            header = bytes.fromhex("003232323232")
            fingers = bytes([val_int] * 5)
            tail = bytes.fromhex("00C8")
            payload = header + fingers + tail
            flags = CANFD_BRS
            res0 = 0
            frame = struct.pack("=IBBBx64s", self.can_id, len(payload), flags, res0, payload.ljust(64, b"\x00"))
            self._socket.send(frame)
            logger.debug("[HandCanController] Trigger: %.2f (%d%%) -> Sent: %s", clamped, val_int, cansend_str)
        except Exception as e:
            logger.warning("[HandCanController] SocketCAN send failed on '%s': %s", self.interface, e)
            print(f"[HandCanController] WARNING: SocketCAN send failed on '{self.interface}': {e}")

    def close(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
