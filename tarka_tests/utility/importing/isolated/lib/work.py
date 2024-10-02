from . import LIB_NAME
from .base import LIB_VER
from ..util import log


class Worker:
    def __init__(self):
        self.name = LIB_NAME
        self.version = LIB_VER
        log(self.name)
