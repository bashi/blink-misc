import contextlib
import os


@contextlib.contextmanager
def scoped_chdir(directory):
    current_dir = os.getcwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(current_dir)
