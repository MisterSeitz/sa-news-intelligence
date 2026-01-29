import aiohttp
from apify import Actor
import os

async def send_discord_alert(webhook_url: str, article_data: dict):
    """
    Sends a rich embed to Discord for High Hype articles.
    """
    if not webhook_url:
        return

    embed = {
        "title": f"🔥 {article_data.get('category', 'News')} Alert: {article_data.get('sentiment', 'High Hype')}",
        "description": article_data.get('ai_summary', "No summary available."),
        "url": article_data.get('url'),
        "color": 16711680 if "High Hype" in article_data.get('sentiment', '') else 3447003, # Red for Hype, Blue otherwise
        "fields": [
            {
                "name": "Niche",
                "value": article_data.get('niche', 'Unknown'),
                "inline": True
            },
            {
                "name": "Source",
                "value": article_data.get('source_feed', 'Unknown'),
                "inline": True
            },
            {
                "name": "Entities",
                "value": ", ".join(article_data.get('key_entities', [])) or "None",
                "inline": False
            }
        ],
        "footer": {
            "text": "Niche Intelligence Actor 🕵️"
        }
    }

    payload = {
        "username": "Niche Scout",
        "embeds": [embed]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status == 204:
                    Actor.log.info("📢 Discord notification sent.")
                else:
                    Actor.log.warning(f"⚠️ Discord webhook failed: {response.status}")
    except Exception as e:
        Actor.log.error(f"❌ Discord notification error: {e}")
