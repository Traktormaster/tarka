from tarka.utility.sentinel import NamedObject


def test_named_object():
    t1 = NamedObject("test-1")
    t2 = NamedObject("test-2")
    assert t1.name == "test-1"
    assert t2.name == "test-2"
    assert t1 is not object()
    assert t1 is not t2
    assert t1 is NamedObject("test-1")
    assert t2 is NamedObject("test-2")
    assert str(t1) == "NamedObject(test-1)"
    assert repr(t1) == "NamedObject(test-1)"
