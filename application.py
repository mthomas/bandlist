import json
from flask import Flask, request, redirect, g, render_template
import requests
import base64
import urllib
import os
import spotipy
import xmltodict

app = Flask(__name__)

#  Client Keys
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)


# Server-side Parameters
CLIENT_SIDE_URL = "http://127.0.0.1"
PORT = 5005
REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)
SCOPE = "playlist-modify-public playlist-modify-private playlist-read-private streaming user-follow-modify user-follow-read user-library-read user-library-modify user-read-private user-read-birthdate user-read-email"
STATE = ""
SHOW_DIALOG_bool = True
SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()


auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    # "state": STATE,
    # "show_dialog": SHOW_DIALOG_str,
    "client_id": CLIENT_ID
}

@app.route("/")
def index():
    # Auth Step 1: Authorization
    url_args = "&".join(["{}={}".format(key,urllib.quote(val)) for key,val in auth_query_parameters.iteritems()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    return redirect(auth_url)


@app.route("/callback/q")
def callback():
    # Auth Step 4: Requests refresh and access tokens
    auth_token = request.args['code']
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": REDIRECT_URI
    }
    base64encoded = base64.b64encode("{}:{}".format(CLIENT_ID, CLIENT_SECRET))
    headers = {"Authorization": "Basic {}".format(base64encoded)}
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)

    # Auth Step 5: Tokens are Returned to Application
    response_data = json.loads(post_request.text)
    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]
    token_type = response_data["token_type"]
    expires_in = response_data["expires_in"]

    return redirect("/home?access_token=" + access_token)


@app.route("/home")
def home():
    token = request.args.get("access_token")
    sp = spotipy.Spotify(auth=token)
    me = sp.me()
    print me

    ##make playlist
    playlist = sp.user_playlist_create(me["id"], "TOP TRACKS for March 14", True)
    print playlist

    ##find events in my area
    uri = 'http://api.seatgeek.com/2/events?geoip=11249&datetime_utc.gte=2015-03-14&datetime_utc.lte=2015-03-21&taxonomies.name=concert&per_page=1000'
    response = requests.get(uri)
    data = response.json()

    print data["meta"]
    for event in data["events"]:
        for performer in event["performers"]:
            artist = sp.search(performer["name"], limit=1, offset=0, type='artist')['artists']['items']
            if artist:
                artist = artist[0]
                top_tracks = sp.artist_top_tracks(artist["uri"])["tracks"]
                if top_tracks:
                    sp.user_playlist_add_tracks(me["id"], playlist["id"], [t["uri"] for t in top_tracks][:2])

                print "added two tracks for " + performer["name"]
            else:
                print "CANT FIND artists FOR " + performer["name"]

    return render_template("index.html",results=[])

if __name__ == "__main__":
    app.run(debug=True,port=PORT)