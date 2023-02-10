from typing import Tuple


def split_extension(name: str) -> Tuple[str, str]:
    """
    Split extension that respects the common, but peculiar exception of multi-level extensions like ".tar.gz".
    Since the extension of name is pretty much optional, arbitrary and has no real standard, the only way to deal
    with them is to care for each specific case we are interested in. Therefore this solution is never going to be
    complete, but at least it is a solution to some.

    NOTE: Additional differences to os.path.splitext():
        - input can't be a path, only a filename is correct
        - ending periods will not be split as an extension
        - no support for bytes

    One can argue that "there is no actual multi-level extension and .tar.gz is just .gz". There is no pertinent
    case when I want to create an archive "foo.tar.gz" and I consider "foo.tar" the name, so the ".tar" must be
    part of the extension by exclusion. The fact that this question arises at all, points out the absolute lack of
    any guidance on what an extension should actually be. It is and always was a form of metadata that indicates
    the type of content the file holds. The most notable system where this convention is kept is Windows, but even
    for them, the official docs only state that an extension is "optional" and "separated from the filename by a
    period": https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file

    NOTE: Validating the name for use is not in the scope of this function to be usable by the OS or FS.
    """
    rightmost_dot = name.rfind(".")
    if rightmost_dot <= 0 or rightmost_dot == len(name) - 1:
        # Either no dot, leading single dot or trailing dot. All of which means that there is no extension to split.
        return name, ""
    for after_hidden in range(rightmost_dot):
        if name[after_hidden] != ".":
            # Found first not-dot that is before the rightmost dot.
            break
    else:
        # All dots are leading, meaning there is no extension to split.
        return name, ""
    second_rightmost_dot = name.rfind(".", after_hidden, rightmost_dot)
    if second_rightmost_dot > after_hidden and 7 <= len(name) - second_rightmost_dot <= 8:
        # There is a second rightmost dot that is right of the first not-dot and it is in the range from the end of
        # the name to be a nested-extension possibly.
        ext = name[second_rightmost_dot:]
        if ext.lower() in (".tar.gz", ".tar.bz2", ".tar.xz"):
            return name[:second_rightmost_dot], ext
    return name[:rightmost_dot], name[rightmost_dot:]
