from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import random
import math
import string
import codecs
# import matplotlib.pyplot as plt
import numpy as np
import mxnet as mx


class RandomChar():
    """用于随机生成汉字"""
    @staticmethod
    def Unicode():
        val = random.randint(0x4E00, 0x9FBF)
        return chr(val)

    @staticmethod
    def GB2312():
        # head = random.randint(0xB0, 0xCF)
        # body = random.randint(0xA, 0xF)
        # tail = random.randint(0, 0xF)
        # val = (head &lt; &lt; 8) | (body & lt; & lt; 4) | tail
        head = random.randint(0xB0, 0xD7)
        body = random.randint(0xA1, 0xFE)
        val = (head << 8) | body
        str = "%x" % val
        str = codecs.decode(str, 'hex')
        str = str.decode('gb2312')
        # return str.decode('hex').decode('gb2312')
        return str, val


s = []
for head in range(0xB0, 0xD7 + 1):
    for body in range(0xA1, 0xFE + 1):
        val = (head << 8) | body
        s.append(val)

s = s[:-5]


class ImageChar():

    def __init__(self, fontColor=(255, 255, 255),
                 size=(100, 20),
                 fontPath='ukai.ttc',
                 bgColor=(0, 0, 0),
                 fontSize=20):
        self.size = size
        self.fontPath = fontPath
        self.bgColor = bgColor
        self.fontSize = fontSize
        self.fontColor = fontColor
        self.font = ImageFont.truetype(self.fontPath, self.fontSize)
        self.image = Image.new('RGB', size, bgColor)

    # def rotate(self):
    #     self.image = self.image.rotate(10, expand=0)

    def drawText(self, pos, txt, fill):
        draw = ImageDraw.Draw(self.image)
        draw.text(pos, txt, font=self.font, fill=fill)
        del draw

    def drawTextV2(self, pos, txt, fill):
        image = Image.new('RGB', (20, 20), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.text((0, -3), txt, font=self.font, fill=fill)
        w = image.rotate(random.randint(-10, 10), expand=1)
        self.image.paste(w, box=pos)
        del draw

    # def randRGB(self):
    #     return (random.randint(0, 255),
    #             random.randint(0, 255),
    #             random.randint(0, 255))

    def randPoint(self, num):
        (width, height) = self.size
        draw = ImageDraw.Draw(self.image)
        for i in range(0, num):
            draw.point([random.randint(0, width),
                        random.randint(0, height)], (255, 255, 255))
        # return (random.randint(0, width), random.randint(0, height)
        del draw

    # def randLine(self, num):
    #     draw = ImageDraw.Draw(self.image)
    #     for i in range(0, num):
    #         draw.line([self.randPoint(), self.randPoint()], self.randRGB())
    #     del draw

    def randChinese(self, num):
        gap = 5
        start = 0
        label = []
        while len(label) < num:
            try:
                char, val = RandomChar().GB2312()
            except UnicodeDecodeError:
                # print(len(label))
                continue
            x = start + self.fontSize * \
                len(label) + random.randint(0, gap) + gap * len(label)
            self.drawTextV2((x, random.randint(-3, 2)),
                            char, (255, 255, 255))
            # self.image.rotate(180)
            # self.rotate()
            label.append(s.index(val))
        self.randPoint(18)
        return label

    def save(self, path):
        self.image.save(path)


class OCRBatch(object):

    def __init__(self, data_names, data, label_names, label):
        self.data = data
        self.label = label
        self.data_names = data_names
        self.label_names = label_names

    @property
    def provide_data(self):
        return [(n, x.shape) for n, x in zip(self.data_names, self.data)]

    @property
    def provide_label(self):
        return [(n, x.shape) for n, x in zip(self.label_names, self.label)]

    def all_data(self):
        return self.data


class OCRIter(mx.io.DataIter):

    def __init__(self, count, batch_size, num_label):
        super(OCRIter, self).__init__()
        # self.ic = ImageChar()

        self.batch_size = batch_size
        self.count = count
        self.num_label = num_label
        self.provide_data = [('data', (batch_size, 1, 100, 20))]
        self.provide_label = [('softmax_label', (self.batch_size, num_label))]

    def __iter__(self):
        for k in range(int(self.count / self.batch_size)):
            data = []
            label = []
            for i in range(self.batch_size):
                ic = ImageChar(fontPath='/home/plkj/ukai.ttc')
                # num = self.ic.randChinese(self.num_label)
                num = ic.randChinese(self.num_label)
                # self.ic.save(str(k) + str(i) + '.jpg')
                # tmp = np.array(self.ic.image.convert("L"))
                # ic.save(str(k) + str(i) + '.jpg')
                tmp = np.array(ic.image.convert("L"))
                tmp = 255 - tmp
                tmp = tmp.reshape(1, 100, 20)
                # print(tmp.shape)
                data.append(tmp)
                label.append(np.array(num))
            data_all = [mx.nd.array(data)]
            label_all = [mx.nd.array(label)]
            data_names = ['data']
            label_names = ['softmax_label']

            data_batch = OCRBatch(data_names, data_all, label_names, label_all)
            yield data_batch

    def reset(self):
        pass


def get_ocrnet():
    data = mx.sym.Variable('data')
    label = mx.sym.Variable('softmax_label')
    conv1_1 = mx.sym.Convolution(data=data, kernel=(3, 3), pad=(1, 1),
                                 no_bias=False, num_filter=64, stride=(1, 1))
    relu1_1 = mx.sym.Activation(data=conv1_1, act_type='relu')
    conv1_2 = mx.sym.Convolution(data=relu1_1, kernel=(3, 3), pad=(1, 1),
                                 stride=(1, 1), no_bias=False, num_filter=64)
    relu1_2 = mx.sym.Activation(data=conv1_2, act_type='relu')
    pool1 = mx.sym.Pooling(data=relu1_2, pool_type="avg",
                           kernel=(2, 2), stride=(2, 2), pad=(0, 0))

    conv2_1 = mx.sym.Convolution(data=pool1, kernel=(3, 3), pad=(1, 1),
                                 no_bias=False, num_filter=128, stride=(1, 1))
    relu2_1 = mx.sym.Activation(data=conv2_1, act_type='relu')
    conv2_2 = mx.sym.Convolution(data=relu2_1, kernel=(3, 3), pad=(1, 1),
                                 stride=(1, 1), no_bias=False, num_filter=128)
    relu2_2 = mx.sym.Activation(data=conv2_2, act_type='relu')
    pool2 = mx.sym.Pooling(data=relu2_2, pool_type="avg",
                           kernel=(2, 2), stride=(2, 2), pad=(0, 0))

    conv3_1 = mx.sym.Convolution(data=pool2, kernel=(3, 3), pad=(1, 1),
                                 no_bias=False, num_filter=256, stride=(1, 1))
    relu3_1 = mx.sym.Activation(data=conv3_1, act_type='relu')
    conv3_2 = mx.sym.Convolution(data=relu3_1, kernel=(3, 3), pad=(1, 1),
                                 stride=(1, 1), no_bias=False, num_filter=256)
    relu3_2 = mx.sym.Activation(data=conv3_2, act_type='relu')
    conv3_3 = mx.sym.Convolution(data=relu3_2, kernel=(3, 3), pad=(1, 1),
                                 stride=(1, 1), no_bias=False, num_filter=256)
    relu3_3 = mx.sym.Activation(data=conv3_3, act_type='relu')
    conv3_4 = mx.sym.Convolution(data=relu3_3, kernel=(3, 3), pad=(1, 1),
                                 stride=(1, 1), no_bias=False, num_filter=256)
    relu3_4 = mx.sym.Activation(data=conv3_4, act_type='relu')
    pool3 = mx.sym.Pooling(data=relu3_4, pool_type="avg",
                           kernel=(2, 2), stride=(2, 2), pad=(0, 0))

    conv4_1 = mx.sym.Convolution(data=pool3, kernel=(3, 3), pad=(1, 1),
                                 no_bias=False, num_filter=512, stride=(1, 1))
    relu4_1 = mx.sym.Activation(data=conv4_1, act_type='relu')
    conv4_2 = mx.sym.Convolution(data=relu4_1, kernel=(3, 3), pad=(1, 1),
                                 stride=(1, 1), no_bias=False, num_filter=512)
    relu4_2 = mx.sym.Activation(data=conv4_2, act_type='relu')
    conv4_3 = mx.sym.Convolution(data=relu4_2, kernel=(3, 3), pad=(1, 1),
                                 stride=(1, 1), no_bias=False, num_filter=512)
    relu4_3 = mx.sym.Activation(data=conv4_3, act_type='relu')
    conv4_4 = mx.sym.Convolution(data=relu4_3, kernel=(3, 3), pad=(1, 1),
                                 stride=(1, 1), no_bias=False, num_filter=512)
    relu4_4 = mx.sym.Activation(data=conv4_4, act_type='relu')
    pool4 = mx.sym.Pooling(data=relu4_4, pool_type="avg",
                           kernel=(2, 2), stride=(2, 2), pad=(0, 0))

    conv5_1 = mx.sym.Convolution(data=pool4, num_filter=512, pad=(1, 1),
                                 kernel=(3, 3), stride=(1, 1), no_bias=False)
    relu5_1 = mx.sym.Activation(data=conv5_1, act_type='relu')
    flatten = mx.sym.Flatten(data=relu5_1)
    fc1 = mx.sym.FullyConnected(data=flatten, num_hidden=4096)
    fc2 = mx.sym.FullyConnected(data=flatten, num_hidden=4096)
    fc3 = mx.sym.FullyConnected(data=flatten, num_hidden=1024)
    fc41 = mx.sym.FullyConnected(data=fc3, num_hidden=3755)
    fc42 = mx.sym.FullyConnected(data=fc3, num_hidden=3755)
    fc43 = mx.sym.FullyConnected(data=fc3, num_hidden=3755)
    fc4 = mx.sym.Concat(*[fc41, fc42, fc43], dim=0)
    label = mx.sym.transpose(data=label)
    label = mx.sym.Reshape(data=label, target_shape=(0, ))
    return mx.sym.SoftmaxOutput(data=fc4, label=label, name="softmax")


def Accuracy(label, pred):
    label = label.T.reshape((-1, ))
    hit = 0
    total = 0
    # print(pred)
    # print(pred.shape)
    for i in range(int(pred.shape[0] / 3)):
        ok = True
        for j in range(3):
            k = i * 3 + j
            # print(k)
            # print(np.argmax(pred[k]))
            # print(int(label[k]))
            # print("========next========")
            if np.argmax(pred[k]) != int(label[k]):
                ok = False
                break
        if ok:
            hit += 1
        total += 1
    return hit / total


batch_size = 128
data_train = OCRIter(10000000, batch_size, 3)
data_test = OCRIter(10000, batch_size, 3)
training_log = 'logs/train'
evaluation_log = 'logs/eval'
batch_end_callbacks = [mx.contrib.tensorboard.LogMetricsCallback(
    training_log),
    mx.callback.Speedometer(batch_size, 50)]
eval_end_callbacks = [
    mx.contrib.tensorboard.LogMetricsCallback(evaluation_log)]
import logging
logging.getLogger().setLevel(logging.DEBUG)
model = mx.mod.Module(symbol=get_ocrnet(), context=mx.gpu(),
                      data_names=['data'], label_names=['softmax_label'])

model.fit(train_data=data_train, eval_data=data_test, optimizer='sgd',
          optimizer_params={'learning_rate': 0.001},
          eval_metric=Accuracy, num_epoch=100,
          batch_end_callback=mx.callback.Speedometer(batch_size, 50),
          epoch_end_callback=mx.callback.module_checkpoint(
              model, prefix='cnn-ocr', save_optimizer_states=True))
