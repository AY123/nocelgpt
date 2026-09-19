"""
Commercial Constitution - 作品级商业规则 (P2-1)

冻结核心商业定位，确保所有章节对齐。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json


class Platform(Enum):
    """目标平台"""
    QIDIAN = "qidian"           # 起点中文网
    TOMATO = "tomato"           # 番茄小说
    QIMAO = "qimao"             # 七猫免费小说
    ZONGHENG = "zongheng"       # 纵横中文网
    JJWXC = "jjwxc"            # 晋江文学城


class Genre(Enum):
    """题材类型"""
    XUANHUAN = "xuanhuan"       # 玄幻
    XIUZHEN = "xiuzhen"         # 修真
    DUSHI = "dushi"             # 都市
    KEHUAN = "kehuan"           # 科幻
    LISHI = "lishi"             # 历史
    JUNSHI = "junshi"           # 军事
    YOUXI = "youxi"             # 游戏
    JINGJI = "jingji"           # 竞技
    XUANYI = "xuanyi"           # 悬疑
    QIHUAN = "qihuan"           # 奇幻


class AgeGroup(Enum):
    """年龄段"""
    TEEN = "teen"               # 青少年 (13-17)
    YOUNG_ADULT = "young_adult" # 青年 (18-25)
    ADULT = "adult"             # 成年 (26-35)
    MIDDLE_AGE = "middle_age"   # 中年 (36-50)


class Gender(Enum):
    """性别倾向"""
    MALE = "male"               # 男频
    FEMALE = "female"           # 女频
    NEUTRAL = "neutral"         # 中性


class PaymentWillingness(Enum):
    """付费意愿"""
    HIGH = "high"               # 高（愿意为内容付费）
    MEDIUM = "medium"           # 中（有条件付费）
    LOW = "low"                 # 低（倾向免费）


@dataclass
class AudienceProfile:
    """受众画像"""
    age_group: AgeGroup
    gender: Gender
    payment_willingness: PaymentWillingness

    # 阅读偏好
    reading_speed: str          # "fast" | "moderate" | "slow"
    content_preference: List[str]  # ["爽文", "剧情", "升级", "感情"]

    # 痛点和需求
    pain_points: List[str]      # 受众的痛点（无聊、压力、焦虑等）
    fulfillment_needs: List[str]  # 满足的需求（成就感、代入感、情绪宣泄）


@dataclass
class SellingPoint:
    """卖点"""
    name: str                   # 卖点名称
    description: str            # 详细描述
    type: str                   # "emotional" | "plot" | "power" | "relationship"

    # 实现方式
    delivery_mechanism: str     # 如何传递这个卖点
    frequency: str              # "every_chapter" | "every_3_chapters" | "arc_milestone"

    # 验证标准
    validation_keywords: List[str]  # 关键词（用于检测）
    minimum_intensity: float    # 最低强度 (0-1)


@dataclass
class ConstitutionConstraints:
    """商业约束"""

    # 内容约束
    forbidden_elements: List[str]  # 禁止元素（政治敏感、暴力过度等）
    required_elements: List[str]   # 必需元素（主角光环、正能量等）

    # 节奏约束
    min_hook_score: float       # 最低钩子分数
    max_chapters_without_payoff: int  # 最多多少章无爽点

    # 商业约束
    target_chapter_length: int  # 目标章节字数
    paywall_earliest_chapter: int  # 最早付费章节

    # 题材约束
    genre_drift_tolerance: float  # 题材漂移容忍度 (0-1)


@dataclass
class CommercialConstitution:
    """
    作品级商业规则宪法

    这是整个作品的商业"宪法"，定义了：
    - 我们的目标是什么？（平台、题材、受众）
    - 我们的卖点是什么？（核心吸引力）
    - 我们的底线是什么？（约束和禁区）

    所有章节必须符合这个宪法，违反宪法的章节应该被标记或拒绝。
    """

    # 基础定位
    constitution_id: str
    work_title: str

    # 平台和题材
    target_platform: Platform
    primary_genre: Genre

    # 受众定位
    primary_audience: AudienceProfile

    # 有默认值的字段必须在后面
    secondary_genres: List[Genre] = field(default_factory=list)
    secondary_audiences: List[AudienceProfile] = field(default_factory=list)

    # 核心卖点
    core_selling_points: List[SellingPoint] = field(default_factory=list)

    # 差异化定位
    differentiation_tags: List[str] = field(default_factory=list)  # ["硬核系统流", "热血战斗"]
    unique_selling_proposition: str = ""  # 独特卖点（一句话）

    # 商业约束
    constraints: Optional[ConstitutionConstraints] = None

    # 元数据
    created_at: str = ""
    updated_at: str = ""
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "constitution_id": self.constitution_id,
            "work_title": self.work_title,
            "target_platform": self.target_platform.value,
            "primary_genre": self.primary_genre.value,
            "secondary_genres": [g.value for g in self.secondary_genres],
            "primary_audience": {
                "age_group": self.primary_audience.age_group.value,
                "gender": self.primary_audience.gender.value,
                "payment_willingness": self.primary_audience.payment_willingness.value,
                "reading_speed": self.primary_audience.reading_speed,
                "content_preference": self.primary_audience.content_preference,
                "pain_points": self.primary_audience.pain_points,
                "fulfillment_needs": self.primary_audience.fulfillment_needs,
            },
            "secondary_audiences": [
                {
                    "age_group": a.age_group.value,
                    "gender": a.gender.value,
                    "payment_willingness": a.payment_willingness.value,
                    "reading_speed": a.reading_speed,
                    "content_preference": a.content_preference,
                    "pain_points": a.pain_points,
                    "fulfillment_needs": a.fulfillment_needs,
                }
                for a in self.secondary_audiences
            ],
            "core_selling_points": [
                {
                    "name": sp.name,
                    "description": sp.description,
                    "type": sp.type,
                    "delivery_mechanism": sp.delivery_mechanism,
                    "frequency": sp.frequency,
                    "validation_keywords": sp.validation_keywords,
                    "minimum_intensity": sp.minimum_intensity,
                }
                for sp in self.core_selling_points
            ],
            "differentiation_tags": self.differentiation_tags,
            "unique_selling_proposition": self.unique_selling_proposition,
            "constraints": {
                "forbidden_elements": self.constraints.forbidden_elements,
                "required_elements": self.constraints.required_elements,
                "min_hook_score": self.constraints.min_hook_score,
                "max_chapters_without_payoff": self.constraints.max_chapters_without_payoff,
                "target_chapter_length": self.constraints.target_chapter_length,
                "paywall_earliest_chapter": self.constraints.paywall_earliest_chapter,
                "genre_drift_tolerance": self.constraints.genre_drift_tolerance,
            } if self.constraints else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommercialConstitution":
        """从字典反序列化"""
        # 解析primary_audience
        pa_data = data["primary_audience"]
        primary_audience = AudienceProfile(
            age_group=AgeGroup(pa_data["age_group"]),
            gender=Gender(pa_data["gender"]),
            payment_willingness=PaymentWillingness(pa_data["payment_willingness"]),
            reading_speed=pa_data.get("reading_speed", "moderate"),
            content_preference=pa_data.get("content_preference", []),
            pain_points=pa_data.get("pain_points", []),
            fulfillment_needs=pa_data.get("fulfillment_needs", []),
        )

        # 解析secondary_audiences
        secondary_audiences = []
        for sa_data in data.get("secondary_audiences", []):
            secondary_audiences.append(AudienceProfile(
                age_group=AgeGroup(sa_data["age_group"]),
                gender=Gender(sa_data["gender"]),
                payment_willingness=PaymentWillingness(sa_data["payment_willingness"]),
                reading_speed=sa_data.get("reading_speed", "moderate"),
                content_preference=sa_data.get("content_preference", []),
                pain_points=sa_data.get("pain_points", []),
                fulfillment_needs=sa_data.get("fulfillment_needs", []),
            ))

        # 解析core_selling_points
        core_selling_points = []
        for sp_data in data.get("core_selling_points", []):
            core_selling_points.append(SellingPoint(
                name=sp_data["name"],
                description=sp_data["description"],
                type=sp_data["type"],
                delivery_mechanism=sp_data["delivery_mechanism"],
                frequency=sp_data["frequency"],
                validation_keywords=sp_data.get("validation_keywords", []),
                minimum_intensity=sp_data.get("minimum_intensity", 0.5),
            ))

        # 解析constraints
        constraints = None
        if data.get("constraints"):
            c_data = data["constraints"]
            constraints = ConstitutionConstraints(
                forbidden_elements=c_data.get("forbidden_elements", []),
                required_elements=c_data.get("required_elements", []),
                min_hook_score=c_data.get("min_hook_score", 75),
                max_chapters_without_payoff=c_data.get("max_chapters_without_payoff", 3),
                target_chapter_length=c_data.get("target_chapter_length", 3000),
                paywall_earliest_chapter=c_data.get("paywall_earliest_chapter", 30),
                genre_drift_tolerance=c_data.get("genre_drift_tolerance", 0.2),
            )

        return cls(
            constitution_id=data["constitution_id"],
            work_title=data["work_title"],
            target_platform=Platform(data["target_platform"]),
            primary_genre=Genre(data["primary_genre"]),
            secondary_genres=[Genre(g) for g in data.get("secondary_genres", [])],
            primary_audience=primary_audience,
            secondary_audiences=secondary_audiences,
            core_selling_points=core_selling_points,
            differentiation_tags=data.get("differentiation_tags", []),
            unique_selling_proposition=data.get("unique_selling_proposition", ""),
            constraints=constraints,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            version=data.get("version", "1.0"),
        )

    def save_to_file(self, filepath: str):
        """保存到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> "CommercialConstitution":
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
