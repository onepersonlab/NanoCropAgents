"""
通知渠道模块 - NanoCropAgents 看板服务器

支持多种通知渠道：飞书、Telegram、Discord、Slack、企业微信等
"""
import urllib.request
import urllib.error
import json
import logging

logger = logging.getLogger('channels')

# ── 渠道注册表 ──

CHANNELS = {}

def register_channel(cls):
    """注册通知渠道类。"""
    CHANNELS[cls.type] = cls
    return cls

def get_channel(channel_type: str):
    """获取渠道类。"""
    return CHANNELS.get(channel_type)

def get_channel_info():
    """返回所有渠道的信息列表。"""
    return [
        {'type': cls.type, 'label': cls.label, 'description': cls.description}
        for cls in CHANNELS.values()
    ]


# ── 基类 ──

class BaseChannel:
    """通知渠道基类。"""
    type = 'base'
    label = '基类'
    description = '基础通知渠道'
    
    @classmethod
    def validate_webhook(cls, webhook_url: str) -> bool:
        """验证 webhook URL 格式。"""
        return bool(webhook_url and webhook_url.startswith('http'))
    
    @classmethod
    def send(cls, webhook_url: str, title: str, content: str, url: str = '') -> bool:
        """发送通知（子类实现）。"""
        raise NotImplementedError


# ── 飞书 ──

@register_channel
class FeishuChannel(BaseChannel):
    type = 'feishu'
    label = '飞书'
    description = '飞书机器人 webhook'
    
    @classmethod
    def validate_webhook(cls, webhook_url: str) -> bool:
        return webhook_url and webhook_url.startswith('https://open.feishu.cn/')
    
    @classmethod
    def send(cls, webhook_url: str, title: str, content: str, url: str = '') -> bool:
        if not cls.validate_webhook(webhook_url):
            logger.warning(f'飞书 webhook URL 无效: {webhook_url}')
            return False
        
        # 飞书消息卡片格式
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "blue"
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": content}},
                    {"tag": "action", "actions": [
                        {"tag": "button", "text": {"tag": "plain_text", "content": "查看详情"},
                         "url": url, "type": "primary"}
                    ] if url else []}
                ]
            }
        }
        
        try:
            data = json.dumps(card).encode('utf-8')
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get('StatusCode', -1) == 0
        except Exception as e:
            logger.warning(f'飞书推送失败: {e}')
            return False


# ── Telegram ──

@register_channel
class TelegramChannel(BaseChannel):
    type = 'telegram'
    label = 'Telegram'
    description = 'Telegram Bot API'
    
    @classmethod
    def validate_webhook(cls, webhook_url: str) -> bool:
        # Telegram webhook 格式: https://api.telegram.org/bot{token}/sendMessage
        return webhook_url and 'telegram.org' in webhook_url
    
    @classmethod
    def send(cls, webhook_url: str, title: str, content: str, url: str = '') -> bool:
        text = f"**{title}**\n\n{content}"
        if url:
            text += f"\n\n[查看详情]({url})"
        
        payload = {
            "text": text,
            "parse_mode": "Markdown"
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get('ok', False)
        except Exception as e:
            logger.warning(f'Telegram 推送失败: {e}')
            return False


# ── Discord ──

@register_channel
class DiscordChannel(BaseChannel):
    type = 'discord'
    label = 'Discord'
    description = 'Discord webhook'
    
    @classmethod
    def validate_webhook(cls, webhook_url: str) -> bool:
        return webhook_url and 'discord.com/api/webhooks' in webhook_url
    
    @classmethod
    def send(cls, webhook_url: str, title: str, content: str, url: str = '') -> bool:
        payload = {
            "content": f"**{title}**\n{content}",
        }
        if url:
            payload["embeds"] = [{"title": title, "description": content, "url": url}]
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 204 or resp.status == 200
        except Exception as e:
            logger.warning(f'Discord 推送失败: {e}')
            return False


# ── Slack ──

@register_channel
class SlackChannel(BaseChannel):
    type = 'slack'
    label = 'Slack'
    description = 'Slack webhook'
    
    @classmethod
    def validate_webhook(cls, webhook_url: str) -> bool:
        return webhook_url and 'hooks.slack.com' in webhook_url
    
    @classmethod
    def send(cls, webhook_url: str, title: str, content: str, url: str = '') -> bool:
        payload = {
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": title}},
                {"type": "section", "text": {"type": "mrkdwn", "text": content}}
            ]
        }
        if url:
            payload["blocks"].append({
                "type": "actions",
                "elements": [{"type": "button", "text": {"type": "plain_text", "text": "查看详情"},
                             "url": url}]
            })
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f'Slack 推送失败: {e}')
            return False


# ── 企业微信 ──

@register_channel
class WecomChannel(BaseChannel):
    type = 'wecom'
    label = '企业微信'
    description = '企业微信 webhook'
    
    @classmethod
    def validate_webhook(cls, webhook_url: str) -> bool:
        return webhook_url and 'qyapi.weixin.qq.com' in webhook_url
    
    @classmethod
    def send(cls, webhook_url: str, title: str, content: str, url: str = '') -> bool:
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"## {title}\n\n{content}\n\n[点击查看详情]({url})" if url else f"## {title}\n\n{content}"
            }
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get('errcode', -1) == 0
        except Exception as e:
            logger.warning(f'企业微信推送失败: {e}')
            return False


# ── 通用 Webhook ──

@register_channel
class WebhookChannel(BaseChannel):
    type = 'webhook'
    label = '通用 Webhook'
    description = '通用 HTTP webhook'
    
    @classmethod
    def send(cls, webhook_url: str, title: str, content: str, url: str = '') -> bool:
        payload = {"title": title, "content": content, "url": url}
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f'Webhook 推送失败: {e}')
            return False