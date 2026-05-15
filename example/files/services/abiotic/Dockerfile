FROM ubuntu:26.04

# setup apt
ENV DEBIAN_FRONTEND=noninteractive
RUN dpkg --add-architecture i386 \
 && echo steam steam/question select "I AGREE" | debconf-set-selections \
 && echo steam steam/license note '' | debconf-set-selections

# install steamcmd and wine
RUN apt-get update \
 && apt-get install -y ca-certificates xdg-user-dirs steamcmd wine64 \
 && rm -rf /var/lib/apt/lists/*
ENV PATH="$PATH:/usr/games"

# install startup script
USER 1000
COPY ./entrypoint.sh /entrypoint.sh
CMD ["/entrypoint.sh"]