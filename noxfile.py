import nox


@nox.session
def tests(session):
    session.install("pytest")
    session.install("pytest-flake8")
    session.install("flake8-black")
    session.run("pytest", "--flake8")
