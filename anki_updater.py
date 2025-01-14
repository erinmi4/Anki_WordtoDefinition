import asyncio
import requests
import urllib.parse
from config import ANKI_CONNECT_URL
from word_processor import WordProcessor, DeepSeekAPIError

class AnkiUpdater:
    def __init__(self, batch_size=20, api_batch_size=5, test_mode=True):
        self.processor = WordProcessor()
        self.batch_size = batch_size  # 每批处理的卡片数量
        self.api_batch_size = api_batch_size  # API调用的批次大小
        self.test_mode = test_mode
        self.max_retries = 3

    async def check_and_display_balance(self):
        """检查并显示API余额"""
        try:
            balance = await self.processor.check_balance()
            print("\nAPI余额信息:")
            
            # 如果获取到真实余额
            if balance['total_tokens'] > 0:
                print(f"总计额度: {balance['total_tokens']:,} tokens")
                print(f"已使用额度: {balance['used_tokens']:,} tokens")
                print(f"剩余额度: {balance['available_tokens']:,} tokens")
                
                # 估算处理成本
                avg_tokens_per_word = 500
                estimated_total = avg_tokens_per_word * self.batch_size
                print(f"\n预估本批次({self.batch_size}个单词)将使用约 {estimated_total:,} tokens")
                
                if balance['available_tokens'] < estimated_total:
                    print("\n警告: 剩余额度可能不足以完成本次处理！")
                    return await self._confirm_continue()
            else:
                print("无法获取准确的余额信息，但程序可以继续运行")
                print("建议在处理少量单词后检查效果")
                return await self._confirm_continue()
                
            return True
            
        except Exception as e:
            print(f"检查余额时出错: {str(e)}")
            print("将继续执行，但请注意监控API使用情况")
            return await self._confirm_continue()

    async def _confirm_continue(self):
        """询问用户是否继续"""
        if self.test_mode:
            return input("\n是否继续处理？(y/n): ").lower() == 'y'
        return True  # 自动模式下默认继续

    async def update_cards(self, deck_name):
        encoded_deck_name = urllib.parse.quote(deck_name)
        
        # 先检查余额
        if not await self.check_and_display_balance():
            if input("\n是否继续处理？(y/n): ").lower() != 'y':
                return
        
        try:
            unprocessed_cards = self._get_unprocessed_cards(encoded_deck_name)
            if not unprocessed_cards:
                print("没有需要更新的卡片")
                return

            total_cards = len(unprocessed_cards)
            print(f"\n找到 {total_cards} 张未处理的卡片")
            print(f"当前设置: 每批处理 {self.batch_size} 张卡片, API每次处理 {self.api_batch_size} 个单词")
            print(f"运行模式: {'测试模式' if self.test_mode else '自动模式'}")
            
            # 添加确认提示
            confirm = input("\n是否继续处理？(y/n): ").strip().lower()
            if confirm != 'y':
                print("已取消处理")
                return
            
            # 处理卡片
            await self._process_all_cards(unprocessed_cards, total_cards)

        except KeyboardInterrupt:
            print("\n用户中断处理")
        except Exception as e:
            print(f"处理过程中出错: {str(e)}")

    async def _process_all_cards(self, unprocessed_cards, total_cards):
        processed_count = 0
        
        for i in range(0, total_cards, self.batch_size):
            try:
                batch_cards = unprocessed_cards[i:i + self.batch_size]
                current_batch = min(i + self.batch_size, total_cards)
                
                print(f"\n处理进度: [{processed_count}/{total_cards}] ({(processed_count/total_cards)*100:.1f}%)")
                print(f"正在处理第 {i + 1} 到 {current_batch} 张卡片...")
                
                await self._process_batch(batch_cards)
                processed_count = current_batch
                
                print(f"批次完成！当前进度: {processed_count}/{total_cards} ({(processed_count/total_cards)*100:.1f}%)")
                
                # 测试模式下询问是否继续
                if self.test_mode and processed_count < total_cards:
                    continue_process = input("\n继续处理下一批？(y/n): ").strip().lower()
                    if continue_process != 'y':
                        print("\n用户选择停止处理")
                        break
                elif not self.test_mode:
                    # 非测试模式下添加短暂延迟
                    await asyncio.sleep(1)
                    
            except Exception as e:
                print(f"\n处理批次时出错: {str(e)}")
                if self.test_mode:
                    if input("\n是否继续处理下一批？(y/n): ").lower() != 'y':
                        break
                else:
                    print("继续处理下一批...")
                    await asyncio.sleep(2)  # 错误后稍长的延迟
                    continue

    async def _process_batch(self, batch_cards):
        """处理一批卡片"""
        words_to_update = []
        card_map = {}
        errors = []
        
        # 收集需要更新的单词
        for card_id in batch_cards:
            try:
                fields = self._get_card_fields(card_id)
                word = fields.get("word", {}).get("value", "").strip()
                if word:
                    words_to_update.append(word)
                    card_map[word] = {"id": card_id, "fields": fields}
            except Exception as e:
                errors.append(f"获取卡片 {card_id} 信息失败: {str(e)}")
                continue

        if not words_to_update:
            if errors:
                print("\n处理过程中出现以下错误:")
                for error in errors:
                    print(f"- {error}")
            return

        try:
            # 批量获取单词信息
            results = await self.processor.get_words_info_batch(words_to_update, batch_size=self.api_batch_size)
            
            # 更新卡片
            success_count = 0
            for word, info in results.items():
                card_info = card_map.get(word)
                if card_info and info.get("mnemonic"):
                    try:
                        await self._update_single_card(card_info["id"], word, info["mnemonic"])
                        success_count += 1
                    except Exception as e:
                        errors.append(f"更新卡片 '{word}' 失败: {str(e)}")

            # 显示处理结果统计
            print(f"\n批次处理完成:")
            print(f"- 成功更新: {success_count} 张卡片")
            if errors:
                print(f"- 失败数量: {len(errors)} 个")
                print("\n错误详情:")
                for error in errors:
                    print(f"- {error}")
            
        except DeepSeekAPIError as e:
            print(f"\nDeepSeek API 错误:")
            print(e.get_error_message())
            raise
        except Exception as e:
            print(f"\n未预期的错误: {str(e)}")
            raise

    async def _update_single_card(self, card_id: int, word: str, content: str):
        """更新单个卡片内容"""
        for attempt in range(self.max_retries):
            try:
                self._update_card_field(card_id, "mnemonic", content)
                self._add_tag_to_note(card_id)
                print(f"已更新卡片 '{word}'")
                return
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise Exception(f"更新失败: {str(e)}")
                await asyncio.sleep(1)

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
    print("欢迎使用Anki卡片更新工具！\n")
    
    # 获取批处理参数
    try:
        # 选择运行模式
        mode = input("请选择运行模式 (1: 测试模式, 2: 自动模式) [默认:1]: ").strip() or "1"
        test_mode = mode == "1"
        
        # 获取处理参数
        batch_size = int(input("请输入每批处理的卡片数量 (默认20): ").strip() or "20")
        api_batch_size = int(input("请输入API每次处理的单词数量 (默认5): ").strip() or "5")
        deck_name = input("请输入牌组名称 (默认为'test'): ").strip() or "test"
        
        print("\n参数确认:")
        print(f"- 运行模式: {'测试模式' if test_mode else '自动模式'}")
        print(f"- 每批处理卡片数: {batch_size}")
        print(f"- API批次大小: {api_batch_size}")
        print(f"- 目标牌组: {deck_name}")
        
        confirm = input("\n确认开始处理？(y/n): ").strip().lower()
        if confirm != 'y':
            print("已取消操作")
            return
            
        updater = AnkiUpdater(
            batch_size=batch_size,
            api_batch_size=api_batch_size,
            test_mode=test_mode
        )
        asyncio.run(updater.update_cards(deck_name))
        
    except ValueError:
        print("输入的数字格式不正确，请输入有效的数字。")
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    main()
