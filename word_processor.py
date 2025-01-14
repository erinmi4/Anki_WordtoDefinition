import asyncio
import httpx
from typing import List, Dict, Any
from config import DEEPSEEK_API_KEY, SYSTEM_PROMPT, DEEPSEEK_API_BASE, API_CONFIG
from cache_manager import CacheManager

class WordProcessor:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        self.cache = CacheManager()
        self.retry_count = 3
        self.retry_delay = 2

    async def get_words_info_batch(self, words: List[str], batch_size: int = 5) -> Dict[str, Any]:
        """批量处理单词，添加重试机制"""
        results = {}
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(0, len(words), batch_size):
                batch = words[i:i + batch_size]
                tasks = []
                for word in batch:
                    # 检查缓存
                    cached = self.cache.get(word)
                    if cached:
                        results[word] = cached
                        print(f"从缓存获取 '{word}' 的信息")
                        continue
                    tasks.append(self._get_single_word_info_with_retry(client, word))
                
                if tasks:
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    for word, result in zip([w for w in batch if w not in results], batch_results):
                        if isinstance(result, Exception):
                            print(f"处理单词 '{word}' 失败: {str(result)}")
                            results[word] = self._get_empty_response(word, str(result))
                        else:
                            results[word] = result
                
                # 批次间隔
                if i + batch_size < len(words):
                    await asyncio.sleep(1)
                
        return results

    async def _get_single_word_info_with_retry(self, client, word: str) -> Dict[str, Any]:
        """带重试机制的单词处理"""
        for attempt in range(self.retry_count):
            try:
                response = await client.post(
                    DEEPSEEK_API_BASE + "/completions",
                    headers=self.headers,
                    json={
                        **API_CONFIG,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": f"请提供单词 {word} 的详细信息"}
                        ]
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    formatted = self._format_response(word, result['choices'][0]['message']['content'])
                    self.cache.set(word, formatted)
                    return formatted
                elif response.status_code == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    response.raise_for_status()
                    
            except httpx.TimeoutException:
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise
            except Exception as e:
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise
        
        raise Exception(f"重试 {self.retry_count} 次后仍然失败")

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
