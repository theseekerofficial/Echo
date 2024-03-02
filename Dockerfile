FROM python:3.10-slim

RUN apt-get update && apt-get install -y git ffmpeg

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8000

#Run the bot
CMD ["python3", "bot.py"]
