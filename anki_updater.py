import asyncio
import requests
import urllib.parse
from config import ANKI_CONNECT_URL
from word_processor import WordProcessor

class AnkiUpdater:
    def __init__(self):
        self.processor = WordProcessor()
        self.batch_size = 50  # 每批处理的卡片数量

    async def update_cards(self, deck_name):
        # 对牌组名称进行URL编码以支持中文
        encoded_deck_name = urllib.parse.quote(deck_name)
        
        # 获取未处理的卡片
        unprocessed_cards = self._get_unprocessed_cards(encoded_deck_name)
        if not unprocessed_cards:
            print("没有需要更新的卡片")
            return

        total_cards = len(unprocessed_cards)
        print(f"找到 {total_cards} 张未处理的卡片")
        
        # 分批处理卡片
        for i in range(0, total_cards, self.batch_size):
            batch_cards = unprocessed_cards[i:i + self.batch_size]
            print(f"\n处理第 {i + 1} 到 {min(i + self.batch_size, total_cards)} 张卡片...")
            
            # 获取这批卡片的信息
            words_to_update = []
            card_map = {}
            
            for card_id in batch_cards:
                fields = self._get_card_fields(card_id)
                word = fields.get("word", {}).get("value", "").strip()
                if word:
                    words_to_update.append(word)
                    card_map[word] = {"id": card_id, "fields": fields}

            if not words_to_update:
                continue

            try:
                # 批量获取单词信息
                results = await self.processor.get_words_info_batch(words_to_update, batch_size=5)
                
                # 批量更新卡片
                batch_updated = 0
                for word, info in results.items():
                    card_info = card_map.get(word)
                    if card_info and info.get("mnemonic"):
                        try:
                            self._update_card_field(card_info["id"], "mnemonic", info["mnemonic"])
                            self._add_tag_to_note(card_info["id"])
                            batch_updated += 1
                            print(f"已更新卡片 '{word}'")
                        except Exception as e:
                            print(f"更新卡片 '{word}' 失败: {str(e)}")
                
                print(f"本批次完成，成功更新 {batch_updated} 张卡片")
                
                # 添加小段休息，避免过于频繁的请求
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"处理批次时出错: {str(e)}")
                continue

    def _get_unprocessed_cards(self, deck_name):
        """获取未添加标签的卡片"""
        query = f'deck:"{deck_name}" -tag:释义已添加'
        try:
            response = self._anki_request("findNotes", query=query)
            cards = response.get("result", [])
            return cards
        except Exception as e:
            print(f"获取卡片列表失败: {str(e)}")
            return []

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
    deck_name = input("请输入牌组名称 (默认为'test'): ").strip() or "test"
    try:
        asyncio.run(updater.update_cards(deck_name))
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    main()
