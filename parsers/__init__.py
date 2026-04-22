import importlib
import pkgutil

PARSERS = {}


def load_parsers():
    global PARSERS

    package = __name__

    for _, module_name, _ in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{package}.{module_name}")

        if hasattr(module, "parse"):
            PARSERS[module_name] = module.parse

    return PARSERS
