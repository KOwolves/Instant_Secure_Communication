import logging
import base64

logger = logging.getLogger(__name__)

class AudioUtils:
    """
    语音工具类，用于处理语音数据的编码和解码。
    """

    def __init__(self):
        pass

    def encode_audio(self, audio_data_bytes):
        """
        对音频数据进行编码，以便于网络传输
        :param audio_data_bytes: 原始音频字节数据
        :return: 编码后的音频数据
        """
        try:
            # 简单使用base64编码
            encoded_data = base64.b64encode(audio_data_bytes).decode('utf-8')
            logger.info(f"AudioUtils: 音频数据已编码，原始大小: {len(audio_data_bytes)} 字节")
            return encoded_data
        except Exception as e:
            logger.error(f"AudioUtils: 音频编码出错: {e}", exc_info=True)
            return None

    def decode_audio(self, encoded_audio_data):
        """
        解码网络传输的音频数据
        :param encoded_audio_data: 编码后的音频数据
        :return: 解码后的原始音频字节数据
        """
        try:
            # 解码base64数据
            decoded_data = base64.b64decode(encoded_audio_data)
            logger.info(f"AudioUtils: 音频数据已解码，解码后大小: {len(decoded_data)} 字节")
            return decoded_data
        except Exception as e:
            logger.error(f"AudioUtils: 音频解码出错: {e}", exc_info=True)
            return None 