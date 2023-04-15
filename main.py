from flask import Flask, request, redirect
import sqlite3
import string
import random
from werkzeug.local import Local

app = Flask(__name__)

# Create thread-local storage for database connection and cursor
tls = Local()

# Function to create a new database connection
def get_db():
    if not hasattr(tls, 'db'):
        tls.db = sqlite3.connect('urls.db')
        tls.db.row_factory = sqlite3.Row
    return tls.db

# Function to create a new database cursor
def get_cursor():
    if not hasattr(tls, 'cursor'):
        tls.cursor = get_db().cursor()
    return tls.cursor

# Create the URLs table if it doesn't exist
with get_db() as conn:
    cursor = get_cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            long_url TEXT NOT NULL,
            short_id TEXT NOT NULL
        )
    ''')
    conn.commit()

# Define the characters for the base62 encoding
CHARS = string.ascii_letters + string.digits
BASE = len(CHARS)

@app.route('/')
def home():
    return '''
    <form method="post" action="/shorten">
        <label for="long_url">Enter Long URL:</label><br>
        <input type="text" id="long_url" name="long_url" required><br>
        <input type="submit" value="Shorten">
    </form>
    '''


@app.route('/shorten', methods=['POST'])
def shorten():
    long_url = request.form['long_url']

    # Check if the long URL already exists in the database
    with get_db() as conn:
        cursor = get_cursor()
        cursor.execute('SELECT short_id FROM urls WHERE long_url=?', (long_url,))
        existing_row = cursor.fetchone()
        if existing_row:
            short_id = existing_row[0]
        else:
            # Generate a unique short ID using base62 encoding
            while True:
                short_id = ''.join(random.choices(CHARS, k=6))
                cursor.execute('SELECT id FROM urls WHERE short_id=?', (short_id,))
                existing_row = cursor.fetchone()
                if not existing_row:
                    break

            # Insert the new mapping into the database
            cursor.execute('INSERT INTO urls (long_url, short_id) VALUES (?, ?)', (long_url, short_id))
            conn.commit()

    # Generate the short URL
    short_url = request.host_url + short_id

    return f'''
    Short URL: <a href="{short_url}" target="_blank">{short_url}</a><br>
    Long URL: {long_url}
    '''


@app.route('/<short_id>')
def redirect_url(short_id):
    # Retrieve the long URL from the database based on the short ID
    with get_db() as conn:
        cursor = get_cursor()
        cursor.execute('SELECT long_url FROM urls WHERE short_id=?', (short_id,))
        row = cursor.fetchone()
        if row:
            long_url = row[0]
            return redirect(long_url)
        else:
            return 'Invalid URL'


if __name__ == "__main__":
    app.run(debug=True)
