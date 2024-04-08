import os
import re
import poplib
from email.parser import Parser
from email.header import decode_header
from email.utils import parseaddr
from datetime import datetime


class EmailReader:
    '''参考 https://blog.csdn.net/weixin_39146980/article/details/111180449'''
    def __init__(self, address, auth_code, **kwargs) -> None:
        self.email_server: poplib.POP3 = None
        self._connet(address, auth_code, **kwargs)

    def _connet(self, address, auth_code, pop_host='pop.163.com', pop_port=110, timeout=10):
        try:
            # 连接pop服务器。如果没有使用SSL，将POP3_SSL()改成POP3(),且监听端口改为：110即可
            self.email_server = poplib.POP3(host=pop_host, port=pop_port, timeout=timeout)
        except Exception as e:
            raise Exception(f"POP server connet failed: {e}")

        try:
            # 验证用户邮箱
            self.email_server.user(address)
            # 验证邮箱授权码（不是登陆密码）
            self.email_server.pass_(auth_code)
        except Exception as e:
            raise Exception(f"Email authorized failed: {e}")

    def parse_email_server(self, min_date='', part_dir: str='data'):
        resp, mails, octets = self.email_server.list()
        num, total_size = self.email_server.stat()

        print("Total email count: " + str(num))
        print(f"latest received date: {min_date}")

        # mails存储了邮件编号列表，
        index = len(mails)
        # 倒序遍历邮件
        for i in range(index, 0, -1):
            item = {}
            # 倒序遍历邮件，这样取到的第一封就是最新邮件
            resp, lines, octets = self.email_server.retr(i)
            # lines存储了邮件的原始文本的每一行,
            # 邮件的原始文本:# lines是邮件内容，列表形式使用join拼成一个byte变量
            msg_content = b'\r\n'.join(lines).decode('utf-8')

            # 解析邮件:
            msg = Parser().parsestr(msg_content)

            # 解析邮件具体内容，包括正文，标题，和附件
            # 邮件的From, To, Subject存在于根对象上:
            # 调用解析邮件头部内容的函数
            item.update(EmailReader.parser_email_header(msg))
            print(item)
            if 'paper_' not in item['subject']:
                continue
            item['content'] = self.parser_content(msg)

            # 获取arxiv发送时的时间，由于arxiv发送的邮件通过gmail邮件手动转发到163邮箱，因此可能存在人为的操作延迟
            # 论文接收日期
            received_date = EmailReader.parser_received_date(item['subject']+' '+item['content'][:2000])

            item['time'] = received_date

            if item['time'] <= min_date:
                print(f"The min received date is {min_date}, but got current received date is {item['time']}, stop parse.")
                break

            # 下载附件
            item['parts'] = []
            for part in msg.walk():
                file_name = part.get_filename()
                if file_name is None:
                    continue
                if not re.match('^paper_\d{6}.md$', file_name):
                    continue
                data = part.get_payload(decode=True)  # 下载附件
                att_path = os.path.join(part_dir, file_name)
                att_file = open(att_path, 'wb')
                att_file.write(data)  # 保存附件
                att_file.close()
                item['parts'].append(att_path)
                print("附件: " + file_name + " 保存成功！")
            yield item

    def close(self):
        self.email_server.quit()

    def parser_content(self, msg):
        content = ''
        file_name = msg.get_filename()  # 获取附件名称
        if msg.is_multipart():
            for part in msg.get_payload():
                part_content = self.parser_content(part).strip()
                content += f'\n{part_content}' if part_content else ''
        # elif file_name is not None:
        #     # 下载附件
        #     data = msg.get_payload(decode=True)  # 下载附件
        #     att_file = open('new_' + file_name, 'wb')  # 在指定目录下创建文件，注意二进制文件需要用wb模式打开
        #     att_file.write(data)  # 保存附件
        #     att_file.close()
        #     print("附件: " + file_name + " 保存成功！")
        else:
            # 解析正文
            content_type = msg.get_content_type()
            if content_type == 'text/plain' or content_type == 'text/html':
                # 纯文本或HTML内容:
                content = msg.get_payload(decode=True)
                # 要检测文本编码:
                charset = EmailReader.guess_charset(msg)
                if charset:
                    content = content.decode(charset)
        return content

    # 解析邮件
    def parser_email_header(msg):
        # 解析邮件标题
        header = {}
        value, charset = decode_header(msg['Subject'])[0]
        if charset:
            value = value.decode(charset)
        if type(value) == bytes:
            value = value.decode()
        header['subject'] = value

        _, addr = parseaddr(msg['From'])
        header['from'] = addr

        _, addr = parseaddr(msg['To'])
        header['to'] = addr
        return header

    # 猜测字符编码
    def guess_charset(msg):
        # 先从msg对象获取编码:
        charset = msg.get_charset()
        if charset is None:
            # 如果获取不到，再从Content-Type字段获取:
            content_type = msg.get('Content-Type', '').lower()
            for item in content_type.split(';'):
                item = item.strip()
                if item.startswith('charset'):
                    charset = item.split('=')[1]
                    break
        return charset

    # 解析论文接收日期
    def parser_received_date(content):
        try:
            received_date = re.findall('paper_(\d{6})[^\d]', content)
            if len(received_date) == 1:
                received_date = received_date[0]
            else:
                received_date = re.findall('(\d+年\d+月\d+日)', content)[0].strip()
                received_date = datetime.strftime(datetime.strptime(received_date, '%Y年%m月%d日'), '%y%m%d')
            return received_date
        except:
            print(f"content: {content[:1000]}...")
            raise Exception("论文接收日期解析错误")
