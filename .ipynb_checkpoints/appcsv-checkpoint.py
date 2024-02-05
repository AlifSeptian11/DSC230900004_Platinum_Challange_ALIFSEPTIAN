#import library
import re
import pandas as pd

from flask import Flask, jsonify, request

from flask import request
import flask
from flasgger import Swagger, LazyString, LazyJSONEncoder
from flasgger import swag_from

class CustomFlaskAppWithEncoder(Flask):
    json_provider_class = LazyJSONEncoder

#memanggil flask objek dan menyimpannya via variable app
app = CustomFlaskAppWithEncoder(__name__)

# menuliskan judul dan input host lazystring untuk random url
swagger_template = dict(
    info = {
        'title' : LazyString(lambda: "API Documentation for Processing and Cleansing"),
        'version' : LazyString(lambda: "1.0.0"),
        'description' : LazyString(lambda: "**Dokumentasi API untuk Processing dan Cleansing Data** \n API BY ALIF"),
    },
    host = LazyString(lambda: request.host)
)


# mendefinisikan endpoint 
swagger_config = {
    "headers" : [],
    "specs" : [
        {
            "endpoint": "docs",
            "route" : "/docs.json",
        }
    ],
    "static_url_path": "/flasgger_static",
    # "static_folder": "static",  # must be set by user
    "swagger_ui": True,
    "specs_route": "/docs/"
}


#membuat fungsi untuk text cleansing dari data upload 
swagger = Swagger(app, template=swagger_template, config = swagger_config)

 #remove_variabel tidak perlu  
def cleansing(text):
    text = re.sub(r'[^a-zA-Z0-9]', ' ', text)
    text = re.sub('.g\\n\\n', ' ', text) # menghilangkan '.g\\n\\n'
    text = re.sub('xf  x f x   x', ' ', text) #menghilangkan string xf
    text = re.sub('\xf0\x9f\x99\x88\xf0\x9f\x99\x88\xf0\x9f', ' ', text) #menghilangkan string \XF0 dst.
    text = re.sub('xe x x', ' ', text)
    text = re.sub('\n',' ',text) # menghilangkan '\n'
    text = re.sub('rt',' ',text) # menghilangkan retweet symbol
    text = re.sub('user',' ',text) # menghilangkan username
    text = re.sub('((www\.[^\s]+)|(https?://[^\s]+)|(http?://[^\s]+))',' ',text) # menghilangkan URL
    text = re.sub('  +', ' ', text) # Remove extra spaces 
    return text

#def clean_text(text):
#    text = re.sub('@[^\text]+', ' ', text) #menghapus username twitter
#    text = re.sub(r'(?:\@|http?\://|https?\://|www)\S+', '', text) #menghapus https dan http
#    text = re.sub('<.*?>', ' ', text) #mengganti karakter html dengan tanda petik
#    text = re.sub('[^a-zA-Z]', ' ', text) #mempertimbangkan huruf dan nama
#    text = re.sub('\n',' ',text) #mengganti line baru dengan spasi
#    text = text.lower() #mengubah ke huruf kecil
#    text = re.sub(r'\b[a-zA-Z]\b', ' ', text) #menghapus single char
#    text = ' '.join(text.split()) #memisahkan dan menggabungkan kata
#    text = re.sub(r'pic.twitter.com.[\w]+', '', text)  #menghapus link picture
#    text = re.sub('user',' ', text) #menghapus username
#    text = re.sub('RT',' ', text) #menghapus RT simbol
#    return text

#kamusalay = dict(zip(df_kamusalay['alay'], df_kamusalay['normal']))
#def alay_to_normal(text):
#    for word in kamusalay:
#        return ' '.join([kamusalay[word] if word in kamusalay else word for word in text.split(' ')])

#def text_cleansing(text):
#    text = clean_text(text)
#    text = alay_to_normal(text)
#    return text   

#@swag_from("docs/swagger_input.yml", methods=['POST'])
#@app.route('/input_text', methods=['POST'])
#def text_processing():
#    input_txt = str(request.form["input_teks"])
#    output_txt = text_cleansing(input_txt)
#
#    conn.execute('create table if not exists input_teks (input_text varchar(255), output_text varchar(255))')
#    query_txt = 'INSERT INTO input_teks (input_text, output_text) values (?,?)'
#    val = (input_txt, output_txt)
#    conn.execute(query_txt, val)
#    conn.commit()
#
#    return_txt = {"input":input_txt, "output": output_txt}
#    return jsonify (return_txt)

# membuat endpoint untuk text clean route text_processing.yml 
@swag_from("docs/text_processing.yml", methods = ['POST'])
@app.route('/text_processing', methods=['POST'])
def text():

    text = request.form['text']
    json_response = {
        'status_code': 200,
        'description': "Teks yang sudah diproses",
        'data' : re.sub(r'[^a-zA-Z0-9]', ' ', text),
    }
    response_data = jsonify(json_response)
    return response_data


#membuat endpoint untuk upload file
@swag_from("docs/csv_processing.yml", methods = ['POST'])
@app.route('/upload', methods=['POST'])
def file_processing():
    
    file_input = request.files['file']

    #readcsvfile
    df=pd.read_csv(file_input, encoding='latin1')

    df_tweet = pd.DataFrame(df[['Tweet']])
    

    #apply cleansing function from data 'cleansing'
    df['Tweet'] = df['Tweet'].apply(cleansing)

    #save data
    result_file_path = 'data_afterpreprocessing.csv'
    df.to_csv(result_file_path, index=False, encoding='utf-8')

    #apply cleansing

    json_response = {
        'status_code': 200,
        'description': "Teks cleansing",
        'data' : 'sukses upload',
        'result_file_path': result_file_path #menambahkan path file hasil cleansing
    }    

    response_data = jsonify(json_response)
    return response_data

if __name__ == '__main__':
    app.run()





