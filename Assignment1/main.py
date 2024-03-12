from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.utils import secure_filename
from google.cloud import datastore
from google.cloud import storage


app = Flask(__name__)
app.secret_key = 'secret_key'
datastore_client = datastore.Client()

# Configure Google Cloud Storage client
storage_client = storage.Client()
bucket_name = 's3683022-storage'
bucket = storage_client.bucket(bucket_name)


query = datastore_client.query(kind='User')
users = list(query.fetch())
for user in users:
    print(user)
@app.route("/")
def root():
    if 'id' in session:
        for user_entity in users:
            if user_entity.get('id') == session['id']:
                print(user_entity.get('id'))
                username = user_entity.get('username')
                profile_picture_url = user_entity.get('profile_picture_url')
        return render_template('forum.html', username=username, profile_picture_url=profile_picture_url)
    return redirect(url_for('login'))

# @app.route("/")
# def root():
#     if 'id' in session:
#         # Fetch user information from datastore based on ID
#         user_id = session['id']
#         user_key = datastore_client.key('User', user_id)
#         user = datastore_client.get(user_key)

#         if user:
#             # Retrieve user information
#             id = user.get('id') 
#             username = user.get('username')
#             profile_picture_url = user.get('profile_picture_url')

#             return render_template('forum.html', username=username, profile_picture_url=profile_picture_url)
#         else:
#             # If user is not found, redirect to login
#             return redirect(url_for('login'))
#     else:
#         # If user is not logged in, redirect to login
#         return redirect(url_for('login'))


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


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)

