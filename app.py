import os
import random
import requests
from flask import Flask, render_template

app = Flask(__name__)

CAT_API_URL = "https://api.thecatapi.com/v1/images/search"

@app.route("/")
def index():
    response = requests.get(CAT_API_URL)
    cat_data = response.json()
    cat_image_url = cat_data[0]['url']

    return render_template("index.html", cat_image_url=cat_image_url)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)