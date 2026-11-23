"""The pages: the same address gives a page to a browser and the JSON to a program."""

import pytest

HTML = {"Accept": "text/html,application/xhtml+xml"}   # what a browser sends


@pytest.mark.parametrize("path", ["/orders", "/health"])
def test_a_browser_gets_a_page(client, path):
    response = client.get(path, headers=HTML)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Nodo Ruta" in response.text


@pytest.mark.parametrize("path", ["/orders", "/health"])
def test_a_program_gets_json(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize("path", ["/orders", "/health"])
def test_the_answer_depends_on_what_the_client_accepts(client, path):
    assert client.get(path, headers=HTML).headers["vary"] == "Accept"
    assert client.get(path).headers["vary"] == "Accept"


@pytest.mark.parametrize("path", ["/", "/orders", "/health"])
def test_every_page_has_the_menu_and_the_instance(client, path):
    page = client.get(path, headers=HTML).text

    for link in ('href="/"', 'href="/orders"', 'href="/health"'):
        assert link in page
    assert "instance-A" in page


def test_the_current_page_is_marked_in_the_menu(client):
    assert '<a href="/orders" class=active>' in client.get("/orders", headers=HTML).text
    assert '<a href="/health" class=active>' in client.get("/health", headers=HTML).text


@pytest.mark.parametrize("path", ["/orders", "/health"])
def test_the_page_loads_even_if_the_data_is_lost_but_the_json_does_not(client, data_file, path):
    data_file.unlink()

    assert client.get(path, headers=HTML).status_code == 200
    assert client.get(path).status_code == 503
