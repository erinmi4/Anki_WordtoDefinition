import asyncio
import httpx
from config import DEEPSEEK_API_KEY, SYSTEM_PROMPT, DEEPSEEK_API_BASE
from cache_manager import CacheManager

class WordProcessor:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        self.cache = CacheManager()
        
    async def get_words_info_batch(self, words, batch_size=5):
        """批量处理单词"""
        results = {}
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 将单词列表分成多个批次
            for i in range(0, len(words), batch_size):
                batch = words[i:i + batch_size]
                # 并发处理每个批次
                tasks = [self._get_single_word_info(client, word) for word in batch]
                batch_results = await asyncio.gather(*tasks)
                results.update(dict(zip(batch, batch_results)))
        return results

    async def _get_single_word_info(self, client, word):
        """处理单个单词"""
        # 检查缓存
        cached = self.cache.get(word)
        if cached:
            return cached

        try:
            response = await client.post(
                DEEPSEEK_API_BASE + "/completions",
                headers=self.headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"请提供单词 {word} 的详细信息"}
                    ]
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"API请求失败: {response.status_code}")
                
            result = response.json()
            formatted = self._format_response(word, result['choices'][0]['message']['content'])
            # 保存到缓存
            self.cache.set(word, formatted)
            return formatted
            
        except Exception as e:
            print(f"API 调用错误: {str(e)}")
            return self._get_empty_response(word, str(e))

    def _format_response(self, word, content):
        formatted = {
            "word": word,
            "mnemonic": "",
            "etymology": "",
            "usage": "",
            "definition": ""
        }
        
        # 分离 HTML 部分并合并所有内容到 mnemonic 字段
        all_content = []
        sections = content.split("<div")
        for section in sections:
            if 'class="mnemonic"' in section or 'class="etymology"' in section:
                all_content.append(f"<div{section}")
        
        formatted["mnemonic"] = "".join(all_content)
        return formatted

    def _get_empty_response(self, word, error_msg):
        return {
            "word": word,
            "mnemonic": f"Error: {error_msg}",
            "etymology": "",
            "usage": "",
            "definition": ""
        }

if __name__ == "__main__":
    processor = WordProcessor()
    word = input("请输入一个单词: ")
    result = asyncio.run(processor.get_words_info_batch([word]))
    print(result)
