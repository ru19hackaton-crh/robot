FROM ev3dev/ev3dev-stretch-ev3-generic
RUN apt-get update && apt-get -qq -y install python3-pip
ADD requirements.txt /tmp/
RUN pip3 install --trusted-host pypi.python.org -r /tmp/requirements.txt

WORKDIR /app
COPY . /app

ENV PYTHONIOENCODING=utf8
ENV ROBOT_BRAIN=localhost

CMD ["python3", "./fake_main.py"]
