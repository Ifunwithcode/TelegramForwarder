import logging
import os
from filters.base_filter import BaseFilter
from enums.enums import PreviewMode

logger = logging.getLogger(__name__)

class SenderFilter(BaseFilter):
    """
    消息发送过滤器，用于发送处理后的消息
    """
    
    async def _process(self, context):
        """
        发送处理后的消息
        
        Args:
            context: 消息上下文
            
        Returns:
            bool: 是否继续处理
        """
        rule = context.rule
        client = context.client
        event = context.event
        
        # 如果不应该转发，直接返回
        if not context.should_forward:
            logger.info('消息不满足转发条件，跳过发送')
            return False
            
        # 获取目标聊天信息
        target_chat = rule.target_chat
        target_chat_id = int(target_chat.telegram_chat_id)
        
        # 设置消息格式
        parse_mode = rule.message_mode.value  # 使用枚举的值（字符串）
        logger.info(f'使用消息格式: {parse_mode}')
        
        try:
            # 处理媒体组消息
            if context.is_media_group:
                await self._send_media_group(context, target_chat_id, parse_mode)
            # 处理单条媒体消息
            elif context.media_files:
                await self._send_single_media(context, target_chat_id, parse_mode)
            # 处理纯文本消息
            else:
                await self._send_text_message(context, target_chat_id, parse_mode)
                
            logger.info(f'消息已发送到: {target_chat.name} ({target_chat_id})')
            return True
        except Exception as e:
            logger.error(f'发送消息时出错: {str(e)}')
            context.errors.append(f"发送消息错误: {str(e)}")
            return False
    
    async def _send_media_group(self, context, target_chat_id, parse_mode):
        """发送媒体组消息"""
        rule = context.rule
        client = context.client
        
        # 如果所有媒体都超限了，但有文本，就发送文本和提示
        if not context.media_group_messages and context.message_text:
            # 构建提示信息
            skipped_info = "\n".join(f"- {size/1024/1024:.1f}MB" for _, size in context.skipped_media)
            text_to_send = (
                f"{context.message_text}\n\n⚠️ {len(context.skipped_media)} 个媒体文件超过大小限制:\n{skipped_info}"
            )
            
            # 组合完整文本
            text_to_send = context.sender_info + text_to_send + context.time_info + context.original_link
            
            await client.send_message(
                target_chat_id,
                text_to_send,
                parse_mode=parse_mode,
                link_preview=True,
                buttons=context.buttons
            )
            logger.info(f'媒体组所有文件超限，已发送文本和提示')
            return
            
        # 如果有可以发送的媒体，作为一个组发送
        try:
            files = []
            for message in context.media_group_messages:
                if message.media:
                    file_path = await message.download_media(os.path.join(os.getcwd(), 'temp'))
                    if file_path:
                        files.append(file_path)
            
            if files:
                # 添加发送者信息、时间信息和原始链接
                caption_text = context.sender_info + context.message_text + context.time_info + context.original_link
                
                # 作为一个组发送所有文件
                await client.send_file(
                    target_chat_id,
                    files,
                    caption=caption_text,
                    parse_mode=parse_mode,
                    buttons=context.buttons,
                    link_preview={
                        PreviewMode.ON: True,
                        PreviewMode.OFF: False,
                        PreviewMode.FOLLOW: context.event.message.media is not None
                    }[rule.is_preview]
                )
                logger.info(f'媒体组消息已发送')
            
            # 删除临时文件
            for file_path in files:
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f'删除临时文件失败: {str(e)}')
        except Exception as e:
            logger.error(f'发送媒体组消息时出错: {str(e)}')
            raise
    
    async def _send_single_media(self, context, target_chat_id, parse_mode):
        """发送单条媒体消息"""
        rule = context.rule
        client = context.client
        
        # 检查是否所有媒体都超限
        if context.skipped_media and not context.media_files:
            # 构建提示信息
            file_size = context.skipped_media[0][1]
            original_link = f"https://t.me/c/{str(context.event.chat_id)[4:]}/{context.event.message.id}"
            
            text_to_send = context.message_text or ''
            text_to_send += f"\n\n⚠️ 媒体文件 ({file_size/1024/1024:.1f}MB) 超过大小限制"
            text_to_send = context.sender_info + text_to_send + context.time_info
            
            if rule.is_original_link:
                text_to_send += original_link
                
            await client.send_message(
                target_chat_id,
                text_to_send,
                parse_mode=parse_mode,
                link_preview=True,
                buttons=context.buttons
            )
            logger.info(f'媒体文件超过大小限制，仅转发文本')
            return
            
        # 发送媒体文件
        for file_path in context.media_files:
            try:
                caption = (
                    context.sender_info + 
                    context.message_text + 
                    context.time_info + 
                    context.original_link
                )
                
                await client.send_file(
                    target_chat_id,
                    file_path,
                    caption=caption,
                    parse_mode=parse_mode,
                    buttons=context.buttons,
                    link_preview={
                        PreviewMode.ON: True,
                        PreviewMode.OFF: False,
                        PreviewMode.FOLLOW: context.event.message.media is not None
                    }[rule.is_preview]
                )
                logger.info(f'媒体消息已发送')
                
                # 删除临时文件
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f'删除临时文件失败: {str(e)}')
            except Exception as e:
                logger.error(f'发送媒体消息时出错: {str(e)}')
                raise
    
    async def _send_text_message(self, context, target_chat_id, parse_mode):
        """发送纯文本消息"""
        rule = context.rule
        client = context.client
        
        if not context.message_text:
            logger.info('没有文本内容，不发送消息')
            return
            
        # 根据预览模式设置 link_preview
        link_preview = {
            PreviewMode.ON: True,
            PreviewMode.OFF: False,
            PreviewMode.FOLLOW: context.event.message.media is not None  # 跟随原消息
        }[rule.is_preview]
        
        # 组合消息文本
        message_text = context.sender_info + context.message_text + context.time_info + context.original_link
        
        await client.send_message(
            target_chat_id,
            message_text,
            parse_mode=parse_mode,
            link_preview=link_preview,
            buttons=context.buttons
        )
        logger.info(f'{"带预览的" if link_preview else "无预览的"}文本消息已发送') 