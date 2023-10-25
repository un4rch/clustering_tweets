import numpy as np
import pandas as pd
import gensim
import nltk
import re
import emoji
import emot
import sys
from sklearn.decomposition import PCA
from sklearn.svm import SVC
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet

class Preprocessor:
    def __init__(self) -> None:
          pass
    
    def convertirEmojis(self, texto, switch):  # convierte un emoji en un conjunto de palabras en inglés que lo representa. Si switch es False, entonces se eliminan los emojis
        if switch:
            texto = emoji.demojize(texto)
            diccionario_emojis = emot.emo_unicode.EMOTICONS_EMO
            for emoticono, texto_emoji in diccionario_emojis.items():
                texto = texto.replace(emoticono, texto_emoji)
        else:
            texto = emoji.demojize(texto)
            texto = re.sub(":.*?:", "", texto)
            texto = texto.strip()
        return texto
    
    def eliminarSignosPuntuacion(self, texto):  # dado un string, devuelve el mismo string eliminando todos los caracteres que no sean alfabéticos
        textoNuevo = ""
        for caracter in texto:  # por cada caracter en el texto
            if caracter == "_":  # si es una barra baja, entonces se traduce como espacio
                textoNuevo = textoNuevo + " "
            if caracter.isalpha() or caracter == " ":  # si pertenece al conjunto de letras del alfabeto, se engancha a "textoNuevo"
                textoNuevo = textoNuevo + caracter
        return(textoNuevo)
    
    def eliminarStopWords(self, texto):  # dado un string, elimina las stopwords de ese string
        texto = word_tokenize(texto, language='english')
        textoNuevo = ""
        for palabra in texto:
            if palabra not in stopwords.words('english'):
                textoNuevo = textoNuevo + " " + palabra
        return(textoNuevo)

    def normalizarTexto(self, texto):  # dado un string que contenga palabras, devuelve un string donde todas las letras sean minúsculas
        return(texto.lower())
    
    def aux_lematizar(self, palabra):
        tag = nltk.pos_tag([palabra])[0][1][0].upper()
        tag_dict = {"J": wordnet.ADJ,
                "N": wordnet.NOUN,
                "V": wordnet.VERB,
                "R": wordnet.ADV}
        return tag_dict.get(tag, wordnet.NOUN)
    
    def lematizar(self, texto):  # dado un string, lematiza las palabras de ese string
        texto = nltk.word_tokenize(texto)

        # Inicializar el lematizador
        lemmatizer = WordNetLemmatizer()

        # Lematizar cada palabra y agregarla a una lista
        palabras_lematizadas = []
        for palabra in texto:
            pos = self.aux_lematizar(palabra)
            palabra_l = lemmatizer.lemmatize(palabra, pos=pos)
            palabras_lematizadas.append(palabra_l)

        # Unir las palabras lematizadas en un solo string y devolverlo
        texto_lematizado = ' '.join(palabras_lematizadas)
        return texto_lematizado
    
    def preprocesarLenguajeNatural(self, pColumna, pSwitch):  # realiza todo el preproceso de un string en el orden correcto
        linea = str(pColumna)
        linea = self.convertirEmojis(linea, pSwitch)
        linea = self.eliminarSignosPuntuacion(linea)
        linea = self.normalizarTexto(linea)
        linea = self.eliminarStopWords(linea)
        linea = self.lematizar(linea)
        return linea
    
    def word2vec(self, texts_array, labels_array, pca_dimensions):
        texts_array = np.array(texts_array)
        labels_array = np.array(labels_array)

        x_cleaned = [self.preprocesarLenguajeNatural(t, "switch") for t in texts_array]
        x_tokenized = [[w for w in sentence.split(" ") if w != ""] for sentence in x_cleaned]
        if not pd.isnull(labels_array).all():
            label_map = {cat:index for index,cat in enumerate(np.unique(labels_array))}
            y_prep = np.asarray([label_map[l] for l in labels_array])
        else:
            y_prep = None
        model = gensim.models.Word2Vec(x_tokenized, vector_size=100)
        sequencer = Sequencer(all_words = [token for seq in x_tokenized for token in seq],
              max_words = 1200,
              seq_len = 15,
              embedding_matrix = model.wv
             )
        x_vecs = np.asarray([sequencer.textToVector(" ".join(seq)) for seq in x_tokenized])

        pca_model = PCA(n_components=pca_dimensions)
        pca_model.fit(x_vecs)   

        x_prep = pca_model.transform(x_vecs)
        #x_prep.shape
        #np.savetxt('x_prep.csv', x_comps, delimiter=',')
        return x_prep,y_prep
    
    def doc2vec(self, texts_array, labels_array, pca_dimensions):
        texts_array = np.array(texts_array)
        y = np.array(labels_array)

        x_cleaned = [self.preprocesarLenguajeNatural(t, "switch") for t in texts_array]
        x_tokenized = [[w for w in sentence.split(" ") if w != ""] for sentence in x_cleaned]

        if not pd.isnull(labels_array).all():
            label_map = {cat:index for index,cat in enumerate(np.unique(labels_array))}
            y_prep = np.asarray([label_map[l] for l in labels_array])
        else:
            y_prep = None

        tagged_data = [TaggedDocument(words=row, tags=[str(label)]) for row, label in zip(x_tokenized, y_prep)]
        model = Doc2Vec(vector_size=1000, window=5, min_count=1, workers=4, epochs=20)
        model.build_vocab(tagged_data)
        model.train(tagged_data, total_examples=model.corpus_count, epochs=model.epochs)
        model.save("reddit_suicide_depression.model")

        nuevo_vectors = []
        for tokens in x_tokenized:
            vector = model.infer_vector(tokens)
            nuevo_vectors.append(vector)

        pca_model = PCA(n_components=200)
        pca_model.fit(nuevo_vectors)

        x_comps = pca_model.transform(nuevo_vectors)
        x_comps.shape

        #np.savetxt('x_prep.csv', x_comps, delimiter=',')
        return x_comps, y_prep

class Sequencer():
    
    def __init__(self,
                 all_words,
                 max_words,
                 seq_len,
                 embedding_matrix
                ):
        
        self.seq_len = seq_len
        self.embed_matrix = embedding_matrix
        """
        temp_vocab = Vocab which has all the unique words
        self.vocab = Our last vocab which has only most used N words.
    
        """
        temp_vocab = list(set(all_words))
        self.vocab = []
        self.word_cnts = {}
        """
        Now we'll create a hash map (dict) which includes words and their occurencies
        """
        for word in temp_vocab:
            # 0 does not have a meaning, you can add the word to the list
            # or something different.
            count = len([0 for w in all_words if w == word])
            self.word_cnts[word] = count
            counts = list(self.word_cnts.values())
            indexes = list(range(len(counts)))
        
        # Now we'll sort counts and while sorting them also will sort indexes.
        # We'll use those indexes to find most used N word.
        cnt = 0
        while cnt + 1 != len(counts):
            cnt = 0
            for i in range(len(counts)-1):
                if counts[i] < counts[i+1]:
                    counts[i+1],counts[i] = counts[i],counts[i+1]
                    indexes[i],indexes[i+1] = indexes[i+1],indexes[i]
                else:
                    cnt += 1
        
        for ind in indexes[:max_words]:
            self.vocab.append(temp_vocab[ind])
                    
    def textToVector(self,text):
        # First we need to split the text into its tokens and learn the length
        # If length is shorter than the max len we'll add some spaces (100D vectors which has only zero values)
        # If it's longer than the max len we'll trim from the end.
        tokens = text.split()
        len_v = len(tokens)-1 if len(tokens) < self.seq_len else self.seq_len-1
        vec = []
        for tok in tokens[:len_v]:
            try:
                vec.append(self.embed_matrix[tok])
            except Exception as E:
                pass
        
        last_pieces = self.seq_len - len(vec)
        for i in range(last_pieces):
            vec.append(np.zeros(100,))
        
        return np.asarray(vec).flatten()