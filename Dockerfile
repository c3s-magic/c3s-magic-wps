# vim:set ft=dockerfile:
FROM continuumio/miniconda3
LABEL maintainer=https://github.com/c3s-magic/c3s-magic-wps
LABEL description="c3s magic WPS Demo" Vendor="c3s-magic" Version="0.3.0"

# Update Debian system
RUN apt-get update && apt-get install -y \
 build-essential \
 gfortran \
 fonts-dejavu \
&& rm -rf /var/lib/apt/lists/*

RUN wget https://julialang-s3.julialang.org/bin/linux/x64/1.0/julia-1.0.3-linux-x86_64.tar.gz && \
    tar xfz julia-*-linux-x86_64.tar.gz && \
    ln -s $(pwd)/julia-*/bin/julia /usr/bin/julia

# Update conda
RUN conda update -n base conda

COPY environment.yml /opt/environment.yml

# Create conda environment
RUN conda env create -n wps -f /opt/environment.yml

# Install development version of pyWPS

RUN git clone https://github.com/geopython/pywps.git /opt/pywps

WORKDIR /opt/pywps
RUN ["/bin/bash", "-c", "source activate wps && pip install ."]

#Add dependancies of esmvaltool to wps conda environement created earlier
WORKDIR /opt/esmvaltool

# RUN conda env update -n wps -f environment.yml
# RUN ["/bin/bash", "-c", "source activate wps && pip install -e ."]
RUN ["/bin/bash", "-c", "source activate wps && Rscript /opt/conda/envs/wps/lib/python3.6/site-packages/esmvaltool/install/R/setup.R"]
RUN ["/bin/bash", "-c", "source activate wps && julia /opt/conda/envs/wps/lib/python3.6/site-packages/esmvaltool/install/Julia/setup.jl"]
# RUN ["/bin/bash", "-c", "source activate wps && conda install -c conda-forge cdo==1.9.5 hdf5==1.10.3"]

# Copy WPS project
COPY . /opt/wps

WORKDIR /opt/wps

# Install WPS
RUN ["/bin/bash", "-c", "source activate wps && python setup.py develop"]

# Start WPS service on port 5000 on 0.0.0.0
EXPOSE 5000
ENTRYPOINT ["/bin/bash", "-c"]
CMD ["source activate wps && j2 /opt/wps/etc/magic-docker.cfg.j2 > /opt/wps/etc/magic-docker.cfg && exec c3s_magic_wps start -b 0.0.0.0 -c /opt/wps/etc/magic-docker.cfg"]

# docker-compose build
# docker-compose up
# http://localhost:5000/wps?request=GetCapabilities&service=WPS
# http://localhost:5000/wps?request=DescribeProcess&service=WPS&identifier=all&version=1.0.0
