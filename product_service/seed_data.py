import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'product_config.settings')
django.setup()

from products.models import Category, SubCategory, Product

# ── Categories ────────────────────────────────────────────────────────────────
cats = {}
for name in ['Electronics', 'Clothing', 'Cosmetics', 'Home & Garden', 'Sports', 'Books', 'Toys']:
    c, _ = Category.objects.get_or_create(name=name)
    cats[name] = c
    print(f'Category: {c.name} (id={c.id})')

# ── SubCategories ─────────────────────────────────────────────────────────────
SUBCATEGORY_MAP = {
    'Electronics': ['Điện thoại', 'Laptop', 'Tai nghe', 'Máy tính bảng', 'Loa'],
    'Clothing':    ['Áo', 'Quần', 'Giày', 'Mũ', 'Túi xách'],
    'Cosmetics':   ['Son môi', 'Phấn', 'Kem dưỡng da', 'Nước hoa', 'Mascara'],
    'Home & Garden': ['Bếp', 'Nội thất', 'Điện gia dụng', 'Vườn'],
    'Sports':      ['Giày thể thao', 'Dụng cụ tập gym', 'Bóng', 'Bình nước'],
    'Books':       ['Kỹ năng sống', 'Tiểu thuyết', 'Kỹ thuật', 'Kinh doanh'],
    'Toys':        ['Đồ chơi xếp hình', 'Máy chơi game', 'Búp bê', 'Xe mô hình'],
}

subcats = {}
for cat_name, sub_names in SUBCATEGORY_MAP.items():
    subcats[cat_name] = {}
    for sub_name in sub_names:
        sc, _ = SubCategory.objects.get_or_create(
            category=cats[cat_name], name=sub_name
        )
        subcats[cat_name][sub_name] = sc
        print(f'  SubCategory: {cat_name} > {sub_name} (id={sc.id})')

# ── Products ──────────────────────────────────────────────────────────────────
# (name, description, price_vnd, stock, category, subcategory, image_url)
products_data = [
    # ── Electronics ───────────────────────────────────────────────────────────
    ('iPhone 15 Pro Max',
     'Smartphone Apple với chip A17 Pro, camera 48MP, thiết kế titanium',
     34990000, 25, 'Electronics', 'Điện thoại',
     'https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=400&h=400&fit=crop'),

    ('Samsung Galaxy S24 Ultra',
     'Flagship Samsung với S Pen, camera 200MP, Snapdragon 8 Gen 3',
     29990000, 30, 'Electronics', 'Điện thoại',
     'https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop'),

    ('Sony WH-1000XM5',
     'Tai nghe chống ồn không dây cao cấp, pin 30 giờ',
     7490000, 50, 'Electronics', 'Tai nghe',
     'https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?w=400&h=400&fit=crop'),

    ('MacBook Air M3',
     'Laptop Apple 13 inch Liquid Retina, pin 18 giờ, 8GB RAM',
     27990000, 20, 'Electronics', 'Laptop',
     'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop'),

    ('iPad Air M2',
     'Máy tính bảng 11 inch Liquid Retina, chip M2, hỗ trợ Apple Pencil',
     15990000, 40, 'Electronics', 'Máy tính bảng',
     'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop'),

    ('Bose SoundLink Flex',
     'Loa Bluetooth di động chống nước, pin 12 giờ',
     3290000, 70, 'Electronics', 'Loa',
     'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=400&fit=crop'),

    # ── Clothing ──────────────────────────────────────────────────────────────
    ('Nike Air Max 270',
     'Giày sneaker lifestyle với đệm Air Max thoải mái',
     3490000, 100, 'Clothing', 'Giày',
     'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop'),

    ("Levi's 501 Original Jeans",
     'Quần jeans ống đứng cổ điển, 100% cotton',
     1690000, 200, 'Clothing', 'Quần',
     'https://images.unsplash.com/photo-1542272604-787c3835535d?w=400&h=400&fit=crop'),

    ('North Face Puffer Jacket',
     'Áo khoác phao lông vũ 700-fill, chống nước',
     5990000, 40, 'Clothing', 'Áo',
     'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=400&h=400&fit=crop'),

    ('New Era 59FIFTY Cap',
     'Mũ lưỡi trai fitted, form cứng, vành phẳng',
     890000, 120, 'Clothing', 'Mũ',
     'https://images.unsplash.com/photo-1588850561407-ed78c334e67a?w=400&h=400&fit=crop'),

    ('Coach Leather Tote Bag',
     'Túi xách da sần cao cấp, khóa kéo, nhiều ngăn',
     7490000, 30, 'Clothing', 'Túi xách',
     'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400&h=400&fit=crop'),

    # ── Cosmetics ─────────────────────────────────────────────────────────────
    ('MAC Ruby Woo Lipstick',
     'Son lì màu đỏ huyền thoại, bền màu cả ngày',
     490000, 150, 'Cosmetics', 'Son môi',
     'https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=400&h=400&fit=crop'),

    ('NARS Radiant Creamy Concealer',
     'Kem che khuyết điểm dạng lỏng, độ che phủ cao',
     790000, 80, 'Cosmetics', 'Kem dưỡng da',
     'https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=400&h=400&fit=crop'),

    ('Charlotte Tilbury Flawless Powder',
     'Phấn phủ mịn da, hiệu ứng soft-focus',
     1090000, 60, 'Cosmetics', 'Phấn',
     'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&h=400&fit=crop'),

    ('Chanel Chance Eau Tendre',
     'Nước hoa Eau de Toilette hương hoa tươi mát, 100ml',
     3590000, 40, 'Cosmetics', 'Nước hoa',
     'https://images.unsplash.com/photo-1541643600914-78b084683601?w=400&h=400&fit=crop'),

    ('Maybelline Sky High Mascara',
     'Mascara kéo dài và nâng mi, công thức xây lớp',
     299000, 200, 'Cosmetics', 'Mascara',
     'https://images.unsplash.com/photo-1631214500115-598fc2cb8ada?w=400&h=400&fit=crop'),

    # ── Home & Garden ─────────────────────────────────────────────────────────
    ('Dyson V15 Detect',
     'Máy hút bụi không dây, công nghệ phát hiện bụi bằng laser',
     18990000, 15, 'Home & Garden', 'Điện gia dụng',
     'https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=400&h=400&fit=crop'),

    ('Instant Pot Duo 7-in-1',
     'Nồi áp suất điện đa năng 7 trong 1: hầm, nấu cơm, nấu chậm',
     2290000, 80, 'Home & Garden', 'Bếp',
     'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop'),

    ('KitchenAid Stand Mixer',
     'Máy trộn bột đứng Artisan 5 Quart, đa năng',
     9490000, 35, 'Home & Garden', 'Bếp',
     'https://images.unsplash.com/photo-1594385208974-2f8bb07b2b6b?w=400&h=400&fit=crop'),

    # ── Sports ────────────────────────────────────────────────────────────────
    ('Yeti Rambler 30oz',
     'Bình giữ nhiệt inox 2 lớp chân không, 900ml',
     890000, 150, 'Sports', 'Bình nước',
     'https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=400&h=400&fit=crop'),

    ('Adidas Ultraboost',
     'Giày chạy bộ đệm Boost, upper Primeknit thoáng khí',
     4490000, 60, 'Sports', 'Giày thể thao',
     'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=400&h=400&fit=crop'),

    ('Wilson Evolution Basketball',
     'Bóng rổ thi đấu trong nhà, da tổng hợp thấm hút mồ hôi',
     1690000, 45, 'Sports', 'Bóng',
     'https://images.unsplash.com/photo-1494199505258-5f95387f933c?w=400&h=400&fit=crop'),

    ('Columbia Hiking Boots',
     'Giày leo núi chống nước, đế Omni-Grip bám tốt',
     2990000, 55, 'Sports', 'Giày thể thao',
     'https://images.unsplash.com/photo-1520219306100-ec4afeeefe58?w=400&h=400&fit=crop'),

    # ── Books ─────────────────────────────────────────────────────────────────
    ('Atomic Habits - James Clear',
     'Sách best-seller về xây dựng thói quen tốt, phá bỏ thói quen xấu',
     199000, 300, 'Books', 'Kỹ năng sống',
     'https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400&h=400&fit=crop'),

    ('The Midnight Library - Matt Haig',
     'Tiểu thuyết cảm động về những khả năng vô hạn của cuộc sống',
     169000, 120, 'Books', 'Tiểu thuyết',
     'https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400&h=400&fit=crop'),

    # ── Toys ──────────────────────────────────────────────────────────────────
    ('LEGO Star Wars Millennium Falcon',
     'Bộ xếp hình 1351 mảnh, 7 nhân vật, nội thất chi tiết',
     4290000, 22, 'Toys', 'Đồ chơi xếp hình',
     'https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop'),

    ('Nintendo Switch OLED',
     'Máy chơi game OLED 7 inch, âm thanh nâng cấp, 64GB',
     7990000, 55, 'Toys', 'Máy chơi game',
     'https://images.unsplash.com/photo-1578303512597-81e6cc155b3e?w=400&h=400&fit=crop'),
]

# Xóa sản phẩm cũ và tạo lại
Product.objects.all().delete()
print('Deleted old products.')

for name, desc, price, stock, cat_name, subcat_name, img in products_data:
    p = Product.objects.create(
        name=name,
        description=desc,
        price=price,
        stock=stock,
        category=cats[cat_name],
        subcategory=subcats[cat_name][subcat_name],
        image_url=img,
    )
    print(f'Created: {p.name} [{cat_name} > {subcat_name}] - {p.price:,.0f}₫')

print(f'\nTotal: {Product.objects.count()} products, '
      f'{Category.objects.count()} categories, '
      f'{SubCategory.objects.count()} subcategories')

