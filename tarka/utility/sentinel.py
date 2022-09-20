class NamedObject(object):
    """
    Singleton named object generation and storage.
    These objects are ideal to be used as special values (sentinels) in algorithms where such are needed.
    """

    _MAP = dict()

    __slots__ = ("_name",)

    def __new__(cls, name):
        self = cls._MAP.get(name)
        if not self:
            cls._MAP[name] = self = object.__new__(cls)
        return self

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def __repr__(self):
        return f"NamedObject({self._name})"

    def __str__(self):
        return f"NamedObject({self._name})"
