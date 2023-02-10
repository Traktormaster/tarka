from tarka.utility.file.name import split_extension


def test_file_split_extension():
    for filename, name, ext in [
        ("", "", ""),
        (".foo", ".foo", ""),
        ("foo.", "foo.", ""),
        (".foo.", ".foo.", ""),
        (".foo..", ".foo..", ""),
        ("...foo", "...foo", ""),
        ("...foo.", "...foo.", ""),
        ("...fo.o", "...fo", ".o"),
        ("...f.o.o", "...f.o", ".o"),
        ("..f..o.o", "..f..o", ".o"),
        ("..f..o.o.", "..f..o.o.", ""),
        (".foo.bar.", ".foo.bar.", ""),
        ("foo.bar.txt", "foo.bar", ".txt"),
        ("foo.BAr.TXt", "foo.BAr", ".TXt"),
        ("foo.txt", "foo", ".txt"),
        ("foo.tar.gz", "foo", ".tar.gz"),
        ("foo.tar.xz", "foo", ".tar.xz"),
        ("foo.tar.bz2", "foo", ".tar.bz2"),
        ("foo.tAR.bZ2", "foo", ".tAR.bZ2"),
        ("foo-12.0a1.en-US.win32.inst.exe", "foo-12.0a1.en-US.win32.inst", ".exe"),
    ]:
        assert split_extension(filename) == (name, ext)
