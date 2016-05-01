# -*- coding: utf-8 -*-
'''
Использование RNN/LSTM для классификации цепочек символов как сов_гл/несов_гл/неопр
30.04.2016 первая реализация на основе кода модели word_is_noun
'''

from __future__ import print_function
from keras.models import Sequential
from keras.layers.core import Activation, Dense, Masking
from keras.layers import recurrent
from keras.callbacks import ModelCheckpoint, EarlyStopping
import keras.callbacks
import numpy as np
from six.moves import range
import sys
from sklearn.metrics import f1_score


PADDING_CHAR=u'\a' # спецсимвол для выравнивания строк на одинаковую длину
NCLASS=3 # кол-во классов
TRAINING_SIZE = 1000000
INVERT = True
RNN = recurrent.LSTM # Try replacing GRU, or SimpleRNN
HIDDEN_SIZE = 64
BATCH_SIZE = 64
LAYERS = 1

corpus_path = 'word2verb_aspect.dat'


class HistoryCallback(keras.callbacks.Callback):

    # ужасная реализация для вычисления точности для бинарной классификации
    # добавить вычисление F1
    def on_epoch_end(self, batch, logs={}):
     y_pred = model.predict( X_test, verbose=0 ).argmax(axis=-1)

     n_error=0
     n_success=0

     for i in range(y_pred.shape[0]):
         
         if y_test[i, y_pred[i]]==1:
             n_success = n_success+1
         else:
             n_error = n_error+1

     err = float(n_error)*100.0/float(n_error+n_success)
     print( 'err=', err )
     
     #F1 = f1_score( y_true_f1, y_pred_f1, average=None)
     #print( 'F1=', F1 )



class CharacterTable(object):
    '''
    Given a set of characters:
    + Encode them to a one hot integer representation
    + Decode the one hot integer representation to their character output
    + Decode a vector of probabilties to their character output
    '''
    def __init__(self, chars, maxlen):
        self.chars = sorted(set(chars))
        self.char_indices = dict((c, i) for i, c in enumerate(self.chars))
        self.indices_char = dict((i, c) for i, c in enumerate(self.chars))
        self.maxlen = maxlen

    def encode(self, C, maxlen=None):
        maxlen = maxlen if maxlen else self.maxlen
        X = np.zeros( (maxlen, bits_per_char) )
        for i, c in enumerate(C):
            if c!=PADDING_CHAR:
                X[i, self.char_indices[c]] = 1
        return X



print('Loading data', corpus_path, '...')

patterns = []
max_word_len = 0

chars = set([])
with open( corpus_path, 'r' ) as fdata:
    
    fdata.readline()
    
    while len(patterns) < TRAINING_SIZE:
        
        toks = fdata.readline().strip().decode('utf-8').split('\t')
        
        word = toks[0]
        
        class_id=0
        if toks[1]==u'СОВЕРШ':
            class_id = 1
        elif toks[1]==u'НЕСОВЕРШ':
            class_id = 2

        max_word_len = max( max_word_len, len(word) )
        patterns.append( (word,class_id) )
        chars.update( list(word) )

bits_per_char = len(chars)
ctable = CharacterTable(chars, max_word_len)
        
print('Total number of patterns:', len(patterns))
print('max_word_len=', max_word_len );

questions = []
expected = []

for ipattern,pattern in enumerate(patterns):
    
    q = pattern[0]
    query = q + PADDING_CHAR * (max_word_len - len(q))
    if INVERT:
        query = query[::-1]
    
    answer = pattern[1]
    
    questions.append(query)
    expected.append(answer)

n_patterns = len(questions)
test_share = 0.1
n_test = int(n_patterns*test_share)
n_train = n_patterns-n_test

print('Vectorization...')
X_train = np.zeros((n_train, max_word_len, bits_per_char), dtype=np.bool)
y_train = np.zeros((n_train, NCLASS), dtype=np.bool)

X_test = np.zeros((n_test, max_word_len, bits_per_char), dtype=np.bool)
y_test = np.zeros((n_test, NCLASS), dtype=np.bool)

i_test = 0
i_train = 0
for i in range(len(questions)):

    word = questions[i]
    class_id = expected[i]

    if i<n_test:
        X_test[i_test] = ctable.encode(word, maxlen=max_word_len)
        y_test[i_test,class_id] = 1
        i_test = i_test+1
    else:
        X_train[i_train] = ctable.encode(word, maxlen=max_word_len)
        y_train[i_train,class_id] = 1
        i_train = i_train+1

print('Build model...')
model = Sequential()

model.add( Masking(mask_value=0,input_shape=(max_word_len,bits_per_char)) )

model.add( RNN(HIDDEN_SIZE, input_shape=(max_word_len, bits_per_char) ) )

model.add(Dense(NCLASS))
model.add(Activation('softmax'))

model.compile(loss='categorical_crossentropy', optimizer='rmsprop')

hist = HistoryCallback()
model_checkpoint = ModelCheckpoint( 'word2verb_aspect.model', monitor='val_loss', verbose=1, save_best_only=True, mode='auto')
early_stopping = EarlyStopping( monitor='val_loss', patience=10, verbose=1, mode='auto')

history = model.fit(X_train, y_train, batch_size=BATCH_SIZE, nb_epoch=30, validation_data=(X_test, y_test), callbacks=[model_checkpoint,early_stopping,hist])
#with open( 'performance.txt', 'a' ) as f:
#    f.write( str(history)+'\n' )
