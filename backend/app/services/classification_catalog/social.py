from __future__ import annotations


def _entry(name: str) -> dict[str, str]:
    return {"name": name, "region": "GLOBAL", "country": "", "vertical": "social"}


SOCIAL: dict[str, dict[str, str]] = {
    "linkedin.com": _entry("LinkedIn"),
    "linkedinmail.com": _entry("LinkedIn"),
    "youtube.com": _entry("YouTube"),
    "youtubemail.com": _entry("YouTube"),
    "facebookmail.com": _entry("Facebook"),
    "facebook.com": _entry("Facebook"),
    "messenger.com": _entry("Messenger"),
    "meta.com": _entry("Meta"),
    "instagram.com": _entry("Instagram"),
    "x.com": _entry("X"),
    "twitter.com": _entry("X"),
    "tiktok.com": _entry("TikTok"),
    "pinterest.com": _entry("Pinterest"),
    "snapchat.com": _entry("Snapchat"),
    "snap.com": _entry("Snapchat"),
    "reddit.com": _entry("Reddit"),
    "redditmail.com": _entry("Reddit"),
    "whatsapp.com": _entry("WhatsApp"),
    "threads.net": _entry("Threads"),
    "nextdoor.com": _entry("Nextdoor"),
    "discord.com": _entry("Discord"),
    "twitch.tv": _entry("Twitch"),
    "tumblr.com": _entry("Tumblr"),
    "telegram.org": _entry("Telegram"),
    "slack.com": _entry("Slack"),
    "meetup.com": _entry("Meetup"),
    "nextdoor.co.uk": _entry("Nextdoor"),
    "behance.net": _entry("Behance"),
    "dribbble.com": _entry("Dribbble"),
}
