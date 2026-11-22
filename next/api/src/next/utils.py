"""Small helpers shared by the app."""

from fastapi import APIRouter


def list_route_paths(router: APIRouter, exclude: str = "/") -> list[str]:
    """Paths registered in a router, without the excluded one."""
    return [route.path for route in router.routes if route.path != exclude]
