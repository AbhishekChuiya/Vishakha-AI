"""Run: python manage.py test apps.assistant.test_persistence"""
import json
from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import ChatConversation, ChatMessage


class ChatPersistenceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.a = User.objects.create_user(username='phase2a', password='SafePass123!', email='a@example.com')
        self.b = User.objects.create_user(username='phase2b', password='SafePass123!', email='b@example.com')
        self.client.force_login(self.a)

    def post(self, url, obj):
        return self.client.post(url, data=json.dumps(obj), content_type='application/json')

    def test_save_list_and_restore_after_login(self):
        r = self.post('/api/chat/library/save/', {
            'chat_id':'gen_test_persist_001', 'application':'general',
            'title':'Follow up email', 'pinned':True,
            'html':'<div class="message">Hello</div>'})
        self.assertEqual(r.status_code, 200)
        record = ChatConversation.objects.get(chat_id='gen_test_persist_001')
        ChatMessage.objects.create(conversation=record, role='user', content='Hello')
        self.client.logout()
        self.client.force_login(self.a)
        r = self.client.get('/api/chat/library/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()['chats']), 1)
        self.assertEqual(r.json()['chats'][0]['title'], 'Follow up email')
        self.assertTrue(r.json()['chats'][0]['pinned'])
        self.assertEqual(record.messages.count(), 1)

    def test_cannot_read_or_take_over_other_users_chat(self):
        self.post('/api/chat/library/save/', {
            'chat_id':'sep_ownership_001', 'application':'ticketing',
            'title':'Private chat', 'html':'private'})
        self.client.force_login(self.b)
        self.assertEqual(self.client.get('/api/chat/library/').json()['chats'], [])
        r = self.post('/api/chat/library/save/', {
            'chat_id':'sep_ownership_001','application':'ticketing',
            'title':'Overwritten', 'html':'hijack'})
        self.assertEqual(r.status_code, 404)
        r = self.post('/api/chat/delete/', {'chat_id':'sep_ownership_001'})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(ChatConversation.objects.get(chat_id='sep_ownership_001').title, 'Private chat')

    def test_application_mismatch_is_rejected(self):
        r = self.post('/api/chat/library/save/', {
            'chat_id':'gen_app_mismatch_001', 'application':'ticketing', 'html':''})
        self.assertEqual(r.status_code, 400)

    def test_delete_cascades_messages(self):
        self.post('/api/chat/library/save/', {
            'chat_id':'gen_deletion_001', 'application':'general', 'html':'hello'})
        chat = ChatConversation.objects.get(chat_id='gen_deletion_001')
        ChatMessage.objects.create(conversation=chat, role='user', content='hello')
        r = self.post('/api/chat/delete/', {'chat_id':'gen_deletion_001'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(ChatConversation.objects.filter(chat_id='gen_deletion_001').exists())
        self.assertFalse(ChatMessage.objects.exists())

    def test_requires_login(self):
        self.client.logout()
        r = self.client.get('/api/chat/library/')
        self.assertNotEqual(r.status_code, 200)
