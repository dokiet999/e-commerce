import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "product_config.settings")
django.setup()

from products.models import (  # noqa: E402
    Category,
    ClothesProduct,
    ComputerProduct,
    MobileProduct,
    Product,
    SubCategory,
)


def get_category(name):
    category, _ = Category.objects.get_or_create(name=name)
    return category


def get_subcategory(category, name):
    subcategory, _ = SubCategory.objects.get_or_create(
        category=category,
        name=name,
    )
    return subcategory


def upsert_product(item):
    category = get_category(item["category"])
    subcategory = get_subcategory(category, item["subcategory"])

    product, created = Product.objects.update_or_create(
        name=item["name"],
        defaults={
            "description": item["description"],
            "price": item["price"],
            "stock": item["stock"],
            "category": category,
            "subcategory": subcategory,
            "image_url": item["image_url"],
            "is_active": True,
        },
    )
    return product, created


MOBILE_PRODUCTS = [
    {
        "name": "iPhone 16 Pro Max",
        "description": "Điện thoại Apple cao cấp với màn hình ProMotion, camera chuyên nghiệp và hiệu năng mạnh.",
        "price": 36990000,
        "stock": 22,
        "category": "Electronics",
        "subcategory": "Điện thoại",
        "image_url": "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop",
        "details": {"brand": "Apple", "screen_size": "6.9 inch", "battery": "4685 mAh", "operating_system": "iOS"},
    },
    {
        "name": "iPhone 15",
        "description": "Điện thoại Apple phổ thông với Dynamic Island, camera 48MP và cổng USB-C.",
        "price": 19990000,
        "stock": 45,
        "category": "Electronics",
        "subcategory": "Điện thoại",
        "image_url": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=400&h=400&fit=crop",
        "details": {"brand": "Apple", "screen_size": "6.1 inch", "battery": "3349 mAh", "operating_system": "iOS"},
    },
    {
        "name": "Samsung Galaxy Z Fold6",
        "description": "Điện thoại gập cao cấp, màn hình lớn cho đa nhiệm và làm việc di động.",
        "price": 41990000,
        "stock": 18,
        "category": "Electronics",
        "subcategory": "Điện thoại",
        "image_url": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop",
        "details": {"brand": "Samsung", "screen_size": "7.6 inch", "battery": "4400 mAh", "operating_system": "Android"},
    },
    {
        "name": "Samsung Galaxy A55 5G",
        "description": "Smartphone tầm trung hỗ trợ 5G, màn hình AMOLED và pin dùng cả ngày.",
        "price": 9690000,
        "stock": 70,
        "category": "Electronics",
        "subcategory": "Điện thoại",
        "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&h=400&fit=crop",
        "details": {"brand": "Samsung", "screen_size": "6.6 inch", "battery": "5000 mAh", "operating_system": "Android"},
    },
    {
        "name": "Xiaomi 14 Ultra",
        "description": "Flagship Xiaomi với cụm camera Leica, sạc nhanh và màn hình sáng.",
        "price": 29990000,
        "stock": 25,
        "category": "Electronics",
        "subcategory": "Điện thoại",
        "image_url": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop",
        "details": {"brand": "Xiaomi", "screen_size": "6.73 inch", "battery": "5000 mAh", "operating_system": "Android"},
    },
    {
        "name": "OPPO Reno12 Pro",
        "description": "Điện thoại chụp chân dung đẹp, thiết kế mỏng nhẹ và sạc nhanh.",
        "price": 18990000,
        "stock": 38,
        "category": "Electronics",
        "subcategory": "Điện thoại",
        "image_url": "https://images.unsplash.com/photo-1567581935884-3349723552ca?w=400&h=400&fit=crop",
        "details": {"brand": "OPPO", "screen_size": "6.7 inch", "battery": "5000 mAh", "operating_system": "Android"},
    },
    {
        "name": "Google Pixel 8 Pro",
        "description": "Điện thoại Android thuần, camera AI mạnh và cập nhật phần mềm lâu dài.",
        "price": 23990000,
        "stock": 20,
        "category": "Electronics",
        "subcategory": "Điện thoại",
        "image_url": "https://images.unsplash.com/photo-1598965402089-897ce52e8355?w=400&h=400&fit=crop",
        "details": {"brand": "Google", "screen_size": "6.7 inch", "battery": "5050 mAh", "operating_system": "Android"},
    },
]


LAPTOP_PRODUCTS = [
    {
        "name": "MacBook Pro 14 M3 Pro",
        "description": "Laptop Apple cho lập trình, thiết kế và dựng video với màn hình Liquid Retina XDR.",
        "price": 52990000,
        "stock": 12,
        "category": "Electronics",
        "subcategory": "Laptop",
        "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop",
        "details": {"brand": "Apple", "ram": "18GB", "storage": "512GB SSD", "cpu": "Apple M3 Pro", "screen_size": "14.2 inch"},
    },
    {
        "name": "Dell XPS 13 Plus",
        "description": "Ultrabook cao cấp, thiết kế mỏng nhẹ, phù hợp làm việc văn phòng và di chuyển.",
        "price": 35990000,
        "stock": 16,
        "category": "Electronics",
        "subcategory": "Laptop",
        "image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400&h=400&fit=crop",
        "details": {"brand": "Dell", "ram": "16GB", "storage": "1TB SSD", "cpu": "Intel Core Ultra 7", "screen_size": "13.4 inch"},
    },
    {
        "name": "ASUS ROG Zephyrus G14",
        "description": "Laptop gaming mỏng nhẹ, GPU rời mạnh, màn hình OLED tần số quét cao.",
        "price": 42990000,
        "stock": 14,
        "category": "Electronics",
        "subcategory": "Laptop",
        "image_url": "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=400&h=400&fit=crop",
        "details": {"brand": "ASUS", "ram": "32GB", "storage": "1TB SSD", "cpu": "AMD Ryzen 9", "screen_size": "14 inch"},
    },
    {
        "name": "Lenovo ThinkPad X1 Carbon Gen 12",
        "description": "Laptop doanh nhân bền bỉ, bàn phím tốt, bảo mật cao và trọng lượng nhẹ.",
        "price": 46990000,
        "stock": 10,
        "category": "Electronics",
        "subcategory": "Laptop",
        "image_url": "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=400&h=400&fit=crop",
        "details": {"brand": "Lenovo", "ram": "16GB", "storage": "1TB SSD", "cpu": "Intel Core Ultra 7", "screen_size": "14 inch"},
    },
    {
        "name": "HP Spectre x360 14",
        "description": "Laptop 2-in-1 màn hình cảm ứng, phù hợp ghi chú, thuyết trình và làm việc sáng tạo.",
        "price": 38990000,
        "stock": 18,
        "category": "Electronics",
        "subcategory": "Laptop",
        "image_url": "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop",
        "details": {"brand": "HP", "ram": "16GB", "storage": "1TB SSD", "cpu": "Intel Core Ultra 5", "screen_size": "14 inch"},
    },
    {
        "name": "Acer Nitro V 15",
        "description": "Laptop gaming phổ thông, cấu hình tốt cho học tập, chơi game và đồ họa cơ bản.",
        "price": 22990000,
        "stock": 32,
        "category": "Electronics",
        "subcategory": "Laptop",
        "image_url": "https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?w=400&h=400&fit=crop",
        "details": {"brand": "Acer", "ram": "16GB", "storage": "512GB SSD", "cpu": "Intel Core i5", "screen_size": "15.6 inch"},
    },
    {
        "name": "MSI Modern 14",
        "description": "Laptop học tập và văn phòng giá tốt, thiết kế gọn nhẹ, pin ổn định.",
        "price": 14990000,
        "stock": 45,
        "category": "Electronics",
        "subcategory": "Laptop",
        "image_url": "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop",
        "details": {"brand": "MSI", "ram": "16GB", "storage": "512GB SSD", "cpu": "Intel Core i5", "screen_size": "14 inch"},
    },
]


CLOTHES_PRODUCTS = [
    {
        "name": "Uniqlo AIRism Cotton T-Shirt",
        "description": "Áo thun cotton thoáng mát, phù hợp mặc hàng ngày.",
        "price": 399000,
        "stock": 160,
        "category": "Clothing",
        "subcategory": "Áo",
        "image_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop",
        "details": {"size": "S/M/L/XL", "color": "White", "material": "Cotton blend", "gender": "Unisex"},
    },
    {
        "name": "Nike Sportswear Club Hoodie",
        "description": "Áo hoodie nỉ mềm, form regular, phù hợp đi học và đi chơi.",
        "price": 1290000,
        "stock": 80,
        "category": "Clothing",
        "subcategory": "Áo",
        "image_url": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=400&h=400&fit=crop",
        "details": {"size": "M/L/XL", "color": "Black", "material": "Fleece", "gender": "Unisex"},
    },
    {
        "name": "Zara Linen Shirt",
        "description": "Áo sơ mi linen nhẹ, thoáng, phù hợp thời tiết nóng.",
        "price": 999000,
        "stock": 65,
        "category": "Clothing",
        "subcategory": "Áo",
        "image_url": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=400&h=400&fit=crop",
        "details": {"size": "S/M/L", "color": "Beige", "material": "Linen", "gender": "Men"},
    },
    {
        "name": "Adidas Tiro Track Pants",
        "description": "Quần thể thao co giãn, phù hợp tập luyện và mặc thường ngày.",
        "price": 1090000,
        "stock": 90,
        "category": "Clothing",
        "subcategory": "Quần",
        "image_url": "https://images.unsplash.com/photo-1506629905607-d9c297d87d4a?w=400&h=400&fit=crop",
        "details": {"size": "S/M/L/XL", "color": "Black", "material": "Polyester", "gender": "Unisex"},
    },
    {
        "name": "Levi's 511 Slim Jeans",
        "description": "Quần jeans slim fit, dễ phối với áo thun hoặc sơ mi.",
        "price": 1890000,
        "stock": 75,
        "category": "Clothing",
        "subcategory": "Quần",
        "image_url": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=400&h=400&fit=crop",
        "details": {"size": "29-34", "color": "Dark Blue", "material": "Denim", "gender": "Men"},
    },
    {
        "name": "H&M Pleated Skirt",
        "description": "Chân váy xếp ly nhẹ, phong cách tối giản, dễ phối đồ.",
        "price": 799000,
        "stock": 70,
        "category": "Clothing",
        "subcategory": "Quần",
        "image_url": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=400&h=400&fit=crop",
        "details": {"size": "S/M/L", "color": "Cream", "material": "Polyester", "gender": "Women"},
    },
    {
        "name": "Puma Suede Classic",
        "description": "Giày sneaker cổ điển, chất liệu da lộn, dễ phối đồ.",
        "price": 2190000,
        "stock": 58,
        "category": "Clothing",
        "subcategory": "Giày",
        "image_url": "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=400&h=400&fit=crop",
        "details": {"size": "39-44", "color": "Navy", "material": "Suede", "gender": "Unisex"},
    },
    {
        "name": "Converse Chuck Taylor 70",
        "description": "Giày canvas cổ cao, thiết kế biểu tượng, phù hợp nhiều phong cách.",
        "price": 1990000,
        "stock": 100,
        "category": "Clothing",
        "subcategory": "Giày",
        "image_url": "https://images.unsplash.com/photo-1607522370275-f14206abe5d3?w=400&h=400&fit=crop",
        "details": {"size": "36-44", "color": "Black", "material": "Canvas", "gender": "Unisex"},
    },
    {
        "name": "MLB New York Yankees Cap",
        "description": "Mũ lưỡi trai logo Yankees, form classic, chất cotton bền.",
        "price": 890000,
        "stock": 95,
        "category": "Clothing",
        "subcategory": "Mũ",
        "image_url": "https://images.unsplash.com/photo-1588850561407-ed78c334e67a?w=400&h=400&fit=crop",
        "details": {"size": "Free size", "color": "Navy", "material": "Cotton", "gender": "Unisex"},
    },
    {
        "name": "Charles & Keith Crossbody Bag",
        "description": "Túi đeo chéo nhỏ gọn, phù hợp đi làm và đi chơi.",
        "price": 1590000,
        "stock": 48,
        "category": "Clothing",
        "subcategory": "Túi xách",
        "image_url": "https://images.unsplash.com/photo-1590874103328-eac38a683ce7?w=400&h=400&fit=crop",
        "details": {"size": "Small", "color": "Brown", "material": "Faux leather", "gender": "Women"},
    },
]


EXISTING_DETAILS = [
    {
        "type": "mobile",
        "name": "iPhone 15 Pro Max",
        "details": {"brand": "Apple", "screen_size": "6.7 inch", "battery": "4441 mAh", "operating_system": "iOS"},
    },
    {
        "type": "mobile",
        "name": "Samsung Galaxy S24 Ultra",
        "details": {"brand": "Samsung", "screen_size": "6.8 inch", "battery": "5000 mAh", "operating_system": "Android"},
    },
    {
        "type": "computer",
        "name": "MacBook Air M3",
        "details": {"brand": "Apple", "ram": "8GB", "storage": "256GB SSD", "cpu": "Apple M3", "screen_size": "13.6 inch"},
    },
    {
        "type": "clothes",
        "name": "Nike Air Max 270",
        "details": {"size": "39-44", "color": "Black/White", "material": "Mesh and synthetic", "gender": "Unisex"},
    },
    {
        "type": "clothes",
        "name": "Levi's 501 Original Jeans",
        "details": {"size": "29-34", "color": "Blue", "material": "Cotton denim", "gender": "Men"},
    },
    {
        "type": "clothes",
        "name": "North Face Puffer Jacket",
        "details": {"size": "M/L/XL", "color": "Black", "material": "Nylon and down", "gender": "Unisex"},
    },
]


def upsert_details(product, detail_type, details):
    if detail_type == "mobile":
        MobileProduct.objects.update_or_create(product=product, defaults=details)
    elif detail_type == "computer":
        ComputerProduct.objects.update_or_create(product=product, defaults=details)
    elif detail_type == "clothes":
        ClothesProduct.objects.update_or_create(product=product, defaults=details)


def main():
    created_count = 0
    updated_count = 0

    for item in MOBILE_PRODUCTS:
        product, created = upsert_product(item)
        upsert_details(product, "mobile", item["details"])
        created_count += int(created)
        updated_count += int(not created)

    for item in LAPTOP_PRODUCTS:
        product, created = upsert_product(item)
        upsert_details(product, "computer", item["details"])
        created_count += int(created)
        updated_count += int(not created)

    for item in CLOTHES_PRODUCTS:
        product, created = upsert_product(item)
        upsert_details(product, "clothes", item["details"])
        created_count += int(created)
        updated_count += int(not created)

    for item in EXISTING_DETAILS:
        product = Product.objects.filter(name=item["name"]).first()
        if product:
            upsert_details(product, item["type"], item["details"])

    print(f"Created products: {created_count}")
    print(f"Updated products: {updated_count}")
    print(f"Total products: {Product.objects.count()}")
    print(f"Mobile detail rows: {MobileProduct.objects.count()}")
    print(f"Computer detail rows: {ComputerProduct.objects.count()}")
    print(f"Clothes detail rows: {ClothesProduct.objects.count()}")


if __name__ == "__main__":
    main()
