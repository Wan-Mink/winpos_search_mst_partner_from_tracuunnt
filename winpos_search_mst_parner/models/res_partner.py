import requests
import logging
from bs4 import BeautifulSoup

from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
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

    @staticmethod
    def _get_link(tax_code):
        """Tìm URL chi tiết của công ty từ trang kết quả tìm kiếm."""
        url = f"https://thuvienphapluat.vn/ma-so-thue/tra-cuu-ma-so-thue-doanh-nghiep?timtheo=ma-so-thue&tukhoa={tax_code}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            result_div = soup.find("div", {"id": "dvResultSearch"})
            if result_div:
                try:
                    first_result = result_div.find("table").find("tbody").find("tr").find("a")
                    if first_result and first_result.get('href'):
                        return "https://thuvienphapluat.vn" + first_result.get('href')
                except AttributeError:
                    raise UserError("Không thể phân tích kết quả tìm kiếm để tìm liên kết của công ty.")
            
            raise UserError("Không tìm thấy thông tin công ty cho Mã số thuế đã cung cấp.")
        except requests.exceptions.RequestException as e:
            raise UserError(f"Lỗi kết nối: {e}") from e

    @staticmethod
    def _get_info(url):
        """Lấy thông tin chi tiết của công ty từ URL."""
        _logger.debug("Đang lấy thông tin từ URL: %s", url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Hàm trợ giúp để lấy text một cách an toàn
            def get_text(element_id):
                element = soup.find("span", {"id": element_id})
                return element.text.strip() if element else None

            info = {
                'vat': get_text("fill_MaSoThue"),
                'name': get_text("fill_TenDoanhNghiep"),
                'global_name': get_text("fill_TenQuocTe"),
                'short_name': get_text("fill_TenVietTat"),
                'address': get_text("fill_DiaChiTruSo"),
            }
            if not info.get('name'):
                raise UserError("Không tìm thấy chi tiết công ty trên trang. Cấu trúc trang web có thể đã thay đổi.")
            return info
        except requests.exceptions.RequestException as e:
            raise UserError(f"Lỗi kết nối: {e}") from e