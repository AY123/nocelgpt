"""The finite compiled extension composition, never a runtime plugin loader."""

from anovel.domain.extensions import ExtensionRegistry
from anovel.genre.extensions.business import BusinessValidator


def registered_extensions() -> ExtensionRegistry:
    return ExtensionRegistry((BusinessValidator(),))
