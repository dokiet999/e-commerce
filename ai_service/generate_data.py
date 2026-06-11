import pandas as pd
import numpy as np
import random
import string
from datetime import datetime, timedelta

# Cấu hình
NUM_USERS = 500
BEHAVIORS_PER_USER = 8
ACTIONS = ['view', 'click', 'add_to_cart', 'purchase', 'wishlist', 'review', 'share', 'compare']
DEVICES = ['mobile', 'desktop', 'tablet']
CATEGORIES = ['electronics', 'fashion', 'food', 'books', 'sports', 'beauty', 'home', 'toys']

# Khoảng thời gian: 2024-01-01 -> 2024-12-31
START_TS = int(datetime(2024, 1, 1, 0, 0, 0).timestamp())
END_TS = int(datetime(2024, 12, 31, 23, 59, 59).timestamp())

# ── User profiles với hành vi khác nhau ──
# Mỗi profile có phân phối action riêng (tạo pattern cho model học)
USER_PROFILES = {
    'browser': {
        'weight': 0.30,
        'action_weights': [0.35, 0.30, 0.05, 0.02, 0.08, 0.02, 0.08, 0.10],
        'device_weights': [0.6, 0.2, 0.2],
        'preferred_categories': ['electronics', 'fashion', 'toys'],
        'duration_range': (5, 120),
    },
    'buyer': {
        'weight': 0.25,
        'action_weights': [0.15, 0.15, 0.20, 0.25, 0.05, 0.10, 0.05, 0.05],
        'device_weights': [0.3, 0.5, 0.2],
        'preferred_categories': ['electronics', 'home', 'beauty'],
        'duration_range': (60, 600),
    },
    'researcher': {
        'weight': 0.20,
        'action_weights': [0.20, 0.15, 0.05, 0.03, 0.10, 0.02, 0.15, 0.30],
        'device_weights': [0.2, 0.6, 0.2],
        'preferred_categories': ['books', 'electronics', 'sports'],
        'duration_range': (120, 500),
    },
    'social': {
        'weight': 0.15,
        'action_weights': [0.15, 0.15, 0.05, 0.05, 0.20, 0.15, 0.20, 0.05],
        'device_weights': [0.7, 0.1, 0.2],
        'preferred_categories': ['fashion', 'beauty', 'food'],
        'duration_range': (10, 200),
    },
    'deal_hunter': {
        'weight': 0.10,
        'action_weights': [0.10, 0.10, 0.30, 0.20, 0.15, 0.05, 0.02, 0.08],
        'device_weights': [0.5, 0.3, 0.2],
        'preferred_categories': ['food', 'home', 'toys'],
        'duration_range': (30, 300),
    },
}

# Category → Product mapping (mỗi category có range sản phẩm riêng)
CATEGORY_PRODUCTS = {
    'electronics': list(range(1, 16)),    # P001-P015
    'fashion':     list(range(16, 28)),   # P016-P027
    'food':        list(range(28, 40)),   # P028-P039
    'books':       list(range(40, 52)),   # P040-P051
    'sports':      list(range(52, 64)),   # P052-P063
    'beauty':      list(range(64, 76)),   # P064-P075
    'home':        list(range(76, 88)),   # P076-P087
    'toys':        list(range(88, 101)),  # P088-P100
}


def generate_session_id():
    """Sinh session_id dạng SESS_XXXXX (5 ký tự alphanumeric uppercase)"""
    chars = string.ascii_uppercase + string.digits
    return 'SESS_' + ''.join(random.choices(chars, k=5))


def generate_data():
    random.seed(42)
    np.random.seed(42)

    profile_names = list(USER_PROFILES.keys())
    profile_weights = [USER_PROFILES[p]['weight'] for p in profile_names]

    rows = []
    for i in range(1, NUM_USERS + 1):
        user_id = f'U{i:03d}'

        # Gán profile cho user
        profile_name = random.choices(profile_names, weights=profile_weights, k=1)[0]
        profile = USER_PROFILES[profile_name]

        # User có 1-2 category yêu thích (70% từ preferred, 30% random)
        preferred_cats = profile['preferred_categories']

        # Device ưu tiên theo profile
        device_weights = profile['device_weights']

        # Sinh chuỗi hành vi theo funnel logic
        # Bước đầu luôn bắt đầu bằng view/click, sau đó theo pattern profile
        base_ts = random.randint(START_TS, END_TS - 86400 * 7)  # Bắt đầu trong 1 tuần

        for step in range(BEHAVIORS_PER_USER):
            # Category: 70% preferred, 30% random
            if random.random() < 0.70:
                category = random.choice(preferred_cats)
            else:
                category = random.choice(CATEGORIES)

            # Product thuộc category đã chọn
            product_num = random.choice(CATEGORY_PRODUCTS[category])
            product_id = f'P{product_num:03d}'

            # Action theo funnel: đầu chuỗi nghiêng view/click, cuối chuỗi nghiêng purchase/review
            if step < 2:
                # 2 hành vi đầu: chủ yếu view/click (khám phá)
                funnel_weights = [0.40, 0.35, 0.05, 0.02, 0.05, 0.01, 0.07, 0.05]
            elif step < 5:
                # Giữa: theo đúng profile
                funnel_weights = profile['action_weights']
            else:
                # 3 hành vi cuối: nghiêng về hành động quyết định
                if profile_name == 'buyer':
                    funnel_weights = [0.05, 0.05, 0.15, 0.40, 0.05, 0.20, 0.05, 0.05]
                elif profile_name == 'deal_hunter':
                    funnel_weights = [0.05, 0.05, 0.25, 0.35, 0.10, 0.10, 0.05, 0.05]
                elif profile_name == 'researcher':
                    funnel_weights = [0.10, 0.10, 0.05, 0.05, 0.05, 0.05, 0.20, 0.40]
                elif profile_name == 'social':
                    funnel_weights = [0.05, 0.05, 0.05, 0.05, 0.25, 0.25, 0.25, 0.05]
                else:  # browser
                    funnel_weights = [0.30, 0.30, 0.10, 0.05, 0.10, 0.02, 0.08, 0.05]

            action = random.choices(ACTIONS, weights=funnel_weights, k=1)[0]

            # Timestamp tăng dần trong session (mô phỏng chuỗi hành vi liên tục)
            ts = datetime.fromtimestamp(base_ts + step * random.randint(60, 3600))
            timestamp = ts.strftime('%Y-%m-%d %H:%M:%S')

            session_id = generate_session_id()

            # Duration phụ thuộc action + profile
            dur_min, dur_max = profile['duration_range']
            if action == 'view':
                duration_seconds = random.randint(dur_min, min(dur_min + 60, dur_max))
            elif action == 'purchase':
                duration_seconds = random.randint(max(dur_min, 120), dur_max)
            elif action in ['compare', 'review']:
                duration_seconds = random.randint(max(dur_min, 60), dur_max)
            else:
                duration_seconds = random.randint(dur_min, dur_max)

            device = random.choices(DEVICES, weights=device_weights, k=1)[0]

            rows.append({
                'user_id': user_id,
                'product_id': product_id,
                'action': action,
                'timestamp': timestamp,
                'session_id': session_id,
                'duration_seconds': duration_seconds,
                'device': device,
                'category': category,
            })

    df = pd.DataFrame(rows)
    return df


if __name__ == '__main__':
    df = generate_data()

    # In 20 dòng đầu
    print("=" * 80)
    print("20 DÒNG ĐẦU TIÊN:")
    print("=" * 80)
    print(df.head(20).to_string(index=False))

    # Lưu file CSV
    output_path = 'data_user500.csv'
    df.to_csv(output_path, index=False)
    print(f"\nĐã lưu file: {output_path}")

    # Thống kê
    print("\n" + "=" * 80)
    print("THỐNG KÊ:")
    print("=" * 80)
    print(f"Số dòng : {df.shape[0]}")
    print(f"Số cột  : {df.shape[1]}")

    print("\nPhân phối ACTION:")
    print(df['action'].value_counts().to_string())

    print("\nPhân phối DEVICE:")
    print(df['device'].value_counts().to_string())
