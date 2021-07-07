from collections import deque
import os
from .abc_model import ModelABC

import torch
import torch.nn as nn


class LSTM_TextClassifier_ptModel(nn.Module):
    def __init__(self, embedding_dim, hidden_dim, vocab_size, tagset_size,
                        save_m_dir='_logs/test/', save_model_name='LSTM_classifier_.pth'):
        super().__init__()
        self.hidden_dim = hidden_dim
        # <pad>の単語IDが0なので、padding_idx=0としている
        self.word_embeddings = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        # batch_first=Trueが大事！
        self.lstm = nn.LSTM(embedding_dim, hidden_dim, batch_first=True)
        self.hidden2tag = nn.Linear(hidden_dim, tagset_size)
        self.softmax = nn.LogSoftmax()

        self.save_m_dir = save_m_dir
        os.makedirs(save_m_dir, exist_ok=True)
        self.save_m_path = os.path.join(save_m_dir, save_model_name)


    def forward(self, sentence):
        embeds = self.word_embeddings(sentence)
        #embeds.size() = (batch_size × len(sentence) × embedding_dim)
        _, lstm_out = self.lstm(embeds)
        # lstm_out[0].size() = (1 × batch_size × hidden_dim)
        tag_space = self.hidden2tag(lstm_out[0])
        # tag_space.size() = (1 × batch_size × tagset_size)

        # (batch_size × tagset_size)にするためにsqueeze()する
        tag_scores = self.softmax(tag_space.squeeze())
        # tag_scores.size() = (batch_size × tagset_size)
        return tag_scores  

    def fit(self, X_batch, Y_batch, criterion, optimizer, device):
        loss = 0
        self.zero_grad()
        X_batch = X_batch.to(device)
        Y_batch = Y_batch.to(device)

        # 順伝搬させるtensorはGPUで処理させるためdevice=にGPUをセット
        # X_tensor = torch.tensor(X_batch, device=device)
        output = self(X_batch)
        # Y_tensor.size() = (batch_size × 1)なので、squeeze()
        # Y_tensor = torch.tensor(Y_batch, device=device).squeeze()

        # print(output, Y_batch)
        loss = criterion(output, Y_batch)
        loss.backward()
        optimizer.step()
        return loss.item() / len(X_batch),  output

    def predict(self, X_batch, Y_batch, criterion, device):
        loss = 0
        with torch.no_grad():
            # 順伝搬させるtensorはGPUで処理させるためdevice=にGPUをセット
            X_batch = X_batch.to(device)
            Y_batch = Y_batch.to(device)
            # X_tensor = torch.tensor(X_batch, device=device)
            pred_arr = self(X_batch)
            # Y_tensor.size() = (batch_size × 1)なので、squeeze()
            # Y_tensor = torch.tensor(Y_batch, device=device).squeeze()

            loss = criterion(pred_arr, Y_batch)
            return loss.item() / len(X_batch), pred_arr


    def load_weights(self, load_m_path='_logs/test/LSTM_classifier.pth',):
        if load_m_path is not None:
            param = torch.load(load_m_path)
            self.load_state_dict(param)
            print(f'[info] {load_m_path} loaded !')

    def save(self, save_f_path=None):
        if save_f_path is None:
            save_f_path = self.save_m_path
        torch.save(self.state_dict(), save_f_path)




import tensorflow as tf

class LSTM_TextClassify_tfModel(ModelABC):
    def __init__(self, vocab_size):
        self.model = tf.keras.Sequential([
            tf.keras.layers.Embedding(vocab_size, 64),
            tf.keras.layers.Bidirectional(tf.keras.layers.LSTM(64)),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(1)
        ])

        self.model.compile(loss=tf.keras.losses.BinaryCrossentropy(from_logits=True),
              optimizer=tf.keras.optimizers.Adam(1e-4),
              metrics=['accuracy'])
    
    def fit(self, dataset):
        imdb = dataset.get_train()
        train_dataset = imdb['train']
        test_dataset = imdb['test']

        self.history = self.model.fit(train_dataset, epochs=10,
                        validation_data=test_dataset, 
                        validation_steps=30)

    def predict(self, data) -> int:
        """
        モデルで予測（predict）する。

        :return np.ndarray : model の予測結果(array)
        【実装例】
            score_arr = 2 * self.predict_proba(data)[:,1] - 1
            return np.array(score_arr)
        """
        raise NotImplementedError()

    def predict_orgf(self, data):
        raise NotImplementedError()

