"""Marks the suite as a package.

Without this, pytest imports each file as a top-level module while any
``tests.x`` import builds a second, separate copy of it. Two module objects for
one file is how a monkeypatch lands on the wrong one and a test passes without
having run anything.
"""
