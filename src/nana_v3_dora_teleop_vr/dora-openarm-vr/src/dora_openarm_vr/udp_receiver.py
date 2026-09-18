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

import collections
import json
import select
import socket
import threading
import time


class JsonUdpReceiver:
    """Background thread that binds a UDP socket and keeps the latest parsed JSON packet."""

    def __init__(self, host: str, port: int, buf_size: int = 4096) -> None:
        self._host = host
        self._port = port
        self._buf_size = buf_size

        self._lock = threading.Lock()
        
        self._latest: dict | None = None
        self._recv_ts: collections.deque[int] = collections.deque(maxlen=512)

        self._running = True

        # Background 스레드에서 실시간으로 Socket을 열어 Quest3로 부터 UDP 패킷 수신
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def latest(self) -> dict | None:
        with self._lock:
            return self._latest

    def drain_recv_timestamps(self) -> list[int]:
        """Return and clear the arrival timestamps (ns) collected since last call."""
        with self._lock:
            items = list(self._recv_ts)
            self._recv_ts.clear()
            return items

    def close(self) -> None:
        self._running = False

    def _parse_packet(self, data: bytes) -> dict | None:
        """
            UDP 패킷 수신 시 JSON 파싱 수행
        """
        try:
            line = data.decode("utf-8", errors="replace").strip()
            if not line:
                return None
            return json.loads(line)
        except json.JSONDecodeError:
            return None

    def _loop(self) -> None:

        while self._running:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as srv: # 소켓 생성 (through socket lib in python3)

                    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    srv.bind((self._host, self._port))
                    srv.settimeout(1.0) # 수신 대기 중 1초 동안 데이터가 없으면 Timeout Error를 발생시켜 self._running 상태를 주기적으로 체크할 수 있게 해줌
                    print(f"[receiver] Listening on UDP {self._host}:{self._port}")

                    while self._running:
                        try:
                            data, _ = srv.recvfrom(self._buf_size) # 가장 마지막에 받은 데이터(last_msg)만 유효한 최신 상태로 보관하고 중간 데이터는 건너 뜀
                            recv_ns = time.time_ns() # 데이터를 받은 시점을 나노초 단위로 기록
                            last_msg = self._parse_packet(data) # 
                            arrivals = [recv_ns] if last_msg is not None else [] # 데이터를 성공적으로 파싱한 경우, 수신 시각을 "arrivals 리스트"에 추가 (json 파싱 실패 시 빈 리스트)

                            # Drain any queued datagrams, keep only the freshest
                            # pose, but record every packet's real arrival time.
                            while select.select([srv], [], [], 0.0)[0]:
                                """
                                    소켓 수신 버퍼에 아직 읽지 않은 패킷이 남아있는 동안, 
                                    지연(Blocking) 없이 빠르게 잔여 데이터를 모두 읽어내기(Drain) 위해 사용된 반복문의 조건식
                                """
                                data, _ = srv.recvfrom(self._buf_size)
                                recv_ns = time.time_ns()
                                parsed = self._parse_packet(data)

                                if parsed is not None:
                                    arrivals.append(recv_ns)
                                    last_msg = parsed

                            with self._lock:
                                self._recv_ts.extend(arrivals)

                                if last_msg is not None:
                                    self._latest = last_msg

                        except TimeoutError:
                            continue

                        except Exception:
                            pass
            except OSError:

                if self._running:
                    # 소켓 bind 실패 시 1초간 대기 후 재시도(주로, 포트가 이미 사용 중일 때 발생)
                    time.sleep(1.0)
