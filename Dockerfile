FROM python:3.11-alpine

RUN pip install click pyyaml rsa

ADD . /configuretron
WORKDIR /configuretron
RUN python setup.py install

ENTRYPOINT ["python", "-m", "configuretron"]