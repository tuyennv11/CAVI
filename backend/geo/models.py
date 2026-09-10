from django.db import models


class Country(models.Model):
    name = models.CharField("Tên", max_length=100, unique=True)
    code = models.CharField("Mã", max_length=5, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Quốc gia"
        verbose_name_plural = "Quốc gia"

    def __str__(self):
        return self.name


class Province(models.Model):
    """Tỉnh/Thành phố — hiện chỉ có dữ liệu đầy đủ cho Việt Nam (63 tỉnh/thành, nguồn
    provinces.open-api.vn). Campuchia/Lào chưa có dữ liệu chuẩn nên chưa nhập cấp này."""

    country = models.ForeignKey(Country, verbose_name="Quốc gia", on_delete=models.CASCADE, related_name="provinces")
    name = models.CharField("Tên", max_length=100)
    code = models.CharField("Mã", max_length=10)
    division_type = models.CharField("Cấp hành chính", max_length=50, blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["country", "code"]
        verbose_name = "Tỉnh/Thành phố"
        verbose_name_plural = "Tỉnh/Thành phố"

    def __str__(self):
        return self.name


class District(models.Model):
    """Quận/Huyện."""

    province = models.ForeignKey(Province, verbose_name="Tỉnh/Thành phố", on_delete=models.CASCADE, related_name="districts")
    name = models.CharField("Tên", max_length=100)
    code = models.CharField("Mã", max_length=10)
    division_type = models.CharField("Cấp hành chính", max_length=50, blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["province", "code"]
        verbose_name = "Quận/Huyện"
        verbose_name_plural = "Quận/Huyện"

    def __str__(self):
        return self.name


class Ward(models.Model):
    """Phường/Xã — cấp thấp nhất, dùng để tính giá gửi hàng theo khu vực."""

    district = models.ForeignKey(District, verbose_name="Quận/Huyện", on_delete=models.CASCADE, related_name="wards")
    name = models.CharField("Tên", max_length=100)
    code = models.CharField("Mã", max_length=10)
    division_type = models.CharField("Cấp hành chính", max_length=50, blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["district", "code"]
        verbose_name = "Phường/Xã"
        verbose_name_plural = "Phường/Xã"

    def __str__(self):
        return self.name
