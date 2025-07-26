from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core import logger
from astrbot.api.message_components import Plain, Video
import aiohttp
import asyncio
import json
from typing import Optional, Dict, Any


@register("随机美女视频", "cloudcranesss", "获取随机美女短视频", "2.0.0",
          "https://github.com/cloudcranesss/astrbot_plugin_game_videos")
class GameVideosPlugin(Star):
    """游戏视频插件 - 优化版本"""
    
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 配置参数
        self.api_urls = [
            "https://api.kuleu.com/api/MP4_xiaojiejie",
            "https://api.apiopen.top/api/getMiniVideo"
        ]
        
        # 超时配置
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.max_retries = 3
        self.retry_delay = 1
        
        # 连接池配置
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        # 创建会话
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        logger.info("🎬 游戏视频插件已初始化")

    async def terminate(self):
        """优雅关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("会话已关闭")

    async def _fetch_video_url(self, api_url: str) -> Optional[Dict[str, Any]]:
        """获取视频URL - 带重试机制"""
        params = {"type": "json"}
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_video_data(data, api_url)
                    else:
                        logger.warning(f"API请求失败: {response.status} - {api_url}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.max_retries})")
            except aiohttp.ClientError as e:
                logger.warning(f"网络错误: {e.__class__.__name__} (尝试 {attempt + 1}/{self.max_retries})")
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析错误: {e}")
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        return None

    def _parse_video_data(self, data: Dict[str, Any], api_url: str) -> Optional[Dict[str, Any]]:
        """解析不同API的视频数据"""
        try:
            if "qqsuu.cn" in api_url:
                video_url = data.get("video")
                title = data.get("title", "美女视频")
            elif "apiopen.top" in api_url:
                video_data = data.get("data", {})
                video_url = video_data.get("url")
                title = video_data.get("title", "短视频")
            elif "vvhan.com" in api_url:
                video_url = data.get("url")
                title = data.get("title", "美女视频")
            else:
                return None
                
            if video_url and video_url.startswith(('http://', 'https://')):
                return {
                    "url": video_url,
                    "title": title,
                    "source": api_url
                }
                
        except Exception as e:
            logger.error(f"解析数据失败: {e}")
        
        return None

    async def _get_random_video(self) -> Optional[Dict[str, Any]]:
        """从多个API获取随机视频"""
        import random
        
        # 随机打乱API顺序
        api_urls = self.api_urls.copy()
        random.shuffle(api_urls)
        
        for api_url in api_urls:
            result = await self._fetch_video_url(api_url)
            if result:
                logger.info(f"成功获取视频: {result['title']} from {result['source']}")
                return result
        
        return None

    @filter.command_group("video")
    async def video_group(self, event: AstrMessageEvent):
        """视频命令组"""
        if not event.message_str.strip():
            yield event.plain_result(
                "🎬 视频插件命令:\n"
                "  video 美女 - 获取美女视频\n"
                "  video 随机 - 获取随机视频\n"
                "  video 状态 - 查看插件状态"
            )

    @video_group.command("美女")
    async def get_beauty_video(self, event: AstrMessageEvent):
        """获取美女视频"""
        try:
            yield event.plain_result("🎬 正在获取美女视频，请稍候...")
            
            video_data = await self._get_random_video()
            
            if video_data:
                yield event.chain_result([
                    Video.fromURL(video_data["url"]),
                    Plain(f"📹 {video_data['title']}")
                ])
            else:
                yield event.plain_result("❌ 获取视频失败，请稍后重试")
                
        except Exception as e:
            logger.error(f"获取视频异常: {e}")
            yield event.plain_result("❌ 获取视频时出现错误")

    @video_group.command("随机")
    async def get_random_video(self, event: AstrMessageEvent):
        """获取随机视频"""
        await self.get_beauty_video(event)

    @video_group.command("状态")
    async def check_plugin_status(self, event: AstrMessageEvent):
        """检查插件状态"""
        status = (
            "📊 视频插件状态:\n"
            f"API数量: {len(self.api_urls)}\n"
            f"会话状态: {'活跃' if not self.session.closed else '已关闭'}\n"
            f"重试次数: {self.max_retries}\n"
            f"超时设置: {self.timeout.total}秒"
        )
        yield event.plain_result(status)