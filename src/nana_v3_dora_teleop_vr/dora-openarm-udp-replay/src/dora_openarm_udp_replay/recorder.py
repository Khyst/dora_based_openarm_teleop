#!/usr/bin/env python3

import argparse
import json
import logging
import os
from pathlib import Path
import time

import dora
import pyarrow as pa

logging.basicConfig(level=logging.INFO, format="[dora-udp-recorder] %(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Dora VR UDP Telemetry Recorder Node")
    parser.add_argument(
        "--file",
        type=str,
        default="recordings/vr_session.jsonl",
        help="Target filepath to record telemetry data",
    )
    args = parser.parse_args()

    target_path = Path(args.file).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Recording VR UDP telemetry to: {target_path}")

    node = dora.Node()
    start_time = time.time()
    record_count = 0

    with target_path.open("w", encoding="utf-8") as f:
        for event in node:
            if event["type"] == "INPUT":
                event_id = event["id"]
                val = event["value"]

                # Convert PyArrow array to Python list
                if hasattr(val, "to_pylist"):
                    py_data = val.to_pylist()
                else:
                    py_data = list(val)

                is_bool = pa.types.is_boolean(val.type)
                data_type = "bool" if is_bool else "float32"

                now = time.time()
                rel_time = now - start_time

                record_entry = {
                    "timestamp": now,
                    "rel_time": rel_time,
                    "id": event_id,
                    "type": data_type,
                    "data": py_data,
                }

                f.write(json.dumps(record_entry) + "\n")
                f.flush()
                record_count += 1

                if record_count % 500 == 0:
                    logger.info(f"Recorded {record_count} events... (latest: {event_id})")

    logger.info(f"Recording finished. Total recorded events: {record_count}")


if __name__ == "__main__":
    main()
