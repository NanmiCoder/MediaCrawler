# 关于词云图相关操作

## 1.如何正确调用词云图
> ps:目前只有保存格式为json文件时，才会生成词云图。其他存储方式添加词云图将在近期添加。

需要修改的配置项（./config/base_config.py）：

```python
# 数据保存类型选项配置,支持三种类型：csv、db、json
#此处需要为json格式保存，原因如上
SAVE_DATA_OPTION = "json"  # csv or db or json
```

```python
# 是否开启爬评论模式, 默认不开启爬评论
#此处为True，需要爬取评论才可以生成评论的词云图。
ENABLE_GET_COMMENTS = True
```

```python
#词云相关
#是否开启生成评论词云图
#打开词云图功能
ENABLE_GET_WORDCLOUD = True
```

```python
# 添加自定义词语及其分组
#添加规则：xx:yy 其中xx为自定义添加的词组，yy为将xx该词组分到的组名。
CUSTOM_WORDS = {
    '零几': '年份',  # 将“零几”识别为一个整体
    '高频词': '专业术语'  # 示例自定义词
}
```

```python
#停用(禁用)词文件路径
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"
```

```python
#中文字体文件路径
FONT_PATH= "./docs/STZHONGS.TTF"
```

**相关解释**

- 自定义词组的添加，`xx:yy` 中`xx`为自定义词语，`yy`为`xx`分配词语的组别。`yy`可以随便给任意值。

- 如果需要添加禁用词，请在./docs/hit_stopwords.txt添加禁用词(保证格式正确，一个词语一行)
- `FONT_PATH`为生成词云图中中文字体的格式，默认为宋体。可以自行添加字体文件，修改路径。

## 2.生成词云图的位置

![image-20240627204928601](https://rosyrain.oss-cn-hangzhou.aliyuncs.com/img2/202406272049662.png)

如图，在data文件下的`words文件夹`下，其中json为词频统计文件，png为词云图。原本的评论内容在`json文件夹`下。