#!/usr/bin/env python3
"""
Broadcast System for Admin Bot - Comprehensive broadcast functionality
"""

import asyncio
import os
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.filters import Command
from aiogram.exceptions import TelegramAPIError

from logging_config import get_logger
from db import get_all_users, get_all_students, get_user_by_id
from i18n import t, detect_lang_from_user
from config import ADMIN_CHAT_IDS

logger = get_logger(__name__)

class BroadcastManager:
    """Enhanced broadcast manager with inline button support"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.broadcast_states = {}  # Track broadcast operations per admin
        self.broadcast_queue = asyncio.Queue()
        self.current_broadcast = None
        self.broadcast_stats = {
            'total_recipients': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def get_state(self, chat_id: int) -> Dict[str, Any]:
        """Get or create broadcast state for chat"""
        if chat_id not in self.broadcast_states:
            self.broadcast_states[chat_id] = {
                'step': None,
                'data': {},
                'recipients': [],
                'message_type': None,
                'content': None,
                'inline_button': None,
                'created_at': datetime.now()
            }
        return self.broadcast_states[chat_id]
    
    def reset_state(self, chat_id: int):
        """Reset broadcast state for chat"""
        if chat_id in self.broadcast_states:
            del self.broadcast_states[chat_id]
        logger.info(f"Broadcast state reset for chat {chat_id}")
    
    async def handle_broadcast_start(self, callback: CallbackQuery):
        """Handle broadcast start"""
        if callback.from_user.id not in ADMIN_CHAT_IDS:
            await callback.answer("❌ Access denied")
            return
        
        state = self.get_state(callback.message.chat.id)
        state['step'] = 'ask_recipients'
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👥 Barcha o'quvchilar", callback_data="broadcast_recipients:all_students"),
                InlineKeyboardButton(text="👨‍🏫 Barcha o'qituvchilar", callback_data="broadcast_recipients:all_teachers")
            ],
            [
                InlineKeyboardButton(text="👥 Barcha foydalanuvchilar", callback_data="broadcast_recipients:all_users"),
                InlineKeyboardButton(text="🎯 Guruh bo'yicha", callback_data="broadcast_recipients:by_group")
            ],
            [
                InlineKeyboardButton(text="✏️ Qo'lda tanlang", callback_data="broadcast_recipients:custom")
            ]
        ])
        
        await callback.message.answer(
            "📢 <b>Broadcast yaratish</b>\n\n"
            "Qabul qiluvchilarni tanlang:",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        await callback.answer()
    
    async def handle_recipients_selection(self, callback: CallbackQuery):
        """Handle recipients selection"""
        state = self.get_state(callback.message.chat.id)
        recipients_type = callback.data.split(':', 1)[1]
        
        if recipients_type == 'all_students':
            students = get_all_students()
            state['recipients'] = students
            state['step'] = 'ask_content_type'
            
            await callback.message.answer(
                f"✅ {len(students)} ta o'quvchi tanlandi\n\n"
                "Endi yuboriladigan kontent turini tanlang:",
                reply_markup=self._get_content_type_keyboard(),
                parse_mode='HTML'
            )
            
        elif recipients_type == 'all_teachers':
            from db import get_all_teachers
            teachers = get_all_teachers()
            state['recipients'] = teachers
            state['step'] = 'ask_content_type'
            
            await callback.message.answer(
                f"✅ {len(teachers)} ta o'qituvchi tanlandi\n\n"
                "Endi yuboriladigan kontent turini tanlang:",
                reply_markup=self._get_content_type_keyboard(),
                parse_mode='HTML'
            )
            
        elif recipients_type == 'all_users':
            all_users = get_all_users()
            state['recipients'] = all_users
            state['step'] = 'ask_content_type'
            
            await callback.message.answer(
                f"✅ {len(all_users)} ta foydalanuvchi tanlandi\n\n"
                "Endi yuboriladigan kontent turini tanlang:",
                reply_markup=self._get_content_type_keyboard(),
                parse_mode='HTML'
            )
            
        elif recipients_type == 'by_group':
            # Implement group selection
            await callback.message.answer(
                "🔧 Guruh bo'yicha tanlash hozircha mavjud emas.\n"
                "Boshqa variantlardan birini tanlang."
            )
            
        elif recipients_type == 'custom':
            state['step'] = 'ask_custom_recipients'
            await callback.message.answer(
                "✏️ Qabul qiluvchilarni qo'lda kiriting (user_id lari vergul bilan ajratilgan):\n\n"
                "Masalan: 12345, 67890, 11111"
            )
        
        await callback.answer()
    
    def _get_content_type_keyboard(self) -> InlineKeyboardMarkup:
        """Get content type selection keyboard"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Matn", callback_data="broadcast_type:text"),
                InlineKeyboardButton(text="📄 Fayl", callback_data="broadcast_type:file")
            ],
            [
                InlineKeyboardButton(text="🖼️ Rasm", callback_data="broadcast_type:photo"),
                InlineKeyboardButton(text="🎥 Video", callback_data="broadcast_type:video")
            ],
            [
                InlineKeyboardButton(text="🎵 Audio", callback_data="broadcast_type:audio")
            ]
        ])
    
    async def handle_content_type_selection(self, callback: CallbackQuery):
        """Handle content type selection"""
        state = self.get_state(callback.message.chat.id)
        content_type = callback.data.split(':', 1)[1]
        
        state['message_type'] = content_type
        state['step'] = 'ask_content'
        
        instructions = {
            'text': "📝 Matn kiriting (inline tugma qo'shish uchun tugma qo'shmasdan keyin 'finish' deb yozing):",
            'file': "📄 Fayl yuboring (PDF, DOC, XLS va h.k.):",
            'photo': "🖼️ Rasm yuboring:",
            'video': "🎥 Video yuboring:",
            'audio': "🎵 Audio yuboring:"
        }
        
        await callback.message.answer(
            instructions.get(content_type, "📝 Kontent kiriting:"),
            reply_markup=self._get_cancel_keyboard()
        )
        await callback.answer()
    
    def _get_cancel_keyboard(self) -> InlineKeyboardMarkup:
        """Get cancel keyboard"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")]
        ])
    
    async def handle_content(self, message: Message):
        """Handle broadcast content"""
        state = self.get_state(message.chat.id)
        
        if not state.get('step'):
            return
        
        if state['step'] == 'ask_custom_recipients':
            await self._handle_custom_recipients(message, state)
        elif state['step'] == 'ask_content':
            await self._handle_content_input(message, state)
    
    async def _handle_custom_recipients(self, message: Message, state: Dict[str, Any]):
        """Handle custom recipients input"""
        try:
            recipient_ids = [int(x.strip()) for x in message.text.split(',') if x.strip().isdigit()]
            
            if not recipient_ids:
                await message.answer("❌ Noto'g'ri format. Iltimos, user_id larni vergul bilan ajrating.")
                return
            
            # Validate user IDs
            valid_users = []
            invalid_ids = []
            
            for user_id in recipient_ids:
                user = get_user_by_id(user_id)
                if user:
                    valid_users.append(user)
                else:
                    invalid_ids.append(user_id)
            
            if invalid_ids:
                await message.answer(
                    f"⚠️ Quyidagi user_id lar topilmadi: {', '.join(map(str, invalid_ids))}\n\n"
                    f"Topilganlar: {len(valid_users)} ta"
                )
                return
            
            state['recipients'] = valid_users
            state['step'] = 'ask_content_type'
            
            await message.answer(
                f"✅ {len(valid_users)} ta foydalanuvchi tanlandi\n\n"
                "Endi yuboriladigan kontent turini tanlang:",
                reply_markup=self._get_content_type_keyboard()
            )
            
        except ValueError:
            await message.answer("❌ Noto'g'ri format. Iltimos, raqamlarni vergul bilan ajrating.")
    
    async def _handle_content_input(self, message: Message, state: Dict[str, Any]):
        """Handle content input"""
        content_type = state['message_type']
        
        if content_type == 'text':
            if message.text:
                state['content'] = message.text
                state['step'] = 'ask_inline_button'
                await self._ask_inline_button(message, state)
            else:
                await message.answer("❌ Matn bo'sh. Iltimos, matn kiriting.")
        
        elif content_type == 'file':
            if message.document:
                state['content'] = message.document
                state['step'] = 'ask_inline_button'
                await self._ask_inline_button(message, state)
            else:
                await message.answer("❌ Fayl topilmadi. Iltimos, fayl yuboring.")
        
        elif content_type == 'photo':
            if message.photo:
                state['content'] = message.photo[-1]  # Get largest photo
                state['step'] = 'ask_inline_button'
                await self._ask_inline_button(message, state)
            else:
                await message.answer("❌ Rasm topilmadi. Iltimos, rasm yuboring.")
        
        elif content_type == 'video':
            if message.video:
                state['content'] = message.video
                state['step'] = 'ask_inline_button'
                await self._ask_inline_button(message, state)
            else:
                await message.answer("❌ Video topilmadi. Iltimos, video yuboring.")
        
        elif content_type == 'audio':
            if message.audio:
                state['content'] = message.audio
                state['step'] = 'ask_inline_button'
                await self._ask_inline_button(message, state)
            else:
                await message.answer("❌ Audio topilmadi. Iltimos, audio yuboring.")
    
    async def _ask_inline_button(self, message: Message, state: Dict[str, Any]):
        """Ask if user wants to add inline button"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, tugma qo'shish", callback_data="broadcast_add_button:yes"),
                InlineKeyboardButton(text="❌ Yo'q, tugmasiz", callback_data="broadcast_add_button:no")
            ]
        ])
        
        await message.answer(
            "🔗 Inline tugma qo'shishni xohlaysizmi?\n\n"
            "Tugma xabarning tagiga qo'shiladi va foydalanuvchi uni bosganda URLga o'tadi.",
            reply_markup=keyboard
        )
    
    async def handle_inline_button_decision(self, callback: CallbackQuery):
        """Handle inline button decision"""
        state = self.get_state(callback.message.chat.id)
        decision = callback.data.split(':', 1)[1]
        
        if decision == 'yes':
            state['step'] = 'ask_button_text'
            await callback.message.answer(
                "🔗 Tugma nomini kiriting (1-64 belgi):\n\n"
                "Masalan: 'Veb saytga o'tish' yoki 'To\'lov qilish'",
                reply_markup=self._get_cancel_keyboard()
            )
        else:
            state['inline_button'] = None
            await self._show_preview(callback.message, state)
        
        await callback.answer()
    
    async def handle_button_text(self, message: Message):
        """Handle button text input"""
        state = self.get_state(message.chat.id)
        
        if not state.get('step') == 'ask_button_text':
            return
        
        button_text = message.text.strip()
        
        if not button_text:
            await message.answer("❌ Tugma nomi bo'sh. Iltimos, tugma nomini kiriting.")
            return
        
        if len(button_text) > 64:
            await message.answer("❌ Tugma nomi 64 belgidan oshmasin. Iltimos, qisqaroq nom kiriting.")
            return
        
        state['inline_button'] = {'text': button_text}
        state['step'] = 'ask_button_url'
        
        await message.answer(
            f"✅ Tugma nomi: '{button_text}'\n\n"
            "Endi URL manzilini kiriting (https://, t.me/, mailto: bilan boshlanishi kerak):",
            reply_markup=self._get_cancel_keyboard()
        )
    
    async def handle_button_url(self, message: Message):
        """Handle button URL input"""
        state = self.get_state(message.chat.id)
        
        if not state.get('step') == 'ask_button_url':
            return
        
        button_url = message.text.strip()
        
        if not button_url:
            await message.answer("❌ URL manzili bo'sh. Iltimos, URL kiriting.")
            return
        
        # Basic URL validation
        if not (button_url.startswith('https://') or button_url.startswith('http://') or 
                button_url.startswith('t.me/') or button_url.startswith('mailto:')):
            await message.answer(
                "❌ Noto'g'ri URL format. URL quyidagilardan biri bilan boshlanishi kerak:\n"
                "• https://example.com\n"
                "• t.me/channel_name\n"
                "• mailto:email@example.com"
            )
            return
        
        state['inline_button']['url'] = button_url
        await self._show_preview(message, state)
    
    async def _show_preview(self, message: Message, state: Dict[str, Any]):
        """Show broadcast preview"""
        recipients = state['recipients']
        content_type = state['message_type']
        content = state['content']
        inline_button = state.get('inline_button')
        
        preview_text = (
            f"📋 <b>Broadcast Preview</b>\n\n"
            f"👥 Qabul qiluvchilar: {len(recipients)} ta\n"
            f"📝 Kontent turi: {content_type}\n"
        )
        
        if content_type == 'text':
            preview_text += f"💬 Matn: {content[:100]}{'...' if len(content) > 100 else ''}\n"
        elif content_type == 'file':
            preview_text += f"📄 Fayl: {content.file_name}\n"
        elif content_type == 'photo':
            preview_text += f"🖼️ Rasm: {content.file_id}\n"
        elif content_type == 'video':
            preview_text += f"🎥 Video: {content.file_name}\n"
        elif content_type == 'audio':
            preview_text += f"🎵 Audio: {content.file_name}\n"
        
        if inline_button:
            preview_text += f"🔗 Tugma: {inline_button['text']} -> {inline_button['url']}\n"
        else:
            preview_text += "🔗 Tugma: Yo'q\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📤 Yuborish", callback_data="broadcast_confirm"),
                InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="broadcast_edit"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")
            ]
        ])
        
        await message.answer(preview_text, reply_markup=keyboard, parse_mode='HTML')
    
    async def handle_broadcast_confirm(self, callback: CallbackQuery):
        """Handle broadcast confirmation"""
        state = self.get_state(callback.message.chat.id)
        
        if not state.get('recipients') or not state.get('content'):
            await callback.answer("❌ Xatolik: Ma'lumotlar to'liq emas")
            return
        
        # Start broadcast
        await self._start_broadcast(callback.message, state)
        await callback.answer()
    
    async def handle_broadcast_edit(self, callback: CallbackQuery):
        """Handle broadcast edit"""
        state = self.get_state(callback.message.chat.id)
        state['step'] = 'ask_content_type'
        
        await callback.message.answer(
            "✏️ Kontentni qayta kiriting:",
            reply_markup=self._get_content_type_keyboard()
        )
        await callback.answer()
    
    async def handle_broadcast_cancel(self, callback: CallbackQuery):
        """Handle broadcast cancellation"""
        state = self.get_state(callback.message.chat.id)
        self.reset_state(callback.message.chat.id)
        
        await callback.message.answer("❌ Broadcast bekor qilindi.")
        await callback.answer()
    
    async def _start_broadcast(self, message: Message, state: Dict[str, Any]):
        """Start the actual broadcast"""
        recipients = state['recipients']
        content_type = state['message_type']
        content = state['content']
        inline_button = state.get('inline_button')
        
        # Reset statistics
        self.broadcast_stats = {
            'total_recipients': len(recipients),
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        await message.answer(
            f"📤 <b>Broadcast boshlandi...</b>\n\n"
            f"👥 Jami: {len(recipients)} ta qabul qiluvchi\n"
            f"⏳ Iltimos, biroz kutib turing...",
            parse_mode='HTML'
        )
        
        # Create preview message for testing
        test_message = await self._create_test_message(message.chat.id, content_type, content, inline_button)
        
        # Ask for confirmation to proceed
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, yuborish", callback_data="broadcast_proceed"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")
            ]
        ])
        
        await self.bot.send_message(
            message.chat.id,
            "🔍 <b>Test message:</b>\n\n"
            "Yuqoridagi xabarni ko'rib, yuborishni tasdiqlang:",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        
        # Store test message for actual broadcast
        state['test_message'] = test_message
    
    async def handle_broadcast_proceed(self, callback: CallbackQuery):
        """Proceed with actual broadcast"""
        state = self.get_state(callback.message.chat.id)
        
        if not state.get('test_message'):
            await callback.answer("❌ Xatolik: Test message topilmadi")
            return
        
        test_message = state['test_message']
        recipients = state['recipients']
        
        await callback.message.answer(
            "📤 <b>Broadcast yuborilmoqda...</b>\n\n"
            f"⏳ {len(recipients)} ta foydalanuvchiga yuborilmoqda...",
            parse_mode='HTML'
        )
        
        # Send broadcast to all recipients
        await self._send_broadcast_to_all(recipients, test_message, callback.message.chat.id)
        
        await callback.answer()
    
    async def _create_test_message(self, chat_id: int, content_type: str, content: Any, inline_button: Optional[Dict] = None) -> Dict[str, Any]:
        """Create test message for preview"""
        test_message = {
            'type': content_type,
            'content': content,
            'inline_button': inline_button
        }
        
        # Send test message to admin for verification
        try:
            if content_type == 'text':
                await self.bot.send_message(
                    chat_id,
                    content,
                    reply_markup=self._create_inline_keyboard(inline_button) if inline_button else None,
                    parse_mode='HTML'
                )
            elif content_type == 'file':
                await self.bot.send_document(
                    chat_id,
                    content,
                    caption="📋 <b>Test fayl</b>",
                    reply_markup=self._create_inline_keyboard(inline_button) if inline_button else None,
                    parse_mode='HTML'
                )
            elif content_type == 'photo':
                await self.bot.send_photo(
                    chat_id,
                    content,
                    caption="📋 <b>Test rasm</b>",
                    reply_markup=self._create_inline_keyboard(inline_button) if inline_button else None,
                    parse_mode='HTML'
                )
            elif content_type == 'video':
                await self.bot.send_video(
                    chat_id,
                    content,
                    caption="📋 <b>Test video</b>",
                    reply_markup=self._create_inline_keyboard(inline_button) if inline_button else None,
                    parse_mode='HTML'
                )
            elif content_type == 'audio':
                await self.bot.send_audio(
                    chat_id,
                    content,
                    caption="📋 <b>Test audio</b>",
                    reply_markup=self._create_inline_keyboard(inline_button) if inline_button else None,
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logger.error(f"Error creating test message: {e}")
            raise
        
        return test_message
    
    def _create_inline_keyboard(self, button: Optional[Dict]) -> Optional[InlineKeyboardMarkup]:
        """Create inline keyboard from button data"""
        if not button:
            return None
        
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button['text'], url=button['url'])]
        ])
    
    async def _send_broadcast_to_all(self, recipients: List[Dict], test_message: Dict, admin_chat_id: int):
        """Send broadcast to all recipients"""
        content_type = test_message['type']
        content = test_message['content']
        inline_button = test_message['inline_button']
        inline_keyboard = self._create_inline_keyboard(inline_button) if inline_button else None
        
        success_count = 0
        failed_count = 0
        
        for i, recipient in enumerate(recipients):
            try:
                if not recipient.get('telegram_id'):
                    self.broadcast_stats['skipped'] += 1
                    continue
                
                telegram_id = recipient['telegram_id']
                
                if content_type == 'text':
                    await self.bot.send_message(
                        telegram_id,
                        content,
                        reply_markup=inline_keyboard,
                        parse_mode='HTML'
                    )
                elif content_type == 'file':
                    await self.bot.send_document(
                        telegram_id,
                        content,
                        reply_markup=inline_keyboard,
                        parse_mode='HTML'
                    )
                elif content_type == 'photo':
                    await self.bot.send_photo(
                        telegram_id,
                        content,
                        reply_markup=inline_keyboard,
                        parse_mode='HTML'
                    )
                elif content_type == 'video':
                    await self.bot.send_video(
                        telegram_id,
                        content,
                        reply_markup=inline_keyboard,
                        parse_mode='HTML'
                    )
                elif content_type == 'audio':
                    await self.bot.send_audio(
                        telegram_id,
                        content,
                        reply_markup=inline_keyboard,
                        parse_mode='HTML'
                    )
                
                success_count += 1
                
                # Update progress every 10 messages
                if (i + 1) % 10 == 0:
                    progress = ((i + 1) / len(recipients)) * 100
                    await self.bot.send_message(
                        admin_chat_id,
                        f"📤 Progress: {progress:.1f}% ({i + 1}/{len(recipients)})\n"
                        f"✅ Muvaffaqiyatli: {success_count}\n"
                        f"❌ Xatolik: {failed_count}",
                        parse_mode='HTML'
                    )
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to send broadcast to {recipient['telegram_id']}: {e}")
        
        # Send final statistics
        self.broadcast_stats['successful'] = success_count
        self.broadcast_stats['failed'] = failed_count
        
        await self._send_final_statistics(admin_chat_id)
    
    async def _send_final_statistics(self, admin_chat_id: int):
        """Send final broadcast statistics"""
        stats = self.broadcast_stats
        total = stats['total_recipients']
        successful = stats['successful']
        failed = stats['failed']
        skipped = stats['skipped']
        
        success_rate = (successful / total * 100) if total > 0 else 0
        
        stats_text = (
            f"📊 <b>Broadcast yakunlandi!</b>\n\n"
            f"👥 Jami qabul qiluvchilar: {total}\n"
            f"✅ Muvaffaqiyatli: {successful}\n"
            f"❌ Xatolik: {failed}\n"
            f"⏭️ O'tkazildi: {skipped}\n"
            f"📈 Muvaffaqiyat foizi: {success_rate:.1f}%"
        )
        
        await self.bot.send_message(admin_chat_id, stats_text, parse_mode='HTML')
        
        # Reset state
        self.reset_state(admin_chat_id)
        
        logger.info(f"Broadcast completed: {successful}/{total} successful")

# Setup function for easy integration
def setup_broadcast_handlers(dp: Dispatcher, bot: Bot):
    """Setup broadcast handlers"""
    broadcast_manager = BroadcastManager(bot)
    
    # Register callback handlers
    dp.callback_query(lambda c: c.data == 'broadcast_start')(broadcast_manager.handle_broadcast_start)
    dp.callback_query(lambda c: c.data.startswith('broadcast_recipients:'))(broadcast_manager.handle_recipients_selection)
    dp.callback_query(lambda c: c.data.startswith('broadcast_type:'))(broadcast_manager.handle_content_type_selection)
    dp.callback_query(lambda c: c.data.startswith('broadcast_add_button:'))(broadcast_manager.handle_inline_button_decision)
    dp.callback_query(lambda c: c.data == 'broadcast_confirm')(broadcast_manager.handle_broadcast_confirm)
    dp.callback_query(lambda c: c.data == 'broadcast_edit')(broadcast_manager.handle_broadcast_edit)
    dp.callback_query(lambda c: c.data == 'broadcast_cancel')(broadcast_manager.handle_broadcast_cancel)
    dp.callback_query(lambda c: c.data == 'broadcast_proceed')(broadcast_manager.handle_broadcast_proceed)
    
    # Register message handlers
    dp.message(broadcast_manager.handle_content)
    
    logger.info("Broadcast handlers setup completed")
    return broadcast_manager
