#!/usr/bin/env python
# -*- coding:utf-8 -*-

import websocket
import datetime
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import threading
import logging
import os
import tempfile
import subprocess
import wave

# 导入配置
try:
    from config import XUNFEI_APPID, XUNFEI_API_KEY, XUNFEI_API_SECRET
except ImportError:
    # 设置默认值或者从环境变量获取
    import os
    XUNFEI_APPID = os.getenv('XUNFEI_APPID', '')
    XUNFEI_API_KEY = os.getenv('XUNFEI_API_KEY', '')
    XUNFEI_API_SECRET = os.getenv('XUNFEI_API_SECRET', '')

# 配置日志
logger = logging.getLogger('utils.ASR')

# 定义帧状态常量
STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识

class XunfeiASR:
    """讯飞语音识别API封装类"""

    def __init__(self, app_id=None, api_key=None, api_secret=None):
        """初始化讯飞ASR类"""
        # 从配置中导入凭证，如果没有提供的话
        if app_id is None or api_key is None or api_secret is None:
            try:
                from config import XUNFEI_APPID, XUNFEI_API_KEY, XUNFEI_API_SECRET
                self.app_id = app_id or XUNFEI_APPID
                self.api_key = api_key or XUNFEI_API_KEY
                self.api_secret = api_secret or XUNFEI_API_SECRET
                logger.info(f"成功从配置导入讯飞API凭证，APPID: {self.app_id[:4]}...")
            except ImportError:
                logger.error("无法导入讯飞API凭证，请确保配置正确")
                self.app_id = app_id or ""
                self.api_key = api_key or ""
                self.api_secret = api_secret or ""
        else:
            self.app_id = app_id
            self.api_key = api_key
            self.api_secret = api_secret
            logger.info(f"使用手动提供的讯飞API凭证，APPID: {self.app_id[:4]}...")
        
        self.base_url = "wss://iat-api.xfyun.cn/v2/iat"
        self.host = "iat-api.xfyun.cn"
        
        logger.info("讯飞语音识别服务已初始化")
    
    def _create_url(self):
        """创建鉴权URL"""
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # 构建签名字符串
        signature_origin = f"host: {self.host}\ndate: {date}\nGET /v2/iat HTTP/1.1"
        
        # 使用hmac-sha256进行加密
        signature_sha = hmac.new(self.api_secret.encode('utf-8'),
                                signature_origin.encode('utf-8'),
                                digestmod=hashlib.sha256).digest()
        
        signature_sha_base64 = base64.b64encode(signature_sha).decode('utf-8')
        
        authorization_origin = f"api_key=\"{self.api_key}\", algorithm=\"hmac-sha256\", headers=\"host date request-line\", signature=\"{signature_sha_base64}\""
        
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
        
        # 构建v2版本url
        params = {
            "authorization": authorization,
            "date": date,
            "host": self.host
        }
        
        url = self.base_url + "?" + urlencode(params)
        logger.info(f"已创建讯飞API鉴权URL: {url[:50]}...")
        return url
    
    def process_audio_file(self, audio_file_path):
        """处理音频文件并返回识别结果"""
        logger.info(f"开始处理音频文件: {audio_file_path}")
        
        if not os.path.exists(audio_file_path):
            logger.error(f"文件不存在: {audio_file_path}")
            return {"error": "文件不存在"}
        
        # 获取音频文件大小和格式检查
        file_size = os.path.getsize(audio_file_path)
        logger.info(f"音频文件大小: {file_size} 字节")
        
        # 检查文件大小
        if file_size < 100:  # 太小的文件可能是损坏的或空的
            logger.error(f"音频文件太小，可能是损坏的或空的: {file_size} 字节")
            return {"error": "音频文件太小，可能是损坏的或空的"}
            
        # 检查文件扩展名
        file_ext = os.path.splitext(audio_file_path)[1].lower()
        if file_ext not in ['.wav', '.pcm']:
            logger.warning(f"文件扩展名不是标准的WAV或PCM格式: {file_ext}")
            # 继续处理，但发出警告
        
        # 如果是WAV文件，检查格式是否符合要求
        if file_ext == '.wav':
            is_valid_wav = check_wav_format(audio_file_path)
            if not is_valid_wav:
                logger.warning("WAV文件格式不符合讯飞API要求（应为16kHz采样率的PCM编码），尝试进行转换")
                # 转换音频格式
                converted_file_path = convert_to_16khz_wav(audio_file_path)
                if converted_file_path != audio_file_path:
                    logger.info(f"使用转换后的音频文件: {converted_file_path}")
                    audio_file_path = converted_file_path
        
        # 处理结果
        result = {"text": "", "error": None}
        result_ready = threading.Event()
        
        # WebSocket回调函数
        def on_message(ws, message):
            logger.info(f"收到WebSocket消息: {message}")
            try:
                logger.debug(f"收到WebSocket消息: {message[:100]}...")
                data = json.loads(message)
                code = data["code"]
                
                if code != 0:
                    error_msg = f"识别错误，错误码: {code}"
                    result["error"] = error_msg
                    logger.error(error_msg)
                    result_ready.set()
                    return
                
                # 提取识别结果
                data = data["data"]
                status = data["status"]
                logger.debug(f"识别状态: {status}")
                
                # 累积中间结果
                if "result" in data and "ws" in data["result"]:
                    partial_result = ""
                    ws_result = data["result"]["ws"]
                    for item in ws_result:
                        if "cw" in item:
                            for cw_item in item["cw"]:
                                if "w" in cw_item:
                                    partial_result += cw_item["w"]
                    
                    # 追加或覆盖当前结果
                    if partial_result:
                        logger.info(f"部分识别结果: {partial_result}")
                        if status == 2:  # 最终结果
                            result["text"] = partial_result
                            logger.info(f"最终识别结果: {result['text']}")
                            result_ready.set()
                        else:
                            # 累积中间结果，即使连接断开也有部分结果
                            result["text"] = partial_result
                
                if status == 2 and result["text"] == "":  # 最终结果但没有内容
                    logger.warning(f"识别完成但没有内容: {data}")
                    result["error"] = "识别完成但未返回文本内容"
                    result_ready.set()
            except Exception as e:
                logger.exception(f"处理识别结果异常: {str(e)}")
                result["error"] = f"处理异常: {str(e)}"
                result_ready.set()
        
        def on_error(ws, error):
            logger.error(f"WebSocket错误: {str(error)}")
            result["error"] = f"连接错误: {str(error)}"
            result_ready.set()
        
        def on_close(ws, close_status_code, close_reason):
            logger.info(f"WebSocket连接关闭: {close_status_code} - {close_reason}")
            if not result_ready.is_set():
                # 尝试从close_reason中提取会话ID，判断是否是正常关闭
                if close_reason and "server read msg timeout" in close_reason:
                    logger.warning("服务器超时关闭连接，但这可能是正常现象 - 讯飞API有时会在处理完成后关闭连接")
                    # 不立即设置result_ready，给额外的1秒等待可能的结果
                    threading.Timer(1.0, lambda: result_ready.set() if not result_ready.is_set() else None).start()
                else:
                    # 其他关闭原因，可能是错误
                    logger.error(f"WebSocket连接异常关闭: {close_status_code} - {close_reason}")
                    result["error"] = f"连接被关闭: {close_reason}"
                    result_ready.set()
        
        def on_open(ws):
            logger.info("WebSocket连接已建立，开始发送音频数据")
            
            def send_data():
                # 读取音频文件
                try:
                    with open(audio_file_path, 'rb') as f:
                        file_content = f.read()
                    
                    logger.info(f"音频文件读取成功，大小: {len(file_content)} 字节")
                    
                    # 发送参数帧
                    frame = {
                        "common": {
                            "app_id": self.app_id
                        },
                        "business": {
                            "language": "zh_cn",
                            "domain": "iat",
                            "accent": "mandarin",
                            "vad_eos": 10000,
                            "dwa": "wpgs",  # 添加动态修正功能
                            "pd": "game",   # 添加领域个性化参数
                            "ptt": 0        # 添加标点符号
                        },
                        "data": {
                            "status": 0,
                            "format": "audio/L16;rate=16000",
                            "encoding": "raw"
                        }
                    }
                    logger.debug(f"发送参数帧: {json.dumps(frame)}")
                    ws.send(json.dumps(frame))
                    
                    # 分帧发送音频
                    chunk_size = 1280  # 每帧大小
                    total_chunks = len(file_content) // chunk_size + (1 if len(file_content) % chunk_size > 0 else 0)
                    logger.info(f"开始分帧发送音频，总帧数: {total_chunks}")
                    
                    for i in range(0, len(file_content), chunk_size):
                        chunk = file_content[i:i + chunk_size]
                        is_last = i + chunk_size >= len(file_content)
                        chunk_num = i // chunk_size + 1
                        
                        frame = {
                            "data": {
                                "status": 2 if is_last else 1,  # 1表示中间帧，2表示最后一帧
                                "format": "audio/L16;rate=16000",
                                "encoding": "raw",
                                "audio": base64.b64encode(chunk).decode('utf-8')
                            }
                        }
                        
                        if chunk_num % 10 == 0 or is_last:
                            logger.debug(f"发送第 {chunk_num}/{total_chunks} 帧，状态: {2 if is_last else 1}")
                        
                        ws.send(json.dumps(frame))
                        
                        # 最后一帧发送后，等待足够时间让服务器处理
                        if is_last:
                            logger.info("最后一帧已发送，等待服务器处理...")
                            time.sleep(1)  # 参考官方示例，增加等待时间
                        else:
                            time.sleep(0.04)  # 控制发送速率
                    
                    logger.info("音频数据发送完成")
                except Exception as e:
                    logger.exception(f"发送音频数据异常: {str(e)}")
                    result["error"] = f"发送数据异常: {str(e)}"
                    result_ready.set()
                    ws.close()
            
            # 在新线程中发送数据，避免阻塞WebSocket接收线程
            threading.Thread(target=send_data).start()
        
        try:
            # 创建WebSocket连接
            websocket_url = self._create_url()
            logger.info("准备建立WebSocket连接")
            
            # 启用WebSocket调试日志
            if logger.level <= logging.DEBUG:
                websocket.enableTrace(True)
            else:
                websocket.enableTrace(False)
                
            ws = websocket.WebSocketApp(
                websocket_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # 启动WebSocket连接，关闭SSL证书验证
            logger.info("启动WebSocket连接，禁用SSL证书验证...")
            ws_thread = threading.Thread(
                target=lambda: ws.run_forever(
                    sslopt={"cert_reqs": ssl.CERT_NONE},
                    skip_utf8_validation=True
                )
            )
            ws_thread.daemon = True
            ws_thread.start()
            logger.info("WebSocket连接线程已启动")
            
            # 等待结果就绪或超时
            timeout = 30  # 30秒超时
            logger.info(f"等待识别结果，超时时间: {timeout}秒")
            if not result_ready.wait(timeout=timeout):
                logger.error("识别超时")
                result["error"] = "识别超时"
                ws.close()
            
            logger.info(f"语音识别过程结束，结果: {result}")
            
            # 如果结果为空但没有错误，返回提示信息
            if result["text"] == "" and result["error"] is None:
                logger.warning("获取到空结果，可能是音频过短或没有语音内容")
                result["error"] = "未识别到有效语音内容"
            
            return result
        except Exception as e:
            logger.exception(f"语音识别过程异常: {str(e)}")
            return {"error": f"处理异常: {str(e)}"}

# 便捷调用函数
def speech_to_text(audio_file_path, app_id=None, api_key=None, api_secret=None):
    """语音转文字便捷函数"""
    logger.info(f"调用speech_to_text函数处理音频: {audio_file_path}")
    asr = XunfeiASR(app_id, api_key, api_secret)
    return asr.process_audio_file(audio_file_path)

def check_wav_format(file_path):
    """检查WAV文件的格式是否符合讯飞API要求（16kHz采样率）"""
    logger = logging.getLogger('utils.ASR')
    
    try:
        # 读取WAV文件头
        with open(file_path, 'rb') as f:
            # 检查RIFF头
            riff = f.read(4)
            if riff != b'RIFF':
                logger.warning(f"文件不是有效的WAV格式，缺少RIFF头: {file_path}")
                return False
                
            # 跳过文件大小
            f.read(4)
            
            # 检查WAVE标识
            wave = f.read(4)
            if wave != b'WAVE':
                logger.warning(f"文件不是有效的WAV格式，缺少WAVE标识: {file_path}")
                return False
                
            # 查找fmt子块
            while True:
                chunk_id = f.read(4)
                if not chunk_id:
                    logger.warning(f"文件格式异常，未找到fmt子块: {file_path}")
                    return False
                    
                if chunk_id == b'fmt ':
                    break
                    
                # 跳过非fmt子块
                chunk_size = int.from_bytes(f.read(4), byteorder='little')
                f.seek(chunk_size, 1)
                
            # 读取fmt子块大小
            fmt_size = int.from_bytes(f.read(4), byteorder='little')
            
            # 读取音频格式（1表示PCM）
            audio_format = int.from_bytes(f.read(2), byteorder='little')
            if audio_format != 1:
                logger.warning(f"不支持的音频格式（非PCM）: {audio_format}")
                return False
                
            # 读取通道数
            channels = int.from_bytes(f.read(2), byteorder='little')
            
            # 读取采样率
            sample_rate = int.from_bytes(f.read(4), byteorder='little')
            
            logger.info(f"音频格式: 通道数={channels}, 采样率={sample_rate}Hz")
            
            # 检查采样率是否为16kHz
            if sample_rate != 16000:
                logger.warning(f"音频采样率不是16kHz，实际为: {sample_rate}Hz")
                return False
                
            return True
    except Exception as e:
        logger.exception(f"检查WAV文件格式时出错: {str(e)}")
        return False

def convert_to_16khz_wav(input_file_path):
    """
    将输入的音频文件转换为16kHz采样率、单声道的WAV文件，返回临时文件路径
    """
    logger = logging.getLogger('utils.ASR')
    
    try:
        # 检查ffmpeg是否可用
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("ffmpeg不可用，无法进行音频格式转换")
            return input_file_path
            
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()
        
        logger.info(f"开始将音频转换为16kHz采样率WAV: {input_file_path} -> {temp_file_path}")
        
        # 使用ffmpeg转换音频
        cmd = [
            'ffmpeg',
            '-i', input_file_path,
            '-ar', '16000',  # 16kHz采样率
            '-ac', '1',      # 单声道
            '-acodec', 'pcm_s16le',  # 16位PCM编码
            '-y',            # 覆盖输出文件
            temp_file_path
        ]
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if process.returncode != 0:
            logger.error(f"音频转换失败: {process.stderr.decode('utf-8', errors='replace')}")
            return input_file_path
        
        # 验证转换后的文件
        try:
            with wave.open(temp_file_path, 'rb') as wf:
                if wf.getframerate() != 16000 or wf.getnchannels() != 1:
                    logger.warning(f"转换后的文件格式不正确：采样率={wf.getframerate()}, 通道数={wf.getnchannels()}")
                else:
                    logger.info(f"音频转换成功：采样率=16000Hz, 通道数=1, 大小={os.path.getsize(temp_file_path)}字节")
        except Exception as e:
            logger.warning(f"无法验证转换后的文件: {str(e)}")
            
        return temp_file_path
    except Exception as e:
        logger.exception(f"音频转换过程出错: {str(e)}")
        return input_file_path 