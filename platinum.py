#import library
from flask import Flask, jsonify, request
from flasgger import Swagger, LazyString, LazyJSONEncoder, swag_from
import pandas as pd
import pickle, re
import sqlite3 as sq
import numpy as np
from keras.preprocessing.text import Tokenizer
from keras.models import load_model
from keras.preprocessing.sequence import pad_sequences

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
swagger = Swagger(app, template=swagger_template, config = swagger_config)

max_features = 5000
tokenizer = Tokenizer(num_words=max_features, split=' ', lower=True)
sentiment = ['negative', 'neutral', 'positive']

def lowercase(s):
    return s.lower()

def punctuation(s):
    s = re.sub(r'(?:\@|http?\://|https?\://|www)\S+', '', s) #menghapus https dan http
    s = re.sub('<.*?>', ' ', s) #mengganti karakter html dengan tanda petik
    s = re.sub('[^0-9a-zA-Z]+', ' ', s) #menghilangkan semua karakter yang bukan huruf atau angka dan menggantinya dengan spasi.
    s = re.sub('\n',' ',s) #mengganti line baru dengan spasi
    s = re.sub(r':', ' ', s) #menggantikan karakter : dengan spasi 
    s = re.sub('gue','saya', s) # Mengganti kata "gue" dengan kata "saya"
    s = re.sub(r'\b[a-zA-Z]\b', ' ', s) #menghapus single char
    s = ' '.join(s.split()) #memisahkan dan menggabungkan kata
    s = s.strip() #menghilangkan whitespace di awal dan di akhir teks
    s = re.sub(r'pic.twitter.com.[\w]+', '', s) #menghapus link picture
    s = re.sub(r'\buser\b',' ', s) #menghapus kata 'user'
    s = re.sub(r'\brt\b',' ', s) #menghapus awalan rt
    s = re.sub('RT',' ', s) #menghapus RT simbol
    s = re.sub(r'‚Ä¶', '', s)
    
    return s

def alay_to_normal(s):
    for word in kamusalay:
        return ' '.join([kamusalay[word] if word in kamusalay else word for word in s.split(' ')])
    
def cleansing(sent):
    string = lowercase(sent)
    string = punctuation(string)
    string = alay_to_normal(string)

    return string

conn = sq.connect('database_pl.db', check_same_thread = False)
df_kamusalay = pd.read_sql_query('SELECT * FROM kamusalay', conn)
kamusalay = dict(zip(df_kamusalay['alay'], df_kamusalay['normal']))

# load hasil feature extraction dari Neural Network
file_NN = open("Neural Network/tfidf_vect.p",'rb')
tfidf_vect = pickle.load(file_NN)
model_file_from_nn = pickle.load(open('Neural Network/model_neuralnetwork.p', 'rb'))
file_NN.close()

def predict_sentiment_neural_network(text):
    cleaned_text = cleansing(text)
    input_text = [cleaned_text]

    input_vector = tfidf_vect.transform(input_text)
    sentiment_label = model_file_from_nn.predict(input_vector)[0]

    return sentiment_label

# load file sequences LSTM
file_LSTM = open('LSTM/x_pad_sequences.pickle', 'rb')
feature_file_from_lstm = pickle.load(file_LSTM)
model_file_from_lstm = load_model('LSTM/model.h5')
file_LSTM.close()

with open('LSTM/tokenizer.pickle', 'rb') as handle:
    tokenizer = pickle.load(handle)

sentiment_labels = ['negative', 'neutral', 'positive']

def predict_sentiment_LSTM(text):
    cleaned_text = cleansing(text)
    input_text = [cleaned_text]

    predicted = tokenizer.texts_to_sequences(input_text)
    guess = pad_sequences(predicted, maxlen=feature_file_from_lstm.shape[1])

    prediction = model_file_from_lstm.predict(guess)[0]
    sentiment_label = sentiment_labels[np.argmax(prediction)]

    return sentiment_label

# endpoint NNtext
@swag_from("docs/NNtext.yml", methods=['POST'])
@app.route('/NNtext', methods=['POST'])
def NN_input_text():
    input_txt = str(request.form["text"])
    output_txt = cleansing(input_txt)
    sentiment_label = predict_sentiment_neural_network(output_txt)

    return_txt = {"input":input_txt, "output": output_txt, "sentiment": sentiment_label}
    return jsonify (return_txt)

# endpoint NNfile
@swag_from("docs/NNfile.yml", methods=['POST'])
@app.route('/NNfile', methods=['POST'])
def NN_upload_file():
    file = request.files["upload_file"]
    df = pd.read_csv(file, encoding=("latin-1"))
    df['Tweet_Clean'] = df['Tweet'].apply(cleansing)
    df['Sentiment'] = df['Tweet_Clean'].apply(predict_sentiment_neural_network)

    sentiment_results = df[['Tweet_Clean', 'Sentiment']].to_dict(orient='records')
    return jsonify({'sentiment_results': sentiment_results})

# endpoint LSTMtext
@swag_from("docs/LSTMtext.yml", methods=['POST'])
@app.route('/LSTMtext', methods=['POST'])
def LSTM_input_text():
    input_txt = str(request.form["text"])
    output_txt = cleansing(input_txt)
    sentiment_label = predict_sentiment_LSTM(output_txt)

    with sq.connect("database_pl.db") as conn:
        conn.execute('create table if not exists input_teks (input_text TEXT, output_text TEXT, sentiment TEXT)')
        query_txt = 'INSERT INTO input_teks(input_text, output_text, sentiment) values (?,?,?)'
        val = (input_txt, output_txt, sentiment_label)
        conn.execute(query_txt, val)
        conn.commit()

    return_txt = {"input":input_txt, "output": output_txt, "sentiment": sentiment_label}
    return jsonify (return_txt)

# endpoint LSTMfile
@swag_from("docs/LSTMfile.yml", methods=['POST'])
@app.route('/LSTMfile', methods=['POST'])
def LSTM_upload_file():
    file = request.files["upload_file"]
    df = pd.read_csv(file, encoding="latin-1")
    df['Tweet_Clean'] = df['Tweet'].apply(cleansing)
    df['Sentiment'] = df['Tweet_Clean'].apply(predict_sentiment_LSTM)

    sentiment_results = df[['Tweet_Clean', 'Sentiment']].to_dict(orient='records')
    return jsonify({'output': sentiment_results})
    
if __name__ == '__main__':
	app.run(debug=True)