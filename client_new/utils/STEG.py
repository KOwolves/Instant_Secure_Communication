from PIL import Image
import logging

logger = logging.getLogger(__name__)


class StegUtils:
    """
    隐写术工具类，用于在图片（PNG格式最佳）的最低有效位（LSB）中嵌入和提取文本。
    """

    def __init__(self):
        pass

    def _text_to_binary(self, text):
        """将文本字符串转换为二进制字符串（8位 per char）。"""
        binary_string = ''.join(format(ord(char), '08b') for char in text)
        return binary_string

    def _binary_to_text(self, binary_string):
        """将二进制字符串转换为文本字符串。"""
        # 确保二进制字符串长度是8的倍数
        if len(binary_string) % 8 != 0:
            logger.warning("StegUtils: 提取的二进制字符串长度不是8的倍数，可能导致解码错误。")
            binary_string = binary_string[:len(binary_string) - (len(binary_string) % 8)]  # 截断不完整的字节

        text = ""
        for i in range(0, len(binary_string), 8):
            byte = binary_string[i:i + 8]
            text += chr(int(byte, 2))
        return text

    def embed_text(self, image_bytes, text_to_hide):
        """
        将文本嵌入到图片数据的LSB中。
        :param image_bytes: 原始图片文件的字节数据。
        :param text_to_hide: 要隐藏的文本字符串。
        :return: 嵌入文本后的图片字节数据，失败返回None。
        """
        try:
            from io import BytesIO
            img = Image.open(BytesIO(image_bytes))  # 从字节数据打开图片
            width, height = img.size

            # 确保图片是RGB模式，如果不是则转换
            if img.mode != 'RGB':
                img = img.convert('RGB')
            pixels = img.load()  # 加载像素数据

            binary_text = self._text_to_binary(text_to_hide)
            # 添加一个结束标记，以便提取时知道文本何时结束
            # 我们用一个特殊的二进制序列作为结束标记，例如 '111111110000000011111111'
            # 确保这个标记不会出现在普通的文本二进制表示中（或者使用更长的随机序列）
            end_marker = "1111111111111110"  # 16位结束标记，例如全1后接一个0，避免与字符的二进制表示重复
            binary_text += end_marker

            data_index = 0
            # 计算图片能隐藏的最大位数
            # 每个像素（RGB）有3个字节，每个字节可以隐藏1位
            max_bits = width * height * 3

            if len(binary_text) > max_bits:
                logger.error(f"StegUtils: 要隐藏的文本过长。最大可隐藏位数: {max_bits}，需要: {len(binary_text)}。")
                return None

            for y in range(height):
                for x in range(width):
                    r, g, b = pixels[x, y]  # 获取RGB像素值

                    # 逐个修改R, G, B的LSB
                    if data_index < len(binary_text):
                        # 清除LSB (最后一位)，然后设置新的LSB
                        r = (r & 0xFE) | int(binary_text[data_index])
                        data_index += 1

                    if data_index < len(binary_text):
                        g = (g & 0xFE) | int(binary_text[data_index])
                        data_index += 1

                    if data_index < len(binary_text):
                        b = (b & 0xFE) | int(binary_text[data_index])
                        data_index += 1

                    pixels[x, y] = (r, g, b)  # 更新像素

                    if data_index >= len(binary_text):
                        break  # 所有数据都已嵌入
                if data_index >= len(binary_text):
                    break

            # 将修改后的图片保存到字节流
            output_buffer = BytesIO()
            img.save(output_buffer, format="PNG")  # PNG是无损格式，适合LSB隐写
            output_buffer.seek(0)
            logger.info(f"StegUtils: 文本已成功嵌入图片。")
            return output_buffer.getvalue()  # 返回图片字节数据

        except Exception as e:
            logger.error(f"StegUtils: 嵌入文本到图片时出错: {e}", exc_info=True)
            return None

    def extract_text(self, image_bytes):
        """
        从图片数据的LSB中提取隐藏的文本。
        :param image_bytes: 包含隐藏文本的图片字节数据。
        :return: 提取出的文本字符串，失败返回None。
        """
        try:
            from io import BytesIO
            img = Image.open(BytesIO(image_bytes))  # 从字节数据打开图片
            width, height = img.size

            if img.mode != 'RGB':
                img = img.convert('RGB')
            pixels = img.load()

            extracted_binary = ""
            end_marker = "1111111111111110"  # 16位结束标记

            for y in range(height):
                for x in range(width):
                    r, g, b = pixels[x, y]  # 获取RGB像素值

                    # 提取LSB
                    extracted_binary += str(r & 1)
                    extracted_binary += str(g & 1)
                    extracted_binary += str(b & 1)

                    # 检查是否遇到结束标记
                    if len(extracted_binary) >= len(end_marker) and \
                            extracted_binary[-len(end_marker):] == end_marker:
                        # 移除结束标记
                        extracted_binary = extracted_binary[:-len(end_marker)]
                        hidden_text = self._binary_to_text(extracted_binary)
                        logger.info(f"StegUtils: 文本已成功从图片中提取。")
                        return hidden_text

            logger.warning("StegUtils: 未在图片中找到结束标记，可能没有隐藏文本或格式不正确。")
            return ""  # 如果没有找到结束标记，可能没有隐藏文本
        except Exception as e:
            logger.error(f"StegUtils: 从图片中提取文本时出错: {e}", exc_info=True)
            return None