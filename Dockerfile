FROM ghcr.io/qubitdimensions/fizilion:dev
RUN mkdir /Fizilion && chmod 777 /Fizilion && git clone https://github.com/DarkGod14/Fizilion -b main /Fizilion
WORKDIR /Fizilion
CMD ["python3","-m","userbot"]
