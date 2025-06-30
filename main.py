from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core  import logger
from astrbot.api.message_components import Plain, Video
import astrbot.api.message_components as comp
import aiohttp
import asyncio
import logging


@register("random beauty videos", "cloudcranesss", "astrbot_plugin_game_video", "1.0.0",
          "https://github.com/cloudcranesss/astrbot_plugin_game_videos")
class DwoVideoPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api_url = "https://api.qqsuu.cn/api/dm-xjj2"
        logger.info(f"DwoVideoPlugin init with api_url: {self.api_url}")
        # 优化点1：设置超时和连接池限制防止资源泄漏
        self.timeout = aiohttp.ClientTimeout(total=15)
        connector = aiohttp.TCPConnector(limit_per_host=5)
        self.session = aiohttp.ClientSession(connector=connector, timeout=self.timeout)

    async def terminate(self):
        # 优化点2：增加安全关闭检查
        if not self.session.closed:
            await self.session.close()

    @filter.command("video", alias={"小视频", "短视频"})
    async def get_dwo_video(self, event: AstrMessageEvent):
        try:
            params = {"type": "json"}
            async with self.session.get(self.api_url, params=params) as response:
                # 优化点3：合并错误处理逻辑
                if response.status != 200:
                    yield event.plain_result(f"请求失败：状态码{response.status}")
                    logger.error(f"请求失败：状态码{response.status}")
                    return

                # 优化点4：正确解析JSON响应
                json_data = await response.json()
                if not (video_url := json_data.get("video")):
                    yield event.plain_result("API返回无效数据：缺少视频URL")
                    logger.error(f"API返回无效数据：缺少视频URL")
                    return

                logger.info(f"视频获取成功：{video_url}")
                yield event.chain_result([
                    Video.fromURL(video_url),
                    Plain("视频获取成功！")
                ])

        except asyncio.TimeoutError:
            yield event.plain_result("视频请求超时，请重试")
        except aiohttp.ClientError as e:
            # 优化点5：减少错误信息长度
            yield event.plain_result(f"网络请求失败：{e.__class__.__name__}")
        # 优化点6：移除冗余的Exception捕获
        except ValueError as e:  # JSON解析异常
            logger.error(f"JSON解析错误：{e}")
            yield event.plain_result("视频数据解析错误")