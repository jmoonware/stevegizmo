from flask import Flask, render_template, request, redirect, url_for
import urllib.parse

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        text = request.form['text']
        hex_string = text.encode().hex()
        # Append the hex string to a specified URL
        appended_url = "https://XXXcore.rock7.com/rockblock/MT?imei=300434068367990&data=" + urllib.parse.quote(hex_string)
        appended_url = appended_url + "&username=someone@gmail.com&password=XXXXXX"
        return redirect(appended_url)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
