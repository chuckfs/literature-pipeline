import importlib
import pkgutil

PARSERS = {}


def load_parsers():
    global PARSERS

    def walk(package_name, path):
        for _, module_name, is_pkg in pkgutil.iter_modules(path):
            full_name = f"{package_name}.{module_name}"
            module = importlib.import_module(full_name)

            if hasattr(module, "parse"):
                key = full_name.replace("parsers.", "")
                PARSERS[key] = module.parse

            if is_pkg:
                walk(full_name, module.__path__)

    walk(__name__, __path__)

    return PARSERS
