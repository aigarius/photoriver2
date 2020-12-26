import nox

nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["tests"]


@nox.session
def tests(session):
    session.install("pytest")
    session.install("pytest-pylint")
    session.install("pytest-flake8")
    session.install("flake8-black")
    session.install("nox")
    session.install(".")
    session.run("pytest", "--flake8", "--pylint", "-vv")


@nox.session
def docker_tests(session):
    session.run("docker", "build", "-t", "photoriver2", ".", external=True)
    session.run(
        "docker",
        "run",
        "--rm",
        "-it",
        "--entrypoint",
        "pytest-3",
        "--workdir",
        "/river/code",
        "photoriver2",
        "--flake8",
        "--pylint",
        "-vv",
        external=True,
    )
