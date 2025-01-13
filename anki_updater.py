import asyncio
import requests
from config import ANKI_CONNECT_URL
from word_processor import WordProcessor

class AnkiUpdater:
    def __init__(self):
        self.processor = WordProcessor()

    async def update_cards(self, deck_name):
        cards = self._get_cards(deck_name)
        # 获取所有卡片信息
        all_fields = [self._get_card_fields(card_id) for card_id in cards]
        
        # 收集需要更新的单词
        words_to_update = []
        card_map = {}  # 用于保存单词到卡片ID的映射
        for card_id, fields in zip(cards, all_fields):
            word = fields.get("word", {}).get("value", "").strip()
            if word and not fields.get("mnemonic", {}).get("value", "").strip():
                words_to_update.append(word)
                card_map[word] = {"id": card_id, "fields": fields}

        if not words_to_update:
            print("没有需要更新的卡片")
            return

        # 批量获取单词信息
        results = await self.processor.get_words_info_batch(words_to_update)
        
        # 批量更新卡片
        for word, info in results.items():
            card_info = card_map.get(word)
            if card_info and info.get("mnemonic"):
                self._update_card_field(card_info["id"], "mnemonic", info["mnemonic"])
                self._add_tag_to_note(card_info["id"])
                print(f"已更新卡片 '{word}' 的记忆方法并添加标签")

    def _get_cards(self, deck_name):
        response = self._anki_request("findNotes", query=f"deck:{deck_name}")
        return response.get("result", [])

    def _get_card_fields(self, card_id):
        response = self._anki_request("notesInfo", notes=[card_id])
        return response.get("result", [{}])[0].get("fields", {})

    def _update_card_field(self, card_id, field_name, value):
        self._anki_request("updateNoteFields", 
                          note={"id": card_id, "fields": {field_name: value}})

    def _anki_request(self, action, **params):
        response = requests.post(ANKI_CONNECT_URL, json={
            "action": action,
            "version": 6,
            "params": params
        })
        response.raise_for_status()
        return response.json()

    def _add_tag_to_note(self, note_id):
        """使用 addTags 操作添加标签到笔记"""
        try:
            self._anki_request("addTags", 
                             notes=[note_id], 
                             tags="释义已添加")
            
            # 强制刷新笔记以确保标签更新
            self._anki_request("updateNoteFields",
                             note={"id": note_id, "fields": {}})
        except Exception as e:
            print(f"添加标签时出错: {str(e)}")

def main():
    updater = AnkiUpdater()
    asyncio.run(updater.update_cards("test"))

if __name__ == "__main__":
    main()
