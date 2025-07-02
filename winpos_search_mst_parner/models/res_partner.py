import requests
import logging
from bs4 import BeautifulSoup
import tkinter as tk
from PIL import Image, ImageTk
import json
from io import BytesIO
import random
import re
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import pickle 
from selenium.webdriver.chrome.options import Options
import base64

from odoo import models, api, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
session = requests.Session()
class ResPartner(models.Model):
    _inherit = 'res.partner'
    captcha = fields.Char("captcha")
    captcha_img = fields.Binary("captcha_img")
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
    
    def get_captcha(self):
        """Lấy hình CAPTCHA mới từ server và cập nhật GUI"""
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        # options.add_argument("--no-sandbox")
        # options.add_argument("--disable-dev-shm-usage")
        # options.add_argument("--disable-extensions")
        options.add_argument("--window-size=1200x800")

        driver = webdriver.Chrome(options=options)

        try:
            driver.get("https://tracuunnt.gdt.gov.vn/tcnnt/mstdn.jsp")
            _logger.info("Đã mở trang tra cứu MST")
            captcha_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'captcha.png')]"))
            )
            src = captcha_elem.get_attribute("src")
            if src.startswith("/"):
                captcha_url = "https://tracuunnt.gdt.gov.vn/tcnnt" + src
            else:
                captcha_url = src
            _logger.info(f"Captcha URL: {captcha_url}")
            # captcha_url = "https://tracuunnt.gdt.gov.vn/tcnnt/captcha.png?uid=" 
            # + src if src.startswith("/") else src
            

            cookies = driver.get_cookies()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
            response = session.get(captcha_url)
            img_bytes = response.content
            # img_bytes = response.content
            # _logger.info(f"Đã lấy ảnh captcha, kích thước: {len(img_bytes)} bytes")
            # print(f"Đã lấy ảnh captcha, kích thước: {len(img_bytes)} bytes")

            b64_img = base64.b64encode(img_bytes).decode('utf-8')
            self.captcha_img = b64_img
            # _logger.info(f"Đã gán captcha_img, độ dài base64: {len(b64_img)}")
            print(f"Đã gán captcha_img, độ dài base64: {len(b64_img)}")

            # Nếu muốn kiểm tra trực tiếp trường đã có dữ liệu chưa:
            if self.captcha_img:
                _logger.info("captcha_img đã có dữ liệu.")
                print("captcha_img đã có dữ liệu.")
            else:
                _logger.warning("captcha_img chưa có dữ liệu!")
                print("captcha_img chưa có dữ liệu!")

        except Exception as e:
            print("Không tìm thấy CAPTCHA:", e)
            _logger.error(f"Lỗi lấy captcha: {e}")
            page_source=driver.page_source
            # print("HTML", page_source[:1000])
            # _logger.error("HTML thực tế (500 ký tự đầu): %s", page_source[:1000])

        finally:
            driver.quit()
    

    def find_data_from_html(data):
        left_str = data.find('nntJson = ')
        right_str = data[left_str:].find('</script>')
        return json.loads(data[left_str:left_str+right_str].replace('nntJson = ', '').strip()[:-1])

    def lookup_mst(self):
        self.ensure_one()
        session = requests.Session()

        with open("cookies.pkl", "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
        session = requests.Session()
        session.cookies.update(cookies)

        """Thực hiện tra cứu MST với CAPTCHA và MST nhập vào"""
        mst = self.vat
        captcha_text = self.captcha
        
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


