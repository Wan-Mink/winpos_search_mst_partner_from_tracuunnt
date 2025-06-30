import requests
import logging
from bs4 import BeautifulSoup
import tkinter as tk
from PIL import Image, ImageTk
import json
from io import BytesIO
import random
import re

from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
session = requests.Session()
class ResPartner(models.Model):
    _inherit = 'res.partner'
    session = requests.Session()

    def action_search_mst_partner(self):
        self.ensure_one()
        if not self.vat:
            raise UserError("Vui lòng cung cấp Mã số thuế để tìm kiếm.")

        _logger.info("Bắt đầu tìm kiếm thông tin cho MST: %s", self.vat)
        try:
            url = self._get_link(self.vat)
            info = self._get_info(url)
            
            vals = {
                'name': info.get('name'),
                'street': info.get('address'),
            }
            self.write(vals)

        except (requests.exceptions.RequestException, UserError) as e:
            _logger.error("Lỗi khi tìm kiếm đối tác với MST %s: %s", self.vat, e)
            raise UserError(f"Không thể lấy thông tin công ty: {e}") from e
    def get_captcha():
        """Lấy hình CAPTCHA mới từ server và cập nhật GUI"""
        try:
            # Thêm tham số ngẫu nhiên để tránh cache
            timestamp = random.randint(10000, 99999)
            url = f"https://tracuunnt.gdt.gov.vn/tcnnt/captcha.png?t={timestamp}"
            
            # Gửi request lấy hình CAPTCHA với session
            response = session.get(url)
            response.raise_for_status()
            
            # Xử lý ảnh và cập nhật GUI
            image = Image.open(BytesIO(response.content))
            photo = ImageTk.PhotoImage(image)
            
            label_captcha.configure(image=photo)
            label_captcha.image = photo  # Giữ reference
            label_status.config(text="CAPTCHA đã tải thành công!", fg="green")
            
        except Exception as e:
            label_status.config(text=f"Lỗi: {str(e)}", fg="red")

    def find_data_from_html(data):
        left_str = data.find('nntJson = ')
        right_str = data[left_str:].find('</script>')
        return json.loads(data[left_str:left_str+right_str].replace('nntJson = ', '').strip()[:-1])

    def lookup_mst():
        """Thực hiện tra cứu MST với CAPTCHA và MST nhập vào"""
        mst = entry_mst.get().strip()
        captcha_text = entry_captcha.get().strip()
        
        if not mst:
            label_status.config(text="Vui lòng nhập mã số thuế!", fg="orange")
            return
        if not captcha_text:
            label_status.config(text="Vui lòng nhập CAPTCHA!", fg="orange")
            return
        
        try:
            # Chuẩn bị dữ liệu gửi đi
            payload = {
                'mst': mst,
                'captcha': captcha_text
            }
            
            # Gửi request POST với session đã duy trì
            response = session.post(
                "https://tracuunnt.gdt.gov.vn/tcnnt/mstdn.jsp",
                data=payload,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': 'https://tracuunnt.gdt.gov.vn/tcnnt/mstdn.jsp'
                }
            )
            response.raise_for_status()
            
            # Phân tích kết quả trả về
            soup = BeautifulSoup(response.text, 'html.parser')
            print (find_data_from_html(response.text))
            error_message = soup.find('p', class_='errormess')
            result_table = soup.find('table', class_='form')
            
            if error_message:
                # Xử lý trường hợp lỗi
                error_text = re.sub(r'\s+', ' ', error_message.get_text()).strip()
                label_status.config(text=f"Lỗi: {error_text}", fg="red")
            elif result_table:
                # Trích xuất kết quả thành công
                results = []
                for row in result_table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        label = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        results.append(f"{label}: {value}")
                
                result_text = "\n".join(results)
                label_status.config(
                    text=f"Tra cứu thành công!\n{result_text}", 
                    fg="green",
                    justify=tk.LEFT
                )
            else:
                label_status.config(text="Không tìm thấy kết quả", fg="blue")
                
            # Tải lại CAPTCHA sau mỗi lần gửi
            get_captcha()
            
        except Exception as e:
            label_status.config(text=f"Lỗi kết nối: {str(e)}", fg="red")


    