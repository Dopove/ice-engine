import logging

logger = logging.getLogger("ice_lazy_loader")

class OptionalModule:
    """
    Handles lazy loading of optional dependencies with professional error reporting.
    """
    def __init__(self, module_name: str, extra_name: str):
        self._module_name = module_name
        self._extra_name = extra_name
        self._module = None

    def __getattr__(self, name):
        if self._module is None:
            self._load()
        return getattr(self._module, name)

    def _load(self):
        try:
            self._module = __import__(self._module_name, fromlist=["*"])
            logger.debug(f"Successfully loaded optional module: {self._module_name}")
        except ImportError:
            error_msg = (
                f"\n[ICE DEPENDENCY ERROR]: The feature you are trying to use requires the '{self._module_name}' module.\n"
                f"Please install it using: pip install ice-engine[{self._extra_name}]"
            )
            raise ImportError(error_msg)

    def is_available(self) -> bool:
        try:
            self._load()
            return True
        except ImportError:
            return False
