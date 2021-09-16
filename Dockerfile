FROM klakegg/hugo:ubuntu

RUN mkdir /dist
COPY . /dist
WORKDIR /dist

# Download Node 

ENV NODE_VERSION=12.6.0
RUN apt-get update && apt install -y curl
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get -y install nodejs
RUN npm --version

# Build

RUN npm install
RUN hugo -d public
