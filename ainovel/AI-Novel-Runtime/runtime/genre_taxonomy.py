"""genre_taxonomy.py — the single source of truth for genre-keyed defaults.

Two things live here, both keyed by genre name: CHANNEL routing (男频/女频) and
the PACING defaults (payoff cadence, free-chapter count, volume length). They
share a home because they share a key and a discipline — one table, one place to
correct when real platform data arrives.

NOT here on purpose: per-chapter character targets. `runtime/chapter_length.py`
already owns chapter length (role-bound bands); adding a second length number
keyed by genre would create exactly the drift this module exists to remove.
Genre affects HOW OFTEN a payoff lands, not how long a chapter runs.

--- Part 1: channel routing ---

The 男频/女频 channel default used to be duplicated as a literal set in two
places, with a comment asking the next editor to keep them in sync by hand:

  - runtime/positioning/generate.py  `_MALE_LEAN = {"玄幻", "仙侠", "科幻", "奇幻"}`
  - runtime/genesis/brain_gen.py     `_MALE_LEAN = {"玄幻", "仙侠", "科幻", "奇幻"}`

They did stay in sync — and were both WRONG the same way. The set held four
一级题材 and nothing else, so every other male-channel genre (武侠 都市 历史
游戏 诸天无限) and EVERY 二级分类 name (东方玄幻 异世大陆 王朝争霸 高武世界
都市异能 异术超能 青春校园 娱乐明星 商战职场 …) fell through to 女频 whenever
the outline's `market_position.channel` was silent. That is a deterministic
misroute, not an evaluative mislabel: it poisons the folded Brain's
`genre.channel`, the Position's `reader_segment.primary`/`leans_on`, and then
the admission check's channel-consistency comparison.

Both `positioning/` and `genesis/` import THIS leaf (they do not import each
other), so the genre→channel contract has exactly one home.

DISCIPLINE:
  - Pure data + pure functions. No I/O, no model, no schema coupling — the
    frozen novel-brain / market-position schemas keep `channel` a free string
    and are untouched by this module.
  - A CHANNEL DEFAULT ONLY. An authored `market_position.channel` always wins;
    this module is consulted only when the author left it blank.
  - Advisory, never gates (ADR-003). An unknown genre is not an error — it
    degrades to `DEFAULT_CHANNEL` exactly as the old literal set did.
  - Reference: docs/QIDIAN_GENRE_ELEMENT_STANDARD.md (九题材) and
    docs/QIDIAN_SUBGENRE_DEEP_DIVE.md §5 (二级分类落地参数表). The taxonomy
    names below are 起点's own category names.

--- Part 2: pacing defaults ---

`outline/agents.py` hardcoded `{"cadence_chapters": 3}` for every genre, while
the same file already varied power tiers and reward types BY genre
(`_GENRE_POWER_TIERS`). So a 王朝争霸 outline (势力级兑现, ~6 章) and a 都市生活
outline (~3 章) got the same payoff rhythm, and every downstream consumer of
`reward_loop.cadence_chapters` inherited it:

  - runtime/scene/serial_pacing.py  — climax-rhythm violation vs the cadence
  - runtime/dashboard/report.py     — the cadence readout
  - runtime/arc/projection.py       — arc payoff spacing
  - runtime/outline/agents.py       — the first-30-chapter beat weave

EVIDENCE GRADE (this matters — do not silently promote it):
The cadence numbers are C-grade experience intervals from
QIDIAN_SUBGENRE_DEEP_DIVE.md §5, NOT measured values. Web research for those
docs failed, so nothing here is calibrated against real 起点 data. They are
better than one hardcoded 3 for all genres because they are at least
genre-differentiated in the right direction, but they are a STARTING POINT for
generation, never a truth. When real ReaderSignal data lands, re-derive them and
delete what the data contradicts.

DISCIPLINE (pacing half):
  - A DEFAULT ONLY. An authored `reward_loop.cadence_chapters` always wins —
    same "the human wins" rule as channel.
  - Advisory, never gates (ADR-003). serial_pacing measures deviation from the
    cadence and reports it; it does not block a build.
  - Unknown genre => DEFAULT_CADENCE (3), which preserves the old behavior
    exactly for any genre not in the table.

--- Part 3: genre discriminant markers (for drift detection) ---

QIDIAN_SUBGENRE_DEEP_DIVE.md §4.3 documents a degradation gradient: 异世大陆 /
武侠 / 仙侠 / 高武世界 all slide toward generic 东方玄幻, which slides toward
undifferentiated 升级爽文. The mechanism is a property of the model, not the
author: 玄幻 is the most-represented genre in the training prior, so absent an
active constraint the prose drifts toward it. Consequence: chapter 30 reads LESS
like its declared subgenre than chapter 3 did.

`_GENRE_MARKERS` lists, per genre, the lexical signals of that genre's
判别式要素 — the vocabulary a chapter cannot avoid if it is still delivering the
genre's promise. 高武世界 that stopped mentioning 段位/评级/武者协会 has stopped
being 高武世界 even if it still has fights.

HONEST LIMITATION (read before trusting a finding):
Marker density is a PROXY. A chapter can keep the genre's substance while using
different words, and can stuff markers while delivering nothing. So this measures
vocabulary presence, not genre fidelity — it is a cheap smoke alarm pointing a
human at a range of chapters, not a verdict. That is exactly why it is advisory
(ADR-003) and reports `evaluative`.
"""
from __future__ import annotations

import re

MALE_CHANNEL = "男频"
FEMALE_CHANNEL = "女频"

# Genre names that default to 男频. Both 一级题材 and 起点 二级分类 names are
# listed, because callers hand us whichever granularity the outline used
# (`outline.genre[0]` is free text and may be either).
MALE_LEAN_GENRES = frozenset({
    # --- 一级题材 (nine, per QIDIAN_GENRE_ELEMENT_STANDARD.md) ---
    "玄幻", "奇幻", "武侠", "仙侠", "都市", "历史", "游戏", "科幻", "诸天无限",
    # --- 玄幻 二级分类 ---
    "东方玄幻", "异世大陆", "王朝争霸", "高武世界",
    # --- 都市 二级分类 ---
    "都市生活", "都市异能", "异术超能", "青春校园", "娱乐明星", "商战职场",
    # --- 其他常用二级/流派名 ---
    "修仙", "修真", "武侠幻想", "古典仙侠", "现代修真", "神话修真",
    "架空历史", "两宋元明", "秦汉三国", "上古先秦", "历史传记", "军事",
    "电子竞技", "虚拟网游", "游戏异界", "游戏系统",
    "无限流", "诸天万界", "末世危机", "时空穿梭", "星际文明", "未来世界",
    "领主流", "幕后流", "克苏鲁", "西方奇幻", "剑与魔法", "史诗奇幻",
    "都市异术", "异世争霸", "转世重生", "重生",
})

# Genre names that default to 女频. Kept explicit rather than "everything else"
# so a typo lands in the DEFAULT_CHANNEL bucket instead of silently flipping
# channel. Mirrors the 女频 keyword groups in runtime/market/analyzer.py.
FEMALE_LEAN_GENRES = frozenset({
    "言情", "现代言情", "古代言情", "幻想言情", "仙侠奇缘", "浪漫青春",
    "豪门世家", "婚恋", "职场婚恋", "青春校园言情",
    "宅斗", "宫斗", "宫廷侯爵", "女尊",
    "治愈", "救赎", "疯批", "双强", "甜宠", "追妻",
})

# What an unrecognized genre gets. 男频 because this project's production line,
# reference corpus, and every shipped baseline are 起点男频 (see the launch plan
# in docs/); a genre we failed to classify is far likelier to be an unlisted
# male-channel subgenre than a female-channel one. The old code defaulted the
# other way, which is precisely how 武侠/都市/历史/游戏 got misrouted.
DEFAULT_CHANNEL = MALE_CHANNEL


def channel_for_genre(genre: str | None) -> str:
    """The channel a genre name defaults to. Deterministic, never raises.

    Exact match first, then a containment pass so compound authored names
    ("东方玄幻·宗门流", "都市异能流") still route. Unknown => DEFAULT_CHANNEL.
    """
    name = (genre or "").strip()
    if not name:
        return DEFAULT_CHANNEL
    if name in MALE_LEAN_GENRES:
        return MALE_CHANNEL
    if name in FEMALE_LEAN_GENRES:
        return FEMALE_CHANNEL
    # Longest-first so 都市异能 wins over 都市 when both are substrings.
    for known in sorted(FEMALE_LEAN_GENRES, key=len, reverse=True):
        if known in name:
            return FEMALE_CHANNEL
    for known in sorted(MALE_LEAN_GENRES, key=len, reverse=True):
        if known in name:
            return MALE_CHANNEL
    return DEFAULT_CHANNEL


def resolve_channel(authored: str | None, genre: str | None) -> str:
    """The channel to use: an authored value always wins over the genre default.

    This is the whole contract both callers need — it keeps "the human wins"
    (ADR-009 in spirit) in one place instead of re-deriving `authored or
    default(genre)` at each call site.
    """
    return (authored or "").strip() or channel_for_genre(genre)


# --------------------------------------------------------------------------- #
# Part 2: pacing defaults (C-grade experience intervals — see module docstring) #
# --------------------------------------------------------------------------- #

# The old hardcoded value, kept as the degrade target so any genre absent from
# the table below behaves EXACTLY as before this module existed.
DEFAULT_CADENCE = 3

# genre -> payoff cadence in chapters (how often a 小兑现 should land).
# Source: docs/QIDIAN_SUBGENRE_DEEP_DIVE.md §5. Rationale for the spread: a
# payoff's natural period scales with the size of the unit that changes. 都市
# changes a person's circumstances (fast); 王朝争霸 changes a faction's holdings
# (slow). Values are deliberately coarse (3–6) — a finer grain would imply a
# precision this data does not have.
_GENRE_CADENCE = {
    # --- 一级题材 ---
    "都市": 3, "游戏": 3, "武侠": 3,
    "玄幻": 4, "科幻": 4, "诸天无限": 4,
    "奇幻": 5, "仙侠": 5, "历史": 5,
    # --- 玄幻 二级分类 ---
    "东方玄幻": 4, "高武世界": 4, "异世大陆": 5, "王朝争霸": 6,
    # --- 都市 二级分类 ---
    "都市生活": 3, "都市异能": 3, "青春校园": 3, "娱乐明星": 3,
    "异术超能": 4, "商战职场": 4,
    # --- 其他常用流派名 ---
    "悬疑": 3, "修仙": 5, "修真": 5, "架空历史": 5, "无限流": 4,
    "电子竞技": 3, "领主流": 5, "克苏鲁": 5,
}


def cadence_for_genre(genre: str | None) -> int:
    """Payoff cadence (chapters) a genre defaults to. Never raises.

    Same match discipline as `channel_for_genre`: exact, then longest-first
    containment so 都市异能 wins over 都市. Unknown => DEFAULT_CADENCE.
    """
    name = (genre or "").strip()
    if not name:
        return DEFAULT_CADENCE
    if name in _GENRE_CADENCE:
        return _GENRE_CADENCE[name]
    for known in sorted(_GENRE_CADENCE, key=len, reverse=True):
        if known in name:
            return _GENRE_CADENCE[known]
    return DEFAULT_CADENCE


def resolve_cadence(authored: int | None, genre: str | None) -> int:
    """The cadence to use: an authored positive int always wins over the default.

    Mirrors `resolve_channel`. A non-positive or non-int authored value is
    treated as absent — outline/qa.py requires a positive integer, so passing a
    bad value through would only move the failure downstream.
    """
    if isinstance(authored, int) and not isinstance(authored, bool) and authored > 0:
        return authored
    return cadence_for_genre(genre)


# --------------------------------------------------------------------------- #
# Part 3: genre discriminant markers (see module docstring for the limitation)  #
# --------------------------------------------------------------------------- #

# genre -> lexical signals of that genre's 判别式要素. Sourced from
# QIDIAN_SUBGENRE_DEEP_DIVE.md §2/§3 (必须有 column) and
# QIDIAN_GENRE_ELEMENT_STANDARD.md §11.3.
#
# Selection rule: a marker must be (a) hard to avoid while still delivering the
# genre promise, and (b) NOT shared with the genre this one degrades INTO —
# otherwise density stays flat while the prose drifts, and the detector is blind
# to the one thing it exists to catch. So 高武世界's markers are the social-
# recognition words (段位/评级/协会/编制), not 突破/修炼 which generic 玄幻 also uses.
_GENRE_MARKERS = {
    # --- 玄幻 二级分类 ---
    "东方玄幻": ["境界", "修为", "灵气", "宗门", "长老", "丹药", "灵石", "突破"],
    "异世大陆": ["公会", "评级", "骑士", "法师", "学院", "魔力", "王国", "领主"],
    "王朝争霸": ["粮草", "兵马", "疆域", "城池", "赋税", "军令", "朝廷", "封赏"],
    "高武世界": ["段位", "评级", "武者", "协会", "考核", "编制", "异兽", "测评"],
    # --- 都市 二级分类 ---
    "都市生活": ["房租", "工资", "生意", "口碑", "街坊", "手艺", "订单", "存款"],
    "都市异能": ["异能", "觉醒", "组织", "管理局", "任务", "隐秘", "普通人", "身份"],
    "异术超能": ["能力", "等级", "进化", "规则", "限制", "冷却", "觉醒者", "研究所"],
    "青春校园": ["考试", "排名", "班级", "老师", "同学", "竞赛", "成绩", "校园"],
    "娱乐明星": ["剧组", "舞台", "经纪", "票房", "收视", "粉丝", "综艺", "作品"],
    "商战职场": ["股权", "合同", "谈判", "融资", "市场", "董事会", "报表", "项目"],
    # --- 一级题材 (used when the outline names only the primary genre) ---
    "玄幻": ["境界", "修为", "灵气", "宗门", "丹药", "突破"],
    "仙侠": ["寿元", "道心", "灵脉", "闭关", "劫", "仙"],
    "武侠": ["江湖", "门派", "招式", "内力", "镖", "侠"],
    "奇幻": ["魔力", "仪式", "位阶", "教会", "序列", "代价"],
    "都市": ["公司", "生意", "圈子", "身份", "资源", "名声"],
    "历史": ["朝廷", "官", "百姓", "粮", "礼", "史"],
    "游戏": ["等级", "技能", "副本", "装备", "属性", "公会"],
    "科幻": ["能源", "舰", "系统", "数据", "文明", "实验"],
    "诸天无限": ["副本", "主神", "轮回", "积分", "兑换", "任务"],
}


# Authors mark their own coinages by quoting them (“梦墟”/「梦晶」). Those coined
# terms — not stock genre words — carry a book's actual genre identity.
_QUOTED_TERM_RE = re.compile(r'[“"「『]([一-龥]{2,8})[”"」』]')

# Fields whose prose is AUTHORED (not generated), so the coinages in them are the
# book's declared vocabulary rather than whatever the model drifted into.
_AUTHORED_MARKER_FIELDS = (
    ("world", "summary"), ("world", "rules"),
    ("core_hook",), ("logline",),
    ("mission",), ("promise",),
)


def _collect_authored_text(source: dict, path: tuple) -> list[str]:
    cur: object = source
    for key in path:
        if not isinstance(cur, dict):
            return []
        cur = cur.get(key)
    if isinstance(cur, str):
        return [cur]
    if isinstance(cur, list):
        return [x for x in cur if isinstance(x, str)]
    return []


def extract_authored_markers(*sources: dict, limit: int = 12) -> list[str]:
    """Coined terms the AUTHOR quoted in outline/brain prose, in first-seen order.

    WHY THIS EXISTS (measured, not theorized): on the real 33-chapter baseline the
    stock `_GENRE_MARKERS` table landed 20 total hits for 都市 across ~177k chars
    and flagged 31/33 chapters as genre-less, while the book's own coinages
    (梦墟/核心执念/梦晶) appeared ~1400 times with a stable, rising density. A book's
    genre identity lives in ITS OWN vocabulary; the stock table is the fallback for
    books that haven't coined any, not the primary instrument.

    Deterministic and order-stable. Empty when the sources coin nothing.
    """
    found: list[str] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        for path in _AUTHORED_MARKER_FIELDS:
            for text in _collect_authored_text(source, path):
                for term in _QUOTED_TERM_RE.findall(text):
                    if term not in found:
                        found.append(term)
    return found[:limit]


# genre -> the ONE thing that genre cannot lose, plus what must not replace it.
# Sourced from QIDIAN_SUBGENRE_DEEP_DIVE.md §5 (判别式要素与禁写项) and
# QIDIAN_GENRE_ELEMENT_STANDARD.md §11.3. `must` is the discriminant requirement;
# `forbid` are the failure modes that specific genre degrades into.
_GENRE_CONTRACT = {
    "东方玄幻": {
        "must": "力量刻度必须可数：读者随时能说出主角现在第几档、共几档；跨大境要解锁新玩法，不只是数值变大",
        "forbid": ["刻度通胀（过早打穿开篇设定的最高境界）", "用「众人震惊」代替结果确认",
                    "开篇倾泻境界名词"],
    },
    "异世大陆": {
        "must": "等级必须有社会含义：由公会/学院/贵族体系公开认定，并能兑换具体地位与资源；穿越者的知识差必须先撞上时代限制再想办法",
        "forbid": ["译名腔（「哦，我的老伙计」式对白）", "术语倾泻", "魔法没有代价",
                    "伪西幻（换音译名但内核仍是中式宗门）"],
    },
    "王朝争霸": {
        "must": "势力数字必须可感：地盘/人口/粮草/兵员/赋税的增减要具体到能记账；敌方是有决策层与情报能力的集团",
        "forbid": ["主角一言堂（谋士只捧不谏）", "战争无后勤", "敌国降智", "地图数字变大但规则不变"],
    },
    "高武世界": {
        "must": "段位即社会货币：武道段位必须由官方测评认定，并与学籍/工资/住房/话语权/法律豁免等现实待遇强绑定",
        "forbid": ["段位失去社会含义（退化成东方玄幻换皮）", "军警官方永久缺席",
                    "异兽只当经验包", "抛弃现实压力锚点"],
    },
    "都市生活": {
        "must": "压力与收益都必须具体：欠款数额/房租日期/病历，以及第一笔钱是多少、评价涨到几星；烟火气要落到具体物",
        "forbid": ["金额数量级失控（写成神豪流）", "细节概括化（只说「生意变好」不写具体物）",
                    "温水章（章末状态与章初相同）"],
    },
    "都市异能": {
        "must": "必须回答「官方为何不管」：要么有管理机构，要么有明确的隐匿规则与代价；异能要有范围/冷却/代价/克制的具体规则",
        "forbid": ["异能无规则（模糊的「精神力」）", "官方永久缺席", "抛弃现实线与普通身份"],
    },
    "异术超能": {
        "must": "能力边界必须可推演：规则清晰稳定，爽点来自在限制内找到出人意料的解法，而非力量更大",
        "forbid": ["能力清单化（每章加一个新能力）", "规则随剧情变动", "只有战斗没有应用",
                    "长篇解释能力原理而主角无动作"],
    },
    "青春校园": {
        "must": "校园日历必须当节奏器：月考/竞赛/运动会/升学提供阶段目标；社会性反馈要具体（排名公示、老师态度转变）",
        "forbid": ["无学业只有恋爱", "老师与家长工具化", "跳过努力过程直接出成绩",
                    "越界的未成年情感描写"],
    },
    "娱乐明星": {
        "must": "作品必须有说服力：靠观众/评委/同行反应的具体性证明作品好，而不是作者断言「太惊艳了」；行业细节要真",
        "forbid": ["作者宣称作品好", "行业悬浮（不知道剧组怎么运转）", "同行反派降智",
                    "指涉真实艺人/公司/节目/歌曲"],
    },
    "商战职场": {
        "must": "信息差必须可验证：主角的判断要写出推理链条，让读者跟得上；商业细节（条款/尽调/股权/渠道）要站得住",
        "forbid": ["商业逻辑经不起推敲", "靠背景碾压而非商业能力", "职场变成办公室恋爱",
                    "专业名词堆砌但无实际运作"],
    },
    # --- 一级题材 ---
    "玄幻": {
        "must": "力量刻度必须可数，且跨境要有质变与代价",
        "forbid": ["刻度通胀", "无限套娃升级（只加数值不改玩法）", "用众人震惊代替结果确认"],
    },
    "仙侠": {
        "must": "寿元与时间尺度必须与凡人不同并产生剧情后果；修炼靠稀缺资源；长生要真的付出过代价",
        "forbid": ["把宗门写成公司、长老写成上司（道韵全无）", "用「十年后」跳过困难",
                    "自创全套境界命名", "神通清单化"],
    },
    "武侠": {
        "must": "江湖规矩必须有约束力（比武不杀/镖不失手/辈分/黑白分际）；招式要有形象与攻防意图",
        "forbid": ["玄幻化（内功变灵气、名位变境界）", "打斗流水账（只有动作无意图）",
                    "配角工具化", "文风在白话与半文言间漂移"],
    },
    "奇幻": {
        "must": "力量必须有代价（理智/寿命/人性/负债/身份为抵押）；体系术语前三章不超过五个",
        "forbid": ["译名腔", "术语倾泻", "体系只写在纸上（正文只用到前两阶）", "过早解释终极真相"],
    },
    "都市": {
        "must": "爽点必须有见证与传播：胜利要有第三方看见并扩散，否则商业效力减半",
        "forbid": ["爽点通胀", "行业悬浮", "打脸对象不会学习"],
    },
    "历史": {
        "must": "时代摩擦必须存在：现代方案要先撞上材料/人力/政治现实；古人用时代内最优解博弈",
        "forbid": ["金手指过硬（随手炼钢造枪）", "称谓与官制错误", "古人被写成傻子",
                    "轻佻处理民族苦难与战争暴行"],
    },
    "游戏": {
        "must": "数值与规则必须前后一致且可验算：读者能复现主角的胜利推导",
        "forbid": ["数值漂移（同一技能前后矛盾）", "副本同构", "赢在数值而非操作与理解",
                    "指涉真实游戏/公司/赛事/选手"],
    },
    "科幻": {
        "must": "一个能持续产生新问题的核心点子，且规则边界可被读者预判与利用；技术冲击要落到具体人的选择",
        "forbid": ["设定倾泻（开篇技术名词过载）", "点子透支", "无动作的解说段",
                    "人物工具化（只有设定没有人）"],
    },
    "诸天无限": {
        "must": "跨副本继承规则必须明确（什么带得走、代价是什么）；相邻副本的规则类型必须不同；跨副本主线每 2–3 个副本推进一次",
        "forbid": ["副本同构（每个副本都是进入—打—通关）", "积累不可感", "原著角色只借名字不借性格",
                    "逛世界而没有主线"],
    },
}


def contract_for_genre(genre: str | None) -> dict:
    """The genre's discriminant requirement + degradation-forbid list.

    Empty dict when unknown — callers must degrade rather than invent a contract.
    Same match discipline as the other tables.
    """
    name = (genre or "").strip()
    if not name:
        return {}
    if name in _GENRE_CONTRACT:
        return dict(_GENRE_CONTRACT[name])
    for known in sorted(_GENRE_CONTRACT, key=len, reverse=True):
        if known in name:
            return dict(_GENRE_CONTRACT[known])
    return {}


def render_genre_contract(genre: str | None, *,
                          authored_markers: list[str] | None = None) -> str:
    """Render the genre contract into a generation-time constraint block.

    This is the PREVENTION half of the loop whose detection half is
    scene/serial_genre_drift.check_serial_genre_drift. Detection measures whether
    the genre's vocabulary survived; this tells the model to keep delivering the
    genre's discriminant requirement in the first place.

    `authored_markers` are the book's own coined terms
    (`extract_authored_markers`). Naming them here closes the loop directly: the
    detector counts those exact terms, so asking the model to keep using them
    targets the same signal that gets measured.

    Returns a stable sentinel for an unknown genre so a bound prompt slot is never
    empty. Deterministic.
    """
    contract = contract_for_genre(genre)
    shown = (genre or "").strip()
    terms = [m for m in (authored_markers or []) if m and m.strip()]

    if not contract:
        if terms:
            return ("本作自有核心术语：" + "、".join(f"「{t}」" for t in terms)
                    + "。本章必须继续使用这些术语来承载题材特征，不要改用泛化表述。")
        return "（未声明题材契约，本章题材特征不受额外约束）"

    lines = [f"本作题材：{shown}。以下是该题材的判别式要素，本章必须继续兑现："]
    lines.append(f"- 必须做到：{contract['must']}")
    forbid = contract.get("forbid") or []
    if forbid:
        lines.append("- 必须避免（这些是本题材退化为通用升级流的典型征兆）：")
        lines.extend(f"  · {f}" for f in forbid)
    if terms:
        lines.append("- 本作自有核心术语：" + "、".join(f"「{t}」" for t in terms)
                     + "。本章应继续用这些术语承载题材特征，不要改用泛化表述。")
    lines.append("题材契约只约束「本章必须仍然像这个题材」，"
                 "它不覆盖事实、强制令或导演目标，也不要求写入故事未挣得的事件。")
    return "\n".join(lines)


def markers_for_genre(genre: str | None) -> list[str]:
    """Discriminant markers for a genre. Empty list when unknown — callers must
    treat empty as "cannot analyze" and degrade, never as "zero markers found".

    Same match discipline as the other two tables: exact, then longest-first
    containment so 都市异能 wins over 都市.
    """
    name = (genre or "").strip()
    if not name:
        return []
    if name in _GENRE_MARKERS:
        return list(_GENRE_MARKERS[name])
    for known in sorted(_GENRE_MARKERS, key=len, reverse=True):
        if known in name:
            return list(_GENRE_MARKERS[known])
    return []
