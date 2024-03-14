from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.utils import secure_filename
from google.cloud import datastore
from google.cloud import storage
from datetime import datetime


app = Flask(__name__)
app.secret_key = 'secret_key'
datastore_client = datastore.Client()

# Configure Google Cloud Storage client
storage_client = storage.Client()
bucket_name = 's3683022-storage'
bucket = storage_client.bucket(bucket_name)


user_query = datastore_client.query(kind='User')
users = list(user_query.fetch())

messages_query = datastore_client.query(kind='Message')
messages_query.order = ['-posted_date']  # Order messages by descending posted_date
messages = list(messages_query.fetch(limit=10))

@app.route("/")
def root():
    # If user is logged in ID will be saved in session, otherwise redirect to login page
    if 'id' in session:
        for user_entity in users:
            if user_entity.get('id') == session['id']:
                print(user_entity.get('id'))
                username = user_entity.get('username')
                profile_picture_url = user_entity.get('profile_picture_url')
        # Fetch username and profile picture for each message's user_id
        for message in messages:
            user_id = message.get('user_id')
            username, profile_picture_url = get_user_info(user_id)
            if username is not None and profile_picture_url is not None:
                message['username'] = username
                message['user_profile_picture_url'] = profile_picture_url
                # Convert posted_date to datetime object if it's a string
                if isinstance(message['posted_date'], str):
                    message['posted_date'] = datetime.strptime(message['posted_date'], "%Y-%m-%d %H:%M:%S")

                # Format posted_date
                message['posted_date'] = message['posted_date'].strftime("%Y-%m-%d %H:%M:%S")

        return render_template('forum.html', username=username, profile_picture_url=profile_picture_url, messages=messages)
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        id = request.form['id']
        password = request.form['password']
        print("Login username: ", id, "Login password: ", password)
        
        query = datastore_client.query(kind='User')
        users = query.fetch() 
        print("User entity Username: ", users)
        if users:
            for user in users:
                if user['id'] == id and user['password'] == password:
                    session['id'] = id
                    print('login')
                    print(session['id'])
                    return redirect(url_for('root'))

            # If the loop finishes without finding a matching user, show error
            return render_template('login.html', error='Invalid id or password')
    # If it's a GET request, render the login page
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Retrieve form data
        id = request.form['id']
        username = request.form['username']
        password = request.form['password']
        profile_picture = request.files['profile_picture']

        # Check if the user already exists in the datastore
        query = datastore_client.query(kind='User')
        existing_users = query.fetch()

        if existing_users:
            # Check if the entered username or ID already exists
            for user_entity in existing_users:
                if user_entity['id'] == id:
                    # ID already exists, render the registration page with error message
                    return render_template("registration.html", message="ID already exists")
                elif user_entity['username'] == username:
                    # Username already exists, render the registration page with error message
                    return render_template("registration.html", message="Username already exists")

        # Create a new entity for the user
        user_key = datastore_client.key('User')
        user = datastore.Entity(key=user_key)
        user.update({
            'id': id,
            'username': username,
            'password': password
        })

        # Save the user entity to Cloud Datastore
        datastore_client.put(user)

        # Store the profile picture in Google Cloud Storage
        if profile_picture:
            # Generate a unique filename for the profile picture
            filename = secure_filename(profile_picture.filename)
            blob = bucket.blob(filename)
            blob.upload_from_file(profile_picture)
            user['profile_picture_url'] = blob.public_url

            # Update the user entity in Cloud Datastore with the profile picture URL
            datastore_client.put(user)

        # Redirect to a success page or login page
        return redirect(url_for('login'))

    else:
        return render_template("registration.html")

@app.route('/forum', methods=['GET', 'POST'])
def message():
    # Fetch messages from datastore
    query = datastore_client.query(kind='Message')
    messages = list(query.fetch())

    # Fetch username and profile picture for each message's user_id
    for message in messages:
        user_id = message.get('user_id')
        username, profile_picture_url = get_user_info(user_id)
        if username is not None and profile_picture_url is not None:
            message['username'] = username
            message['user_profile_picture_url'] = profile_picture_url
            message['posted_date'] = message['posted_date'].strftime("%Y-%m-%d %H:%M:%S")

    if request.method == 'POST':
        # Retrieve message data from the form
        subject = request.form['subject']
        message_text = request.form['message-text']
        image = request.files['image'] if 'image' in request.files else None

        # Save the message data to Cloud Datastore
        message_key = datastore_client.key('Message')
        message = datastore.Entity(key=message_key)
        message.update({
            'subject': subject,
            'text': message_text,
            'user_id': session.get('id'), 
            'posted_date': datetime.now()
        })
        datastore_client.put(message)

        # Store the image in Google Cloud Storage if provided
        if image:
            filename = secure_filename(image.filename)
            blob = bucket.blob(filename)
            blob.upload_from_file(image)
            message['image_url'] = blob.public_url

            # Update the message entity in Cloud Datastore with the image URL
            datastore_client.put(message)

        # Redirect back to the forum page
        return redirect(url_for('root'))
    
    # Render the forum page with the updated messages
    return render_template('forum.html', messages=messages)


def get_user_info(user_id):
    
    # Query the datastore for the user with the given user_id
    user_query = datastore_client.query(kind='User')
    user_query.add_filter('id', '=', user_id)
    print(user_id)
    user_entities = list(user_query.fetch(limit=1))
    print(user_entities)
    if user_entities:
        user = user_entities[0]
        username = user.get('username')
        print(username)
        profile_picture_url = user.get('profile_picture_url')
        print(profile_picture_url)
        return username, profile_picture_url
    else:
        return None, None

@app.route('/logout')
def logout():
    session.pop('id', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)

