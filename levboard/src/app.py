from flask import session, request, url_for, redirect
from .app_factory import app

from .storage import Process
from .charts import create_song_chart


@app.route('/')
def index():
    if 'username' in session:
        return redirect(f'/home/{session["username"]}')
    return redirect('/login')


@app.route('/home/<username>')
def user_home(username: str):
    if session.get('username') == username:
        return f'welcome to your home page :)'
    return f'username home for {username}'


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    return """
        <form method="post">
            <p><input type=text name=username>
            <p><input type=submit value=Login>
        </form>
    """


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/config')
def display_config():
    with Process(session) as process:
        return process.config.to_dict()


@app.route('/chart')
def create_charts():
    if 'username' in session:
        with Process(session) as process:
            return {"rows": create_song_chart(process)}
    else:
        return 'You need to sign in', 400


"""
@app.route('/config', methods=['GET', 'POST'])
def change_settings():
    if request.method == 'POST':
        config = update_config_from_form(request.form)
        update_session_from_config(config, session)
        return redirect(url_for('index'))
    return '''
        <form method="post">
            <p><input type=text name=username>
            <p><input type=submit value=Submit>
        </form>
    '''
"""