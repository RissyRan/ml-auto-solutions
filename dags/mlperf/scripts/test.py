"""Minimal ray job to test job submission."""

import logging
import os
import pprint
import sys
import ray

sys.path.insert(0, os.path.dirname(__file__))


def main():
  logging.basicConfig(
      format="[RAY TEST JOB] %(asctime)s %(levelname)-8s %(message)s",
      level=logging.INFO,
      datefmt="%Y-%m-%d %H:%M:%S",
  )
  logging.info("Initializing ray")
  ray.init()
  logging.info("Ray init done")
  logging.info("Ray nodes are %s", pprint.pformat(ray.nodes()))

  logging.info("Shutting down ray")
  ray.shutdown()


if __name__ == "__main__":
  main()
