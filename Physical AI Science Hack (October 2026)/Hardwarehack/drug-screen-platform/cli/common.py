"""Shared error handling for the command-line tools."""

import functools
from typing import Callable

import typer

from flex_client import FlexError
from protocol_generator import ProtocolError


def friendly_errors(command: Callable) -> Callable:
    """Turn expected failures into a one-line ``Error: ...`` and exit code 2."""

    @functools.wraps(command)
    def wrapper(*args, **kwargs):
        try:
            return command(*args, **kwargs)
        except (FlexError, ProtocolError, OSError, ValueError, KeyError) as error:
            message = error.args[0] if isinstance(error, KeyError) and error.args else error
            typer.echo(f"Error: {message}")
            raise typer.Exit(2)

    return wrapper
