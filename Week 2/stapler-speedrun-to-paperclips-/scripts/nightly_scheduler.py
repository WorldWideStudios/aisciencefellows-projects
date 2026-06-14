from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

from apscheduler.schedulers.blocking import BlockingScheduler

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.living_review import check_topic, list_tracked_topics


def run_check_cycle(logger: logging.Logger) -> None:
    topics = list_tracked_topics()
    if isinstance(topics, dict):
        logger.info("No topics to check: %s", topics.get("message", "no message"))
        return

    logger.info("Running nightly check for %d topic(s)", len(topics))

    for topic in topics:
        label = topic.get("label", "")
        if not label:
            continue

        try:
            result: dict[str, Any] = check_topic(label)
            logger.info("Topic=%s Result=%s", label, json.dumps(result, ensure_ascii=True))
        except (sqlite3.Error, OSError, ValueError, RuntimeError) as exc:
            logger.exception("Topic=%s failed: %s", label, exc)


def build_logger(log_file: Path) -> logging.Logger:
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("living_review_scheduler")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


def main() -> int:
    parser = argparse.ArgumentParser(description="Nightly scheduler for tracked review topics")
    parser.add_argument("--hour", type=int, default=2, help="Hour of day (0-23)")
    parser.add_argument("--minute", type=int, default=0, help="Minute of hour (0-59)")
    parser.add_argument(
        "--log-file",
        default="review_db/nightly_checks.log",
        help="Path to scheduler log file",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run one immediate check cycle and exit",
    )
    args = parser.parse_args()

    logger = build_logger(Path(args.log_file))

    if args.run_once:
        run_check_cycle(logger)
        return 0

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_check_cycle, "cron", hour=args.hour, minute=args.minute, args=[logger])

    logger.info(
        "Scheduler started. Next runs daily at %02d:%02d UTC. Press Ctrl+C to stop.",
        args.hour,
        args.minute,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user")
        time.sleep(0.1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
