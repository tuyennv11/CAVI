"""Tiện ích dùng chung cho export/import Excel ở trang admin (dựa trên django-import-export). Mọi
Resource nên kế thừa ExcelModelResource thay vì viết tay 3 việc lặp lại ở mọi model:

  1. Cột khoá ngoại (FK/O2O/M2M) phải hiện TÊN cho người đọc, nhưng vẫn nhập ngược lại KHÔNG bị
     nhầm giữa 2 bản ghi trùng tên — đã kiểm tra: Partner.name, Province/District/Ward.name+code,
     Product.sku... KHÔNG model nào có field chữ nào chắc chắn duy nhất toàn cục (chỉ duy nhất cùng
     bản ghi cha, hoặc không duy nhất gì cả) — nên phải ghép "id — tên" cho MỌI khoá ngoại, không
     phân biệt model nào "có vẻ" an toàn hay không, để chỉ có đúng 1 quy tắc áp dụng thống nhất.
  2. Tiêu đề cột (column_name) phải là đúng verbose_name tiếng Việt đã khai trên model, không phải
     tên field kỹ thuật (vd "Khách hàng", không phải "customer") — ĐỔI THẲNG column_name (không chỉ
     đổi header lúc export) vì lúc Nhập lại, field.clean() tra giá trị bằng row[column_name] — nếu
     export hiện "Khách hàng" mà column_name vẫn là "customer" thì nhập lại sẽ không khớp được cột
     nào cả, cột đó bị bỏ qua âm thầm (đã phát hiện bằng test round-trip thực tế, không phải suy đoán).
  3. 1 base ModelAdmin CHỈ export (không cho nhập) — dùng cho auth.User/Group (tài khoản đăng nhập/
     nhóm quyền không nên sửa qua Excel, phải qua đúng luồng có xác thực của Django) và các bảng
     nhật ký/lịch sử tự động (vd hr.ProfileChangeLog — do signal tạo, không phải nơi nhập tay).
"""

import functools
import re

from django.db import models as django_models
from import_export import resources, widgets
from import_export.admin import ExportMixin
from import_export.utils import get_related_model

# "8 — Cửa hàng Chị Lụa": số id đứng đầu để tra ngược lúc nhập lại (không đổi dù tên bị sửa), phần
# chữ phía sau chỉ để người đọc hiểu trên Excel — sửa/xoá phần chữ không ảnh hưởng gì tới việc nhập.
ID_NAME_SEP = " — "
_LEADING_ID_RE = re.compile(r"^\s*(\d+)")


class IdNameForeignKeyWidget(widgets.ForeignKeyWidget):
    """Thay cho ForeignKeyWidget(model, field="...") mặc định — xem audit ở đầu file, không có field
    chữ nào an toàn để tra ngược 1 mình. Ghép "id — tên" giải quyết cả đọc được lẫn nhập lại đúng."""

    def render(self, value, obj=None, **kwargs):
        if value is None:
            return ""
        return f"{value.pk}{ID_NAME_SEP}{value}"

    def clean(self, value, row=None, **kwargs):
        text = "" if value is None else str(value).strip()
        if not text:
            return None
        match = _LEADING_ID_RE.match(text)
        if match:
            pk = match.group(1)
            try:
                return self.model.objects.get(pk=pk)
            except self.model.DoesNotExist:
                raise ValueError(
                    f"Không tìm thấy {self.model._meta.verbose_name} có id={pk}. Đừng xoá số id ở "
                    f'đầu ô — giữ đúng định dạng "id{ID_NAME_SEP}tên".'
                )
        # Dòng người dùng tự gõ tay không kèm id (vd thêm 1 dòng mới) — chỉ chấp nhận khi tên khớp
        # DUY NHẤT 1 bản ghi, để không lỡ gán nhầm khi có 2 bản ghi trùng tên.
        matches = [o for o in self.model.objects.all() if str(o) == text]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ValueError(f'Không tìm thấy {self.model._meta.verbose_name} nào tên "{text}".')
        raise ValueError(
            f'Có {len(matches)} {self.model._meta.verbose_name} cùng tên "{text}" — phải ghi rõ id, '
            f'định dạng "id{ID_NAME_SEP}tên" (xem đúng định dạng ở lần export gần nhất).'
        )


class IdNameManyToManyWidget(widgets.ManyToManyWidget):
    """Bản tương đương IdNameForeignKeyWidget cho ManyToMany — nhiều giá trị nối bằng dấu ";"."""

    OUTER_SEP = "; "

    def render(self, value, obj=None, **kwargs):
        if value is None:
            return ""
        return self.OUTER_SEP.join(f"{o.pk}{ID_NAME_SEP}{o}" for o in value.all())

    def clean(self, value, row=None, **kwargs):
        text = "" if value is None else str(value)
        ids = []
        for chunk in text.split(";"):
            chunk = chunk.strip()
            if not chunk:
                continue
            match = _LEADING_ID_RE.match(chunk)
            if not match:
                raise ValueError(
                    f'Không đọc được giá trị "{chunk}" — mỗi mục cách nhau bởi ";", định dạng '
                    f'"id{ID_NAME_SEP}tên; id{ID_NAME_SEP}tên".'
                )
            ids.append(match.group(1))
        return self.model.objects.filter(pk__in=ids)


class ExcelModelResource(resources.ModelResource):
    """Base Resource dùng chung cho mọi model — chỉ cần khai `class Meta: model = TênModel`, KHÔNG
    cần khai lại field/widget cho từng khoá ngoại. Tự động áp dụng IdName*Widget cho mọi FK/O2O/M2M
    và dịch tiêu đề cột export sang đúng verbose_name tiếng Việt của model."""

    # django-import-export chỉ map CharField -> CharWidget, KHÔNG map TextField (dù TextField cũng
    # thường blank=True) — để mặc định thì field TextField rơi vào Widget gốc, clean(None) trả về
    # None thay vì "", làm nhập lại 1 ô trống bị lỗi "NOT NULL constraint" (phát hiện qua test
    # round-trip thực tế: model note/mô tả nào cũng là TextField). Model ở đây dùng TextField cho hầu
    # hết các cột ghi chú/mô tả nên bắt buộc phải bổ sung mapping này.
    WIDGETS_MAP = {**resources.ModelResource.WIDGETS_MAP, "TextField": widgets.CharWidget}

    @classmethod
    def get_fk_widget(cls, field):
        return functools.partial(IdNameForeignKeyWidget, model=get_related_model(field))

    @classmethod
    def get_m2m_widget(cls, field):
        return functools.partial(IdNameManyToManyWidget, model=get_related_model(field))

    @classmethod
    def field_from_django_field(cls, field_name, django_field, readonly):
        field = super().field_from_django_field(field_name, django_field, readonly)
        # import_export tự tối ưu FK/O2O thành đọc thẳng cột "<field>_id" (khỏi join) khi Resource
        # không khai Meta.widgets riêng cho field đó — nhưng IdNameForeignKeyWidget cần NGUYÊN bản
        # ghi liên quan (obj.pk, str(obj)) để hiện "id — tên", nên trả .attribute về đúng tên field
        # gốc (bỏ hậu tố "_id") cho FK/O2O.
        if isinstance(django_field, (django_models.ForeignKey, django_models.OneToOneField)):
            auto_id_attribute = f"{field_name}_id"
            if field.attribute == auto_id_attribute:
                field.attribute = field_name
        # Đổi thẳng column_name sang verbose_name tiếng Việt — dùng chung cho cả export (hiện làm
        # tiêu đề cột) lẫn import (field.clean() tra giá trị bằng row[column_name], nên phải khớp
        # đúng tên cột thật trong file, không thể chỉ đổi mỗi header lúc hiển thị).
        field.column_name = str(django_field.verbose_name)
        return field


class ExportOnlyAdmin(ExportMixin):
    """Trộn vào ModelAdmin cho các bảng KHÔNG được nhập qua Excel (auth.User/Group, hr.ProfileChangeLog).
    CHỈ dùng ExportMixin — quan trọng: has_add_permission()/has_change_permission() trên ModelAdmin
    KHÔNG chặn được nút Import của import_export (nó tự kiểm tra quyền Django add_<model>/
    change_<model>, không gọi lại 2 hàm override đó), nên phải chặn từ gốc bằng cách không trộn
    ImportMixin/ImportExportMixin vào — không dựa vào các override has_*_permission."""
