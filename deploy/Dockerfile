FROM python:3.12-slim
LABEL maintainer="citto@72to.ru"
ENV PYTHONUNBUFFERED=1
ENV LANG=ru_RU.UTF-8

RUN apt-get update &&  \
    apt-get install --no-install-recommends -y \
    git \
    binutils \
    libpq-dev\
    gcc  && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

WORKDIR /code
COPY . /code

RUN pip install -e . && pip cache purge
RUN chmod +x ./deploy/.dockerinit.sh

CMD [ "./deploy/.dockerinit.sh" ]
