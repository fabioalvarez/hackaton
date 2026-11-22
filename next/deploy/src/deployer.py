"""Deploys a new version next to the current one, and keeps it only if it works.

If the new containers do not become healthy, they are removed and the current version never stops.
"""

import time
from pathlib import Path

import docker as docker_cli

REPLICAS = 2     # containers the service runs, and how many new ones a deployment starts
CHECKS = 60      # how many times the new containers are checked...
INTERVAL = 2     # ...every this many seconds (2 minutes in total)
KEEP_IMAGES = 5


def say(text: str) -> None:
    print(text, flush=True)


class Deployer:
    def __init__(self, docker=docker_cli, history_file: Path = Path(".deploy-history"), sleep=time.sleep) -> None:
        self.docker = docker
        self.history_file = history_file
        self.sleep = sleep

    def deploy(self, tag: str, broken: bool = False) -> bool:
        """Returns True if the new version is now the one running."""
        current = self.docker.running()
        self.remove_leftovers(current)

        say(f"current version: {self.docker.image_of(current[0])}" if current else "no version is running")
        say(f"building the image {docker_cli.IMAGE}:{tag}")
        self.docker.build(tag, broken)

        say(f"starting {REPLICAS} new containers next to the {len(current)} current ones")
        error = self.start_new_containers(current, tag)
        new = [container for container in self.docker.containers() if container not in current]

        if error is None and self.wait_until_healthy(new) and self.wait_until_balancer_uses(new):
            self.keep_new_version(tag, current)
            return True

        self.discard_new_version(new, error)
        return False

    def start_new_containers(self, current: list[str], tag: str) -> str | None:
        """Returns the reason if the containers could not even start."""
        try:
            self.docker.start_next_to_the_current(len(current) + REPLICAS, tag)
        except RuntimeError as error:
            return str(error).splitlines()[-1]

        return None

    # --- Outcome ---------------------------------------------------------------

    def keep_new_version(self, tag: str, current: list[str]) -> None:
        say("the new containers are healthy, removing the previous ones")
        self.docker.remove(current)
        self.record(tag)
        self.remove_old_images()

        say(f"done: {docker_cli.IMAGE}:{tag} is running")

    def discard_new_version(self, new: list[str], error: str | None) -> None:
        if error:
            say(f"the new containers could not start: {error}")
        else:
            failed = next((c for c in new if self.docker.state_of(c) != "healthy"), new[0])
            say(f"the new version did not become healthy, last logs:\n{self.docker.logs_of(failed)}")

        if new:
            self.docker.remove(new)

        say("rolled back: the previous version keeps running")

    def remove_leftovers(self, current: list[str]) -> None:
        """Containers that are not running are left over from a deployment that failed."""
        leftovers = [container for container in self.docker.containers() if container not in current]

        if leftovers:
            self.docker.remove(leftovers)

    def record(self, tag: str) -> None:
        """The history has one tag per line; the last one is the version that runs."""
        with self.history_file.open("a") as history:
            history.write(f"{tag}\n")

    def remove_old_images(self) -> None:
        """Keeps the images of the last versions deployed, and removes the rest."""
        history = self.history_file.read_text().split()
        keep = set(history[-KEEP_IMAGES:])

        for tag in self.docker.image_tags():
            if tag not in keep:
                self.remove_image(tag)

    def remove_image(self, tag: str) -> None:
        try:
            self.docker.remove_image(tag)
        except RuntimeError:
            pass  # still used by a container

    # --- Waiting ---------------------------------------------------------------

    def wait_until_healthy(self, containers: list[str]) -> bool:
        for _ in range(CHECKS):
            states = [self.docker.state_of(container) for container in containers]

            if all(state == "healthy" for state in states):
                return True

            if any(state in ("unhealthy", "restarting", "exited", "dead", "created") for state in states):
                return False

            say(f"waiting for the new containers: {', '.join(states)}")
            self.sleep(INTERVAL)

        return False

    def wait_until_balancer_uses(self, containers: list[str]) -> bool:
        """Healthy is not enough: the balancer must already be sending traffic to the new containers."""
        wanted = {container[:12] for container in containers}  # the instance id is the short container id

        for _ in range(CHECKS):
            if wanted <= self.docker.instances_served():
                return True

            say("waiting for the balancer to send traffic to the new containers")
            self.sleep(INTERVAL)

        return False
