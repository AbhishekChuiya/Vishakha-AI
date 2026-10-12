# Database-backed conversations and messages for Vishakha AI Phase 2.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('assistant', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(name='ChatConversation', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('chat_id', models.CharField(max_length=105, unique=True)),
            ('application', models.CharField(choices=[('general','General'),('ticketing','Service Excellence Portal')], max_length=24)),
            ('title', models.CharField(default='New Chat', max_length=160)),
            ('pinned', models.BooleanField(default=False)),
            ('rendered_html', models.TextField(blank=True, default='')),
            ('workflow_state', models.JSONField(blank=True, default=dict)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
             related_name='vishakha_conversations', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering':['-updated_at']}),
        migrations.CreateModel(name='ChatMessage', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('role', models.CharField(choices=[('user','User'),('assistant','Assistant')], max_length=12)),
            ('content', models.TextField()),
            ('response_type', models.CharField(blank=True, default='', max_length=48)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
             related_name='messages', to='assistant.chatconversation')),
        ], options={'ordering':['id']}),
        migrations.AddIndex(model_name='chatconversation',index=models.Index(fields=['user','application','-updated_at'],name='vish_chat_user_app_idx')),
        migrations.AddIndex(model_name='chatmessage',index=models.Index(fields=['conversation','id'],name='vish_chat_msg_seq_idx')),
    ]
