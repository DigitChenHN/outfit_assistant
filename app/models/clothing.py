from datetime import datetime
import json
from app import db

class Clothing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(20), nullable=False)  # 上装/下装/鞋子/配饰
    description = db.Column(db.String(200), nullable=False)  # 详细描述，如"深海蓝修身羊毛呢大衣"
    seasons = db.Column(db.String(50))                   # 适用季节，存储为JSON数组
    occasions = db.Column(db.String(100))                # 适用场合，存储为JSON数组
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Clothing, self).__init__(**kwargs)
        # 确保seasons和occasions是JSON字符串
        if 'seasons' in kwargs and not isinstance(kwargs['seasons'], str):
            self.seasons = json.dumps(kwargs['seasons'])
        if 'occasions' in kwargs and not isinstance(kwargs['occasions'], str):
            self.occasions = json.dumps(kwargs['occasions'])

    @property
    def seasons_list(self):
        """获取季节列表"""
        return json.loads(self.seasons) if self.seasons else []

    @property
    def occasions_list(self):
        """获取场合列表"""
        return json.loads(self.occasions) if self.occasions else []

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'category': self.category,
            'description': self.description,
            'seasons': self.seasons_list,
            'occasions': self.occasions_list,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<Clothing {self.category}-{self.description}>'

# 定义常量
CATEGORIES = {
    'tops': '上装',
    'bottoms': '下装',
    'shoes': '鞋子',
    'accessories': '配饰'
}

SEASONS = ['春', '夏', '秋', '冬']

OCCASIONS = ['日常', '工作', '运动', '正式', '休闲', '派对']

# 示例描述，用于前端提示
DESCRIPTION_EXAMPLES = [
    "深海蓝修身羊毛呢大衣",
    "米白色宽松棉麻衬衫",
    "黑色直筒西装裤",
    "棕色真皮布洛克皮鞋",
    "藏青色羊绒围巾",
    "浅灰色休闲运动卫衣",
    "深绿色格纹羊毛西装",
    "水洗蓝直筒牛仔裤",
    "白色简约帆布鞋"
]