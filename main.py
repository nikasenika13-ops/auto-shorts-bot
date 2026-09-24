import os
import asyncio
import requests
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

def get_trending_data(youtube):
    print("Fetching trending videos...")
    request = youtube.videos().list(
        part="snippet,statistics",
        chart="mostPopular",
        regionCode="US", 
        maxResults=5
    )
    response = request.execute()
    
    top_video = response['items'][0]['snippet']
    title = top_video['title']
    
    tags = top_video.get('tags', [])
    hashtags = [f"#{tag.replace(' ', '')}" for tag in tags[:3]]
    if len(hashtags) < 3:
        hashtags.extend(["#trending", "#viral", "#shorts"][:3 - len(hashtags)])
        
    category_id = top_video.get('categoryId', '24')
    
    return title, hashtags, category_id

def download_background_video(query="abstract background"):
    print("Downloading background video from Pexels...")
    api_key = os.environ.get("PEXELS_API_KEY")
    headers = {"Authorization": api_key}
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=1"
    
    response = requests.get(url, headers=headers).json()
    if 'videos' not in response or not response['videos']:
        raise Exception("No video found on Pexels.")
        
    video_url = response['videos'][0]['video_files'][0]['link']
    
    video_data = requests.get(video_url).content
    bg_filename = "background.mp4"
    with open(bg_filename, "wb") as f:
        f.write(video_data)
        
    return bg_filename

async def generate_voice(text, filename="voice.mp3"):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(filename)
    return filename

def generate_short(trending_title):
    print("Generating Short...")
    
    script = f"Trending now! Everyone is watching: {trending_title}. Make sure you don't miss out on the most popular video today!"
    asyncio.run(generate_voice(script))
    
    bg_path = download_background_video(query="abstract motion")
    
    background = VideoFileClip(bg_path).resize((1080, 1920))
    audio = AudioFileClip("voice.mp3")
    
    duration = min(audio.duration + 1, background.duration)
    background = background.subclip(0, duration)
    
    text_clip = TextClip(
        trending_title,
        fontsize=60,
        color='white',
        font='Liberation-Sans-Bold', 
        method='caption',
        size=(900, None),
        align='center'
    ).set_position('center').set_duration(duration)
    
    final = CompositeVideoClip([background, text_clip]).set_audio(audio)
    
    output = "short.mp4"
    final.write_videofile(output, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast")
    
    background.close()
    audio.close()
    return output

def upload_video(youtube, video_file, title, hashtags, category_id):
    print("Uploading to YouTube...")
    
    hashtag_str = " ".join(hashtags)
    max_title_len = 95 - len(hashtag_str)
    short_title = (title[:max_title_len] + "...") if len(title) > max_title_len else title
    full_title = f"{short_title} {hashtag_str}"
    
    body = {
        "snippet": {
            "title": full_title,
            "description": f"Trending topic overview: {title}\n\n{hashtag_str}",
            "tags": [h.strip('#') for h in hashtags],
            "categoryId": category_id
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

if __name__ == "__main__":
    try:
        youtube = get_youtube_service()
        title, hashtags, category_id = get_trending_data(youtube)
        video_path = generate_short(title)
        upload_video(youtube, video_path, title, hashtags, category_id)
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
        
