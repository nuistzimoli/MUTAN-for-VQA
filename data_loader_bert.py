import os
import numpy as np
import torch
import torch.utils.data as data
import torchvision.transforms as transforms
from PIL import Image
from utils import text_helper
from transformers import BertTokenizer, BertModel

class VqaDataset(data.Dataset):
    r"The purpose of this class is to create a dataset of Vqa"
    def __init__(self, input_dir, input_vqa, max_qst_length=30, max_num_ans=10, transform=None):
        self.input_dir = input_dir
        self.vqa = np.load(input_dir + '/' + input_vqa, allow_pickle=True)
        self.qst_vocab = text_helper.VocabDict(input_dir + '/vocab_questions.txt')
        self.ans_vocab = text_helper.VocabDict(input_dir + '/vocab_answers.txt')
        self.max_qst_length = max_qst_length
        self.max_num_ans = max_num_ans
        self.load_ans = ('valid_answers' in self.vqa[0]) and (self.vqa[0]['valid_answers'] is not None)
        self.transform = transform
        self.tokenizer = BertTokenizer.from_pretrained(r"D:\data\Pretrained_data\BERT")
    def __getitem__(self, idx):#重写DataSet这个类的__getitem__函数。

        vqa = self.vqa
        qst_vocab = self.qst_vocab
        ans_vocab = self.ans_vocab
        max_qst_length = self.max_qst_length
        max_num_ans = self.max_num_ans
        transform = self.transform
        load_ans = self.load_ans
        question = vqa[idx]['question_str']
        qst_id = vqa[idx]['question_id']
        qst_token = self.tokenizer.encode(question,add_special_tokens=False, return_tensors="pt", max_length=max_qst_length, padding="max_length",
                                truncation=True,return_attention_mask=False,
                                               return_token_type_ids=False,return_special_tokens_mask=False,
                                               return_offsets_mapping=False)
        qst_token = qst_token.squeeze()
        image_path = vqa[idx]['image_path'] #比如train448.npy里面的第一个样本的图像的路径
        image = Image.open(image_path).convert('RGB')
        sample = {'image': image, 'question': qst_token,'qst_id':qst_id} #一个样本对儿

        if load_ans:
            ans2idc = [ans_vocab.word2idx(w) for w in vqa[idx]['valid_answers']]
            ans2idx = np.random.choice(ans2idc)
            sample['answer_label'] = ans2idx  # for training

            mul2idc = list([-1] * max_num_ans)  # padded with -1 (no meaning) not used in 'ans_vocab'
            mul2idc[:len(ans2idc)] = ans2idc  # our model should not predict -1
            sample['answer_multi_choice'] = mul2idc  # for evaluation metric of 'multiple choice'

        if transform:
            sample['image'] = transform(sample['image']) #把图像变成Tensor

        return sample

    def __len__(self): #return length of dataset

        return len(self.vqa)


def get_loader(input_dir, input_vqa_train, input_vqa_valid,input_vqa_test, max_qst_length, max_num_ans, batch_size, num_workers):
    transform = {
        phase: transforms.Compose([transforms.ToTensor(),
                                   #    transforms.Normalize((0.485, 0.456, 0.406),
                                   #                         (0.229, 0.224, 0.225))])
                                   transforms.Normalize((0.5, 0.5, 0.5),
                                                        (0.5, 0.5, 0.5))])
        for phase in ['train', 'valid','test']}

    vqa_dataset = {
        'train': VqaDataset(
            input_dir=input_dir,
            input_vqa=input_vqa_train,
            max_qst_length=max_qst_length,
            max_num_ans=max_num_ans,
            transform=transform['train']),
        'valid': VqaDataset(
            input_dir=input_dir,
            input_vqa=input_vqa_valid,
            max_qst_length=max_qst_length,
            max_num_ans=max_num_ans,
            transform=transform['valid']),
        'test':VqaDataset(
            input_dir=input_dir,
            input_vqa=input_vqa_test,
            max_qst_length=max_qst_length,
            max_num_ans=max_num_ans,
            transform=transform['valid'])}

    data_loader = {
        phase: torch.utils.data.DataLoader(
            dataset=vqa_dataset[phase],
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers)
        for phase in ['train', 'valid','test']}

    return data_loader