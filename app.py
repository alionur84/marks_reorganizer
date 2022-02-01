from flask import Flask, render_template, flash, request, redirect, url_for, session, send_from_directory, abort, send_file
import os
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
import uuid
import io
from xls_creator import *



app=Flask(__name__)

app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config["UPLOADS"] = os.environ['UPLOADS']

app.config["ALLOWED_EXTENSIONS"] = ["XLSX", "XLS", "CSV"]
app.config['DOWNLOAD_FOLDER'] = os.environ['DOWNLOADS']
MAX_CONTENT_LENGTH = 1500000



def allowed_ext(filename):

    if not "." in filename:
        return False

    ext = filename.rsplit(".", 1)[1]

    if ext.upper() in app.config["ALLOWED_EXTENSIONS"]:
        return True
    else:
        return False

def check_size(file):
    pos = file.tell()
    file.seek(0, 2)  #seek to end
    size = file.tell()
    file.seek(pos)
    if size <= MAX_CONTENT_LENGTH:
        return True
    else:
        return False


@app.route("/")
@app.route("/home")
def home():

    session.pop('user_id', default=None)
    session.pop('unknown_students', default=None)
    session.pop('corrected_ids', default=None)
    session.pop('attended_count', default=None)
    session.pop('mean_mark', default=None)
    session.pop('enrolled_count', default=None)
    session.pop('std_dev', default=None)
    user_id = str(uuid.uuid4())
    session['user_id'] = user_id
    session['unknown_students'] = {}
    session['corrected_ids'] = {}
    session['attended_count'] = str(0)
    session['mean_mark'] = str(0)
    session['enrolled_count'] = str(0)
    session['std_dev'] = str(0)

    return render_template("index.html", title='Home')


@app.route("/sessioner")
def check():
    return render_template("session.html", user_id=session['user_id'], title='Session ID')


# upload file
@app.route("/upload-file", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        if request.files:

            
            not_listesi = request.files["not_listesi"]
            orgun_sablon = request.files["orgun_sablon"]
            IO_sablon = request.files["IO_sablon"]
            
            if not_listesi.filename == "" or orgun_sablon.filename == "" or IO_sablon.filename == "":
                flash('Eksik dosya yüklenmiş ya da dosya adları desteklenmiyor. Lütfen dosyaları ve dosya adlarını kontrol ediniz!!', 'danger')
                session.pop('user_id', default=None)
                return redirect(url_for('home'))

            if check_size(not_listesi) and check_size(orgun_sablon) and check_size(IO_sablon):

                if allowed_ext(not_listesi.filename) and allowed_ext(orgun_sablon.filename) and allowed_ext(IO_sablon.filename):
                    not_listesi_fname = secure_filename(not_listesi.filename)
                    orgun_sablon_fname = secure_filename(orgun_sablon.filename)
                    IO_sablon_fname = secure_filename(IO_sablon.filename)

                    not_listesi_path = os.path.join(app.config["UPLOADS"], session['user_id'] + "_" + not_listesi_fname)
                    orgun_sablon_path = os.path.join(app.config["UPLOADS"], session['user_id'] + "_" + orgun_sablon_fname)
                    IO_sablon_path = os.path.join(app.config["UPLOADS"], session['user_id'] + "_" + IO_sablon_fname)


                    not_listesi.save(not_listesi_path)
                    orgun_sablon.save(orgun_sablon_path)
                    IO_sablon.save(IO_sablon_path)

                    # files uploaded are different
                    # some had headers some dont
                    # so they have to be handled differently
                    # if no header and null rows than move to next try except

                    try:
                        
                        df = file_uploader(not_listesi_path)
                        
                        df = header_dropper(df)
                                            
                        
                        result = clean_na(df)
                        session['attended_count'] = str(result['attended_count'])
                        session['mean_mark'] = str(result['mean_mark'])
                        session['std_dev'] = str(result['std_dev'])
                        
                        
                        df = convert_datatypes(result['df'])
                        

                        template_result = template_concat(orgun_sablon_path, IO_sablon_path)
                        session['enrolled_count'] = str(template_result['enrolled_count'])
                        
                        
                        id_corrected = id_correct(df, template_result['template_df'])
                        df = id_corrected[0]
                        unknown_students = id_corrected[1]
                        corrected_ids = id_corrected[2]
                        
                                         
                        
                        for i in unknown_students.index:
                            session['unknown_students'][str(unknown_students.loc[i, ['TCKimlikNo']][0])] = [str(unknown_students.loc[i, ['Adı ']][0]), str(unknown_students.loc[i, ['Soyadı']][0]), int(unknown_students.loc[i, [unknown_students.columns[-1]]][0])]

                        for z in corrected_ids.index:
                            session['corrected_ids'][str(corrected_ids.loc[z, ['TCKimlikNo']][0])] = [str(corrected_ids.loc[z, ['Adı ']][0]), str(corrected_ids.loc[z, ['Soyadı']][0]), int(corrected_ids.loc[z, [corrected_ids.columns[-2]]][0]), int(corrected_ids.loc[z, [corrected_ids.columns[-1]]][0]) ]

                        
                                                
                        final_file = finalizer(df, template_result['template_df'])
                        final_file[0].to_excel(os.path.join(app.config['DOWNLOAD_FOLDER'], session['user_id'] + "_" + "orgun.xlsx" ), index=False)
                        final_file[1].to_excel(os.path.join(app.config['DOWNLOAD_FOLDER'], session['user_id'] + "_" + "io.xlsx" ), index=False)
                        
                                                
                        filename_orgun = session['user_id'] + "_" + "orgun.xlsx"
                        filename_io = session['user_id'] + "_" + "io.xlsx"
                        
                        os.remove(not_listesi_path)
                        os.remove(orgun_sablon_path)
                        os.remove(IO_sablon_path)

                                                
                        flash('Dosyalar başarıyla yüklendi', 'success')
                        return redirect(url_for('download_page', filename1=filename_orgun, filename2=filename_io))

                    except:

                        try:
                            df1 = file_uploader(not_listesi_path)
                            
                            result = stats(df1)
                            session['attended_count'] = str(result['attended_count'])
                            session['mean_mark'] = str(result['mean_mark'])
                            session['std_dev'] = str(result['std_dev'])
                            
                            df1 = convert_datatypes(df1)
                            
                            template_result = template_concat(orgun_sablon_path, IO_sablon_path)
                            session['enrolled_count'] = str(template_result['enrolled_count'])
                            
                            id_corrected = id_correct(df1, template_result['template_df'])
                            df1 = id_corrected[0]
                            unknown_students = id_corrected[1]
                            corrected_ids = id_corrected[2]
                                                        
                            for i in unknown_students.index:
                                session['unknown_students'][str(unknown_students.loc[i, ['TCKimlikNo']][0])] = [str(unknown_students.loc[i, ['Adı ']][0]), str(unknown_students.loc[i, ['Soyadı']][0]), int(unknown_students.loc[i, [unknown_students.columns[-1]]][0])]

                            for z in corrected_ids.index:
                                session['corrected_ids'][str(corrected_ids.loc[z, ['TCKimlikNo']][0])] = [str(corrected_ids.loc[z, ['Adı ']][0]), str(corrected_ids.loc[z, ['Soyadı']][0]), int(corrected_ids.loc[z, [corrected_ids.columns[-2]]][0]), int(corrected_ids.loc[z, [corrected_ids.columns[-1]]][0]) ]

                                                
                            final_file = finalizer(df1, template_result['template_df'])
                            final_file[0].to_excel(os.path.join(app.config['DOWNLOAD_FOLDER'], session['user_id'] + "_" + "orgun.xlsx" ), index=False)
                            final_file[1].to_excel(os.path.join(app.config['DOWNLOAD_FOLDER'], session['user_id'] + "_" + "io.xlsx" ), index=False)
                            
                        
                            filename_orgun = session['user_id'] + "_" + "orgun.xlsx"
                            filename_io = session['user_id'] + "_" + "io.xlsx"
                            
                            os.remove(not_listesi_path)
                            os.remove(orgun_sablon_path)
                            os.remove(IO_sablon_path)
                            
                            flash('Dosyalar başarıyla yüklendi', 'success')
                            return redirect(url_for('download_page', filename1=filename_orgun, filename2=filename_io))

                        except:
                            flash('Lütfen yüklediğiniz dosyaların orijinal şablonlar ve optik okuyucu dosyası olduğundan emin olunuz!!', 'danger')
                            abort(404)
                else:
                    session.pop('user_id', default=None)
                    flash('Dosya uzantıları xls, xlsx ya da csv olmalıdır!!', 'danger')
                    return redirect(url_for('home'))
            else:
                session.pop('user_id', default=None)
                flash("Dosya boyutu 1.5 megabyte'dan yüksek olamaz!!", "danger")
                return redirect(url_for('home'))

    return render_template('upload_file.html', title='Upload File')


@app.route('/downloads/<filename1>+<filename2>')
def download_page(filename1, filename2):

    filename1 = filename1
    filename2 = filename2

    if session['user_id'] in filename1 and session['user_id'] in filename2:
        try:
            unknown_students = session['unknown_students']
            corrected_ids = session['corrected_ids']
            attended_count = session['attended_count']
            mean_mark = session['mean_mark']
            std_dev = session['std_dev']
            enrolled_count = session['enrolled_count']
            

            if len(unknown_students)>0:
                unknowns = True
            else:
                unknowns = False

            if len(corrected_ids)>0:
                corrected = True
            else:
                corrected = False


            return render_template("downloads.html", filename1=filename1, filename2=filename2, 
                unknown_students=unknown_students, unknowns=unknowns, corrected_ids=corrected_ids,
                corrected=corrected, attended_count=attended_count,
                mean_mark=mean_mark, std_dev=std_dev,
                enrolled_count=enrolled_count, title='Download your files')
        except:
            flash('Bir sorun oluştu, lütfen tekrar deneyiniz!!', 'danger')
            abort(404)
    else:
        flash('Bir sorun oluştu, lütfen tekrar deneyiniz!!', 'danger')
        abort(404)

@app.route('/downloads/<path:filename>', methods=['GET', 'POST'])
def downloads(filename):
    try:
        # Appending app path to upload folder path within app root folder
        download_dir = app.config['DOWNLOAD_FOLDER']
        path_to_file = os.path.join(download_dir, filename)
        
        # this part writes the file to memory in order to delete it after sending
        return_data = io.BytesIO()
        with open(path_to_file, 'rb') as fo:
            return_data.write(fo.read())
        # (after writing, cursor will be at last byte, so move it to start)
        return_data.seek(0)

        os.remove(path_to_file)

        return send_file(return_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         attachment_filename=session['user_id']+"_"+"download.xlsx")
    except:
        flash('Bir sorun oluştu, lütfen tekrar deneyiniz!!', 'danger')
        abort(404)
    # Returning file from appended path
    #return send_from_directory(download_dir, filename, as_attachment=True)


#invalid url
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

#internal server error
@app.errorhandler(500)
def page_not_found(e):
    return render_template("500.html"), 500


if __name__ == '__main__':
    app.run(debug=True)