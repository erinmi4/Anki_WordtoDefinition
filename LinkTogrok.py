import requests
import openai
from word_processor import WordProcessor

ANKI_CONNECT_URL = "http://localhost:8765"
DEEPSEEK_API_KEY = "sk-0b00a078c14244478023355e727c4c2b"

def update_card_field(card_id, field_name, value):
    payload = {
        "action": "updateNoteFields",
        "version": 6,
        "params": {
            "note": {
                "id": card_id,
                "fields": {
                    field_name: value
                }
            }
        }
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload)
    response.raise_for_status()
    return response.json()["result"]

def get_cards(deck_name):
    payload = {
        "action": "findNotes",
        "version": 6,
        "params": {
            "query": f"deck:{deck_name}"
        }
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload)
    response.raise_for_status()
    return response.json()["result"]

def get_card_fields(card_id):
    payload = {
        "action": "notesInfo",
        "version": 6,
        "params": {
            "notes": [card_id]
        }
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload)
    response.raise_for_status()
    return response.json()["result"][0]["fields"]

def main():
    deck_name = "test"  # 替换为目标 Deck 的名字
    cards = get_cards(deck_name)
    processor = WordProcessor(api_key=DEEPSEEK_API_KEY)

    for card_id in cards:
        fields = get_card_fields(card_id)
        print(fields)  # 打印 fields 字典内容以调试
        try:
            word = fields.get("word", {}).get("value", None)
            if not word:
                raise KeyError("word")
            # 直接获取释义并更新卡片，不检查是否已存在
            word_info = processor.get_word_info(word)
            new_definition = word_info["definitions"]
            mnemonic = word_info["mnemonic"]
            update_card_field(card_id, "definition", new_definition)
            if mnemonic:
                update_card_field(card_id, "mnemonic", mnemonic)
            print(f"Updated card '{word}' with new definition and mnemonic.")
        except KeyError:
            print(f"Error: 'word' field not found in card {card_id}.")
        except Exception as e:
            print(f"Error processing card {card_id}: {e}")

if __name__ == "__main__":
    main()