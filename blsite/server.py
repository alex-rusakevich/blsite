import hashlib
import os
import random

from belat.schemes import SCHEMES
from belat.fileprocessor import FileProcessor
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    after_this_request,
)
from werkzeug.utils import secure_filename
from pathlib import Path

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = os.urandom(24)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 5  # 5 mb max
app.config["URL_PREFIX"] = os.environ.get("URL_PREFIX", "")
app.config["UPLOAD_FOLDER"] = str(Path("./uploads").resolve())

Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = ["txt", "epub", "fb2"]
IMAGE_LIST = os.listdir(Path("static/img").resolve())


@app.route("/favicon.ico")
def favicon():
    print(os.path.join(app.root_path, "static"))

    return send_from_directory(
        os.path.join(app.root_path, "..", "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/", methods=["POST", "GET"])
def index_page():
    text_in = ""
    text_out = ""
    sel_scheme = 0
    sel_dir = 0

    if request.method == "POST":
        text_in = request.form.get("text_in")

        sel_scheme = int(request.form.get("scheme"))
        scheme_lat = list(SCHEMES.values())[sel_scheme]

        sel_dir = int(request.form.get("dir"))

        if sel_dir == 0:
            text_out = scheme_lat.cyr_to_lat(text_in)
        elif sel_dir == 1:
            text_out = scheme_lat.lat_to_cyr(text_in)

    return render_template(
        "index.html",
        schemes=tuple(SCHEMES.values()),
        text_in=text_in,
        text_out=text_out,
        sel_scheme=sel_scheme,
        sel_dir=sel_dir,
        static_prefix=app.config["URL_PREFIX"],
        image_list=IMAGE_LIST,
    )


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/file", methods=["POST", "GET"])
def file_page():
    sel_enc_in = "utf8"
    sel_enc_out = "utf8"
    sel_scheme = 0
    sel_dir = 0
    sel_file_type = 0

    download_link = ""

    err_msg = ""

    file_types = ["txt", "epub", "fb2"]
    encodings = ["utf8", "cp1251", "koi8-r"]

    if request.method == "POST":
        if "file" not in request.files:
            flash("Не атрымалася загрузіць файл. Праверце шляхі і тыпы файлаў")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("Вы не выбралі файл")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            file_in = request.files["file"]
            file_in.seek(0)
            extens = filename.rsplit(".", 1)[1].lower()
            file_in_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                str(
                    hashlib.md5(
                        (filename + str(random.randint(0, 255 ^ 2))).encode()
                    ).hexdigest()
                )
                + "."
                + extens,
            )
            file_in.seek(0)

            print(file_in_path)
            file_in.save(file_in_path)

            sel_scheme = int(request.form.get("scheme"))
            scheme_lat = list(SCHEMES.values())[sel_scheme]

            sel_dir = int(request.form.get("dir"))
            sel_enc_in = int(request.form.get("enc_in", 0))
            sel_enc_out = int(request.form.get("enc_out", 0))
            sel_file_type = int(request.form.get("file_type"))
            dir_work = ""

            if sel_dir == 0:
                dir_work = FileProcessor.CTL
            elif sel_dir == 1:
                dir_work = FileProcessor.LTC

            FileProcessor(
                file_in_path,
                file_in_path,
                encodings[sel_enc_in],
                encodings[sel_enc_out],
                dir_work,
                scheme_lat,
                file_types[sel_file_type],
            ).work()

            file_short_name = os.path.split(file_in_path)[-1]

            download_link = "/download/" + file_short_name

    return render_template(
        "file_work.html",
        schemes=tuple(SCHEMES.values()),
        file_types=file_types,
        encodings=encodings,
        download_link=download_link,
        err_msg=err_msg,
        sel_scheme=sel_scheme,
        sel_dir=sel_dir,
        sel_enc_in=sel_enc_in,
        sel_enc_out=sel_enc_out,
        sel_file_type=sel_file_type,
        static_prefix=app.config["URL_PREFIX"],
        image_list=IMAGE_LIST,
    )


@app.route("/download/<file_name>")
def download_file(file_name):
    @after_this_request
    def remove_file(response):
        try:
            os.remove(
                os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(file_name))
            )
        except Exception as error:
            app.logger.error("Error removing or closing downloaded file handle", error)
        return response

    return send_from_directory(app.config["UPLOAD_FOLDER"], secure_filename(file_name))


wsgi_app = app.wsgi_app
