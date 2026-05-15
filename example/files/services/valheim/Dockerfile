FROM ubuntu:26.04

# setup apt
ENV DEBIAN_FRONTEND=noninteractive
RUN dpkg --add-architecture i386 \
 && echo steam steam/question select "I AGREE" | debconf-set-selections \
 && echo steam steam/license note '' | debconf-set-selections

# install steamcmd
RUN apt-get update \
 && apt-get install -y ca-certificates xdg-user-dirs steamcmd \
 && rm -rf /var/lib/apt/lists/*
ENV PATH="$PATH:/usr/games"

# install startup script
USER 1000
COPY ./entrypoint.sh /entrypoint.sh
CMD ["/entrypoint.sh"]

# server wants SIGINT to shut down properly
STOPSIGNAL SIGINT