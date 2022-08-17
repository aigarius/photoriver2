FROM debian:testing

RUN apt-get update && apt-get install -y python3-requests python3-httpretty python3-mock python3-pytest python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip install black

RUN mkdir -p /river/code /river/base /river/config /river/locals
ADD photoriver2 /river/code/photoriver2
ADD tests /river/code/tests
ADD pylintrc /river/code
ADD pyproject.toml /river/code
ADD setup.cfg /river/code

ENV PYTHONPATH="/river/code"
WORKDIR "/river/code/photoriver2/"

ENTRYPOINT ["/usr/bin/python3"]
CMD ["/river/code/photoriver2/main.py"]
