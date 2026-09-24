import os
import asyncio
import datetime
from moviepy.editor import *
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import edge_tts
def get_youtube_service():
creds = Credentials(
token=None,
refresh_token=os.environ["YT_REFRESH_TOKEN"],
token_uri="https://oauth2.googleapis.com/token",
client_id=os.environ["YT_CLIENT_ID"],
client_secret=os.environ["YT_CLIENT_SECRET"],
scopes=[
"https://www.googleapis.com/auth/youtube.upload",
"https://www.googleapis.com/auth/youtube.readonly"
]
)
if not creds.valid:
creds.refresh(Request())
return build("youtube", "v3", credentials=creds)
async def generate_voice(text, filename="voice.mp3"):
communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
await communicate.save(filename)
return filename
def generate_short():
print("Generating Short...")
# Simple educational script (you can improve this later)
script = "Did you know? The Western Ghats in Maharashtra block moisture from the Arabian Sea and create heavy rainfall on the western side. This is why places like Mahabaleshwar get so much rain!"
# Generate voice
asyncio.run(generate_voice(script))
# Create vertical video
width, height = 1080, 1920
duration = 25  # seconds
background = ColorClip(size=(width, height), color=(20, 20, 40)).set_duration(duration)
text_clip = TextClip(
"Maharashtra Geography\nWestern Ghats Fact",
fontsize=70,
color='white',
font='Arial-Bold',
method='caption',
size=(900, None),
align='center'
).set_position('center').set_duration(duration)
audio = AudioFileClip("voice.mp3")
final = CompositeVideoClip([background, text_clip]).set_audio(audio)
final = final.set_duration(min(duration, audio.duration))
output = "short.mp4"
final.write_videofile(output, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast")
return output
def upload_video(youtube, video_file):
print("Uploading to YouTube...")
title = "Maharashtra Geography Fact #Shorts"
description = "Daily geography facts for students! #geography #maharashtra #class10 #shorts #education"
body = {
"snippet": {
"title": title,
"description": description,
"tags": ["education", "geography", "maharashtra", "shorts", "class10"],
"categoryId": "27"
},
"status": {
"privacyStatus": "public",
"selfDeclaredMadeForKids": False
}
}
media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
response = None
while response is None:
status, response = request.next_chunk()
if status:
print(f"Uploaded {int(status.progress() * 100)}%")
print(f"Upload complete! Video ID: {response['id']}")
return response['id']
if name == "main":
try:
video_path = generate_short()
youtube = get_youtube_service()
upload_video(youtube, video_path)
print("Success!")
except Exception as e:
print(f"Error: {e}")
exit(1)

