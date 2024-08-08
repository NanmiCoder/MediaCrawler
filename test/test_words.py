# -*- coding: utf-8 -*-
import sys
sys.path.append('.')
from tools.time_util import *
from tools.words import AsyncWordCloudGenerator
import unittest


words = '''
走廊灯关上 书包放
走到房间窗外望
回想刚买的书
一本名叫半岛铁盒
放在床 边堆好多
第一页 第六页 第七页序
我永远 都想不到
陪我看这书的你会要走
不再是 不再有
现在已经看不到
铁盒的钥匙孔
透了光 看见它 锈了好久
好旧好旧
外围的灰尘包围了我
好暗好暗
铁盒的钥匙我找不到
放在糖果旁的
是我很想回忆的甜
然而过滤了你和我
沦落而成美
沉在盒子里的
是你给我的快乐
我很想记得
可是我记不得
为什么这样子
你拉着我 说你有些犹豫
怎么这样子
雨还没停 你就撑伞要走
已经习惯 不去阻止你
过好一阵子 你就会回来
印象中的爱情
好像顶不住那时间
为什么这样子
你看着我 说你已经决定
我拉不住你
他的手应该比我更暖
铁盒的序 变成了日记
变成了空气 演化成回忆
印象中的爱情
好像顶不住那时间
所以你弃权
走廊灯关上 书包放
走到房间窗外望
回想刚买的书
一本名叫半岛铁盒
放在床 边堆好多
第一页 第六页 第七页序
我永远 都想不到
陪我看这书的你会要走
不再是 不再有
现在已经看不到
铁盒的钥匙孔
透了光 看见它 锈了好久
好旧好旧
外围的灰尘包围了我
好暗好暗
铁盒的钥匙我找不到
放在糖果旁的
是我很想回忆的甜
然而过滤了你和我
沦落而成美
沉在盒子里的
是你给我的快乐
我很想记得
可是我记不得
为什么这样子
你拉着我 说你有些犹豫
怎么这样子
雨还没停 你就撑伞要走
已经习惯 不去阻止你
过好一阵子 你就会回来
印象中的爱情
好像顶不住那时间
为什么这样子
你拉着我 说你有些犹豫
怎么这样子
雨还没停 你就撑伞要走
已经习惯 不去阻止你
过好一阵子 你就会回来
印象中的爱情
好像顶不住那时间
为什么这样子
你看着我 说你已经决定
我拉不住你
他的手应该比我更暖
铁盒的序 变成了日记
变成了空气 演化成回忆
印象中的爱情
好像顶不住那时间
所以你弃权
'''

# 词云排序及生成测试
class TestAsyncWordCloudGenerator(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.data = [{"content": words}]
        self.instance = AsyncWordCloudGenerator()

    async def test_generate_word_frequency_and_cloud(self):
        result = await self.instance.generate_word_frequency_and_cloud(
            self.data, (get_current_date() + "_freq_words"))


if __name__ == '__main__':
    unittest.main()
