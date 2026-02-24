# chat/consumers.py - UPDATED VERSION
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Conversation, Message, TypingIndicator

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close(code=4001)
            return
        
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'chat_{self.conversation_id}'
        
        # Verify user has access to this conversation
        if not await self.verify_conversation_access():
            await self.close(code=4003)
            return
        
        # Store user as online
        await self.set_user_online(True)
        
        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'WebSocket connected successfully'
        }))
    
    async def disconnect(self, close_code):
        # Mark user as offline
        await self.set_user_online(False)
        
        await self.channel_layer.group_discard(
            self.conversation_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.handle_ping()
            elif message_type == 'message':
                await self.handle_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
        except json.JSONDecodeError:
            print("Invalid JSON received")
    
    async def handle_ping(self):
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': timezone.now().isoformat()
        }))
    
    async def handle_message(self, data):
        content = data.get('content')
        message_type = data.get('message_type', 'text')
        
        message = await self.save_message(content, message_type)
        
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'chat_message',
                'message': await self.serialize_message(message)
            }
        )
    async def handle_typing(self, data):
        is_typing = data.get('is_typing', False)
        
        await self.update_typing_indicator(is_typing)
        
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'typing_indicator',
                'conversation_id': self.conversation_id,  # ADD THIS
                'user_id': self.user.id,
                'is_typing': is_typing,
                'user_name': f"{self.user.first_name} {self.user.last_name}"
            }
    )
        
    async def handle_read_receipt(self, data):
        message_id = data.get('message_id')
        
        # Mark message as read
        await self.mark_message_as_read(message_id)
        
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'read_receipt',
                'message_id': message_id,
                'user_id': self.user.id,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'data': event['message']
        }))
    
    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'conversation_id': event['conversation_id'],  # ADD THIS
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'is_typing': event['is_typing']
        }))
    
    async def read_receipt(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'timestamp': event['timestamp']
        }))
    
    @database_sync_to_async
    def verify_conversation_access(self):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return self.user in [conversation.recruiter.user, conversation.job_seeker.user]
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def set_user_online(self, is_online):
        from django.core.cache import cache
        cache_key = f'user_online_{self.user.id}'
        
        if is_online:
            cache.set(cache_key, timezone.now().isoformat(), timeout=300)  # 5 minutes
        else:
            cache.delete(cache_key)
        
        # Also update last_seen in user profile
        try:
            from accounts.models import CustomUser
            user = CustomUser.objects.get(id=self.user.id)
            user.last_seen = timezone.now()
            user.save(update_fields=['last_seen'])
        except Exception as e:
            print(f"Error updating last_seen: {e}")

    
    @database_sync_to_async
    def save_message(self, content, message_type):
        conversation = Conversation.objects.get(id=self.conversation_id)
        
        if self.user == conversation.recruiter.user:
            receiver = conversation.job_seeker.user
        else:
            receiver = conversation.recruiter.user
        
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            receiver=receiver,
            content=content,
            message_type=message_type,
            status='delivered'
        )
        
        # Update conversation
        conversation.last_message_at = timezone.now()
        
        # Increment unread count for receiver
        if receiver == conversation.recruiter.user:
            conversation.unread_by_recruiter += 1
        else:
            conversation.unread_by_job_seeker += 1
        
        conversation.save()
        
        return message
    
    @database_sync_to_async
    def update_typing_indicator(self, is_typing):
        conversation = Conversation.objects.get(id=self.conversation_id)
        
        typing_indicator, created = TypingIndicator.objects.get_or_create(
            conversation=conversation,
            user=self.user
        )
        typing_indicator.is_typing = is_typing
        typing_indicator.last_typing_at = timezone.now()
        typing_indicator.save()
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        try:
            message = Message.objects.get(id=message_id, receiver=self.user)
            message.mark_as_read()
            
            # Update conversation unread count
            conversation = message.conversation
            if self.user == conversation.recruiter.user:
                conversation.unread_by_recruiter = max(0, conversation.unread_by_recruiter - 1)
            else:
                conversation.unread_by_job_seeker = max(0, conversation.unread_by_job_seeker - 1)
            conversation.save()
            
            return message
        except Message.DoesNotExist:
            return None
    
    @database_sync_to_async
    def serialize_message(self, message):
        """Serialize message for WebSocket"""
        from django.core.cache import cache
        
        # Check if receiver is online
        receiver_cache_key = f'user_online_{message.receiver.id}'
        receiver_online = cache.get(receiver_cache_key) is not None
        
        # Get attachments
        attachments_data = []
        for attachment in message.message_attachments.all():
            attachments_data.append({
                'id': attachment.id,
                'file_name': attachment.file_name,
                'file_size': attachment.file_size,
                'file_type': attachment.file_type,
                'file_url': attachment.file.url if attachment.file else None,
                'is_image': attachment.is_image(),
                'uploaded_at': attachment.uploaded_at.isoformat() if attachment.uploaded_at else None
            })
        
        return {
            'id': message.id,
            'conversation': message.conversation.id,
            'sender': {
                'id': message.sender.id,
                'first_name': message.sender.first_name,
                'last_name': message.sender.last_name,
                'email': message.sender.email,
                'is_online': message.sender.id == self.user.id or cache.get(f'user_online_{message.sender.id}') is not None
            },
            'receiver': {
                'id': message.receiver.id,
                'first_name': message.receiver.first_name,
                'last_name': message.receiver.last_name,
                'email': message.receiver.email,
                'is_online': receiver_online
            },
            'content': message.content,
            'message_type': message.message_type,
            'status': message.status,
            'created_at': message.created_at.isoformat(),
            'read_at': message.read_at.isoformat() if message.read_at else None,
            'attachments': attachments_data,
            'is_own_message': message.sender.id == self.user.id
        }