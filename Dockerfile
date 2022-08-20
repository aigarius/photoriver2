FROM debian:testing

RUN apt-get update && apt-get install -y python3-requests python3-httpretty python3-mock python3-pytest python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip install black

RUN mkdir -p /river/code /river/base /river/config /river/locals
ADD . /river/code/

RUN pip install /river/code

ENTRYPOINT ["/usr/local/bin/photoriver2"]
