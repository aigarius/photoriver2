import nox

nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["tests"]


@nox.session
def tests(session):
    session.install("pytest")
    session.install("pytest-pylint")
    session.install("nox")
    session.install("black")
    session.install(".")
    session.run("pytest", "--pylint", "-vv")
    session.run("black", "-l", "119", ".")


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
        "--pylint",
        "-vv",
        external=True,
    )
