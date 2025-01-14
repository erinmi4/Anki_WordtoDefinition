import asyncio
import httpx
from typing import List, Dict, Any
from config import (DEEPSEEK_API_KEY, SYSTEM_PROMPT, DEEPSEEK_API_BASE, 
                   API_CONFIG, HTML_TEMPLATE, BALANCE_URL)
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
        self.semaphore = asyncio.Semaphore(3)  # 限制并发请求数

    async def check_balance(self) -> Dict[str, Any]:
        """检查API余额"""
        async with httpx.AsyncClient() as client:
            response = await client.get(BALANCE_URL, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return {
                    "total_tokens": data.get("total_tokens", 0),
                    "used_tokens": data.get("used_tokens", 0),
                    "available_tokens": data.get("available_tokens", 0)
                }
            raise Exception(f"获取余额失败: {response.status_code} - {response.text}")

    async def get_words_info_batch(self, words: List[str], batch_size: int = 5) -> Dict[str, Any]:
        results = {}
        tasks = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for word in words:
                if cached := self.cache.get(word):
                    results[word] = cached
                    print(f"从缓存获取 '{word}' 的信息")
                    continue
                tasks.append(self._get_single_word_info_with_retry(client, word))
            
            if tasks:
                async with asyncio.TaskGroup() as tg:
                    word_tasks = [tg.create_task(task) for task in tasks]
                
                for word, task in zip([w for w in words if w not in results], word_tasks):
                    try:
                        result = task.result()
                        results[word] = result
                    except Exception as e:
                        print(f"处理单词 '{word}' 失败: {str(e)}")
                        results[word] = self._get_empty_response(word, str(e))
        
        return results

    async def _get_single_word_info_with_retry(self, client, word: str) -> Dict[str, Any]:
        async with self.semaphore:  # 使用信号量控制并发
            for attempt in range(self.retry_count):
                try:
                    response = await client.post(
                        f"{DEEPSEEK_API_BASE}/chat/completions",
                        headers=self.headers,
                        json={
                            **API_CONFIG,
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": f"分析单词: {word}"}
                            ]
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result['choices'][0]['message']['content']
                        formatted = self._format_response(word, content)
                        self.cache.set(word, formatted)
                        return formatted
                    elif response.status_code == 429:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    else:
                        response.raise_for_status()
                        
                except Exception as e:
                    if attempt < self.retry_count - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    raise
            
            raise Exception(f"重试 {self.retry_count} 次后失败")

    def _format_response(self, word: str, content: str) -> Dict[str, Any]:
        try:
            # 解析 JSON 响应
            data = json.loads(content)
            # 使用模板格式化输出
            formatted_content = HTML_TEMPLATE.format(
                word_structure=data['mnemonic']['word_structure'],
                memory_method=data['mnemonic']['memory_method'],
                practical_usage=data['mnemonic']['practical_usage'],
                root_origin=data['etymology']['root_origin'],
                meaning_evolution=data['etymology']['meaning_evolution'],
                related_words=data['etymology']['related_words']
            )
            return {"word": word, "mnemonic": formatted_content}
        except Exception as e:
            print(f"格式化响应失败: {str(e)}")
            return self._get_empty_response(word, str(e))

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
