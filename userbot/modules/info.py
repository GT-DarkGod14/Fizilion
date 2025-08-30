import os
import html
import asyncio
from pathlib import Path
from typing import Optional, Tuple, Union, Any
from dataclasses import dataclass

from telethon import events, types
from telethon.errors import (
    UserIdInvalidError, UsernameNotOccupiedError, ChatAdminRequiredError,
    UserNotParticipantError, ChannelInvalidError, ChannelPrivateError, 
    PeerIdInvalidError, FloodWaitError
)
from telethon.tl.types import (
    MessageEntityMentionName, User, Channel, Chat,
    ChannelParticipantsAdmins
)
from telethon.tl.functions.users import GetFullUserRequest

from userbot import CMD_HELP, TEMP_DOWNLOAD_DIRECTORY, trgg
from userbot.events import register


@dataclass
class UserInfo:
    entity: User
    full_info: Any
    photo_path: Optional[str] = None


class InfoHandler:
    def __init__(self):
        self.temp_dir = self._get_safe_temp_dir()
    
    def _get_safe_temp_dir(self) -> Path:
        try:
            path = Path(TEMP_DOWNLOAD_DIRECTORY)
            path.mkdir(parents=True, exist_ok=True)
            return path
        except Exception:
            fallback = Path("/tmp/fizilion_downloads/")
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback
    
    async def resolve_user(self, event) -> Optional[UserInfo]:
        arg = self._extract_argument(event)
        if event.reply_to_msg_id and not arg:
            return await self._resolve_from_reply(event)
        if self._has_mention_entity(event):
            return await self._resolve_from_mention(event)
        return await self._resolve_from_argument(event, arg)
    
    def _extract_argument(self, event) -> Optional[str]:
        if event.pattern_match and event.pattern_match.group(1):
            return event.pattern_match.group(1).strip()
        return None
    
    def _has_mention_entity(self, event) -> bool:
        return (event.message and 
                event.message.entities and 
                isinstance(event.message.entities[0], MessageEntityMentionName))
    
    async def _resolve_from_reply(self, event) -> Optional[UserInfo]:
        try:
            msg = await event.get_reply_message()
            if not msg or not hasattr(msg, "from_id") or not msg.from_id:
                await event.edit("`Reply message doesn't contain user information.`")
                return None
            
            entity = await event.client.get_entity(msg.from_id)
            if not isinstance(entity, User):
                await event.edit("`This command only works with users.`")
                return None
                
            full_info = await event.client(GetFullUserRequest(msg.from_id))
            return UserInfo(entity, full_info)
        except Exception:
            await event.edit("`Could not resolve user from reply.`")
        return None
    
    async def _resolve_from_mention(self, event) -> Optional[UserInfo]:
        try:
            mention = event.message.entities[0]
            entity = await event.client.get_entity(mention.user_id)
            if not isinstance(entity, User):
                await event.edit("`This command only works with users.`")
                return None
                
            full_info = await event.client(GetFullUserRequest(mention.user_id))
            return UserInfo(entity, full_info)
        except Exception:
            await event.edit("`Could not resolve mentioned user.`")
        return None
    
    async def _resolve_from_argument(self, event, arg: Optional[str]) -> Optional[UserInfo]:
        try:
            target = int(arg) if arg and arg.lstrip('-').isnumeric() else arg
            entity = await event.client.get_entity(target) if target else await event.client.get_me()
            
            if not isinstance(entity, User):
                await event.edit("`This command only works with users.`")
                return None
            
            full_info = await event.client(GetFullUserRequest(entity.id))
            return UserInfo(entity, full_info)
        except (UsernameNotOccupiedError, ValueError, TypeError, 
                UserIdInvalidError, PeerIdInvalidError):
            await event.edit("`Could not find that user.`")
        except Exception as e:
            await event.edit(f"`Unexpected error: {str(e)}`")
        return None
    
    def _create_permalink(self, entity_id: int, text: str = "link") -> str:
        return f'<a href="tg://user?id={entity_id}">{html.escape(str(text))}</a>'
    
    async def _download_profile_photo(self, event, entity) -> Optional[str]:
        try:
            file_id = getattr(entity, 'id', 'unknown')
            photo_path = self.temp_dir / f"profile_{file_id}.jpg"
            downloaded_path = await event.client.download_profile_photo(
                entity, 
                file=str(photo_path),
                download_big=True
            )
            return downloaded_path if downloaded_path and os.path.exists(downloaded_path) else None
        except Exception:
            return None
    
    async def format_user_info(self, event, info: UserInfo) -> Tuple[Optional[str], str]:
        user = info.entity
        full = info.full_info
        first_name = (user.first_name or "None").replace("\u2060", "")
        last_name = user.last_name or None
        username = f"@{user.username}" if user.username else "None"
        about = (getattr(full, "about", None) or 
                getattr(getattr(full, "full_user", None), "about", None))
        
        text_parts = [
            "<b>User Info:</b>",
            f"<b>ID:</b> <code>{user.id}</code>",
            f"<b>First Name:</b> {self._create_permalink(user.id, first_name)}",
        ]
        
        if last_name:
            text_parts.append(f"<b>Last Name:</b> {html.escape(last_name)}")
        
        text_parts.extend([
            f"<b>Username:</b> <code>{html.escape(username)}</code>",
            f"<b>Permalink:</b> {self._create_permalink(user.id)}",
        ])
        
        if about:
            text_parts.append(f"<b>About:</b> <code>{html.escape(about)}</code>")
        
        flags = self._get_user_flags(user)
        if flags:
            text_parts.extend(flags)
        
        photo = await self._download_profile_photo(event, user)
        return photo, "\n".join(text_parts)
    
    def _get_user_flags(self, user: User) -> list:
        flags = []
        flag_mapping = {
            "verified": "Verified",
            "premium": "Premium", 
            "bot": "Bot",
            "scam": "Scam",
            "fake": "Fake",
            "restricted": "Restricted"
        }
        for attr, label in flag_mapping.items():
            if getattr(user, attr, None):
                flags.append(f"<b>{label}:</b> <code>True</code>")
        return flags
    
    async def send_info_response(self, event, photo: Optional[str], text: str):
        if photo and os.path.exists(photo):
            try:
                await event.client.send_file(
                    event.chat_id,
                    file=photo,
                    caption=text,
                    parse_mode="html",
                    force_document=False,
                    link_preview=False,
                )
                await event.delete()
                return
            except Exception:
                pass
            finally:
                try:
                    os.unlink(photo)
                except Exception:
                    pass
        await event.edit(text, parse_mode="html", link_preview=False)


info_handler = InfoHandler()


@register(pattern=f"^{trgg}info(?: |$)(.*)", outgoing=True)
async def info_command(event):
    await event.edit("`Sit tight while I steal some data from *Global Network Zone*...`")
    try:
        user_info = await info_handler.resolve_user(event)
        if not user_info:
            return
        
        photo, text = await info_handler.format_user_info(event, user_info)
        await info_handler.send_info_response(event, photo, text)
    except FloodWaitError as e:
        await event.edit(f"`Rate limit reached. Wait {e.seconds} seconds.`")
    except Exception as e:
        await event.edit(f"`Error getting user information: {str(e)}`")

CMD_HELP.update(
    {
        "info": (
            ".info <username,user_id> or reply to someone's text with .info"
            "\nUsage: Gets info of an user."
        )
    }
)
