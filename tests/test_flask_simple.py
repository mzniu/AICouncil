from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello World"

if __name__ == '__main__':
    print("Starting Flask...")
    app.run(port=5000, debug=False)
    print("Flask stopped")
