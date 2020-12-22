import nox

nox.options.reuse_existing_virtualenvs = True


@nox.session
def tests(session):
    session.install("pytest")
    session.install("pytest-pylint")
    session.install("pytest-flake8")
    session.install("flake8-black")
    session.install("nox")
    session.install(".")
    session.run("pytest", "--flake8", "--pylint", "-vv")
