"""Deployer (QA-04): the new version is kept only if it becomes healthy."""

from pathlib import Path

import pytest

from deployer import Deployer


class FakeDocker:
    """Stands in for docker: two containers run the current version."""

    IMAGE = "next-api"

    def __init__(self, new_version_state: str, fails_to_start: bool = False, balancer_uses_new: bool = True) -> None:
        self.balancer_uses_new = balancer_uses_new
        self.running_containers = ["old-1", "old-2"]
        self.stopped: list[str] = []   # containers that exist but are not running
        self.fails_to_start = fails_to_start
        self.new_version_state = new_version_state
        self.removed: list[str] = []
        self.removed_images: list[str] = []
        self.built: list[tuple[str, bool]] = []

    def running(self):
        return [c for c in self.running_containers if c not in self.stopped]

    def containers(self):
        return list(self.running_containers)

    def image_of(self, container):
        return "next-api:1.0.0"

    def state_of(self, container):
        return "healthy" if container.startswith("old") else self.new_version_state

    def instances_served(self):
        """Ids the balancer answers with; the new containers only if it already found them."""
        return {c[:12] for c in self.running_containers if c.startswith("old") or self.balancer_uses_new}

    def logs_of(self, container, lines=5):
        return "the logs of the container"

    def build(self, tag, broken):
        self.built.append((tag, broken))

    def start_next_to_the_current(self, total, tag):
        self.running_containers += [f"new-{n}" for n in range(1, total - len(self.running_containers) + 1)]

        if self.fails_to_start:
            self.stopped += [c for c in self.running_containers if c.startswith("new")]
            raise RuntimeError("docker compose up\nexec: \"next\": executable file not found in $PATH")

    def remove(self, containers):
        self.removed += containers
        self.running_containers = [c for c in self.running_containers if c not in containers]

    def image_tags(self):
        return ["1.1.0", "1.0.0", "0.9.0", "0.8.0", "0.7.0", "0.6.0", "dev"]

    def remove_image(self, tag):
        self.removed_images.append(tag)


@pytest.fixture
def history_file(tmp_path: Path) -> Path:
    return tmp_path / ".deploy-history"


def deployer(docker, history_file):
    return Deployer(docker, history_file, sleep=lambda seconds: None)


def test_healthy_new_version_replaces_the_previous_one(history_file):
    docker = FakeDocker("healthy")

    assert deployer(docker, history_file).deploy("1.1.0") is True
    assert docker.running_containers == ["new-1", "new-2"]
    assert history_file.read_text().split()[-1] == "1.1.0"


def test_the_new_version_is_built_with_its_tag(history_file):
    docker = FakeDocker("healthy")
    deployer(docker, history_file).deploy("1.1.0", broken=True)

    assert docker.built == [("1.1.0", True)]


def test_previous_containers_are_not_removed_before_the_new_ones_are_healthy(history_file):
    docker = FakeDocker("unhealthy")
    deployer(docker, history_file).deploy("bad")

    assert "old-1" not in docker.removed and "old-2" not in docker.removed


@pytest.mark.parametrize("state", ["unhealthy", "restarting", "exited"])
def test_unhealthy_new_version_is_discarded_and_the_previous_one_keeps_running(history_file, state):
    docker = FakeDocker(state)

    assert deployer(docker, history_file).deploy("bad") is False
    assert docker.running_containers == ["old-1", "old-2"]
    assert not history_file.exists()


def test_containers_that_cannot_even_start_are_discarded(history_file):
    docker = FakeDocker("created", fails_to_start=True)

    assert deployer(docker, history_file).deploy("broken") is False
    assert docker.running_containers == ["old-1", "old-2"]
    assert not history_file.exists()


def test_leftovers_of_a_failed_deploy_are_removed_before_the_next_one(history_file):
    docker = FakeDocker("healthy")
    docker.running_containers.append("left-over")
    docker.stopped.append("left-over")
    deployer(docker, history_file).deploy("1.1.0")

    assert "left-over" in docker.removed


def test_new_version_is_discarded_if_the_balancer_never_sends_traffic_to_it(history_file):
    docker = FakeDocker("healthy", balancer_uses_new=False)

    assert deployer(docker, history_file).deploy("1.1.0") is False
    assert docker.running_containers == ["old-1", "old-2"]
    assert not history_file.exists()


def test_two_replicas_remain_even_if_only_one_was_running(history_file):
    docker = FakeDocker("healthy")
    docker.running_containers = ["old-1"]
    deployer(docker, history_file).deploy("1.1.0")

    assert docker.running_containers == ["new-1", "new-2"]


def test_a_new_version_that_never_finishes_starting_is_discarded(history_file):
    docker = FakeDocker("starting")

    assert deployer(docker, history_file).deploy("slow") is False
    assert docker.running_containers == ["old-1", "old-2"]


def test_failed_deploy_keeps_the_version_that_was_recorded(history_file):
    history_file.write_text("1.0.0\n")
    deployer(FakeDocker("unhealthy"), history_file).deploy("bad")

    assert history_file.read_text() == "1.0.0\n"


def test_only_the_images_of_the_last_five_versions_deployed_are_kept(history_file):
    history_file.write_text("0.8.0\n0.9.0\n1.0.0\n")
    docker = FakeDocker("healthy")
    deployer(docker, history_file).deploy("1.1.0")

    assert sorted(docker.removed_images) == ["0.6.0", "0.7.0", "dev"]


def test_the_version_just_deployed_is_never_removed(history_file):
    docker = FakeDocker("healthy")
    deployer(docker, history_file).deploy("1.1.0")

    assert "1.1.0" not in docker.removed_images


def test_images_are_not_touched_after_a_failed_deploy(history_file):
    docker = FakeDocker("unhealthy")
    deployer(docker, history_file).deploy("bad")

    assert docker.removed_images == []


def test_a_version_is_not_recorded_twice_in_a_row(history_file):
    history_file.write_text("v1\n")
    Deployer(FakeDocker("healthy"), history_file, sleep=lambda seconds: None).deploy("v1")

    assert history_file.read_text() == "v1\n"
