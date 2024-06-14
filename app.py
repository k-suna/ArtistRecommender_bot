from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage, BubbleContainer, ImageComponent, BoxComponent, TextComponent, CarouselContainer
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

def get_artist_uri(name):
    results = sp.search(q='artist:' + name, type='artist')
    if results['artists']['items']:
        artist = results['artists']['items'][0]
        uri = artist['uri']
        return uri
    else:
        return None

def get_related_artist_info(uri):
    related_artists = sp.artist_related_artists(uri)['artists']
    return related_artists

def get_top_artists(artist_name):
    uri = get_artist_uri(artist_name)
    if not uri:
        return None, None

    related_artists = get_related_artist_info(uri)
    if not related_artists:
        return [], {}

    top_artists_list = [artist['name'] for artist in related_artists[:10]]
    top_tracks_dict = {}

    for artist in top_artists_list:
        uri = get_artist_uri(artist)
        if uri:
            top_tracks = sp.artist_top_tracks(uri)['tracks']
            top_tracks_info = []
            for track in top_tracks[:6]:
                track_info = {
                    'name': track['name'],
                    'release_date': track['album']['release_date'].split('-')[0],
                    'image_url': track['album']['images'][0]['url']
                }
                top_tracks_info.append(track_info)
            top_tracks_dict[artist] = top_tracks_info

    return top_artists_list, top_tracks_dict

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Check your channel secret and access token.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    artist_name = event.message.text.strip()
    
    # ユーザの入力が「開始」の場合
    if artist_name == "開始":
        # 歓迎メッセージを返す
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="Welcome to Artists Recommender\n"
            "あなたの好きなアーティストと関連度(*)の高いアーティストを10人推薦します。\n"
            "アーティスト名をローマ字で入力して下さい。\n\n"
            "(例) 嵐 >> ARASHI\n"
            "    平井堅 >> Ken Hirai")
        )
        return

    top_artists_list, top_tracks_dict = get_top_artists(artist_name)
    if not top_artists_list:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="アーティストが見つかりません。別の名前を試してください。")
        )
        return

    bubbles = []
    for i, artist in enumerate(top_artists_list):
        rank = i + 1
        if rank == 1:
            rank_str = f"{rank}st"
        elif rank == 2:
            rank_str = f"{rank}nd"
        elif rank == 3:
            rank_str = f"{rank}rd"
        else:
            rank_str = f"{rank}th"

        track_bubbles = []
        for track in top_tracks_dict[artist]:
            track_bubble = BoxComponent(
                layout="vertical",
                contents=[
                    ImageComponent(url=track['image_url'], size="full", aspect_ratio="1:1", aspect_mode="cover"),
                    TextComponent(text=f"{track['name']} ({track['release_date']})", size="sm", wrap=True)
                ]
            )
            track_bubbles.append(track_bubble)

        artist_bubble = BubbleContainer(
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(text=f"{rank_str}. {artist}", weight="bold", size="xl", margin="md"),
                    *track_bubbles
                ]
            )
        )
        bubbles.append(artist_bubble)

    carousel = CarouselContainer(contents=bubbles)
    flex_message = FlexSendMessage(
        alt_text=f"{artist_name}と関連度の高いアーティスト",
        contents=carousel
    )

    line_bot_api.reply_message(
        event.reply_token,
        flex_message
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)

