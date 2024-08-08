import asyncio
import json
from collections import Counter

import aiofiles
import jieba
import matplotlib.pyplot as plt
from wordcloud import WordCloud

import config
from tools import utils

plot_lock = asyncio.Lock()

class AsyncWordCloudGenerator:
    def __init__(self):
        self.stop_words_file = config.STOP_WORDS_FILE
        self.lock = asyncio.Lock()
        self.stop_words = self.load_stop_words()
        self.custom_words = config.CUSTOM_WORDS
        for word, group in self.custom_words.items():
            jieba.add_word(word)

    def load_stop_words(self):
        with open(self.stop_words_file, 'r', encoding='utf-8') as f:
            return set(f.read().strip().split('\n'))

    async def generate_word_frequency_and_cloud(self, data, save_words_prefix):
        all_text = ' '.join(item['content'] for item in data)
        words = [word for word in jieba.lcut(all_text) if word not in self.stop_words and len(word.strip()) > 0]
        word_freq = Counter(words)

        # Save word frequency to file
        freq_file = f"{save_words_prefix}_word_freq.json"
        async with aiofiles.open(freq_file, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(word_freq, ensure_ascii=False, indent=4))

        # Try to acquire the plot lock without waiting
        if plot_lock.locked():
            utils.logger.info("Skipping word cloud generation as the lock is held.")
            return

        await self.generate_word_cloud(word_freq, save_words_prefix)

    async def generate_word_cloud(self, word_freq, save_words_prefix):
        await plot_lock.acquire()
        top_20_word_freq = {word: freq for word, freq in
                            sorted(word_freq.items(), key=lambda item: item[1], reverse=True)[:20]}
        wordcloud = WordCloud(
            font_path=config.FONT_PATH,
            width=800,
            height=400,
            background_color='white',
            max_words=200,
            stopwords=self.stop_words,
            colormap='viridis',
            contour_color='steelblue',
            contour_width=1
        ).generate_from_frequencies(top_20_word_freq)

        # Save word cloud image
        plt.figure(figsize=(10, 5), facecolor='white')
        plt.imshow(wordcloud, interpolation='bilinear')

        plt.axis('off')
        plt.tight_layout(pad=0)
        plt.savefig(f"{save_words_prefix}_word_cloud.png", format='png', dpi=300)
        plt.close()

        plot_lock.release()