FROM amd64/ubuntu

MAINTAINER Carlos Queiroz
LABEL version="0.2"

ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y \
    dcmtk \
    libgdcm-tools \
    libvtkgdcm-tools \
    rsync \
    python3 \
    python3-pip \
    python3-pydicom \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 104 4100

COPY receive.sh /home/www/
COPY storescp.cfg /home/www/
COPY organizer.py /home/www/

WORKDIR /home

# Inicia apenas o receptor DICOM (organizador agora está no SCU)
CMD /home/www/receive.sh
