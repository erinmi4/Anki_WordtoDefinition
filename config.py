DEEPSEEK_API_KEY = "sk-a98fb70181d44709876e81d83ab31fa5"
ANKI_CONNECT_URL = "http://localhost:8765"
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
BALANCE_URL = f"{DEEPSEEK_API_BASE}/user/balance"

# API 配置
API_CONFIG = {
    "model": "deepseek-chat",
    "temperature": 0.1,  # 降低随机性，提高一致性
    "top_p": 0.8,       # 调整采样范围
    "max_tokens": 1000,
    "frequency_penalty": 0.1,
    "presence_penalty": 0.1,
    "response_format": {"type": "json_object"},  # 使用 JSON 模式
    "stop": ["</div>"],
    "stream": False,
    "seed": 42,         # 添加随机种子以保持一致性
    "functions": [{      # 添加函数调用
        "name": "word_analysis",
        "description": "分析英语单词的记忆方法和词源",
        "parameters": {
            "type": "object",
            "properties": {
                "mnemonic": {
                    "type": "object",
                    "properties": {
                        "word_structure": {"type": "string", "description": "词形分析"},
                        "memory_method": {"type": "string", "description": "记忆方法"},
                        "practical_usage": {"type": "string", "description": "实际应用场景"}
                    },
                    "required": ["word_structure", "memory_method", "practical_usage"]
                },
                "etymology": {
                    "type": "object",
                    "properties": {
                        "root_origin": {"type": "string", "description": "词根来源"},
                        "meaning_evolution": {"type": "string", "description": "词义演变"},
                        "related_words": {"type": "string", "description": "相关词汇"}
                    },
                    "required": ["root_origin", "meaning_evolution", "related_words"]
                }
            },
            "required": ["mnemonic", "etymology"]
        }
    }]
}

SYSTEM_PROMPT = """你是一个专业的英语词汇教师。请以JSON格式返回单词分析，包含以下字段：
{
    "mnemonic": {
        "word_structure": "词形分析",
        "memory_method": "记忆方法",
        "practical_usage": "实际应用场景"
    },
    "etymology": {
        "root_origin": "词根来源",
        "meaning_evolution": "词义演变",
        "related_words": "相关词汇"
    }
}

要求：
1. 内容简明扼要，重点突出
2. 记忆方法要具体生动
3. 解释要通俗易懂"""

# HTML 模板
HTML_TEMPLATE = """
<div class="mnemonic">
<h4>联想记忆</h4>
<p>
1. 词形分析：{word_structure}<br><br>
2. 记忆方法：{memory_method}<br><br>
3. 实际场景：{practical_usage}
</p>
</div>

<div class="etymology">
<h4>词根词缀</h4>
<p>
1. 词根来源：{root_origin}<br><br>
2. 词义演变：{meaning_evolution}<br><br>
3. 相关词汇：{related_words}
</p>
</div>
"""
