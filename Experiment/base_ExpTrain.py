import os
import random
import time
from tqdm import tqdm

from model_abc import (
    LSTM_text_classify_model,
)


###  Train  ###
from collections import deque
from sklearn.utils import shuffle
import time

import torch
import torch.nn as nn
from torch import optim
from torch.utils.data import DataLoader
# import torchmetrics
from torch.utils.tensorboard import SummaryWriter


class Batch_ExpTrain():
    def __init__(self, train_dataset, valid_dataset, device):
        self.train_dataset = train_dataset
        self.valid_dataset = valid_dataset

        self.device = device

    # データをバッチでまとめるための関数
    # def xy2batch(self, X, Y, batch_size=100):
    #     X_batch = []
    #     Y_batch = []
    #     X_shuffle, Y_shuffle = shuffle(X, Y)
    #     for i in range(0, len(X), batch_size):
    #         X_batch.append(X_shuffle[i:i+batch_size])
    #         Y_batch.append(Y_shuffle[i:i+batch_size])
    #     return X_batch, Y_batch

    def exec(self, model: LSTM_text_classify_model,
                    criterion, optimizer,
                    epochs=30, batch_size=200, teacher_forcing=0.5, early_stopping=20):
        
        log_dir = model.save_m_dir

        # default `log_dir` is "runs" - we'll be more specific here
        writer = SummaryWriter(log_dir)
        
        ###  DataLoader  ###
        batch_num = len(self.train_dataset) / batch_size
        train_dataloader = DataLoader(self.train_dataset, batch_size=batch_size, shuffle=True)
        # valid_dataloader = DataLoader(self.valid_dataset, batch_size=int(len(self.valid_dataset)/batch_num), shuffle=False)
        valid_dataloader = DataLoader(self.valid_dataset, batch_size=batch_size, shuffle=False)
        print('[Info] len(train_dataloader) : ', len(train_dataloader),  '  batch_num : ', batch_num)
        print('[Info] len(valid_dataloader) : ', len(valid_dataloader))

        min_loss = 1.0
        valid_acc_arr = []
        
        for epc in tqdm(range(epochs)):
            ## train
            train_loss = 0
            train_acc = 0
            total_count = 0
            for idx, (X_batch, Y_batch) in enumerate(train_dataloader):
                loss_batch = 0
                loss_batch, pred_batch_arr = model.fit(X_batch, Y_batch, criterion, optimizer, self.device)
                train_loss += loss_batch
                _, pred_batch = torch.max(pred_batch_arr, 1)
                # acc を計算する。
                for j, ans in enumerate(Y_batch):
                    if pred_batch[j].item() == ans.item():
                        train_acc += 1
                total_count += Y_batch.size(0)
            train_acc /= total_count
            
            ## valid
            valid_acc = 0
            total_count = 0
            for idx, (X_batch, Y_batch) in enumerate(valid_dataloader):
                valid_loss = 0
                valid_loss, pred_batch_arr = model.predict(X_batch, Y_batch, criterion, self.device)
                _, pred_batch = torch.max(pred_batch_arr, 1)
                # acc を計算する。
                for j, ans in enumerate(Y_batch):
                    # print(pred_batch[j].item(), ans.item())
                    if pred_batch[j].item() == ans.item():
                        valid_acc += 1
                total_count += Y_batch.size(0)
            valid_acc /= total_count

            # tensorboard
            writer.add_scalar('train loss', train_loss, epc)
            writer.add_scalar('valid loss', valid_loss, epc)
            writer.add_scalar('train acc', train_acc, epc)
            writer.add_scalar('valid acc', valid_acc, epc)

            # print(f'[Info] train (loss, acc) : {train_loss}, {train_acc} \n    valid (loss, acc) : {valid_loss}, {valid_acc}')

            # valid が最大の時の重みを保存
            if min_loss > valid_acc:
                model.save()
                min_loss = valid_acc
                print('[Info] model saved! (max valid)')
            
            # 最終 step の重みを保存
            model.save('model_weghts_latest.pth')

            valid_acc_arr.append(valid_acc)
            if max(valid_acc_arr[-early_stopping:]) < max(valid_acc_arr):
                print('[Info] early stopping します。')
                break
        
        writer.close()
        return max(valid_acc_arr)







if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    ## Data
    input_lang, output_lang, pairs = prepareData(
        'eng', 'fra', '_data_example/data', False)
    print(random.choice(pairs))
    # train / test split
    from sklearn.model_selection import train_test_split
    train_pairs, test_pairs = train_test_split(pairs, test_size=0.2)

    ## Model
    tokenizer = Seq2SeqTranslate_ptTokenizer(
                    input_lang, output_lang, device)

    ###  test  ###
    batch_size = 10
    emb_size = 8
    hid_size = 12
    MAX_LENGTH = 18

    seq2seq_test_model = Seq2Seq_batch_ptModel(
                        tokenizer, device,
                        dropout_p=0.1, max_length=MAX_LENGTH)
    test_encoder = EncoderLSTM(input_lang.n_words, emb_size, hid_size)
    test_decoder1 = AttnDecoderLSTM1(
                        emb_size, hid_size, output_lang.n_words,
                        device, max_length=MAX_LENGTH)
    
    seq2seq_test_model.load_enc_dec_models(test_encoder, test_decoder1)
    seq2seq_test_model.exec_test(train_pairs, batch_size=batch_size)

    attn_size = 9
    test_decoder2 = AttnDecoderLSTM2(
                        emb_size, hid_size, attn_size, 
                        output_lang.n_words, device).to(device)
    seq2seq_test_model.load_enc_dec_models(test_encoder, test_decoder2)
    seq2seq_test_model.exec_test(train_pairs, batch_size=batch_size)


    ###  exp 1  ###
    emb_size = 1024
    hidden_size = 1024

    encoder = EncoderLSTM(input_lang.n_words, emb_size, hidden_size).to(device)
    decoder = AttnDecoderLSTM1(emb_size, hidden_size, output_lang.n_words).to(device)
    seq2seq_model = Seq2Seq_batch_ptModel(
                        encoder, decoder, tokenizer, device,
                        dropout_p=0.1, max_length=10)

