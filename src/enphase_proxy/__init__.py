import importlib.metadata


def version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0"


__version__ = version(__name__)
